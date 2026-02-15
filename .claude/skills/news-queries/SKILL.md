---
name: news-queries
description: Cypher query patterns for News nodes. Reference doc auto-loaded by neo4j-news agent.
user-invocable: false
---

# Neo4j News Queries

## Reference

- **Field inventory** (channels, tags, market sessions, sectors, industries): see `.claude/references/neo4j-news-fields.md`
- **Schema** (node types, relationship properties, data types, indexes): loaded via `neo4j-schema` skill

## 1. Core Access Patterns

### News for company in date range
```cypher
MATCH (n:News)-[r:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.created >= $start_date AND n.created <= $end_date
RETURN n.id, n.title, n.teaser, n.created, n.channels
ORDER BY n.created DESC
```

### News by channel filter
```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.channels CONTAINS $channel
RETURN n.title, n.created, n.channels
ORDER BY n.created DESC
```

### Latest news for company
```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
RETURN n.title, n.teaser, n.created, n.channels
ORDER BY n.created DESC
LIMIT 10
```

### Fulltext search (keyword)
```cypher
CALL db.index.fulltext.queryNodes('news_ft', $query)
YIELD node, score
RETURN node.title, node.created, score
ORDER BY score DESC
LIMIT 20
```

### Fulltext search for company
```cypher
CALL db.index.fulltext.queryNodes('news_ft', $query)
YIELD node, score
MATCH (node)-[:INFLUENCES]->(c:Company {ticker: $ticker})
RETURN node.title, node.created, score
ORDER BY score DESC
LIMIT 20
```

### Fulltext search with body preview
```cypher
CALL db.index.fulltext.queryNodes('news_ft', $query)
YIELD node, score
RETURN node.title, node.teaser, substring(node.body, 0, 500) AS body_preview, score
ORDER BY score DESC
LIMIT 10
```

## 2. Return & Impact Patterns

### News with stock returns (INFLUENCES → Company)
```cypher
MATCH (n:News)-[r:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.created >= $start_date AND n.created <= $end_date
  AND r.daily_stock IS NOT NULL
RETURN n.title, n.created,
       r.daily_stock, r.daily_industry, r.daily_sector, r.daily_macro
ORDER BY n.created
```

### News around filing (with return filter)
```cypher
MATCH (n:News)-[r:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.created >= $start_date AND n.created <= $end_date
  AND r.daily_stock IS NOT NULL AND NOT isNaN(r.daily_stock)
RETURN n.title, n.channels, n.created, r.daily_stock, r.daily_macro
ORDER BY n.created
```

### News with highest impact (excess return)
```cypher
MATCH (n:News)-[r:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.created >= $start_date AND n.created <= $end_date
  AND r.daily_stock IS NOT NULL AND NOT isNaN(r.daily_stock)
RETURN n.title, n.created, r.daily_stock, r.daily_macro,
       abs(r.daily_stock - r.daily_macro) AS impact
ORDER BY impact DESC
LIMIT 10
```

### Aggregate news impact
```cypher
MATCH (n:News)-[r:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.created >= $start_date AND n.created <= $end_date
  AND r.daily_stock IS NOT NULL AND NOT isNaN(r.daily_stock)
RETURN count(n) AS news_count,
       avg(r.daily_stock) AS avg_stock_return,
       avg(r.daily_stock - r.daily_macro) AS avg_excess_return
```

### News by market session
```cypher
MATCH (n:News)-[rel:INFLUENCES]->(c:Company)
WHERE n.market_session = $session
  AND ABS(rel.session_stock) > 2.0
RETURN n.title, c.ticker, n.created,
       rel.session_stock as session_impact,
       rel.daily_stock as full_day_impact
ORDER BY ABS(rel.session_stock) DESC
LIMIT 20
```

### Hourly vs daily return divergence
```cypher
MATCH (n:News)-[r:INFLUENCES]->(c:Company)
WHERE r.hourly_stock IS NOT NULL AND r.daily_stock IS NOT NULL
  AND ((r.hourly_stock > 0 AND r.daily_stock < 0) OR (r.hourly_stock < 0 AND r.daily_stock > 0))
RETURN c.ticker, n.title, r.hourly_stock, r.daily_stock, n.created
ORDER BY abs(r.hourly_stock - r.daily_stock) DESC
LIMIT 20
```

