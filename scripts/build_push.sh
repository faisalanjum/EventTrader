#!/usr/bin/env bash
# Build & push Docker image for one component.
# Usage:  ./scripts/build_push.sh event-trader   | xbrl-worker
set -e
cd "$(dirname "$0")/.."            # repo root

case "$1" in
  xbrl-worker)   DOCKERFILE=Dockerfile.xbrl   ; IMAGE=faisalanjum/xbrl-worker:latest ;;
  event-trader)  DOCKERFILE=Dockerfile.event  ; IMAGE=faisalanjum/event-trader:latest ;;
  *) echo "Usage: $0 {xbrl-worker|event-trader}"; exit 1;;
esac

echo "▶︎ Building  $IMAGE …"
docker build -f "$DOCKERFILE" -t "$IMAGE" .
echo "▶︎ Pushing   $IMAGE …"
docker push "$IMAGE"
echo "✔︎ Image pushed"
