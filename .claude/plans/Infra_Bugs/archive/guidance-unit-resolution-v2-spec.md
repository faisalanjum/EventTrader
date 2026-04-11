# Guidance Unit Resolution V2 Spec

**Created**: 2026-04-10
**Status**: Proposed
**Goal**: Eliminate silent unit corruption in guidance extraction without breaking downstream consumers.

---

## 1. Design Goal

The current system asks `unit_raw` to answer too many questions at once:

- what kind of thing is this (`money`, `ratio`, `count`, `multiplier`)?
- if it is money, is it aggregate or price-like?
- what scale is the numeric value (`billion`, `million`, `cents`, none)?

V2 separates those concerns while preserving the existing graph contract:

- keep writing `canonical_unit`
- keep `evhash16` format unchanged
- keep renderer/cache/query behavior unchanged
- add only the minimum new extraction hints needed to resolve units safely

**Key rule**: LLM output is a strong hint, not final authority. The CLI remains the canonical resolver.

---

## 2. Handoff Rules

This document is the implementation handoff for the V2 guidance unit-resolution fix.

### 2.1 Source Of Truth

- this spec is the source of truth for implementation
- if existing code comments, older tests, or older guidance docs conflict with this spec, follow this spec
- preserve backward compatibility only where this spec explicitly requires it

### 2.2 Implement Exactly These 15 Files

Required implementation surface:

1. `.claude/skills/earnings-orchestrator/scripts/guidance_ids.py`
2. `.claude/skills/earnings-orchestrator/scripts/guidance_write_cli.py`
3. `.claude/skills/earnings-orchestrator/scripts/guidance_writer.py`
4. `.claude/skills/extract/types/guidance/primary-pass.md`
5. `.claude/skills/extract/types/guidance/enrichment-pass.md`
6. `.claude/skills/extract/types/guidance/core-contract.md`
7. `.claude/skills/extract/types/guidance/guidance-queries.md`
8. `.claude/skills/extract/types/guidance/assets/8k-primary.md`
9. `.claude/skills/earnings-orchestrator/scripts/test_guidance_ids.py`
10. `.claude/skills/earnings-orchestrator/scripts/test_guidance_write_cli.py`
11. `.claude/skills/earnings-orchestrator/scripts/test_guidance_writer.py`
12. `scripts/earnings/test_guidance_unit_safety.py`
13. `.claude/plans/Infra_Bugs/guidance-unit-resolution-v2-spec.md`
14. `.claude/skills/earnings-orchestrator/scripts/warmup_cache.py` (optional downstream cleanup only)
15. `scripts/earnings/earnings_orchestrator.py` (optional downstream cleanup only)

### 2.3 Implementation Order

Implement in this order:

1. `guidance_ids.py`
2. `guidance_write_cli.py`
3. `guidance_writer.py`
4. guidance extraction/readback docs (`primary-pass.md`, `enrichment-pass.md`, `core-contract.md`, `guidance-queries.md`, `assets/8k-primary.md`)
5. tests
6. optional downstream cleanup only after the write path is correct

### 2.4 Validation Caveats

- `test_guidance_write_cli.py` is not a plain-`python3` gate today because several tests require `monkeypatch`
- `scripts/earnings/test_guidance_unit_safety.py` is not a pre-backfill migration gate; use it only after targeted V2 re-extraction / backfill or after updating its assertions per this spec
- shadow diff review is part of validation, not optional observability noise

### 2.5 Non-goals

- do not perform a graph-wide delete
- do not ship a Cypher-only in-place unit patch as the primary correction path
- do not change the downstream `canonical_unit` contract during V2 rollout
- do not require cache or renderer contract rewrites for correctness

---

## 3. New Payload Fields

These fields are added to the extraction JSON item payload.

### 3.1 `unit_kind_hint`

- Type: `string`
- Enum: `money | ratio | count | multiplier | unknown`
- Required for new primary/enrichment extractions
- Optional for legacy / 7E readback items during migration

Examples:

- `Revenue $10.3 billion` -> `money`
- `EPS $3.22` -> `money`
- `97.4 million shares outstanding` -> `count`
- `gross margin 42%` -> `ratio`
- `leverage 2.5x` -> `multiplier`

### 3.2 `money_mode_hint`

- Type: `string | null`
- Enum: `aggregate | price_like | unknown`
- Required when `unit_kind_hint == "money"`
- Must be `null` or omitted for non-money kinds

Examples:

- `Revenue $10.3 billion` -> `aggregate`
- `EPS $3.22` -> `price_like`
- `Average Selling Price $490,000` -> `price_like`
- `Fuel Cost per Metric Ton $675` -> `price_like`

### 3.3 Existing `unit_raw`

`unit_raw` remains required and remains verbatim surface unit text from the source, but its role changes:

- **Old role**: mixed semantic classifier + scale parser
- **New role**: scale / surface evidence only
- when a denominator phrase exists, preserve it inside `unit_raw` rather than stripping it away (for example `cents per share`, `$ per metric ton`, `dollars per unit`)

Examples:

- `"$10.3 billion"` -> `unit_raw="billion"`
- `"$490,000"` -> `unit_raw="$"`
- `"32 cents per share"` -> `unit_raw="cents per share"`
- `"$675 per metric ton"` -> `unit_raw="$ per metric ton"`
- `"97.4 million shares"` -> `unit_raw="million"`
- `"13 million members"` -> `unit_raw="million"`
- `"42%"` -> `unit_raw="%"`

### 3.4 Backward Compatibility

During migration:

- old payloads without `unit_kind_hint` / `money_mode_hint` must still work
- CLI falls back to deterministic surface/XBRL/label resolution when hints are absent
- phase-1 `shadow` mode must not change the authoritative Neo4j write contract
- additive resolved-axis graph properties become required when V2 writes / backfill begin, not during pure shadow writes

---

## 4. Internal Resolution Axes

These are internal resolver outputs. They are always computed in V2 code paths. They are persisted to Neo4j only for V2-written / backfilled rows, not for pure shadow-mode writes.

