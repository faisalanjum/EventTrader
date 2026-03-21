# Fiscal Math Issues

Date: 2026-03-19 (updated 2026-03-21)
Status: Fix designed, validated & finalized. Implementation TBD.
Related: Session `get_quarterly_filings`

---

## TL;DR — FINALIZED FIX (2026-03-21)

**Fixed (2026-03-19):** `get_quarterly_filings.py` — fiscal labeling (XBRL-direct, 99.94% accurate) and dedup (min-lag, 0 wrong picks). Ready for the earnings orchestrator.

**Still broken:** `build_guidance_period_id()` in `guidance_ids.py` — wrong FYE month for **~41-44 tickers** (not 18 as originally reported). Affects guidance data only.

**Bug scope:** ~41-44 tickers (core set: ~39 uniform + 2 irregular). 5 tickers already have wrong guidance data in production (FIVE: 468, ASO: 387, LULU: 355, DLTR: 351, SAIC: 297 = 1,858 items). ~173 items on wrong period convention (~28-day offset). Independently confirmed by SEC EDGAR cross-validation (737/738 = 99.86% agreement with our corrected FYE).

**Finalized fix — SEC API approach (v4):**

```
build_guidance_period_id(ticker, fiscal_year, fiscal_quarter):

  Step 1 — SEC quarter cache (EXACT, for any filed quarter):
    Local Redis cache (no TTL), populated on initial bootstrap + incremental via TradeReady scanner
    83,091 quarters across 739 tickers, 100% coverage, zero anomalies
    → If found: return exact (start_date, end_date). DONE.

  Step 2 — Predict unfiled quarter (for 8-K/transcript current/forward guidance):
    start = previous quarter's end (exact, from Step 1 cache)
    end = start + median historical quarter length for (ticker, quarter_number)
    98.4% within ±1d, 99.2% within ±3d
    → Return predicted dates. First-write-wins: MERGE reuses existing node.

  Step 3 — SEC FYE fallback (brand new ticker, no history):
    Fetch fiscalYearEnd from SEC submissions API, apply day≤5 adjustment
    → Last resort. ±3-5d for uniform, ±11-24d for irregular.
```

**Why SEC API (v4) supersedes the graph-based v3 cascade:**
- Eliminates all 19 span anomalies from FY label collisions
- Eliminates KR ±24d and COST ±19d worst cases (SEC has exact dates for their irregular calendars)
- No XBRL reprocessing prerequisite (SEC already processed everything)
- No HAS_XBRL gate needed on guidance trigger daemon
- 100% historical coverage (vs 84.8% for graph v3)
- Simpler: one HTTP call per ticker vs complex Cypher with YTD differencing

**Duplicate prevention — first-write-wins with fiscal-identity lookup (REQUIRES CODE CHANGE):**

The duplicate risk is at TWO levels, not one:
- `period_u_id` = `gp_{start}_{end}` — encodes dates in GuidancePeriod node ID
- `guidance_update_id` = `gu:{source_id}:{label_slug}:{period_u_id}:{basis}:{segment}` — **embeds period_u_id** (`guidance_ids.py:570-572`)

If dates change (predicted → exact), BOTH IDs change → MERGE creates duplicate GuidancePeriod AND duplicate GuidanceUpdate. MERGE alone does NOT prevent this because the IDs differ.

**The fix — fiscal-identity lookup before ID generation:**

```python
# In _ensure_period() or build_guidance_period_id(), BEFORE computing dates:
# Check if a GuidancePeriod already exists for this (ticker, fiscal_year, fiscal_quarter).
# GuidanceUpdate nodes DO carry fiscal_quarter (guidance_writer.py:170).

existing = session.run("""
    MATCH (gu:GuidanceUpdate)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
    WHERE gu.fiscal_year = $fiscal_year AND gu.fiscal_quarter = $fiscal_quarter
    MATCH (gu)-[:HAS_PERIOD]->(gp:GuidancePeriod)
    RETURN gp.u_id AS period_u_id LIMIT 1
""", ticker=ticker, fiscal_year=fiscal_year, fiscal_quarter=fiscal_quarter)

if existing:
    return existing['period_u_id']  # reuse existing, first-write-wins
else:
    # compute new dates from SEC cache (Step 1) or prediction (Step 2)
```

This is NOT zero code change. It requires a Neo4j lookup before every ID computation. But it guarantees: once a GuidancePeriod is created for a (ticker, FY, quarter), all subsequent extractions reuse it, regardless of whether the date computation changes.

**Design decision: First-write-wins vs Revise-when-filed (analyzed 2026-03-21)**

Two options were evaluated for handling the 40-day gap between 8-K/transcript extraction (predicted dates) and 10-Q filing (exact dates available):

**Option A — First-write-wins (CHOSEN):**
- First extraction writes predicted dates → fossilized permanently
- All subsequent extractions for the same quarter reuse the existing period via fiscal-identity lookup
- ±1d fossilized for 98.4%, ±7d on 53-week transitions (~1 per ticker per 6yr)
- Implementation: fiscal-identity lookup in `_ensure_period()` (~10 lines)

**Option B — Revise when filing arrives (REJECTED):**
- Same as A for initial write, but a daily batch job revises GuidancePeriod dates to exact after SEC cache refreshes
- Requires: fiscal-identity lookup (same as A) + batch revision job that re-points `(gu)-[:HAS_PERIOD]->(new_gp)` edges + orphan cleanup
- The `guidance_update_id` stays stale (embeds old `period_u_id` in the string at `guidance_ids.py:570`) — changing it would require delete+recreate of GuidanceUpdate nodes
- Still needs the fiscal-identity lookup to prevent MERGE duplicates from future extractions

**Why Option A wins — fossilization has zero functional impact:**

The earnings orchestrator (`earnings-orchestrator.md §2a`) queries guidance by **ticker**, not by period date range:
```
Step 3a: Load all prior quarters' guidance history for this ticker
→ MATCH (gu:GuidanceUpdate)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
```

A GuidancePeriod with dates ±1-7d off still:
- Links to the correct GuidanceUpdate via `:HAS_PERIOD` ✓
- Links to the correct Company via `:FOR_COMPANY` (on GuidanceUpdate) ✓
- Has the correct `fiscal_year` and `fiscal_quarter` on the GuidanceUpdate node ✓
- Gets returned by any ticker-based query ✓

No current consumer queries GuidancePeriod by exact date range. The dates are for dedup (node ID) and human readability, not retrieval filtering.

| | Option A (first-write-wins) | Option B (revise) |
|---|---|---|
| Code change | Fiscal-identity lookup (~10 lines) | Same lookup + batch job (~100 lines) + CronJob |
| Batch jobs | None | Daily revision after SEC refresh |
| GuidancePeriod dates | ±1-7d fossilized | Exact after revision |
| GuidanceUpdate id | Consistent (never changes) | Stale (old period_u_id baked in) |
| Duplicate prevention | Fiscal-identity lookup | Same lookup (still required) |
| Functional impact on orchestrator | None | None |
| Complexity | Low | High (edge deletion, MERGE, orphan cleanup) |
| Risk | Cosmetic ±1-7d on period nodes | Relationship surgery failures, orphaned nodes |

**When to reconsider Option B:** Only if a future consumer needs to query GuidancePeriod by exact date range (e.g., `WHERE gp.start_date = '2024-08-04'`). No current consumer does this.

**How first-write-wins works in practice:**
1. Transcript fires Day 0 → no existing period → SEC cache miss (unfiled) → Step 2 predicts → creates `gp_2024-08-04_2024-11-02` → `guidance_update_id` includes this → MERGE creates both nodes
2. 8-K fires Day 0 (same quarter) → fiscal-identity lookup finds existing period → reuses `gp_2024-08-04_2024-11-02` → same `guidance_update_id` → MERGE hits existing node. **Zero duplicate.**
3. 10-Q files Day 40 → SEC cache refreshes → exact dates = `gp_2024-08-04_2024-11-03` → BUT any new extraction for this quarter hits the fiscal-identity lookup first → finds existing `gp_2024-08-04_2024-11-02` → reuses it. **Zero duplicate.** ±1d off permanently. No functional impact.

**Accuracy summary:**

| Scenario | Accuracy | Confidence |
|---|---|---|
| Any filed quarter (all data assets) | **Exact (0d)** | **PROVEN** — 83,091 quarters, 739/739 tickers |
| 8-K/transcript current/forward quarter | **±0-1d (98.4%), fossilized** | **SIMULATION** — not E2E production-tested |
| 53-week transition quarter (~1 per ticker per 6yr) | **±7d, fossilized** | **HIGH** — historical pattern |
| KR Q1, COST Q3 (old worst cases) | **Exact (0d)** | **PROVEN** — SEC has their irregular calendar dates |

**To implement:**
1. Build `scripts/sec_quarter_cache_loader.py` (~200 lines) — initial bootstrap + manual refresh
2. Add ~20 lines to `scripts/trade_ready_scanner.py` — for each active TradeReady ticker, fetch SEC data if cache is missing or stale (>90 days). Covers both new and returning tickers. Piggybacks on existing 4x/day CronJob, no new deployment.
3. Run initial bootstrap: `python3 sec_quarter_cache_loader.py` once (~90 sec, all 739 tickers)
4. **Add fiscal-identity lookup** in `_ensure_period()` (`guidance_write_cli.py:~78`) — query existing GuidancePeriod by (ticker, fiscal_year, fiscal_quarter) before calling `build_guidance_period_id()`
5. Modify `build_guidance_period_id()` in `guidance_ids.py:376` (Steps 1→2→3 for new periods only)
6. Run one-time migration for 1,858 existing wrong guidance items
7. Keep graph v3 query as offline fallback only
8. Optionally deploy `sec-quarter-refresh.yaml` as weekly safety net (Sunday 6 AM) for cache corruption recovery

