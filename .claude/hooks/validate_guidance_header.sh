#!/bin/bash
# validate_guidance_header.sh
# Blocks guidance.csv writes that use an old or incorrect header.

INPUT=$(cat 2>/dev/null) || INPUT=""
if [ -z "$INPUT" ]; then
  echo "{}"
  exit 0
fi

FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // .tool_input.new_string // empty')

case "$FILE" in
  *"/earnings-analysis/Companies/"*/"guidance.csv") ;;
  *) echo "{}"; exit 0 ;;
esac

EXPECTED="quarter|period_type|fiscal_year|fiscal_quarter|segment|metric|low|mid|high|unit|basis|derivation|qualitative|source_type|source_id|source_key|given_date|section|quote"

# Simple audit log
LOG_FILE="/home/faisal/EventMarketDB/logs/guidance-header-guard.log"
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"; }

# If file exists, ensure its header is already correct.
if [ -f "$FILE" ]; then
  EXISTING=$(head -n 1 "$FILE" | tr -d '\r')
  if [ -n "$EXISTING" ] && [ "$EXISTING" != "$EXPECTED" ]; then
    log "BLOCK existing header mismatch: file=$FILE header=$EXISTING"
    echo "{\"decision\":\"block\",\"reason\":\"guidance.csv has unexpected header; expected: ${EXPECTED}\"}"
    exit 0
  fi
fi

FIRST=$(printf "%s\n" "$CONTENT" | awk 'NF{print; exit}')
if [ -z "$FIRST" ]; then
  echo "{}"
  exit 0
fi

# If creating a new file, header must be correct.
if [ ! -f "$FILE" ]; then
  if [ "$FIRST" != "$EXPECTED" ]; then
    log "BLOCK new header mismatch: file=$FILE header=$FIRST"
    echo "{\"decision\":\"block\",\"reason\":\"guidance.csv header must be: ${EXPECTED}\"}"
    exit 0
  fi
  log "ALLOW new header ok: file=$FILE"
  echo "{}"
  exit 0
fi

# If the write includes a header line, validate it.
if [[ "$FIRST" == "quarter|period_type|"* || "$FIRST" == "time_horizon|"* ]]; then
  if [ "$FIRST" != "$EXPECTED" ]; then
    log "BLOCK write header mismatch: file=$FILE header=$FIRST"
    echo "{\"decision\":\"block\",\"reason\":\"guidance.csv header must be: ${EXPECTED}\"}"
    exit 0
  fi
fi

log "ALLOW write ok: file=$FILE"
echo "{}"
exit 0
