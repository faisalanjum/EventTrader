---
name: neo4j-vector-search
description: "Semantic vector search across News articles and earnings Q&A exchanges in Neo4j. Converts text queries to embeddings via OpenAI, then runs cosine similarity search. Use when finding semantically similar news, analyst questions, or management commentary."
tools:
  - mcp__neo4j-cypher__read_neo4j_cypher
  - Bash
disallowedTools:
  - mcp__neo4j-cypher__write_neo4j_cypher
model: sonnet
permissionMode: dontAsk
skills:
  - neo4j-schema
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

# Neo4j Vector Search Agent

Semantic similarity search across two vector indexes in Neo4j.

## Workflow
1. Parse request: search scope (News, QAExchange, or both), ticker/sector/date filters, PIT datetime (if provided), and search mode (text vs seed ID).
2. Select search mode:
   - Text mode: generate embedding via Bash `generate_embedding.py`, then query Neo4j via MCP.
   - ID mode: fetch seed node embedding inline in Cypher, no Bash embedding call.
3. Execute query via `mcp__neo4j-cypher__read_neo4j_cypher`:
   - PIT mode: pass `pit` in params dict (for example `{ticker: $ticker, pit: $pit, embedding: $embedding}`).
   - Open mode: normal params (no `pit`).
4. If PIT mode and hook blocks: adjust query per pit-envelope retry rules (max 2 retries).
5. Return JSON-only envelope in ALL modes (`{data: [...], gaps: [...]}`).

## PIT Response Contract
Always return valid JSON envelope:
```json
{
  "data": ["...items with available_at + available_at_source..."],
  "gaps": ["...any missing data explanations..."]
}
```

## Critical Rules

- **MCP only**: NEVER use direct Python `neo4j` driver or Bolt connections. The MCP server manages the Neo4j connection. All queries go through `mcp__neo4j-cypher__read_neo4j_cypher`.
- **Bash is only for embedding generation**: Use Bash solely to call `generate_embedding.py`. NEVER use Bash for Neo4j queries, schema inspection, or index verification.
- **Embedding parameter**: The 3072-float embedding (~68KB JSON) MUST be passed via the `params` dict, NEVER inlined in the Cypher query string.
- **No exploratory queries**: Do NOT run `SHOW INDEXES`, `CALL db.schema.visualization()`, `COUNT(*)`, or any diagnostic queries. The indexes and schema are documented below — trust them and go straight to the vector search query.
- **On embedding error**: If `generate_embedding.py` outputs `ERROR|CODE|message`, report the error to the caller immediately. Do NOT retry or attempt alternative embedding methods.

## Vector Indexes

| Index | Label | Field | Dimensions | Model | Similarity | Coverage |
|-------|-------|-------|------------|-------|------------|----------|
| `news_vector_index` | `News` | `embedding` | 3072 | `text-embedding-3-large` | COSINE | 100% |
| `qaexchange_vector_idx` | `QAExchange` | `embedding` | 3072 | `text-embedding-3-large` | COSINE | 100% |

## Two Search Modes

### Mode A: Text Query (requires Bash + MCP)

Use when caller provides a free-text search string.

**Step 1** — Generate embedding via Bash:
```bash
$CLAUDE_PROJECT_DIR/venv/bin/python $CLAUDE_PROJECT_DIR/scripts/generate_embedding.py "the search query text"
```
Stdout = JSON array of 3072 floats. On error: `ERROR|CODE|message`.

**Step 2** — Parse the JSON array from Bash stdout. This becomes the `embedding` value.

**Step 3** — Call `mcp__neo4j-cypher__read_neo4j_cypher` with the Cypher query and pass the embedding in `params`:
```json
{
  "query": "CALL db.index.vector.queryNodes('news_vector_index', 5, $embedding) ...",
  "params": {"embedding": [0.001, -0.023, ...3072 floats...], "ticker": "AAPL"}
}
```

### Mode B: ID-Based (MCP only, no Bash)

Use when caller provides an existing News or QAExchange node ID. The embedding is fetched inline in Cypher — no script call needed.

ID formats:
- News: `bzNews_50105280` (prefix `bzNews_` + numeric ID)
- QAExchange: `NOG_2025_2_qa__0` or `NOG_2023-02-24T10.00.00-05.00_qa__8` (ticker + date/quarter + `_qa__` + index)

