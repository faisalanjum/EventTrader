---
name: test-re-inherit-parent2
description: "Retest 2026-02-05: Parent WITH MCP - does child inherit it?"
allowed-tools:
  - mcp__neo4j-cypher__read_neo4j_cypher
  - Skill
  - Write
context: fork
---
# Test: Tool inheritance (parent HAS MCP, child does NOT)

1. Call /test-re-inherit-child2
2. Write to earnings-analysis/test-outputs/test-re-inherit-parent2.txt:
   - What child returned
   - "INHERIT_UP: YES" if child could use MCP without ToolSearch (inherited from parent)
   - "INHERIT_UP: NO" if child needed ToolSearch or couldn't access MCP
