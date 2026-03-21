# Fiscal Math Fix — Implementation Plan (v5)

**Created**: 2026-03-21
**Status**: Ready to implement
**Parent**: `fiscal-math-issues.md` (investigation & validation), `GuidanceTrigger.md` (daemon architecture)

---

## Summary

Fix guidance period resolution in `_ensure_period()` (`guidance_write_cli.py:78`) to produce correct fiscal quarter/annual calendar dates for ~41-44 affected tickers (currently off by ~28 days). Adds SEC EDGAR exact-date lookup and fiscal-identity dedup BEFORE the existing `build_guidance_period_id()` call, which itself remains unchanged.

**Strategy (in this order for dedup correctness)**:
1. Existing period reuse (first-write-wins via Neo4j fiscal-identity lookup)
2. SEC cache exact dates (for filed quarters/annuals)
3. [Optional] Predict from previous quarter end + historical length (±1d vs ±3-5d, zero functional impact)
4. Corrected FYE month-boundary math with SEC-corrected FYE (last resort)

The order matters: Step 1 MUST run before Step 2, otherwise a later SEC-exact lookup could bypass an already-written period and recreate the duplicate problem.

**Minimal vs full implementation**: Without optional Step 3, the plan is ~315 lines across 6 files. With Step 3: ~355 lines. Step 3 improves unfiled-quarter accuracy from ±3-5d to ±1d but has zero impact on the earnings orchestrator (queries by ticker, not date range). Recommended: implement without Step 3 first, add later if a consumer needs ±1d.

**Key design decisions**:
- First-write-wins: once a GuidancePeriod is created for a (ticker, FY, quarter), all subsequent extractions reuse it — zero duplicates
- SEC cache refresh driven by the guidance trigger daemon (asset-aware), not by age-based TTL
- ACTIVE_WINDOW_DAYS must be 45 (not 1) to cover the 40-day 10-Q filing window
- SEC inclusive end-date convention (industry standard)
- All new steps are additive short-circuits — if they all miss, the original code path runs unchanged

---

## Files to Change (6 required + 1 optional)

| File | Type | Lines | What |
|---|---|---|---|
| `scripts/sec_quarter_cache_loader.py` | **NEW** | ~200 | Bootstrap + manual SEC cache refresh |
| `scripts/guidance_trigger_daemon.py` | **MODIFY** | ~30 | Asset-aware SEC cache refresh on enqueue |
| `k8s/processing/guidance-trigger.yaml` | **MODIFY** | 1 line | `ACTIVE_WINDOW_DAYS: "1"` → `"45"` |
| `guidance_write_cli.py` | **MODIFY** | ~35 (or ~55 with optional Step C) | Thread ticker, lazy Neo4j/Redis, fiscal-identity lookup, SEC cache, corrected FYE fallback. Optional: prediction from prev Q. |
| Migration script | **NEW** | ~60 | Rekey GuidanceUpdate.id + re-point HAS_PERIOD + collision preflight |
| `scripts/trigger-extract.py` | **MODIFY** | ~10 | SEC cache prefetch for manual runs (after find, before queue) |
| `scripts/trade_ready_scanner.py` | **OPTIONAL** | ~25 | Prewarm SEC cache on TradeReady entry |
| **Total** | | **~375** | **~8-10 hours** |

---

## File 1: `scripts/sec_quarter_cache_loader.py` (~200 lines, NEW)

**Purpose**: Bootstrap + manual refresh of SEC quarter cache in Redis.

**What it does**:
1. Download `https://www.sec.gov/files/company_tickers.json` → ticker→CIK map
   - Fallback: query `Company.cik` from Neo4j for ~33 tickers missing from SEC lookup
2. For each ticker (or `--ticker FIVE` for single):
   - GET `https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/EarningsPerShareBasic.json`
   - Fallback concept: `NetIncomeLoss` (~10 tickers without EPS)
3. Filter BOTH quarterly AND annual:
   - `fp in ['Q1','Q2','Q3']` with span 60-130d → quarterly cache
     (Note: SEC XBRL has no `fp='Q4'` — Q4 results are in the 10-K which uses `fp='FY'`.
      Q4 standalone dates are derived: Q4.start = Q3.end + 1d, Q4.end = FY.end.
      The loader should compute and cache Q4 from this derivation.)
   - `fp = 'FY'` with span 300-400d → annual cache
   - Deduplicate by `(fy, fp)`: keep latest `filed` date (handles amendments)
