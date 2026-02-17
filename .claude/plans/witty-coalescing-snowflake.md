# Test Plan: All Completed Data Sub-Agents

## Context
7 data sub-agents are marked DONE. Need exhaustive testing of every query pattern in both PIT and open modes against the live Neo4j database to verify correctness.

## Test Strategy
1. **Direct MCP queries** — run every PIT query from each skill via `mcp__neo4j-cypher__read_neo4j_cypher` to verify they return data and correct envelope format
2. **Open mode queries** — run representative standard queries to verify full data access (no restrictions)
3. **Hook validation** — run pit_gate.py against sample PIT and open-mode responses to verify allow/block behavior
4. **Lint** — run `lint_data_agents.py` as structural compliance check
5. **Live agent tests** — spawn 2-3 agents via Task to test full stack (agent + hook + query)

## Test Ticker
Use `AAPL` (high data coverage across all domains). Fallback: `NOG`, `MSFT`.

## PIT Timestamp
Use `2025-06-01T00:00:00-04:00` — mid-2025, ensures data exists before cutoff.

---

## Tests by Agent

### 1. neo4j-news (5 PIT queries + open mode)

**PIT queries** (params: `{ticker: "AAPL", pit: "2025-06-01T00:00:00-04:00", start_date: "2025-01-01", channel: "Earnings"}`):
- [ ] News in Date Range (PIT) — verify data[], available_at <= pit, source = neo4j_created
- [ ] News by Channel (PIT) — verify channel filter works with envelope
- [ ] Fulltext News Search (PIT) — query = "earnings guidance", verify ft_score present
- [ ] News by Tag (PIT) — if exists
- [ ] Latest News (PIT) — verify LIMIT 1 still produces envelope

**Open mode** (no pit in params):
- [ ] News with INFLUENCES properties (daily_stock, hourly_stock, etc.) — verify forbidden keys ARE returned
- [ ] Fulltext search — verify works without envelope
- [ ] Count queries — verify basic data presence

**Verify**: No forbidden keys in PIT results. INFLUENCES properties present in open results.

### 2. neo4j-report (5 PIT queries + open mode)

**PIT queries** (params: `{ticker: "AAPL", pit: "2025-06-01T00:00:00-04:00", start_date: "2024-01-01"}`):
- [ ] Filings in Date Range (PIT) — verify accessionNo, formType in envelope
- [ ] 8-K Earnings Item 2.02 (PIT) — verify items CONTAINS filter works
- [ ] Fulltext Search Sections (PIT) — query = "revenue", verify section_name, content_preview
- [ ] Fulltext Search Exhibits (PIT) — query = "earnings", verify exhibit_number
- [ ] Latest Filing (PIT) — verify LIMIT 5 with envelope

**Open mode**:
- [ ] Reports with PRIMARY_FILER properties — verify daily_stock accessible
- [ ] Sections/exhibits content — verify full text access
- [ ] 10-K/10-Q filings — verify formType filter

**Verify**: edgar_accepted source tag. No PRIMARY_FILER return fields in PIT.

### 3. neo4j-transcript (4 PIT queries + open mode)

**PIT queries** (params: `{ticker: "AAPL", pit: "2025-06-01T00:00:00-04:00", start_date: "2024-01-01"}`):
- [ ] Transcripts in Date Range (PIT) — verify conference_datetime, fiscal_quarter
- [ ] Latest Transcript (PIT) — verify LIMIT 1 envelope
- [ ] Q&A for Transcript (PIT) — verify questioner (NOT speaker), responders, exchanges, sequence ordering
- [ ] Fulltext Search Q&A (PIT) — query = "margins", verify questioner field

**Open mode**:
- [ ] Transcript with INFLUENCES properties — verify daily_stock, session_stock accessible
- [ ] Q&A exchanges — verify questioner, questioner_title, responders fields
- [ ] Prepared remarks — verify content access

**Verify**: neo4j_created source. Field is `questioner` not `speaker`. No INFLUENCES properties in PIT.

### 4. neo4j-xbrl (3 PIT queries + open mode)

**PIT queries** (params: `{ticker: "AAPL", pit: "2025-06-01T00:00:00-04:00", concept_qname: "us-gaap:EarningsPerShareDiluted"}`):
- [ ] XBRL Metrics (PIT) — verify concept_qname, value, period fields
- [ ] Specific Metric (PIT) — verify EPS data with envelope
- [ ] Concept Search (PIT) — query = "Revenue", verify fulltext results