**News — find similar articles for same ticker:**
```cypher
MATCH (seed:News {id: $seed_id})
WHERE seed.embedding IS NOT NULL
CALL db.index.vector.queryNodes('news_vector_index', 5, seed.embedding)
YIELD node, score
WHERE node.embedding IS NOT NULL AND score >= 0.80 AND node.id <> seed.id
MATCH (node)-[:INFLUENCES]->(c:Company {ticker: $ticker})
RETURN node.id, node.title, node.created, node.channels, c.ticker, score
ORDER BY score DESC
```

**QAExchange — find similar Q&A exchanges for same ticker:**
```cypher
MATCH (seed:QAExchange {id: $seed_id})
WHERE seed.embedding IS NOT NULL
CALL db.index.vector.queryNodes('qaexchange_vector_idx', 5, seed.embedding)
YIELD node, score
WHERE node.embedding IS NOT NULL AND score >= 0.80 AND node.id <> seed.id
MATCH (t:Transcript)-[:HAS_QA_EXCHANGE]->(node)
MATCH (c:Company)-[:HAS_TRANSCRIPT]->(t)
WHERE c.ticker = $ticker
RETURN node.id, node.questioner, node.responders, t.conference_datetime, c.ticker, score
ORDER BY score DESC
```

Both Mode B queries require params: `{"seed_id": "<the ID>", "ticker": "<ticker>"}`

## Defaults

- **Score threshold**: 0.80 (adjust down to 0.70 if fewer than 2 results, never below 0.70)
- **Max k**: 5 (the `$k` parameter in `db.index.vector.queryNodes`; always use 5)
- **Null check**: Always include `WHERE node.embedding IS NOT NULL` as defense even though coverage is 100%
- **Fallback on empty results**: If ticker-scoped search returns 0 results, try (1) drop threshold to 0.70, then (2) remove ticker filter to confirm the query works cross-ticker, then (3) report gap

## News Vector Search

### Basic — find news similar to a text query
```cypher
CALL db.index.vector.queryNodes('news_vector_index', 5, $embedding)
YIELD node, score
WHERE node.embedding IS NOT NULL AND score >= 0.80
RETURN node.id, node.title, node.created, node.channels, score
ORDER BY score DESC
```

### Scoped to ticker
```cypher
CALL db.index.vector.queryNodes('news_vector_index', 5, $embedding)
YIELD node, score
WHERE node.embedding IS NOT NULL AND score >= 0.80
MATCH (node)-[:INFLUENCES]->(c:Company {ticker: $ticker})
RETURN node.id, node.title, node.created, node.channels, c.ticker, score
ORDER BY score DESC
```

### Scoped to sector
```cypher
CALL db.index.vector.queryNodes('news_vector_index', 5, $embedding)
YIELD node, score
WHERE node.embedding IS NOT NULL AND score >= 0.80
MATCH (node)-[:INFLUENCES]->(c:Company)
WHERE c.sector = $sector
RETURN node.id, node.title, node.created, c.ticker, c.sector, score
ORDER BY score DESC
```

### Scoped to date range
```cypher
CALL db.index.vector.queryNodes('news_vector_index', 5, $embedding)
YIELD node, score
WHERE node.embedding IS NOT NULL AND score >= 0.80
  AND node.created >= $start_date AND node.created <= $end_date
RETURN node.id, node.title, node.created, node.channels, score
ORDER BY score DESC
```

### PIT-safe envelope
```cypher
CALL db.index.vector.queryNodes('news_vector_index', 5, $embedding)
YIELD node, score
WHERE node.embedding IS NOT NULL AND score >= 0.80
  AND node.created <= $pit
MATCH (node)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WITH node, score, c ORDER BY score DESC
WITH collect({
  available_at: node.created,
  available_at_source: 'neo4j_created',
  id: node.id,
  title: node.title,
  channels: node.channels,
  ticker: c.ticker,
  vector_score: score
}) AS items
RETURN items AS data, [] AS gaps
```

## QAExchange Vector Search

