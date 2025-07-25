#!/usr/bin/env bash
# Build & push Docker image for one component.
# Usage:  ./scripts/build_push.sh event-trader | xbrl-worker | report-enricher
set -e
cd "$(dirname "$0")/.."            # repo root

case "$1" in
  xbrl-worker)     DOCKERFILE=Dockerfile.xbrl     ; IMAGE=faisalanjum/xbrl-worker:latest ;;
  event-trader)    DOCKERFILE=Dockerfile.event    ; IMAGE=faisalanjum/event-trader:latest ;;
  report-enricher) DOCKERFILE=Dockerfile.enricher ; IMAGE=faisalanjum/report-enricher:latest ;;
  mcp-http) 
    # MCP HTTP doesn't need image build - uses python:3.11-slim directly
    echo "▶︎ MCP HTTP uses python:3.11-slim base image (no build needed)"
    exit 0
    ;;
  *) echo "Usage: $0 {xbrl-worker|event-trader|report-enricher|mcp-http}"; exit 1;;
esac

echo "▶︎ Building  $IMAGE …"
docker build -f "$DOCKERFILE" -t "$IMAGE" .
echo "▶︎ Pushing   $IMAGE …"
docker push "$IMAGE"
echo "✔︎ Image pushed"
