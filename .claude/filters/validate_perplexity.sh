#!/bin/bash
# validate_perplexity.sh - Validates Perplexity text responses
# Parses structured output format for article publication dates
#
# Perplexity output format:
#   Found N search results:
#   1. **Title**
#      URL: ...
#      Content...
#      Date: YYYY-MM-DD
#
# Usage: echo "$RESPONSE" | ./validate_perplexity.sh --pit "2025-07-31T16:30:25-04:00"

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/rules.json"

# Parse arguments
PIT=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --pit) PIT="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Read response from stdin
RESPONSE=$(cat)

# Check if validation is enabled
ENABLED=$(jq -r '.enabled // true' "$CONFIG_FILE")
if [ "$ENABLED" != "true" ]; then
    echo "CLEAN:validation_disabled"
    exit 0
fi

# ============================================================
# Check 1: PIT compliance on article publication dates
# ============================================================
# Perplexity article dates appear as "Date: YYYY-MM-DD" at end of each result
# This is the ONLY date we check - not dates mentioned in article content

if [ -n "$PIT" ]; then
    PIT_EPOCH=$(date -d "$PIT" +%s 2>/dev/null || echo "")

    if [ -n "$PIT_EPOCH" ]; then
        # Extract publication dates in two formats:
        # 1. Text format: "Date: YYYY-MM-DD"
        # 2. JSON format: "date": "YYYY-MM-DD"
        PUB_DATES_TEXT=$(echo "$RESPONSE" | grep -oE 'Date: [0-9]{4}-[0-9]{2}-[0-9]{2}' | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' || echo "")
        PUB_DATES_JSON=$(echo "$RESPONSE" | grep -oE '"date": "[0-9]{4}-[0-9]{2}-[0-9]{2}"' | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' || echo "")
        PUB_DATES=$(echo -e "$PUB_DATES_TEXT\n$PUB_DATES_JSON" | sort -u | grep -v '^$' || echo "")

        for DATE in $PUB_DATES; do
            DATE_EPOCH=$(date -d "$DATE" +%s 2>/dev/null || echo "")
            if [ -n "$DATE_EPOCH" ] && [ "$DATE_EPOCH" -gt "$PIT_EPOCH" ]; then
                echo "CONTAMINATED:PIT_VIOLATION:$DATE"
                exit 1
            fi
        done
    fi
fi

# ============================================================
# Note: No forbidden pattern check for Perplexity
# ============================================================
# Perplexity returns web articles, not Neo4j data.
# It won't have fields like "daily_stock" or "hourly_stock".
# Natural language mentions of stock movement are allowed
# (e.g., "analysts expect stock to rise") - these are opinions, not data.
# Only post-PIT publication dates are blocked.

echo "CLEAN"
exit 0