### Complete return path (all levels)
```cypher
MATCH (n:News)-[r:INFLUENCES]->(c:Company)
WHERE r.daily_stock IS NOT NULL AND r.daily_industry IS NOT NULL
  AND r.daily_sector IS NOT NULL AND r.daily_macro IS NOT NULL
  AND ABS(toFloat(r.daily_stock)) > 3.0
RETURN n.title, c.ticker,
       r.daily_stock as stock_return, r.daily_industry as industry_return,
       r.daily_sector as sector_return, r.daily_macro as market_return
ORDER BY ABS(toFloat(r.daily_stock)) DESC LIMIT 20
```

### Companies outperforming market
```cypher
MATCH (n:News)-[r:INFLUENCES]->(c:Company)
WHERE r.daily_stock IS NOT NULL AND r.daily_macro IS NOT NULL
  AND r.daily_stock > r.daily_macro + 5.0
RETURN c.ticker, n.title, r.daily_stock, r.daily_macro,
       r.daily_stock - r.daily_macro AS excess_return
ORDER BY excess_return DESC
LIMIT 20
```

### Multi-level return coverage check
```cypher
MATCH ()-[r:INFLUENCES]->()
WITH count(*) AS total,
     count(r.daily_stock) AS has_daily_stock,
     count(r.hourly_stock) AS has_hourly_stock,
     count(r.daily_industry) AS has_daily_industry,
     count(r.daily_sector) AS has_daily_sector,
     count(r.daily_macro) AS has_daily_macro
RETURN total,
       round(100.0 * has_daily_stock / total) AS daily_stock_pct,
       round(100.0 * has_hourly_stock / total) AS hourly_stock_pct,
       round(100.0 * has_daily_industry / total) AS daily_industry_pct,
       round(100.0 * has_daily_sector / total) AS daily_sector_pct,
       round(100.0 * has_daily_macro / total) AS daily_macro_pct
```

## 3. INFLUENCES Target Patterns

These query INFLUENCES edges to non-Company targets. See `neo4j-schema` for which return fields exist on each target type.

### Industry-Wide News Events
```cypher
MATCH (n:News)-[rel:INFLUENCES]->(i:Industry)
WHERE ABS(rel.daily_industry) > 2.0
RETURN n.title, i.name as industry,
       rel.daily_industry as industry_impact,
       n.created
ORDER BY ABS(rel.daily_industry) DESC
LIMIT 20
```

### Sector-Wide News Events
```cypher
MATCH (n:News)-[rel:INFLUENCES]->(s:Sector)
WHERE ABS(rel.daily_sector) > 1.0
RETURN n.title, s.name as sector,
       rel.daily_sector as sector_impact,
       n.created
ORDER BY ABS(rel.daily_sector) DESC
LIMIT 20
```

### News impact on SPY market index
```cypher
MATCH (n:News)-[r:INFLUENCES]->(m:MarketIndex)
WHERE m.ticker = 'SPY' AND r.daily_macro IS NOT NULL AND ABS(toFloat(r.daily_macro)) > 1.0
RETURN n.title, r.daily_macro, n.created
ORDER BY ABS(toFloat(r.daily_macro)) DESC LIMIT 20
```

### SPY daily returns from news
```cypher
MATCH (n:News)-[r:INFLUENCES]->(m:MarketIndex)
WHERE m.ticker = 'SPY' AND r.daily_macro IS NOT NULL
RETURN n.title, r.daily_macro, n.created
ORDER BY ABS(toFloat(r.daily_macro)) DESC LIMIT 20
```

## 4. Cross-Domain Patterns

> **Cross-domain date anchor only.** These patterns join to Transcript or Report nodes solely as date anchors for finding News. Do NOT query Transcript/Report content — use `neo4j-transcript` or `neo4j-report` agents for that.

