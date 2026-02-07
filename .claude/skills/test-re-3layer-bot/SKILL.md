---
name: test-re-3layer-bot
description: "Retest 2026-02-05: 3-layer nesting L3"
allowed-tools:
  - mcp__neo4j-cypher__read_neo4j_cypher
context: fork
---
# Layer 3 (Bottom)

Run this query: MATCH (c:Company) RETURN c.ticker LIMIT 2
Reply with: "L3_RESULT:[tickers]"
