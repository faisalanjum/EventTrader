# Neo4j Schema Reference for Earnings Attribution (Validated)

## Scope and Validation
- Validated on 2026-01-04 against bolt://localhost:30687 (Neo4j 5.26.4).
- Counts from: `CALL db.stats.retrieve('GRAPH COUNTS')`.
- Types from: `CALL apoc.meta.nodeTypeProperties` and `CALL apoc.meta.relTypeProperties`.
- Counts are for orientation only (data coverage), not for logic.

## Read This First (No Assumptions)
1. **Returns live on relationships**, not nodes: `PRIMARY_FILER`, `INFLUENCES`, `REFERENCED_IN`.
2. **All timestamps are Strings** (Report.created, News.created, Transcript.conference_datetime, Date.*).
3. **JSON is stored as Strings** (Report.items, Report.exhibit_contents, Report.extracted_sections, News.channels/tags/authors).
4. **Numeric-looking fields are Strings** (Company.mkt_cap, Company.shares_out, Company.employees, Fact.value).
5. **XBRL booleans are Strings**: Fact.is_numeric/is_nil, Dimension.is_explicit/is_typed, Unit.is_simple_unit/is_divide.
6. **Returns are percentages** (5.06 means 5.06%, not 0.0506).
7. **INFLUENCES alias trap**: using `inf` as the alias breaks (`inf` is treated as infinity). Use `r`.
8. **NaN exists** in return fields (PRIMARY_FILER: 4 rows; INFLUENCES: 1 row). Filter with `isNaN()`.
9. **hourly_stock is usually Float** but appears once as `LIST OF FLOAT` on PRIMARY_FILER; handle list-or-float.
10. **Some Facts lack Context**: 12,939 Facts have no `IN_CONTEXT` relationship; exclude unless needed.
11. **Period end_date can be string 'null'** for `period_type='instant'` (2,776 rows).

## Schema Discovery (Run First If Unsure)
```cypher
CALL db.labels() YIELD label RETURN label ORDER BY label
CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType ORDER BY relationshipType
CALL apoc.meta.schema()
```

## Core Labels (Counts + Key Properties)

### Event + Company
| Label | Count | Key properties (type) |
|------|-------|------------------------|
| **Report** | 33,947 | `id`, `accessionNo`, `formType`, `created` (String); `items` (String JSON); `market_session` |
| **Company** | 796 | `ticker`, `symbol`, `name` (String); `mkt_cap`/`shares_out`/`employees` (String) |
| **News** | 186,206 | `title`/`teaser`/`body` (String); `channels`/`tags`/`authors` (String JSON); `created`/`updated` (String) |
| **Transcript** | 4,387 | `id`, `conference_datetime`, `created`/`updated` (String); `fiscal_quarter`/`fiscal_year` |
| **QAExchange** | 79,651 | `exchanges`, `questioner`/`responders`, `sequence` (String); `embedding` (float[]) |
| **PreparedRemark** | 4,253 | `content` (String) |
| **Dividend** | 4,282 | `declaration_date`, `cash_amount`, `dividend_type` (String) |
| **Split** | 33 | `execution_date`, `split_from`, `split_to` (String) |

### Market + Calendar
| Label | Count | Key properties (type) |
|------|-------|------------------------|
| **MarketIndex** | 1 | `name`, `ticker`, `etf` (String) |
| **Sector** | 11 | `name`, `etf` (String) |
| **Industry** | 115 | `name`, `etf` (String) |
| **Date** | 946 | `date`, `is_trading_day`, `market_open_*`, `market_close_*`, `pre_market_*`, `post_market_*` (String) |

