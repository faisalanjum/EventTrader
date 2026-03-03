# Fix Issue #28: PER_SHARE_LABELS Too Narrow

**Issue**: `guidance_ids.py:68` hard-codes a 4-element set `PER_SHARE_LABELS = {'eps', 'dps', 'earnings_per_share', 'dividends_per_share'}`. Any per-share label not in this exact set (e.g., `adjusted_eps`, `non_gaap_eps`, `affo_per_share`) silently gets assigned `m_usd` instead of `usd`, corrupting both unit and value.

**Fix**: Replace the hard-coded set with a deterministic pattern-matching function + add fail-closed validation guards in the writer.

**Scope**: 4 files changed. No schema changes, no prompt changes, no new fields, no regex.

---

## File 1: `guidance_ids.py`

**Path**: `.claude/skills/earnings-orchestrator/scripts/guidance_ids.py`

### Change 1A: Replace `PER_SHARE_LABELS` set with `_is_per_share_label()` function

**DELETE** lines 67-68 (the comment + set):

```python
# Per-share metrics → always usd (not m_usd)
PER_SHARE_LABELS = {'eps', 'dps', 'earnings_per_share', 'dividends_per_share'}
```

**INSERT** in the same location (between the `UNIT_ALIASES` dict closing `}` on line 65 and the `_SCALE_TO_MILLIONS` comment on line 70):

```python
def _is_per_share_label(label_slug: str) -> bool:
    """Detect per-share metrics via slug token patterns.

    Rules (any match → True):
      1. Exact: 'eps' or 'dps'
      2. Prefix: starts with 'eps_' or 'dps_' (catches XBRL-ordered labels like eps_diluted)
      3. Suffix: ends with '_eps' or '_dps' (catches adjusted_eps, non_gaap_eps, etc.)
      4. Contains: 'per_share' or 'per_unit' (catches ffo_per_share, distributions_per_unit, etc.)
    """
    if label_slug in ('eps', 'dps'):
        return True
    if label_slug.startswith('eps_') or label_slug.startswith('dps_'):
        return True
    if label_slug.endswith('_eps') or label_slug.endswith('_dps'):
        return True
    if 'per_share' in label_slug or 'per_unit' in label_slug:
        return True
    return False
```

**Why 4 rules instead of 3**: SKILL.md §4 convention is modifier-first ("Diluted EPS" → `diluted_eps`), but XBRL concept names use base-first ordering (`EarningsPerShareDiluted`). Over 10,000 reports, LLM agents may echo the XBRL ordering, producing "EPS Diluted" → `eps_diluted`. Without `startswith('eps_')`, this escapes detection. False positive risk is zero: no financial metric starts with `eps_` or `dps_` that isn't EPS/DPS-family. Even `eps_growth` is safe — the per-share override in `canonicalize_unit()` only fires when `canonical == 'm_usd'`, so percentage growth metrics (`percent_yoy`) pass through unaffected.

### Change 1B: Update call site in `canonicalize_unit()` (currently line 136)

**FIND** this exact code in `canonicalize_unit()`:

```python
    # 4. Per-share override: EPS/DPS always usd, never m_usd
    if canonical == 'm_usd' and label_slug in PER_SHARE_LABELS:
        return 'usd'
```

**REPLACE WITH**:

```python
    # 4. Per-share override: always usd, never m_usd
    if canonical == 'm_usd' and _is_per_share_label(label_slug):
        return 'usd'
```

### Change 1C: Update call site in `canonicalize_value()` (currently line 160)

**FIND** this exact code in `canonicalize_value()`:

```python
    # Per-share: no scaling
    if label_slug in PER_SHARE_LABELS:
        return value
```

**REPLACE WITH**:

```python
    # Per-share: no scaling
    if _is_per_share_label(label_slug):
        return value
```

### What NOT to change

