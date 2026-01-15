#!/bin/bash
# Build Obsidian-compatible thinking index from Claude Code transcripts
#
# Usage:
#   ./build-thinking-index.sh                  # Build all from history
#   ./build-thinking-index.sh <accession>      # Build for single accession
#   ./build-thinking-index.sh index            # Rebuild index only
#
# Output: ~/Obsidian/EventTrader/Earnings/earnings-analysis/thinking/
#   - index.md          Master index with clickable links
#   - runs/*.md         Combined thinking per accession

SCRIPT_DIR="$(dirname "$0")"

python3 "$SCRIPT_DIR/build-thinking-index.py" "${@:-all}"
