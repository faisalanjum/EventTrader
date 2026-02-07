---
name: test-re-inherit-child2
description: "Retest 2026-02-05: Child WITHOUT MCP - tests if parent's MCP inherited"
allowed-tools: []
context: fork
---
# Test: Child without MCP (parent has it)

WITHOUT using ToolSearch, try mcp__neo4j-cypher__read_neo4j_cypher:
- Query: RETURN 'inherited' AS source
- Reply with: "CHILD2_MCP: INHERITED" if it worked without ToolSearch
- Reply with: "CHILD2_MCP: NOT_INHERITED" if tool not available