- Do NOT delete `PER_SHARE_LABELS` as a name yet — see Change 1D below.
- Do NOT change any other function signatures. `canonicalize_unit(unit_raw, label_slug)` and `canonicalize_value(value, unit_raw, canonical_unit, label_slug)` keep their existing signatures.
- Do NOT change `UNIT_ALIASES`, `CANONICAL_UNITS`, `_SCALE_TO_MILLIONS`, or any other data structures.

### Change 1D: Keep backward-compatible alias (for test imports)

**ADD** immediately after the `_is_per_share_label()` function definition:

```python
# Legacy constant — no longer used internally. Kept for backward compatibility
# in case external code imports this name.
PER_SHARE_LABELS = {'eps', 'dps', 'earnings_per_share', 'dividends_per_share'}
```

This keeps the existing constant importable for any external code referencing it, but the two internal call sites (1B, 1C) now use the function. The set is no longer the source of truth — it is a legacy alias only.

### Note: no test import changes needed

The new function `_is_per_share_label` is private (underscore prefix) and is tested indirectly through `canonicalize_unit()` and `canonicalize_value()`. No changes to `test_guidance_ids.py` imports required.

---

## File 2: `guidance_writer.py`

**Path**: `.claude/skills/earnings-orchestrator/scripts/guidance_writer.py`

### Change 2A: Import the classifier and slug function

**FIND** the imports at the top of the file. Currently there are no imports from `guidance_ids`. **ADD** after the existing imports (after `from datetime import datetime, timezone` on line 22):

```python
from guidance_ids import _is_per_share_label, slug
```

### Change 2B: Add two fail-closed guards to `_validate_item()`

**FIND** the end of `_validate_item()` (currently lines 65-69):

```python
    for field in REQUIRED_ITEM_FIELDS:
        val = item.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            return False, f"missing required field: {field}"
    return True, None
```

**REPLACE WITH**:

```python
    for field in REQUIRED_ITEM_FIELDS:
        val = item.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            return False, f"missing required field: {field}"

    # Guard A: per-share label with m_usd is the specific corruption this fix prevents.
    # Only check == 'm_usd', NOT != 'usd'. Per-share labels can legitimately have
    # non-usd units like 'percent_yoy' (EPS growth rate) or 'unknown' (qualitative
    # EPS guidance like "we expect strong EPS growth"). Blocking those would cause
    # false rejections at scale across 10,000 reports.
    label_slug = item.get('label_slug') or slug(item.get('label', ''))
    canonical_unit = item.get('canonical_unit', '')
    if _is_per_share_label(label_slug) and canonical_unit == 'm_usd':
        return False, (
            f"per-share label '{label_slug}' has canonical_unit='m_usd'"
            f" (expected 'usd' — per-share values must not be stored as millions)"
        )

    # Guard B: xbrl_qname indicates per-share but unit is m_usd (same corruption).
    # Also uses == 'm_usd' for consistency with Guard A. Catches cases where
    # the label doesn't match the classifier patterns but the XBRL concept clearly
    # says per-share. Includes PerDilutedShare and PerBasicShare because XBRL uses
    # the pattern 'IncomeLossFromContinuingOperationsPerDilutedShare' where
    # 'PerShare' is NOT a substring (verified against real DB concepts).
    xbrl_qname = item.get('xbrl_qname') or ''
    if xbrl_qname and (
        'PerShare' in xbrl_qname
        or 'PerUnit' in xbrl_qname
        or 'PerDilutedShare' in xbrl_qname
        or 'PerBasicShare' in xbrl_qname
    ):
        if canonical_unit == 'm_usd':
            return False, (
                f"xbrl_qname '{xbrl_qname}' indicates per-share but"
                f" canonical_unit='m_usd' (expected 'usd')"
            )

    return True, None
```

**Why `== 'm_usd'` and not `!= 'usd'`**: This was validated by tracing real scenarios:

| Scenario | label_slug | canonical_unit | `!= 'usd'` | `== 'm_usd'` |
|----------|-----------|---------------|------------|--------------|
| "EPS of $1.46" | `eps` | `usd` | pass | pass |
| "Adjusted EPS $1.46" (corrupted) | `adjusted_eps` | `m_usd` | REJECT | REJECT |
| "EPS growth of 10-15% YoY" | `eps` | `percent_yoy` | **FALSE REJECT** | pass |
| "We expect strong EPS growth" | `eps` | `unknown` | **FALSE REJECT** | pass |
| "AFFO/sh growth of 5-7%" | `affo_per_share` | `percent` | **FALSE REJECT** | pass |
| "DPS to increase" (qualitative) | `dps` | `unknown` | **FALSE REJECT** | pass |

Using `!= 'usd'` would reject qualitative and percentage-based EPS/DPS guidance — which is common across 10,000 reports. The bug is specifically per-share values stored as millions (`m_usd`). The guard targets exactly that.

**Why `PerDilutedShare` and `PerBasicShare` in Guard B**: These XBRL concept name patterns exist in the database but do NOT contain `PerShare` as a substring:

| XBRL Concept | Contains `PerShare`? | Contains `PerDilutedShare`? |
|-------------|---------------------|---------------------------|
| `us-gaap:EarningsPerShareDiluted` | Yes | No |
| `us-gaap:IncomeLossFromContinuingOperationsPerDilutedShare` | **No** | Yes |
| `us-gaap:IncomeLossFromContinuingOperationsPerBasicShare` | **No** | No (PerBasicShare) |
| `us-gaap:IncomeLossFromDiscontinuedOperationsNetOfTaxPerDilutedShare` | **No** | Yes |

Without these extra checks, 4+ real XBRL per-share concepts would escape Guard B.

### What NOT to change

- Do NOT change `REQUIRED_ITEM_FIELDS`.
- Do NOT change `_build_core_query()`, `_build_params()`, `write_guidance_item()`, `write_guidance_batch()`, or any other function.
- Do NOT add quote parsing or any NLP heuristics.

---

## File 3: `test_guidance_ids.py`

**Path**: `.claude/skills/earnings-orchestrator/scripts/test_guidance_ids.py`

### Change 3A: Expand the existing `test_unit_per_share_override()` test

**FIND** the existing test (currently lines 42-48):

```python
def test_unit_per_share_override():
    # EPS should always be usd, never m_usd
    assert canonicalize_unit("m_usd", "eps") == "usd"
    assert canonicalize_unit("usd", "eps") == "usd"
    assert canonicalize_unit("$", "eps") == "usd"
    assert canonicalize_unit("million", "eps") == "usd"
    assert canonicalize_unit("B", "dps") == "usd"
```

**REPLACE WITH**:

