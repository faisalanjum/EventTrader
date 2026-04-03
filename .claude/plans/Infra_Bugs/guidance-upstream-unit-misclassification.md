# Guidance Upstream Unit Misclassification

**Created**: 2026-03-31
**Status**: OPEN — affects 1,813 / 8,291 GuidanceUpdate rows (21.9%)
**Impact**: predictor sees wrong `$` signs on count metrics, missing `$`/`%` on unknown-unit metrics
**Fix**: deterministic canonicalization/classifier repair first, then targeted re-extraction

---

## Summary

The guidance extraction pipeline still assigns wrong `canonical_unit` values to GuidanceUpdate nodes. The renderer is not the bug here: it trusts the stored unit on purpose. The active failure mode is upstream canonicalization.

The most important correction from the 2026-04-02 deep dive is this:

- this is not mainly an "LLM extracted the wrong thing" problem
- the extractor often emits a usable `label` plus a usable surface `unit_raw`
- the deterministic unit pipeline drops or misclassifies that signal

The bug now splits into three code-level buckets:

1. missing unit aliases
2. overly narrow label classifiers
3. a risky write-path fallback that lets `canonical_unit` stand in for `unit_raw`

Prompt improvements still help, but prompt work alone will not fix the live graph.

---

## 2026-04-02 Deep Dive — What the live graph actually shows

Audit rerun on 2026-04-02 against all 8,291 GuidanceUpdate rows:

- `unknown`: 1,672 rows
- `m_usd`: 2,830 rows total
- validation still fails on:
  - `no_unknown_units`
  - `per_share_metrics_use_usd`
  - `share_count_metrics_use_count`
  - `count_like_metrics_not_money`

The dominant active problem is not the old catastrophic `m_usd` corruption alone. It is the surviving `unknown` population, especially for per-share metrics.

### Per-share numeric `unknown` rows are mostly recoverable today

Numeric per-share / per-unit rows with `canonical_unit='unknown'`: **285**

Of those:

- rows whose `unit_raw` is already a recoverable alias-like string such as `per share`, `per diluted share`, `dollars per share`, `per_share`, `cents`: **275**
- rows that already have an `xbrl_qname`: **212**

This is the highest-signal proof that the current bug is mostly deterministic normalization, not extractor misunderstanding.

Top `unit_raw` values among numeric `unknown` rows on 2026-04-02:

- `per share`: 217
- `communities`: 35
- `per diluted share`: 16
- `dollar`: 16
- `dollars per share`: 15
- `<NULL>`: 15
- `clients`: 14
- `homes`: 10
- `thousand units`: 10
- `per_share`: 8
- `million shares`: 2

---

## Affected Rows

### 1. Misclassified `m_usd` — 141 rows (1.7%)

Metrics stored as `m_usd` (millions of USD) that are not money. The renderer multiplies by 1e6 and adds `$`, producing absurd output.

| Category | Rows | Metrics | What renders | What should render |
|----------|------|---------|-------------|-------------------|
| Share counts | 75 | Weighted Average Basic Shares Outstanding (30), Weighted Average Diluted Shares Outstanding (21), Diluted Weighted Average Shares Outstanding (21), Basic Shares Outstanding (3) | `~$97.4M` | `~97.4M` (`count`) |
| Count-like | 10 | Loyalty Members (3), HSA Count (3), Total Accounts (3), Net Active Customer Additions per Quarter (1) | `≥$11M` | `≥11M` (`count`) |
| Per-unit prices | 56 | Average Selling Price (48), Fuel Cost per Metric Ton (8) | `~$490B`, `~$675M` | `~$490K` / `~$675` (`usd`) |

Examples still present in the graph on 2026-04-02:

- `guidance:adjusted_eps_diluted` rows like `Adjusted net income per diluted share $3.22 to $3.30` still stored as `m_usd`
- `guidance:hsa_count` rows like `approximately 9.8 million` still stored as `m_usd`
- `guidance:loyalty_members` rows like `over 13 million members` still stored as `m_usd`
- `guidance:total_accounts` rows like `approximately 17 million` still stored as `m_usd`

These rows are numeric, not qualitative-only. That matters because it proves the remaining `m_usd` population is not explained solely by qualitative fallback behavior.