---

## Orchestrator Readiness

**`get_quarterly_filings.py` is ready for the earnings orchestrator as-is.** The hook (`build_orchestrator_event_json.py`) already parses its output and builds `event.json` with `quarter_label`, so no JSON mode or format changes needed.

**Known gaps (not blockers):**
- `daily_stock`/`hourly_stock` not in discovery output (removed when switching to min-lag dedup). Orchestrator fetches returns separately at learner time. Could be re-added as optimization if needed.
- 8-K/A amendments excluded by query design (`formType = '8-K'`), not specially handled. This is intentional per `8k_reference.md:388`.
- No automated tests for `get_earnings_with_10q()`, the XBRL deny list, or min-lag dedup. Empirical validation was done this session (248 content-verified disagreements, 7,926 XBRL ground truth comparisons) but not persisted as repo tests.
- Hardcoded `.env` path — works in current K8s deployment (hostPath mount). Portability smell, not a break.
- `neo4j_session()` context manager (lines 49-63) has a latent double-yield bug: if an exception propagates from inside the `with` block back to the generator, the `except` tries to yield a second time → would crash with `RuntimeError`. Currently masked because `get_earnings_with_10q()` catches all exceptions internally. Zero risk today (one caller), but would break any future caller without its own try/except.

---

## What We Fixed Today

### `get_quarterly_filings.py` — the 8-K earnings discovery function

| Fix | Description | Accuracy |
|---|---|---|
| **XBRL fiscal identity** | Read `DocumentFiscalYearFocus` + `DocumentFiscalPeriodFocus` from matched 10-Q/10-K instead of calculating. Hybrid proximity guard + 11-accession deny list for bad XBRL. | 99.94% (7,921/7,926 vs XBRL ground truth) |
| **XBRL deny list** | 11 accessions: AES×3, WMS×3, URBN×2, CAKE×1, PLCE×1, RH×1. Bad XBRL that leaks through the proximity guard or fiscal year transition collisions. | Verified via SEC EDGAR web search |
| **Min-lag dedup** | Replace 218-ticker static `USE_FIRST_TICKERS` with min `abs(lag_hours)` to matched 10-Q/10-K. Picks the canonical earnings 8-K (filed closest to the periodic filing). | 0 wrong picks out of 248 content-verified disagreements |
| **MAX_LAG_HOURS** | 45 → 90 days to cover slow Q4 10-K filers. | Fixes Q4 N/A misses |
| **Dead copy deleted** | `scripts/earnings/get_quarterly_filings.py` removed. Single source of truth at `.claude/skills/earnings-orchestrator/scripts/get_quarterly_filings.py`. Symlinked to `~/bin/get_quarterly_filings`. | Zero runtime consumers verified |

All of the above only affect the **fiscal labeling and dedup** path in `get_quarterly_filings.py`. The XBRL-direct approach bypasses `period_to_fiscal()` for 96% of rows.

---

## What Is Still Wrong

### Root cause: `_compute_fiscal_dates()` and `period_to_fiscal()` in `fiscal_math.py`

These two functions are the shared math used by everything. They have two known issues:

**Issue A — Raw FYE derivation**: `get_derived_fye()` uses the raw month from 10-K `periodOfReport` without applying the 52-week calendar adjustment (day ≤ 5). For 18 retailers with 52-week calendars, this gives FYE=2 (February) when the real FYE is 1 (January). Affected tickers: ANF, ASO, BJ, BURL, DKS, DLTR, FIVE, GME, KR, KSS, OLLI, OXM, PLAY, PLCE, PVH, RH, ROST, ULTA.

**Issue B — Fiscal year labeling convention**: For companies with FYE in months 1-5, `period_to_fiscal()` labels the fiscal year by the calendar year of the period end. But XBRL/SEC convention labels by the calendar year containing the majority of the fiscal months. For a Jan-FYE company, the fiscal year ending Jan 2024 is labeled FY2024 by `period_to_fiscal` but FY2023 by XBRL. This is a systematic +1 year offset for ~50 tickers.

**For `get_quarterly_filings.py`, we bypassed both issues** by reading XBRL labels directly. But the underlying math functions are still wrong and are consumed by the live guidance extraction path.

---

## Functions Still Affected

### 1. `build_guidance_period_id()` in `guidance_ids.py:376`

**Status: LIVE — called during every guidance extraction**

This is the live bug. It converts fiscal labels to calendar dates for GuidancePeriod node IDs by calling `_compute_fiscal_dates()` directly. This is the calendar-based `gp_{start}_{end}` path described in `core-contract.md:394` and `:442`.

**Important:** The live guidance bug is specifically in `build_guidance_period_id()` → `_compute_fiscal_dates()`. The dead code (`fiscal_to_dates()` and `fiscal_resolve.py`) has additional XBRL Period lookup/classification logic that is NOT part of the live guidance path. These are separate code paths.

**Call chain:**
```
Extraction agent → guidance_write_cli.py:94 → _ensure_period() → build_guidance_period_id()
  → _compute_fiscal_dates(fye_month, fiscal_year, fiscal_quarter)
  → returns gp_{start_date}_{end_date}
```

**The FYE month comes from:** Query 1B in `queries-common.md` — the extraction agent reads the latest 10-K's `periodOfReport` and extracts the month. This is the raw month (same as `get_derived_fye`), not adjusted for 52-week calendars.

**Measured impact (snapshot estimates from Neo4j, 2026-03-19):**

ASO and DLTR (both FYE=2 raw, should be 1) show **two different period conventions** for the same fiscal year in production data:
- `gp_2023-02-01_2024-01-31` (FYE=1 convention)
- `gp_2023-03-01_2024-02-29` (FYE=2 convention)

This creates duplicate GuidancePeriod nodes for the same quarter — ~28 day offset between them. Data is usable but inconsistent — guidance items for the same quarter can land on different period nodes.

Scope:
- 4 of 18 affected retailers currently have guidance data: FIVE (468), ASO (387), LULU (355), DLTR (351) = 1,561 items
- 1,561 / 5,227 total GuidanceUpdate nodes = **~29.9% of all guidance data is from affected tickers**
- Within those tickers, ~15-27% of items use the FYE=1 convention instead of FYE=2:
  - ASO: 55 FYE=1 vs 269 FYE=2 (17.0% of XBRL-dated items on alternate convention; 14.2% of all ASO guidance)
  - DLTR: 90 FYE=1 vs 158 FYE=2 (36.3% of XBRL-dated items; 25.6% of all DLTR guidance)
  - FIVE: 28 FYE=1 vs 266 FYE=2 (9.5% of XBRL-dated items; 6.0% of all FIVE guidance)
- **~173 items (~3.3% of all guidance) are on the wrong period convention**
- The remaining 14 of 18 retailers have no guidance yet — when processed, the affected share grows
- **High estimate: ~30% of guidance data is from tickers where this bug can produce inconsistent period boundaries (~28-day offset)**

**Inherent accuracy limit:** Even with a correct FYE input, `_compute_fiscal_dates()` always returns month boundaries (1st to last day of month). For 52-week calendar companies (AAPL, COST, TSLA, retailers), actual quarter boundaries are ±5 days off from month boundaries. This is inherent to the function's design (`fiscal_math.py:105`: "Gives standard month boundaries") and can only be solved by the XBRL Period lookup path (which is what `fiscal_to_dates()` and `fiscal_resolve.py` attempted, but those are dead code). So the best-case accuracy for the live `build_guidance_period_id()` path is **±5 days even if the FYE input is fixed.**

**Test gap:** There are no targeted Jan/Feb retailer tests around `build_guidance_period_id()` in `test_guidance_ids.py` or `test_guidance_write_cli.py`. Existing 146 tests all pass but do not cover this edge case.

### 2. `fiscal_to_dates()` in `get_quarterly_filings.py:70`

**Status: DEAD CODE — runtime-dead, but not fully removable without doc cleanup**

~175-line function + 2 module-level caches (`_FYE_CACHE`, `_PERIOD_SCAN_CACHE`) only used within this function. Was intended for the earnings orchestrator's "actuals comparison" feature (not yet built). Queries Neo4j Period nodes and classifies them using `period_to_fiscal()` with the raw FYE. Has additional XBRL Period lookup/classification logic NOT shared with the live guidance path.

**If deleted, also becomes dead:**
- `timedelta` import (line 27) — only used inside `fiscal_to_dates()` at lines 200, 220
- `calendar` import (line 28) — already dead now (imported but `calendar.` never called anywhere in the file)

**Measured impact (empirical, not theoretical):**
- ANF FY2023 Q4: returns Oct 2022 - Jan 2023 (off by 1 year — should be Oct 2023 - Jan 2024)
- CAKE FY2023 Q4: returns a 462-day period (should be ~90 days)
- AAPL FY2024 Q1: correct

**No production impact** since nothing calls it. Runtime-dead: zero callers, zero importers. Full removal requires cleaning stale doc references:
- `guidance-extraction-flow.html:570, :812, :878, :927` — HTML doc references
- `.claude/plans/guidanceInventory.md:917` — plan doc describing it as "kept for future actuals comparison"

