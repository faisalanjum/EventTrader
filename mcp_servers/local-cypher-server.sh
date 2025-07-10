#!/bin/bash
# MCP server wrapper for Claude CLI - Neo4j Cypher

# Set required environment variables (same as Kubernetes pods)
export NEO4J_URI="bolt://localhost:30687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="Next2020#"
export NEO4J_DATABASE="neo4j"
export PYTHONPATH="/home/faisal/neo4j-mcp-server/servers/mcp-neo4j-cypher/src:$PYTHONPATH"

# Activate the virtual environment
source /home/faisal/EventMarketDB/venv/bin/activate

# Run the MCP server using the entry point
cd /home/faisal/neo4j-mcp-server/servers/mcp-neo4j-cypher/src
exec python -c "from mcp_neo4j_cypher import main; main()"