4. Write to Redis:
   ```
   fiscal_quarter:{TICKER}:{FY}:Q{N} → {"start":"2024-02-04","end":"2024-05-04"}  (inclusive end)
   fiscal_quarter:{TICKER}:{FY}:FY   → {"start":"2024-02-04","end":"2025-02-01"}  (annual)
   # fiscal_quarter_length keys — PHASE 2 only (for Step C prediction)
   # fiscal_quarter_length:{TICKER}:Q{N} → 91  (median span across all FYs)
   fiscal_year_end:{TICKER} → {"raw":"0201","month_adj":1}  (SEC fiscalYearEnd, day<=5 adjusted)
   fiscal_quarter:{TICKER}:last_refreshed → timestamp (no TTL — daemon manages freshness)
   ```
5. Also fetch `https://data.sec.gov/submissions/CIK{cik}.json` → `fiscalYearEnd` field
   - Apply day<=5 adjustment: if DD <= 5, `month_adj = MM - 1` (with Dec wrap)

**Exports** a `refresh_ticker(redis_client, ticker)` function that the daemon and trigger-extract can call.

**CLI**:
```bash
python3 sec_quarter_cache_loader.py              # all tickers (~90 sec)
python3 sec_quarter_cache_loader.py --ticker FIVE # single ticker (<1 sec)
```

**SEC rate limit**: 10 req/sec, `User-Agent` header required (e.g., `"EventMarketDB research@example.com"`).

**Dependencies**: `redis`, `urllib` (stdlib), `json` (stdlib). Optional: `neograph.Neo4jConnection` for CIK fallback.

---

## File 2: `scripts/guidance_trigger_daemon.py` (~30 lines added, MODIFY)

**Why the daemon, not just the scanner**: The daemon is the correctness hook because:
- It sees when each specific asset type (transcript, 8-K, 10-Q, 10-K) is ready for extraction
- A 10-Q/10-K appearing means SEC EDGAR just processed a new filing → new exact data available
- The scanner runs at earnings time (before the 8-K), not when the 10-Q files 40 days later
- Scanner prewarm is an optimization; daemon refresh is the correctness guarantee

**WHERE**: Inside `sweep_once()`, before `enqueue_with_lease()` call (~line 236).

**WHAT**: Asset-aware SEC cache refresh:

```python
def _precompute_sec_refresh(r, to_enqueue, dry_run):
    """Precompute one SEC cache refresh decision per ticker per sweep.

    Rules:
      - If any pending asset for a ticker is 10q/10k → fill-if-missing (new filing may have new data)
      - If only transcript/8k → fill-if-missing
      - --list mode → no-op (no Redis writes during dry-run)

    Called ONCE before the enqueue loop, not per-item.
    """
    if dry_run:
        return  # no side effects during --list

    # Collect unique tickers and whether they have periodic filings pending
    tickers_seen = {}  # ticker → bool (has_periodic)
    for item, asset_name in to_enqueue:
        sym = item["symbol"] or item["id"].split("_")[0]
        if sym not in tickers_seen:
            tickers_seen[sym] = False
        if asset_name in ("10q", "10k"):
            tickers_seen[sym] = True

    # Refresh once per ticker
    for ticker, has_periodic in tickers_seen.items():
        last_key = f"fiscal_quarter:{ticker}:last_refreshed"
        if not r.exists(last_key) or has_periodic:
            try:
                from sec_quarter_cache_loader import refresh_ticker
                refresh_ticker(r, ticker)
            except Exception as e:
                log.warning(f"SEC cache refresh failed for {ticker}: {e}")
```

**Call site**: Inside `sweep_once()`, BEFORE the enqueue loop (not inside it):
```python
# Line ~228, after to_enqueue is sorted but before the for loop:
_precompute_sec_refresh(r, to_enqueue, dry_run)  # NEW LINE — once per sweep

for item, asset_name in to_enqueue:
    sid = item["id"]
    sym = item["symbol"] or sid.split("_")[0]
    st = item["status"]
    enqueued = enqueue_with_lease(r, sid, asset_name, sym, st, queue, dry_run)
    ...
```

**Import**: `from sec_quarter_cache_loader import refresh_ticker` (lazy import inside the function to avoid startup dependency).

---

## File 3: `k8s/processing/guidance-trigger.yaml` (1 line, MODIFY)

**Line ~37**: Change `ACTIVE_WINDOW_DAYS` from `"1"` to `"45"`.

```yaml
- name: ACTIVE_WINDOW_DAYS
  value: "45"    # was "1" — must cover 40-day 10-Q filing window after earnings
```

**Why**: With `ACTIVE_WINDOW_DAYS=1`, the daemon stops considering a ticker 1 day after earnings. The 10-Q arrives ~40 days later → daemon ignores it → never triggers SEC cache refresh or 10-Q guidance extraction. Setting to 45 covers the SEC 10-Q filing deadline for all filer categories (large accelerated: 40d, non-accelerated: 45d).

**Reference**: `GuidanceTrigger.md` line 166 documents this: "default=1 in deployed code, design doc originally said 45 for backfill."