```python
def test_unit_per_share_override():
    # Original 4 labels (must still work)
    assert canonicalize_unit("m_usd", "eps") == "usd"
    assert canonicalize_unit("usd", "eps") == "usd"
    assert canonicalize_unit("$", "eps") == "usd"
    assert canonicalize_unit("million", "eps") == "usd"
    assert canonicalize_unit("B", "dps") == "usd"
    assert canonicalize_unit("$", "earnings_per_share") == "usd"
    assert canonicalize_unit("$", "dividends_per_share") == "usd"

    # Variant EPS labels (Issue #28 — previously mapped to m_usd)
    assert canonicalize_unit("$", "adjusted_eps") == "usd"
    assert canonicalize_unit("$", "non_gaap_eps") == "usd"
    assert canonicalize_unit("$", "diluted_eps") == "usd"
    assert canonicalize_unit("$", "basic_eps") == "usd"
    assert canonicalize_unit("$", "gaap_eps") == "usd"
    assert canonicalize_unit("$", "pro_forma_eps") == "usd"
    assert canonicalize_unit("$", "core_eps") == "usd"
    assert canonicalize_unit("$", "normalized_eps") == "usd"
    assert canonicalize_unit("$", "operating_eps") == "usd"
    assert canonicalize_unit("million", "adjusted_eps") == "usd"

    # XBRL-ordered labels (base metric first — startswith rule)
    assert canonicalize_unit("$", "eps_diluted") == "usd"
    assert canonicalize_unit("$", "eps_basic") == "usd"
    assert canonicalize_unit("$", "dps_declared") == "usd"

    # Per-share / per-unit labels (REIT, MLP, specialty)
    assert canonicalize_unit("$", "ffo_per_share") == "usd"
    assert canonicalize_unit("$", "affo_per_share") == "usd"
    assert canonicalize_unit("$", "core_ffo_per_share") == "usd"
    assert canonicalize_unit("$", "nav_per_share") == "usd"
    assert canonicalize_unit("$", "book_value_per_share") == "usd"
    assert canonicalize_unit("$", "distributable_earnings_per_share") == "usd"
    assert canonicalize_unit("$", "distributions_per_unit") == "usd"
    assert canonicalize_unit("$", "affo_per_unit") == "usd"
    assert canonicalize_unit("$", "free_cash_flow_per_share") == "usd"

    # Per-share labels with non-currency units must NOT be overridden
    # (the override only fires when canonical == 'm_usd')
    assert canonicalize_unit("% yoy", "eps") == "percent_yoy"
    assert canonicalize_unit("%", "affo_per_share") == "percent"
    assert canonicalize_unit(None, "eps") == "unknown"
    assert canonicalize_unit(None, "dps") == "unknown"

    # Negative controls: aggregate labels must NOT trigger per-share override
    assert canonicalize_unit("$", "revenue") == "m_usd"
    assert canonicalize_unit("$", "opex") == "m_usd"
    assert canonicalize_unit("$", "capex") == "m_usd"
    assert canonicalize_unit("$", "net_income") == "m_usd"
    assert canonicalize_unit("$", "operating_expenses") == "m_usd"
    assert canonicalize_unit("$", "share_repurchase") == "m_usd"
    assert canonicalize_unit("$", "free_cash_flow") == "m_usd"
    assert canonicalize_unit("$", "adjusted_ebitda") == "m_usd"

    # Edge cases: words containing 'eps' substring must NOT match
    assert canonicalize_unit("$", "steps") == "m_usd"
    assert canonicalize_unit("$", "concepts") == "m_usd"
    assert canonicalize_unit("$", "receipts") == "m_usd"
```

### Change 3B: Expand the existing `test_value_per_share_no_scaling()` test

**FIND** (currently lines 98-101):

```python
def test_value_per_share_no_scaling():
    # EPS $1.13 stays 1.13 regardless of raw unit
    assert canonicalize_value(1.13, "usd", "usd", "eps") == 1.13
    assert canonicalize_value(1.13, "$", "usd", "eps") == 1.13
```

**REPLACE WITH**:

```python
def test_value_per_share_no_scaling():
    # EPS $1.13 stays 1.13 regardless of raw unit
    assert canonicalize_value(1.13, "usd", "usd", "eps") == 1.13
    assert canonicalize_value(1.13, "$", "usd", "eps") == 1.13

    # Variant per-share labels also skip scaling (Issue #28)
    assert canonicalize_value(1.46, "$", "usd", "adjusted_eps") == 1.46
    assert canonicalize_value(3.50, "$", "usd", "non_gaap_eps") == 3.50
    assert canonicalize_value(2.15, "$", "usd", "affo_per_share") == 2.15
    assert canonicalize_value(0.26, "$", "usd", "distributions_per_unit") == 0.26

    # XBRL-ordered labels also skip scaling (startswith rule)
    assert canonicalize_value(1.13, "$", "usd", "eps_diluted") == 1.13
    assert canonicalize_value(1.13, "$", "usd", "eps_basic") == 1.13
```

---

## File 4: `test_guidance_writer.py`

**Path**: `.claude/skills/earnings-orchestrator/scripts/test_guidance_writer.py`

