#!/usr/bin/env bash
# Build & push Docker image for one component.
# Usage:  ./scripts/build_push.sh event-trader | xbrl-worker | report-enricher
set -e
cd "$(dirname "$0")/.."            # repo root

case "$1" in
  xbrl-worker)     DOCKERFILE=Dockerfile.xbrl     ; IMAGE=faisalanjum/xbrl-worker:latest ;;
  event-trader)    DOCKERFILE=Dockerfile.event    ; IMAGE=faisalanjum/event-trader:latest ;;
  report-enricher) DOCKERFILE=Dockerfile.enricher ; IMAGE=faisalanjum/report-enricher:latest ;;
  mcp-http-pinned)
    # Pinned-image build for mcp-neo4j-cypher HTTP runtime (Phase H).
    # Tag scheme: http-v0.2.1-mcp1.26.0-YYYY-MM-DD-<shortSHA>
    # Reuses the existing public repo faisalanjum/mcp-neo4j-cypher.
    # NEVER pushes :latest — that still points at the 9-month-old stdio image.
    DRY_RUN=false
    if [[ "${2:-}" == "--dry-run" ]]; then
      DRY_RUN=true
    elif [[ -n "${2:-}" ]]; then
      echo "Unknown option for mcp-http-pinned: $2"
      echo "Usage: $0 mcp-http-pinned [--dry-run]"
      exit 1
    fi

    TAG_VER="http-v0.2.1-mcp1.26.0"
    TAG_DATE=$(date +%Y-%m-%d)
    SRC_REPO=/home/faisal/neo4j-mcp-server
    BUILD_CTX="$SRC_REPO/servers/mcp-neo4j-cypher"
    TAG_SHA=$(git -C "$SRC_REPO" rev-parse --short HEAD)
    IMAGE="faisalanjum/mcp-neo4j-cypher:${TAG_VER}-${TAG_DATE}-${TAG_SHA}"

    if [[ "$DRY_RUN" == "true" ]]; then
      echo "DRY RUN: would copy k8s/mcp-services/run_http.py → $BUILD_CTX/run_http.py"
      echo "DRY RUN: would copy k8s/mcp-services/requirements.lock → $BUILD_CTX/requirements.lock"
      echo "DRY RUN: would docker build -f k8s/mcp-services/Dockerfile.neo4j-cypher-http -t $IMAGE $BUILD_CTX"
      echo "DRY RUN: would docker push $IMAGE"
      echo "DRY RUN: no files copied, no Docker commands run"
      exit 0
    fi

    # Both files live in EventMarketDB but Dockerfile's COPY sources are build-context-relative,
    # so we temp-copy them into the hostPath build context. trap cleans up on any exit.
    cp k8s/mcp-services/run_http.py        "$BUILD_CTX/run_http.py"
    cp k8s/mcp-services/requirements.lock  "$BUILD_CTX/requirements.lock"
    trap 'rm -f "$BUILD_CTX/run_http.py" "$BUILD_CTX/requirements.lock"' EXIT

    echo "▶︎ Building  $IMAGE …"
    docker build \
      -f k8s/mcp-services/Dockerfile.neo4j-cypher-http \
      -t "$IMAGE" \
      "$BUILD_CTX"

    echo "▶︎ Pushing   $IMAGE …"
    docker push "$IMAGE"
    echo "✔︎ Image pushed: $IMAGE"
    echo "To deploy: update k8s/mcp-services/mcp-neo4j-cypher-http-deployment.yaml image tag then kubectl apply -f ..."
    exit 0
    ;;
  *) echo "Usage: $0 {xbrl-worker|event-trader|report-enricher|mcp-http-pinned}"; exit 1;;
esac

echo "▶︎ Building  $IMAGE …"
docker build -f "$DOCKERFILE" -t "$IMAGE" .
echo "▶︎ Pushing   $IMAGE …"
docker push "$IMAGE"
echo "✔︎ Image pushed"
