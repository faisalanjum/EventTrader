#!/bin/bash
# validate_news_id_hook.sh - Ensures news_id contains URL(s) for external sources
# For websearch/perplexity: news_id must be URL(s), semicolon-separated if multiple

INPUT=$(cat)
STDOUT=$(echo "$INPUT" | jq -r '.tool_response.stdout // ""')

# Only validate 10-field pipe format
[ $(echo "$STDOUT" | tr -cd '|' | wc -c) -eq 9 ] || { echo "{}"; exit 0; }

NEWS_ID=$(echo "$STDOUT" | cut -d'|' -f2)
SOURCE=$(echo "$STDOUT" | cut -d'|' -f8)

# If source is websearch or perplexity, first item in news_id must be URL
if [ "$SOURCE" = "websearch" ] || [ "$SOURCE" = "perplexity" ]; then
    echo "$NEWS_ID" | cut -d';' -f1 | grep -qE '^https?://' || {
        echo "{\"decision\":\"block\",\"reason\":\"news_id must contain URL(s) when source=$SOURCE. Got: $NEWS_ID\"}"
        exit 0
    }
fi

echo "{}"
