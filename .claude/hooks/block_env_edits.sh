#!/bin/bash
# block_env_edits.sh
# Blocks Edit/Write operations targeting .env files to prevent accidental
# credential exposure or modification.

INPUT=$(cat 2>/dev/null) || INPUT=""
if [ -z "$INPUT" ]; then
  echo "{}"
  exit 0
fi

FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
if [ -z "$FILE" ]; then
  echo "{}"
  exit 0
fi

# Block any .env file (root or nested)
case "$FILE" in
  *.env|*.env.*|*/.env|*/.env.*)
    echo "{\"decision\":\"block\",\"reason\":\"BLOCKED: .env files must not be edited by Claude — contains secrets/credentials.\"}"
    exit 0
    ;;
esac

echo "{}"
exit 0
