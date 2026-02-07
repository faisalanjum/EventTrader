---
name: test-re-mcp-wildcard
description: "Retest 2026-02-05: Do MCP wildcards pre-load tools?"
allowed-tools:
  - mcp__neo4j-cypher__*
  - Write
context: fork
---
# Test: MCP wildcard pre-load

Your allowed-tools has mcp__neo4j-cypher__* (wildcard). Test:

WITHOUT using ToolSearch, try calling mcp__neo4j-cypher__read_neo4j_cypher directly:
- Query: RETURN 1 AS test
- If it works without ToolSearch: write "WILDCARD_PRELOAD: YES" to earnings-analysis/test-outputs/test-re-mcp-wildcard.txt
- If you need ToolSearch: write "WILDCARD_PRELOAD: NO"
