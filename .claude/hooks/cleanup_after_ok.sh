#!/bin/bash
# cleanup_after_ok.sh
# Cleans per-task output directories after .ok marker is written.

INPUT=$(cat 2>/dev/null) || INPUT=""
if [ -z "$INPUT" ]; then
  echo "{}"
  exit 0
fi

FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

case "$FILE" in
  *"/earnings-analysis/Companies/"*/"manifests/"*.ok) ;;
  *) echo "{}"; exit 0 ;;
esac

BASE="${FILE%.ok}"
QUARTER=$(basename "$BASE")
MANIFEST_DIR=$(dirname "$BASE")
GX_DIR="${MANIFEST_DIR}/${QUARTER}/gx"
JUDGE_DIR="${MANIFEST_DIR}/${QUARTER}/judge"

LOG_DIR="/home/faisal/EventMarketDB/logs"
LOG_FILE="$LOG_DIR/cleanup-after-ok.log"
mkdir -p "$LOG_DIR"

timestamp=$(date '+%Y-%m-%d %H:%M:%S')

# Remove per-task outputs if they exist
if [ -d "$GX_DIR" ]; then
  rm -rf "$GX_DIR"
  echo "[$timestamp] removed gx_dir=$GX_DIR" >> "$LOG_FILE"
fi
if [ -d "$JUDGE_DIR" ]; then
  rm -rf "$JUDGE_DIR"
  echo "[$timestamp] removed judge_dir=$JUDGE_DIR" >> "$LOG_FILE"
fi

echo "{}"
exit 0