### XBRL
| Label | Count | Key properties (type) |
|------|-------|------------------------|
| **XBRLNode** | 8,189 | `id`, `report_id`, `accessionNo`, `primaryDocumentUrl` (String) |
| **Fact** | 9,930,840 | `value` (String), `is_numeric`/`is_nil` (String), `period_ref`, `unit_ref` |
| **Concept** | 467,963 | `qname`, `label`, `type_local`, `period_type` |
| **Context** | 3,021,535 | `context_id`, `period_u_id`, `member_u_ids` (String) |
| **Period** | 9,919 | `period_type`, `start_date`, `end_date` (String) |
| **Unit** | 6,146 | `name`, `namespace`, `unit_reference` (String); `is_simple_unit`/`is_divide` (String) |
| **Dimension** | 878,021 | `qname`, `label`, `network_uri` (String); `is_explicit`/`is_typed` (String) |
| **Domain** | 120,488 | `qname`, `label`, `level` (String) |
| **Member** | 1,240,344 | `qname`, `label`, `level` (String) |
| **Abstract** | 50,354 | `label`, `qname` (String) |

### Content
| Label | Count | Key properties (type) |
|------|-------|------------------------|
| **ExtractedSectionContent** | 157,841 | `content`, `section_name`, `filing_id` (String) |
| **ExhibitContent** | 30,812 | `content`, `exhibit_number`, `filing_id` (String) |
| **FinancialStatementContent** | 31,312 | `value`, `statement_type`, `filing_id` (String) |
| **FilingTextContent** | 1,908 | `content`, `filing_id` (String) |
| **FullTranscriptText** | 28 | `content` (String) |
| **QuestionAnswer** | 41 | `content`, `speaker_roles` (String) |

## Relationship Overview (Counts + Purpose)

### Returns and Impact
| Relationship | Count | Notes |
|-------------|-------|-------|
| **PRIMARY_FILER** | 32,942 | `Report -> Company`. Returns stored here (Double). |
| **INFLUENCES** | 864,234 | `News/Transcript/Report -> Company/Sector/Industry/MarketIndex`. Returns stored here (Double). |
| **REFERENCED_IN** | 1,075 | `Report -> Company`. Returns often populated (1,010/1,075). |
| **HAS_PRICE** | 551,563 | `Date -> Company/Sector/Industry/MarketIndex`. OHLCV on relationship. |

### Event Content
HAS_SECTION (Report -> ExtractedSectionContent), HAS_EXHIBIT, HAS_FINANCIAL_STATEMENT, HAS_FILING_TEXT,
HAS_TRANSCRIPT, HAS_QA_EXCHANGE, HAS_PREPARED_REMARKS, HAS_FULL_TEXT, HAS_QA_SECTION, NEXT_EXCHANGE,
IN_CATEGORY (Report -> AdminReport), HAS_SUB_REPORT.

### Company Classification and Actions
BELONGS_TO, RELATED_TO (properties: relationship_type, source_ticker, target_ticker, bidirectional),
DECLARED_DIVIDEND, HAS_DIVIDEND, DECLARED_SPLIT, HAS_SPLIT, NEXT (Date -> Date).

### XBRL Graph
HAS_XBRL, REPORTS, HAS_CONCEPT, IN_CONTEXT, HAS_PERIOD, HAS_UNIT, FACT_MEMBER, FACT_DIMENSION,
HAS_DOMAIN, HAS_MEMBER, PARENT_OF, PRESENTATION_EDGE, CALCULATION_EDGE, FOR_COMPANY.

## Returns: What Lives Where (Validated Counts)

INFLUENCES returns depend on target label:
- **To Company**: total 190,593; daily_stock 188,806; daily_industry 190,363; daily_sector 190,593; daily_macro 190,593.
- **To Industry**: total 224,561; daily_industry 224,304; daily_stock 0.
- **To Sector**: total 224,540; daily_sector 224,540; daily_stock 0.
- **To MarketIndex**: total 224,540; daily_macro 224,540; daily_stock 0.

**Rule**: Use the Company-target INFLUENCES edge if you want both stock and benchmark returns on one relationship.

