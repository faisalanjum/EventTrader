# CCL: Price Data Gap & SEC Filings Ingested as Ghost News

**Created**: 2026-03-31
**Updated**: 2026-04-02
**Status**: Issue 1 FIXED (startup repair applied) · Issue 2 OPEN

**Discovered during**: Section 6 (Inter-Quarter Events) renderer testing
**Impact**: CCL inter-quarter context missing ~5 months of daily prices; predictor sees 13 duplicate ghost news rows per 425 filing batch

---

## Issue 1: Price Data Gap (Sep 2025 → Jan 2026)

**Status**: FIXED — startup date coverage reconciliation applied 2026-04-02

**Scope**: **All tickers** (not just CCL) had **zero price data** from 2025-09-03 to 2026-01-25 (~5 months). The Date nodes themselves did not exist — this was a whole-calendar gap, not a per-ticker issue.

| Boundary | Date | Close (CCL) |
|----------|------|-------------|
| Last price before gap | 2025-09-02 | $31.16 |
| First price after gap | 2026-01-26 | $28.67 |

### Root cause (proven)

The original bug report hypothesized "Polygon ingestion stopped or failed for CCL." Investigation proved the actual cause was deeper — a chain of three code defects:

1. **`is_initialized()` gates `create_dates()`** (`config/DataManagerCentral.py:723`): On restart, `is_initialized()` returns `true` (Company/Sector/etc. nodes exist), so the `else` branch containing `create_dates()` is **never executed**. Date nodes created during the offline period are simply never backfilled.

2. **`reconcile_date_nodes()` only creates yesterday** (`neograph/mixins/reconcile.py:331`): The live midnight reconciler only creates yesterday and day-before-yesterday. It has **no gap detection** — cannot discover or fill multi-day holes.

3. **The event trader was offline for ~5 months** (log evidence: `event_trader_20250824` → `event_trader_20260202`, no logs in between). When it restarted on 2026-02-02, defects #1 and #2 meant the Sep 3 → Jan 25 gap was never filled.

Additional findings:
- Multiple smaller date gaps also existed: Jul 24 → Aug 6, Aug 7 → Aug 22, Aug 23 → Aug 28 (sporadic operation before shutdown)
- 14 existing dates have exactly 500 HAS_PRICE relationships vs expected ~923 (partial prices from Polygon intersection logic)
- `is_trading_day` stored as STRING `"1"`/`"0"` in Neo4j (not boolean) due to `format_value()` in `Neo4jManager.py:498` treating Python `bool` as `int`
- `create_dates()` had a `skip_latest` batch boundary bug: default `skip_latest=True` dropped the last date of each 1000-date batch from price loading
- `create_dates()` did not create NEXT relationships across batch boundaries

### Fix applied (2026-04-02) — 3 edits

**Edit 1: `neograph/mixins/reconcile.py`** — Added `reconcile_full_date_coverage()`:
- Step 1: Generate all calendar days from 2023-01-01 to today
- Step 2: Query Neo4j for existing Date nodes, compute set difference
- Step 3: Create each missing date via `create_single_date()` (MERGE-based, includes prices via Polygon with `skip_latest=False`)
- Step 4: Bulk MERGE all consecutive NEXT relationships (repairs chain breaks)
- Step 5: Find zero-price historical trading days (using `coalesce(toString(d.is_trading_day), '') IN ['1', 'true', 'True']` to handle string storage), load prices for them
- Uses `today = end_date` (resolved once at method entry) for internal consistency

**Edit 2: `neograph/Neo4jInitializer.py`** — Fixed `create_dates()`:
- Added `prev_batch_last_node` tracking for cross-batch NEXT relationship linking
- Changed all `add_price_relationships_to_dates()` calls to pass `skip_latest=False`
- Pre-filters to trading days using Python `node.is_trading_day` bool (not Neo4j string)
- Removed unnecessary `len(batch) > 1` guard

**Edit 3: `config/DataManagerCentral.py`** — Startup hook:
- `reconcile_full_date_coverage(start_date="2023-01-01")` runs **after** the `is_initialized()` if/else block, so it executes on every startup regardless of initialization state
- `process_report_data()` consolidated to single call after reconciliation

### What this fix does NOT cover (by design)

- **Partial-price dates (500/923 HAS_PRICE)**: 14 existing dates have fewer prices than the current universe size. These are NOT re-processed because the per-date skip guard (`existing_count > 0`) correctly skips them — they reflect the universe and Polygon data available at load time. Re-pricing them on every startup would waste API calls for identical results.

