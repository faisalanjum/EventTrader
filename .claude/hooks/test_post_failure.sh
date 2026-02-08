#!/bin/bash
# Hook script for PostToolUseFailure event test
# Logs all input to a test output file for verification
LOG_FILE="/home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-hook-post-failure.log"
STDIN_DATA=$(cat)
echo "---POST_TOOL_USE_FAILURE_EVENT---" >> "$LOG_FILE"
echo "TIMESTAMP: $(date -Iseconds)" >> "$LOG_FILE"
echo "STDIN: $STDIN_DATA" >> "$LOG_FILE"
echo "---END---" >> "$LOG_FILE"
