#!/bin/bash
# block_bash_guard.sh
# Blocks Bash writes to guarded artifacts; require Write/Edit tool instead.

INPUT=$(cat 2>/dev/null) || INPUT=""
if [ -z "$INPUT" ]; then
  echo "{}"
  exit 0
fi

CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
if [ -z "$CMD" ]; then
  echo "{}"
  exit 0
fi

# If Bash command writes to .ok or processed CSVs, block.
case "$CMD" in
  *"manifests/"*.ok*|*"news_processed.csv"*|*"guidance_processed.csv"*)
    echo "{\"decision\":\"block\",\"reason\":\"Use Write/Edit tool for .ok and processed CSV updates (Bash write blocked).\"}"
    exit 0
    ;;
esac

echo "{}"
exit 0