### 3. `fiscal_resolve.py` (CLI wrapper)

**Status: DEAD CODE — runtime-dead, but doc-exposed (NOT safe to delete without doc cleanup)**

220-line CLI wrapper that replicates `fiscal_to_dates()` Phase 1 logic using pre-fetched Period data via stdin. Has its own XBRL Period lookup/classification logic (same as `fiscal_to_dates()`, different from the live guidance path).

**Doc references that could cause LLM agents to invoke it:**
- `.claude/skills/extract/queries-common.md:72-74` — usage example with bash invocation
- `.claude/skills/guidance-inventory/QUERIES.md:67-69` — same pattern
- `.claude/plans/Extractions/extraction-pipeline-reference.md:238` — pipeline reference table

**No current production impact.** NOT safe to delete until doc references are removed first (agent could read docs and call it). Companion `test_fiscal_resolve.py` (29 tests) should be deleted with it.

**If deleted, stale docstring in `fiscal_math.py:4-5`:** Currently says "Extracted from get_quarterly_filings.py to allow clean imports from guidance_ids.py, fiscal_resolve.py, and any future consumer". Would need update to remove the `fiscal_resolve.py` reference.

### 4. `_compute_fiscal_dates()` in `fiscal_math.py:102`

**Status: LIVE — called by `build_guidance_period_id()`. Also called by `fiscal_resolve.py` (dead code).**

The pure math function that converts (fye_month, fiscal_year, fiscal_quarter) → (start_date, end_date). Uses standard month boundaries (e.g., Q1 = first 3 months after FYE). This function itself is correct GIVEN correct inputs — the issue is that its callers pass the wrong FYE month (raw instead of adjusted).

**Important distinction:** The live guidance issue comes from `_compute_fiscal_dates()` (deterministic month-boundary math), NOT from the XBRL Period lookup/classification logic that exists in `fiscal_to_dates()` and `fiscal_resolve.py`. Those are dead code with additional complexity (Period node scanning, `period_to_fiscal()` classification). The live path is simpler but shares the same FYE input problem.

### 5. `period_to_fiscal()` in `fiscal_math.py:13`

**Status: LIVE — fallback path in `get_quarterly_filings.py` (4% of rows), classification in `fiscal_to_dates()` and `fiscal_resolve.py` (both dead)**

The function that converts a period end date → fiscal label. Has the 52-week day≤5 adjustment built in, but it receives the raw FYE from callers. The 52-week adjustment fixes the QUARTER but not the YEAR for retailers with FYE in months 1-5.

For `get_quarterly_filings.py`, this only matters for the ~4% fallback path (filings without XBRL). For the dead code paths, it would cause year-off-by-one for retailers if those paths were ever revived.

### 6. `get_derived_fye()` in `get_quarterly_filings.py:244`

**Status: LIVE — called once per ticker per invocation**

The FYE derivation query that uses raw 10-K period months. The root source of Issue A. If this were fixed to apply the 52-week adjustment (day ≤ 5 → previous month), it would resolve the FYE=2→FYE=1 issue for all 18 retailers.