**Updated root cause**:

- some rows still come from upstream misclassification
- but the durable code issue is that the classifier layer is too narrow to rescue them once a scale word or pre-canonicalized unit pushes them toward `m_usd`

### 2. Unknown unit — 1,672 rows (20.2%)

Rows where canonicalization ended at `unknown`. Renderer shows plain numbers with no `$` or `%`.

| Subcategory | Rows | Impact |
|-------------|------|--------|
| Qualitative-only (no numbers) | 1,200 | None — quote-driven rendering only |
| Numeric with inferable type | 472 | Real data quality issue |

Top numeric `unknown` metrics:

| Metric | Rows | Should be |
|--------|------|-----------|
| EPS | 72 | `usd` |
| Dividend Per Share | 64 | `usd` |
| Adjusted EPS | 50 | `usd` |
| Non-GAAP Net Loss Per Share | 28 | `usd` |
| Year-End Community Count | 14 | `count` |
| Average Community Count | 5 | `count` |

**Updated root cause**:

For a large share of these rows, the extractor *did* emit a usable unit surface form. The canonicalizer simply does not know the string.

### 3. Duplicate display rows — same metric, multiple units

20+ metrics still appear with multiple `canonical_unit` values.

| Metric | Units found | Problem |
|--------|------------|---------|
| Adjusted EPS Diluted | `m_usd`, `unknown`, `usd` | Three series for same concept |
| Adjusted EBITDA | `basis_points`, `m_usd`, `percent`, `unknown` | Four series |
| Adjusted EBITDA Margin | `basis_points`, `percent`, `percent_points`, `unknown` | Four series |
| Fuel Cost per Metric Ton | `m_usd`, `unknown` | Dollar vs per-ton price |
| Active Customers | `count`, `percent_yoy`, `unknown` | Count vs growth rate |

---

## Why the current code fails

### 1. `UNIT_ALIASES` is much narrower than the strings the extractor already emits

`guidance_ids.py:UNIT_ALIASES` supports only a compact set of aliases:

- `$`, `dollars`
- `million`, `billion`, `thousand`
- `%`, `yoy`, `bps`
- `times`
- `shares`, `units`, `employees`, `stores`

Missing strings from the active failure population:

- `per share`
- `per diluted share`
- `dollars per share`
- `per_share`
- `dollars_per_share`
- `dollar_per_share`
- `dollar`
- `cents`
- `million shares`
- `members`
- `communities`
- `clients`
- `homes`
- `clinics`
- `restaurants`
- `locations`
- `thousand units`

This is the main `unknown` bug.

### 2. The label classifiers are still too narrow

`_is_per_share_label()` correctly handles:

- exact `eps` / `dps`
- prefix `eps_*` / `dps_*`
- suffix `*_eps` / `*_dps`
- contains `per_share` / `per_unit`

But it still misses real infix variants such as:

- `adjusted_eps_diluted`

`_is_share_count_label()` is intentionally narrow and only covers:

- `share_count`
- `shares_outstanding`
- `*_share_count`
- `*_shares`

That misses reviewed count-like labels such as:

- `hsa_count`
- `loyalty_members`
- `total_accounts`
- `community_count`
- `year_end_community_count`
- `average_community_count`
- weighted-average share labels ending in `_shares_outstanding`

This classifier layer is the real safety net because it is the last defense for both:

- alias misses that would otherwise become `unknown`
- scale-word or pre-canonicalized inputs that would otherwise become `m_usd`

### 3. `guidance_write_cli.py:328` is a real bypass path

Current code:

```python
unit_raw=item.get('unit_raw') or item.get('canonical_unit') or 'unknown'
```

This is risky because an upstream payload can omit `unit_raw` and feed `canonical_unit='m_usd'` directly into `build_guidance_ids()`. At that point:

- alias lookup is bypassed
- only the label classifiers can still save the row

This fallback does not explain the entire current bug population, but it is a real contract violation risk and should not be ignored.

### 4. Writer guards only stop the worst old bug

`guidance_writer.py` currently rejects:

- per-share labels with `canonical_unit='m_usd'`
- share-count labels with `canonical_unit='m_usd'`
- obvious PerShare/PerUnit XBRL concepts with `canonical_unit='m_usd'`

