# Fix Issues #52-#58: Corrected Diagnosis + Denormalized Slugs

## Investigation Summary

Cross-referenced the **spec** (SKILL.md §1-§3), **writer code** (`guidance_writer.py`), **test suite** (`test_guidance_writer.py:693`), and **live DB** (Neo4j property audit of all 47 GuidanceUpdate nodes).

**Finding: the writer is correctly implementing the spec. 5 of 7 issues are either audit errors or spec misreadings. 2 are legitimate queryability gaps.**

### Issue-by-Issue Diagnosis

| # | Claimed Bug | Root Cause | Evidence | Verdict |
|---|---|---|---|---|
| 52 | `u_id` null on GuidanceUpdate | Spec defines `u_id` only on GuidancePeriod (§1 line 407-408). GuidanceUpdate §1 (lines 94-99) lists: `id`, `evhash16`, `xbrl_qname`, `unit_raw` — no `u_id`. | `MATCH (gp:GuidancePeriod) WHERE gp.u_id IS NOT NULL RETURN count(gp)` → 8. No `u_id` in GU spec. | **Not a bug** — close |
| 53 | `label`/`label_slug` null on GU | `label` is on Guidance parent node (§1 line 86), not GU. `label_slug` is an ID computation intermediate (§3 line 177), not a stored property. The spec stores metric identity on the parent; GU reaches it via `UPDATES` edge. | §2 extraction fields (lines 107-128): 20 fields listed, `label`/`label_slug` not among them. | **Queryability gap** — fix |
| 54 | `direction` null on GU | `direction` appears **zero times** in the entire SKILL.md. Grep confirmed: no matches. Field was never designed or specified. | `grep -c direction SKILL.md` → 0 | **Not a bug** — close |
| 55 | `segment_raw`/`segment_slug` null | `segment` (§2 field #6, line 114) IS stored and populated 47/47. `segment_slug` is an ID computation intermediate (§3 line 178), not a stored property. `segment_raw` doesn't exist in spec — `segment` serves that role. | DB audit: `count(gu.segment)` → 47/47. | **Queryability gap** — fix |
| 56 | `evhash` null | Correct property name IS `evhash16` per spec (§1 line 97, §3 lines 158-161: "Stored as `gu.evhash16` property"). DB has it on 47/47. Audit queried wrong name. | `count(gu.evhash16)` → 47/47 | **Audit error** — close |
| 57 | `value_low/high/point` null | Correct names ARE `low/mid/high` per spec (§2 fields 7-9, lines 115-117). DB has them on 30/47 (17 qualitative-only items are correctly null). Audit queried wrong names. | `count(gu.low)` → 30/47 (correct) | **Audit error** — close |
| 58 | `basis_raw` null | Writer is correctly wired (`_build_params` line 259, Cypher SET line 163). Agent extraction JSON doesn't populate this field. Extraction-side gap, not writer bug. | Writer code ✅; DB `count(gu.basis_raw)` → 0 because agent doesn't set it | **Extraction gap** — separate issue |

---

## What We're Fixing (Issues #53 and #55 only)

**Problem**: You can't efficiently query GuidanceUpdate nodes by metric name or segment without parsing the composite ID string or doing a JOIN through the `UPDATES` edge to the Guidance parent.

**Examples of queries that DON'T work today:**
```cypher
-- These fail (properties don't exist on GU):
MATCH (gu:GuidanceUpdate) WHERE gu.label_slug = 'revenue' RETURN gu
MATCH (gu:GuidanceUpdate) WHERE gu.segment_slug = 'iphone' RETURN gu

-- Current workarounds (fragile or expensive):
MATCH (gu:GuidanceUpdate) WHERE gu.id CONTAINS ':revenue:' RETURN gu  -- false positives possible
MATCH (gu)-[:UPDATES]->(g:Guidance {id: 'guidance:revenue'}) RETURN gu  -- requires JOIN
```

**Fix**: Denormalize 3 properties onto GuidanceUpdate:

| Property | Type | Source | Example | Enables |
|---|---|---|---|---|
| `label` | String | Verbatim from extraction `label` field | `"Revenue"` | `WHERE gu.label = 'Revenue'`, display without JOIN |
| `label_slug` | String | `slug(label)` | `"revenue"` | `WHERE gu.label_slug = 'revenue'`, indexable |
| `segment_slug` | String | `slug(segment)` | `"iphone"` | `WHERE gu.segment_slug = 'iphone'`, indexable |

**What we're NOT adding** (and why):

| Field | Why not |
|---|---|
| `u_id` | Redundant with `id`. Only GuidancePeriod uses the `u_id` convention (inherited from XBRL Period/Unit nodes). GuidanceUpdate's `id` IS the MERGE key. |
| `direction` | Undefined in spec. Would require new enum design, extraction prompt changes, validation logic. This is new feature work, not a missing wire. |
| `segment_raw` | Redundant with existing `segment` property (which already stores the human-readable value). |

---

## Changes (4 files, 7 edits)

### File 1: `guidance_writer.py` — 2 edits

**Edit 1A: Add 3 properties to `_build_core_query()` SET block**

Current (line 172):
```
      gu.unit_raw = $unit_raw
```

New:
```
      gu.unit_raw = $unit_raw,
      gu.label = $label,
      gu.label_slug = $label_slug,
      gu.segment_slug = $segment_slug
```

Note: `$label` param already exists (used for `g.label` on Guidance parent at line 135). Reusing it — same value, denormalized onto GU.

**Edit 1B: Add 2 entries to `_build_params()`**

Add after line 254 (`'segment': item.get('segment', 'Total'),`):
```python
        'label_slug': item.get('label_slug') or slug(item.get('label', '')),
        'segment_slug': item.get('segment_slug') or slug(item.get('segment', 'Total')),
```

The `or slug(...)` fallback is critical — handles the edge case where `_ensure_ids()` returns early (line 117: `if item.get('guidance_update_id'): return item`) and `build_guidance_ids()` was never called by the CLI, so `label_slug`/`segment_slug` aren't in the item dict. Same defensive pattern already used at line 77: `label_slug = item.get('label_slug') or slug(item.get('label', ''))`.

### File 2: `test_guidance_writer.py` — 3 edits

**Edit 2A: Update `test_query_contains_all_gu_properties` (line 696)**

Add to `expected_props` list:
```python
        'gu.label', 'gu.label_slug', 'gu.segment_slug',
```

**Edit 2B: Add test for defensive slug computation**

```python
def test_params_label_and_segment_slugs():
    """label_slug and segment_slug are denormalized into params for GuidanceUpdate."""
    item = _make_item()
    params = _build_params(item, 'src1', 'transcript', 'AAPL')
    assert params['label_slug'] == 'revenue'
    assert params['segment_slug'] == 'total'

def test_params_slug_fallback_when_missing():
    """Slugs computed from raw fields when pre-computed slugs are absent."""
    item = _make_item()
    del item['label_slug']
    del item['segment_slug']
    params = _build_params(item, 'src1', 'transcript', 'AAPL')
    assert params['label_slug'] == 'revenue'   # computed from label='Revenue'
    assert params['segment_slug'] == 'total'    # computed from segment='Total'

def test_params_slug_segment_variant():
    """segment_slug correctly slugifies non-trivial segment names."""
    item = _make_item(segment='Wearables, Home and Accessories', segment_slug='wearables_home_and_accessories')
    params = _build_params(item, 'src1', 'transcript', 'AAPL')
    assert params['segment_slug'] == 'wearables_home_and_accessories'
```

**Edit 2C: Update `test_params_complete_roundtrip` verification**

No change needed — this test already validates all `$param` references in the query exist in the params dict. When we add `$label_slug` and `$segment_slug` to the query (Edit 1A), this test automatically catches if they're missing from params. Existing test coverage is sufficient.

### File 3: `SKILL.md` — 1 edit (spec update)

**Edit 3A: Add to §1 GuidanceUpdate Node Properties table (after line 99)**

```
| `label` | String | Metric name (denormalized from Guidance parent) |
| `label_slug` | String | `slug(label)` — for direct queries without JOIN |
| `segment_slug` | String | `slug(segment)` — for direct queries by segment |
```

### File 4: `guidance-extraction-issues.md` — 1 edit (tracker update)

Reclassify all 7 issues:

| # | Old Status | New Status | New Notes |
|---|---|---|---|
| 52 | Open (Medium) | **Closed (not-a-bug)** | Spec defines `u_id` on GuidancePeriod only, not GuidanceUpdate. `id` serves the same role. |
| 53 | Open (HIGH) | **Fixed** | Added `label` + `label_slug` as denormalized properties on GuidanceUpdate. |
| 54 | Open (Medium) | **Closed (not-a-bug)** | `direction` not defined anywhere in spec. New feature would require separate design. |
| 55 | Open (Medium) | **Fixed** | Added `segment_slug` as denormalized property. `segment` (raw) already stored 47/47. |
| 56 | Open (Medium) | **Closed (audit error)** | Correct name is `evhash16` per spec §1/§3. Populated 47/47. Audit queried wrong name `evhash`. |
| 57 | Open (HIGH) | **Closed (audit error)** | Correct names are `low/mid/high` per spec §2 fields 7-9. Populated 30/47 (17 qualitative-only = correctly null). Audit queried wrong names `value_low/value_high/value_point`. |
| 58 | Open (Low) | **Open (reclassified)** | Writer correctly wired. Agent doesn't populate `basis_raw`. Reclassify as extraction prompt issue, not writer bug. |

---

## What We're NOT Changing

- **`guidance_ids.py`** — `build_guidance_ids()` already returns `label_slug` and `segment_slug`. No changes.
- **`guidance_write_cli.py`** — `_ensure_ids()` already merges slugs via `item.update(ids)`. No changes.
- **`guidance_write.sh`** — Shell wrapper, no changes.
- **Agent prompts** — JSON payload format stays the same. New properties are computed by the writer from existing fields.
- **No backfill query needed** — next re-extraction via MERGE+SET will populate the new properties on existing nodes. All 47 AAPL nodes get the slugs on next Run 8.

---

## Verification

1. Run existing test suite: `python3 test_guidance_writer.py` — must pass (151 → 154+ tests)
2. Run existing ID tests: `python3 test_guidance_ids.py` — must pass (78 tests, unchanged)
3. Dry-run one transcript to verify new properties appear in CLI output:
   ```bash
   bash .claude/skills/earnings-orchestrator/scripts/guidance_write.sh /tmp/gu_AAPL_test.json --dry-run
   ```
4. After next write-mode run: verify in Neo4j:
   ```cypher
   MATCH (gu:GuidanceUpdate)
   WHERE gu.label_slug IS NOT NULL
   RETURN count(gu)
   -- Expected: 47 (all nodes)

   MATCH (gu:GuidanceUpdate)
   WHERE gu.label_slug = 'revenue' AND gu.segment_slug = 'iphone'
   RETURN gu.id
   -- Expected: returns iPhone Revenue items
   ```
