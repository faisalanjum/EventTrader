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

**Status**: OPEN — root cause proven, fix designed (4 lines in 3 files), not yet applied
**Updated**: 2026-04-02

### Scope (revised — much larger than originally reported)

| Metric | Original report | Deep investigation (2026-04-02) |
|--------|----------------|--------------------------------|
| Ghost News nodes | 13 (CCL Form 425s) | **6,693** |
| Date range | 2025-12-19 only | **2025-08-25 → 2026-03-27** (ongoing) |
| Have INFLUENCES rels? | Not checked | **Yes — with real return data** (e.g., FMC -46.52%) |
| Titles | Assumed NULL | **Empty string `''`** (not NULL) |
| Monthly rate | — | ~700-1,700 new ghosts/month |

Monthly distribution:
```
2025-08:   34  |  2025-09:  462  |  2025-10: 1,144  |  2025-11: 1,277
2025-12:  685  |  2026-01:  673  |  2026-02: 1,680  |  2026-03:   738
```

**Impact on predictor**: Ghost News nodes have INFLUENCES relationships with real return data (extracted from the report payload). The predictor sees these as separate "news events" with significant returns — e.g., an FMC SEC filing appears as a ghost news event with -46.52% daily return. This actively pollutes the prediction signal, not just cosmetic noise.

### Root cause (proven, verified against live code 2026-04-02)

The news reconciliation code uses `self.event_trader_redis.source` (which is `'reports'` when news source is disabled) instead of hardcoding `RedisKeys.SOURCE_NEWS`. This causes it to scan report keys and create ghost News nodes from SEC filings.

**The active bug path** (`reconcile.py:37-112`):
```
reconcile.py:39  — scan pattern: reports:withreturns:* (should be news:*)
  ↓
reconcile.py:50  — manufacture: bzNews_{SEC_accession_number}
  ↓
reconcile.py:61  — check Neo4j: News node doesn't exist → process it
  ↓
reconcile.py:73  — guard check: tracking:meta:news:... → not found (metadata was
                   written to tracking:meta:reports:... by Bug #3) → guard fails
  ↓
reconcile.py:95  — read data: reports:withreturns:{id} (should be news:*)
  ↓
reconcile.py:100 — call _process_deduplicated_news(bzNews_{accession}, report_json)
  ↓
news.py:172      — _create_news_node_from_data: title='' (report has no title field)
  ↓
news.py:182      — _prepare_entity_relationship_params: extracts symbols + returns from report
  ↓
news.py:257      — MERGE News node + INFLUENCES relationships with real return data
  ↓
news.py:241      — write metadata to tracking:meta:reports:... (Bug #3 — wrong namespace)
```

**Three namespace coupling bugs:**

1. **`reconcile.py:39`** — scan pattern uses `self.event_trader_redis.source` ('reports') → scans `reports:withreturns:*` instead of `news:withreturns:*`. **This is the active bug creating ghosts.**

2. **`reconcile.py:95`** — data read key uses `self.event_trader_redis.source` ('reports') → reads report payloads and feeds them to `_process_deduplicated_news()`. **Must be fixed together with line 39.**

3. **`news.py:241`** — metadata write uses `self.event_trader_redis.source` ('reports') → writes to `tracking:meta:reports:...` instead of `tracking:meta:news:...`. **Breaks the dedup guard** at `reconcile.py:73` which checks `tracking:meta:news:...`.

4. **`pubsub.py:254`** — news subscription uses `self.event_trader_redis.source` ('reports') → subscribes to `reports:*` channels instead of `news:*`. **Dormant bug**: the handler routing at `pubsub.py:305` uses hardcoded `RedisKeys.SOURCE_NEWS` prefix check, so messages are correctly routed to report processing. Real impact: if news source is re-enabled, real-time news PubSub won't work.

**Verified NOT creating ghosts:**
- `pubsub.py:305-310` — handler routing is hardcoded to `SOURCE_NEWS`/`SOURCE_REPORTS`, correctly routes regardless of subscription bug
- `news.py:42` — `process_news_to_neo4j()` hardcodes `"news:withreturns:*"`, only processes actual news keys
- Report reconciliation (section 2, line 114+) — separate code, uses its own hardcoded `SOURCE_REPORTS`

### Fix (4 lines in 3 files + cleanup)

| File | Line | Old | New |
|------|------|-----|-----|
| `reconcile.py` | 39 | `self.event_trader_redis.source` | `RedisKeys.SOURCE_NEWS` |
| `reconcile.py` | 95 | `self.event_trader_redis.source` | `RedisKeys.SOURCE_NEWS` |
| `news.py` | 241 | `self.event_trader_redis.source` | `RedisKeys.SOURCE_NEWS` |
| `pubsub.py` | 254 | `self.event_trader_redis.source` | `RedisKeys.SOURCE_NEWS` |

**Cleanup** (run after code fix, one-time):
```cypher
-- Delete 6,693 ghost News nodes + their INFLUENCES relationships
-- Pattern matches SEC accession format (10-2-6 digits), never matches Benzinga numeric IDs
MATCH (n:News)
WHERE n.title = '' AND n.id =~ 'bzNews_\\d{10}-\\d{2}-\\d{6}'
DETACH DELETE n
RETURN count(n) AS deleted
```

### Regression risk: zero

- `reconcile.py:39,95` → scans `news:*` keys. News source disabled → finds nothing → no ghost creation. When re-enabled, correctly processes news.
- `news.py:241` → metadata in correct namespace → dedup guard at line 73 works correctly.
- `pubsub.py:254` → subscribes to `news:*` channels. News disabled → no messages. Correct when re-enabled.
- Cleanup regex `\d{10}-\d{2}-\d{6}` only matches SEC accession IDs, never legitimate 8-digit Benzinga news IDs.
- Report reconciliation (section 2) untouched.
- No Report nodes are deleted or modified.

### Validation queries

```cypher
-- Verify zero ghost news remain (should return 0 after cleanup)
MATCH (n:News)
WHERE n.title = '' AND n.id =~ 'bzNews_\\d{10}-\\d{2}-\\d{6}'
RETURN count(n) AS ghost_count

-- Verify legitimate news unaffected
MATCH (n:News)
WHERE n.title <> '' AND n.title IS NOT NULL
RETURN count(n) AS legitimate_news_count

-- Verify no new ghosts created after fix (run after next reconciliation cycle)
MATCH (n:News)
WHERE n.title = ''
RETURN count(n) AS new_ghosts
```

---

## Priority (updated)

**Issue 1 (price gap)**: FIXED (2026-04-02). Startup reconciliation fills missing dates. Atomic per-date writes prevent new partial dates. 14 legacy 500-count dates repaired. Indexed entity lookups eliminate AllNodesScan bottleneck.

**Issue 2 (ghost news)**: ~~Low-Medium~~ **Medium-High**. 6,693 ghost News nodes with real INFLUENCES return data actively pollute the prediction signal. Fix is 4 lines + one-time cleanup. Not yet applied.
