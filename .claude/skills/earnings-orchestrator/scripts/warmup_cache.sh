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

# Neo4j connection — MUST match MCP server (mcp_servers/local-cypher-server.sh)
# Force-set to known-good values. Shell env may have stale/wrong URI.
# Override with GUIDANCE_NEO4J_URI etc. if you need a different target.
export NEO4J_URI="${GUIDANCE_NEO4J_URI:-bolt://localhost:30687}"
export NEO4J_USERNAME="${GUIDANCE_NEO4J_USERNAME:-neo4j}"
export NEO4J_PASSWORD="${GUIDANCE_NEO4J_PASSWORD:-Next2020#}"
export NEO4J_DATABASE="${GUIDANCE_NEO4J_DATABASE:-neo4j}"

# Activate venv
source "$REPO_ROOT/venv/bin/activate"

# Run CLI
exec python3 "$SCRIPT_DIR/warmup_cache.py" "$@"