### News around earnings calls (Transcript date anchor)
```cypher
MATCH (c:Company {ticker: $ticker})-[:HAS_TRANSCRIPT]->(t:Transcript)
WITH c, t, datetime(t.conference_datetime) as call_date
ORDER BY call_date DESC
LIMIT 1
MATCH (n:News)-[:INFLUENCES]->(c)
WHERE datetime(n.created) > call_date - duration('P2D')
  AND datetime(n.created) < call_date + duration('P2D')
RETURN n.title, n.created,
       CASE
         WHEN datetime(n.created) < call_date THEN 'Before Call'
         ELSE 'After Call'
       END as timing
ORDER BY n.created
LIMIT 20
```

### Same-day report and news (Report date anchor)
```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)
WITH c, r, date(datetime(r.created)) as report_date
MATCH (n:News)-[rel:INFLUENCES]->(c)
WHERE date(datetime(n.created)) = report_date AND rel.daily_stock IS NOT NULL
RETURN c.ticker, r.formType, n.title, rel.daily_stock
ORDER BY ABS(toFloat(rel.daily_stock)) DESC LIMIT 20
```

## 5. Analytical Examples

Derived from core patterns — the agent can compose similar queries by adjusting filters, thresholds, and aggregations.

### News with maximum daily_stock values
```cypher
MATCH (n:News)-[r:INFLUENCES]->(c:Company)
WHERE r.daily_stock IS NOT NULL AND r.daily_stock <> 'NaN'
WITH n, c, toFloat(r.daily_stock) as daily_return
WHERE NOT isNaN(daily_return)
RETURN n.title, c.ticker, daily_return ORDER BY daily_return DESC LIMIT 10
```

### News causing extreme market movements (>10%)
```cypher
MATCH (n:News)-[r:INFLUENCES]->(c:Company)
WHERE r.daily_stock IS NOT NULL AND ABS(toFloat(r.daily_stock)) > 10.0
RETURN n.title, c.ticker, r.daily_stock, r.daily_industry, r.daily_sector, r.daily_macro,
       r.hourly_stock, r.session_stock, n.created
ORDER BY ABS(toFloat(r.daily_stock)) DESC LIMIT 20
```

### News causing extreme positive movements (>8%)
```cypher
MATCH (n:News)-[r:INFLUENCES]->(c:Company)
WHERE r.daily_stock IS NOT NULL AND r.daily_stock <> 'NaN' AND toFloat(r.daily_stock) > 8.0
RETURN n.title, c.ticker, r.daily_stock, n.created
ORDER BY toFloat(r.daily_stock) DESC LIMIT 20
```

### Count news with daily_stock > 10%
```cypher
MATCH (n:News)-[r:INFLUENCES]->(c:Company)
WHERE r.daily_stock IS NOT NULL AND r.daily_stock <> 'NaN' AND toFloat(r.daily_stock) > 10.0
RETURN COUNT(n) AS news_count
```

### News driving stocks below market (-3%)
```cypher
MATCH (n:News)-[r:INFLUENCES]->(c:Company)
WHERE r.daily_stock < r.daily_macro - 3.0
RETURN n.title, c.ticker, r.daily_stock, r.daily_macro
ORDER BY r.daily_stock LIMIT 20
```

### Opposite hourly vs daily returns (with NaN handling)
```cypher
MATCH (n:News)-[r:INFLUENCES]->(c:Company)
WHERE r.hourly_stock IS NOT NULL AND r.hourly_stock <> 'NaN'
  AND r.daily_stock IS NOT NULL AND r.daily_stock <> 'NaN'
WITH n, c, r, toFloat(r.hourly_stock) as hourly_return, toFloat(r.daily_stock) as daily_return
WHERE NOT isNaN(hourly_return) AND NOT isNaN(daily_return)
  AND ((hourly_return > 0 AND daily_return < 0) OR (hourly_return < 0 AND daily_return > 0))
RETURN n.title, c.ticker, hourly_return, daily_return, n.created
ORDER BY abs(hourly_return - daily_return) DESC LIMIT 20
```

