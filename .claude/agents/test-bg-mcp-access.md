---
name: test-bg-mcp-access
description: "Test: Can background: true agents access MCP tools (neo4j, perplexity)?"
background: true
model: haiku
---
You are testing MCP tool access in a `background: true` agent.

The official docs say "MCP tools are not available in background subagents" but previous tests showed they DO work. Let's verify.

1. Try ToolSearch for "neo4j" — report if it returns results
2. If ToolSearch works, try calling `mcp__neo4j-cypher__read_neo4j_cypher` with:
   ```cypher
   MATCH (c:Company {ticker: 'AAPL'}) RETURN c.name LIMIT 1
   ```
3. Try ToolSearch for "perplexity" — report if it returns results
4. If ToolSearch works, try calling a perplexity tool with a simple query

5. Write ALL results to `earnings-analysis/test-outputs/test-bg-mcp-access.txt`:
```
BG_MCP_TEST=v2.1.50
BACKGROUND_FIELD=true
TOOLSEARCH_AVAILABLE=YES|NO
TOOLSEARCH_neo4j=FOUND|NOT_FOUND|ERROR - [details]
MCP_neo4j_call=WORKS|BLOCKED|ERROR - [details]
MCP_neo4j_result=[result or error]
TOOLSEARCH_perplexity=FOUND|NOT_FOUND|ERROR - [details]
MCP_perplexity_call=WORKS|BLOCKED|ERROR - [details]
MCP_perplexity_result=[result or error]
BG_MCP_ACCESS=WORKS|BLOCKED|PARTIAL - [summary]
```