---

## File 4: `guidance_write_cli.py` (~55 lines, MODIFY)

### Change 1: Thread `ticker` into `_ensure_period`

**Why**: `_ensure_period()` needs `ticker` for the fiscal-identity lookup and SEC cache lookup. Currently `ticker` is only at the top-level payload (`data['ticker']` at line 240), not in individual items. The CLI only injects `source_id` into items (line 256), not `ticker`.

```python
# Line 115 — _ensure_ids signature:
def _ensure_ids(item, fye_month=None, ticker=None):
    ...
    _ensure_period(item, fye_month, ticker)
    ...

# Line 78 — _ensure_period signature:
def _ensure_period(item, fye_month, ticker=None):
    ...

# Line 265 — call site:
item = _ensure_ids(item, fye_month=fye_month, ticker=ticker)
```

### Change 2: 4-step cascade in `_ensure_period`

Replace the current body of `_ensure_period` (lines 78-112):

```python
def _ensure_period(item, fye_month, ticker=None):
    """
    Compute period_u_id + GuidancePeriod fields if not already present.

    3-step cascade (Step C is optional — see note):
      A. Reuse existing period (first-write-wins dedup via Neo4j fiscal-identity lookup)
      B. SEC cache lookup (exact dates for filed quarters and annuals)
      C. [OPTIONAL] Predict from previous quarter end + historical length (unfiled quarters)
         Improves accuracy from +-3-5d to +-1d on current-quarter transcripts/8-Ks.
         Zero functional impact on orchestrator (queries by ticker, not date range).
         Adds ~20 lines + fiscal_quarter_length Redis keys. Can be added later if needed.
      D. Corrected FYE math (last resort — sentinels, long-range, half, monthly, uncached)

    Steps A/B are additive. If both return None (Neo4j down, Redis down, cache empty),
    Step D runs — same code path as today, but now may use SEC-corrected FYE input.
    """
    if item.get('period_u_id'):
        return item

    fiscal_year = item.get('fiscal_year')
    fiscal_quarter = item.get('fiscal_quarter')

    # Guard: Steps A/B only handle standard quarter and annual duration items.
    # Half (88 items), monthly (2), sentinel (235), long_range (150), and instant
    # items need special routing that only Step D provides. Without this guard,
    # Step B would give annual dates to half-year items (fiscal_quarter=None → suffix="FY").
    is_standard_period = (
        item.get('time_type') != 'instant'
        and not item.get('half')
        and not item.get('month')
        and not item.get('sentinel_class')
        and not item.get('long_range_end_year')
    )

    # Step A: Reuse existing period (first-write-wins dedup)
    # Prevents duplicate GuidancePeriod AND GuidanceUpdate nodes when dates change
    if is_standard_period and ticker and fiscal_year:
        existing = _lookup_existing_period(ticker, fiscal_year, fiscal_quarter)
        if existing:
            item['period_u_id'] = existing['period_u_id']
            item['period_scope'] = existing.get('period_scope', 'quarter' if fiscal_quarter else 'annual')
            item['time_type'] = existing.get('time_type', 'duration')
            item['gp_start_date'] = existing.get('start_date')
            item['gp_end_date'] = existing.get('end_date')
            return item

    # Step B: SEC cache lookup (quarter or annual — covers 89.9% of guidance items)
    if is_standard_period and ticker and fiscal_year:
        suffix = f"Q{fiscal_quarter}" if fiscal_quarter else "FY"
        sec_dates = _lookup_sec_cache(ticker, fiscal_year, suffix)
        if sec_dates:
            item['period_u_id'] = f"gp_{sec_dates['start']}_{sec_dates['end']}"
            item['period_scope'] = 'quarter' if fiscal_quarter else 'annual'
            item['time_type'] = 'duration'
            item['gp_start_date'] = sec_dates['start']
            item['gp_end_date'] = sec_dates['end']
            return item

    # [PHASE 2 — not in initial implementation]
    # Step C: Predict from previous quarter end + historical length
    # Improves unfiled-quarter accuracy from +-3-5d to +-1d.
    # No known orchestrator impact. Add when/if a consumer needs +-1d.
    # Requires: _predict_from_prev_quarter() + fiscal_quarter_length Redis keys.
    # See "Phase 2" section at end of this document.

    # Step D: FYE math (last resort)
    # Handles: sentinel, long_range, monthly, half, and uncached quarter/annual
    # Use SEC-corrected FYE if available (fixes +-28d bug even at fallback level)
    effective_fye = fye_month
    if ticker:
        sec_fye = _get_sec_corrected_fye(ticker)
        if sec_fye is not None:
            effective_fye = sec_fye

    if effective_fye is None:
        raise ValueError("Cannot compute period: fye_month required at top level when items lack period_u_id")

    period = build_guidance_period_id(
        fye_month=effective_fye,
        fiscal_year=item.get('fiscal_year'),
        fiscal_quarter=item.get('fiscal_quarter'),
        half=item.get('half'),
        month=item.get('month'),
        long_range_start_year=item.get('long_range_start_year'),
        long_range_end_year=item.get('long_range_end_year'),
        calendar_override=item.get('calendar_override', False),
        sentinel_class=item.get('sentinel_class'),
        time_type=item.get('time_type'),
        label_slug=item.get('label_slug'),
    )
    item['period_u_id'] = period['u_id']
    item['period_scope'] = period['period_scope']
    item['time_type'] = period['time_type']
    item['gp_start_date'] = period['start_date']
    item['gp_end_date'] = period['end_date']
    return item
```