But it still permits:

- numeric per-share rows with `canonical_unit='unknown'`
- count-like rows outside the narrow reviewed classifier

So the writer catches only the old fail-closed corruption, not the dominant remaining population.

---

## Implementation traces — exact code paths to fix

These traces are the shortest path from symptom to code edit. They are based on the current write pipeline:

1. `_ensure_ids()` in `guidance_write_cli.py`
2. `build_guidance_ids()` calling `canonicalize_unit()` / `canonicalize_value()`
3. `_validate_item()` in `guidance_writer.py`

### Trace A — `adjusted_eps_diluted` can still land as `m_usd`

Representative live symptom:

- label family: `adjusted_eps_diluted`
- quote text like: `Adjusted net income per diluted share $3.22 to $3.30`
- bad stored unit: `m_usd`

One concrete reachable path is:

1. `guidance_write_cli.py:319-328` builds IDs with:
   - `label=item['label']`
   - `unit_raw=item.get('unit_raw') or item.get('canonical_unit') or 'unknown'`
2. If the payload omitted `unit_raw` but already carried `canonical_unit='m_usd'`, line 328 passes the string `m_usd` into `build_guidance_ids()`.
3. `guidance_ids.py:172-176` lowercases to `u='m_usd'` and treats it as already canonical.
4. `guidance_ids.py:185` asks `_is_per_share_label('adjusted_eps_diluted')`.
5. `guidance_ids.py:76-83` returns `False` because the slug:
   - is not exactly `eps` / `dps`
   - does not start with `eps_` / `dps_`
   - does not end with `_eps` / `_dps`
   - does not contain `per_share` / `per_unit`
6. `guidance_ids.py:192` returns `m_usd` unchanged.
7. `guidance_ids.py:223-236` treats the row as aggregate currency, not per-share, so numeric values like `3.22` stay numerically unchanged but semantically wrong.
8. `guidance_writer.py:77-79` recomputes the same `label_slug` and misses the same per-share classifier.
9. `guidance_writer.py:91-102` only saves the row if `xbrl_qname` is absent or non-per-share; otherwise Guard B would reject it.
10. Result: a real per-share metric can persist as `m_usd`.

Important nuance:

- this trace proves line 328 is a real bypass path
- it does **not** prove every `adjusted_eps_diluted` row took this exact route
- the live graph only proves the end state; once written, it no longer records whether `m_usd` came from raw aliasing upstream or from the line-328 fallback

### Trace B — `unit_raw='per share'` still ends at `unknown`

Representative live symptom:

- labels like `eps`, `adjusted_eps`, `dividend_per_share`
- raw surface unit already present as `per share`
- bad stored unit: `unknown`

Current path:

1. `guidance_write_cli.py:328` passes `unit_raw='per share'` into `build_guidance_ids()`.
2. `guidance_ids.py:172` normalizes to `u='per share'`.
3. `guidance_ids.py:175-179` fails both:
   - already-canonical check
   - alias lookup, because `per share` is not in `UNIT_ALIASES`
4. `guidance_ids.py:181-182` sets `canonical='unknown'`.
5. `guidance_ids.py:185` does **not** help, because the per-share override only fires when `canonical == 'm_usd'`.
6. `guidance_ids.py:192` returns `unknown`.
7. `guidance_ids.py:220-221` returns numeric values unchanged because `unknown` is not a currency unit.
8. `guidance_writer.py:79-109` allows the row through because the writer only fail-closes `m_usd` corruption, not numeric per-share `unknown`.

This is the clearest proof that many current misses are alias-table misses, not extractor misunderstanding.

### Trace C — `weighted_average_basic_shares_outstanding` still lands as `m_usd`

Representative live symptom:

- label family: `weighted_average_basic_shares_outstanding`
- quote text like: `weighted average basic shares outstanding of 97.4 million`
- bad stored unit: `m_usd`

Current path:

1. `guidance_write_cli.py:328` passes `unit_raw='million'`.
2. `guidance_ids.py:178-179` maps `million -> m_usd`.
3. `guidance_ids.py:189` asks `_is_share_count_label('weighted_average_basic_shares_outstanding')`.
4. `guidance_ids.py:110-115` returns `False` because the slug:
   - is not exactly `share_count` / `shares_outstanding`
   - does not end with `_share_count`
   - does not end with `_shares`