- `resolved_kind`: `money | ratio | count | multiplier | unknown`
- `resolved_money_mode`: `aggregate | price_like | unknown`
- `resolved_ratio_subtype`: `percent | percent_yoy | percent_points | basis_points | unknown`
- `resolved_scale_mode`: parsed from `unit_raw` only

Derived compatibility output:

- `canonical_unit`: existing enum

Mapping:

| resolved_kind | resolved_money_mode | resolved_ratio_subtype | canonical_unit |
|---|---|---|---|
| money | aggregate | n/a | `m_usd` |
| money | price_like | n/a | `usd` |
| ratio | n/a | percent | `percent` |
| ratio | n/a | percent_yoy | `percent_yoy` |
| ratio | n/a | percent_points | `percent_points` |
| ratio | n/a | basis_points | `basis_points` |
| count | n/a | n/a | `count` |
| multiplier | n/a | n/a | `x` |
| unknown | unknown | unknown | `unknown` |

### 4.1 `resolved_money_mode` semantics

`resolved_money_mode` is intentionally **not** a denominator field.

It answers the storage / interpretation question:

- `aggregate`: total money values normalized to millions of USD
- `price_like`: face-value money values normalized to absolute USD

Examples:

- `Revenue $89B` -> `money + aggregate` -> `m_usd`
- `EPS $3.22` -> `money + price_like` -> `usd`
- `Average Selling Price $490,000` -> `money + price_like` -> `usd`
- `Fuel Cost per Metric Ton $675` -> `money + price_like` -> `usd`

Per-share is a subset of `price_like`, not the whole category.

---

## 5. Resolver Precedence

V2 resolves each axis independently.

Implementation rule: collect all hard-evidence hits for an axis first, detect contradictions second, and only then apply precedence. Do not short-circuit on the first substring match; conflicting hard evidence must fail closed to `unknown`.

### 5.1 `resolved_kind`

| Priority | Evidence source | Rule | Output |
|---|---|---|---|
| 1 | explicit surface ratio markers | `unit_raw` contains isolated ratio markers such as `%`, `pct`, `percent`, `percentage`, `yoy`, `y/y`, `bp`, `bps`, `basis points`, `pp`, `ppts`, `percentage points` | `ratio` |
| 2 | explicit multiplier markers | `unit_raw` contains isolated multiplier markers such as `x`, `times`, `multiple`, including numeric suffix forms like `2.5x` | `multiplier` |
| 3 | explicit surface money markers | `unit_raw` contains isolated money markers such as `$`, `usd`, `dollar`, `dollars`, `cent`, `cents` | `money` |
| 4 | explicit XBRL count markers | XBRL concept contains reviewed share-count patterns such as `SharesOutstanding`, `ShareCount`, `WeightedAverageNumberOf...Shares`, `NumberOf...Shares`, and does not contain `PerShare` / `PerUnit` | `count` |
| 5 | explicit XBRL per-share markers | XBRL concept contains `PerShare`, `PerUnit`, `PerDilutedShare`, `PerBasicShare` | `money` |
| 6 | strong label hard evidence | tokenized label contains isolated `eps` or `dps`, or slug contains `per_share` / `per_unit` | `money` |
| 7 | LLM hint | valid `unit_kind_hint` present | hint value |
| 8 | conservative label prior | narrow count families only: `shares_outstanding`, `share_count`, `headcount` | prior value |
| 9 | fallback | no reliable evidence | `unknown` |

### 5.2 `resolved_money_mode`

Only evaluated when `resolved_kind == "money"`.

| Priority | Evidence source | Rule | Output |
|---|---|---|---|
| 1 | explicit XBRL per-share / per-unit markers | XBRL contains `PerShare`, `PerUnit`, `PerDilutedShare`, `PerBasicShare` | `price_like` |
| 2 | explicit surface denominator markers | `unit_raw` contains `per share`, `per diluted share`, `per basic share`, `per unit`, `per metric ton`, `per watt`, `per gallon`, or generic `per <noun>` | `price_like` |
| 3 | strong label hard evidence | tokenized label contains isolated `per`, `eps`, `dps`, or contains `per_share`, `per_unit` | `price_like` |
| 4 | LLM hint | valid `money_mode_hint` present | hint value |
| 5 | conservative label prior | very narrow weak prior only: exact/common price-like families such as `average_selling_price`, `average_daily_rate`, `asp`, `adr`, `arpu`, `revpar` | `price_like` |
| 6 | fallback | no evidence of face-value pricing | `aggregate` |

Important safety rule:

- do **not** use `quote` as hard evidence for `resolved_kind` or `resolved_money_mode`
- extraction quotes may contain neighboring metrics in the same sentence, so `%` / `$` / `per share` can belong to another item
- do **not** use a generic `price` substring as evidence
- live labels such as `price_contribution`, `price_mix`, and `average_selling_price_increase` prove broad `price` matching is unsafe
- `cost_per_*` does not need a special prior because isolated `per` already acts as strong hard evidence once `resolved_kind == "money"`

### 5.3 `resolved_ratio_subtype`

Only evaluated when `resolved_kind == "ratio"`.

Important rule: unit subtype wins over time qualifier. `yoy` describes temporal context, but `bps` and `percentage points` determine how the numeric value itself must be interpreted. Because the legacy enum cannot encode both dimensions at once, numeric-interpretation subtype must take precedence.

| Priority | Evidence source | Rule | Output |
|---|---|---|---|
| 1 | explicit bps markers | `unit_raw` tokenized match contains `bp`, `bps`, `basis point`, `basis points` | `basis_points` |
| 2 | explicit points markers | `unit_raw` tokenized match contains `pp`, `ppt`, `ppts`, `point`, `points`, `percentage point`, `percentage points` | `percent_points` |
| 3 | explicit YoY markers | `unit_raw` tokenized match contains `yoy`, `y/y`, `year over year`, `year-over-year`, `yr/yr` | `percent_yoy` |
| 4 | fallback | plain percentage level | `percent` |