**Risk of fixing:** Changing FYE derivation affects ALL downstream consumers — `period_to_fiscal()` fallback, `_compute_fiscal_dates()` dates, `build_guidance_period_id()` period IDs. Any existing GuidancePeriod nodes with FYE=2-derived dates would become orphaned (new extractions would create FYE=1-derived period IDs that don't match).

---

## Functions NOT Affected

| Function | Why safe |
|---|---|
| `parse_xbrl_fiscal_identity()` | Reads XBRL directly, no math |
| `should_use_xbrl_fiscal()` | Compares two labels, no FYE dependency |
| `guidance_writer.py` | Writes to Neo4j, doesn't compute periods |
| `concept_resolver.py` | XBRL concept matching, no fiscal math |
| `warmup_cache.py` | Cache pre-fetch, no fiscal math |
| `guidance_trigger_daemon.py` | Queries `guidance_status`, no fiscal math |
| `extraction_worker.py` | Queue consumer, no fiscal math |

---

## Summary of Production Impact

| Path | Status | Issue | Severity |
|---|---|---|---|
| `get_quarterly_filings.py` fiscal labeling | **FIXED** | XBRL-direct bypasses bad math for 96% of rows | Resolved |
| `get_quarterly_filings.py` dedup | **FIXED** | Min-lag replaces stale 218-ticker list | Resolved |
| `build_guidance_period_id()` | **LIVE BUG** | ~28-day period offset for 18 retailers, creates duplicate GuidancePeriod nodes. ~3.3% of guidance items on wrong convention. | Low — data usable but inconsistent |
| `fiscal_to_dates()` | **DEAD CODE** | Off by 1 year for retailers, 462-day period for CAKE | None — runtime-dead, full removal needs doc cleanup |
| `fiscal_resolve.py` | **DEAD CODE** | Same class of issues as fiscal_to_dates (different code path) | None — runtime-dead, doc-exposed, removal needs doc cleanup first |

---

## Open Questions (Not Yet Answered)

1. **Can we fix `get_derived_fye()` without breaking existing GuidancePeriod nodes?** If we change FYE=2→FYE=1 for retailers, all new period IDs will differ from existing ones. Need a migration plan for the ~72 affected period nodes.

2. **`CurrentFiscalYearEndDate` is NOT a reliable FYE fix.** Verified in Neo4j: for ANF, PLCE, RH, FIVE, LULU, ASO, DLTR, the XBRL `CurrentFiscalYearEndDate` bounces between `--01-28`, `--02-01`, `--02-03` across consecutive 10-Ks for the same ticker. Extracting the month from this field gives 1 or 2 depending on the filing, which is the same instability as the raw `periodOfReport`. This is not a proof-grade fix.

3. **Is the year labeling convention (Issue B) a real problem for guidance?** The guidance extraction agent labels fiscal years based on what the company says in its filings. If the company says "Fiscal 2024" and `_compute_fiscal_dates` interprets that differently from the company's convention, the dates will be off by a year. Empirically, ASO and DLTR already show mixed `gp_...` conventions in production data — "usable but inconsistent" is the accurate description, not "happens to align."

4. **`fiscal_to_dates()` removal plan.** Runtime-dead (zero callers, zero importers). Full removal requires:
   - Delete function + caches (`_FYE_CACHE`, `_PERIOD_SCAN_CACHE`) from `get_quarterly_filings.py`
   - Clean `timedelta` import (becomes dead; `calendar` import is already dead)
   - Update 5 stale doc references: `guidance-extraction-flow.html:570, :812, :878, :927` and `guidanceInventory.md:917`

5. **`fiscal_resolve.py` removal plan.** Runtime-dead (zero Python/shell callers). Full removal requires:
   - Delete `fiscal_resolve.py` + `test_fiscal_resolve.py`
   - Remove 4 doc references: `queries-common.md:72-74`, `guidance-inventory/QUERIES.md:67-69`, `extraction-pipeline-reference.md:238`, `docs/extraction-pipeline-visual.html:687`
   - Update `fiscal_math.py:4-5` docstring (references `fiscal_resolve.py`)

6. **Docs are internally inconsistent.** Some plan docs (guidanceInventory.md §6, §15) still describe the old fiscal-keyed/no-date-computation design ("simple string concatenation", "no `fiscal_resolve.py` dependency"), while the current v3.1 code and contract (core-contract.md:394, :442) use calendar-based `gp_{start}_{end}` with `_compute_fiscal_dates()`. The docs should be reconciled to reflect the current reality: the guidance pipeline DOES use date math via `build_guidance_period_id()`.

7. **Test gap.** No targeted Jan/Feb retailer tests exist for `build_guidance_period_id()` in `test_guidance_ids.py` (557 lines) or `test_guidance_write_cli.py` (320 lines). Existing 146 tests all pass but do not exercise the FYE=2 vs FYE=1 edge case.

---

## Empirical Validation & Proven Fix: XBRL Period Lookup (2026-03-20)

### Correction: Bug Scope Is 41 Tickers, Not 18

The original analysis (above) claimed 18 retailers were affected. Comprehensive empirical testing across **2,196 10-K filings for 772 tickers** proves the actual scope is **41 tickers across two code paths**.

**Methodology**: For every 10-K filing in Neo4j, compute raw month from `periodOfReport` and the day≤5-adjusted month. Compare mode (for `get_derived_fye()`) and latest-filing month (for guidance extraction path) against the adjusted month.

**Two code paths, two different scopes:**

| Code Path | How it gets FYE | Affected | Bug mechanism |
|---|---|---|---|
| `get_derived_fye()` in `get_quarterly_filings.py:244` | Mode of all 10-K `periodOfReport` months | **29 tickers** | Mode flips when majority of filings have day≤5 |
| Guidance extraction (Query 1B in `queries-common.md`) → `build_guidance_period_id()` in `guidance_ids.py:376` | Latest single 10-K `periodOfReport` month | **36 tickers** | Latest filing has day≤5 regardless of mode |
| **Union (either path)** | | **41 tickers** | |

**Complete affected ticker list (29 mode-affected marked with `M`, 12 guidance-only with `G`):**

| Ticker | Path | Raw FYE → Correct FYE | Sector |
|---|---|---|---|
| ANF | M+G | 2→1 | Retail |
| ASO | M+G | 2→1 | Retail |
| BJ | M+G | 2→1 | Retail |
| BURL | M+G | 2→1 | Retail |
| DKS | M+G | 2→1 | Retail |
| DLTR | M+G | 2→1 | Retail |
| FIVE | M+G | 2→1 | Retail |
| GME | M+G | 2→1 | Retail |
| KR | M+G | 2→1 | Retail |
| KSS | M+G | 2→1 | Retail |
| OLLI | M+G | 2→1 | Retail |
| OXM | M+G | 2→1 | Retail |
| PLAY | M+G | 2→1 | Retail |
| PLCE | M+G | 2→1 | Retail |
| PVH | M+G | 2→1 | Retail |
| RH | M+G | 2→1 | Retail |
| ROST | M+G | 2→1 | Retail |
| ULTA | M+G | 2→1 | Retail |
| BBY | M+G | 2→1 | Retail |
| TJX | M+G | 2→1 | Retail |
| LOW | M+G | 2→1 | Home improvement |
| DELL | M+G | 2→1 | Technology |
| IOT | M+G | 2→1 | IoT/Technology |
| MRVL | M+G | 2→1 | Semiconductors |
| PSTG | M+G | 2→1 | Data storage |
| SAIC | M+G | 2→1 | Defense/IT |
| ADBE | M only | 12→11 | Software |
| CAKE | M only | 1→12 | Restaurants |
| COST | M only | 9→8 | Retail/Wholesale |
| ADI | G only | 11→10 (latest only) | Semiconductors |
| AVGO | G only | 11→10 (latest only) | Semiconductors |
| CBRL | G only | 8→7 (latest only) | Restaurants |
| CHWY | G only | 2→1 (latest only) | E-commerce |
| CIEN | G only | 11→10 (latest only) | Networking |
| CNM | G only | 2→1 (latest only) | Distribution |
| EXEL | G only | 1→12 (latest only) | Biotech |
| KBR | G only | 1→12 (latest only) | Defense |
| LEVI | G only | 12→11 (latest only) | Apparel |
| LULU | G only | 2→1 (latest only) | Retail |
| TRMB | G only | 1→12 (latest only) | Technology |
| UNFI | G only | 8→7 (latest only) | Food distribution |

**Why the original 18 was wrong**: The original analysis only checked FYE=2→1 (Jan/Feb boundary retailers). The bug is month-agnostic — any 52-week company whose fiscal period crosses a month boundary with day≤5 is affected. Examples: ADBE (Dec→Nov), CAKE (Jan→Dec), COST (Sep→Aug).

**Notable: LULU** was listed in the original doc as having affected guidance data but was NOT in the 18-ticker list. Empirically confirmed: LULU's mode is correct (FYE=1) but its latest 10-K has day=2 → raw month=2 → guidance path gets wrong FYE=2. The guidance path and mode path are genuinely different.

**15 additional at-risk tickers** have the day≤5 pattern in historical filings but are safe today by vote margin. Their next 10-K filing could flip them: BOOT, DNUT, HAE, ILMN, MSM, PFGC, QDEL, QRVO, RL, SBUX, SFM, SYY, TDY, UTZ, VFC.

### Neo4j Graph Model for Period Nodes

The XBRL Period lookup uses this graph chain:

```
(Context)-[:FOR_COMPANY]->(Company)    — links XBRL data to a ticker
(Context)-[:HAS_PERIOD]->(Period)      — links to the reporting period
(Fact)-[:IN_CONTEXT]->(Context)        — individual XBRL facts
(Fact)-[:HAS_PERIOD]->(Period)         — direct shortcut
```

**Period node properties:**
- `id` / `u_id`: e.g. `duration_2024-02-04_2025-02-02`
- `period_type`: `duration` (for date ranges) or `instant` (balance sheet dates)
- `start_date`: string, e.g. `2024-02-04`
- `end_date`: string, e.g. `2025-02-02`

**No fiscal labels on Period nodes.** They only have raw dates. Fiscal quarter assignment must be derived from the date structure (annual periods define FY boundaries, quarterly periods chain within them).

**Total in graph**: 9,919 Period nodes (7,143 duration, 2,776 instant). 12.9M `HAS_PERIOD` relationships.

### Proven Fix: DEI-Anchored YTD Differencing Algorithm (v3 — 2026-03-21)

**Purpose**: Replace `_compute_fiscal_dates()` in `build_guidance_period_id()` with exact dates from XBRL Period nodes, eliminating both the wrong-FYE bug AND the ±5-day month-boundary approximation.

**Version history:**
- v1: dei context_id join → 60% (dei facts label the filing, not the context — comparative year contexts leak)
- v2: periodOfReport → Period end_date matching → 99.98% core / 92.3% routing (FY label mapping unsolved)
- **v3: DEI-anchored YTD differencing → 100.00% on all derived quarters, 100.0% affected 41** ← current

**The v3 insight**: v2 failed the routing step (fy_label → correct Period) because it used approximate dates + offset tables. v3 solves this by going through the **actual graph path**: `Report → HAS_XBRL → XBRLNode ← REPORTS ← Fact → IN_CONTEXT → Context → HAS_PERIOD → Period`. This binds dei facts to the **same Context node** as the Period, not by string matching. It also correctly handles Q2/Q3 as YTD periods and derives standalone quarters by differencing adjacent YTD endpoints.

**Algorithm — single Cypher query:**

```cypher
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType IN ['10-K', '10-Q']
  AND r.periodOfReport IS NOT NULL

CALL {
  WITH r, c
  -- Traverse the actual graph path: Report → XBRL → Fact → Context → Period
  MATCH (r)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(fy:Fact
    {qname:'dei:DocumentFiscalYearFocus'})-[:IN_CONTEXT]->(ctx:Context)-[:FOR_COMPANY]->(c)
  MATCH (fp:Fact {qname:'dei:DocumentFiscalPeriodFocus'})-[:IN_CONTEXT]->(ctx)
  MATCH (ctx)-[:HAS_PERIOD]->(p:Period {period_type:'duration'})
  WITH
    collect(DISTINCT fy.value) AS fys,
    collect(DISTINCT fp.value) AS fps,
    collect(DISTINCT {start:p.start_date, end:p.end_date}) AS periods
  -- Require unambiguous dei identity: exactly one FY label, one FP label, one Period
  WHERE size(fys) = 1 AND size(fps) = 1 AND size(periods) = 1
  RETURN
    head(fys) AS fiscal_year_label,
    head(fps) AS fiscal_period_label,
    head(periods).start AS ctx_period_start,
    head(periods).end AS ctx_period_end
}

-- Group by fiscal year, collect all quarter filings
WITH c.ticker AS ticker, fiscal_year_label,
  collect({fp: fiscal_period_label, ctx_start: ctx_period_start,
           ctx_end: ctx_period_end, filing_period_end: r.periodOfReport}) AS rows

-- Extract individual quarter YTD periods
WITH ticker, fiscal_year_label,
  head([x IN rows WHERE x.fp = 'Q1' | x]) AS q1,
  head([x IN rows WHERE x.fp = 'Q2' | x]) AS q2_ytd,
  head([x IN rows WHERE x.fp = 'Q3' | x]) AS q3_ytd,
  head([x IN rows WHERE x.fp = 'FY' | x]) AS fy

-- Derive standalone quarters by differencing adjacent YTD endpoints
UNWIND [
  CASE WHEN q1 IS NOT NULL THEN
    {quarter:'Q1', start_date:q1.ctx_start, end_date:q1.ctx_end, basis:'direct'}
  END,
  CASE WHEN q1 IS NOT NULL AND q2_ytd IS NOT NULL THEN
    {quarter:'Q2', start_date:q1.ctx_end, end_date:q2_ytd.ctx_end, basis:'ytd_diff'}
  END,
  CASE WHEN q2_ytd IS NOT NULL AND q3_ytd IS NOT NULL THEN
    {quarter:'Q3', start_date:q2_ytd.ctx_end, end_date:q3_ytd.ctx_end, basis:'ytd_diff'}
  END,
  CASE WHEN q3_ytd IS NOT NULL AND fy IS NOT NULL THEN
    {quarter:'Q4', start_date:q3_ytd.ctx_end, end_date:fy.ctx_end, basis:'fy_diff'}
  END
] AS qtr
WITH ticker, fiscal_year_label, qtr WHERE qtr IS NOT NULL

RETURN ticker, fiscal_year_label, qtr.quarter, qtr.start_date, qtr.end_date, qtr.basis
ORDER BY fiscal_year_label DESC, qtr.quarter
```

**Why this works (v2 and v1 failures resolved):**

| Problem | v1/v2 failure | v3 fix |
|---|---|---|
| dei facts label the filing, not the context | v1 joined by `context_id` string → comparative year contexts leaked | v3 traverses the graph: `Report → HAS_XBRL → XBRLNode ← REPORTS ← Fact → IN_CONTEXT → Context`. The Report→XBRLNode→Fact chain ensures the dei fact belongs to THIS filing only. |
| Q2/Q3 dei contexts are YTD, not standalone | v2 tried to match approximate dates to standalone quarterly Periods → FY label mapping problem | v3 uses YTD endpoints and derives standalone quarters: Q2 = Q1.end → Q2_YTD.end |
| FY label convention varies by ticker | v2 needed per-ticker offset table (92.3% for affected) | v3 reads `DocumentFiscalYearFocus` directly from the filing's own XBRL → the company's label, no offset needed |
| Ambiguous dei (multiple contexts per filing) | v1 got wrong period matches | v3 filters: `size(fys) = 1 AND size(fps) = 1 AND size(periods) = 1` — drops ambiguous filings |
| Quarter boundary convention | v2 used ±3d tolerance, sometimes matched wrong quarter | v3 uses exact boundary chaining: Q2.start = Q1.end (graph's own convention, 100% chain accuracy) |

**Derivation rules:**
- **Q1**: Direct from Q1 10-Q's dei context period (start and end)
- **Q2**: start = Q1 context end, end = Q2 YTD context end
- **Q3**: start = Q2 YTD context end, end = Q3 YTD context end
- **Q4**: start = Q3 YTD context end, end = FY context end (from 10-K)

This preserves the graph's boundary convention (Q2.start = Q1.end, not Q1.end + 1 day).

**Fallback for filings without XBRL (24 tickers, none affected):**
Use `_compute_fiscal_dates()` with corrected FYE month (day≤5 adjustment).

**Fallback for future periods (forward guidance "FY2027"):**
Use `_compute_fiscal_dates()` with corrected FYE from latest known XBRL data.

### Empirical Validation Results (v3)

**Test methodology**: Run the v3 Cypher query for ALL tickers (no ticker filter). Cross-validate every derived quarter: (1) qtr_end ≈ filing periodOfReport ±3d, (2) quarter span 60-130d, (3) quarter chaining (Q1.end = Q2.start).

| Metric | Count | Rate |
|---|---|---|
| **Derived quarters** | **6,828** | — |
| Matched (qtr_end ≈ filing period ±3d) | 6,828 | **100.00%** |
| Mismatched | 0 | 0% |
| Quarter chain checks | 4,334 | **100.00%** |
| Tickers at 100% | 772 | **772/772** |

**Affected 41 tickers — all 100%:**

All 41 affected tickers produce correct quarters with zero mismatches. Every ticker: ✓ (353/353 quarters validated).

**Basis distribution:** direct Q1 context: 2,164 | YTD differencing (Q2/Q3): 3,216 | FY differencing (Q4): 1,448

**Filing coverage:** 6,828/8,053 filings (84.8%) produce derived quarters. The 1,225 uncovered are: older filings without HAS_XBRL relationships, filings where dei facts are ambiguous (size > 1 filter), and partial FYs missing prerequisite quarters for YTD differencing.

**19 span anomalies:** 19 derived quarters have negative or oversized spans (start > end, or > 130 days). These are from comparative data leaks in a few tickers (APO, ARES, AVAV, BMBL, CAKE FY2023 Q4, CRWD, DELL FY2024 Q4, ESTC, KHC). The end dates are correct (matched filing ±3d) but the start dates are wrong. **Filter:** reject any quarter where `end_date - start_date < 60 or > 130 days` and fall back to corrected FYE for that specific quarter. Of the 41 affected tickers, only CAKE (1 quarter) and DELL (1 quarter) have this issue.

**v3 vs v2 comparison:**

| Metric | v2 (periodOfReport matching) | v3 (DEI-anchored YTD diff) |
|---|---|---|
| Core accuracy | 99.98% (8,051/8,053) | **100.00%** (6,828/6,828) |
| Affected 41 accuracy | 99.8% (422/423) | **100.0%** (353/353) |
| FY label routing | 92.3% (needed offset table) | **N/A** (FY label from XBRL directly) |
| Quarter chaining | Not tested | **100.00%** (4,334/4,334) |
| Filing coverage | 99.98% (8,051/8,053) | 84.8% (6,828/8,053) |
| Requires offset table | Yes (51 mixed tickers) | **No** |
| Requires approximate→exact search | Yes (45d window) | **No** (exact from graph) |

v3 trades some coverage (84.8% vs 99.98%) for perfect accuracy and zero offset/routing complexity. The 15.2% uncovered filings fall to v2 (direct periodOfReport matching) or corrected FYE fallback.

**SUPERSEDED — see "SEC API Approach (v4)" section below for the finalized fix.**

**Previous approach — 3-tier graph cascade (v3, kept for reference and offline fallback):**

```
Tier 1 — v3 XBRL exact (for quarters with filed 10-Q/10-K + XBRL processed):
  Run v3 query → lookup table of (fiscal_year_label, quarter) → (start_date, end_date)
  Accuracy: 99.7% on 6,828 derived quarters (19 span anomalies filterable).
  ±1d offset (XBRL "day after" convention).

Tier 2 — Previous quarter end + historical length (for current/forward quarters from 8-K/transcript):
  When v3 doesn't have the requested quarter (10-Q not yet filed):
    start = previous quarter's end_date (exact, from v3 Tier 1)
    end = start + median historical length for this (ticker, quarter_number)
  Accuracy: 98.4% within ±1d, 99.21% within ±3d, 99.77% within ±7d.
  Tested on 5,673 quarters across all 772 tickers.
  13 failures (0.23%) — all Q1 predictions where prev FY Q4 has a span anomaly.
    These 13 are ±364d off (full year), NOT ±7d — they fall to Tier 3.

Tier 3 — Corrected FYE month-boundary math (last resort):
  When no v3 data exists at all (24 tickers without XBRL, new tickers, span anomaly Q1s):
  Use _compute_fiscal_dates() with corrected FYE (day≤5 adjustment).
  Accuracy: ±3-5d for uniform 13-week companies, ±11-24d for irregular (COST, KR).
  None of the 24 no-XBRL tickers are in the affected 41, so Tier 3 is correct for them.
```

**Why Tier 2 is critical**: 8-Ks and transcripts are the PRIMARY sources of guidance data (56% of existing guidance items are from transcripts). They fire BEFORE the current quarter's 10-Q is filed (40-day gap). Without Tier 2, every current-quarter guidance item from a transcript or 8-K would hit Tier 3 (±3-24d). With Tier 2, they get ±0-1d for 98.4% of cases.

**Tier 2 empirical validation (tested 2026-03-21):**

| Metric | Result |
|---|---|
| Quarters tested | 5,673 |
| Start date accuracy | 100% (prev Q end = current Q start by graph construction) |
| End ±0d (exact) | 87.6% (4,971 quarters) |
| End ±1d cumulative | 98.4% (5,580 quarters) |
| End ±3d cumulative | 99.21% (5,628 quarters) |
| End ±7d cumulative | 99.77% (5,660 quarters) |
| End >7d | 0.23% (13 quarters — all ±364d, fall to Tier 3) |
| FYs with all quarters ±7d | 99.7% (2,131/2,138) |

**One assumption in Tier 2**: Quarter lengths are stable across fiscal years for the same ticker. FIVE Q3 = 91d in FY2023, FY2024, FY2025 → predict FY2026 Q3 = 91d. This held for 99.77% of tested quarters. Breaks during 53-week year transitions (~1 quarter per ticker per 6 years, ±7d).

**Historical quarter length computation**: For each (ticker, quarter_number), take the median span across all v3-derived quarters for that ticker. Distribution: 84d (4-4-5 companies like COST), 89-93d (52-week companies), 112d (4-5-4 Q1 like KR). The median is stable — quarter lengths are structurally determined by the fiscal calendar.

### Known Limitations & Failures (fully honest, 2026-03-21)

**v3 Tier 1 known failures — 19 span anomalies across 17 tickers:**

Root cause: FY label collision — a ticker's 10-K and Q1 10-Q both have the same `dei:DocumentFiscalYearFocus` value but belong to DIFFERENT actual fiscal years (the 10-K ending Feb 2024 and the Q1 starting Feb 2024 both labeled "FY2024"). The v3 query groups them together, producing a Q4 with negative span (start after end).

Affected tickers: APO, ARES, AVAV, BMBL, CAKE, CRWD, DELL, ESTC, KHC, KR, NUE, OLLI, PFGC, PLCE, RH, WMS, ZS. Of the 41 FYE-affected tickers: CAKE (1 quarter), DELL (1), KR (1), OLLI (1), PLCE (1), RH (2) = 7 quarters across 6 tickers.

**Not fixable with ORDER BY** — tested 2026-03-21. The collision is in the company's own dei labeling (inconsistent FY convention between 10-K and 10-Q filings), not duplicate selection. Detection: any derived quarter with `span < 60 or > 130` is a span anomaly → filter and fall to Tier 2/3.

**Tier 2 → Tier 3 cascade for span-anomaly tickers:**

When Q4 has a span anomaly, Q1 of the NEXT FY cannot use Tier 2 (prev Q4 end is wrong). Falls to Tier 3:

| Ticker | Quarter affected | Tier 3 accuracy | Why |
|---|---|---|---|
| KR | FY2025 Q1 | **±24d** | 16-week Q1, Tier 3 assumes 3-month = ±24d off |
| COST | (not Q1 affected) | N/A | COST Q4 anomaly doesn't propagate to next Q1 |
| CAKE | FY2024 Q1 | ±5d | Uniform 13-week, Tier 3 is decent |
| DELL | FY2025 Q1 | ±5d | Same |
| OLLI | FY2025 Q1 | ±5d | Same |
| PLCE | FY2025 Q1 | ±5d | Same |
| RH | FY2024 Q1, FY2025 Q1 | ±5d | Same |

**KR is the single worst-case ticker**: FY label collision + irregular calendar (16-week Q1) + Tier 3 inadequate for Q1. The ±24d error on KR Q1 is the worst residual error in the entire system. All other affected tickers get ±5d or better at Tier 3.

**What has NOT been tested end-to-end:**

- Actual transcript guidance extraction through `build_guidance_period_id()` → Tier 2 prediction. The 99.77% is from a simulation (predicting v3 quarters from other v3 quarters), not from real transcript processing.
- The 37 duplicate (ticker, fy_label, fp_label) groups in v3 — `head()` without deterministic ordering. Adding `ORDER BY r.periodOfReport DESC` was tested but does not fix FY label collisions.
- Integration with the guidance trigger daemon's race condition handling (HAS_XBRL gate).

### Worst-Case Summary (all scenarios)

| Scenario | Frequency | Error | Detection |
|---|---|---|---|
| Normal case, XBRL available (Tier 1) | ~85% of filings | **±1d** | N/A — correct |
| Normal case, 8-K/transcript current Q (Tier 2) | ~14% of filings | **±0-1d** | N/A — correct |
| 53-week year quarter (Tier 2 assumption breaks) | ~1 Q per ticker per 6 years | **±7d** | Detectable after 10-Q files |
| Span anomaly → Tier 3, uniform calendar | 7 quarters across 6 affected tickers | **±3-5d** | span < 60 or > 130 filter |
| **KR Q1 via Tier 3 (worst single case)** | **1 ticker, 1 quarter per FY** | **±24d** | span filter on prev Q4 |
| 24 no-XBRL tickers | 24 tickers, none affected | **0d** | All calendar-month-end |
| Brand new ticker, first quarter | Rare | **±3-5d** | No historical data available |
| No XBRL processing for >2 years | All tickers | **accumulating ±4d/year** | Detectable by checking v3 staleness |

### Data Freshness & Race Condition

**Current state (Aug 2025 XBRL cutoff):** SEC report ingestion stopped Aug 2025. Filings ingested before then have full XBRL data → v3 works. Filings after have Report nodes but no HAS_XBRL → v3 returns nothing, falls to corrected FYE (approximate ±3-5d). **Recommendation**: reprocess XBRL before deploying to avoid duplicates.

**Ongoing race condition (even with XBRL fully up-to-date):**

This is not just a one-time data gap — it's a permanent race condition in the pipeline:

1. New filing arrives → Report node created immediately
2. XBRL processing runs (creates HAS_XBRL, Fact, Context, Period nodes) — takes time
3. Guidance trigger daemon polls every 60s → may fire BEFORE XBRL processing completes
4. `build_guidance_period_id()` called → v3 query finds NO XBRL for the new filing → falls to corrected FYE → approximate dates → `gp_2026-02-01_2026-04-30`
5. Later, XBRL processes → v3 now returns exact dates → `gp_2026-02-02_2026-05-04`
6. Next guidance item for the same quarter → different GuidancePeriod node → **duplicate**

This is the same class of bug (duplicate GuidancePeriod nodes) just with a smaller offset (±3-5d instead of ±28d).

**Fix options (choose one):**

| Option | How | Tradeoff |
|---|---|---|
| **A. XBRL gate on guidance trigger** | Guidance trigger daemon checks `(r)-[:HAS_XBRL]->()` exists before enqueuing a filing for extraction. Filing without HAS_XBRL is skipped (picked up next sweep after XBRL processes). | Simple. Adds up to 60s + XBRL processing time delay to guidance extraction. Best option — guaranteed no race. |
| B. Two-phase write | `build_guidance_period_id()` always uses corrected FYE first, then a post-XBRL reconciliation job merges approximate → exact nodes. | Complex. Requires migration logic. |
| C. Accept and migrate | Extract with approximate dates. After XBRL processes, run a one-time fix to update GuidancePeriod nodes. | Technical debt. Requires knowing which nodes are approximate. |

**Recommendation: Option A.** Add to the guidance trigger daemon's eligibility query:
```cypher
AND EXISTS { MATCH (r)-[:HAS_XBRL]->() }
```
This ensures no filing is sent to extraction until its XBRL data is available. The v3 query then always has complete data. Zero race condition.

### What This Fix Eliminates

1. **Issue A (wrong FYE input)**: Completely bypassed. Path A uses Period node dates directly — no FYE derivation needed.
2. **Issue B (±5-day month-boundary approximation)**: Replaced with exact dates. Example for FIVE FY2025 Q1:
   - Current `_compute_fiscal_dates(fye=2, fy=2025, q="Q1")` → `2024-03-01 → 2024-05-31` (wrong FYE + approximate)
   - Path A → `2024-02-04 → 2024-05-05` (exact, 26 days more accurate on both ends)

### Reproducing This Validation

All queries used Neo4j Cypher against the live graph. To reproduce:

**Query 1 — 10-K filing data (FYE bug scope test):**
```cypher
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company)
WHERE r.formType = '10-K' AND r.periodOfReport IS NOT NULL
WITH c.ticker AS ticker, r.periodOfReport AS period,
     date(r.periodOfReport).year AS yr,
     date(r.periodOfReport).month AS raw_month,
     date(r.periodOfReport).day AS day, r.accessionNo AS accession
RETURN ticker, period, yr, raw_month, day, accession
ORDER BY ticker, period
```

**Query 2 — Quarterly Period data:**
```cypher
MATCH (ctx:Context)-[:FOR_COMPANY]->(c:Company)
MATCH (ctx)-[:HAS_PERIOD]->(p:Period {period_type: 'duration'})
WITH c.ticker AS ticker, p.start_date AS sd, p.end_date AS ed,
     duration.inDays(date(p.start_date), date(p.end_date)).days AS span
WHERE span >= 80 AND span <= 100
WITH DISTINCT ticker, sd, ed, span
RETURN ticker, sd, ed, span ORDER BY ticker, sd
```

**Query 3 — Annual Period data:** Same as Query 2 with `span >= 350 AND span <= 380`.

**Query 4 — All 10-K + 10-Q filings:**
```cypher
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company)
WHERE r.formType IN ['10-K', '10-Q'] AND r.periodOfReport IS NOT NULL
RETURN c.ticker AS ticker, r.formType AS form, r.periodOfReport AS period,
       date(r.periodOfReport).year AS yr,
       date(r.periodOfReport).month AS mo,
       date(r.periodOfReport).day AS dy
ORDER BY ticker, period
```

**Query 5 — XBRL fiscal identity (for FY label mapping test):**
```cypher
MATCH (fy_fact:Fact {qname: 'dei:DocumentFiscalYearFocus'})
MATCH (fy_fact)-[:IN_CONTEXT]->(ctx:Context)-[:FOR_COMPANY]->(c:Company)
MATCH (fp_fact:Fact {qname: 'dei:DocumentFiscalPeriodFocus'})
WHERE fp_fact.context_id = fy_fact.context_id
MATCH (ctx)-[:HAS_PERIOD]->(p:Period {period_type: 'duration'})
WITH c.ticker AS ticker, fy_fact.value AS fiscal_year_label,
     fp_fact.value AS fiscal_period_label,
     p.start_date AS ctx_period_start, p.end_date AS ctx_period_end,
     duration.inDays(date(p.start_date), date(p.end_date)).days AS ctx_span
WHERE ctx_span >= 80
RETURN DISTINCT ticker, fiscal_year_label, fiscal_period_label,
       ctx_period_start, ctx_period_end, ctx_span
ORDER BY ticker, fiscal_year_label, fiscal_period_label
```

**Validation algorithm** (pseudocode):
```
For each filing (ticker, form, periodOfReport):
  1. find_qtr(ticker, periodOfReport, tolerance=3):
     scan quarterly Periods for ticker, return one whose end_date is within ±3d
  2. If not found AND form == '10-K': derive_q4():
     find quarterly Period ending 60-130d before periodOfReport (= Q3),
     return {sd: Q3.ed, ed: periodOfReport}
  3. If not found: corrected FYE fallback (Path B)
  4. Validate: result.end_date within ±5d of periodOfReport
```

**Key files referenced:**
- `_compute_fiscal_dates()`: `.claude/skills/earnings-orchestrator/scripts/fiscal_math.py:102`
- `period_to_fiscal()`: `.claude/skills/earnings-orchestrator/scripts/fiscal_math.py:13`
- `get_derived_fye()`: `.claude/skills/earnings-orchestrator/scripts/get_quarterly_filings.py:244`
- `build_guidance_period_id()`: `.claude/skills/earnings-orchestrator/scripts/guidance_ids.py:376`
- Guidance FYE source: `.claude/skills/extract/queries-common.md` (Query 1B)
- 52-week edge cases docstring: `.claude/skills/earnings-orchestrator/scripts/fiscal_math.py:22-32`

### Independent SEC EDGAR Cross-Validation (2026-03-21)

**What this is:** An independent "second opinion" from the SEC itself. NOT used in the fix. Purely confirms our math is right.

**How it works:**
1. Ask SEC EDGAR for every company's declared `fiscalYearEnd` (from `data.sec.gov/submissions/CIK{cik}.json`)
2. Apply the same day<=5 adjustment to SEC's answer
3. Compare SEC's answer against our Neo4j-derived answer

**Results (738 tickers tested):**

| Metric | Count | Rate |
|---|---|---|
| SEC adjusted FYE == our adjusted FYE | **737** | **99.86%** |
| SEC adjusted FYE != our adjusted FYE | 1 (MSTR only) | 0.14% |
| SEC confirms raw FYE is wrong (day<=5 fixes it) | 32 tickers | -- |

- **MSTR mismatch**: company changed its fiscal year end (SEC says June, Neo4j has December). Not an algorithm error.
- **32 tickers**: SEC's own FYE, after day<=5 adjustment, disagrees with our raw mode but AGREES with our corrected mode. Independent proof the fix is right.
- **Why 32 not 41?** This test validates the MODE path only. The extra 9 in our 41 are "guidance-only" (latest filing wrong but mode correct) -- those match SEC because SEC agrees with the mode.

**Validation script:** `/tmp/sec_fye_scale_test.py` (reads `/tmp/neo4j_fye_data.json`, fetches SEC EDGAR, compares). Full results: `/tmp/sec_fye_full_results.json`.

---

## FINALIZED FIX: SEC API Approach (v4 — 2026-03-21)

**This is the finalized production approach.** The v3 graph-based cascade (above) is superseded — preserved for reference and as an offline fallback only.

### Why SEC API Replaces the 3-Tier Graph Cascade

Two SEC APIs solve both Issue A (wrong FYE) and Issue B (approximate boundaries) with zero anomalies:

**Issue 1 — Wrong FYE month → SEC Submissions API:**
```
URL: https://data.sec.gov/submissions/CIK{cik}.json
Field: fiscalYearEnd (MMDD format, e.g., "0201" = February 1st)
Apply day<=5: if DD <= 5, real FYE = MM - 1
Result: stable, correct FYE for every company (not mode-dependent, not latest-filing-dependent)
Tested: 737/738 match (99.86%). 1 mismatch (MSTR) = detectable FY change.
```

**Issue 2 — Approximate quarter boundaries → SEC XBRL Company Concept API:**
```
URL: https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/EarningsPerShareBasic.json
Each fact has: start, end, fy (fiscal year label), fp (Q1/Q2/Q3/Q4/FY)
Filter: standalone quarters (60-130d span, fp in Q1-Q4), deduplicate by (fy, fp, latest filed)
Result: exact (start_date, end_date) for every filed quarter
Tested: 739/739 tickers, 83,091 quarters, 100% coverage, zero anomalies
Fallback concept: NetIncomeLoss (for ~10 tickers without EarningsPerShareBasic)
Cross-validated: 27/27 quarters vs Neo4j v3 = exact start, end +1d (systematic convention diff)
```

**What the SEC approach eliminates vs the v3 graph approach:**

| Old problem | SEC approach |
|---|---|
| 19 span anomalies (FY label collisions) | **Gone** — per-fact periods, no FY grouping |
| KR Q1 ±24d worst case | **Gone** — SEC has KR's 111d Q1 exact dates |
| COST Q3 ±19d if Tier 3 | **Gone** — SEC has COST's 84d Q3 exact dates |
| XBRL reprocessing prerequisite (stopped Aug 2025) | **Gone** — SEC already processed all filings |
| HAS_XBRL gate on guidance trigger | **Gone** — no local XBRL dependency |
| 37 duplicate groups (head without ORDER BY) | **Gone** — deduplicate by (fy, fp, latest filed) |
| 84.8% filing coverage | **Gone** — SEC has 100% back to ~2009 |
| Complex v3 Cypher query | **Gone** — one HTTP call per ticker |

### Production Architecture

```
build_guidance_period_id(ticker, fiscal_year, fiscal_quarter):

  Step 1 — SEC quarter cache lookup (primary):
    Local cache (Redis, no TTL), populated by initial bootstrap + incremental via TradeReady scanner
    Key: (ticker, fy_label, quarter) → (start_date, end_date)
    Source: SEC XBRL Company Concept API
    Coverage: 83,091 quarters, 739 tickers, avg 112 quarters/ticker
    Accuracy: EXACT (±0d, or ±1d if using inclusive vs exclusive end convention)
    → If found: DONE. Return exact dates.

  Step 2 — Predict unfiled quarter (8-K/transcript current/forward guidance):
    start = previous quarter's end_date (exact, from Step 1 cache)
    end = start + median historical quarter length for (ticker, quarter_number)
    Accuracy: 98.4% within ±1d, 99.2% within ±3d
    One assumption: quarter lengths stable across FYs (breaks ±7d on 53-week transitions)
    → Return predicted dates.

  Step 3 — SEC FYE fallback (brand new ticker, no XBRL history):
    Fetch fiscalYearEnd from SEC submissions API
    Apply day<=5 → corrected FYE month
    Compute month-boundary dates via _compute_fiscal_dates()
    Accuracy: ±3-5d (uniform), ±11-24d (irregular)
    → Last resort.
```

### Infrastructure To Build

**File 1: `scripts/sec_quarter_cache_loader.py` (~200 lines)**

Fetches SEC data for all tickers and writes to cache.

```
For each ticker (~772):
  1. Look up CIK via bulk file: https://www.sec.gov/files/company_tickers.json
  2. Fetch: https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/EarningsPerShareBasic.json
     Fallback: try NetIncomeLoss if EPS not available
  3. Filter: standalone quarters (60-130d span, fp in Q1-Q4)
  4. Deduplicate: by (fy, fp), keep latest filed
  5. Also fetch: https://data.sec.gov/submissions/CIK{cik}.json → fiscalYearEnd
  6. Write to Redis + compute median quarter lengths

SEC rate limit: 10 req/sec with User-Agent header (required: "EventMarketDB research@example.com")
Full refresh: ~739 tickers / 8 req/sec = ~92 seconds
```

**Redis cache structure:**
```
# Exact quarter boundaries (from SEC XBRL)
fiscal_quarter:{TICKER}:{FY}:{QN} → {"start":"2024-02-04","end":"2024-05-04"}
  Example: fiscal_quarter:FIVE:2024:Q1 → {"start":"2024-02-04","end":"2024-05-04"}
  TTL: none (persists forever, populated on initial bootstrap + incremental via TradeReady scanner)

# Median quarter lengths (computed from SEC data)
fiscal_quarter_length:{TICKER}:{QN} → 91
  Example: fiscal_quarter_length:FIVE:Q3 → 91
  Example: fiscal_quarter_length:KR:Q1 → 112
  Example: fiscal_quarter_length:COST:Q1 → 84

# FYE month (from SEC submissions, day<=5 adjusted)
fiscal_year_end:{TICKER} → {"raw":"0201","month_adj":1}
  Example: fiscal_year_end:FIVE → {"raw":"0201","month_adj":1}

# Ticker→CIK mapping
sec_cik:{TICKER} → "0001177609"
```

**File 2 (OPTIONAL): `k8s/processing/sec-quarter-refresh.yaml` (~40 lines)**

Safety net only — the primary refresh is piggybacked on TradeReady scanner. This CronJob is a weekly full-refresh fallback for cache corruption or extended SEC outage recovery.

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: sec-quarter-refresh
  namespace: processing
spec:
  schedule: "0 6 * * 0"          # Sunday 6 AM ET weekly (safety net only)
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      backoffLimit: 3
      template:
        spec:
          nodeSelector:
            kubernetes.io/hostname: minisforum
          containers:
          - name: loader
            image: python:3.11-slim
            command: ["/project/venv/bin/python3", "/project/scripts/sec_quarter_cache_loader.py"]
            env:
            - name: REDIS_HOST
              value: "redis.infrastructure.svc.cluster.local"
            - name: REDIS_PORT
              value: "6379"
            resources:
              requests: {cpu: "50m", memory: "128Mi"}
              limits:   {cpu: "250m", memory: "256Mi"}
            volumeMounts:
            - name: project
              mountPath: /project
          volumes:
          - name: project
            hostPath:
              path: /home/faisal/EventMarketDB
          restartPolicy: OnFailure
```

### ±1 Day Convention Decision

SEC uses inclusive end dates. Our v3 graph uses exclusive ("day after"). Example:
```
FIVE Q1: SEC = 2024-02-04 → 2024-05-04 (inclusive, May 4 is last day)
         v3  = 2024-02-04 → 2024-05-05 (exclusive, May 5 is next Q start)
```

**Decision: Use SEC inclusive convention.** Reason: it's the industry standard, and existing GuidancePeriod nodes need migration anyway (they have wrong ~28d-offset dates). The convention switch comes free with the migration.

GuidancePeriod node IDs become: `gp_2024-02-04_2024-05-04` (not `_2024-05-05`).

### Migration Plan for Existing Wrong Guidance Data

1,858 guidance items on 5 tickers (FIVE, ASO, LULU, DLTR, SAIC) have wrong GuidancePeriod nodes (~28d offset).

**Critical: migration must update GuidanceUpdate.id, not just re-point edges.**

The `guidance_update_id` embeds `period_u_id` (see §Critical Code Detail below). If migration only re-points `HAS_PERIOD` edges to the correct GuidancePeriod but leaves the old `period_u_id` baked into `GuidanceUpdate.id`, the next extraction with the fiscal-identity lookup will:
1. Find the correct GuidancePeriod (via re-pointed edge) → get correct `period_u_id`
2. Compute a `guidance_update_id` with the correct `period_u_id` embedded
3. MERGE finds NO match (old node still has old `period_u_id` in its `id`) → creates DUPLICATE GuidanceUpdate

Verified empirically — FIVE FY2025 Q1 has:
```
Current gu.id: gu:FIVE_2024-03-20T08.30:revenue:gp_2024-03-01_2024-05-31:unknown:total
                                                 ^^^^^^^^^^^^^^^^^^^^^^^^
                                                 old wrong period embedded

After edge-only migration, new extraction would compute:
           gu:FIVE_2024-03-20T08.30:revenue:gp_2024-02-04_2024-05-04:unknown:total
                                            ^^^^^^^^^^^^^^^^^^^^^^^^
                                            correct SEC period — DIFFERENT ID → duplicate
```

**Migration steps (handles both levels):**

```
1. Load SEC quarter cache (run sec_quarter_cache_loader.py)

2. For each affected (ticker, fiscal_year, fiscal_quarter) group:
   a. Query: find all GuidanceUpdate nodes on wrong-date GuidancePeriod
      MATCH (gu:GuidanceUpdate)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
      WHERE gu.fiscal_year = $fy AND gu.fiscal_quarter = $fq
      MATCH (gu)-[old_hp:HAS_PERIOD]->(old_gp:GuidancePeriod)
      WHERE old_gp.id = $old_period_id

   b. MERGE correct GuidancePeriod node with SEC-derived dates:
      MERGE (new_gp:GuidancePeriod {id: $new_period_id})
        ON CREATE SET new_gp.u_id = $new_period_id,
                      new_gp.start_date = $sec_start,
                      new_gp.end_date = $sec_end

   c. Update GuidanceUpdate.id in-place (replace old period_u_id segment):
      SET gu.id = replace(gu.id, $old_period_id, $new_period_id)

   d. Re-point HAS_PERIOD edge:
      DELETE old_hp
      MERGE (gu)-[:HAS_PERIOD]->(new_gp)

3. Delete orphaned wrong-date GuidancePeriod nodes (only if no other
   GuidanceUpdate still references them — shared by calendar-month tickers)

4. Verify:
   - Zero duplicate periods per (ticker, fiscal_year, fiscal_quarter)
   - Every GuidanceUpdate.id contains the period_u_id that matches
     its HAS_PERIOD target's gp.id
   - Uniqueness constraint on GuidanceUpdate.id still holds
     (no collisions from the string replacement)
```

**Why in-place `SET gu.id` is safe:**
- Neo4j allows changing property values including those under uniqueness constraints, as long as the new value doesn't collide
- The new ID (with correct SEC period) has never been written before (no prior extraction used SEC dates), so no collision
- Future MERGE calls with the new ID will find the updated node correctly
- Future MERGE calls with the old ID won't find it (correct — old dates should never be used again)

### Accuracy Summary — Final (v4)

| Scenario | Source | Accuracy | Confidence |
|---|---|---|---|
| Historical quarters (all filed 10-Q/10-K) | SEC cache (Step 1) | **Exact** | **PROVEN** — 83,091 qtrs, 739/739 tickers |
| 8-K/transcript past-quarter reference | SEC cache (Step 1) | **Exact** | **PROVEN** — prior 10-Q already filed |
| 8-K/transcript current quarter | Step 2 prediction | **±0-1d (98.4%)** | **SIMULATION** — not E2E tested |
| 8-K/transcript forward guidance | Step 2 prediction | **±0-1d (98.4%)** | **SIMULATION** |
| Far-future guidance (>1yr ahead) | Step 2 chained | **±1d/quarter accum** | **SIMULATION** |
| 53-week transition quarter | Step 2 assumption break | **±7d** | **HIGH** — once per ~6yr |
| Brand new ticker | Step 3 FYE fallback | **±3-5d** | **PROVEN** — SEC FYE cross-validated |
| KR Q1 (old ±24d worst case) | SEC cache (Step 1) | **Exact (0d)** | **PROVEN** |
| COST Q3 (old ±19d case) | SEC cache (Step 1) | **Exact (0d)** | **PROVEN** |
| SEC API unavailable | Graph v3 offline fallback | **99.7%** | **PROVEN** — v3 as backup |

### SEC Cache Refresh Strategy — Piggyback on TradeReady Scanner

**No separate CronJob needed.** The TradeReady scanner (`scripts/trade_ready_scanner.py`) already runs 4x/day and identifies every ticker with upcoming earnings 1-3 days before the 8-K fires. Piggyback the SEC cache refresh on it:

```
TradeReady scanner runs (4x/day, already live in K8s):
  For each active TradeReady ticker (new or returning):
    If SEC quarter cache is missing OR stale (e.g., last fetch > 90 days ago):
      Fetch SEC XBRL Company Concept API → write to Redis (~1 API call, <1 sec)
```

**Important:** TradeReady preserves `added_at` for existing tickers and only updates `updated_at` (`trade_ready_scanner.py:368`). A returning ticker (next quarter's earnings) is NOT "newly added" but may have a new 10-Q filed since the last cache fetch. The trigger condition is **cache missing or stale**, not **first-ever add**.

**Why this is sufficient:**
- The guidance trigger daemon is driven BY TradeReady — it only extracts guidance for tickers in TradeReady
- So every ticker that will call `build_guidance_period_id()` has already been through TradeReady → cache is warm
- 1-3 day lead time before 8-K fires = plenty of time for the SEC fetch
- Cache has no TTL — once fetched, stays forever. No re-fetch needed for historical quarters
- ~5-15 new tickers per day during earnings season = <2 seconds of SEC API calls

**Why NOT a full daily refresh of 739 tickers:**
- 83,091 historical quarters don't change — fetching them daily wastes 90 seconds and 739 API calls
- Only ~5-15 tickers per day have new filings
- SEC rate limit (10 req/sec) is better spent on incremental fetches

**Setup:**
1. **One-time full refresh** — run `sec_quarter_cache_loader.py` once to populate entire cache (~90 sec, 739 tickers, ~83K quarters). This is the initial bootstrap.
2. **Incremental via TradeReady** — add ~20 lines to `trade_ready_scanner.py`: after adding a ticker, check Redis for SEC cache → if missing, fetch from SEC API and write. The existing 4x/day K8s CronJob schedule handles everything.
3. **Manual fallback** — `sec_quarter_cache_loader.py --ticker LULU` for ad-hoc refreshes or manual `trigger-extract.py` runs.

**Gaps (minor, with mitigations):**

| Gap | Impact | Mitigation |
|---|---|---|
| Manual `trigger-extract.py --ticker XYZ` for non-TradeReady ticker | Cache miss → Step 2/3 | Add SEC fetch to manual trigger script, or run cache loader for that ticker first |
| 10-Q files Day 40 after ticker dropped from TradeReady window | New quarter not in cache | First-write-wins already created the period on Day 0 — no new period needed |
| Brand new ticker, no earnings yet | No TradeReady entry, no cache | Step 3 FYE fallback until first earnings cycle |
| SEC down during TradeReady scan | Fetch fails | Cache from previous scans persists (no TTL). Retry on next scan (4x/day). Step 2/3 fallback if still down. |
| Extended SEC outage or cache corruption | Multiple tickers uncached | Run `sec_quarter_cache_loader.py` manually — full refresh of all 739 tickers in ~90 sec. Also available as K8s CronJob fallback (see below). |

### Implementation Order

1. **Build `scripts/sec_quarter_cache_loader.py`** — full SEC fetch for all tickers, write to Redis (~200 lines). Three uses: (a) initial bootstrap, (b) manual ad-hoc refreshes (`--ticker LULU`), (c) fallback full-refresh if incremental pipeline fails or cache is corrupted (`python3 sec_quarter_cache_loader.py` with no args = all tickers). Optionally deploy as a weekly K8s CronJob (`sec-quarter-refresh.yaml`, Sunday 6 AM) as a safety net behind the incremental TradeReady piggyback.
2. **Add SEC incremental fetch to `trade_ready_scanner.py`** (~20 lines) — after adding ticker to TradeReady, fetch its SEC quarter data if not cached. Piggybacks on existing 4x/day K8s CronJob. No new deployment needed.
3. **Run initial bootstrap** — `python3 sec_quarter_cache_loader.py` once (~90 sec) to populate cache with all 83K historical quarters.
4. **Add fiscal-identity lookup** in `_ensure_period()` (`guidance_write_cli.py:~78`) — before calling `build_guidance_period_id()`, query Neo4j for existing GuidancePeriod by `(ticker, fiscal_year, fiscal_quarter)` via GuidanceUpdate relationships. If found, reuse its `period_u_id`. This prevents duplicate GuidancePeriod AND GuidanceUpdate nodes when date computation changes (predicted → exact). Requires code change — NOT automatic from MERGE.
5. **Modify `build_guidance_period_id()` in `guidance_ids.py:376`** — Step 1 SEC cache lookup, Step 2 prediction, Step 3 FYE fallback (only reached when fiscal-identity lookup finds no existing period)
6. **Run migration** — fix existing 1,858 guidance items on 5 tickers
7. **Keep v3 Cypher query** as offline fallback (if SEC unavailable)
8. **Remove** XBRL reprocessing prerequisite and HAS_XBRL gate requirement (no longer needed)

### Critical Code Detail: Why MERGE Alone Doesn't Prevent Duplicates

The `guidance_update_id` embeds `period_u_id` (`guidance_ids.py:570-572`):
```python
guidance_update_id = f"gu:{safe_source_id}:{label_slug}:{period_u_id}:{basis_norm}:{segment_slug}"
```

If `period_u_id` changes (e.g., `gp_..._11-02` → `gp_..._11-03`), the entire `guidance_update_id` changes too. The MERGE on `guidance_update_id` creates a NEW GuidanceUpdate node — a full duplicate of the guidance item, not just a duplicate period.

The fiscal-identity lookup (Step 3 above) prevents this by ensuring `period_u_id` never changes for an already-written quarter. The lookup uses `GuidanceUpdate.fiscal_year` and `GuidanceUpdate.fiscal_quarter` (both persisted at `guidance_writer.py:169-170`) to find existing periods without needing to know the exact dates.
