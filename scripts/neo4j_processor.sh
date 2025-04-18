#!/bin/bash
# Helper script to run Neo4jProcessor.py with simplified command line arguments
# Usage: ./neo4j_processor.sh [options]

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (one level up from script directory)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Print the command being run
echo "Running: python $PROJECT_ROOT/neograph/Neo4jProcessor.py $@"

# Run the Neo4jProcessor script with all arguments passed to this script
python "$PROJECT_ROOT/neograph/Neo4jProcessor.py" "$@" --verbose 