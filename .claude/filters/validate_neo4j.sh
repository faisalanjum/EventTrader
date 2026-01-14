#!/bin/bash
# validate_neo4j.sh - Validates Neo4j JSON responses
# Uses jq for 100% reliable JSON parsing
#
# Usage: echo "$RESPONSE" | ./validate_neo4j.sh --pit "2025-07-31T16:30:25-04:00"

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

# Extract JSON from response (handles text wrapped around JSON)
# Looks for [...] or {...} patterns
JSON_CONTENT=$(echo "$RESPONSE" | grep -oE '\[.*\]|\{.*\}' | head -1 || echo "")

# ============================================================
# Check 1: Forbidden field names in JSON keys
# ============================================================
FORBIDDEN=$(jq -r '.forbidden_patterns | .[]' "$CONFIG_FILE")

if [ -n "$JSON_CONTENT" ]; then
    # Use jq to find any forbidden field names in the JSON
    for PATTERN in $FORBIDDEN; do
        # Check if pattern exists as a key anywhere in JSON
        FOUND=$(echo "$JSON_CONTENT" | jq -r ".. | objects | keys[]? | select(test(\"$PATTERN\"; \"i\"))" 2>/dev/null | head -1 || echo "")
        if [ -n "$FOUND" ]; then
            echo "CONTAMINATED:$FOUND"
            exit 1
        fi
        # Also check if pattern appears in string values (e.g., field names in result)
        FOUND_VAL=$(echo "$JSON_CONTENT" | jq -r ".. | strings | select(test(\"$PATTERN\"; \"i\"))" 2>/dev/null | head -1 || echo "")
        if [ -n "$FOUND_VAL" ]; then
            echo "CONTAMINATED:$PATTERN"
            exit 1
        fi
    done
else
    # Fallback: regex check if no valid JSON found
    PATTERNS=$(jq -r '.forbidden_patterns | join("|")' "$CONFIG_FILE")
    MATCHES=$(echo "$RESPONSE" | grep -oiE "$PATTERNS" 2>/dev/null | head -1 || true)
    if [ -n "$MATCHES" ]; then
        echo "CONTAMINATED:$MATCHES"
        exit 1
    fi
fi

# ============================================================
# Check 2: PIT compliance on date fields
# ============================================================
# Only check EVENT/AVAILABILITY timestamps, NOT period coverage dates
# - created: when data became available (Report, News, Transcript)
# - conference_datetime: when earnings call occurred (Transcript)
# - declaration_date: when dividend announced (Dividend)
# - execution_date: when split executed (Split)
# - date: calendar date (Date node)
#
# NOT checked (these are period coverage, not event times):
# - periodOfReport: fiscal period the report covers
# - start_date, end_date: XBRL period coverage

if [ -n "$PIT" ]; then
    PIT_EPOCH=$(date -d "$PIT" +%s 2>/dev/null || echo "")

    if [ -n "$PIT_EPOCH" ] && [ -n "$JSON_CONTENT" ]; then
        # Event/availability timestamp fields ONLY
        for FIELD in created conference_datetime declaration_date execution_date date; do
            # Handle both array and object JSON, extract field values
            DATES=$(echo "$JSON_CONTENT" | jq -r "
                (if type == \"array\" then .[] else . end) |
                .$FIELD // empty
            " 2>/dev/null | sort -u || echo "")

            for DATE in $DATES; do
                # Skip if not a date-like string
                if ! echo "$DATE" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}'; then
                    continue
                fi

                DATE_EPOCH=$(date -d "$DATE" +%s 2>/dev/null || echo "")
                if [ -n "$DATE_EPOCH" ] && [ "$DATE_EPOCH" -gt "$PIT_EPOCH" ]; then
                    echo "CONTAMINATED:PIT_VIOLATION:$DATE"
                    exit 1
                fi
            done
        done
    fi
fi

echo "CLEAN"
exit 0