### 5.4 Scale Parsing

Scale is parsed from `unit_raw` only. It must not determine semantic kind.

Supported scale signals:

- `trillion`, `trillions`, `t` -> `1e12`
- `billion`, `billions`, `bn`, `b` -> `1e9`
- `million`, `millions`, `mm`, `mn`, `m` -> `1e6`
- `thousand`, `thousands`, `k` -> `1e3`
- `cent`, `cents` -> `1e-2`
- no scale word -> `1`

Compound unit strings must be supported:

- `million shares`
- `million members`
- `thousand units`
- `cents per share`

Implementation rules:

- parse for **one recognized scale token anywhere in the string**
- match scale words at the word/token level, not by arbitrary substring
- ignore non-scale nouns after scale extraction
- `million shares` -> `million`
- `cents per share` -> `cents`

### 5.5 Contradiction Policy

The resolver must never silently prefer a weak hint over strong evidence.

Rules:

- hard surface/XBRL evidence always outranks LLM hints
- strong label hard evidence outranks LLM hints
- if two hard-evidence sources disagree across incompatible families, resolve to `unknown`
- if a hint conflicts with hard evidence, ignore the hint and continue
- if evidence is incomplete but non-contradictory, accept the best available signal

Examples:

- hint=`money`, surface=`%` -> `ratio`
- hint=`money+aggregate`, XBRL=`PerShare` -> `money+price_like`
- hint=`count`, surface=`$` with no count hard evidence -> `money`
- hard count evidence + hard money evidence -> `unknown`
- `resolved_kind=money` + `resolved_money_mode=aggregate` + `unit_raw` containing isolated `cent` / `cents` -> contradiction; fail closed during V2 resolution / scaling by raising `ValueError`, never normalize as aggregate money

---

## 6. Canonical Value Normalization

Once axes are resolved:

### 6.1 Money, aggregate

- canonical unit: `m_usd`
- normalization target: millions of USD

Examples:

- `10.3 billion` -> `10300.0`
- `94 million` -> `94.0`
- `2000` with no scale -> `2000.0` (assumed already in millions per existing contract)

### 6.2 Money, price-like

- canonical unit: `usd`
- normalization target: face dollars

Examples:

- `3.22` -> `3.22`
- `32 cents` -> `0.32`
- `490000` -> `490000`

### 6.2A Scale conversion tables

For clarity, V2 uses two distinct scale interpretations for money:

| Scale word | aggregate money -> millions | price-like money -> absolute dollars |
|---|---:|---:|
| trillion | `1000000` | `1e12` |
| billion | `1000` | `1e9` |
| million | `1` | `1e6` |
| thousand | `0.001` | `1e3` |
| cent / cents | n/a | `0.01` |
| none | `1` (legacy behavior) | `1` |

Guard rule:

- `cent` / `cents` is only valid for `money + price_like`
- authoritative detection point: `_scale_aggregate_money()` must raise `ValueError` if aggregate money encounters isolated `cent` / `cents`
- writer validation then acts as belt-and-suspenders for any item that reaches the write path in that impossible state
- do not silently reinterpret aggregate money as price-like inside normalization

### 6.3 Count

- canonical unit: `count`
- normalization target: absolute quantity

Examples:

- `97.4 million` -> `97_400_000`
- `13 million` -> `13_000_000`
- `244` -> `244`

Count scale conversion table:

| Scale word | count -> absolute quantity |
|---|---:|
| trillion | `1e12` |
| billion | `1e9` |
| million | `1e6` |
| thousand | `1e3` |
| none | `1` |

### 6.4 Ratio and multiplier

- `percent*` -> preserve numeric face value
- `x` -> preserve numeric face value

### 6.5 Ambiguous / unknown

- preserve numeric face value unchanged
- do not invent scaling

---

## 7. Function-Level Code Changes

## 7.1 `.claude/skills/earnings-orchestrator/scripts/guidance_ids.py`

### Add constants

- `VALID_UNIT_KIND_HINTS = {'money', 'ratio', 'count', 'multiplier', 'unknown'}`
- `VALID_MONEY_MODE_HINTS = {'aggregate', 'price_like', 'unknown'}`

### Add helper functions

- `_normalize_unit_text(text: Optional[str]) -> str`
- `_extract_scale_factor(unit_raw: str) -> Optional[float]` — returns the raw absolute scale multiplier per §5.4's scale table (e.g., `1e9` for "billion", `1e6` for "million", `0.01` for "cents", `None` for no scale word). Mode-independent; the `_scale_*` functions apply mode-specific normalization.
- `_scale_aggregate_money(value: float, unit_raw: str) -> float`
- `_scale_price_like_money(value: float, unit_raw: str) -> float`
- `_scale_count_absolute(value: float, unit_raw: str) -> float`
- `_has_ratio_surface(unit_raw: str) -> bool`
- `_has_multiplier_surface(unit_raw: str) -> bool`
- `_has_money_surface(unit_raw: str) -> bool`
- `_has_price_like_surface(unit_raw: str, xbrl_qname: Optional[str]) -> bool`
- `_has_hard_label_money_signal(label_slug: str) -> bool`
- `_has_hard_label_price_like_signal(label_slug: str) -> bool`
- `_resolve_kind(unit_kind_hint, unit_raw, xbrl_qname, label_slug) -> str`
- `_resolve_money_mode(money_mode_hint, unit_raw, xbrl_qname, label_slug, resolved_kind) -> str`
- `_resolve_ratio_subtype(unit_raw, quote) -> str`
- `_combine_resolved_unit(resolved_kind, resolved_money_mode, resolved_ratio_subtype) -> str`

Implementation notes:

- `_normalize_unit_text()` should lowercase, strip, and collapse internal whitespace before token/word matching
- `_has_ratio_surface()` must use token/word matching so `percent` is ratio, not money via `cent`
- `_has_money_surface()` must match `cent` / `cents` as isolated words or symbols, never as substrings inside `percent`
- `_has_multiplier_surface()` must recognize isolated `x` and numeric suffix forms like `2.5x`, with behavior equivalent to whole-word `x` or a numeric token ending in `x`; it must not match false positives such as `tax`, `max`, `next`, or `index`
- `_resolve_ratio_subtype()` may use `quote` only to supply YoY temporal context after all explicit `unit_raw` subtype checks fail; never inspect `quote` for `bp` / `bps` / `point` / `points` / `percentage point(s)` markers; `quote` must never override an explicit `unit_raw` subtype hit
- `_scale_aggregate_money()` must implement the millions-normalized column of table 6.2A and preserve the legacy pre-scaled guard semantics relative to the millions target unit. In practice, compare the scale-to-millions factor, not the raw absolute scale token, so the guard still fires for billion/trillion but not for ordinary million-scale inputs.
- `_scale_count_absolute()` must preserve the same legacy pre-scaled guard semantics used by the current count path. Do not apply a literal `raw_scale > 1` check to absolute factors, or valid inputs like `1500 million shares` will be rejected.
- `_scale_price_like_money()` must implement the absolute-dollar column of table 6.2A. Do not inherit the legacy guard literally from V1, because V1 had no equivalent price-like scaling path and a raw absolute-factor check would incorrectly reject valid `cents` / `thousand` inputs.
- keep `_parse_numeric_with_scale()` for backward-compatible legacy fallback paths when resolved axes are absent; V2 paths should prefer `_extract_scale_factor()`

### Keep for backward compatibility

- `canonicalize_unit(unit_raw, label_slug)` must remain callable
- keep the existing legacy behavior / alias semantics for this function so current callers and tests still work for scale-only words like `billion`, `million`, `bn`, and `m`
- do **not** make `canonicalize_unit()` a thin wrapper around the V2 resolver with all hints/evidence absent; that would break backward compatibility on legacy callers that rely on V1 alias behavior

### Change `canonicalize_value(...)`

Current signature:

```python
canonicalize_value(value, unit_raw, canonical_unit, label_slug)
```

New signature:

```python
canonicalize_value(
    value,
    unit_raw,
    canonical_unit,
    label_slug,
    resolved_kind: Optional[str] = None,
    resolved_money_mode: Optional[str] = None,
)
```

New behavior:

- stop gating count scaling on `_is_share_count_label()`
- stop gating per-share no-scaling on `_is_per_share_label()`
- scale according to resolved axes when provided
- preserve current fallback behavior when axes are absent

Required branching structure:

```python
if value is None:
    return None

if resolved_kind is not None:
    # V2 path
    if resolved_kind == 'money':
        if resolved_money_mode == 'price_like':
            return _scale_price_like_money(value, unit_raw)
        if resolved_money_mode == 'aggregate':
            return _scale_aggregate_money(value, unit_raw)
    if resolved_kind == 'count':
        return _scale_count_absolute(value, unit_raw)
    return value

# V1 fallback path (preserve existing legacy behavior when axes are absent)
if canonical_unit == 'count' and _is_share_count_label(label_slug) and unit_raw:
    ...
if _is_per_share_label(label_slug):
    return value
if canonical_unit == 'm_usd' and unit_raw:
    ...
return value
```

Price-like examples that MUST work in V2:

- `32` + `unit_raw='cents'` -> `0.32`
- `490` + `unit_raw='thousand'` -> `490000.0`
- `3.22` + `unit_raw='dollars'` -> `3.22`

### Change `build_guidance_ids(...)`

Add optional params:

```python
unit_kind_hint: Optional[str] = None,
money_mode_hint: Optional[str] = None,
quote: Optional[str] = None,
xbrl_qname: Optional[str] = None,
existing_guidance_id: Optional[str] = None,
existing_resolved_kind: Optional[str] = None,
existing_resolved_money_mode: Optional[str] = None,
existing_resolved_ratio_subtype: Optional[str] = None,
existing_resolution_version: Optional[str] = None,
resolution_mode: str = 'v2',
```

Implementation:

1. validate hint enums if present
2. compute `label_slug`
3. resolve axes
4. if current evidence is insufficient, allow existing resolved-axis fallback only when `existing_resolution_version >= "v2"` and the incoming `label_slug` still matches the existing `guidance_id` / prior label identity from 7E
5. derive `canonical_unit`
6. compute canonical values using resolved axes
7. compute `evhash16` unchanged from derived `canonical_unit`
8. return resolved axes as additive internal fields
9. do **not** include raw LLM hint fields in return payload

Required additive return fields:

- `resolved_kind`
- `resolved_money_mode`
- `resolved_ratio_subtype`
- `resolution_version`

These are writer-authoritative internal outputs, not agent hints.

### Shadow-mode behavior

`build_guidance_ids()` must support explicit `resolution_mode` branching:

- `v1`: compute current behavior only
- `v2`: compute V2 behavior only
- `shadow`: compute both, return V1 as effective write payload plus a nested V2 diff block for observability

Preferred design:

- CLI reads `GUIDANCE_UNIT_RESOLUTION_MODE`
- CLI passes `resolution_mode` explicitly into `build_guidance_ids()`
- do **not** hide env branching inside low-level helpers where possible

In `shadow`, include enough diff metadata for logging:

```python
shadow_v2 = {
    'canonical_unit': ...,
    'canonical_low': ...,
    'canonical_mid': ...,
    'canonical_high': ...,
    'resolved_kind': ...,
    'resolved_money_mode': ...,
    'resolved_ratio_subtype': ...,
}
```

## 7.2 `.claude/skills/earnings-orchestrator/scripts/guidance_write_cli.py`

### `_ensure_ids(...)`

`_ensure_ids()` must no longer early-return on pre-computed IDs.

Replace the current behavior:

```python
if item.get('guidance_update_id'):
    return item
```

With:

- always recompute deterministic fields from the current payload
- preserve `period_u_id` when already present
- overwrite stale `guidance_id`, `guidance_update_id`, `evhash16`, `canonical_unit`, and canonical numeric values with CLI-authoritative results
- if pre-computed deterministic fields were present, optionally capture a diff in shadow/debug output

Also replace:

```python
unit_raw=item.get('unit_raw') or item.get('canonical_unit') or 'unknown'
```

With:

```python
unit_raw=item.get('unit_raw') or 'unknown'
```

And pass through:

```python
unit_kind_hint=item.get('unit_kind_hint'),
money_mode_hint=item.get('money_mode_hint'),
quote=item.get('quote'),
xbrl_qname=item.get('xbrl_qname'),
existing_guidance_id=item.get('guidance_id'),
existing_resolved_kind=item.get('resolved_kind'),
existing_resolved_money_mode=item.get('resolved_money_mode'),
existing_resolved_ratio_subtype=item.get('resolved_ratio_subtype'),
existing_resolution_version=item.get('resolution_version'),
resolution_mode=resolution_mode,
```

### Validation

Add deterministic payload-origin classification before enforcing hint requirements.

Required top-level CLI input field for post-upgrade batches:

```json
{"payload_origin": "extract_v2 | legacy_extract | readback"}
```

Classification rules:

- if `payload_origin == "extract_v2"`, treat items as fresh post-upgrade extraction output
- if `payload_origin == "readback"`, treat items as 7E enrichment/readback payloads
- if `payload_origin == "legacy_extract"`, treat items as pre-upgrade / backward-compatible extraction payloads

Fallback inference is only for backward compatibility:

- if `payload_origin` is absent and `resolution_version == "v2"`, infer `readback`
- otherwise default to `legacy_extract`
- do **not** infer `readback` from `guidance_id` or `guidance_update_id` alone

Add pre-ID validation:

- if `unit_kind_hint` invalid -> `ValueError`
- if `money_mode_hint` present but invalid -> `ValueError`
- if `unit_kind_hint != 'money'` and `money_mode_hint` present non-null -> `ValueError`
- if payload origin is `extract_v2` and `unit_kind_hint` is absent -> `ValueError`
- if payload origin is `extract_v2` and `unit_kind_hint == 'money'` and `money_mode_hint` is absent -> `ValueError`
- if payload origin is `extract_v2` and any of `low`, `mid`, `high` is numeric and `unit_raw` is absent, blank, or literal `"unknown"` -> `ValueError`
- if payload origin is `legacy_extract` or `readback`, allow missing `money_mode_hint`; those may fall through to deterministic evidence and conservative fallback

Implementation note: this payload-origin classification must be explicit and shared so every CLI implementation makes the same decision about whether missing hints are an error.

### Batch ordering fix

`main()` must change ordering so XBRL concept repair is available before V2 unit resolution:

1. inject `source_id`
2. compute `label_slug = slug(item["label"])` early for every item that has a label
3. ensure / validate periods and minimal required fields
4. load concept cache
5. apply deterministic concept resolution
6. apply concept inheritance across same-label siblings
7. compute IDs + canonical fields via `build_guidance_ids()`
8. compute `concept_family_qname`
9. validate and write

Implementation note: because current `_ensure_ids()` is monolithic in live code, implementation should either split it into period-stage and ID-stage helpers or otherwise guarantee this ordering explicitly. The important contract is that period computation and concept repair run before final ID/unit computation.

This is required because V2 resolution uses `xbrl_qname` as hard evidence.

### Concept resolution ordering

The preferred fix is to reorder concept repair before ID computation, not to treat XBRL evidence as best-effort only.

Rationale:

- `apply_concept_resolution()` already works from `label_slug` or `slug(label)` and does not require pre-computed IDs
- concept inheritance also only needs label identity, not finalized IDs
- this lets V2 use repaired / inherited `xbrl_qname` during canonical resolution and writer validation

### Observability sidecar

Extend `/tmp/gu_written_{source_id}.json` rows with:

- `unit_kind_hint`
- `money_mode_hint`
- `resolution_version: "v2"`
- `resolved_kind`
- `resolved_money_mode`
- `resolved_ratio_subtype`

For `shadow`, write a separate or extended diff artifact containing both V1 and V2 effective outputs.

This is additive only and not part of graph schema.

## 7.3 `.claude/skills/earnings-orchestrator/scripts/guidance_writer.py`

### `_validate_item(...)`

Add stricter numeric fail-closed checks:

- numeric per-share labels cannot write as `unknown`
- numeric price-like labels cannot write as `m_usd`
- numeric aggregate-money items cannot write with `unit_raw` containing isolated `cent` / `cents`
- numeric explicit ratio evidence cannot write as `m_usd`, `usd`, or `count`
- numeric explicit count evidence cannot write as `m_usd`
- numeric contradictory hard evidence must reject instead of downgrading silently

Rules:

- qualitative-only items may still use `unknown`
- aggregate money items remain allowed as `m_usd`
- preserve current existing guards

Writer validation must consume resolved axes from the item when available:

- prefer `resolved_kind`, `resolved_money_mode`, and `resolved_ratio_subtype` from `build_guidance_ids()`
- only fall back to legacy label/XBRL heuristics when resolved axes are absent (V1 / older payload compatibility)

### Write-path scope

V2 explicitly changes the authoritative Neo4j write path:

- `guidance_writer.py` must persist the V2-resolved `canonical_unit`
- `guidance_writer.py` must persist V2-normalized numeric values (`low`, `mid`, `high`) under the existing graph properties
- `guidance_writer.py` must persist additive resolved-axis properties needed for safe 7E round-trips:
  - `resolved_kind`
  - `resolved_money_mode`
  - `resolved_ratio_subtype`
  - `resolution_version`
- the graph write contract remains backward-compatible because the written property names do not change
- downstream readers should receive corrected data from Neo4j without needing a parallel contract migration

### `_build_params(...)`

Required signature change:

