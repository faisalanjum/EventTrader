# Comprehensive Test Plan: All 7 PIT-Complete Data Sub-Agents

## Context

Phase 3 of DataSubAgents rollout is complete — 7 agents now have full PIT gating. Before moving to Phase 4, we need absolute certainty that every agent works correctly in both open mode (live trading) and PIT mode (backtesting), across every query category, every node/relationship type, and every known edge case. **This is a read-only test pass — zero code changes.**

## Scope

**7 Agents**: neo4j-news, neo4j-vector-search, neo4j-report, neo4j-transcript, neo4j-xbrl, neo4j-entity, bz-news-api

**2 Modes**: Open (no PIT — live trading) and PIT (with datetime boundary — backtesting)

**Test Parameters**:
- Reference ticker: `AAPL` (guaranteed coverage across all data types)
- Date range: `2024-01-01` to `2025-06-30`
- PIT timestamp: `2025-06-15T16:00:00-04:00` (EDT market close)
- Secondary tickers as needed: `SPY` (MarketIndex), any ticker with splits

---

## Phase 0: Infrastructure Validation (existing test suites)

Run 3 existing test suites — zero code changes:

| ID | Command | Expected |
|----|---------|----------|
| T0.1 | `python3 .claude/hooks/test_pit_gate.py` | 37/37 pass, exit 0 |
| T0.2 | `python3 .claude/skills/earnings-orchestrator/scripts/test_pit_fetch.py` | 6/6 pass, exit 0 |
| T0.3 | `python3 .claude/skills/earnings-orchestrator/scripts/lint_data_agents.py` | PASS, 0 errors, >=7 agents |

---

## Phase 1: Schema & Data Inventory (5 queries)

Verify database structure and baseline counts via `mcp__neo4j-cypher__read_neo4j_cypher`:

| ID | What | Pass Criteria |
|----|------|--------------|
| T1.1 | Node label counts (`MATCH (n) WITH labels(n)...`) | All expected labels present: Company ~796, News ~186K, Report ~33K, Transcript ~4387, Date ~946, Dividend ~4282, Split ~33, Sector ~11, Industry ~115, MarketIndex 1 |
| T1.2 | Relationship type counts | All expected rels present: INFLUENCES, HAS_PRICE, PRIMARY_FILER, HAS_SECTION, HAS_EXHIBIT, HAS_XBRL, REPORTS, HAS_CONCEPT, IN_CONTEXT, HAS_PERIOD, BELONGS_TO, DECLARED_DIVIDEND, HAS_DIVIDEND, DECLARED_SPLIT, HAS_SPLIT, HAS_QA_EXCHANGE, HAS_PREPARED_REMARKS, HAS_FULL_TEXT, NEXT_EXCHANGE, NEXT, FACT_MEMBER, FACT_DIMENSION, REFERENCED_IN |
| T1.3 | Data inventory for AAPL (news, reports, transcripts, XBRL, dividends) | All counts > 0 |
| T1.4 | `SHOW FULLTEXT INDEXES` | All 9 agent-used indexes ONLINE: news_ft, qa_exchange_ft, prepared_remarks_ft, full_transcript_ft, concept_ft, fact_textblock_ft, exhibit_content_ft, extracted_section_content_ft, financial_statement_content_ft |
| T1.5 | `SHOW VECTOR INDEXES` | Both ONLINE: news_vector_index (3072D), qaexchange_vector_idx (3072D) |

---

## Phase 2: Open-Mode Query Coverage (~40 queries)

One query per distinct category from each agent's skill. No PIT parameter. Verify data returns correctly with INFLUENCES/return properties included where applicable.