**Critical checks**:
- [ ] Verify `IN_CONTEXT` filter is present (line 333, 359)
- [ ] Verify `OPTIONAL MATCH (f)-[:HAS_PERIOD]->(p:Period)` — check if period_start/period_end are NULL or populated (this is the known HAS_PERIOD chain issue)
- [ ] Verify REPORTS relationship direction works
- [ ] Verify only 10-K/10-Q returned (no 8-K)

**Open mode**:
- [ ] XBRL metrics with context — verify toFloat works
- [ ] Segment breakdown — verify FACT_MEMBER pattern
- [ ] Facts with period details via IN_CONTEXT chain

**Verify**: edgar_accepted source. No PRIMARY_FILER returns in PIT. Period data behavior.

### 5. neo4j-entity (5 PIT queries + open mode)

**PIT queries** (params: `{ticker: "AAPL", pit: "2025-06-01T00:00:00-04:00", start_date: "2025-01-01"}`):
- [ ] Price Series (PIT) — verify market_close_current_day normalization produces valid ISO8601
- [ ] Price Series in Date Range (PIT) — verify date filtering + pit ceiling
- [ ] Latest Price (PIT) — verify LIMIT 1 with envelope
- [ ] Dividends (PIT) — verify Date JOIN + NULL filter, cash_amount, dividend_type
- [ ] Splits (PIT) — verify split_from, split_to

**Critical checks**:
- [ ] Verify available_at format: `YYYY-MM-DDTHH:MM:SS±HH:MM` (with colon in offset)
- [ ] Verify available_at_source = `time_series_timestamp`
- [ ] Verify no `daily_return` in PIT results
- [ ] Verify `d.market_close_current_day IS NOT NULL` filter excludes holidays

**Open mode** (NO pit in params — gateway allows as open):
- [ ] Company info — ticker, name, sector, mkt_cap
- [ ] Price series with daily_return — verify full HAS_PRICE properties
- [ ] Dividends without Date JOIN — verify all dividends accessible
- [ ] Sector/industry classification

**Verify**: time_series_timestamp source. Normalization produces valid timestamps. Company metadata works without pit.

### 6. neo4j-vector-search (2 PIT queries + open mode)

**PIT queries** (need embedding — use seed ID mode instead):
- [ ] News PIT envelope — use seed News ID, verify created <= pit
- [ ] QAExchange PIT envelope — use seed QA ID, verify conference_datetime <= pit

**Open mode**:
- [ ] News vector search — basic similarity
- [ ] QAExchange vector search — verify questioner, exchanges fields
- [ ] Cross-scope search — ticker-scoped vs unscoped

**Verify**: neo4j_created source. No INFLUENCES properties in PIT. Vector scores present.

### 7. bz-news-api (PIT + open via pit_fetch.py)

**PIT mode** (Bash with --pit flag):
- [ ] `pit_fetch.py --source bz-news-api --tickers AAPL --pit 2025-06-01T00:00:00-04:00 --lookback-minutes 43200`
- [ ] Verify envelope: data[], gaps[], available_at, available_at_source

**Open mode** (Bash without --pit):
- [ ] `pit_fetch.py --source bz-news-api --tickers AAPL --lookback-minutes 1440`
- [ ] Verify full data access, no filtering

**Verify**: provider_metadata source. Envelope format from wrapper.

---

## Cross-Cutting Checks

- [ ] **Lint pass**: `python3 .claude/skills/earnings-orchestrator/scripts/lint_data_agents.py` — must show PASS, 0 errors
- [ ] **Forbidden keys scan**: For every PIT result, grep for daily_stock, hourly_stock, session_stock, daily_return — must find NONE
- [ ] **available_at format**: Every PIT item must have full ISO8601+TZ (not date-only)
- [ ] **Empty envelope**: Test with impossible pit (e.g., `1990-01-01T00:00:00-05:00`) — must return `{"data":[], "gaps":[]}` and pass gate
- [ ] **Hook integration**: Spawn at least neo4j-news and neo4j-entity as Task agents with PIT params to verify full agent+hook stack

## Execution Order
1. Lint (fast sanity check)
2. All PIT queries per agent (bulk — parallel where possible)
3. All open mode queries per agent
4. Cross-cutting forbidden key scan on PIT results
5. Empty envelope edge case
6. 2-3 live agent spawns via Task

## Expected Outcome
Every query returns data (not empty when data exists), every PIT envelope is valid, every open query has full access. Zero blocked queries in open mode.
