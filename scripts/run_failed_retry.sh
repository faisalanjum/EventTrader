#!/bin/bash
# Auto-retry all failed/timed-out chunks from the 9 gap-fill runs
# Runs with the updated 6h CHUNK_MAX_WAIT_SECONDS
# SISMEMBER check skips already-confirmed reports automatically

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$(dirname "$SCRIPT_DIR")/logs"
MASTER_LOG="$LOG_DIR/gap_fill_retry_$(date +%Y%m%d_%H%M%S).log"

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

log "===== SCANNING FOR FAILED CHUNKS ====="

# Find all ChunkHist dirs from the gap fill batch (started Apr 2)
FAILED_RANGES=()
for combined_log in "$LOG_DIR"/ChunkHist_*_2026040*/combined_*.log; do
    [ -f "$combined_log" ] || continue
    # Extract failed chunk date ranges
    while IFS= read -r line; do
        # Parse: "ERROR: Python script exited with status 1 for chunk 2026-02-16 to 2026-02-20."
        from_date=$(echo "$line" | grep -oP 'for chunk \K\d{4}-\d{2}-\d{2}')
        to_date=$(echo "$line" | grep -oP 'to \K\d{4}-\d{2}-\d{2}')
        if [ -n "$from_date" ] && [ -n "$to_date" ]; then
            FAILED_RANGES+=("$from_date:$to_date")
            log "  Found failed chunk: $from_date to $to_date (from $combined_log)"
        fi
    done < <(grep "ERROR: Python script exited" "$combined_log" 2>/dev/null)
done

# Also scan Run 2+ logs that may still be writing
for combined_log in "$LOG_DIR"/ChunkHist_*_2026040*/combined_*.log; do
    [ -f "$combined_log" ] || continue
    while IFS= read -r line; do
        from_date=$(echo "$line" | grep -oP 'for chunk \K\d{4}-\d{2}-\d{2}')
        to_date=$(echo "$line" | grep -oP 'to \K\d{4}-\d{2}-\d{2}')
        if [ -n "$from_date" ] && [ -n "$to_date" ]; then
            # Deduplicate
            key="$from_date:$to_date"
            found=0
            for existing in "${FAILED_RANGES[@]}"; do
                [ "$existing" = "$key" ] && found=1 && break
            done
            [ "$found" -eq 0 ] && FAILED_RANGES+=("$key") && log "  Found failed chunk: $from_date to $to_date"
        fi
    done < <(grep "ERROR: Python script exited" "$combined_log" 2>/dev/null)
done

# Deduplicate
declare -A SEEN
UNIQUE_RANGES=()
for range in "${FAILED_RANGES[@]}"; do
    if [ -z "${SEEN[$range]}" ]; then
        SEEN[$range]=1
        UNIQUE_RANGES+=("$range")
    fi
done

TOTAL=${#UNIQUE_RANGES[@]}
if [ "$TOTAL" -eq 0 ]; then
    log "No failed chunks found! All chunks completed successfully."
    exit 0
fi

log ""
log "===== RETRYING $TOTAL FAILED CHUNKS (6h timeout) ====="
log ""

COMPLETED=0
FAILED=0

for i in $(seq 0 $((TOTAL - 1))); do
    IFS=':' read -r FROM TO <<< "${UNIQUE_RANGES[$i]}"
    RUN_NUM=$((i + 1))
    log "===== RETRY $RUN_NUM/$TOTAL: $FROM to $TO ====="

    flush_stale

    log "  Starting chunked-historical..."
    RUN_START=$(date +%s)

    bash "$SCRIPT_DIR/event_trader.sh" chunked-historical "$FROM" "$TO"
    EXIT_CODE=$?
    RUN_END=$(date +%s)
    RUN_DURATION=$(( (RUN_END - RUN_START) / 60 ))

    COMBINED_LOG=$(ls -t "$LOG_DIR"/ChunkHist_${FROM}_to_${TO}_*/combined_*.log 2>/dev/null | head -1)
    CHUNK_ERRORS=$(grep -c "exited with ERROR" "$COMBINED_LOG" 2>/dev/null) || true

    if [ "$EXIT_CODE" -ne 0 ]; then
        log "  FAILED after ${RUN_DURATION} minutes (exit code: $EXIT_CODE)"
        FAILED=$((FAILED + 1))
    elif [ "${CHUNK_ERRORS:-0}" -gt 0 ] 2>/dev/null; then
        log "  PARTIAL after ${RUN_DURATION} minutes ($CHUNK_ERRORS chunks had errors)"
        FAILED=$((FAILED + 1))
    else
        log "  COMPLETED in ${RUN_DURATION} minutes"
        COMPLETED=$((COMPLETED + 1))
    fi

    log ""
done

END_TIME=$(date +%s)
log "===== RETRY COMPLETE ====="
log "Completed: $COMPLETED / $TOTAL"
log "Failed: $FAILED / $TOTAL"
log ""
log "Next: re-run gap analysis to verify:"
log "  source venv/bin/activate && python3 scripts/report_gap_secapi.py --start-date 2023-01-01 --end-date 2026-03-28"
