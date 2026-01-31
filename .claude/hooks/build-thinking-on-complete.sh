#!/bin/bash
# PostToolUse hook for Bash commands in earnings-orchestrator
# Only triggers thinking extraction when orchestrator outputs ORCHESTRATOR_COMPLETE marker

# Always exit 0 and output {} - never fail
trap 'echo "{}"; exit 0' ERR

# Read hook input from stdin (may be empty)
INPUT=$(cat 2>/dev/null) || INPUT=""

# Exit early if no input
if [ -z "$INPUT" ]; then
    echo '{}'
    exit 0
fi

# Get the command that was just executed (handle jq errors gracefully)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null) || COMMAND=""

# Only proceed if this is the ORCHESTRATOR_COMPLETE marker
if [[ "$COMMAND" != *"ORCHESTRATOR_COMPLETE"* ]]; then
    echo '{}'
    exit 0
fi

# Extract TICKER using sed instead of grep -P (more portable)
TICKER=$(echo "$COMMAND" | sed -n 's/.*ORCHESTRATOR_COMPLETE[[:space:]]*\([A-Z]\{1,5\}\).*/\1/p' 2>/dev/null) || TICKER=""

if [ -z "$TICKER" ]; then
    echo '{}'
    exit 0
fi

# Create log directory if needed
LOG_DIR="/home/faisal/EventMarketDB/logs"
mkdir -p "$LOG_DIR" 2>/dev/null
LOG_FILE="$LOG_DIR/thinking-hook.log"

# Log the trigger
echo "[$(date '+%Y-%m-%d %H:%M:%S')] HOOK TRIGGERED: Building thinking for $TICKER" >> "$LOG_FILE" 2>/dev/null

# Run thinking extraction in background (don't block the response)
(
    cd /home/faisal/EventMarketDB
    source venv/bin/activate 2>/dev/null

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running build-news-thinking.py --ticker $TICKER" >> "$LOG_FILE" 2>/dev/null
    python scripts/earnings/build-news-thinking.py --ticker "$TICKER" >> "$LOG_FILE" 2>&1

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running build-guidance-thinking.py --ticker $TICKER" >> "$LOG_FILE" 2>/dev/null
    python scripts/earnings/build-guidance-thinking.py --ticker "$TICKER" >> "$LOG_FILE" 2>&1

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] COMPLETE: Thinking files built for $TICKER" >> "$LOG_FILE" 2>/dev/null
) &

# Return success (don't block Claude's response)
echo '{}'
exit 0