### Change 4A: Add validation guard tests

**ADD** the following tests at the end of the file (after the last existing test function). Do NOT modify any existing tests.

```python
# ── Per-share validation guards (Issue #28) ──────────────────────────────

def test_validate_per_share_label_with_m_usd():
    """Guard A: per-share label + canonical_unit='m_usd' must be rejected."""
    item = _make_item(
        label='Adjusted EPS',
        label_slug='adjusted_eps',
        canonical_unit='m_usd',
        guidance_id='guidance:adjusted_eps',
        guidance_update_id='gu:src:adjusted_eps:gp_2025-01-01_2025-03-31:non_gaap:total',
    )
    ok, err = _validate_item(item, 'src1', 'transcript')
    assert ok is False
    assert 'per-share' in err
    assert 'adjusted_eps' in err


def test_validate_per_share_label_with_correct_unit():
    """Per-share label + canonical_unit='usd' must pass."""
    item = _make_item(
        label='Adjusted EPS',
        label_slug='adjusted_eps',
        canonical_unit='usd',
        canonical_low=1.46,
        canonical_mid=1.48,
        canonical_high=1.50,
        guidance_id='guidance:adjusted_eps',
        guidance_update_id='gu:src:adjusted_eps:gp_2025-01-01_2025-03-31:non_gaap:total',
    )
    ok, err = _validate_item(item, 'src1', 'transcript')
    assert ok is True
    assert err is None


def test_validate_per_share_label_with_percent_unit():
    """Per-share label + canonical_unit='percent' must pass (growth rate guidance).

    Real example: 'AFFO per share growth of 5-7%' → label='AFFO Per Share',
    unit_raw='%', canonical_unit='percent'. This is valid — the label identifies
    the metric (AFFO/sh), the unit identifies this particular guidance instance
    (a growth rate). Guard A must NOT reject this.
    """
    item = _make_item(
        label='AFFO Per Share',
        label_slug='affo_per_share',
        canonical_unit='percent',
        canonical_low=5.0,
        canonical_high=7.0,
        guidance_id='guidance:affo_per_share',
        guidance_update_id='gu:src:affo_per_share:gp_2025-01-01_2025-03-31:unknown:total',
    )
    ok, err = _validate_item(item, 'src1', 'transcript')
    assert ok is True
    assert err is None


def test_validate_per_share_label_with_unknown_unit():
    """Per-share label + canonical_unit='unknown' must pass (qualitative guidance).

    Real example: 'We expect continued strong EPS growth' → label='EPS',
    unit_raw=None, canonical_unit='unknown'. Guard A must NOT reject this.
    """
    item = _make_item(
        label='EPS',
        label_slug='eps',
        canonical_unit='unknown',
        canonical_low=None,
        canonical_mid=None,
        canonical_high=None,
        qualitative='continued strong growth',
        guidance_id='guidance:eps',
        guidance_update_id='gu:src:eps:gp_2025-01-01_2025-03-31:gaap:total',
    )
    ok, err = _validate_item(item, 'src1', 'transcript')
    assert ok is True
    assert err is None


def test_validate_xbrl_per_share_with_m_usd():
    """Guard B: xbrl_qname with PerShare + canonical_unit='m_usd' must be rejected."""
    item = _make_item(
        label='Diluted Earnings',
        label_slug='diluted_earnings',
        canonical_unit='m_usd',
        xbrl_qname='us-gaap:EarningsPerShareDiluted',
        guidance_id='guidance:diluted_earnings',
        guidance_update_id='gu:src:diluted_earnings:gp_2025-01-01_2025-03-31:gaap:total',
    )
    ok, err = _validate_item(item, 'src1', 'transcript')
    assert ok is False
    assert 'xbrl_qname' in err


def test_validate_xbrl_per_diluted_share_with_m_usd():
    """Guard B: xbrl_qname with PerDilutedShare pattern + m_usd must be rejected.

    Tests the PerDilutedShare pattern which does NOT contain 'PerShare' as a
    substring (verified: 'IncomeLoss...PerDilutedShare' has 'PerDiluted' not 'PerShare').
    """
    item = _make_item(
        label='Continuing Operations Income',
        label_slug='continuing_operations_income',
        canonical_unit='m_usd',
        xbrl_qname='us-gaap:IncomeLossFromContinuingOperationsPerDilutedShare',
        guidance_id='guidance:continuing_operations_income',
        guidance_update_id='gu:src:continuing_operations_income:gp_2025-01-01_2025-03-31:gaap:total',
    )
    ok, err = _validate_item(item, 'src1', 'transcript')
    assert ok is False
    assert 'xbrl_qname' in err


def test_validate_xbrl_per_unit_with_m_usd():
    """Guard B: xbrl_qname with PerUnit + canonical_unit='m_usd' must be rejected."""
    item = _make_item(
        label='LP Distributions',
        label_slug='lp_distributions',
        canonical_unit='m_usd',
        xbrl_qname='us-gaap:DistributionMadeToLimitedPartnerDistributionsPaidPerUnit',
        guidance_id='guidance:lp_distributions',
        guidance_update_id='gu:src:lp_distributions:gp_2025-01-01_2025-03-31:gaap:total',
    )
    ok, err = _validate_item(item, 'src1', 'transcript')
    assert ok is False
    assert 'xbrl_qname' in err


def test_validate_xbrl_per_share_with_correct_unit():
    """xbrl_qname with PerShare + canonical_unit='usd' must pass."""
    item = _make_item(
        label='EPS',
        label_slug='eps',
        canonical_unit='usd',
        canonical_low=1.46,
        canonical_mid=1.48,
        canonical_high=1.50,
        xbrl_qname='us-gaap:EarningsPerShareDiluted',
        guidance_id='guidance:eps',
        guidance_update_id='gu:src:eps:gp_2025-01-01_2025-03-31:gaap:total',
    )
    ok, err = _validate_item(item, 'src1', 'transcript')
    assert ok is True
    assert err is None


def test_validate_aggregate_label_unchanged():
    """Non-per-share labels with m_usd must still pass (no false positive)."""
    item = _make_item()  # default is revenue + m_usd
    ok, err = _validate_item(item, 'src1', 'transcript')
    assert ok is True
    assert err is None


def test_validate_xbrl_aggregate_unchanged():
    """xbrl_qname without PerShare/PerUnit + m_usd must pass."""
    item = _make_item(xbrl_qname='us-gaap:Revenues')
    ok, err = _validate_item(item, 'src1', 'transcript')
    assert ok is True
    assert err is None
```

