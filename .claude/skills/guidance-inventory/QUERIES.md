# Queries for Guidance Inventory

**IMPORTANT**: This skill runs in forked context (called from earnings-orchestrator at Layer 1).
Task tool is BLOCKED in forked contexts. Use **Skill tool** (`/neo4j-report`, etc.) or **MCP tools directly**.

**Parameter Substitution**: Cypher queries use `$variable` syntax (e.g., `$ticker`, `$start_date`). When using MCP tools directly, pass these as parameters to `mcp__neo4j-cypher__read_neo4j_cypher`. When using Skills, include the values in your query prompt.

## Table of Contents

1. [Fiscal Profile](#1-fiscal-profile)
2. [8-K Guidance (Primary Source)](#2-8-k-guidance-primary-source)
3. [Transcript Guidance](#3-transcript-guidance)
4. [Historical Financials](#4-historical-financials-for-beatmiss-pattern)
5. [Consensus Estimates](#5-consensus-estimates)
6. [Gap Filling](#6-gap-filling)
7. [Execution Order](#execution-order)
8. [Guidance Extraction Keywords](#guidance-extraction-keywords)

---

## 1. Fiscal Profile

### Via Skill
```
/neo4j-entity
Query: "Get fiscal year end for {ticker} from Company node or latest 10-K periodOfReport"
```

### Via MCP (Direct Cypher)
```cypher
MATCH (c:Company {ticker: $ticker})<-[:PRIMARY_FILER]-(r:Report {formType: '10-K'})
RETURN c.ticker, c.name, r.periodOfReport
ORDER BY r.created DESC
LIMIT 1
```
**Usage**: `periodOfReport` reveals FYE (e.g., `2024-09-30` = September FYE)

---

## 2. 8-K Guidance (Primary Source)

### Via Skill
```
/neo4j-report
Query: "All 8-K filings with Item 2.02 and EX-99.1 for {ticker} [date range].
Extract forward guidance, outlook, expects, anticipates statements."
```

### Via MCP (Direct Cypher)

**Get 8-K list:**
```cypher
MATCH (r:Report)-[pf:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType = '8-K'
  AND r.items CONTAINS '2.02'
  AND r.created >= $start_date
  AND r.created <= $end_date
RETURN r.accessionNo, r.created, r.items
ORDER BY r.created
```

**Get EX-99.1 content:**
```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_EXHIBIT]->(e:ExhibitContent)
WHERE e.exhibit_type CONTAINS '99.1'
RETURN e.content
LIMIT 1
```

**Pre-announcements (Item 7.01):**
```cypher
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType = '8-K'
  AND (r.items CONTAINS '7.01' OR r.items CONTAINS '8.01')
  AND r.created >= $start_date
  AND r.created <= $end_date
RETURN r.accessionNo, r.created, r.items
ORDER BY r.created
```

---

## 3. Transcript Guidance

### Via Skill
```
/neo4j-transcript
Query: "All transcripts for {ticker} [date range].
Extract forward-looking statements, EPS/revenue guidance, management outlook."
```

### Via MCP (Direct Cypher)

**Get transcript list:**
```cypher
MATCH (t:Transcript)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE t.conference_datetime >= $start_date
  AND t.conference_datetime <= $end_date
RETURN t.id, t.conference_datetime, t.fiscal_quarter, t.fiscal_year
ORDER BY t.conference_datetime
```

**Get full text:**
```cypher
MATCH (t:Transcript {id: $transcript_id})-[:HAS_FULL_TEXT]->(ft:FullTranscriptText)
RETURN ft.content
```

**Search for guidance keywords:**
```cypher
CALL db.index.fulltext.queryNodes('full_transcript_ft', 'guidance OR outlook OR expects')
YIELD node, score
MATCH (t:Transcript)-[:HAS_FULL_TEXT]->(node)
MATCH (t)-[:INFLUENCES]->(c:Company {ticker: $ticker})
RETURN t.conference_datetime, score, substring(node.content, 0, 500)
ORDER BY score DESC
LIMIT 5
```

---

## 4. Historical Financials (For Beat/Miss Pattern)

### Via Skill
```
/neo4j-xbrl
Query: "EPS and Revenue history for {ticker} from last 8 quarters of 10-K/10-Q filings"
```

### Via MCP (Direct Cypher)

**EPS history:**
```cypher
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType IN ['10-K', '10-Q']
MATCH (r)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
MATCH (f)-[:HAS_CONCEPT]->(con:Concept)
WHERE con.qname IN ['us-gaap:EarningsPerShareDiluted', 'us-gaap:EarningsPerShareBasic']
  AND f.is_numeric = '1'
RETURN r.periodOfReport, con.qname, f.value
ORDER BY r.periodOfReport DESC
LIMIT 12
```

---

## 5. Consensus Estimates

### Via Skill
```
/alphavantage-earnings
Query: "Consensus estimates for {ticker} - EPS for current and next quarter"
```

### Via MCP
Use `mcp__alphavantage__EARNINGS_ESTIMATES` with symbol parameter.

---

## 6. Gap Filling

### Via Skill
```
/perplexity-search
Query: "{company_name} ({ticker}) FY{year} earnings guidance history outlook"
```

### Via MCP
Use `mcp__perplexity__perplexity_search` with query parameter.

---

## Execution Order

### For q=1 (Initial Build)
1. `/neo4j-entity` → Get fiscal profile
2. `/neo4j-report` → All 8-K with guidance (no date filter)
3. `/neo4j-transcript` → All transcripts (no date filter)
4. `/alphavantage-earnings` → Consensus for comparison
5. `/perplexity-search` → Fill any gaps

### For q>=2 (Update)
1. `/neo4j-report` → 8-K in date range only
2. `/neo4j-transcript` → Transcripts in date range only

**Note**: Skills execute SEQUENTIALLY in forked context. No parallel execution possible.

---

## Guidance Extraction Keywords

When parsing content, search for:

| Category | Keywords |
|----------|----------|
| **Forward-looking** | expects, anticipates, projects, forecasts, outlook |
| **Guidance** | guidance, range, target, between X and Y |
| **Periods** | Q1-Q4, full year, fiscal year, FY, for the quarter |
| **Metrics** | EPS, earnings per share, revenue, sales, margin |
| **Revisions** | raises, lowers, maintains, reaffirms, withdraws |

---
*Version 1.3 | 2026-01-17 | Added parameter substitution note*
