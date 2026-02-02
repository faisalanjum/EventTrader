#!/bin/bash
# validate_judge_output.sh
# Validates per-task judge output files written by news-driver-judge.

INPUT=$(cat 2>/dev/null) || INPUT=""
if [ -z "$INPUT" ]; then
  echo "{}"
  exit 0
fi

FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // .tool_input.new_string // empty')

case "$FILE" in
  *"/earnings-analysis/Companies/"*/"manifests/"*/"judge/"*.tsv) ;;
  *) echo "{}"; exit 0 ;;
esac

LOG_DIR="/home/faisal/EventMarketDB/logs"
LOG_FILE="$LOG_DIR/judge-output-guard.log"
mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"; }

if [ -z "$CONTENT" ]; then
  log "BLOCK empty content: file=$FILE"
  echo "{\"decision\":\"block\",\"reason\":\"Judge output file is empty\"}"
  exit 0
fi

non_empty=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  non_empty=$((non_empty+1))
  if [[ "$line" == NO_GUIDANCE\|* ]] || [[ "$line" == ERROR\|* ]]; then
    continue
  fi
  if [[ "$line" == date\|* ]]; then
    log "BLOCK header line found: file=$FILE"
    echo "{\"decision\":\"block\",\"reason\":\"Judge output must not include header\"}"
    exit 0
  fi
  fields=$(printf "%s" "$line" | awk -F'|' '{print NF}')
  if [ "$fields" -ne 12 ]; then
    log "BLOCK invalid field count: file=$FILE fields=$fields line=${line:0:120}"
    echo "{\"decision\":\"block\",\"reason\":\"Judge output must have 12 fields per line\"}"
    exit 0
  fi
done <<< "$CONTENT"

if [ "$non_empty" -ne 1 ]; then
  log "BLOCK multiple lines: file=$FILE count=$non_empty"
  echo "{\"decision\":\"block\",\"reason\":\"Judge output must be a single line\"}"
  exit 0
fi

log "ALLOW judge output: file=$FILE"
echo "{}"
exit 0
