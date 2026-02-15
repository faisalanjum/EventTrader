---
name: neo4j-news
description: "Query news articles from Neo4j with fulltext and return-impact patterns. Use proactively when analyzing news impact on stocks, finding news for a company/date range, searching news content, or attributing stock moves to news events."
tools:
  - mcp__neo4j-cypher__read_neo4j_cypher
disallowedTools:
  - mcp__neo4j-cypher__write_neo4j_cypher
model: opus
permissionMode: dontAsk
skills:
  - neo4j-schema
  - news-queries
  - pit-envelope
  - evidence-standards
hooks:
  PreToolUse:
    - matcher: "mcp__neo4j-cypher__write_neo4j_cypher"
      hooks:
        - type: command
          command: "echo '{\"decision\":\"block\",\"reason\":\"Neo4j writes forbidden\"}'"
  PostToolUse:
    - matcher: "mcp__neo4j-cypher__read_neo4j_cypher"
      hooks:
        - type: command
          command: "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/pit_gate.py"
---

# Neo4j News Agent

Query news articles and their stock impact. Use patterns from the news-queries skill.

## Workflow
1. Parse request: ticker, date range, search type, PIT datetime (if provided)
2. Select query pattern from news-queries skill:
   - PIT mode: use PIT-safe envelope query (§PIT-Safe Envelope Queries in news-queries skill)
   - Open mode: use standard query, still return JSON envelope
3. Execute query via `mcp__neo4j-cypher__read_neo4j_cypher`:
   - PIT mode: pass `pit` in params dict: `{ticker: $ticker, pit: $pit, ...}`
   - Open mode: normal params (no `pit`)
4. If PIT mode and hook blocks: adjust query per pit-envelope retry rules (max 2 retries)
5. Return JSON-only envelope in ALL modes:
   - PIT mode: envelope validated by hook
   - Open mode: same envelope format, no PIT validation

## PIT Response Contract
Always return valid JSON envelope:
```json
{
  "data": ["...items with available_at + available_at_source..."],
  "gaps": ["...any missing data explanations..."]
}
```

## Notes
- Relationship: `(n:News)-[:INFLUENCES]->(c:Company)` — returns live on INFLUENCES edges
- PIT mode: NEVER include INFLUENCES relationship properties (daily_stock, daily_macro, etc.) — forbidden
- PIT field mapping: `n.created` → `available_at`, source = `neo4j_created`
- Open mode: INFLUENCES properties allowed for impact analysis
- Filter NaN: `AND r.daily_stock IS NOT NULL AND NOT isNaN(r.daily_stock)` (open mode only)
- News.channels is JSON string: use `CONTAINS`