```python
def _build_params(item, source_id, source_type, ticker, resolution_mode='v2'):
```

`write_guidance_item()` and `write_guidance_batch()` must also accept and forward `resolution_mode` so the CLI can thread it through from the top-level env var.

Required additions:

- map `resolved_kind`
- map `resolved_money_mode`
- map `resolved_ratio_subtype`
- map `resolution_version`
- in `v1` and `shadow`, `_build_params()` must suppress `resolved_kind`, `resolved_money_mode`, `resolved_ratio_subtype`, and `resolution_version` even if those keys are present on the item
- only `resolution_mode == "v2"` may map those fields into Cypher params / `SET` clauses

`_build_core_query(...)` must add matching `SET` clauses on `gu` for those additive properties (V2 mode only).

Keep this logic unchanged by design:

```python
'unit_raw': item.get('unit_raw') if item.get('canonical_unit') == 'unknown' else None
```

Implication:

- V2 should persist **fewer** `unit_raw` values than V1 because fewer items remain `unknown`
- this is intentional and should not be treated as a regression

### Additive graph-property change

Pure phase-1 shadow mode still requires no new constraints or indexes. Additive node properties become required when the V2 write path is enabled and 7E round-trips are expected to carry resolved axes.

- keep writing `canonical_unit`
- keep writing `unit_raw` only when `canonical_unit == 'unknown'`
- do not require new constraints or indexes just to ship V2 correctness
- additive resolved-axis properties are required for the V2 write path and V2-backed 7E round-trips

## 7.4 `.claude/skills/extract/types/guidance/primary-pass.md`

Update extraction contract:

- add `unit_kind_hint`
- add `money_mode_hint`
- redefine `unit_raw` as scale/surface only
- keep instruction: copy source text exactly for numeric value and scale

### Required wording change

Add:

```text
unit_kind_hint: REQUIRED. One of money, ratio, count, multiplier, unknown.
money_mode_hint: REQUIRED when unit_kind_hint == money. One of aggregate, price_like, unknown.
unit_raw: REQUIRED. Verbatim surface scale/unit text from source. Preserve denominator phrases when present, for example `cents per share` or `$ per metric ton`. Used for scale parsing and denominator-surface detection, not final semantic classification.
```

## 7.5 `.claude/skills/extract/types/guidance/enrichment-pass.md`

Same field additions as primary pass.

Special rule:

- enrichment Step 6 output (changed + new items) should use `payload_origin=extract_v2` because every emitted item was actively processed by the enrichment agent and must carry hints
- pure 7E readback used as agent input (not the CLI write payload) is a separate concern; if a readback-only batch is ever written directly, it should use `payload_origin=readback`
- for `readback` items, hints may be absent
- for `extract_v2` items (including enrichment output), `unit_kind_hint` is required; `unit_raw` is required for numeric items (any of `low`/`mid`/`high` non-null) per §7.2 validation
- CLI fallback must remain safe when hints are absent

Enrichment round-trip rule:

- 7E readback must include `resolved_kind`, `resolved_money_mode`, `resolved_ratio_subtype`, and `resolution_version` for V2-written / backfilled rows
- pre-V2 rows are not guaranteed to have recoverable resolved-axis context; enrichment fallback must not assume they do
- existing items should preserve returned resolved-axis fields from 7E as fallback semantic context only when `resolution_version >= "v2"`
- if enrichment changes label/unit semantics materially, the new payload should include fresh hints and/or raw surface evidence so old resolved-axis fallback is not relied on
- after the Phase-4 V2 flip, pre-V2 readback items without fresh hints/raw surface evidence or validated V2 resolved-axis context must not be V2-rewritten during enrichment; skip rewrite or leave the legacy row untouched until targeted re-extraction/backfill upgrades that source
- **control point**: in `guidance_write_cli.py`, before an item is added to `valid_items` for `resolution_mode='v2'`, if `payload_origin == 'readback'` and the item lacks both (a) fresh incoming hints/raw surface evidence and (b) `resolution_version == "v2"` fallback context, the CLI must skip the item, must not pass it to `write_guidance_batch()`, and must record `pre_v2_readback_skip` in `id_errors`
- update `.claude/skills/extract/types/guidance/guidance-queries.md` query 7E accordingly

## 7.6 Tests

### Update / add tests in:

- `.claude/skills/earnings-orchestrator/scripts/test_guidance_ids.py`
- `.claude/skills/earnings-orchestrator/scripts/test_guidance_write_cli.py`
- `.claude/skills/earnings-orchestrator/scripts/test_guidance_writer.py`

### Required new cases

