# Fiscal Math — Remaining Issues

Date: 2026-03-19
Status: Investigation complete, fix TBD
Related: Session `get_quarterly_filings` (this session)

---

## What We Fixed Today

### `get_quarterly_filings.py` — the 8-K earnings discovery function

| Fix | Description | Accuracy |
|---|---|---|
| **XBRL fiscal identity** | Read `DocumentFiscalYearFocus` + `DocumentFiscalPeriodFocus` from matched 10-Q/10-K instead of calculating. Hybrid proximity guard + 8-accession deny list for bad XBRL. | 99.94% (7,921/7,926 vs XBRL ground truth) |
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

**For `get_quarterly_filings.py`, we bypassed both issues** by reading XBRL labels directly. But the underlying math functions are still wrong and are consumed by other code paths.

---

## Functions Still Affected

### 1. `build_guidance_period_id()` in `guidance_ids.py:376`

**Status: LIVE — called during every guidance extraction**

This is the function that converts fiscal labels to calendar dates for GuidancePeriod node IDs. It calls `_compute_fiscal_dates()` directly.

**Call chain:**
```
Extraction agent → guidance_write_cli.py:94 → _ensure_period() → build_guidance_period_id()
  → _compute_fiscal_dates(fye_month, fiscal_year, fiscal_quarter)
  → returns gp_{start_date}_{end_date}
```

**The FYE month comes from:** Query 1B in `queries-common.md` — the extraction agent reads the latest 10-K's `periodOfReport` and extracts the month. This is the raw month (same as `get_derived_fye`), not adjusted for 52-week calendars.

**Measured impact:** ASO and DLTR (both FYE=2 raw, should be 1) show **two different period conventions** for the same fiscal year in production data:
- `gp_2023-02-01_2024-01-31` (FYE=1 convention, from XBRL Period lookup)
- `gp_2023-03-01_2024-02-29` (FYE=2 convention, from _compute_fiscal_dates fallback)

This creates duplicate GuidancePeriod nodes for the same quarter — ~28 day offset between them. Not catastrophic (both cover approximately the right timeframe), but guidance items for the same quarter can land on different period nodes.

**Estimated scope:** Affects ~18 retailers × ~4 quarters with guidance data = ~72 potentially duplicated periods. Approximately 2-3% of all GuidancePeriod nodes for these tickers.

### 2. `fiscal_to_dates()` in `get_quarterly_filings.py:70`

**Status: DEAD CODE — zero runtime callers**

170-line function that was intended for the earnings orchestrator's "actuals comparison" feature (not yet built). It queries Neo4j Period nodes and classifies them using `period_to_fiscal()` with the raw FYE.

**Measured impact:** When tested empirically:
- ANF FY2023 Q4: returns Oct 2022 - Jan 2023 (off by 1 year — should be Oct 2023 - Jan 2024)
- CAKE FY2023 Q4: returns a 462-day period (should be ~90 days)
- AAPL FY2024 Q1: correct

**No production impact** since nothing calls it. Can be deleted.

### 3. `fiscal_resolve.py` (CLI wrapper)

**Status: DEAD CODE — zero runtime callers**

220-line CLI wrapper that replicates `fiscal_to_dates()` Phase 1 logic using pre-fetched Period data. Documented in `queries-common.md` and `QUERIES.md` as a usage example, but the extraction pipeline switched to `build_guidance_period_id()` and no longer calls it.

**No production impact.** Can be deleted.

### 4. `_compute_fiscal_dates()` in `fiscal_math.py:102`

**Status: LIVE — called by `build_guidance_period_id()` and `fiscal_resolve.py`**

The pure math function that converts (fye_month, fiscal_year, fiscal_quarter) → (start_date, end_date). Uses standard month boundaries (e.g., Q1 = first 3 months after FYE). This function itself is correct GIVEN correct inputs — the issue is that its callers pass the wrong FYE month (raw instead of adjusted).

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
| `build_guidance_period_id()` | **LIVE BUG** | ~28-day period offset for 18 retailers, creates duplicate GuidancePeriod nodes | Low — data usable, periods approximately correct |
| `fiscal_to_dates()` | **DEAD CODE** | Off by 1 year for retailers, 462-day period for CAKE | None — can delete |
| `fiscal_resolve.py` | **DEAD CODE** | Same issues as fiscal_to_dates | None — can delete |

---

## Open Questions (Not Yet Answered)

1. **Can we fix `get_derived_fye()` without breaking existing GuidancePeriod nodes?** If we change FYE=2→FYE=1 for retailers, all new period IDs will differ from existing ones. Need a migration plan for the ~72 affected period nodes.

2. **Should `build_guidance_period_id()` use XBRL `CurrentFiscalYearEndDate` instead of `get_derived_fye()`?** This would give the correct FYE for 99.6% of tickers. But it requires the extraction agent to query XBRL data (Query 1B already does this partially — agent reads `periodOfReport` which is close but not identical to `CurrentFiscalYearEndDate`).

3. **Is the year labeling convention (Issue B) a real problem for guidance?** The guidance extraction agent labels fiscal years based on what the company says in its filings. If the company says "Fiscal 2024" and `_compute_fiscal_dates` interprets that differently from the company's convention, the dates will be off by a year. Empirically, the production data (FIVE, LULU, ASO, DLTR) shows correct dates — suggesting the convention happens to align for these tickers. But it may not for all.

4. **Should we delete `fiscal_to_dates()` and `fiscal_resolve.py` now?** They're dead code. Deleting them removes 390 lines and eliminates confusion. The "future actuals comparison" use case they were kept for hasn't been built and can be re-implemented when needed.