### neo4j-news (8 queries)
| ID | Category | Key Verification |
|----|----------|-----------------|
| T2.1.1 | News for company in date range | Rows with id, title, created |
| T2.1.2 | News by channel filter | channels CONTAINS filter works |
| T2.1.3 | Fulltext: news_ft | Score > 0, index functional |
| T2.1.4 | News with stock returns (INFLUENCES props) | daily_stock, daily_macro numeric |
| T2.1.5 | INFLUENCES -> Industry | daily_industry populated |
| T2.1.6 | INFLUENCES -> Sector | daily_sector populated |
| T2.1.7 | INFLUENCES -> MarketIndex (SPY) | daily_macro populated |
| T2.1.8 | Cross-domain: News around earnings call | HAS_TRANSCRIPT as date anchor |

### neo4j-vector-search (3 queries)
| ID | Category | Key Verification |
|----|----------|-----------------|
| T2.2.1 | News vector search (ID-based, Mode B) | news_vector_index, score >= 0.70 |
| T2.2.2 | QAExchange vector search (ID-based) | qaexchange_vector_idx, score >= 0.70 |
| T2.2.3 | Sector-scoped vector search | Sector filter on vector results |

### neo4j-report (9 queries)
| ID | Category | Key Verification |
|----|----------|-----------------|
| T2.3.1 | Reports by form type (8-K) | formType, items fields |
| T2.3.2 | 8-K Item 2.02 with PRIMARY_FILER returns | daily_stock, daily_macro numeric |
| T2.3.3 | Exhibit EX-99.1 content | HAS_EXHIBIT -> ExhibitContent |
| T2.3.4 | Extracted sections | HAS_SECTION -> ExtractedSectionContent |
| T2.3.5 | Financial statement content | HAS_FINANCIAL_STATEMENT -> FinancialStatementContent |
| T2.3.6 | Filing text content | HAS_FILING_TEXT -> FilingTextContent |
| T2.3.7 | Fulltext: extracted_section_content_ft | Score > 0 |
| T2.3.8 | Fulltext: exhibit_content_ft | Score > 0 |
| T2.3.9 | Fulltext: financial_statement_content_ft | Score > 0 |

### neo4j-transcript (9 queries)
| ID | Category | Key Verification |
|----|----------|-----------------|
| T2.4.1 | Transcripts for company (INFLUENCES) | conference_datetime, fiscal fields |
| T2.4.2 | Q&A exchanges (HAS_QA_EXCHANGE) | sequence as String, exchanges non-empty |
| T2.4.3 | Prepared remarks (HAS_PREPARED_REMARKS) | PreparedRemark.content non-empty |
| T2.4.4 | Full transcript text (HAS_FULL_TEXT) | FullTranscriptText.content |
| T2.4.5 | Fulltext: qa_exchange_ft | Score > 0 |
| T2.4.6 | Fulltext: prepared_remarks_ft | Score > 0 |
| T2.4.7 | Fulltext: full_transcript_ft | Score > 0 |
| T2.4.8 | NEXT_EXCHANGE chain | >= 2 exchanges in chain |
| T2.4.9 | Transcript INFLUENCES returns | daily_stock, session_stock |

### neo4j-xbrl (7 queries)
| ID | Category | Key Verification |
|----|----------|-----------------|
| T2.5.1 | Metrics (EPS/Revenue) context-safe | HAS_XBRL, REPORTS, IN_CONTEXT, HAS_CONCEPT chain |
| T2.5.2 | Total only (no FACT_MEMBER) | NOT EXISTS filter works |
| T2.5.3 | Segmented with dimensions | FACT_MEMBER, FACT_DIMENSION, Member, Dimension |
| T2.5.4 | Context + Period details | IN_CONTEXT -> Context -> HAS_PERIOD -> Period |
| T2.5.5 | Fulltext: concept_ft | Concept search works |
| T2.5.6 | Fulltext: fact_textblock_ft | Text block facts found |
| T2.5.7 | FOR_COMPANY relationship | XBRLNode -> Company link |

