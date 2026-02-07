---
name: test-re-3layer-mid
description: "Retest 2026-02-05: 3-layer nesting L2"
allowed-tools:
  - Skill
  - mcp__neo4j-cypher__read_neo4j_cypher
context: fork
---
# Layer 2 (Mid)

1. SECRET = "beta"
2. Call /test-re-3layer-bot
3. Reply with: "L2_SECRET:beta | L3_RETURNED:[what bot returned]"
