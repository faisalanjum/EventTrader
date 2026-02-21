# Guidance Extraction Queries

Complete Cypher reference for the guidance extraction agent. Every query the agent needs to reach any part of the database, organized by extraction workflow step.

**Tool**: All queries use `mcp__neo4j-cypher__read_neo4j_cypher` (read-only). Graph writes go through `guidance_writer.py`.

**Parameter Substitution**: `$variable` syntax. Pass as parameters dict to the MCP tool call. Pass `null` for optional date parameters to omit filtering, except where explicitly marked date-required (e.g., 6B/6C).

**Schema Rules** (from neo4j-schema):
- All timestamps are Strings (Report.created, News.created, Transcript.conference_datetime)
- Returns live on relationships (PRIMARY_FILER, INFLUENCES), not on nodes
- XBRL booleans are Strings ('0'/'1')
- Fact.value is String even for numeric facts; use `toFloat()` when `is_numeric='1'`
- Report.items is JSON string; use `CONTAINS` for item matching
- Period.end_date can be string 'null' for instant periods
- NaN exists in return fields; filter with `isNaN()` when needed

## Table of Contents

1. [Context Resolution](#1-context-resolution)
2. [Warmup Caches](#2-warmup-caches)
3. [Source Content: Transcript](#3-source-content-transcript)
4. [Source Content: 8-K / Exhibits](#4-source-content-8-k--exhibits)
5. [Source Content: 10-Q / 10-K](#5-source-content-10-q--10-k)
6. [Source Content: News](#6-source-content-news)
7. [Existing Guidance Lookup](#7-existing-guidance-lookup)
8. [Data Inventory](#8-data-inventory)
9. [Fulltext / Keyword Recall](#9-fulltext--keyword-recall)
10. [Guidance Extraction Keywords](#10-guidance-extraction-keywords)

---

## 1. Context Resolution

Resolve company identity, fiscal calendar, and period dates before extraction begins.

### 1A. Company + CIK Lookup

```cypher
MATCH (c:Company {ticker: $ticker})
RETURN c.ticker, c.name, c.cik,
       c.sector, c.industry, c.mkt_cap
```
**Usage**: CIK is required for Context node creation (§6). Never accept CIK from external input; always read from graph.

### 1B. FYE Derivation (from Latest 10-K)

```cypher
MATCH (c:Company {ticker: $ticker})<-[:PRIMARY_FILER]-(r:Report {formType: '10-K'})
RETURN c.ticker, c.name, c.cik, r.periodOfReport, r.created
ORDER BY r.created DESC
LIMIT 1
```
**Usage**: `periodOfReport` reveals FYE month. Example: `2024-09-28` = September FYE (month 9). Extract month from date string.

### 1C. Period Pre-Fetch (for fiscal_resolve.py)

Pre-fetch all Period nodes for a company so `fiscal_resolve.py` can classify them without a second Neo4j connection.

```cypher
MATCH (ctx:Context)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
MATCH (ctx)-[:HAS_PERIOD]->(p:Period)
WHERE p.period_type = 'duration'
RETURN p.u_id AS u_id, p.start_date AS start_date, p.end_date AS end_date
```
**Usage**: Pipe output as JSON array to `fiscal_resolve.py` via Bash:
```bash
echo '$periods_json' | python3 .claude/skills/earnings-orchestrator/scripts/fiscal_resolve.py $TICKER $FISCAL_YEAR $FISCAL_QUARTER $FYE_MONTH
```
Returns: `{"start_date": "...", "end_date": "...", "period_u_id": "duration_...", "period_node_type": "duration", "source": "lookup|fallback"}`

### 1D. All 10-K/10-Q Periods (Alternative Pre-Fetch)

If Context-based pre-fetch returns sparse results, fetch periods from filings directly:

```cypher
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType IN ['10-K', '10-Q']
MATCH (r)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact)
MATCH (f)-[:IN_CONTEXT]->(ctx:Context)-[:HAS_PERIOD]->(p:Period)
WHERE p.period_type = 'duration'
WITH DISTINCT p.u_id AS u_id, p.start_date AS start_date, p.end_date AS end_date
RETURN u_id, start_date, end_date
```

---

## 2. Warmup Caches

Run once per company per extraction run. Feed results to extraction prompt so LLM can map metrics to XBRL concepts and members.

### 2A. Concept Usage Cache

Consolidated facts only (no dimensional members) from most recent 10-K + subsequent 10-Qs. Scoped to current taxonomy window.

```cypher
// Step 1: find most recent 10-K filing date
MATCH (rk:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE rk.formType = '10-K'
WITH c, rk ORDER BY rk.created DESC LIMIT 1
WITH c, rk.created AS last_10k_date
// Step 2: all facts from that 10-K + subsequent 10-Qs
MATCH (f:Fact)-[:HAS_CONCEPT]->(con:Concept)
MATCH (f)-[:IN_CONTEXT]->(ctx:Context)-[:FOR_COMPANY]->(c)
MATCH (f)-[:REPORTS]->(:XBRLNode)<-[:HAS_XBRL]-(r:Report)-[:PRIMARY_FILER]->(c)
WHERE r.formType IN ['10-K','10-Q']
  AND r.created >= last_10k_date
  AND f.is_numeric = '1'
  AND (ctx.member_u_ids IS NULL OR ctx.member_u_ids = [])
WITH con.qname AS qname, count(f) AS usage
ORDER BY usage DESC
RETURN qname, usage
```
**Usage**: Build concept-to-qname lookup. For each guidance metric, pattern-match against this cache to set `xbrl_qname`.

### 2B. Member Profile Cache

Context-based member discovery. Handles CIK padding differences across node families.

```cypher
MATCH (ctx:Context)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
WHERE size(ctx.dimension_u_ids) > 0 AND size(ctx.member_u_ids) > 0
UNWIND range(0, size(ctx.member_u_ids)-1) AS i
WITH ctx.dimension_u_ids[i] AS dim_u_id, ctx.member_u_ids[i] AS mem_u_id
WHERE dim_u_id IS NOT NULL AND mem_u_id IS NOT NULL
  AND (
    dim_u_id CONTAINS 'Axis'
    OR dim_u_id CONTAINS 'Segment'
    OR dim_u_id CONTAINS 'Product'
    OR dim_u_id CONTAINS 'Geography'
    OR dim_u_id CONTAINS 'Region'
  )
WITH dim_u_id, mem_u_id,
     split(mem_u_id, ':')[0] AS mem_cik_raw
WITH dim_u_id, mem_u_id,
     CASE
       WHEN mem_cik_raw =~ '^[0-9]+$'
       THEN toString(toInteger(mem_cik_raw)) + substring(mem_u_id, size(mem_cik_raw))
       ELSE mem_u_id
     END AS mem_u_id_nopad
MATCH (m:Member)
WHERE m.u_id = mem_u_id OR m.u_id = mem_u_id_nopad
WITH m.qname AS member_qname,
     m.u_id AS member_u_id,
     m.label AS member_label,
     dim_u_id,
     split(dim_u_id, ':') AS dim_parts,
     count(*) AS usage
WITH member_qname,
     member_u_id,
     member_label,
     dim_u_id AS axis_u_id,
     dim_parts[size(dim_parts)-2] + ':' + dim_parts[size(dim_parts)-1] AS axis_qname,
     usage
ORDER BY member_qname, usage DESC
WITH member_qname,
     collect({
       member_u_id: member_u_id,
       member_label: member_label,
       axis_qname: axis_qname,
       axis_u_id: axis_u_id,
       usage: usage
     }) AS versions
RETURN member_qname,
       versions[0].member_u_id AS best_member_u_id,
       versions[0].member_label AS best_member_label,
       versions[0].axis_qname AS best_axis_qname,
       versions[0].axis_u_id AS best_axis_u_id,
       versions[0].usage AS best_usage,
       reduce(total = 0, v IN versions | total + v.usage) AS total_usage
```
**Usage**: Feed `member_label` values to LLM so it can match segment names from source text to XBRL members.

---

## 3. Source Content: Transcript

### 3A. Transcript List

```cypher
MATCH (t:Transcript)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE ($start_date IS NULL OR t.conference_datetime >= $start_date)
  AND ($end_date IS NULL OR t.conference_datetime <= $end_date)
RETURN t.id, t.conference_datetime, t.fiscal_quarter, t.fiscal_year, t.company_name
ORDER BY t.conference_datetime
```
**Usage**: Pass `null` for both dates to retrieve all historical transcripts. Uses `INFLUENCES` relationship. `conference_datetime` is ISO string.

### 3B. Structured Transcript Content (Primary Fetch)

Returns prepared remarks AND all Q&A exchanges in a single query. This is the primary content fetch for transcript extraction.

```cypher
MATCH (t:Transcript {id: $transcript_id})
OPTIONAL MATCH (t)-[:HAS_PREPARED_REMARKS]->(pr:PreparedRemark)
OPTIONAL MATCH (t)-[:HAS_QA_EXCHANGE]->(qa:QAExchange)
WITH t, pr,
     qa ORDER BY toInteger(qa.sequence)
WITH t,
     pr.content AS prepared_remarks,
     [item IN collect({
       sequence: qa.sequence,
       questioner: qa.questioner,
       questioner_title: qa.questioner_title,
       responders: qa.responders,
       responder_title: qa.responder_title,
       exchanges: qa.exchanges
     }) WHERE item.sequence IS NOT NULL] AS qa_exchanges
RETURN t.id AS transcript_id,
       t.conference_datetime AS call_date,
       t.company_name AS company,
       t.fiscal_quarter AS fiscal_quarter,
       t.fiscal_year AS fiscal_year,
       prepared_remarks,
       qa_exchanges
```
**Critical**: Returns `prepared_remarks` (JSON text with speaker statements) and `qa_exchanges` (array of Q&A objects). Both must be scanned for guidance. See PROFILE_TRANSCRIPT.md for extraction rules.

**Empty check**: If `qa_exchanges` is empty list, try 3C (Q&A Section fallback) before concluding Q&A is missing. If BOTH `prepared_remarks` is null/empty AND no Q&A from either 3B or 3C, try 3D (full transcript text).

### 3C. Q&A Section Content (Fallback)

40 transcripts use `HAS_QA_SECTION → QuestionAnswer` instead of `HAS_QA_EXCHANGE → QAExchange`. Try this when 3B returns empty `qa_exchanges`.

```cypher
MATCH (t:Transcript {id: $transcript_id})-[:HAS_QA_SECTION]->(qa:QuestionAnswer)
RETURN qa.id, qa.content, qa.speaker_roles
```
**Content format**: `content` is a JSON string containing an array of speaker-labeled dialogue lines. `speaker_roles` is a JSON string containing an object mapping speaker names to roles (OPERATOR, EXECUTIVE, ANALYST). Both require JSON parsing. `speaker_roles` is NULL on ~7 of 41 nodes — handle gracefully.

**Note**: These ~40 transcripts have no QAExchange nodes. Without this fallback, their Q&A content is invisible to the agent.

### 3D. Full Transcript Text (Fallback)

Use only when 3B and 3C both return empty content (prepared remarks and Q&A both missing).

```cypher
MATCH (t:Transcript {id: $transcript_id})-[:HAS_FULL_TEXT]->(ft:FullTranscriptText)
RETURN ft.content
```
**Note**: Only 28 FullTranscriptText nodes exist in the database. Most transcripts use PreparedRemark + QAExchange instead.

### 3E. Latest Transcript for Company

```cypher
MATCH (t:Transcript)-[:INFLUENCES]->(c:Company {ticker: $ticker})
RETURN t.id, t.conference_datetime, t.fiscal_quarter, t.fiscal_year
ORDER BY t.conference_datetime DESC
LIMIT 1
```

### 3F. Q&A Exchanges Only

Use when re-scanning Q&A for a specific transcript.

```cypher
MATCH (t:Transcript {id: $transcript_id})-[:HAS_QA_EXCHANGE]->(qa:QAExchange)
RETURN qa.sequence, qa.questioner, qa.questioner_title,
       qa.responders, qa.responder_title, qa.exchanges
ORDER BY toInteger(qa.sequence)
```

### 3G. Q&A by Questioner

Search for a specific analyst's questions across transcripts.

```cypher
MATCH (t:Transcript)-[:INFLUENCES]->(c:Company {ticker: $ticker})
MATCH (t)-[:HAS_QA_EXCHANGE]->(qa:QAExchange)
WHERE qa.questioner CONTAINS $analyst_name
RETURN t.conference_datetime, qa.questioner, qa.questioner_title, qa.exchanges
ORDER BY t.conference_datetime DESC
```

---

## 4. Source Content: 8-K / Exhibits

### 4A. 8-K Filings with Item 2.02 (Earnings)

```cypher
MATCH (r:Report {formType: '8-K'})-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.items CONTAINS 'Item 2.02'
  AND ($start_date IS NULL OR r.created >= $start_date)
  AND ($end_date IS NULL OR r.created <= $end_date)
RETURN r.accessionNo, r.created, r.items, r.market_session
ORDER BY r.created
```
**Usage**: Pass `null` for both dates to retrieve all historical 8-K earnings filings.

### 4B. Pre-Announcements (Item 7.01 / 8.01)

Mid-quarter updates, often market-moving. Check between regular earnings dates.

```cypher
MATCH (r:Report {formType: '8-K'})-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE (r.items CONTAINS '7.01' OR r.items CONTAINS '8.01')
  AND ($start_date IS NULL OR r.created >= $start_date)
  AND ($end_date IS NULL OR r.created <= $end_date)
RETURN r.accessionNo, r.created, r.items
ORDER BY r.created
```

### 4C. Exhibit Content (EX-99.x Press Release)

Primary content source for 8-K earnings. 94% of Item 2.02 filings have data in EX-99.1.

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_EXHIBIT]->(e:ExhibitContent)
WHERE e.exhibit_number = $source_key
RETURN e.content AS content, r.created AS filing_date
```
**Note**: Use exact match on `exhibit_number` (e.g., `'EX-99.1'`). Common values: `EX-99.1` (press release), `EX-99.2` (presentation). If exact match fails, use 4D to discover actual exhibit numbers (dirty variants like `EX-99.01` exist).

### 4D. All Exhibits for Report (Discovery)

Run when unsure which exhibit has content or when exact match fails.

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_EXHIBIT]->(e:ExhibitContent)
RETURN e.exhibit_number, size(e.content) AS content_length
ORDER BY e.exhibit_number
```

### 4E. Section Content (8-K Item Text)

For items where data is in the section itself (33% of 8-Ks have section-only data).

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_SECTION]->(s:ExtractedSectionContent)
WHERE s.section_name = $source_key
RETURN s.content AS content, r.created AS filing_date
```
**Key section_name values for 8-K**:
- `ResultsofOperationsandFinancialCondition` (Item 2.02)
- `RegulationFDDisclosure` (Item 7.01)
- `OtherEvents` (Item 8.01)
- `FinancialStatementsandExhibits` (Item 9.01)

### 4F. Filing Text Content (Fallback)

Fallback when exhibit and section parsing both fail. Average 690KB — large.

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_FILING_TEXT]->(f:FilingTextContent)
RETURN f.content AS content, r.created AS filing_date
```

### 4G. Content Inventory for Report

Quickly check what content types exist before fetching.

```cypher
MATCH (r:Report {accessionNo: $accession})
OPTIONAL MATCH (r)-[:HAS_EXHIBIT]->(e:ExhibitContent)
OPTIONAL MATCH (r)-[:HAS_SECTION]->(s:ExtractedSectionContent)
OPTIONAL MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(fs:FinancialStatementContent)
OPTIONAL MATCH (r)-[:HAS_FILING_TEXT]->(ft:FilingTextContent)
RETURN r.accessionNo, r.formType, r.created,
       collect(DISTINCT e.exhibit_number) AS exhibits,
       collect(DISTINCT s.section_name) AS sections,
       collect(DISTINCT fs.statement_type) AS financial_stmts,
       count(DISTINCT ft) AS filing_text_count
```

---

## 5. Source Content: 10-Q / 10-K

### 5A. 10-Q/10-K Filing List

```cypher
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType IN ['10-K', '10-Q']
  AND ($start_date IS NULL OR r.created >= $start_date)
  AND ($end_date IS NULL OR r.created <= $end_date)
RETURN r.accessionNo, r.formType, r.created, r.periodOfReport
ORDER BY r.created
```

### 5B. MD&A Section Content (Primary for 10-Q/10-K)

MD&A is the primary scan scope for 10-Q/10-K guidance extraction.

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_SECTION]->(s:ExtractedSectionContent)
WHERE s.section_name STARTS WITH 'Management'
  AND s.section_name CONTAINS 'DiscussionandAnalysisofFinancialCondition'
RETURN s.content AS content, s.section_name, r.created AS filing_date
```
**Note**: Two naming variants exist. Check both.

### 5C. Financial Statement Content (Supplementary)

Structured JSON data — look for footnotes/annotations with forward guidance.

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_FINANCIAL_STATEMENT]->(fs:FinancialStatementContent)
WHERE fs.statement_type = $source_key
RETURN fs.value AS content, r.created AS filing_date
```
**statement_type values**: `BalanceSheets`, `StatementsOfIncome`, `StatementsOfCashFlows`, `StatementsOfShareholdersEquity`.

### 5D. All Sections for Report (Discovery)

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_SECTION]->(s:ExtractedSectionContent)
RETURN s.section_name, size(s.content) AS content_length
ORDER BY s.section_name
```

### 5E. Risk Factors (Exclude from Guidance)

Useful to identify so guidance scanner can skip this section (legal/risk-heavy content).

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_SECTION]->(s:ExtractedSectionContent)
WHERE s.section_name = 'RiskFactors'
RETURN size(s.content) AS risk_factors_length
```

---

## 6. Source Content: News

### 6A. News Content by ID

```cypher
MATCH (n:News {id: $news_id})
RETURN n.body AS content, n.created AS pub_date, n.title AS title, n.channels
```
**Empty check**: If BOTH `title` and `body` are null/empty, return `EMPTY_CONTENT|news|full`.

### 6B. Guidance-Channel News (Pre-Filtered)

Filter by Benzinga channels BEFORE LLM processing. These channels most likely contain company guidance. **Dates are required** — news result sets are too large for unbounded queries.

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
**Note**: `body` field is often empty — title may contain complete guidance. Always process both.

### 6E. Earnings Beat/Miss News (for Context)

News tagged as earnings results, useful for cross-referencing guidance context.

```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.created >= $start_date
  AND n.created <= $end_date
  AND n.channels CONTAINS 'Earnings'
RETURN n.id, n.title, n.created, n.channels
ORDER BY n.created
```

---

## 7. Existing Guidance Lookup

Query existing guidance graph nodes before extraction to provide context to LLM.

### 7A. Existing Guidance Tags for Company

```cypher
MATCH (g:Guidance)<-[:UPDATES]-(gu:GuidanceUpdate)
      -[:IN_CONTEXT]->(ctx:Context)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
RETURN DISTINCT g.label, g.id
```
**Usage**: Feed existing Guidance labels to LLM so it reuses canonical metric names rather than creating duplicates.

### 7B. Latest Guidance per Metric

```cypher
MATCH (gu:GuidanceUpdate)-[:UPDATES]->(g:Guidance)
MATCH (gu)-[:IN_CONTEXT]->(ctx:Context)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
WITH g, gu ORDER BY gu.given_date DESC, gu.id DESC
WITH g, collect(gu)[0] AS latest
RETURN g.label, latest.given_date, latest.low, latest.mid, latest.high,
       latest.unit, latest.basis_norm, latest.segment,
       latest.fiscal_year, latest.fiscal_quarter
```

### 7C. Check Existing GuidanceUpdate by ID

Idempotency check — compute ID first, then verify it doesn't already exist.

```cypher
MATCH (gu:GuidanceUpdate {id: $guidance_update_id})
RETURN gu.id, gu.given_date, gu.evhash16
```

### 7D. All GuidanceUpdates for Source

Check what guidance was already extracted from a specific source document.

```cypher
MATCH (gu:GuidanceUpdate)-[:FROM_SOURCE]->(src)
WHERE src.id = $source_id
MATCH (gu)-[:UPDATES]->(g:Guidance)
RETURN g.label, gu.id, gu.given_date, gu.low, gu.mid, gu.high,
       gu.unit, gu.basis_norm, gu.segment
ORDER BY g.label
```

---

## 8. Data Inventory

Run first to understand what data exists for a company.

### 8A. Comprehensive Data Inventory

```cypher
MATCH (c:Company {ticker: $ticker})
OPTIONAL MATCH (r8k:Report {formType: '8-K'})-[:PRIMARY_FILER]->(c)
  WHERE r8k.items CONTAINS 'Item 2.02'
  AND ($start_date IS NULL OR r8k.created >= $start_date)
  AND ($end_date IS NULL OR r8k.created <= $end_date)
OPTIONAL MATCH (t:Transcript)-[:INFLUENCES]->(c)
  WHERE ($start_date IS NULL OR t.conference_datetime >= $start_date)
  AND ($end_date IS NULL OR t.conference_datetime <= $end_date)
OPTIONAL MATCH (n:News)-[:INFLUENCES]->(c)
  WHERE ($start_date IS NULL OR n.created >= $start_date)
  AND ($end_date IS NULL OR n.created <= $end_date)
OPTIONAL MATCH (rxbrl:Report)-[:PRIMARY_FILER]->(c)
  WHERE rxbrl.formType IN ['10-K', '10-Q']
RETURN c.ticker, c.name,
       count(DISTINCT r8k) AS earnings_8k_count,
       count(DISTINCT t) AS transcript_count,
       count(DISTINCT n) AS news_count,
       count(DISTINCT rxbrl) AS xbrl_report_count
```

### 8B. Existing Guidance Node Count

```cypher
MATCH (gu:GuidanceUpdate)-[:IN_CONTEXT]->(ctx:Context)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
MATCH (gu)-[:UPDATES]->(g:Guidance)
RETURN count(DISTINCT g) AS guidance_tags,
       count(gu) AS guidance_updates,
       min(gu.given_date) AS earliest,
       max(gu.given_date) AS latest
```

---

## 9. Fulltext / Keyword Recall

Supplementary recall queries for finding guidance-related content across fulltext indexes.

### 9A. Search Q&A Exchanges (Fulltext)

```cypher
CALL db.index.fulltext.queryNodes('qa_exchange_ft', $query)
YIELD node, score
MATCH (node)<-[:HAS_QA_EXCHANGE]-(t:Transcript)-[:INFLUENCES]->(c:Company {ticker: $ticker})
RETURN t.conference_datetime, node.questioner, node.exchanges, score
ORDER BY score DESC
LIMIT 20
```

### 9B. Search Prepared Remarks (Fulltext)

```cypher
CALL db.index.fulltext.queryNodes('prepared_remarks_ft', $query)
YIELD node, score
MATCH (t:Transcript)-[:HAS_PREPARED_REMARKS]->(node)
MATCH (t)-[:INFLUENCES]->(c:Company {ticker: $ticker})
RETURN t.conference_datetime, substring(node.content, 0, 500), score
ORDER BY score DESC
LIMIT 10
```

### 9C. Search Full Transcripts (Fulltext)

```cypher
CALL db.index.fulltext.queryNodes('full_transcript_ft', $query)
YIELD node, score
MATCH (t:Transcript)-[:HAS_FULL_TEXT]->(node)
MATCH (t)-[:INFLUENCES]->(c:Company {ticker: $ticker})
RETURN t.conference_datetime, score, substring(node.content, 0, 500)
ORDER BY score DESC
LIMIT 5
```

### 9D. Search Exhibit Content (Fulltext)

```cypher
CALL db.index.fulltext.queryNodes('exhibit_content_ft', $query)
YIELD node, score
MATCH (node)<-[:HAS_EXHIBIT]-(r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
RETURN r.accessionNo, r.created, node.exhibit_number,
       substring(node.content, 0, 500), score
ORDER BY score DESC
LIMIT 10
```

### 9E. Search Extracted Sections (Fulltext)

```cypher
CALL db.index.fulltext.queryNodes('extracted_section_content_ft', $query)
YIELD node, score
MATCH (node)<-[:HAS_SECTION]-(r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
RETURN r.accessionNo, r.formType, node.section_name,
       substring(node.content, 0, 500), score
ORDER BY score DESC
LIMIT 10
```

### 9F. Search News (Fulltext)

```cypher
CALL db.index.fulltext.queryNodes('news_ft', $query)
YIELD node, score
MATCH (node)-[:INFLUENCES]->(c:Company {ticker: $ticker})
RETURN node.id, node.title, node.created, score
ORDER BY score DESC
LIMIT 20
```

---

## 10. Guidance Extraction Keywords

When searching via fulltext or scanning content, use these terms:

| Category | Keywords |
|----------|----------|
| **Forward-looking** | expects, anticipates, projects, forecasts, outlook, looking ahead |
| **Guidance** | guidance, range, target, between X and Y, approximately |
| **Periods** | Q1-Q4, full year, fiscal year, FY, for the quarter, second half |
| **Metrics** | EPS, earnings per share, revenue, sales, margin, income, cash flow |
| **Revisions** | raises, lowers, maintains, reaffirms, withdraws, narrows, widens |
| **Qualitative** | low single digits, double-digit, mid-teens, high single digits |
| **Conditional** | assumes, contingent on, excluding, subject to |

**Fulltext query construction**: Combine with OR for broad recall:
```
guidance OR outlook OR expects OR anticipates OR "full year" OR "fiscal year"
```

---

## Fulltext Index Reference

| Index Name | Node Label | Fields Indexed |
|-----------|-----------|----------------|
| `qa_exchange_ft` | QAExchange | exchanges |
| `prepared_remarks_ft` | PreparedRemark | content |
| `full_transcript_ft` | FullTranscriptText | content |
| `exhibit_content_ft` | ExhibitContent | content, exhibit_number |
| `extracted_section_content_ft` | ExtractedSectionContent | content, section_name |
| `news_ft` | News | title, body, teaser |
| `concept_ft` | Concept | label, qname |
| `fact_textblock_ft` | Fact | value, qname |
| `financial_statement_content_ft` | FinancialStatementContent | value, statement_type |
| `filing_text_content_ft` | FilingTextContent | content, form_type |
| `company_ft` | Company | name, displayLabel |

---

## Execution Order

### Initial Build (New Company)
1. **Context**: 1A (Company+CIK) → 1B (FYE) → 1C (Period pre-fetch)
2. **Warmup**: 2A (Concept cache) → 2B (Member cache)
3. **Existing**: 7A (Existing Guidance tags)
4. **Sources** (chronological by filing date):
   - 4A (earnings 8-K) + 4B (pre-announcements) with null dates → for each: 4C/4E (content)
   - 3A with null dates (All transcripts) → for each: 3B (structured content), 3C if Q&A missing
   - 5A with null dates (All 10-Q/10-K filings) → for each: 5B (MD&A)
   - 6B (Guidance-channel news, dates required) → for each: 6A (content)
5. **Write**: `guidance_writer.py` handles all graph writes (not Cypher in this file)

### Single Source Extraction
1. **Context**: 1A → 1B → 1C (if not cached)
2. **Warmup**: 2A → 2B (if not cached)
3. **Existing**: 7A
4. **Fetch**: Source-specific query (3B/3C, 4C/4E, 5B, 6A)
5. **Extract** → **Validate** → **Write** via `guidance_writer.py`

---
*Version 2.6 | 2026-02-21 | Fixed 3B phantom null (collect filter), null-date guards for 4B/5A, corrected QuestionAnswer types to STRING, marked 6B/6C dates as required. Prior: v2.5 (4B exec order), v2.4 (3C fallback), v2.3 (MD&A apostrophe).*