### neo4j-entity (11 queries)
| ID | Category | Key Verification |
|----|----------|-----------------|
| T2.6.1 | Company classification (BELONGS_TO chain) | Industry -> Sector -> MarketIndex |
| T2.6.2 | Price series (HAS_PRICE -> Company) | OHLCV data, daily_return |
| T2.6.3 | Price series (HAS_PRICE -> MarketIndex SPY) | SPY prices |
| T2.6.4 | Price series (HAS_PRICE -> Sector) | Sector prices |
| T2.6.5 | Dividends (DECLARED_DIVIDEND) | Dividend properties |
| T2.6.6 | Dividends via Date (HAS_DIVIDEND) | Date -> Dividend chain |
| T2.6.7 | Splits (DECLARED_SPLIT) | Split properties |
| T2.6.8 | Splits via Date (HAS_SPLIT) | Date -> Split chain |
| T2.6.9 | Date properties + trading calendar | market_close_current_day non-null for trading days |
| T2.6.10 | NEXT relationship (Date chain) | Calendar adjacency works |
| T2.6.11 | RELATED_TO relationship | Cross-company links |

### bz-news-api (2 queries)
| ID | Category | Key Verification |
|----|----------|-----------------|
| T2.7.1 | Ticker + date range (open mode) | JSON envelope, data[] array |
| T2.7.2 | Theme + channel filter | Macro-themed results |

---

## Phase 3: PIT-Mode Envelope Coverage (~15 queries)

Run PIT-safe envelope queries from each skill with `pit: '2025-06-15T16:00:00-04:00'` in params. Validate each result against pit_gate.py expectations.

### Validation criteria for ALL PIT tests:
- Envelope has `data[]` array and `gaps[]` array
- Every item in `data[]` has `available_at` (full ISO8601 + tz) and `available_at_source` (valid value)
- Every `available_at <= pit` (no future data leaks)
- Zero forbidden keys: daily_stock, hourly_stock, session_stock, daily_return, daily_macro, daily_industry, daily_sector, hourly_macro, hourly_industry, hourly_sector

### neo4j-news PIT (3 queries)
| ID | Envelope Source | available_at_source |
|----|----------------|---------------------|
| T3.1.1 | News date range, `n.created <= $pit` | neo4j_created |
| T3.1.2 | News channel filter + PIT | neo4j_created |
| T3.1.3 | Fulltext news_ft + PIT | neo4j_created |

### neo4j-vector-search PIT (2 queries)
| ID | Envelope Source | available_at_source |
|----|----------------|---------------------|
| T3.2.1 | News vector + `node.created <= $pit` | neo4j_created |
| T3.2.2 | QA vector + `t.conference_datetime <= $pit` | neo4j_created |

### neo4j-report PIT (4 queries)
| ID | Envelope Source | available_at_source |
|----|----------------|---------------------|
| T3.3.1 | Filings date range, `r.created <= $pit` | edgar_accepted |
| T3.3.2 | 8-K Item 2.02 + PIT | edgar_accepted |
| T3.3.3 | Fulltext sections + PIT | edgar_accepted |
| T3.3.4 | Fulltext exhibits + PIT | edgar_accepted |

### neo4j-transcript PIT (3 queries)
| ID | Envelope Source | available_at_source |
|----|----------------|---------------------|
| T3.4.1 | Transcripts, `t.conference_datetime <= $pit` | neo4j_created |
| T3.4.2 | Q&A for latest transcript + PIT | neo4j_created |
| T3.4.3 | Fulltext Q&A + PIT | neo4j_created |

### neo4j-xbrl PIT (2 queries)
| ID | Envelope Source | available_at_source |
|----|----------------|---------------------|
| T3.5.1 | XBRL metrics, parent `r.created <= $pit` | edgar_accepted |
| T3.5.2 | Concept search + PIT | edgar_accepted |

### neo4j-entity PIT (4 queries)
| ID | Envelope Source | available_at_source |
|----|----------------|---------------------|
| T3.6.1 | Price series, `norm_close <= $pit` (2-step normalization) | time_series_timestamp |
| T3.6.2 | Dividends via Date + PIT | time_series_timestamp |
| T3.6.3 | Splits via Date + PIT | time_series_timestamp |
| T3.6.4 | Company metadata (NO pit in params — open mode pass-through) | N/A (open mode) |

