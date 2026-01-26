#!/bin/bash
# validate_pit_hook.sh - PostToolUse hook for PIT validation
# Blocks if tool output contains dates AFTER the PIT date
# Log file in same directory as this script

LOG_FILE="$(dirname "$0")/validate_pit_hook.log"
log() { echo "[$(date +%H:%M:%S)] $1" >> "$LOG_FILE"; }

INPUT=$(cat)

# Extract PIT from command (Bash) or query (WebSearch/Perplexity)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // .tool_input.query // ""')
STDOUT=$(echo "$INPUT" | jq -r '.tool_response.stdout // .tool_response // ""')

# Extract first date from command/query as PIT
PIT=$(echo "$COMMAND" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1)
if [ -z "$PIT" ]; then
    log "SKIP (no PIT date in command)"
    echo "{}"; exit 0
fi

PIT_EPOCH=$(date -d "$PIT" +%s 2>/dev/null)
if [ -z "$PIT_EPOCH" ]; then
    log "SKIP (can't parse PIT: $PIT)"
    echo "{}"; exit 0
fi

log "=================================================="
log "PIT: $PIT | STDOUT_LINES: $(echo "$STDOUT" | wc -l)"

# Check all dates in output
for DATE in $(echo "$STDOUT" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | sort -u); do
    DATE_EPOCH=$(date -d "$DATE" +%s 2>/dev/null) || continue
    if [ "$DATE_EPOCH" -gt "$PIT_EPOCH" ]; then
        log "BLOCK ($DATE > $PIT)"
        echo "{\"decision\":\"block\",\"reason\":\"PIT violation: $DATE > $PIT\"}"
        exit 0
    fi
done

log "ALLOW (all dates <= $PIT)"
echo "{}"
