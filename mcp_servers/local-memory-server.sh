#!/bin/bash
# MCP server wrapper for Claude CLI - Neo4j Memory

# Set required environment variables (same as Kubernetes pods)
export NEO4J_URI="bolt://localhost:30687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="Next2020#"
export NEO4J_DATABASE="neo4j"

# Run the MCP server directly from current directory
cd /home/user/EventTrader/mcp_servers
exec python3 neo4j_memory_server.py