---

## Verification Steps (Run After All Changes)

Run these commands from the repo root. All must pass.

### Step 1: Run existing + new unit tests

```bash
cd /home/faisal/EventMarketDB
python3 -m pytest .claude/skills/earnings-orchestrator/scripts/test_guidance_ids.py -v
python3 -m pytest .claude/skills/earnings-orchestrator/scripts/test_guidance_writer.py -v
```

**Expected**: All tests pass, including the expanded per-share tests and the new validation guard tests.

### Step 2: Run integration smoke test

```bash
python3 -c "
import sys
sys.path.insert(0, '.claude/skills/earnings-orchestrator/scripts')
from guidance_ids import canonicalize_unit, slug

# These 8 MUST return 'usd' (were broken before fix)
broken_before = [
    'Adjusted EPS', 'Non-GAAP EPS', 'Diluted EPS', 'GAAP EPS',
    'AFFO Per Share', 'FFO Per Share', 'NAV Per Share', 'Distributions Per Unit',
]
for label in broken_before:
    result = canonicalize_unit('\$', slug(label))
    assert result == 'usd', f'FAIL: {label} -> {result}'

# These 3 MUST also return 'usd' (XBRL-ordered labels, startswith rule)
xbrl_ordered = ['EPS Diluted', 'EPS Basic', 'DPS Declared']
for label in xbrl_ordered:
    result = canonicalize_unit('\$', slug(label))
    assert result == 'usd', f'FAIL: {label} -> {result}'

# These 4 MUST return 'm_usd' (must not regress)
aggregate = ['Revenue', 'OpEx', 'CapEx', 'Net Income']
for label in aggregate:
    result = canonicalize_unit('\$', slug(label))
    assert result == 'm_usd', f'FAIL: {label} -> {result}'

# Per-share labels with non-currency units must pass through unchanged
assert canonicalize_unit('% yoy', slug('EPS')) == 'percent_yoy'
assert canonicalize_unit(None, slug('EPS')) == 'unknown'

print('ALL SMOKE TESTS PASSED')
"
```

