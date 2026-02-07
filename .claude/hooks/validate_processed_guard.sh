#!/bin/bash
# validate_processed_guard.sh
# Blocks updates to processed CSVs unless validation marker exists

INPUT=$(cat 2>/dev/null) || INPUT=""
if [ -z "$INPUT" ]; then
  echo "{}"
  exit 0
fi

FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
PAYLOAD=$(echo "$INPUT" | jq -r '.tool_input.new_string // .tool_input.content // empty')

# Only guard processed CSVs
case "$FILE" in
  *"/earnings-analysis/news_processed.csv") TARGET="news" ;;
  *"/earnings-analysis/guidance_processed.csv") TARGET="guidance" ;;
  *"/earnings-analysis/prediction_processed.csv") TARGET="prediction" ;;
  *) echo "{}"; exit 0 ;;
esac

# Extract last non-header row from payload
ROW=$(echo "$PAYLOAD" | tr '\r' '\n' | awk -F'|' 'NF>=4 && $1!="ticker" {line=$0} END{print line}')
TICKER=$(echo "$ROW" | cut -d'|' -f1)
QUARTER=$(echo "$ROW" | cut -d'|' -f2)
RAW_FY=$(echo "$ROW" | cut -d'|' -f3)
FY=$(echo "$RAW_FY" | sed 's/^FY//')
ACCESSION=$(echo "$ROW" | cut -d'|' -f5)

if [ -z "$TICKER" ] || [ -z "$QUARTER" ] || [ -z "$FY" ]; then
  echo "{\"decision\":\"block\",\"reason\":\"Missing ticker/quarter in processed update\"}"
  exit 0
fi

# Enforce fiscal_year format FY#### to avoid cache mismatches
if ! echo "$RAW_FY" | grep -qE '^FY[0-9]{4}$'; then
  echo "{\"decision\":\"block\",\"reason\":\"fiscal_year must be FY#### (got: ${RAW_FY})\"}"
  exit 0
fi

MARKER="/home/faisal/EventMarketDB/earnings-analysis/Companies/${TICKER}/manifests/${QUARTER}_FY${FY}.ok"
OUT_DIR="/home/faisal/EventMarketDB/earnings-analysis/Companies/${TICKER}"
if [ "$TARGET" = "prediction" ]; then
  OUT_FILE="/home/faisal/EventMarketDB/earnings-analysis/predictions.csv"
  PRED_REPORT="${OUT_DIR}/pre_${ACCESSION}.md"
else
  OUT_FILE="${OUT_DIR}/${TARGET}.csv"
fi

if [ ! -f "$MARKER" ]; then
  echo "{\"decision\":\"block\",\"reason\":\"Validation marker not found: ${MARKER}\"}"
  exit 0
fi

# Require output CSV to exist before allowing processed update
if [ ! -f "$OUT_FILE" ]; then
  echo "{\"decision\":\"block\",\"reason\":\"Output CSV not found: ${OUT_FILE}\"}"
  exit 0
fi

if [ "$TARGET" = "prediction" ] && [ ! -f "$PRED_REPORT" ]; then
  echo "{\"decision\":\"block\",\"reason\":\"Prediction report not found: ${PRED_REPORT}\"}"
  exit 0
fi

echo "{}"
exit 0
# Prediction requires accession to verify report file
if [ "$TARGET" = "prediction" ] && [ -z "$ACCESSION" ]; then
  echo "{\"decision\":\"block\",\"reason\":\"Missing accession in prediction_processed update\"}"
  exit 0
fi
