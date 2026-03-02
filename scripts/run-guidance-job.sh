#!/bin/bash
# run-guidance-job.sh — Push a guidance extraction job and follow logs
#
# Usage:
#   ./scripts/run-guidance-job.sh TICKER SOURCE_ID [MODE]
#
# Examples:
#   ./scripts/run-guidance-job.sh AAPL AAPL_2025-07-31T17.00.00-04.00           # write (default)
#   ./scripts/run-guidance-job.sh AAPL AAPL_2025-07-31T17.00.00-04.00 dry_run   # dry run
#
# Prerequisites:
#   - redis-cli available (apt install redis-tools)
#   - kubectl configured for the cluster

set -euo pipefail

TICKER="${1:?Usage: $0 TICKER SOURCE_ID [MODE]}"
SOURCE_ID="${2:?Usage: $0 TICKER SOURCE_ID [MODE]}"
MODE="${3:-write}"

REDIS_HOST="192.168.40.72"
REDIS_PORT="31379"
NAMESPACE="processing"
DEPLOYMENT="claude-code-worker"

PAYLOAD="{\"ticker\":\"${TICKER}\",\"source_id\":\"${SOURCE_ID}\",\"mode\":\"${MODE}\"}"

echo "[job] Pushing to earnings:trigger: ${PAYLOAD}"
redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" LPUSH earnings:trigger "$PAYLOAD"

echo "[job] Waiting for KEDA to scale up pod (polling every 10s)..."
while true; do
    POD_STATUS=$(kubectl get pods -n "$NAMESPACE" -l app="$DEPLOYMENT" --no-headers 2>/dev/null || true)
    if echo "$POD_STATUS" | grep -q Running; then
        echo "[job] Pod running: $POD_STATUS"
        break
    fi
    sleep 10
done

echo "[job] Following logs (Ctrl-C to stop)..."
kubectl logs -f deployment/"$DEPLOYMENT" -n "$NAMESPACE" --tail=100
