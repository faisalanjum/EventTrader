# Unit Canonicalization Bug — Full Analysis (2026-03-13)

Status: analysis complete, fix not yet implemented

## Bug Summary

AVGO `Diluted Share Count` persisted as `canonical_unit='m_usd'` with `low=mid=high=4940.0` instead of `canonical_unit='count'` with absolute value `4940000000.0`. Source text: "4.94 billion shares".

## Complete Trace

### Layer 1: Agent extraction (correct behavior)
- Agent follows primary-pass.md:92: "Copy the number and unit exactly as printed"
- `"4.94 billion shares"` → `label="Diluted Share Count"`, `low=4.94`, `unit_raw="billion"`
- This is correct per the contract — the canonicalizer is supposed to handle scaling

### Layer 2: Unit canonicalization (the bug)
- `guidance_ids.py:canonicalize_unit("billion", "diluted_share_count")`:
  - "billion" → UNIT_ALIASES["billion"] = "m_usd" (line 49)
  - `_is_per_share_label("diluted_share_count")` → False (no eps/dps/per_share/per_unit)
  - Returns "m_usd" ← **BUG: should be "count"**
- `guidance_ids.py:canonicalize_value(4.94, "billion", "m_usd", "diluted_share_count")`:
  - Enters aggregate currency path (line 185)
  - `_parse_numeric_with_scale("4.94billion")` → (4.94, 1000.0)
  - Returns 4.94 × 1000 = 4940.0 ← stored as "$4,940 million"

### Layer 3: CLI ID computation (propagates the bug)
- `guidance_write_cli.py:_ensure_ids()` calls `build_guidance_ids()` (line 141)
- Uses `unit_raw=item.get('unit_raw')` (line 150) — still "billion" from agent JSON
- `build_guidance_ids()` returns dict with canonical_unit='m_usd', does NOT include 'unit_raw' (correct per line 548-551)
- `item.update(ids)` (line 154) merges canonical fields BUT does NOT remove existing 'unit_raw' key from item

### Layer 4: Writer persistence (design mismatch — amplifies the bug)
- `guidance_writer.py:_build_params()` (line 281): `'unit_raw': item.get('unit_raw')` — passes through "billion" unconditionally
- Cypher at line 179: `gu.unit_raw = $unit_raw` — persists "billion" even though canonical_unit='m_usd'
- **Contract violation**: core-contract.md:96 says `unit_raw` should only exist when `canonical_unit='unknown'`
- `build_guidance_ids()` correctly strips unit_raw for known units (line 548-551), but the writer bypasses this by reading from the original item dict

### Layer 5: Enrichment re-feed hazard (consequence of Layer 4)
- 7E readback returns `gu.unit_raw` (guidance-queries.md:72) — "billion" still present
- enrichment-pass.md:72-74: enrichment preserves unit_raw from 7E when present
- When enrichment re-emits the item, it passes the canonical value (4940.0) together with unit_raw="billion"
- This is exactly why AVGO AI Revenue enrichment nearly double-scaled (100000 + "billion" → rejected as pre-scaled)
- The self-correction saved it, but the structural hazard remains

## Root Cause Chain

1. `UNIT_ALIASES` maps scale words → `m_usd` unconditionally (no count-label awareness)
2. No `_is_count_label()` function analogous to `_is_per_share_label()`
3. Writer persists `unit_raw` for known canonical units (violates contract)
4. Enrichment re-consumes persisted `unit_raw` with canonical values (re-feed hazard)

## Correct Fix (4 changes + 1 guard + tests)

### Change 1: `guidance_ids.py` — Add `_is_count_label()`
Narrow share-count classifier patterned after `_is_per_share_label()`:
- Suffix `_count` → `diluted_share_count`, `share_count`, `store_count`, etc.
- Suffix `_shares` → `diluted_shares`, `basic_shares`, `weighted_average_shares`
- Exact: `shares_outstanding`
- Does NOT match: `share_repurchase`, `share_based_compensation`, `discount`, `revenue`

### Change 2: `guidance_ids.py:canonicalize_unit()` — Count override
After per-share override (step 4), add step 5:
```python
if canonical == 'm_usd' and _is_count_label(label_slug):
    return 'count'
```

### Change 3: `guidance_ids.py:canonicalize_value()` — Count scaling
Before the non-currency early return, add count path:
- When canonical_unit='count' and unit_raw is a scale word (billion/million/k)
- Scale to absolute: 4.94 × 1e9 = 4,940,000,000.0
- Same pre-scale safety check as currency (multiplier > 1 and value > 999 → raise)
- Uses existing `_parse_numeric_with_scale()`, multiplier × 1e6 for to-absolute

### Change 4: `guidance_writer.py:_build_params()` — Fix unit_raw persistence
Only persist unit_raw when canonical_unit='unknown':
```python
'unit_raw': item.get('unit_raw') if item.get('canonical_unit') == 'unknown' else None,
```
This aligns the writer with the contract (core-contract.md:96) and closes the enrichment re-feed hazard.

### Guard: `guidance_writer.py:_validate_item()` — Guard C
Reject count labels with canonical_unit='m_usd' (parallel to Guards A/B for per-share):
```python
if _is_count_label(label_slug) and canonical_unit == 'm_usd':
    return False, "count label with m_usd..."
```

### Tests to add
- `canonicalize_unit('billion', 'diluted_share_count')` → `'count'`
- `canonicalize_unit('million', 'share_count')` → `'count'`
- `canonicalize_unit('billion', 'revenue')` → `'m_usd'` (negative control)
- `canonicalize_unit('billion', 'share_repurchase')` → `'m_usd'` (negative control)
- `canonicalize_value(4.94, 'billion', 'count', 'diluted_share_count')` → `4940000000.0`
- `canonicalize_value(300, 'million', 'count', 'subscriber_count')` → `300000000.0`
- Integration: full `build_guidance_ids` for AVGO case → canonical_unit='count', canonical_low=4940000000.0
- Writer: known-unit writes do not persist unit_raw
- Writer: share-count + m_usd rejected at validation

## What NOT to do
- No `m_count` / `m_shares` — existing `count` canonical unit suffices
- No prompt-only changes — the bug is in the deterministic layer
- No writer-guard-only rejection — must fix the source
- No broad "all count-like metrics" heuristics — only proven share-count class

## Files touched
1. `guidance_ids.py` — changes 1-3 (~25 lines)
2. `guidance_writer.py` — change 4 + guard (~10 lines)
3. `test_guidance_ids.py` — new tests (~35 lines)
4. `core-contract.md` §8 — count override note (~5 lines)
5. `primary-pass.md` — count metric example (~1 line)

## Regression Risk
- All 78 existing tests verified passing before any changes
- Every existing code path traced: zero regression (see trace table in conversation)
- `_is_count_label` has zero false positives against all known label patterns
- The unit_raw persistence fix is strictly more correct than current behavior (aligns with contract)

## Existing corrupted data
- AVGO `diluted_share_count` row needs fresh re-extraction after fix deployment
- Graph query confirms exactly 1 bad persisted row of this type
