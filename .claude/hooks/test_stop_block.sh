#!/bin/bash
# Hook script for SubagentStop blocking test
# Blocks first stop attempt, allows second (when stop_hook_active is true)
LOG_FILE="/home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-hook-stop-block.log"
STDIN_DATA=$(cat)
ACTIVE=$(echo "$STDIN_DATA" | jq -r '.stop_hook_active // false')

echo "---STOP_HOOK_FIRED---" >> "$LOG_FILE"
echo "TIMESTAMP: $(date -Iseconds)" >> "$LOG_FILE"
echo "STOP_HOOK_ACTIVE: $ACTIVE" >> "$LOG_FILE"
echo "---END---" >> "$LOG_FILE"

if [ "$ACTIVE" = "true" ]; then
  exit 0  # Allow stop on second attempt
fi

# Block first stop attempt
echo '{"decision":"block","reason":"STOP_BLOCKED: You must write the exact text STOP_WAS_BLOCKED to /home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-hook-stop-block.txt before you can stop."}'