### Change 3: Lazy Neo4j/Redis connections + helper functions

Added at module level (before `_ensure_period`):

```python
import os
from datetime import date, timedelta

_neo4j_mgr = None
_redis_cli = None


def _get_neo4j():
    """Lazy Neo4j connection. Returns None on failure (graceful degradation)."""
    global _neo4j_mgr
    if _neo4j_mgr is None:
        try:
            from neograph.Neo4jConnection import get_manager
            _neo4j_mgr = get_manager()
        except Exception:
            pass  # Steps A falls through to Step B/C/D
    return _neo4j_mgr


def _get_redis():
    """Lazy Redis connection. Returns None on failure (graceful degradation)."""
    global _redis_cli
    if _redis_cli is None:
        try:
            import redis
            _redis_cli = redis.Redis(
                host=os.environ.get('REDIS_HOST', '192.168.40.72'),
                port=int(os.environ.get('REDIS_PORT', '31379')),
                decode_responses=True)
            _redis_cli.ping()
        except Exception:
            _redis_cli = None  # Steps B/C fall through to Step D
    return _redis_cli


def _lookup_existing_period(ticker, fiscal_year, fiscal_quarter):
    """Check Neo4j for existing GuidancePeriod for this fiscal identity.

    Uses GuidanceUpdate.fiscal_year and GuidanceUpdate.fiscal_quarter
    (both persisted at guidance_writer.py:169-170).

    Handles both quarterly (fiscal_quarter is int) and annual (fiscal_quarter is None).

    IMPORTANT: Uses execute_cypher_query_all() (returns list[dict], not a Record).
    execute_cypher_query() returns a single Record — not dict-indexable with [0].
    See neograph/Neo4jManager.py:1091 vs :1107.

    IMPORTANT: Must be deterministic. The live graph has 28 duplicate quarter groups
    and 34 duplicate annual groups (from the FYE bug). LIMIT 1 without ORDER BY
    could pick the wrong period. ORDER BY: most GuidanceUpdate references first
    (majority = most likely correct), then latest end_date, then u_id for tiebreak.
    After migration cleans up duplicates, the ORDER BY is harmless (only one result).
    """
    mgr = _get_neo4j()
    if not mgr:
        return None
    try:
        if fiscal_quarter is not None:
            result = mgr.execute_cypher_query_all("""
                MATCH (gu:GuidanceUpdate)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
                WHERE gu.fiscal_year = $fy AND gu.fiscal_quarter = $fq
                MATCH (gu)-[:HAS_PERIOD]->(gp:GuidancePeriod)
                WITH gp, count(gu) AS ref_count
                ORDER BY ref_count DESC, gp.end_date DESC, gp.u_id
                RETURN gp.u_id AS period_u_id, gp.start_date AS start_date,
                       gp.end_date AS end_date
                LIMIT 1
            """, {'ticker': ticker, 'fy': fiscal_year, 'fq': fiscal_quarter})
        else:
            # Annual: fiscal_quarter IS NULL and period_scope = 'annual'
            result = mgr.execute_cypher_query_all("""
                MATCH (gu:GuidanceUpdate)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
                WHERE gu.fiscal_year = $fy AND gu.fiscal_quarter IS NULL
                  AND gu.period_scope = 'annual'
                MATCH (gu)-[:HAS_PERIOD]->(gp:GuidancePeriod)
                WITH gp, count(gu) AS ref_count
                ORDER BY ref_count DESC, gp.end_date DESC, gp.u_id
                RETURN gp.u_id AS period_u_id, gp.start_date AS start_date,
                       gp.end_date AS end_date
                LIMIT 1
            """, {'ticker': ticker, 'fy': fiscal_year})
        return result[0] if result else None
    except Exception:
        return None


def _lookup_sec_cache(ticker, fiscal_year, suffix):
    """Check Redis for SEC-derived exact dates. suffix is 'Q1'-'Q4' or 'FY'."""
    r = _get_redis()
    if not r:
        return None
    try:
        data = r.get(f"fiscal_quarter:{ticker}:{fiscal_year}:{suffix}")
        return json.loads(data) if data else None
    except Exception:
        return None


# _predict_from_prev_quarter() — PHASE 2, not in initial implementation.
# See "Phase 2" section at end of document.


def _get_sec_corrected_fye(ticker):
    """Get SEC-adjusted FYE month from Redis cache.

    Fixes the +-28d bug even at the Step D fallback level by using
    SEC's own fiscalYearEnd (day<=5 adjusted) instead of the raw
    fye_month from the extraction payload's Query 1B.
    """
    r = _get_redis()
    if not r:
        return None
    try:
        data = r.get(f"fiscal_year_end:{ticker}")
        if data:
            return json.loads(data).get('month_adj')
    except Exception:
        pass
    return None
```

