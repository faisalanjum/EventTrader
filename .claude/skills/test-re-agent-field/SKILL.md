---
name: test-re-agent-field
description: "Retest 2026-02-05: Does agent: field grant agent's tools?"
agent: neo4j-news
context: fork
---
# Test: agent: field

You have agent: neo4j-news set. The neo4j-news agent has mcp__neo4j-cypher__read_neo4j_cypher.

WITHOUT using ToolSearch, try calling mcp__neo4j-cypher__read_neo4j_cypher directly:
- Query: RETURN 1 AS test
- If it works: write "AGENT_FIELD: WORKS" to earnings-analysis/test-outputs/test-re-agent-field.txt
- If you need ToolSearch: write "AGENT_FIELD: NOT_WORKING"
- Include query result
