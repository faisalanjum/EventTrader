# CCL: Price Data Gap & SEC Filings Ingested as Ghost News

**Created**: 2026-03-31
**Status**: OPEN
**Discovered during**: Section 6 (Inter-Quarter Events) renderer testing
**Impact**: CCL inter-quarter context missing ~5 months of daily prices; predictor sees 13 duplicate ghost news rows per 425 filing batch

---

## Issue 1: Price Data Gap (Sep 2025 → Jan 2026)

**Scope**: CCL has **zero price data** in Neo4j from 2025-09-03 to 2026-01-25 (~5 months).

| Boundary | Date | Close |
|----------|------|-------|
| Last price before gap | 2025-09-02 | $31.16 |
| First price after gap | 2026-01-26 | $28.67 |

**Data model**: Prices live on `(Date)-[:HAS_PRICE]->(Company)` relationship properties (close, open, high, low, volume, vwap, transactions, daily_return, timestamp).

**Root cause**: Polygon daily price ingestion stopped or failed for CCL during this period. The `HAS_PRICE` relationships simply don't exist for these dates. The Date nodes exist (they're shared across all companies), but no CCL-specific price relationship was created.

**Effect on renderer**: The builder marks these days as `is_trading_day: false` (no price data → no trading day). The renderer correctly shows `Trd=N` with all price/return columns as `—`. The summary reports fewer trading days than the actual market calendar.

**Effect on predictor**: Missing ~100 trading days of price trajectory between earnings. The predictor loses the cumulative return picture and significant move detection for that period. News events on those days still appear (with forward_returns from the INFLUENCES relationship), but there's no day-level context.

**Fix**: Re-run Polygon daily price ingestion for CCL covering 2025-09-03 to 2026-01-25. Check if other tickers have similar gaps.

**Validation query**:
```cypher
MATCH (d:Date)-[rel:HAS_PRICE]->(c:Company {ticker: 'CCL'})
RETURN min(d.date) AS earliest, max(d.date) AS latest, count(*) AS cnt
```
Expected after fix: continuous daily coverage with no multi-day gaps (excluding weekends/holidays).

---

## Issue 2: SEC Filings Ingested as Ghost News Nodes

**Scope**: 13 Form 425 (merger prospectus) filings on 2025-12-19 appear as **both** Report nodes and News nodes in Neo4j. The News nodes have null titles, empty channels, empty URLs, and empty authors.

**The smoking gun — IDs match exactly**:

```
News ID:   bzNews_0001104659-25-123226    created: 2025-12-19T16:44:14
Report ID:        0001104659-25-123226    created: 2025-12-19T16:44:14

News ID:   bzNews_0001104659-25-123231    created: 2025-12-19T16:45:33
Report ID:        0001104659-25-123231    created: 2025-12-19T16:45:33

News ID:   bzNews_0001104659-25-123233    created: 2025-12-19T16:46:58
Report ID:        0001104659-25-123233    created: 2025-12-19T16:46:58
```

All 13 pairs follow this pattern: the News node ID is `bzNews_` + the exact SEC accession number. Same timestamps to the second.

**Root cause**: The Benzinga news ingestion pipeline is creating News nodes from SEC EDGAR filings. Either:
- Benzinga's API returns SEC filings as "news" items (Benzinga does serve SEC filings), and the ingestion pipeline stores them as News nodes without extracting the title/channels
- Or the ingestion pipeline directly creates News nodes from EDGAR data, prepending `bzNews_` to the accession number as the ID

**Context**: These are Form 425 filings related to the Carnival Corp / Carnival Plc unification (see news N36 in the rendered output: "Carnival Entered Into Unification Agreement; To Unify Carnival Corporation And Carnival Plc Under Single Company Structure"). Form 425 is a merger-related prospectus filing.

**Effect on renderer**: The renderer correctly shows `—` for null titles and empty channels. No crash, no broken tables.

**Effect on predictor**: The predictor sees 13 ghost news rows (N1-N13) that are content-free duplicates of the 13 filing rows (F1-F13). Each ghost row shows `— | — | {adj_returns}` — no title, no channels, just adjusted returns identical to the corresponding filing. This is noise that wastes predictor attention without adding any signal.

**Also observed**: Additional null-title news events on other dates (N29 on 2026-01-27, N33 on 2026-02-12, N35 on 2026-02-20). These may be the same pattern — SEC filings ingested as Benzinga news. The N35 event on 2026-02-20 corresponds to the unification agreement 8-K.

**Fix**: In the Benzinga news ingestion pipeline:
1. Skip or deduplicate news items whose ID matches a known SEC accession pattern (`bzNews_{accession}`)
2. Or filter out news items with null/empty title at ingestion time
3. Or add a post-ingestion cleanup that removes News nodes where `n.id STARTS WITH 'bzNews_' AND n.title IS NULL`

**Validation query**:
```cypher
MATCH (n:News)
WHERE n.title IS NULL OR n.title = ''
RETURN count(n) AS null_title_count,
       collect(DISTINCT substring(n.id, 0, 7)) AS id_prefixes
```

**Validation query (cross-check with Reports)**:
```cypher
MATCH (n:News)
WHERE n.title IS NULL
WITH n, replace(n.id, 'bzNews_', '') AS possible_accession
MATCH (r:Report {accessionNo: possible_accession})
RETURN count(*) AS confirmed_duplicates
```

---

## Priority

**Issue 1 (price gap)**: Medium. Affects CCL prediction quality. Check other tickers for similar gaps.

**Issue 2 (ghost news)**: Low-Medium. Cosmetic noise in the rendered bundle. The predictor can work around empty-title rows but they dilute attention. Fix prevents the pattern from recurring for future merger/unification filings.
