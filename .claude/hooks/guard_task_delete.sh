#!/bin/bash
# guard_task_delete.sh
# Blocks TaskUpdate status=deleted for GX-* tasks until the validation marker exists.

INPUT=$(cat 2>/dev/null) || INPUT=""
if [ -z "$INPUT" ]; then
  echo "{}"
  exit 0
fi

STATUS=$(echo "$INPUT" | jq -r '.tool_input.status // empty')
TASK_ID=$(echo "$INPUT" | jq -r '.tool_input.taskId // empty')

# Only guard deletions
if [ "$STATUS" != "deleted" ] || [ -z "$TASK_ID" ]; then
  echo "{}"
  exit 0
fi

# Find the task file in any task list directory
TASK_FILE=""
for d in /home/faisal/.claude/tasks/*; do
  [ -d "$d" ] || continue
  if [ -f "$d/${TASK_ID}.json" ]; then
    TASK_FILE="$d/${TASK_ID}.json"
    break
  fi
done

# If task file not found, allow deletion (nothing to protect)
if [ -z "$TASK_FILE" ]; then
  echo "{}"
  exit 0
fi

SUBJECT=$(jq -r '.subject // empty' "$TASK_FILE")

# Only guard GX-* tasks
if [[ "$SUBJECT" =~ ^GX-([A-Za-z0-9_]+)[[:space:]]+([A-Za-z0-9._-]+)[[:space:]] ]]; then
  QUARTER="${BASH_REMATCH[1]}"
  TICKER="${BASH_REMATCH[2]}"
  MARKER="/home/faisal/EventMarketDB/earnings-analysis/Companies/${TICKER}/manifests/${QUARTER}.ok"
  if [ ! -f "$MARKER" ]; then
    echo "{\"decision\":\"block\",\"reason\":\"Cannot delete GX task before validation marker exists: ${MARKER}\"}"
    exit 0
  fi
fi

echo "{}"
exit 0
