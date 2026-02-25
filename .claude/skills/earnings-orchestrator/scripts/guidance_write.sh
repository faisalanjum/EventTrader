#!/bin/bash
# Shell wrapper for guidance_write_cli.py — sets up venv + Neo4j connection
# Called by guidance-extract agent via: Bash("guidance_write.sh /tmp/items.json --write")

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
exec python3 "$SCRIPT_DIR/guidance_write_cli.py" "$@"
