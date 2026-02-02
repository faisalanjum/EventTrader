#!/bin/bash
# validate_gx_output.sh
# Validates per-task guidance output files written by guidance-extract.

INPUT=$(cat 2>/dev/null) || INPUT=""
if [ -z "$INPUT" ]; then
  echo "{}"
  exit 0
fi

FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // .tool_input.new_string // empty')

case "$FILE" in
  *"/earnings-analysis/Companies/"*/"manifests/"*/"gx/"*.tsv) ;;
  *) echo "{}"; exit 0 ;;
esac

LOG_DIR="/home/faisal/EventMarketDB/logs"
LOG_FILE="$LOG_DIR/gx-output-guard.log"
mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"; }

if [ -z "$CONTENT" ]; then
  log "BLOCK empty content: file=$FILE"
  echo "{\"decision\":\"block\",\"reason\":\"GX output file is empty\"}"
  exit 0
fi

# Validate each non-empty line
while IFS= read -r line; do
  [ -z "$line" ] && continue
  if [[ "$line" == NO_GUIDANCE\|* ]] || [[ "$line" == ERROR\|* ]]; then
    continue
  fi
  if [[ "$line" == period_type\|* ]] || [[ "$line" == time_horizon\|* ]]; then
    log "BLOCK header line found: file=$FILE"
    echo "{\"decision\":\"block\",\"reason\":\"GX output must not include header\"}"
    exit 0
  fi
  fields=$(printf "%s" "$line" | awk -F'|' '{print NF}')
  if [ "$fields" -ne 18 ]; then
    log "BLOCK invalid field count: file=$FILE fields=$fields line=${line:0:120}"
    echo "{\"decision\":\"block\",\"reason\":\"GX output must have 18 fields per line\"}"
    exit 0
  fi
done <<< "$CONTENT"

log "ALLOW gx output: file=$FILE"
echo "{}"
exit 0