## Data Type Alerts and Anomalies (Validated)
- **Report.items** is JSON string. Example: `["Item 2.02: Results of Operations and Financial Condition", "Item 9.01: Financial Statements and Exhibits"]`.
- **News.channels** is JSON string. Example: `["News", "Guidance"]`.
- **Report.created** is ISO string with TZ. Example: `2023-01-04T13:48:33-05:00`.
- **Fact.value** is String even for numeric facts; use `toFloat` when `is_numeric='1'`.
- **is_numeric/is_nil** are string booleans ('0'/'1').
- **Dimension.is_explicit/is_typed** are string booleans ('0'/'1').
- **Unit.is_simple_unit/is_divide** are string booleans ('0'/'1').
- **Period.period_type** is String; `end_date='null'` appears for 2,776 instant periods.
- **NaN returns** exist. Use `WHERE r.daily_stock IS NOT NULL AND NOT isNaN(r.daily_stock)`.
- **hourly_stock** appears once as list-of-float on PRIMARY_FILER; handle list-or-float.
- **News anomaly**: 1,746 News->Company INFLUENCES edges have `daily_industry` but `daily_stock` is NULL.
- **Facts without context**: 12,939 Facts have no `IN_CONTEXT` edge.

## Data Inventory Query (Run First)

Before analyzing any 8-K, run this to know what data exists:

```cypher
MATCH (c:Company {ticker: $ticker})
OPTIONAL MATCH (r:Report {formType: '8-K'})-[:PRIMARY_FILER]->(c)
  WHERE r.items CONTAINS 'Item 2.02' AND r.created >= $start_date AND r.created <= $end_date
OPTIONAL MATCH (n:News)-[:INFLUENCES]->(c)
  WHERE n.created >= $start_date AND n.created <= $end_date
OPTIONAL MATCH (t:Transcript)-[:INFLUENCES]->(c)
  WHERE t.conference_datetime >= $start_date AND t.conference_datetime <= $end_date
OPTIONAL MATCH (xr:Report)-[:PRIMARY_FILER]->(c)
  WHERE xr.formType IN ['10-K', '10-Q']
OPTIONAL MATCH (c)-[:DECLARED_DIVIDEND]->(div:Dividend)
  WHERE div.declaration_date >= $start_date AND div.declaration_date <= $end_date
OPTIONAL MATCH (c)-[:DECLARED_SPLIT]->(sp:Split)
  WHERE sp.execution_date >= $start_date AND sp.execution_date <= $end_date
RETURN c.ticker, c.name,
       count(DISTINCT r) AS reports_8k,
       count(DISTINCT n) AS news_count,
       count(DISTINCT t) AS transcript_count,
       count(DISTINCT xr) AS xbrl_reports,
       count(DISTINCT div) AS dividends,
       count(DISTINCT sp) AS splits
```

## Query Cookbook (Copy/Paste)

### 1) Company by ticker
```cypher
MATCH (c:Company {ticker: $ticker})
RETURN c
```

### 2) Latest report for company
```cypher
MATCH (c:Company {ticker: $ticker})<-[:PRIMARY_FILER]-(r:Report)
RETURN r ORDER BY r.created DESC LIMIT 1
```

### 3) 8-K Item 2.02 filings for company
```cypher
MATCH (r:Report {formType: '8-K'})-[pf:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.items CONTAINS 'Item 2.02'
RETURN r.id, r.created, r.market_session,
       pf.daily_stock, pf.daily_macro,
       round((pf.daily_stock - pf.daily_macro) * 100) / 100 AS daily_adj
ORDER BY r.created DESC
```

### 4) Top earnings movers in date range
```cypher
MATCH (r:Report {formType: '8-K'})-[pf:PRIMARY_FILER]->(c:Company)
WHERE r.items CONTAINS 'Item 2.02'
  AND r.created >= $start_date AND r.created < $end_date
  AND pf.daily_stock IS NOT NULL AND NOT isNaN(pf.daily_stock)
RETURN c.ticker, r.id, r.created,
       round((pf.daily_stock - pf.daily_macro) * 100) / 100 AS daily_adj
ORDER BY abs(pf.daily_stock - pf.daily_macro) DESC
LIMIT 10
```

