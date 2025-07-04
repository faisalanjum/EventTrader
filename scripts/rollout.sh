#!/usr/bin/env bash
# Restart the deployments so the cluster pulls the new image.
# Usage:  ./scripts/rollout.sh event-trader | xbrl-worker | report-enricher
set -e
if [[ $1 == "xbrl-worker" ]]; then
  # Check if KEDA configurations need to be applied
  if ! kubectl get scaledobject xbrl-worker-heavy-scaler -n processing &>/dev/null; then
    echo "▶︎ Applying KEDA configurations for xbrl-worker..."
    # Delete old HPAs if they exist
    kubectl delete hpa xbrl-worker-heavy-hpa xbrl-worker-medium-hpa xbrl-worker-light-hpa -n processing 2>/dev/null || true
    kubectl apply -f k8s/xbrl-worker-deployments.yaml
    kubectl apply -f k8s/xbrl-worker-scaledobjects.yaml
    sleep 5
  fi
  kubectl rollout restart deployment/xbrl-worker-heavy   -n processing
  kubectl rollout restart deployment/xbrl-worker-medium  -n processing
  kubectl rollout restart deployment/xbrl-worker-light   -n processing
elif [[ $1 == "event-trader" ]]; then
  kubectl rollout restart deployment/event-trader -n processing
elif [[ $1 == "report-enricher" ]]; then
  kubectl rollout restart deployment/report-enricher -n processing
else
  echo "Usage: $0 {xbrl-worker|event-trader|report-enricher}"; exit 1
fi
echo "✔︎ Rollout triggered"