### What's unchanged

- `build_guidance_period_id()` in `guidance_ids.py` — zero changes
- `build_guidance_ids()` in `guidance_ids.py` — zero changes
- `guidance_writer.py` (MERGE queries, Cypher, write logic) — zero changes
- `_ensure_ids()` body — only signature adds `ticker=None` (backward compatible)
- Step D code path — identical to current `_ensure_period()` body, just uses `effective_fye` instead of `fye_month`
- Dry-run mode — now attempts lazy Neo4j/Redis connections (graceful fallback: fails silently → Steps A/B skip → Step D runs as before). Output unchanged, but external connections are attempted.
- All 200 existing tests (86 guidance_ids + 31 write_cli + 83 writer) — pass unchanged (`ticker=None` default preserves old behavior)

---

## File 5: Migration script (~60 lines, NEW)

**Purpose**: Fix existing 1,858 wrong guidance items on 5 tickers (FIVE, ASO, LULU, DLTR, SAIC).

**What it must do**:

1. Load SEC exact dates from Redis cache (run `sec_quarter_cache_loader.py` first)
2. For each affected ticker, find all GuidanceUpdate nodes with wrong GuidancePeriod (~28d offset)
3. For each GuidanceUpdate:
   a. Look up correct dates from SEC cache by `(ticker, gu.fiscal_year, gu.fiscal_quarter or 'FY')`
   b. Compute correct `period_u_id` = `gp_{correct_start}_{correct_end}`
   c. MERGE correct GuidancePeriod node with exact dates
   d. Delete old `(gu)-[:HAS_PERIOD]->(old_gp)` relationship
   e. Create new `(gu)-[:HAS_PERIOD]->(correct_gp)` relationship
   f. Recompute `guidance_update_id` with new `period_u_id` (using `build_guidance_ids()`)
   g. **PREFLIGHT**: check if another node already has the target `guidance_update_id`
      - If collision exists: **ABORT for this node** and log for manual review. Do NOT auto-merge.
        Full merge logic (union source_refs, preserve edges) can be added later if collisions are actually observed.
      - If no collision: `SET gu.id = $new_guidance_update_id` (in-place property update)
4. Delete orphaned wrong-date GuidancePeriod nodes (`WHERE NOT ()-[:HAS_PERIOD]->()`)
5. Verify: zero duplicate periods per (ticker, fiscal_year, fiscal_quarter)

**Why preflight collisions**: While collisions should be impossible (the new ID has a different `period_u_id` that no existing node has), a safe migration must check. A partial previous migration or concurrent extraction could create unexpected state. Checking before `SET gu.id` prevents a cryptic uniqueness constraint failure. Cost: ~1 Cypher query per node.

**Why rekey GuidanceUpdate.id**: The `guidance_update_id` embeds `period_u_id` at `guidance_ids.py:570`:
```python
guidance_update_id = f"gu:{safe_source_id}:{label_slug}:{period_u_id}:{basis_norm}:{segment_slug}"
```
If only `HAS_PERIOD` is re-pointed but `gu.id` still contains the old `period_u_id`, future MERGEs with the new `period_u_id` would create a duplicate GuidanceUpdate.

---

## File 6: `scripts/trigger-extract.py` (~5 lines, MODIFY)

**Purpose**: SEC cache prefetch for manual (non-TradeReady) runs.

**WHERE**: In `main()`, after `items = find_unprocessed(...)` returns and before `push_to_queue()` (around line ~267). The script has no per-ticker loop — it finds items first, then queues them. SEC prefetch goes between those steps.

**WHAT**:
```python
# After items are found but before queuing — prefetch SEC cache for unique tickers
# ONLY for guidance extraction (not news or other types)
# trigger-extract.py already imports redis (line 36) and defines REDIS_HOST/REDIS_PORT
if (not args.list and items
        and extraction_type == "guidance"
        and asset in ("transcript", "8k", "10q", "10k")):
    unique_tickers = sorted({item["symbol"] or item["id"].split("_")[0] for item in items})
    import redis as _redis
    _r = _redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    for t in unique_tickers:
        try:
            from sec_quarter_cache_loader import refresh_ticker
            refresh_ticker(_r, t)
        except Exception as e:
            print(f"SEC cache prefetch failed for {t}: {e}", file=sys.stderr)
```