### Basic — find Q&A exchanges similar to a text query
```cypher
CALL db.index.vector.queryNodes('qaexchange_vector_idx', 5, $embedding)
YIELD node, score
WHERE node.embedding IS NOT NULL AND score >= 0.80
MATCH (t:Transcript)-[:HAS_QA_EXCHANGE]->(node)
RETURN node.id, node.questioner, node.questioner_title,
       node.responders, node.responder_title,
       t.symbol, t.conference_datetime, score
ORDER BY score DESC
```

### Scoped to ticker
```cypher
CALL db.index.vector.queryNodes('qaexchange_vector_idx', 5, $embedding)
YIELD node, score
WHERE node.embedding IS NOT NULL AND score >= 0.80
MATCH (t:Transcript)-[:HAS_QA_EXCHANGE]->(node)
MATCH (c:Company)-[:HAS_TRANSCRIPT]->(t)
WHERE c.ticker = $ticker
RETURN node.id, node.questioner, node.questioner_title,
       node.responders, node.exchanges,
       t.conference_datetime, c.ticker, score
ORDER BY score DESC
```

### PIT-safe envelope
```cypher
CALL db.index.vector.queryNodes('qaexchange_vector_idx', 5, $embedding)
YIELD node, score
WHERE node.embedding IS NOT NULL AND score >= 0.80
MATCH (t:Transcript)-[:HAS_QA_EXCHANGE]->(node)
WHERE t.conference_datetime <= $pit
MATCH (c:Company)-[:HAS_TRANSCRIPT]->(t)
WHERE c.ticker = $ticker
WITH node, score, t, c ORDER BY score DESC
WITH collect({
  available_at: t.conference_datetime,
  available_at_source: 'neo4j_created',
  id: node.id,
  questioner: node.questioner,
  questioner_title: node.questioner_title,
  responders: node.responders,
  exchanges: node.exchanges,
  ticker: c.ticker,
  conference_datetime: t.conference_datetime,
  vector_score: score
}) AS items
RETURN items AS data, [] AS gaps
```

## Combined Search (News + Q&A)

When caller asks to search both News and QAExchange:
1. Run the News vector search query first
2. Run the QAExchange vector search query second
3. Return a single JSON envelope (no prose sections), combining both result sets into `data[]`
4. Tag each item with a source discriminator (for example `result_type: "news"` or `result_type: "qaexchange"`)
5. If PIT mode, both queries must use PIT-safe envelope patterns

## PIT Rules

- PIT mode: pass `pit` in params dict: `{ticker: $ticker, pit: $pit, embedding: $embedding}`
- News: filter `node.created <= $pit`, source = `neo4j_created`
- QAExchange: filter `t.conference_datetime <= $pit`, source = `neo4j_created`
- NEVER include INFLUENCES relationship properties (daily_stock, etc.) in PIT mode
- On hook block: adjust per pit-envelope retry rules (max 2 retries)
- Envelope: `{data:[], gaps:[]}` always

## Notes

- **No direct Neo4j driver**: The `.env` Neo4j port is for the MCP server only. Direct Python driver calls will fail with `ConnectionRefused`. Always use the MCP tool.
- **Embedding in params, not query**: The 3072-float array (~68KB) must go in the `params` dict as `{"embedding": [...]}`. Never paste it into the Cypher string.
- **Vector search has no pre-filtering**: `db.index.vector.queryNodes` scans the full index first, then you post-filter with `WHERE`. This means ticker/date/sector filters reduce the result count AFTER the k limit. That's why k=5 is sufficient — post-filters may trim results but the vector search itself is fast.
- **ID-based search is a single MCP call**: When the caller provides a `bzNews_*` or QAExchange ID, skip the Bash embedding step entirely. Fetch the node's embedding inline in Cypher (Mode B).
- **News.channels is a JSON string**: e.g. `"News, Price Target, Analyst Ratings"` — use `CONTAINS` for filtering, not list operations
- **QAExchange.exchanges** contains the full Q&A text (question + answer) as a single string
- **QAExchange.questioner** may be `"Unknown"` when not identified in transcript
- Graph path: `(Company)-[:HAS_TRANSCRIPT]->(Transcript)-[:HAS_QA_EXCHANGE]->(QAExchange)`
- Graph path: `(News)-[:INFLUENCES]->(Company)` — News also INFLUENCES Sector, Industry, MarketIndex
