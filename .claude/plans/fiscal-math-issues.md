# Fiscal Math Issues

Date: 2026-03-19
Status: Investigation complete, fix TBD
Related: Session `get_quarterly_filings`

---

## TL;DR

**Fixed today:** `get_quarterly_filings.py` — fiscal labeling (XBRL-direct, 99.94% accurate) and dedup (min-lag, 0 wrong picks). Fully fixed and ready for the earnings orchestrator.

**Still broken:** One live function — `build_guidance_period_id()` in `guidance_ids.py` — calls `_compute_fiscal_dates()` with the wrong FYE month for 18 retailers. Guidance-only issue; does not affect `get_quarterly_filings.py` or the earnings orchestrator.

**~3.3% of guidance items** (~173 / 5,227) are on the wrong period convention (~28-day offset). ~23% of guidance data is from affected tickers where future extractions could also produce inconsistent periods.

**Functions with issues:** 2 live (`build_guidance_period_id()`, `get_derived_fye()`), 2 dead code (`fiscal_to_dates()`, `fiscal_resolve.py`) — same bugs but zero production impact.

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
- 3 of 18 affected retailers currently have guidance data: FIVE (468), ASO (387), DLTR (351) = 1,206 items
- 1,206 / 5,227 total GuidanceUpdate nodes = **~23% of all guidance data is from affected tickers**
- Within those tickers, ~15-27% of items use the FYE=1 convention instead of FYE=2:
  - ASO: 55 FYE=1 vs 269 FYE=2 (15.5% on alternate convention)
  - DLTR: 90 FYE=1 vs 158 FYE=2 (26.5%)
  - FIVE: 28 FYE=1 vs 266 FYE=2 (6.2%)
- **~173 items (~3.3% of all guidance) are on the wrong period convention**
- The remaining 15 of 18 retailers have no guidance yet — when processed, the affected share grows
- **High estimate: ~23% of guidance data is from tickers where this bug can produce inconsistent period boundaries (~28-day offset)**

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
   - Remove 3 LLM-facing doc references: `queries-common.md:72-74`, `guidance-inventory/QUERIES.md:67-69`, `extraction-pipeline-reference.md:238`
   - Update `fiscal_math.py:4-5` docstring (references `fiscal_resolve.py`)

6. **Docs are internally inconsistent.** Some plan docs (guidanceInventory.md §6, §15) still describe the old fiscal-keyed/no-date-computation design ("simple string concatenation", "no `fiscal_resolve.py` dependency"), while the current v3.1 code and contract (core-contract.md:394, :442) use calendar-based `gp_{start}_{end}` with `_compute_fiscal_dates()`. The docs should be reconciled to reflect the current reality: the guidance pipeline DOES use date math via `build_guidance_period_id()`.

7. **Test gap.** No targeted Jan/Feb retailer tests exist for `build_guidance_period_id()` in `test_guidance_ids.py` (557 lines) or `test_guidance_write_cli.py` (320 lines). Existing 146 tests all pass but do not exercise the FYE=2 vs FYE=1 edge case.
