#!/bin/bash

# Script to process transcripts through Neo4jProcessor.py
# Usage: ./process_transcripts.sh [--batch N] [--max N] [--skip-without-returns]

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (one level up from script directory)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Set PYTHONPATH to include the project root
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Default to verbose mode
VERBOSE="--verbose"

# Parse custom options
OPTIONS=""
for arg in "$@"; do
    OPTIONS="$OPTIONS $arg"
done

echo "Starting transcript processing..."
echo "Full command: python $PROJECT_ROOT/neograph/Neo4jProcessor.py transcripts $OPTIONS $VERBOSE"

# Run the Neo4jProcessor script in transcripts mode with all arguments passed to this script
python "$PROJECT_ROOT/neograph/Neo4jProcessor.py" transcripts $OPTIONS $VERBOSE

echo "Transcript processing completed." 