5. `guidance_ids.py:192` returns `m_usd` unchanged instead of `count`.
6. `guidance_ids.py:228-233` treats `97.4` + `million` as aggregate currency-in-millions, so the stored value stays `97.4`.
7. `guidance_writer.py:104-109` misses the same label because Guard C reuses `_is_share_count_label()`.
8. Result: renderer later interprets the row as roughly `$97.4M` instead of `97.4M shares`.

This is why classifier broadening has to come before any historical cleanup.

---

## What the renderer does today

The renderer trusts `resolved_unit` from the builder. No overrides, no heuristics.

- `m_usd` → multiply by 1e6, format with `$` and M/B suffix
- `usd` → format with `$`
- `percent` → format with `%`
- `count` → plain number with magnitude scaling
- `unknown` → plain number

This is deliberate and should stay that way. The renderer is not the right repair layer.

---

## How to fix

### Fix 0: audit and tighten the write-path contract

Audit every caller that relies on:

```python
unit_raw=item.get('unit_raw') or item.get('canonical_unit') or 'unknown'
```

Best end-state:

- callers provide `unit_raw`
- canonicalization happens once inside `build_guidance_ids()`
- `canonical_unit` is not silently reused as if it were raw unit text

Do not call this zero-risk until callers are verified, but treat it as a real bug vector.

### Fix 1: broaden the label classifiers first

Priority should be slightly higher than this file originally proposed because the classifiers are the last line of defense.

Expand `_is_per_share_label()` to catch infix / token-order variants such as:

- `adjusted_eps_diluted`
- `adjusted_diluted_eps`
- other `*_eps_*` forms

Expand `_is_share_count_label()` or add a reviewed count classifier for:

- weighted-average share labels
- `basic_shares_outstanding`
- `diluted_shares_outstanding`
- `hsa_count`
- `loyalty_members`
- `total_accounts`
- community-count families

### Fix 2: add the missing unit aliases

Add the strings the live graph is already giving us:

- per-share: `per share`, `per diluted share`, `dollars per share`, `per_share`, `dollars_per_share`, `dollar_per_share`, `usd_per_share`, `cents`
- scaled share-count: `million shares`
- generic counts: `members`, `communities`, `clients`, `homes`, `clinics`, `restaurants`, `locations`, `thousand units`

### Fix 3: improve prompt examples, but treat prompt work as secondary

The extraction contract should include explicit examples for:

- `X million shares` → `count`
- `X million members/customers/accounts` → `count`
- `$X per share` / `X cents per share` → `usd`
- `$X per metric ton` → `usd`

Prompt work still matters, but it is not enough on its own because the active failures persist even when the extractor already supplied a recoverable surface unit.

### Fix 4: strengthen write-time validation

Add warnings or fail-closed checks for:

- numeric per-share labels landing as `unknown`
- numeric reviewed count-like labels landing as `m_usd` or `usd`
- obviously bad scale patterns on count metrics

### Fix 5: re-run the affected companies after code fixes land

Especially:

- weighted-average share-count companies
- `HSA Count`
- `Loyalty Members`
- `Total Accounts`
- `Average Selling Price`
- `Fuel Cost per Metric Ton`

---

## Validation script

```bash
venv/bin/python scripts/earnings/test_guidance_unit_safety.py
```

Current results (2026-04-02):

- PASS: guidance_rows_present (8,291 rows)
- PASS: canonical_unit_enum_covered
- FAIL: no_unknown_units (1,672 unknown)
- FAIL: per_share_metrics_use_usd (324 mismatches)
- FAIL: share_count_metrics_use_count (2 mismatches)
- FAIL: count_like_metrics_not_money (10 mismatches)

Target: all 6 checks pass after targeted re-extraction.

---

## Current conclusion

As of 2026-04-02, the right mental model is:

- not primarily an LLM comprehension bug
- not a renderer bug
- primarily a deterministic normalization bug split across:
  - alias coverage
  - classifier breadth
  - a risky `canonical_unit` fallback path in `guidance_write_cli.py`

This should be fixed before the full historical backtest and before treating guidance units as calibration-grade data.