### Hourly sector returns for tech vs healthcare
```cypher
MATCH (n:News)-[r:INFLUENCES]->(c:Company)
WHERE r.hourly_sector IS NOT NULL AND r.hourly_sector <> 'NaN'
  AND datetime(n.created) > datetime() - duration('P30D')
  AND (c.sector = 'Technology' OR c.sector = 'Healthcare')
WITH n, c, r, toFloat(r.hourly_sector) as hourly_sector_return
WHERE NOT isNaN(hourly_sector_return)
RETURN c.sector, n.title, c.ticker, hourly_sector_return, n.created,
       CASE WHEN hourly_sector_return > 0 THEN 'Positive'
            WHEN hourly_sector_return < 0 THEN 'Negative' ELSE 'Neutral' END as return_direction
ORDER BY c.sector, hourly_sector_return DESC LIMIT 50
```

### Companies with news outperforming macro in last 30 days
```cypher
MATCH (n:News)-[rel:INFLUENCES]->(c:Company)
WHERE datetime(n.created) > datetime() - duration('P30D')
  AND rel.daily_stock IS NOT NULL AND rel.daily_stock <> 'NaN'
  AND rel.daily_stock > rel.daily_macro AND rel.daily_macro > 0
RETURN DISTINCT c.ticker, n.title, rel.daily_stock, rel.daily_macro
ORDER BY rel.daily_stock DESC LIMIT 20
```

### Recent news with populated data (last 7 days)
```cypher
MATCH (n:News)-[r:INFLUENCES]->(c:Company)
WHERE datetime(n.created) > datetime() - duration('P7D')
  AND n.title IS NOT NULL AND n.title <> ''
  AND c.ticker IS NOT NULL AND c.ticker <> ''
  AND r.daily_stock IS NOT NULL AND r.daily_stock <> 'NaN'
WITH n, c, toFloat(r.daily_stock) as daily_return
WHERE NOT isNaN(daily_return)
RETURN n.title, c.ticker, daily_return
ORDER BY datetime(n.created) DESC LIMIT 20
```

### News events from past week with market impact
```cypher
MATCH (n:News)-[r:INFLUENCES]->(c:Company)
WHERE datetime(n.created) > datetime() - duration('P7D') AND r.daily_stock IS NOT NULL
RETURN n.title, c.ticker, r.daily_stock, n.created
ORDER BY ABS(toFloat(r.daily_stock)) DESC LIMIT 30
```

### Industries with divergent company vs industry returns
```cypher
MATCH (n:News)-[r:INFLUENCES]->(c:Company)
WHERE r.hourly_industry IS NOT NULL AND r.hourly_industry <> 'NaN'
  AND r.hourly_stock IS NOT NULL AND r.hourly_stock <> 'NaN'
  AND datetime(n.created) > datetime() - duration('P7D')
WITH n, c, r, toFloat(r.hourly_industry) as industry_return, toFloat(r.hourly_stock) as stock_return
WHERE NOT isNaN(industry_return) AND NOT isNaN(stock_return)
  AND industry_return < 0 AND stock_return > 0
RETURN DISTINCT c.industry LIMIT 100
```

### Count all INFLUENCES relationships
```cypher
MATCH ()-[r:INFLUENCES]->() RETURN count(r)
```

### Count news with embeddings
```cypher
MATCH (n:News) WHERE n.embedding IS NOT NULL RETURN COUNT(n) as embedded_news
```

### News embedding coverage
```cypher
MATCH (n:News) WHERE n.embedding IS NOT NULL
WITH COUNT(n) as embedded_count
MATCH (n2:News)
WITH embedded_count, COUNT(n2) as total_count
RETURN embedded_count, total_count, ROUND(100.0 * embedded_count / total_count) as coverage_pct
```

### Find relationships with null returns
```cypher
MATCH ()-[r:INFLUENCES]->()
WHERE r.daily_stock IS NULL OR r.hourly_stock IS NULL
RETURN COUNT(*) as null_count
```

## 6. PIT-Safe Envelope Queries

