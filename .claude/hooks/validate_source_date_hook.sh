#!/bin/bash
# validate_source_date_hook.sh - Validates source_pub_date <= analysis_date
# For PostToolUse on Bash - validates echo output from news drivers
#
# Expected format: date|news_id|title|driver|confidence|daily_stock|daily_adj|market_session|source|external_research|source_pub_date
# Field 1: analysis_date (the date being analyzed)
# Field 11: source_pub_date (when the source was published)

# Log file in same directory as this script
LOG_FILE="$(dirname "$0")/validate_source_date_hook.log"

INPUT=$(cat)

# Extract command and response
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')
STDOUT=$(echo "$INPUT" | jq -r '.tool_response.stdout // ""')

# Log helper
log() { echo "[$(date +%H:%M:%S)] $1" >> "$LOG_FILE"; }

log "=================================================="
log "COMMAND: $COMMAND"
log "STDOUT: $STDOUT"

# Only validate echo commands that look like our output format
if ! echo "$COMMAND" | grep -q "^echo "; then
    echo "{}" # Not an echo command, allow
    exit 0
fi

# Check if output has pipe-delimited format with at least 11 fields
FIELD_COUNT=$(echo "$STDOUT" | tr -cd '|' | wc -c)
if [ "$FIELD_COUNT" -lt 10 ]; then
    echo "{}" # Not our format, allow
    exit 0
fi

# Extract fields
ANALYSIS_DATE=$(echo "$STDOUT" | cut -d'|' -f1)
SOURCE_PUB_DATE=$(echo "$STDOUT" | cut -d'|' -f11)

log "ANALYSIS_DATE: $ANALYSIS_DATE | SOURCE_PUB_DATE: $SOURCE_PUB_DATE"

# If source_pub_date is N/A or empty, allow (can't validate)
if [ -z "$SOURCE_PUB_DATE" ] || [ "$SOURCE_PUB_DATE" = "N/A" ]; then
    log "ALLOW (no source date)"
    echo "{}"
    exit 0
fi

# Parse dates
ANALYSIS_EPOCH=$(date -d "$ANALYSIS_DATE" +%s 2>/dev/null)
SOURCE_EPOCH=$(date -d "$SOURCE_PUB_DATE" +%s 2>/dev/null)

if [ -z "$ANALYSIS_EPOCH" ] || [ -z "$SOURCE_EPOCH" ]; then
    log "ALLOW (can't parse dates)"
    echo "{}"
    exit 0
fi

# Validate: source_pub_date must be <= analysis_date
if [ "$SOURCE_EPOCH" -gt "$ANALYSIS_EPOCH" ]; then
    log "BLOCK (source_pub_date $SOURCE_PUB_DATE > analysis_date $ANALYSIS_DATE)"
    echo "{\"decision\":\"block\",\"reason\":\"PIT violation: source published on $SOURCE_PUB_DATE but analyzing $ANALYSIS_DATE. Source must be from on or before the analysis date.\"}"
    exit 0
fi

log "ALLOW (source_pub_date <= analysis_date)"
echo "{}"
