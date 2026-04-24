#!/bin/bash
# Shell wrapper for warmup_cache.py — pre-fetches extraction caches via direct Bolt
# Called by extraction agents via:
#   Bash("bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh TICKER")
#   Bash("bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh TICKER --transcript TID")
#   Bash("bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh TICKER --8k-packet ACC [--out-path PATH]")
#   Bash("bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh TICKER --guidance-history [--pit ISO8601] [--out-path PATH]")

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

# Neo4j connection default: kube-proxy routes ClusterIP 10.102.222.120:7687
# to the in-cluster neo4j-bolt Service (NodePort 30687 was the old flaky path).
# Override with GUIDANCE_NEO4J_URI if you need a different target (pods set
# it to bolt://neo4j-bolt.neo4j.svc.cluster.local:7687).
export NEO4J_URI="${GUIDANCE_NEO4J_URI:-bolt://10.102.222.120:7687}"
export NEO4J_USERNAME="${GUIDANCE_NEO4J_USERNAME:-neo4j}"
export NEO4J_PASSWORD="${GUIDANCE_NEO4J_PASSWORD:-${NEO4J_PASSWORD:-}}"
export NEO4J_DATABASE="${GUIDANCE_NEO4J_DATABASE:-neo4j}"

# Activate venv
source "$REPO_ROOT/venv/bin/activate"

# Run CLI
exec python3 "$SCRIPT_DIR/warmup_cache.py" "$@"
