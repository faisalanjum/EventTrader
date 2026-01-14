#!/bin/bash
# validate.sh - Dispatcher for source-specific validators
# Routes to validate_neo4j.sh or validate_perplexity.sh based on --source
#
# Usage:
#   echo "$RESPONSE" | ./validate.sh --source neo4j-report --pit "2025-07-31T16:30:25-04:00"
#   echo "$RESPONSE" | ./validate.sh --source perplexity-search --pit "2025-07-31T16:30:25-04:00"
#   echo "$RESPONSE" | ./validate.sh --pit "2025-07-31T16:30:25-04:00"  # fallback to generic

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse arguments
SOURCE=""
PIT=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --source) SOURCE="$2"; shift 2 ;;
        --pit) PIT="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Read response from stdin into temp file (so we can pass to sub-validator)
RESPONSE=$(cat)

# Build args for sub-validator
ARGS=""
if [ -n "$PIT" ]; then
    ARGS="--pit $PIT"
fi

# Route to appropriate validator based on source
if [[ "$SOURCE" == neo4j-* ]]; then
    # Neo4j sources: use jq-based JSON validator
    echo "$RESPONSE" | "$SCRIPT_DIR/validate_neo4j.sh" $ARGS
elif [[ "$SOURCE" == perplexity-* ]]; then
    # Perplexity sources: use text-based validator
    echo "$RESPONSE" | "$SCRIPT_DIR/validate_perplexity.sh" $ARGS
else
    # Unknown or no source: use Neo4j validator as default (more strict)
    echo "$RESPONSE" | "$SCRIPT_DIR/validate_neo4j.sh" $ARGS
fi
