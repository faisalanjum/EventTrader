#!/usr/bin/env bash
# check_broken_search.sh — tripwire for Obsidian's broken built-in search.
#
# Obsidian v1.12.4 (headless) returns EMPTY for words that exist (verified 2026-06-17) via
#   `obsidian search`, `obsidian search:context`, `obsidian search:open`, `obsidian search total`.
# Any executable code that relies on those silently gets zero results. Use the reliable helper
#   scripts/obsidian/vault_search.py   (ripgrep on disk) instead.
#
# This script flags such calls in executable code (.sh/.py/.bash). It scans CODE only — docs and
# plans (*.md) are intentionally ignored. Run it manually or wire it into CI.
#
# Exit 0 = clean (no offending calls).   Exit 1 = offending calls found.   Exit 2 = setup error.
set -uo pipefail

REPO="${1:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || echo /home/faisal/EventMarketDB)}"
command -v rg >/dev/null 2>&1 || { echo "check_broken_search: error: ripgrep (rg) not found" >&2; exit 2; }
[ -d "$REPO" ] || { echo "check_broken_search: error: repo not found: $REPO" >&2; exit 2; }

# Match `obsidian search`, `obsidian search:context|:open`, `obsidian search ... total`,
# and `obsidian search query=`. Exclude this helper folder, vendored, git, and worktrees.
mapfile -t hits < <(rg -n --no-heading \
  -g '*.sh' -g '*.py' -g '*.bash' \
  -g '!scripts/obsidian/**' -g '!**/.git/**' -g '!**/node_modules/**' -g '!**/worktrees/**' \
  -e 'obsidian[[:space:]]+search(:[a-z]+)?([[:space:]]+(total|query=))?' \
  "$REPO" 2>/dev/null)

if (( ${#hits[@]} )); then
  echo "FAIL: ${#hits[@]} call(s) to Obsidian's broken built-in search found."
  echo "      Replace each with: python3 scripts/obsidian/vault_search.py \"<query>\""
  printf '  %s\n' "${hits[@]}"
  exit 1
fi

echo "OK: no executable code calls Obsidian's broken built-in search."
echo "    Reliable helper: scripts/obsidian/vault_search.py"
exit 0
