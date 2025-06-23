#!/usr/bin/env bash
# One command: git pull → build+push → rollout
# Usage:  ./scripts/deploy.sh event-trader   | xbrl-worker
set -e
COMP="$1"
[[ "$COMP" == "event-trader" || "$COMP" == "xbrl-worker" ]] || {
  echo "Usage: $0 {event-trader|xbrl-worker}"; exit 1; }

cd "$(dirname "$0")/.."    # repo root
echo "▶︎ git pull"
git pull

./scripts/build_push.sh "$COMP"
./scripts/rollout.sh    "$COMP"