- **Polygon intersection logic** (`eventReturns/polygonClass.py:781`): The line `common_symbols = df_latest.index.intersection(df_prev.index)` silently drops tickers missing from either day's Polygon response. This is the upstream cause of partial-price dates and remains a **separate fix** (Edit 5, designed but not applied — requires downstream `daily_return` NaN/null handling verification in `scripts/earnings/macro_snapshot.py:494,496`).

- **`format_value()` bool-to-string bug** (`Neo4jManager.py:498`): `is_trading_day` continues to be stored as `"1"`/`"0"`. The reconciliation works around this with `coalesce(toString(...))` in Cypher. Root-causing the format_value bug is separate.

### Validation queries

```cypher
-- Verify no date gaps remain (should return 0 rows)
MATCH (d:Date)
WHERE d.date >= '2023-01-01'
WITH d.date AS dt ORDER BY dt
WITH collect(dt) AS dates
UNWIND range(0, size(dates)-2) AS i
WITH dates[i] AS d1, dates[i+1] AS d2
WHERE date(d2) > date(d1) + duration('P3D')
RETURN d1 AS gap_start, d2 AS gap_end

-- Verify NEXT chain is continuous (should return 0 rows)
MATCH (d:Date)
WHERE d.date >= '2023-01-01'
WITH d ORDER BY d.date
WITH collect(d) AS dates
UNWIND range(0, size(dates)-2) AS i
WITH dates[i] AS d1, dates[i+1] AS d2
WHERE NOT EXISTS((d1)-[:NEXT]->(d2))
RETURN d1.date AS from_date, d2.date AS to_date

-- Verify zero-price trading days are filled
MATCH (d:Date)
WHERE d.date >= '2023-01-01' AND d.date < date()
  AND coalesce(toString(d.is_trading_day), '') IN ['1', 'true', 'True']
OPTIONAL MATCH (d)-[r:HAS_PRICE]->()
WITH d, count(r) AS cnt WHERE cnt = 0
RETURN d.date AS zero_price_date ORDER BY d.date
```

---

## Issue 2: SEC Filings Ingested as Ghost News Nodes

**Status**: OPEN — root cause proven, fix designed but not applied

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

### Root cause (proven)

The original report speculated "Benzinga API returns SEC filings as news." Codex investigation proved the actual cause is internal code misrouting:

1. **`DataManagerCentral.py:689-693`**: News source is commented out, only `reports` source is active. The Neo4j processor is built from the `reports` Redis client.

2. **`reconcile.py:39`**: The news reconciliation branch uses `self.event_trader_redis.source` (which resolves to `reports`) instead of hardcoding `news`. So it scans `reports:withreturns:*` / `reports:withoutreturns:*` keys.

3. **`reconcile.py:50`**: Blindly manufactures `news_id = f"bzNews_{base_id}"` from whatever it finds — including SEC accession numbers.

4. **`reconcile.py:99-100`**: Feeds report payloads into `_process_deduplicated_news()`, which tolerates missing title/url/channels and writes blank News nodes.

**The fix** (3 locations sharing the same namespace coupling bug):

| File | Line | Bug | Fix |
|------|------|-----|-----|
| `reconcile.py` | L39 | `self.event_trader_redis.source` → scans `reports:*` | Hardcode `RedisKeys.SOURCE_NEWS` |
| `pubsub.py` | L254 | Same source-coupling → subscribes to `reports:*` | Hardcode `news` namespace |
| `news.py` | L241 | Writes tracking metadata with wrong source namespace | Hardcode `SOURCE_NEWS` |

**Not yet applied** — fixing all 3 together as one commit is recommended to avoid partial namespace inconsistency.

### Validation queries

```cypher
-- Count ghost news nodes (should be 0 after fix)
MATCH (n:News)
WHERE n.title IS NULL OR n.title = ''
RETURN count(n) AS null_title_count,
       collect(DISTINCT substring(n.id, 0, 7)) AS id_prefixes

-- Cross-check with Reports
MATCH (n:News)
WHERE n.title IS NULL
WITH n, replace(n.id, 'bzNews_', '') AS possible_accession
MATCH (r:Report {accessionNo: possible_accession})
RETURN count(*) AS confirmed_duplicates
```

---

## Priority (updated)

**Issue 1 (price gap)**: ~~Medium~~ FIXED. Startup reconciliation permanently prevents future gaps. Partial-price upstream fix (Polygon intersection) is separate.

**Issue 2 (ghost news)**: Low-Medium. Root cause proven, fix designed (3 files), not yet applied. Cosmetic noise — predictor works around it but ghost rows dilute attention.
