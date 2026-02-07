---
name: test-agent-field-2026
description: Test if agent field grants agent tools/permissions
agent: neo4j-news
context: fork
---
You have agent: neo4j-news set in frontmatter. The neo4j-news agent has mcp__neo4j-cypher__read_neo4j_cypher.

Test: WITHOUT using ToolSearch/MCPSearch, try calling mcp__neo4j-cypher__read_neo4j_cypher directly with: "RETURN 1 AS test"

Report:
- "AGENT_FIELD: WORKS" if MCP tool was available without ToolSearch
- "AGENT_FIELD: NOT_WORKING" if you needed ToolSearch or couldn't access it

Write result to: earnings-analysis/test-outputs/agent-field-2026.txt
