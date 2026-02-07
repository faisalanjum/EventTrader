---
name: test-re-inherit-child
description: "Retest 2026-02-05: Child WITH MCP - tests own access"
allowed-tools:
  - mcp__neo4j-cypher__read_neo4j_cypher
context: fork
---
# Test: Child with MCP tool

WITHOUT using ToolSearch, try mcp__neo4j-cypher__read_neo4j_cypher:
- Query: RETURN 'child_mcp' AS source
- Reply with: "CHILD_MCP: WORKS" or "CHILD_MCP: NEEDS_TOOLSEARCH"
- Include query result
