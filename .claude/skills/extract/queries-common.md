# Common Extraction Queries

Shared Cypher queries loaded by all extraction agents. Covers context resolution, warmup caches, data inventory, and fulltext recall. Asset-specific and type-specific queries are in separate files.

**Tool**: All queries use `mcp__neo4j-cypher__read_neo4j_cypher` (read-only). Graph writes go through type-specific writer scripts via Bash.

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
8. [Data Inventory](#8-data-inventory)
9. [Fulltext / Keyword Recall](#9-fulltext--keyword-recall)

Asset-specific queries: see `assets/{asset}-queries.md`
Type-specific queries: see `types/{type}/{type}-queries.md`

---

## 1. Context Resolution

Resolve company identity, fiscal calendar, and period dates before extraction begins.

### 1A. Company + CIK Lookup

```cypher
MATCH (c:Company {ticker: $ticker})
RETURN c.ticker, c.name, c.cik,
       c.sector, c.industry, c.mkt_cap
```
**Usage**: CIK is required for Period node creation (§6). Never accept CIK from external input; always read from graph.

### 1B. FYE Derivation (from Latest 10-K)

```cypher
MATCH (c:Company {ticker: $ticker})<-[:PRIMARY_FILER]-(r:Report {formType: '10-K'})
RETURN c.ticker, c.name, c.cik, r.periodOfReport, r.created
ORDER BY r.created DESC
LIMIT 1
```
**Usage**: `periodOfReport` reveals FYE month. Example: `2024-09-28` = September FYE (month 9). Extract month from date string.

### 1C. Period Pre-Fetch

Pre-fetch all Period nodes for a company. Used by XBRL pipeline for period classification. Not required for guidance extraction (guidance uses calendar-based GuidancePeriod nodes via `build_guidance_period_id()` instead).

```cypher
MATCH (ctx:Context)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
MATCH (ctx)-[:HAS_PERIOD]->(p:Period)
WHERE p.period_type = 'duration'
WITH DISTINCT p.u_id AS u_id, p.start_date AS start_date, p.end_date AS end_date
RETURN u_id, start_date, end_date
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
WITH DISTINCT dim_u_id, mem_u_id
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
1. **Context**: 1A (Company+CIK) → 1B (FYE)
2. **Warmup**: 2A (Concept cache) → 2B (Member cache)
3. **Existing**: Type-specific lookup (see type queries)
4. **Sources** (chronological by filing date):
   - 4A (earnings 8-K) + 4B (pre-announcements) with null dates → for each: 4C/4E (content)
   - 3A with null dates (All transcripts) → for each: 3B (structured content), 3C if Q&A missing
   - 5A with null dates (All 10-Q/10-K filings) → for each: 5B (MD&A)
   - 6B (Guidance-channel news, dates required) → for each: 6A (content)
5. **Write**: Type-specific writer scripts handle all graph writes (not Cypher in this file)

### Single Source Extraction
1. **Context**: 1A → 1B
2. **Warmup**: 2A → 2B (if not cached)
3. **Existing**: Type-specific lookup (see type queries)
4. **Fetch**: Source-specific query (see asset queries)
5. **Extract** → **Validate** → **Write** via type-specific writer scripts

---
*Version 2.11 | 2026-02-26 | 7E: Period→GuidancePeriod, gu.period_type→gu.period_scope, added gu.time_type, gp.start_date/end_date, removed p.period_type AS period_node_type. Prior: v2.10 (removed 1C from Execution Order). v2.9 (7A/7B/8B FOR_COMPANY fix, 7B/7D canonical_unit). v2.8 (1C DISTINCT dedup). v2.7 (3B phantom null, null-date guards).*
