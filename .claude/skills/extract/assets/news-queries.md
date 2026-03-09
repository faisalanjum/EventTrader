# News Queries (S6)

Source content queries for News nodes.

---

## 6. Source Content: News

### 6A. News Payload by ID

```cypher
MATCH (n:News {id: $news_id})
RETURN
  n.id,
  n.title,
  n.body,
  n.teaser,
  n.created,
  n.updated,
  n.url,
  n.authors,
  n.channels,
  n.tags,
  n.market_session,
  n.returns_schedule
```
**Empty check**: If `title`, `body`, and `teaser` are all null/empty, return `EMPTY_CONTENT|news|full`.
**Note**: `authors`, `channels`, `tags`, and `returns_schedule` are JSON strings in Neo4j.

### 6B. All News for Company (Date Range Required)

Dates are required. News result sets are too large for unbounded company queries.

```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.created >= $start_date
  AND n.created <= $end_date
RETURN
  n.id,
  n.title,
  n.teaser,
  n.created,
  n.updated,
  n.channels,
  n.market_session,
  n.url
ORDER BY n.created DESC
```

### 6C. Channel-Filtered Company News (Caller-Supplied Channels)

Use only when the extraction type defines a channel strategy. Dates are required.

```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.created >= $start_date
  AND n.created <= $end_date
  AND ANY(channel IN $channels WHERE n.channels CONTAINS ('"' + channel + '"'))
RETURN
  n.id,
  n.title,
  n.created,
  n.updated,
  n.channels,
  n.market_session
ORDER BY n.created DESC
```

### 6D. News Influence Context by ID

```cypher
MATCH (n:News {id: $news_id})
OPTIONAL MATCH (n)-[:INFLUENCES]->(c:Company)
OPTIONAL MATCH (n)-[:INFLUENCES]->(s:Sector)
OPTIONAL MATCH (n)-[:INFLUENCES]->(i:Industry)
OPTIONAL MATCH (n)-[:INFLUENCES]->(m:MarketIndex)
RETURN
  n.id,
  collect(DISTINCT c.ticker) AS company_tickers,
  collect(DISTINCT c.name) AS company_names,
  collect(DISTINCT s.name) AS sectors,
  collect(DISTINCT i.name) AS industries,
  collect(DISTINCT m.id) AS market_indexes
```

### 6E. Company News by Market Session

Useful when an extraction type cares about pre-market, in-market, post-market, or closed-session timing.

```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.created >= $start_date
  AND n.created <= $end_date
  AND n.market_session = $market_session
RETURN
  n.id,
  n.title,
  n.created,
  n.updated,
  n.market_session,
  n.channels
ORDER BY n.created DESC
```
