#!/bin/bash
# Extract thinking blocks from Claude Code transcripts
#
# Usage:
#   ./extract-thinking.sh                     # List sessions with thinking
#   ./extract-thinking.sh 0415feb7            # Extract & save to earnings-analysis/thinking/
#   ./extract-thinking.sh --stdout 0415feb7   # Print to terminal only
#
# Output saved to: earnings-analysis/thinking/{session-id}.txt

CLAUDE_DIR="$HOME/.claude/projects/-home-faisal-EventMarketDB"
OUTPUT_DIR="/home/faisal/EventMarketDB/earnings-analysis/thinking"

# Create output directory if needed
mkdir -p "$OUTPUT_DIR"

# If no args, list sessions
if [ -z "$1" ]; then
    echo "Sessions with thinking blocks:"
    echo "=============================="
    grep -l '"type":"thinking"' "$CLAUDE_DIR"/*.jsonl 2>/dev/null | while read f; do
        count=$(grep -c '"type":"thinking"' "$f")
        name=$(basename "$f" .jsonl)
        modified=$(stat -c %y "$f" | cut -d' ' -f1)
        echo "  ${name:0:20}...  ($count blocks, $modified)"
    done | head -30
    echo ""
    echo "Usage: $0 <session-id-prefix>        # Save to $OUTPUT_DIR/"
    echo "       $0 --stdout <session-id>      # Print to terminal"
    exit 0
fi

# Check for --stdout flag
STDOUT_ONLY=false
if [ "$1" == "--stdout" ]; then
    STDOUT_ONLY=true
    shift
fi

# Find file by prefix or use direct path
if [ -f "$1" ]; then
    FILE="$1"
else
    FILE=$(ls "$CLAUDE_DIR"/$1*.jsonl 2>/dev/null | head -1)
fi

if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
    echo "No transcript found matching: $1"
    exit 1
fi

SESSION_ID=$(basename "$FILE" .jsonl)

if [ "$STDOUT_ONLY" == "true" ]; then
    echo "Extracting thinking from: $SESSION_ID"
    echo "============================================"
    python3 /home/faisal/EventMarketDB/scripts/extract-thinking.py "$FILE"
else
    OUTPUT_FILE="$OUTPUT_DIR/${SESSION_ID}.txt"
    echo "Extracting thinking from: $SESSION_ID"
    echo "Saving to: $OUTPUT_FILE"
    echo ""
    python3 /home/faisal/EventMarketDB/scripts/extract-thinking.py "$FILE" > "$OUTPUT_FILE"

    # Show summary
    BLOCK_COUNT=$(grep -c "^--- Thinking Block" "$OUTPUT_FILE" || echo 0)
    echo "✓ Saved $BLOCK_COUNT thinking blocks to:"
    echo "  $OUTPUT_FILE"
fi
