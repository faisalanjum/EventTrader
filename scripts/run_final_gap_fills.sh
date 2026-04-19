#!/bin/bash
# Final gap-fill: recover 1,049 primary-type filings identified by report_gap_secapi.py
# on 2026-04-07. All 1,049 accessions are NOT in Redis confirmed_in_neo4j SET —
# no Redis cleanup needed, standard re-runs will pick them up.
#
# CHUNK_MAX_WAIT_SECONDS = 86400 (24h) — previous 3h timeout failures won't recur.
# SISMEMBER check skips ~40K already-confirmed filings automatically.
#
# Gap distribution:
#   Run 1:  2026-02-16 → 2026-02-28  (685 gaps — failed chunks from original Run 1)
#   Run 2:  2026-03-28 → 2026-04-07  (116 gaps — new April data)
#   Run 3:  2026-03-01 → 2026-03-27  ( 81 gaps — remaining March)
#   Run 4:  2025-11-01 → 2025-12-15  ( 28 gaps — failed Nov-Dec chunks)
#   Run 5:  2023-01-01 → 2023-12-31  ( 88 gaps — 2023 scatter)
#   Run 6:  2024-01-01 → 2024-12-31  ( 60 gaps — 2024 scatter)
#   Run 7:  2025-01-01 → 2025-10-31  ( 46 gaps — 2025 pre-Nov scatter)
#                              Total: 1,104 coverage (exceeds 1,049 — runs overlap some NT types)
#
# Estimated runtime: ~12-18 hours (scatter runs fast since 97%+ filings skip via SISMEMBER)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$(dirname "$SCRIPT_DIR")/logs"
MASTER_LOG="$LOG_DIR/final_gap_fill_$(date +%Y%m%d_%H%M%S).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$MASTER_LOG"
}

flush_stale() {
    local count
    count=$(redis-cli -p 31379 EVAL "local k=redis.call('KEYS','reports:withoutreturns:*'); for _,v in ipairs(k) do redis.call('DEL',v) end; return #k" 0 2>/dev/null)
    [ "$count" -gt 0 ] 2>/dev/null && log "  Flushed $count stale reports:withoutreturns:* keys"
    count=$(redis-cli -p 31379 EVAL "local k=redis.call('KEYS','reports:withreturns:*'); for _,v in ipairs(k) do redis.call('DEL',v) end; return #k" 0 2>/dev/null)
    [ "$count" -gt 0 ] 2>/dev/null && log "  Flushed $count stale reports:withreturns:* keys"
}

# Snapshot baseline
BASELINE_SET=$(redis-cli -p 31379 SCARD reports:confirmed_in_neo4j 2>/dev/null)

log "===== FINAL GAP-FILL: RECOVER 1,049 MISSING FILINGS ====="
log "Master log: $MASTER_LOG"
log "Baseline confirmed SET: $BASELINE_SET"
log "CHUNK_MAX_WAIT_SECONDS: 86400 (24h)"
log ""

# Ordered by priority: biggest fixable gaps first, then scatter runs
declare -a RUN_NAMES=(
    "Feb 2026 failed chunks (685 gaps)"
    "Apr 2026 new data (116 gaps)"
    "Mar 2026 remaining (81 gaps)"
    "Nov-Dec 2025 failed chunks (28 gaps)"
    "2023 full year scatter (88 gaps)"
    "2024 full year scatter (60 gaps)"
    "2025 Jan-Oct scatter (46 gaps)"
)
declare -a RUN_FROM=(
    "2026-02-16"
    "2026-03-28"
    "2026-03-01"
    "2025-11-01"
    "2023-01-01"
    "2024-01-01"
    "2025-01-01"
)
declare -a RUN_TO=(
    "2026-02-28"
    "2026-04-07"
    "2026-03-27"
    "2025-12-15"
    "2023-12-31"
    "2024-12-31"
    "2025-10-31"
)

TOTAL_RUNS=${#RUN_NAMES[@]}
COMPLETED=0
FAILED=0
START_TIME=$(date +%s)

for i in $(seq 0 $((TOTAL_RUNS - 1))); do
    RUN_NUM=$((i + 1))
    log "===== RUN $RUN_NUM/$TOTAL_RUNS: ${RUN_NAMES[$i]} ====="
    log "  Date range: ${RUN_FROM[$i]} to ${RUN_TO[$i]}"

    # Safety: flush stale withreturns/withoutreturns between runs
    flush_stale

    # Snapshot SET before this run
    PRE_SET=$(redis-cli -p 31379 SCARD reports:confirmed_in_neo4j 2>/dev/null)

    log "  Confirmed SET before run: $PRE_SET"
    log "  Starting chunked-historical..."
    RUN_START=$(date +%s)

    bash "$SCRIPT_DIR/event_trader.sh" chunked-historical "${RUN_FROM[$i]}" "${RUN_TO[$i]}"
    EXIT_CODE=$?
    RUN_END=$(date +%s)
    RUN_DURATION=$(( (RUN_END - RUN_START) / 60 ))

    # Check combined log for chunk errors
    COMBINED_LOG=$(ls -t "$LOG_DIR"/ChunkHist_${RUN_FROM[$i]}_to_${RUN_TO[$i]}_*/combined_*.log 2>/dev/null | head -1)
    CHUNK_ERRORS=0
    if [ -n "$COMBINED_LOG" ]; then
        CHUNK_ERRORS=$(grep -c "exited with ERROR" "$COMBINED_LOG" 2>/dev/null) || true
    fi

    # Snapshot SET after this run
    POST_SET=$(redis-cli -p 31379 SCARD reports:confirmed_in_neo4j 2>/dev/null)
    DELTA=$((POST_SET - PRE_SET))

    if [ "$EXIT_CODE" -ne 0 ]; then
        log "  FAILED after ${RUN_DURATION} minutes (exit code: $EXIT_CODE). +$DELTA new confirmations."
        FAILED=$((FAILED + 1))
    elif [ "${CHUNK_ERRORS:-0}" -gt 0 ] 2>/dev/null; then
        log "  PARTIAL after ${RUN_DURATION} minutes ($CHUNK_ERRORS chunks had errors). +$DELTA new confirmations."
        FAILED=$((FAILED + 1))
    else
        log "  COMPLETED in ${RUN_DURATION} minutes. +$DELTA new confirmations."
        COMPLETED=$((COMPLETED + 1))
    fi

    log ""
done

END_TIME=$(date +%s)
TOTAL_DURATION=$(( (END_TIME - START_TIME) / 60 ))
FINAL_SET=$(redis-cli -p 31379 SCARD reports:confirmed_in_neo4j 2>/dev/null)
TOTAL_DELTA=$((FINAL_SET - BASELINE_SET))

log "===== FINAL GAP-FILL COMPLETE ====="
log "Completed: $COMPLETED / $TOTAL_RUNS"
log "Failed: $FAILED / $TOTAL_RUNS"
log "Total time: ${TOTAL_DURATION} minutes"
log "Confirmed SET: $BASELINE_SET → $FINAL_SET (+$TOTAL_DELTA)"
log ""
log "Next step: re-run gap analysis to verify near-zero PIPELINE_LOST:"
log "  source venv/bin/activate && python3 scripts/report_gap_secapi.py --start-date 2023-01-01 --end-date 2026-04-07"