### bz-news-api PIT (1 query)
| ID | Envelope Source | available_at_source |
|----|----------------|---------------------|
| T3.7.1 | pit_fetch.py `--pit` flag | provider_metadata |

---

## Phase 4: Edge Cases & Data Anomalies (14 tests)

| ID | Edge Case | Expected |
|----|-----------|----------|
| T4.1 | NaN on INFLUENCES (daily_stock) | >= 1 row with isNaN |
| T4.2 | NaN on PRIMARY_FILER | >= 1 row (documented: 4) |
| T4.3 | NULL market_close_current_day on trading days | Rows exist (21 holidays) |
| T4.4 | Orphan dividends (no Date link) | >= 1 row (documented: 44) |
| T4.5 | XBRL Facts without Context (IN_CONTEXT) | Count ~12,939 |
| T4.6 | Period end_date = string 'null' | Count ~2,776 |
| T4.7 | hourly_stock as LIST type on PRIMARY_FILER | Type check (may need apoc) |
| T4.8 | Gate rejects forbidden key (daily_stock in PIT envelope) | BLOCK PIT_FORBIDDEN_FIELD |
| T4.9 | Gate rejects future available_at | BLOCK PIT_VIOLATION_GT_CUTOFF |
| T4.10 | Gate allows empty data[] (clean gap) | ALLOW |
| T4.11 | Gate rejects missing available_at_source | BLOCK PIT_INVALID_AVAILABLE_AT_SOURCE |
| T4.12 | XBRL comma-formatted values (toFloat edge) | Value contains commas |
| T4.13 | Transcript INFLUENCES: daily_stock NULL but daily_industry present | >= 1 row |
| T4.14 | News INFLUENCES: daily_stock NULL but daily_industry present | >= 1 row |

---

## Phase 5: Cross-Agent Integration (5 tests)

| ID | What | Pass Criteria |
|----|------|---------------|
| T5.1 | Same-day coverage: Report + News + Transcript for AAPL | same_day_news > 0 for an 8-K Item 2.02 date |
| T5.2 | Full XBRL chain: Company <- PRIMARY_FILER - Report - HAS_XBRL -> XBRLNode <- REPORTS - Fact - HAS_CONCEPT -> Concept; Fact - IN_CONTEXT -> Context - HAS_PERIOD -> Period | All fields non-null (except instant period end_date) |
| T5.3 | All 4 available_at_source values exercised | neo4j_created, edgar_accepted, time_series_timestamp, provider_metadata all used in Phase 3 |
| T5.4 | All 10 forbidden keys exist on INFLUENCES relationship | Verify complete coverage |
| T5.5 | REFERENCED_IN relationship count | ~1,075 |

---

## Execution Strategy

**All testing via MCP tool + Bash — zero code changes, zero file edits.**

1. Phase 0: Run 3 Bash commands (existing test suites)
2. Phase 1-5: Run Cypher queries via `mcp__neo4j-cypher__read_neo4j_cypher` MCP tool
3. PIT gate tests (T4.8-T4.11): Construct synthetic payloads and validate behavior
4. bz-news-api tests: Run pit_fetch.py via Bash
5. Use parallel Task agents where independent (e.g., Phase 2 agents in parallel)

**Total: ~82 tests across 6 phases**

## Coverage Matrix

| Dimension | Coverage |
|-----------|----------|
| Node types | 22/22 (Company, News, Report, Transcript, QAExchange, XBRLNode, Fact, Concept, Context, Period, Date, Dividend, Split, Sector, Industry, MarketIndex, PreparedRemark, FullTranscriptText, ExhibitContent, ExtractedSectionContent, FinancialStatementContent, FilingTextContent) |
| Relationship types | 23/23 (all documented types) |
| Fulltext indexes | 9/9 |
| Vector indexes | 2/2 |
| Agents | 7/7 |
| Open mode | 7/7 agents tested |
| PIT mode | 7/7 agents tested |
| available_at_source values | 4/4 |
| Forbidden keys | 10/10 verified |
| Known edge cases | 14 specific anomalies tested |
