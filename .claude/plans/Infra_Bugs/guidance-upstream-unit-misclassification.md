# Guidance Upstream Unit Misclassification

**Created**: 2026-03-31
**Status**: OPEN — affects 1,813 / 8,291 GuidanceUpdate rows (21.9%)
**Impact**: Predictor sees wrong `$` signs on count metrics, missing `$`/`%` on unknown-unit metrics
**Fix**: Re-run guidance extraction with improved unit canonicalization prompts

---

## Summary

The guidance extraction pipeline sometimes assigns wrong `canonical_unit` values to GuidanceUpdate nodes. The renderer formats whatever unit it receives — so wrong units produce wrong display (e.g., "$97.4M" for 97.4 million shares). The renderer does NOT try to fix these — that was deliberately removed after evaluating hardcoded overrides (too fragile, false positive risk).

---

## Affected Rows (audited 2026-03-31, all 8,291 rows)

### 1. Misclassified m_usd — 141 rows (1.7%)

Metrics stored as `m_usd` (millions of USD) that are NOT money. The renderer multiplies by 1e6 and adds `$`, producing absurd values.

| Category | Rows | Metrics | What renders | What should render |
|----------|------|---------|-------------|-------------------|
| **Share counts** | 75 | Weighted Average Basic Shares Outstanding (30), Weighted Average Diluted Shares Outstanding (21), Diluted Weighted Average Shares Outstanding (21), Basic Shares Outstanding (3) | `~$97.4M` | `~97.4M` (count) |
| **Count-like** | 10 | Loyalty Members (3), HSA Count (3), Total Accounts (3), Net Active Customer Additions per Quarter (1) | `≥$11M` | `≥11M` (count) |
| **Per-unit prices** | 56 | Average Selling Price (48), Fuel Cost per Metric Ton (8) | `~$490B`, `~$675M` | `~$490K` (usd), `~$675` (usd) |

**Root cause**: Extraction LLM sees "97.4 million shares" and assigns `m_usd` because "million" triggers the monetary scale heuristic. Similarly, "$490,000 average selling price" gets stored as 490000 with `m_usd` instead of `usd`.

**Source breakdown**:
- Share counts: 44 from transcript, 31 from 8k
- Count-like: 4 from transcript, 6 from 8k
- Per-unit prices: 18 from 8k, 17 from transcript, 16 from 10q, 5 from 10k

### 2. Unknown unit — 1,672 rows (20.2%)

Metrics where extraction couldn't determine the unit. Renderer shows plain numbers (no `$`, no `%`).

| Subcategory | Rows | Impact |
|-------------|------|--------|
| Qualitative-only (no numbers) | 1,200 | **None** — renders as quoted text, no unit needed |
| Numeric with inferable type | 472 | **Mild** — missing `$` or `%` but metric name gives context |

**Top unknown-unit metrics with numeric values** (should have been classified):

| Metric | Rows | Should be | Example value |
|--------|------|-----------|---------------|
| EPS | 72 | `usd` | 6.7-6.85 (missing `$`) |
| Dividend Per Share | 64 | `usd` | 0.09 (missing `$`) |
| Adjusted EPS | 50 | `usd` | 5.75-6.5 (missing `$`) |
| Non-GAAP Net Loss Per Share | 28 | `usd` | -0.14 (missing `$`) |
| Year-End Community Count | 14 | `count` | 270 (correct as plain number) |
| Average Community Count | 5 | `count` | 244 (correct as plain number) |

### 3. Duplicate display rows — metrics with multiple units

20+ metrics appear with different `canonical_unit` values across their GuidanceUpdate nodes. This creates duplicate-looking rows in the guidance table (same metric name, different values).

| Metric | Units found | Problem |
|--------|------------|---------|
| Adjusted EPS Diluted | m_usd, unknown, usd | Three series for same concept |
| Adjusted EBITDA | basis_points, m_usd, percent, unknown | Four series |
| Adjusted EBITDA Margin | basis_points, percent, percent_points, unknown | Four series |
| Fuel Cost per Metric Ton | m_usd, unknown | Dollar vs per-ton price |
| Active Customers | count, percent_yoy, unknown | Count vs growth rate |

---

## What the renderer does today

The renderer trusts `resolved_unit` from the builder. No overrides, no heuristics.

- `m_usd` → multiply by 1e6, format with `$` and M/B suffix
- `usd` → format with `$`
- `percent` → format with `%`
- `count` → plain number with magnitude scaling (207M, 1,540)
- `unknown` → plain number (no `$`, no `%`)

This was a deliberate choice (commit `66568d7`). Hardcoded overrides were evaluated and rejected because:
- Keyword matching ("shares", "members") had false positive risk on money metrics ("Share-Based Compensation", "Passenger Revenue", "Accounts Receivable")
- Each new metric required manual addition to the override list
- The real fix is upstream canonicalization, not renderer heuristics

---

## How to fix (upstream)

### Fix 1: Improve extraction prompt unit rules

In the extraction contract (`.claude/skills/extract/types/guidance/core-contract.md`), add explicit rules:

```
Unit canonicalization rules:
- "X million shares" → canonical_unit=count, value=X*1e6 (NOT m_usd)
- "X million members/customers/accounts" → canonical_unit=count, value=X*1e6
- "$X per share" → canonical_unit=usd, value=X
- "$X,000 average selling price" → canonical_unit=usd, value=X000
- "$X per metric ton" → canonical_unit=usd, value=X
- "X% margin" → canonical_unit=percent, value=X
- "X basis points" → canonical_unit=basis_points, value=X
```

### Fix 2: Re-run extraction for affected companies

**Share count companies** (75 rows):
- Whoever has Weighted Average Basic/Diluted Shares Outstanding stored as m_usd

**Count-like companies** (10 rows):
- Academy Sports (Loyalty Members: 3)
- HealthEquity (HSA Count: 3)
- WEX (Total Accounts: 3)
- One other (Net Active Customer Additions: 1)

**Per-unit price companies** (56 rows):
- KBH (Average Selling Price: 48)
- CCL (Fuel Cost per Metric Ton: 8)

### Fix 3: Add unit validation to write path

In `guidance_writer.py`, add a post-write check:
- If metric label contains "shares outstanding" and unit is m_usd → warn
- If metric label contains "per share" and unit is not usd → warn
- If value > 100000 and unit is m_usd and metric is not revenue/income/expense → warn

This catches future misclassifications at write time instead of display time.

---

## Validation script

```bash
python3 scripts/earnings/test_guidance_unit_safety.py
```

Current results (2026-03-31):
- PASS: guidance_rows_present (8,291 rows)
- PASS: canonical_unit_enum_covered (9 known units)
- FAIL: no_unknown_units (1,672 unknown)
- FAIL: per_share_metrics_use_usd (324 mismatches)
- FAIL: share_count_metrics_use_count (2 mismatches)
- FAIL: count_like_metrics_not_money (10 mismatches)

Target: all 6 checks pass after re-extraction.

---

## Priority

**Medium**. The predictor LLM can work around these issues (metric names provide context). But for production accuracy, this should be fixed before the full historical backtest to ensure clean calibration data.
