# News Queries (S6)

Source content queries for news articles.

---

## 6. Source Content: News

### 6A. News Content by ID

```cypher
MATCH (n:News {id: $news_id})
RETURN n.body AS content, n.created AS pub_date, n.title AS title, n.channels
```
**Empty check**: If BOTH `title` and `body` are null/empty, return `EMPTY_CONTENT|news|full`.

### 6B. Channel-Filtered News (Pre-Filtered)

Filter by Benzinga channels BEFORE LLM processing. These channels most likely contain forward-looking content. **Dates are required** — news result sets are too large for unbounded queries.

```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.created >= $start_date
  AND n.created <= $end_date
  AND (n.channels CONTAINS 'Guidance'
    OR n.channels CONTAINS 'Earnings'
    OR n.channels CONTAINS 'Previews'
    OR n.channels CONTAINS 'Management')
RETURN n.id, n.title, n.created, n.channels
ORDER BY n.created
```

### 6C. All News for Company (Date Range Required)

```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.created >= $start_date
  AND n.created <= $end_date
RETURN n.id, n.title, n.teaser, n.created, n.channels
ORDER BY n.created DESC
```

### 6D. News with Body Content

Full content fetch for a specific news item.

```cypher
MATCH (n:News {id: $news_id})
RETURN n.id, n.title, n.body, n.teaser, n.created, n.channels, n.tags
```
**Note**: `body` field is often empty — title may contain complete forward-looking content. Always process both.

### 6E. Earnings Beat/Miss News (for Context)

News tagged as earnings results, useful for cross-referencing extraction context.

```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.created >= $start_date
  AND n.created <= $end_date
  AND n.channels CONTAINS 'Earnings'
RETURN n.id, n.title, n.created, n.channels
ORDER BY n.created
```
