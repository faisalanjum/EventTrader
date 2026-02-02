#!/bin/bash
# validate_ok_marker.sh
# Blocks creation of .ok marker unless all expected guidance output files exist.

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
MANIFEST="${BASE}.json"
RETRY="${BASE}.retry.json"
QUARTER=$(basename "$BASE")
GX_DIR="$(dirname "$BASE")/${QUARTER}/gx"
JUDGE_DIR="$(dirname "$BASE")/${QUARTER}/judge"

if [ ! -f "$MANIFEST" ]; then
  echo "{\"decision\":\"block\",\"reason\":\"Manifest not found: ${MANIFEST}\"}"
  exit 0
fi

if [ -f "$RETRY" ]; then
  echo "{\"decision\":\"block\",\"reason\":\"Retry file exists: ${RETRY}\"}"
  exit 0
fi

# Verify guidance + judge output files exist for every manifest ID
python3 - <<'PY' "$MANIFEST" "$GX_DIR" "$JUDGE_DIR"
import json, os, sys
manifest_path, gx_dir, judge_dir = sys.argv[1:4]
with open(manifest_path, "r") as f:
    m = json.load(f)

g_ids = []
for t in m.get("guidance", {}).get("tasks", []):
    tid = t.get("id")
    if tid is not None:
        g_ids.append(str(tid))

missing = []
for tid in g_ids:
    path = os.path.join(gx_dir, f"{tid}.tsv")
    if not os.path.isfile(path):
        missing.append(f"gx:{tid}")

n_ids = []
for t in m.get("news", {}).get("judge_tasks", []):
    tid = t.get("id")
    if tid is not None:
        n_ids.append(str(tid))

for tid in n_ids:
    path = os.path.join(judge_dir, f"{tid}.tsv")
    if not os.path.isfile(path):
        missing.append(f"judge:{tid}")

if missing:
    print(f"MISSING {len(missing)}")
    sys.exit(2)
print("OK")
PY

if [ $? -ne 0 ]; then
  echo "{\"decision\":\"block\",\"reason\":\"Missing one or more output files in ${GX_DIR} or ${JUDGE_DIR}\"}"
  exit 0
fi

echo "{}"
exit 0