- `Adjusted EPS Diluted` + `unit_kind_hint=money` + `money_mode_hint=price_like` -> `usd`
- `Weighted Average Basic Shares Outstanding` + `unit_kind_hint=count` + `unit_raw=million` -> `count`, scaled absolute
- `Loyalty Members` + `unit_kind_hint=count` + `unit_raw=million` -> `count`, scaled absolute
- `Average Selling Price` + `unit_kind_hint=money` + `money_mode_hint=price_like` -> `usd`
- `Average Daily Rate` + `unit_kind_hint=money` + `money_mode_hint=price_like` -> `usd`
- `ARPU` + `unit_kind_hint=money` + `money_mode_hint=price_like` -> `usd`
- `Fuel Cost per Metric Ton` + `unit_kind_hint=money` + `money_mode_hint=price_like` -> `usd`
- `Dividend Per Share` + `unit_raw=cents` -> `usd`, value divided by `100`
- `EPS growth 4%-5%` with ratio surface -> `percent_yoy` or `percent`
- hard label token `per` in `fuel_cost_per_metric_ton` forces `price_like` over bad aggregate hint
- mixed-kind label: `Content Per Vehicle` with money quote and `unit_kind_hint=money` resolves to `usd`
- mixed-kind label: `Content Per Vehicle` with `%` surface resolves to `percent` / `percent_points`, not money
- `Adjusted Cruise Costs Excluding Fuel Per ALBD Growth` with `%` surface resolves to ratio even though label contains isolated `per`
- `Net Active Customer Additions Per Quarter` with `unit_kind_hint=count` resolves to `count`; isolated `per` must not influence non-money kinds
- `Revenue` with quote containing both `$89 billion` and `15% growth` still resolves to money because kind uses `unit_raw`, not quote
- `unit_raw=percent` resolves to ratio; `cent` substring must not leak into money detection
- `unit_raw=2.5x` resolves to multiplier
- `unit_raw="50 bps yoy"` resolves to `basis_points`, not `percent_yoy`
- `unit_raw="1.5 percentage points yoy"` resolves to `percent_points`
- `unit_raw="2% yoy"` resolves to `percent_yoy`
- `Revenue Run Rate` with money hints resolves to `m_usd`; `rate` in label must not trigger ratio
- empty `unit_raw` / `None` with valid V2 hints still resolves correctly for `legacy_extract` or `readback` payloads (extract_v2 numeric items are rejected at validation per §7.2; qualitative-only extract_v2 items may also lack `unit_raw`)
- mixed-case `unit_raw="Billion"` resolves like `billion`
- `unit_raw="trillion"` and `unit_raw="t"` both scale correctly
- count item with `unit_raw="billion"` scales to absolute quantity
- plural `unit_raw="millions"` resolves like `million`
- price-like money with `unit_raw="thousand"` scales to absolute dollars
- `Tax Rate` with `unit_raw=%` resolves to ratio regardless of money hints
- `unit_kind_hint=money` + `money_mode_hint=aggregate` + `unit_raw=cents` fails closed; aggregate money cannot use cents
- bad money hint + `%` surface resolves to `ratio`
- conflicting hard count + hard money evidence resolves to `unknown`
- old payload with no hints still works via fallback
- `Average Selling Price` read back from 7E with `resolved_kind=money`, `resolved_money_mode=price_like`, no hints, and no `unit_raw` must still recompute to `usd`
- readback ratio item with `resolved_kind=ratio` and `resolved_ratio_subtype=percent_yoy`, no `unit_raw`, must preserve ratio family
- pre-computed `guidance_update_id` present but stale -> CLI overwrites it with recomputed authoritative ID
- concept-repaired `xbrl_qname` available before ID computation changes a would-be fallback classification into the correct XBRL-backed classification

## 7.7 Optional Downstream Cleanup

These changes are **not required for V2 correctness** because corrected data should already flow through the existing Neo4j properties.

### Optional: `.claude/skills/earnings-orchestrator/scripts/warmup_cache.py`

Relevant touch points:

- `resolve_unit_groups(...)`
- `_format_value(...)`

Optional cleanup tasks:

- add regression coverage proving `resolved_unit` grouping behaves correctly once `canonical_unit` is fixed upstream
- verify unknown-remap behavior does not hide mixed-unit series after V2 backfill
- add focused formatting tests for corrected `usd`, `m_usd`, `count`, and ratio outputs using known bad families such as `average_selling_price`, weighted-average share counts, and `dividend_per_share`

Important note:

- no semantic regrouping change is required for V2 rollout
- existing grouping/formatting logic should improve automatically once Neo4j is populated with corrected `canonical_unit` values

### Optional: `scripts/earnings/earnings_orchestrator.py`

Relevant touch point:

- `_fmt_guidance_value(...)`

Optional cleanup tasks:

- add renderer regression tests for corrected face-value `usd` metrics, corrected `count` metrics, and ratio metrics that previously collided under bad units
- verify no stale assumptions remain about known misclassified families

Important note:

- no renderer contract change is required for V2 rollout
- this file should only need optional cleanup / test hardening, not core semantic changes

---

## 8. Migration Plan

## Phase 0: Land Backward-Compatible Code

- Add V2 resolver logic
- Keep current constraints/indexes
- Keep current downstream readers
- Keep fallback path for old payloads
- Add code support for additive resolved-axis properties needed for safe V2 round-trips

No behavior switch yet.

## Phase 1: Shadow Mode

Introduce env flag:

- `GUIDANCE_UNIT_RESOLUTION_MODE=shadow | v1 | v2`

Behavior:

- `v1`: current behavior only
- `shadow`: compute both V1 and V2, write pure V1 graph data only, persist no V2 `resolved_*` fields to Neo4j, and log the V2 diff summary out-of-band
- `v2`: compute and write V2 result, including additive `resolved_*` fields and `resolution_version`

Shadow logging must capture:

- label
- unit_raw
- old `canonical_unit`
- new `canonical_unit`
- old vs new canonical values
- old vs new resolved axes
- whether the item is numeric or qualitative

## Phase 2: Prompt Upgrade

Update all guidance extraction/reference docs together:

- `.claude/skills/extract/types/guidance/primary-pass.md`
- `.claude/skills/extract/types/guidance/enrichment-pass.md`
- `.claude/skills/extract/types/guidance/core-contract.md`
- `.claude/skills/extract/types/guidance/guidance-queries.md`
- `.claude/skills/extract/types/guidance/assets/8k-primary.md`

Add / document emitted fields:

- `unit_kind_hint`
- `money_mode_hint`
- top-level `payload_origin=extract_v2` for fresh post-upgrade extraction batches

Required explicit replacements in `assets/8k-primary.md`:

- replace `"$94-98 billion"` example: change `low=94000, high=98000` to `low=94, high=98, unit_raw="billion"`
- replace `"$2 billion"` example: change `mid=2000` to `mid=2, unit_raw="billion"`
- replace `"at least $150M"` example: change `low=150` to `low=150, unit_raw="million"`

Prepare the 7E readback contract to expose, for V2-written / backfilled rows:

- `resolved_kind`
- `resolved_money_mode`
- `resolved_ratio_subtype`
- `resolution_version`

## Phase 3: Validation Gate

Run in `shadow` until all of these are true on recent corpora:

- no regression in aggregate money series
- `Average Selling Price` and `Fuel Cost per Metric Ton` resolve to `usd`
- per-share numeric `unknown` collapses materially
- weighted-average share counts resolve to `count`
- count-like money leaks collapse materially

Validation commands:

- `python3 .claude/skills/earnings-orchestrator/scripts/test_guidance_ids.py`
- `python3 .claude/skills/earnings-orchestrator/scripts/test_guidance_writer.py`
- corpus-scoped shadow diff review on recent guidance populations
- `test_guidance_write_cli.py` is not a plain-`python3` gate today because several tests require `monkeypatch`; either run it under `pytest` in a pytest-enabled env or convert those tests to a standalone runner before using it as a gate

Do **not** use `scripts/earnings/test_guidance_unit_safety.py` as a pre-backfill Phase-3 gate. That script is database-wide and currently flags all `unknown` rows and non-`usd` per-share rows, which is incompatible with the staged migration and qualitative-only `unknown` allowance. Run an updated version of that script only after targeted V2 re-extraction / backfill.

## Phase 4: Flip to V2 Write

- set `GUIDANCE_UNIT_RESOLUTION_MODE=v2`
- write corrected `canonical_unit` and normalized numeric values to Neo4j through the existing `GuidanceUpdate` properties
- keep graph schema unchanged
- keep downstream renderer/cache/query code unchanged because `canonical_unit` output contract is preserved
- do not V2-rewrite pre-V2 enrichment readback items unless the incoming payload carries fresh hints/raw surface evidence or validated `resolution_version >= "v2"` fallback context

## Phase 5: Targeted Re-extraction

Re-run the known bad families first, using pattern/family selection rather than exact slugs only:

- EPS / DPS / per-share families, including label variants such as `adjusted_eps_diluted`, `adjusted_diluted_eps`, `dividend_per_share`, `dividends_per_share`, `fcf_per_share`
- weighted-average share-count / shares-outstanding families
- operational count families such as `hsa_count`, `loyalty_members`, `total_accounts`, `active_customers`, `net_active_customer_additions_per_quarter`
- price-like money families such as `average_selling_price`, `average_daily_rate`, `arpu`, `revpar`, `fuel_cost_per_metric_ton`, `content_per_vehicle`
- any additional live rows surfaced by the shadow diff / safety queries as `m_usd` leaks, numeric `unknown`, or count-like money mismatches

Operational note for the known 885 source docs that already have guidance:

- validated on the live graph on 2026-04-10: the query below returned `885` distinct source docs on three consecutive runs, and the grouped source listing also returned `885` rows
- once V2 is finalized, setting `guidance_status = NULL` on those specific source docs is sufficient to let them re-enter normal guidance extraction / merge flow without `--force`
- this works because both the daemon and the default bulk trigger treat `guidance_status IS NULL` as eligible for requeue
- caveat: the source still must be otherwise eligible for routing, and the daemon may defer immediate requeue if a Redis guidance lease is still active

Discovery query for the exact source-doc population:

```cypher
MATCH (gu:GuidanceUpdate)-[:FROM_SOURCE]->(src)
WITH labels(src) AS source_labels,
     src.id AS source_id,
     src.guidance_status AS guidance_status,
     count(gu) AS guidance_update_count
RETURN source_labels, source_id, guidance_status, guidance_update_count
ORDER BY source_id;
```

Count query used to validate the population size:

```cypher
MATCH (gu:GuidanceUpdate)-[:FROM_SOURCE]->(src)
WITH DISTINCT src
RETURN count(src) AS source_doc_count;
```

Reset query for that discovered population:

```cypher
MATCH (gu:GuidanceUpdate)-[:FROM_SOURCE]->(src)
WITH DISTINCT src
SET src.guidance_status = NULL
RETURN count(src) AS reset_count;
```

## Phase 6: Historical Backfill

After targeted validation passes, backfill broader history.

---

## 9. No-Downstream-Breakage Guarantees

These outputs must remain unchanged in interface:

- `canonical_unit` field continues to exist
- `GuidanceUpdate` graph schema remains valid
- `evhash16` format remains unchanged
- `guidance_update_id` format remains unchanged
- renderer continues to consume `resolved_unit` / `canonical_unit`
- warmup cache grouping continues to use `resolved_unit`

Important implication:

- cache grouping and renderer behavior improve automatically once the Neo4j write path starts emitting corrected `canonical_unit` values
- no separate downstream semantic migration is required for correctness

Additive only in phase 1:

- new request payload fields
- sidecar observability fields
- internal resolver helpers

Not required in pure phase-1 shadow mode:

- no new graph constraints
- no new Neo4j persisted `resolved_*` fields
- no new downstream consumer query changes are required in pure phase-1 shadow mode
- no cache schema change

---

## 10. Success Criteria

V2 is considered successful when:

1. all existing unit tests pass
2. new V2 tests pass
3. `Average Selling Price` / `Fuel Cost per Metric Ton` stop writing as `m_usd`
4. weighted-average share counts stop writing as `m_usd`
5. numeric per-share `unknown` drops materially
6. count-like money leaks drop to near zero
7. no aggregate money regressions appear in shadow diff review

**Primary objective**: no silent wrong-unit writes.
**Secondary objective**: maximize automatic classification coverage.

### 10.1 Residual exposed set

Even in V2, a bounded class of metrics will still depend primarily on hints or narrow priors because they lack strong structural evidence:

- abbreviated / label-compressed price-like families such as `average_selling_price`, `average_daily_rate`, `arpu`, `revpar`
- some operational count families such as `hsa_count`, `loyalty_members`, `total_accounts`, `active_customers`, and `net_active_customer_additions_per_quarter` when raw surface evidence is sparse

This is acceptable because:

- current V1 already misclassifies several of these badly
- LLM semantic understanding is the best available signal for them
- only very narrow weak priors are allowed for the most common exact families / abbreviations
- broad substring matching is explicitly forbidden because live counterexamples already exist
- contradiction checks still prevent obvious hard-evidence conflicts from writing silently