### Step 3: Run full test suite to check for regressions

```bash
python3 -m pytest .claude/skills/earnings-orchestrator/scripts/ -v
```

**Expected**: All tests pass. No regressions in any existing test file.

---

## Summary of Changes

| File | What changes | Lines |
|------|-------------|------:|
| `guidance_ids.py` | Replace `PER_SHARE_LABELS` set check with `_is_per_share_label()` function (4 rules) at 2 call sites | ~18 |
| `guidance_writer.py` | Add import + 2 fail-closed guards (`== 'm_usd'`) in `_validate_item()` with expanded XBRL patterns | ~20 |
| `test_guidance_ids.py` | Expand `test_unit_per_share_override` (add startswith, percent/unknown passthrough, basic_eps) and `test_value_per_share_no_scaling` (add XBRL-ordered labels) | ~55 |
| `test_guidance_writer.py` | Add 10 new validation guard tests (incl. percent/unknown passthrough, PerDilutedShare) | ~120 |
| **Total** | | **~213** |

## What is NOT changed

- No schema changes (no new Neo4j nodes, edges, or properties)
- No prompt changes (no SKILL.md or agent doc edits)
- No new extraction fields (no `is_per_share` field added to JSON payload)
- No regex or NLP heuristics
- No quote parsing
- No changes to `guidance_write_cli.py` exit behavior in this revision (policy decision deferred; see below)
- No changes to any Cypher queries
- No changes to `_build_params()`, `_build_core_query()`, or `write_guidance_item()`

## Open Policy Decision (Deferred)

- `guidance_write_cli.py` job failure policy is intentionally left undecided and must be finalized before rollout.
- Why this remains open: this Issue #28 fix addresses per-share unit correctness (`m_usd` vs `usd`), but batch failure behavior is a separate operational policy choice with throughput vs strictness tradeoffs.
- Option A (`partial-success`): write valid items and report invalid ones. Better throughput, but a bad item can be missed unless monitoring is strict.
- Option B (`fail-fast`): any item-level ID/validation/write error exits non-zero for the job. Stronger reliability guarantees, but one bad item blocks the batch.
- Explicitly deciding this later avoids accidental policy lock-in while keeping the technical fix implementation-ready.

## After Implementation: Update Issue Tracker

In `.claude/plans/guidance-extraction-issues.md`, change issue #28 status from `**Open**` to `**Fixed**`:

```
| 28 | `PER_SHARE_LABELS` too narrow — `adjusted_eps`, `non_gaap_eps` get `m_usd` instead of `usd` | Medium | **Fixed** | Replaced exact-match set with `_is_per_share_label()` pattern function (4 rules: exact `eps`/`dps`, startswith `eps_`/`dps_`, endswith `_eps`/`_dps`, contains `per_share`/`per_unit`). Added fail-closed guards in `_validate_item()`: Guard A rejects per-share label + `m_usd`, Guard B rejects xbrl_qname PerShare/PerUnit/PerDilutedShare/PerBasicShare + `m_usd`. Guards use `== 'm_usd'` (not `!= 'usd'`) to avoid false-rejecting qualitative and percentage EPS/DPS guidance. |
```