### 5) News around filing (with anomaly filter)
```cypher
MATCH (n:News)-[r:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.created >= $start_date AND n.created <= $end_date
  AND r.daily_stock IS NOT NULL AND NOT isNaN(r.daily_stock)
RETURN n.title, n.channels, n.created, r.daily_stock, r.daily_macro
ORDER BY n.created
```

### 6) News by channel
```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.channels CONTAINS 'Guidance'
RETURN n.title, n.created, n.channels
ORDER BY n.created DESC
```

### 7) Transcript and Q&A
```cypher
MATCH (t:Transcript)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE t.conference_datetime >= $start_date AND t.conference_datetime <= $end_date
RETURN t.id, t.conference_datetime

MATCH (t:Transcript {id: $transcript_id})-[:HAS_QA_EXCHANGE]->(qa:QAExchange)
RETURN qa.questioner, qa.questioner_title, qa.exchanges
ORDER BY toInteger(qa.sequence)
LIMIT 10
```

### 8) Press release (Exhibit EX-99.1)
```cypher
MATCH (r:Report {id: $accession_no})-[:HAS_EXHIBIT]->(e:ExhibitContent)
WHERE e.exhibit_number = 'EX-99.1'
RETURN e.content
```

### 9) Extracted sections (narrative)
```cypher
MATCH (r:Report {id: $accession_no})-[:HAS_SECTION]->(s:ExtractedSectionContent)
RETURN s.section_name, s.content
```

### 10) XBRL metrics (EPS and Revenue, context-safe)
```cypher
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType IN ['10-K','10-Q']
WITH r ORDER BY r.periodOfReport DESC LIMIT 1
MATCH (r)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
MATCH (f)-[:IN_CONTEXT]->(:Context)
MATCH (f)-[:HAS_CONCEPT]->(con:Concept)
WHERE con.qname IN [
  'us-gaap:EarningsPerShareDiluted',
  'us-gaap:EarningsPerShareBasic',
  'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax',
  'us-gaap:Revenues'
]
  AND f.is_numeric = '1'
RETURN con.qname, con.label, f.value, f.period_ref
```

### 11) XBRL total vs segmented values
```cypher
-- Total only (no dimensions)
MATCH (f:Fact)-[:HAS_CONCEPT]->(con:Concept)
WHERE con.label CONTAINS 'Revenue'
  AND f.is_numeric = '1'
  AND NOT EXISTS((f)-[:FACT_MEMBER]->())
RETURN con.label, f.value LIMIT 10

-- With dimensions
MATCH (f:Fact)-[:FACT_MEMBER]->(m:Member)
MATCH (f)-[:HAS_CONCEPT]->(con:Concept)
WHERE con.label CONTAINS 'Revenue'
  AND f.is_numeric = '1'
RETURN m.label, con.label, f.value LIMIT 10
```

### 12) Price series (OHLCV)
```cypher
MATCH (d:Date)-[p:HAS_PRICE]->(c:Company {ticker: $ticker})
WHERE d.date >= $start_date AND d.date <= $end_date
RETURN d.date, p.open, p.high, p.low, p.close, p.volume, p.daily_return
ORDER BY d.date
```

### 13) Dividends (around filing date)
```cypher
MATCH (c:Company {ticker: $ticker})-[:DECLARED_DIVIDEND]->(d:Dividend)
WHERE d.declaration_date >= $start_date AND d.declaration_date <= $end_date
RETURN d.declaration_date, d.cash_amount, d.dividend_type, d.frequency
ORDER BY d.declaration_date
```

### 14) Splits (around filing date)
```cypher
MATCH (c:Company {ticker: $ticker})-[:DECLARED_SPLIT]->(s:Split)
WHERE s.execution_date >= $start_date AND s.execution_date <= $end_date
RETURN s.execution_date, s.split_from, s.split_to
```

### 15) Fulltext search (News)
```cypher
CALL db.index.fulltext.queryNodes('news_ft', $query)
YIELD node, score
RETURN node.title, node.created, score
ORDER BY score DESC
LIMIT 20
```

