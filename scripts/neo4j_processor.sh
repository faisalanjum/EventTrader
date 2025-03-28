#!/bin/bash

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (one level up from script directory)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Set PYTHONPATH to include the project root
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Run the Neo4jProcessor script with all arguments passed to this script
# Add the --verbose flag to enable detailed logging
python "$PROJECT_ROOT/utils/Neo4jProcessor.py" "$@" --verbose 