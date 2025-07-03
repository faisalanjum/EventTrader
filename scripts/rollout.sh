#!/usr/bin/env bash
# Restart the deployments so the cluster pulls the new image.
# Usage:  ./scripts/rollout.sh event-trader   | xbrl-worker
set -e
if [[ $1 == "xbrl-worker" ]]; then
  kubectl rollout restart deployment/xbrl-worker-heavy   -n default
  kubectl rollout restart deployment/xbrl-worker-medium  -n default
  kubectl rollout restart deployment/xbrl-worker-light   -n default
elif [[ $1 == "event-trader" ]]; then
  kubectl rollout restart deployment/event-trader -n default
else
  echo "Usage: $0 {xbrl-worker|event-trader}"; exit 1
fi
echo "✔︎ Rollout triggered"