Queries for PIT (Point-in-Time) mode. All use `<= $pit` (boundary-inclusive) and return the standard envelope format. Pass `pit` in the `params` dict alongside other Cypher parameters.

### News in Date Range (PIT)
```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.created >= $start_date AND n.created <= $pit
WITH n ORDER BY n.created DESC
WITH collect({
  available_at: n.created,
  available_at_source: 'neo4j_created',
  id: n.id,
  title: n.title,
  teaser: n.teaser,
  channels: n.channels,
  created: n.created
}) AS items
RETURN items AS data, [] AS gaps
```

### News by Channel (PIT)
```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.created >= $start_date AND n.created <= $pit
  AND n.channels CONTAINS $channel
WITH n ORDER BY n.created DESC
WITH collect({
  available_at: n.created,
  available_at_source: 'neo4j_created',
  id: n.id,
  title: n.title,
  channels: n.channels,
  created: n.created
}) AS items
RETURN items AS data, [] AS gaps
```

### Fulltext Search (PIT)
```cypher
CALL db.index.fulltext.queryNodes('news_ft', $query)
YIELD node, score
MATCH (node)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE node.created <= $pit
WITH node, score ORDER BY score DESC LIMIT 20
WITH collect({
  available_at: node.created,
  available_at_source: 'neo4j_created',
  id: node.id,
  title: node.title,
  teaser: node.teaser,
  created: node.created,
  ft_score: score
}) AS items
RETURN items AS data, [] AS gaps
```

### Latest News (PIT)
```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.created <= $pit
WITH n ORDER BY n.created DESC LIMIT 10
WITH collect({
  available_at: n.created,
  available_at_source: 'neo4j_created',
  id: n.id,
  title: n.title,
  teaser: n.teaser,
  channels: n.channels,
  created: n.created
}) AS items
RETURN items AS data, [] AS gaps
```

### PIT-Safe Query Rules
- Use `n.created <= $pit` (boundary-inclusive; items at PIT are valid)
- NEVER include INFLUENCES relationship properties (daily_stock, daily_macro, etc.)
- Always include `available_at: n.created` and `available_at_source: 'neo4j_created'`
- Use `collect({...})` to produce `data[]` array
- Always `RETURN items AS data, [] AS gaps`
- Pass `pit` in the `params` dict alongside other Cypher parameters
- If query returns 0 results, the envelope `{"data":[],"gaps":[]}` passes the gate

## 7. Notes (News-Specific)

These are unique to the News domain. For general schema rules (timestamps as strings, returns on relationships, NaN handling, INFLUENCES targets), see the `neo4j-schema` skill.

- **`body` field**: Access via `substring(node.body, 0, N)`. Often empty. Full-text indexed in `news_ft`.
- **Channel/tag filtering**: Use `n.channels CONTAINS $channel`. Values are JSON strings. See `.claude/references/neo4j-news-fields.md` for complete channel/tag inventory.
- **`market_session` filtering**: Use `n.market_session = $session`. See `.claude/references/neo4j-news-fields.md` for values.
- **Defensive NaN pattern**: Some analytical queries use a belt-and-suspenders approach: `r.daily_stock <> 'NaN'` then `NOT isNaN(toFloat(r.daily_stock))`. The simpler `IS NOT NULL AND NOT isNaN()` from `neo4j-schema` is sufficient for standard use.
- **Data gap**: 1,746 News→Company edges (0.9%) have `daily_industry` but `daily_stock` is NULL.
- **Property name**: `n.created` (ISO string with TZ), NOT `n.published_utc`.

## 8. Known Data Gaps

| Date | Gap | Affected | Mitigation |
|------|-----|----------|------------|
| 2026-01-11 | Common user error: using `published_utc` instead of `created` | News date filtering | Property is `n.created` (ISO string), not `n.published_utc`. Use `date(n.created)` for date comparisons. |

---
*Version 1.3 | 2026-02-09 | Reorganized: core/return/target/cross-domain/analytical sections; removed vector search (separate agent); added field reference doc; trimmed neo4j-schema duplication from Notes*
