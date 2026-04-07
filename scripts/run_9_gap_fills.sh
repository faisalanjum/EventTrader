#!/bin/bash
# Run all 9 targeted gap-fill backfills sequentially
# Prerequisites completed:
#   1. reports:confirmed_in_neo4j SET re-seeded (38,748 accessions)
#   2. pending_returns permanent fix applied (no longer blocks completion gate)
#   3. withoutreturns:* keys already at 0
#
# These 9 runs cover 100% of 3,409 missing accessions (verified programmatically)
# The set_filing() SISMEMBER check skips existing reports automatically.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$(dirname "$SCRIPT_DIR")/logs"
MASTER_LOG="$LOG_DIR/gap_fill_9runs_$(date +%Y%m%d_%H%M%S).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$MASTER_LOG"
}

flush_withoutreturns() {
    local count
    count=$(redis-cli -p 31379 EVAL "local k=redis.call('KEYS','reports:withoutreturns:*'); for _,v in ipairs(k) do redis.call('DEL',v) end; return #k" 0 2>/dev/null)
    if [ "$count" -gt 0 ] 2>/dev/null; then
        log "  Flushed $count stale reports:withoutreturns:* keys"
    fi
    count=$(redis-cli -p 31379 EVAL "local k=redis.call('KEYS','reports:withreturns:*'); for _,v in ipairs(k) do redis.call('DEL',v) end; return #k" 0 2>/dev/null)
    if [ "$count" -gt 0 ] 2>/dev/null; then
        log "  Flushed $count stale reports:withreturns:* keys"
    fi
}

log "===== STARTING 9 TARGETED GAP-FILL RUNS ====="
log "Master log: $MASTER_LOG"
log ""

# Define the 9 runs (ordered by gap count, biggest first)
declare -a RUN_NAMES=(
    "Feb 2026 (1,052 gaps)"
    "Nov-Dec 2025 (738 gaps)"
    "Aug 2024 (538 gaps)"
    "Mar 2026 (515 gaps)"
    "Q4 2024 (250 gaps)"
    "2024 H1 (158 gaps)"
    "2023 full year (124 gaps)"
    "2025 Q1-Q2 (30 gaps)"
    "2025 Aug (4 gaps)"
)
declare -a RUN_FROM=(
    "2026-02-01"
    "2025-10-25"
    "2024-07-25"
    "2026-03-01"
    "2024-09-08"
    "2024-01-01"
    "2023-01-01"
    "2025-02-05"
    "2025-08-05"
)
declare -a RUN_TO=(
    "2026-02-28"
    "2025-12-31"
    "2024-09-01"
    "2026-03-28"
    "2024-12-08"
    "2024-07-24"
    "2023-12-31"
    "2025-06-26"
    "2025-08-25"
)

TOTAL_RUNS=${#RUN_NAMES[@]}
COMPLETED=0
FAILED=0
START_TIME=$(date +%s)

for i in $(seq 0 $((TOTAL_RUNS - 1))); do
    RUN_NUM=$((i + 1))
    log "===== RUN $RUN_NUM/$TOTAL_RUNS: ${RUN_NAMES[$i]} ====="
    log "  Date range: ${RUN_FROM[$i]} to ${RUN_TO[$i]}"

    # Safety: flush any stale withreturns/withoutreturns between runs
    flush_withoutreturns

    log "  Starting chunked-historical..."
    RUN_START=$(date +%s)

    bash "$SCRIPT_DIR/event_trader.sh" chunked-historical "${RUN_FROM[$i]}" "${RUN_TO[$i]}"
    EXIT_CODE=$?
    RUN_END=$(date +%s)
    RUN_DURATION=$(( (RUN_END - RUN_START) / 60 ))

    # event_trader.sh always exits 0 even if chunks fail (exit 1 is commented out).
    # So check the combined log for actual chunk errors.
    COMBINED_LOG=$(ls -t "$LOG_DIR"/ChunkHist_${RUN_FROM[$i]}_to_${RUN_TO[$i]}_*/combined_*.log 2>/dev/null | head -1)
    CHUNK_ERRORS=0
    if [ -n "$COMBINED_LOG" ]; then
        CHUNK_ERRORS=$(grep -c "exited with ERROR" "$COMBINED_LOG" 2>/dev/null) || true
    fi

    if [ "$EXIT_CODE" -ne 0 ]; then
        log "  FAILED after ${RUN_DURATION} minutes (exit code: $EXIT_CODE)"
        FAILED=$((FAILED + 1))
    elif [ "${CHUNK_ERRORS:-0}" -gt 0 ] 2>/dev/null; then
        log "  PARTIAL after ${RUN_DURATION} minutes ($CHUNK_ERRORS chunks had errors, see $COMBINED_LOG)"
        FAILED=$((FAILED + 1))
    else
        log "  COMPLETED in ${RUN_DURATION} minutes"
        COMPLETED=$((COMPLETED + 1))
    fi

    log ""
done

END_TIME=$(date +%s)
TOTAL_DURATION=$(( (END_TIME - START_TIME) / 60 ))

log "===== ALL 9 RUNS FINISHED ====="
log "Completed: $COMPLETED / $TOTAL_RUNS"
log "Failed: $FAILED / $TOTAL_RUNS"
log "Total time: ${TOTAL_DURATION} minutes"
log ""
log "Next step: re-run gap analysis to verify near-zero PIPELINE_LOST:"
log "  source venv/bin/activate && python3 scripts/report_gap_secapi.py --start-date 2023-01-01 --end-date 2026-03-28"
