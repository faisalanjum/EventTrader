#!/bin/bash
# Hook script for SubagentStart context injection test
# Logs the event and injects additionalContext into the subagent
LOG_FILE="/home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-hook-subagent-start.log"
STDIN_DATA=$(cat)
echo "---SUBAGENT_START_EVENT---" >> "$LOG_FILE"
echo "TIMESTAMP: $(date -Iseconds)" >> "$LOG_FILE"
echo "STDIN: $STDIN_DATA" >> "$LOG_FILE"
echo "---END---" >> "$LOG_FILE"

# Return additionalContext to inject into the subagent's context
echo '{"hookSpecificOutput":{"hookEventName":"SubagentStart","additionalContext":"INJECTED_MAGIC_STRING_7842: This context was injected by the SubagentStart hook. If you can see this, the hook additionalContext injection works."}}'