### 16) Vector search (News or QAExchange)
```cypher
CALL db.index.vector.queryNodes('news_vector_index', $k, $embedding)
YIELD node, score
RETURN node.title, node.created, score
ORDER BY score DESC
```

## When to Use XBRL vs Non-XBRL
- **Need numeric metrics (EPS, revenue)**: Use XBRL (10-K/10-Q only).
- **Need narrative or 8-K**: Use ExtractedSectionContent or ExhibitContent.
- **8-K has no XBRL**: Use sections/exhibits instead.

## Indexes and Search Capabilities
- Range/unique indexes: `Report.id`, `News.id`, `Transcript.id`, `Company.id`.
- Fulltext: `abstract_ft` (Abstract.label), `concept_ft` (Concept.label/qname), `company_ft` (Company.name/displayLabel),
  `exhibit_content_ft` (ExhibitContent.content/exhibit_number), `extracted_section_content_ft` (ExtractedSectionContent.content/section_name),
  `fact_textblock_ft` (Fact.value/qname), `filing_text_content_ft` (FilingTextContent.content/form_type),
  `financial_statement_content_ft` (FinancialStatementContent.value/statement_type), `full_transcript_ft` (FullTranscriptText.content),
  `news_ft` (News.title/body/teaser), `prepared_remarks_ft` (PreparedRemark.content), `qa_exchange_ft` (QAExchange.exchanges),
  `question_answer_ft` (QuestionAnswer.content), `search` (Memory.name/type/observations).
- Vector: `news_vector_index` (News.embedding), `qaexchange_vector_idx` (QAExchange.embedding).
- No index on `Company.ticker`. Company count is small; exact match scans are acceptable.

**Generic fulltext query**:
```cypher
CALL db.index.fulltext.queryNodes($index_name, $query)
YIELD node, score
RETURN labels(node), node.id, score
ORDER BY score DESC
LIMIT 20
```

## Other Labels and Relationships Present (0 count)
**Labels**: AdminSection, FinancialStatement, Guidance, HyperCube, LineItems, Other, Memory, XBRLMapping, ExtractionPattern, ConceptMapping,
GeoMapping, ProductMapping, ConceptPattern, GeoPattern, MetricRule, GeoRule, Extraction, Pattern, NewsExtraction, TranscriptExtraction,
TestAbstract, TestFact, Framework, ConceptGroup, Benefit, Tutorial, LearningStep, ExampleApplication, _Bloom_Perspective_, _Bloom_Scene_,
TestNode, TestContentNode_1754141732.
**Relationships**: HAS_EXTRACTION, MAPS_TO_FACT, COULD_MAP_TO_REAL_FACT, POTENTIAL_XBRL_MATCH, TEST_REL, TEST_EDGE, REFERENCES, _Bloom_HAS_SCENE_.

## Advanced Patterns (Optional)
For deeper query libraries, see:
- /home/faisal/EventMarketDB/drivers/docs/XBRL_PATTERNS.md
- /home/faisal/EventMarketDB/drivers/docs/NON_XBRL_PATTERNS.md

## Validation Queries (Re-run if DB changes)
```cypher
CALL db.stats.retrieve('GRAPH COUNTS')

CALL apoc.meta.nodeTypeProperties({includeLabels: ['Report','Company','News','Transcript','Fact','Concept','XBRLNode']})
CALL apoc.meta.relTypeProperties({includeRels: ['PRIMARY_FILER','INFLUENCES','REFERENCED_IN','HAS_PRICE']})

MATCH (n:News)-[r:INFLUENCES]->(:Company)
WHERE r.daily_stock IS NULL AND r.daily_industry IS NOT NULL
RETURN count(r) AS news_anomaly_count

MATCH ()-[r:PRIMARY_FILER]->()
WHERE r.hourly_stock IS NOT NULL
RETURN apoc.meta.cypher.type(r.hourly_stock) as t, count(*) as c
```

*Version 3.2 | 2026-01-04 | Re-added query cookbook and validated XBRL/return anomalies*
