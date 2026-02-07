#!/bin/bash
# Hook script for TeammateIdle event test
# Logs all input to a test output file for verification
LOG_FILE="/home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-hook-teammate-idle.log"
STDIN_DATA=$(cat)
echo "---TEAMMATE_IDLE_EVENT---" >> "$LOG_FILE"
echo "TIMESTAMP: $(date -Iseconds)" >> "$LOG_FILE"
echo "STDIN: $STDIN_DATA" >> "$LOG_FILE"
echo "ENV_VARS:" >> "$LOG_FILE"
env | grep -i "CLAUDE\|TASK\|TEAM" >> "$LOG_FILE" 2>/dev/null
echo "---END---" >> "$LOG_FILE"