**Note**: `trigger-extract.py` uses `print(..., file=sys.stderr)` for output (line 118+), not a `log` logger. Redis is created inline — the script already imports `redis` at line 36 and creates clients inside `push_to_queue()` at line 168.

**Why**: Manual `trigger-extract.py --ticker XYZ` bypasses TradeReady and the daemon. Without this, a non-TradeReady ticker has no SEC cache → Steps A/B miss → Step D runs with potentially buggy FYE.

---

## File 7 (OPTIONAL): `scripts/trade_ready_scanner.py` (~25 lines, MODIFY)

**Purpose**: Prewarm SEC cache when tickers enter TradeReady. This is an **optimization**, not the correctness hook (that's the daemon in File 2).

**WHERE**: AFTER `pipe.execute()` completes (around line 390), NOT inside the Redis pipeline batching loop. Placing SEC HTTP fetches inside the pipeline loop would block the fast pipeline-building path with slow external calls.

**WHAT**:
```python
def _prewarm_sec_cache(r, entries):
    """Prewarm SEC quarter data for active tickers if cache missing. Fill-if-missing only."""
    for ticker in entries:
        last_key = f"fiscal_quarter:{ticker}:last_refreshed"
        if r.exists(last_key):
            continue  # already cached
        try:
            from sec_quarter_cache_loader import refresh_ticker
            refresh_ticker(r, ticker)
        except Exception as e:
            log.warning(f"SEC cache prewarm failed for {ticker}: {e}")

# Call site: AFTER pipe.execute() and the existing Redis writes complete
# write_to_redis(r, entries)  # existing function
# _prewarm_sec_cache(r, entries)  # NEW — separate from the pipeline
```

**Note**: This is fill-if-missing, not force-refresh. The daemon handles force-refresh on 10-Q/10-K arrival. The scanner just ensures the cache is warm before the 8-K fires (1-3 day lead time). Placed after pipe.execute() to avoid mixing slow SEC HTTP calls into the fast Redis pipeline.

---

## Execution Order

**TWO CRITICAL ordering constraints:**
1. Migration must run BEFORE enabling Step A — the live graph has 28+34 duplicate fiscal-identity groups from the FYE bug. Step A without migration could fossilize the wrong period.
2. Code changes and ACTIVE_WINDOW_DAYS=45 must deploy TOGETHER — deploying 45 with old buggy code widens the extraction window, creating MORE wrong items with the old ±28d bug before the fix is live.

1. **Build `sec_quarter_cache_loader.py`** — the foundation everything depends on
2. **Run initial bootstrap**: `python3 sec_quarter_cache_loader.py` (all tickers, ~90 sec)
3. **Run migration** — fix 1,858 existing wrong items on 5 tickers
4. **Verify migration**: zero duplicate GuidancePeriod nodes per (ticker, fiscal_year, fiscal_quarter)
5. **Deploy ALL code changes + ACTIVE_WINDOW_DAYS=45 together (atomic rollout)**:
   - `guidance_write_cli.py` — 3-step cascade
   - `guidance_trigger_daemon.py` — per-ticker SEC refresh, skip in --list
   - `trigger-extract.py` — SEC prefetch (gated on guidance type)
   - `k8s/processing/guidance-trigger.yaml` — `ACTIVE_WINDOW_DAYS=45`
6. **Test**: extract guidance for one affected ticker (e.g., FIVE), verify correct period dates
7. **Run new tests** (see Required New Tests section)
8. **(Optional)** Modify `trade_ready_scanner.py` for prewarm

---

## SEC Date Convention

SEC XBRL Company Concept API uses **inclusive** end dates (the last day of the quarter IS the end date).

```
FIVE Q1 FY2024:
  SEC API:    start=2024-02-04, end=2024-05-04  (inclusive: May 4 is the last day)
  Graph v3:   start=2024-02-04, end=2024-05-05  (exclusive: May 5 is the next Q start)
```

**Decision: Use SEC inclusive convention.** The GuidancePeriod node ID becomes `gp_2024-02-04_2024-05-04` (not `_2024-05-05`). Existing nodes need migration regardless (wrong ~28d offset), so the convention switch is free.

**Prediction math with inclusive dates**:
```python
# SEC inclusive: prev quarter end = last day of that quarter
# Next quarter starts the NEXT day
start = prev_end + 1 day
end = start + length - 1
```

---

## What This Does NOT Change

| Component | Status | Why |
|---|---|---|
| `guidance_ids.py` (`build_guidance_period_id`, `build_guidance_ids`) | **Unchanged** | Still called by Step D exactly as today |
| `guidance_writer.py` (MERGE queries, Cypher, write logic) | **Unchanged** | The writer receives the same fields; only the input values change |
| `fiscal_math.py` (`_compute_fiscal_dates`, `period_to_fiscal`) | **Unchanged** | Still used by Step D; SEC-corrected FYE fixes the input, not the function |
| Dry-run mode in `guidance_write_cli.py` | **Graceful fallback** | Lazy connections now attempt Neo4j/Redis but fail silently (None) → Steps A/B skip → Step D runs. Output unchanged. |
| All 200 existing tests (86+31+83) | **Pass unchanged** | `ticker=None` default preserves old `_ensure_period` and `_ensure_ids` behavior |
| `get_quarterly_filings.py` (already fixed with XBRL-direct) | **Unchanged** | Separate fix, unrelated to this implementation |
| Extraction agent prompts / pass files | **Unchanged** | The agent still extracts the same fields; ID computation happens downstream |
| Neo4j connection count in write mode | **No change** | `get_manager()` is a singleton (`Neo4jConnection.py:15-17`). The lazy `_get_neo4j()` and the existing write-mode `get_manager()` at line 326 share the same instance. Zero duplicate connections. |

---

## Regression Risks

| Risk | Severity | Mitigation |
|---|---|---|
| **Steps A/B give annual dates to half/monthly/sentinel/long_range items** | HIGH if unguarded | `is_standard_period` guard skips Steps A/B for non-quarter/non-annual items. 475 items (9.1%) protected. |
| **Step A returns wrong period from pre-migration duplicates** | HIGH if migration hasn't run | Execution order: migration (step 3) BEFORE code deploy (step 5). ORDER BY ref_count DESC as fallback. |
| **Dry-run attempts external connections** | LOW | `_get_neo4j()` and `_get_redis()` fail silently (return None). Output unchanged. Slightly slower on first call (~100ms timeout). |
| **Daemon SEC refresh fails (SEC down)** | LOW | try/except swallows error, logs warning, enqueue proceeds. Extraction uses Step D fallback. |
| **Daemon SEC refresh in --list mode** | NONE (fixed) | `_precompute_sec_refresh()` checks `dry_run` flag and no-ops. |
| **Same ticker refreshed multiple times per sweep** | NONE (fixed) | `_precompute_sec_refresh()` dedupes per-ticker before the enqueue loop. |
| **`_lookup_existing_period` nondeterministic** | NONE (fixed) | ORDER BY ref_count DESC, end_date DESC, u_id. Deterministic even with duplicates. |
| **`_ensure_period` signature change breaks tests** | NONE | `ticker=None` default. All 200 tests call without ticker → Steps A/B skip → Step D unchanged. |
| **`_ensure_ids` signature change breaks tests** | NONE | `ticker=None` default. 11 test call sites all use positional/keyword args without ticker. |
| **Migration collision on GuidanceUpdate.id rekey** | LOW | Preflight check before SET. Abort + log on collision for manual review. No auto-merge. |
| **ACTIVE_WINDOW_DAYS=45 increases daemon workload** | LOW | ~225 active tickers in `IN` clause at peak. Negligible Neo4j load — documented in GuidanceTrigger.md:172 ("most have all assets completed"). |

---

## Required New Tests

The 200 existing tests protect the old Step D path. They do NOT prove new Steps A/B, daemon refresh, or manual prefetch work. These new tests are required before signoff:

| Test | What it proves | File |
|---|---|---|
| Step A returns existing period over SEC exact | fiscal-identity lookup works, first-write-wins dedup | `test_guidance_write_cli.py` |
| Step B returns SEC exact quarter dates | SEC cache lookup works for quarters | `test_guidance_write_cli.py` |
| Step B returns SEC exact annual dates | SEC cache lookup works for annuals (61.5% of items) | `test_guidance_write_cli.py` |
| Step A/B skip when ticker=None | Old behavior preserved (test backward compat) | `test_guidance_write_cli.py` |
| Step A/B skip when Neo4j/Redis unavailable | Graceful degradation → Step D | `test_guidance_write_cli.py` |
| Daemon --list does not write Redis | No side effects during dry-run | `test_guidance_trigger_daemon.py` (or manual) |
| Daemon refreshes once per ticker per sweep | No redundant API calls for multi-asset tickers | `test_guidance_trigger_daemon.py` (or manual) |
| trigger-extract.py prefetch gates on guidance type | SEC prefetch skips non-guidance extraction types | Manual verification |

These can be unit tests (mocking Neo4j/Redis) or integration tests against the live graph. Minimum: the first 5 (unit-testable without external dependencies).

---

## Accuracy After Implementation

| Scenario | Accuracy | Source |
|---|---|---|
| Filed quarter/annual (all data assets) | **Exact (0d)** | SEC cache (Step B) |
| 8-K/transcript past-quarter reference | **Exact (0d)** | SEC cache (prior 10-Q already filed) |
| 8-K/transcript current quarter (unfiled) | **+-3-5d normal case**, fossilized | Step D with corrected FYE (uniform 13-week). Irregular calendars (COST, KR) can be worse (+-11-24d) if SEC cache AND Step A both miss. Phase 2 Step C improves to +-1d. |
| 8-K/transcript forward guidance | Same as above | Same |
| Sentinel/long-range/half/monthly | **Same as today** | Step D unchanged |
| KR Q1 (old +-24d worst case) | **Exact (0d) if SEC cache hit** | SEC cache has KR's 111d Q1 exact dates. If SEC cache misses AND Step A misses: Step D = +-24d (irregular calendar). |
| COST Q3 (old +-19d worst case) | **Exact (0d) if SEC cache hit** | SEC cache has COST's 84d Q3 exact dates. If SEC cache misses AND Step A misses: Step D = +-19d. |
| Step D fallback (all tiers miss) | **+-3-5d normal case (was +-28d)** | SEC-corrected FYE fixes the month. Normal case = uniform 13-week. Irregular calendars can be worse (+-11-24d). |

---

## References

- `fiscal-math-issues.md` — full investigation, bug scope, all validation data
- `GuidanceTrigger.md` — daemon architecture, ACTIVE_WINDOW_DAYS, TradeReady scanner
- `guidance_write_cli.py:78` — `_ensure_period()` (the function being modified)
- `guidance_ids.py:376` — `build_guidance_period_id()` (Step D, unchanged)
- `guidance_ids.py:570` — `guidance_update_id` embeds `period_u_id` (why migration must rekey)
- `guidance_writer.py:157-197` — MERGE queries (unchanged)
- `guidance_writer.py:169-170` — `GuidanceUpdate.fiscal_year` and `.fiscal_quarter` persisted
- `guidance_trigger_daemon.py:49` — `ACTIVE_WINDOW_DAYS` config
- `guidance_trigger_daemon.py:53-63` — `ASSET_CONFIGS` (asset types the daemon processes)
- `trade_ready_scanner.py:368` — `added_at` preservation for returning tickers
- `/tmp/sec_fye_scale_test.py` — SEC EDGAR cross-validation script (737/738 = 99.86%)
- `/tmp/sec_fye_full_results.json` — full SEC cross-validation results

---

## Phase 2 — Optional Future Improvements

### Step C: Prediction from previous quarter + historical length

Improves unfiled-quarter accuracy from ±3-5d (Step D) to ±1d. No known orchestrator impact. Add when/if a consumer needs ±1d precision on GuidancePeriod dates for unfiled quarters.

**What to add:**
1. `fiscal_quarter_length:{TICKER}:Q{N}` Redis keys — median quarter span computed from SEC cache
2. `_predict_from_prev_quarter()` function in `guidance_write_cli.py`
3. Step C block between Step B and Step D in `_ensure_period()`

**Prediction math (SEC inclusive convention):**
```python
def _predict_from_prev_quarter(ticker, fiscal_year, fiscal_quarter):
    r = _get_redis()
    if not r: return None
    prev_q = fiscal_quarter - 1 if fiscal_quarter > 1 else 4
    prev_fy = fiscal_year if fiscal_quarter > 1 else fiscal_year - 1
    prev_data = r.get(f"fiscal_quarter:{ticker}:{prev_fy}:Q{prev_q}")
    length = r.get(f"fiscal_quarter_length:{ticker}:Q{fiscal_quarter}")
    if prev_data and length:
        prev = json.loads(prev_data)
        start = (date.fromisoformat(prev['end']) + timedelta(days=1)).isoformat()
        end = (date.fromisoformat(start) + timedelta(days=int(length) - 1)).isoformat()
        return {"start": start, "end": end}
    return None
```

**Accuracy:** 98.4% within ±1d, 99.2% within ±3d (tested on 5,673 quarters).
**One assumption:** Quarter lengths stable across FYs. Breaks ±7d on 53-week transitions (~1 per ticker per 6yr).
**Lines:** ~20 added to guidance_write_cli.py + median computation in sec_quarter_cache_loader.py.

### Decouple GuidanceUpdate identity from period assignment

Long-term architectural improvement. Remove `period_u_id` from `guidance_update_id` formula and replace with fiscal-identity-based key (`fy2025_q3`). Makes period dates fully mutable without affecting GuidanceUpdate identity. Requires schema migration of all GuidanceUpdate nodes. See `fiscal-math-issues.md` for full analysis.
