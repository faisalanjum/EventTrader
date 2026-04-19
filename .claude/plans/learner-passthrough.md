# 🔧 Learner → Predictor Feed Change Playbook

**Purpose.** Authoritative reference for modifying what the learner's output passes to the predictor. Consult whenever a task description contains any of: "feed more/less of learner output to predictor", "add/remove a field visible to the predictor", "change what predictor sees from prior lessons", "change ticker.json / global.json render", "change learning_context shape", "change lesson labeling scope or order", "change per-scope caps", "change PIT filter in read path".

**When NOT to consult.** Pure learner-internal changes (e.g., retouching the learner's SKILL.md §Five-Phase workflow without changing its output fields), pure predictor-internal changes (e.g., tweaking Phase 2 "Reasoning" prose), pure plumbing changes (logging, hooks, env vars).

---

## 1. Data-flow map (ground truth — line numbers verified)

```
LEARNER SDK writes learning/result.json    (attribution_result.v2)
       │
       ├─ finalize_learning_result          earnings_orchestrator.py:3009
       │    └─ stamps model_version, sdk_session_id on the learner output
       │
       ├─ append_ticker_lesson              earnings_orchestrator.py:2214
       │    └─ entry dict at L2237-2255     → learnings/ticker/{TICKER}.json
       │    └─ upsert key = quarter_label       (L2260-2262)
       │
       └─ append_global_lessons             earnings_orchestrator.py:2268
            └─ enriched dict at L2311-2327  → learnings/global.json
            └─ upsert key = (source_ticker, quarter_label)  (L2348-2352)
            └─ flock-protected atomic write
                                                      │
                                                      ▼
                   build_learning_context             earnings_orchestrator.py:2365
                        ├─ ticker_lessons[]  (cap 8, dedupe by quarter_label)
                        ├─ global_lessons[]  (sector≤4 + macro≤4 + cross≤2, order matters)
                        ├─ ticker_ref        (path to ticker.json if present, else None)
                        ├─ global_ref        (path to global.json if present, else None)
                        ├─ PIT filter via _passes_pit  (L2420, fires BEFORE scope routing for globals)
                        ├─ scope routing   (L2491-2531, 6 exclusion counters)
                        └─ observability log  (L2562-2579, 8 counters)
                                                      │
                                                      ▼
                   attached to bundle["learning_context"]   build_prediction_bundle (~L190)
                                                      │
                                ┌─────────────────────┴─────────────────────┐
                                ▼                                           ▼
                    _render_learning_context                    bundle["learning_context"] embedded
                    earnings_orchestrator.py:2603               in context_bundle.json (this is what
                    returns (text, ordered_lesson_texts)        the PREDICTOR reads at BUNDLE_PATH)
                    ├─ walk: ticker_lessons[i].predictor_lessons[j]
                    ├─ then: globals by scope sector→macro→cross_ticker
                    ├─ ordered.append() at 4 sites: L2641, L2666, L2675, L2685
                    │
                    ▼
                    render_bundle_text                earnings_orchestrator.py:1468-1506
                        └─ splices text into context_bundle_rendered.txt (Section 10)
                                                      │
                                                      ▼
                    PREDICTOR SDK reads JSON at BUNDLE_PATH
                        └─ SKILL.md Phase 0 walk  (.claude/skills/earnings-prediction/SKILL.md:30-67)
                        └─ LLM emits lesson_labels[] in walk order
                                                      │
                                                      ▼
                    finalize_prediction_result        earnings_orchestrator.py:3066
                        └─ Python stamps buckets + predicted_at + prompt_version + sdk_session_id
                        └─ triggers best-effort result.md (result_md_renderer.py) + thinking.md
                           (thinking_harvester.py) sidecars — these are what Obsidian captures
                                                      │
                                                      ▼
                    6 validate call sites derive expected_lesson_texts
                      = _render_learning_context((bundle or {}).get("learning_context") or {})[1]
                    (orchestrator:3417, run_ab_baseline:137, run_burl_ab_sequential:120,
                     run_calibration_sequential:78, run_nvda_ab_sequential:115,
                     run_q3_from_existing_bundle:86)
                                                      │
                                                      ▼
                    validate_prediction_result        earnings_orchestrator.py:1575
                                                      (NOT a separate module)
                        ├─ shape/enum/sentinel discipline  (L1671-1696)
                        ├─ positional equality vs expected_lesson_texts  (L1698-1710)
                        ├─ cites_lesson_indices → confirmed-only          (L1712-1739)
                        └─ analysis substring floor (≥30 chars)            (L1741-1757)
```

---

## 2. The four-surface alignment invariant (MUST hold after every change)

These four must always agree:

| # | Surface | Location |
|---|---|---|
| 1 | **Renderer traversal order + labeled set** | `_render_learning_context` — which `ordered.append(...)` sites fire and in what order |
| 2 | **Predictor walk instructions** | `.claude/skills/earnings-prediction/SKILL.md` Phase 0 L36-47 ("What to label" / "What NOT to label" / "Emission order") |
| 3 | **LLM emission** | the model's actual `lesson_labels[]` array in `prediction/result.json` |
| 4 | **Validator expectation** | `validate_prediction_result` positional check at L1699-1710, which reads `_render_learning_context(...)[1]` |

Surface #4 is automatically derived from #1 when the 6 call sites call `_render_learning_context`. Surface #3 is a runtime behaviour of the LLM that must match #2, which must match #1. Any edit to one requires verifying all four still agree.

---

## 3. Change-scenario matrix

**The default path** for "change what the learner feeds into the predictor" is scenarios 1–6. Scenarios 7–9 are conditional — only triggered if the nature of the change affects learner output schema, predictor output schema, or routing types. Scenario 10 covers the Obsidian capture surface.

---

### Scenario 1 — Add/remove a RENDERED-ONLY field (visible to predictor but NOT labeled)

Example: surface `predicted_confidence_score` in the ticker-lesson header; show `primary_driver_summary` without labeling it.

| File | Edit |
|---|---|
| `scripts/earnings/earnings_orchestrator.py::append_ticker_lesson` L2237-2255 | Stamp the new field into the entry dict if not already stored (skip if already in ticker.json) |
| `scripts/earnings/earnings_orchestrator.py::_render_learning_context` L2630-2647 | Emit the new text in the header fstring or as an extra bullet — **do NOT call `ordered.append()`** |
| `.claude/skills/earnings-prediction/SKILL.md` Phase 0 "What NOT to label" block (L42-45) | Add the new field name so the LLM does not mistakenly add it to `lesson_labels[]` |
| `scripts/earnings/test_render_learning_context.py` R2/R4 | Update rendered-substring assertions; **`ordered` list length must remain unchanged** (critical regression guard) |
| `scripts/earnings/test_learning_context.py` W-tests | Update writer fixture if the entry shape changed |
| `.claude/plans/learner.md` §7 "What goes into each entry" | Doc sync |

**NOT touched**: `validate_prediction_result`, 6 validate call sites, `validate_learning.py`, `.claude/hooks/validate_learning_output.py`, `finalize_*_result`.

---

### Scenario 2 — Add/remove a LABELED field (predictor must label it)

Example: make `contributing_factors[].summary` labelable; add a `retrospective_miss` lesson type that must be labeled.

| File | Edit |
|---|---|
| `scripts/earnings/earnings_orchestrator.py::append_ticker_lesson` or `append_global_lessons` | Stamp the new field into the entry dict |
| `scripts/earnings/earnings_orchestrator.py::_render_learning_context` | Emit the text AND call `ordered.append(text)` at the correct position in the traversal |
| `.claude/skills/earnings-prediction/SKILL.md` Phase 0 "What to label" block (L37-41) | Add the new field; explicitly state its position in the walk order |
| `scripts/earnings/test_render_learning_context.py` | New R-test for the new `ordered` position + length |
| `scripts/earnings/test_validate_prediction_result.py` | New V-test for the new position in `lesson_labels[]` |
| `scripts/earnings/test_learning_context.py` W-tests | Updated entry-shape fixtures |
| `.claude/plans/learner.md` Appendix B §4.4 "What gets labeled — scope" | Doc sync — the scope table must reflect the new field |

**NOT touched**: `validate_prediction_result` code itself (positional check is generic — auto-picks up new length/content via `_render_learning_context(...)[1]`). **6 validate call sites unchanged**.

---

### Scenario 3 — Change the ORDER of labeled lessons

Example: move `macro` globals before `sector`; interleave ticker and global lessons.

| File | Edit |
|---|---|
| `scripts/earnings/earnings_orchestrator.py::_render_learning_context` | Reorder the `ordered.append()` call sites and the render blocks to match |
| `scripts/earnings/earnings_orchestrator.py::build_learning_context` L2548-2552 | If you want the JSON output of `global_lessons` to also be in the new order (so the predictor reading JSON sees the same order as the renderer), reorder the concat |
| `.claude/skills/earnings-prediction/SKILL.md` Phase 0 walk-order bullets | Update the sequence |
| `scripts/earnings/test_render_learning_context.py` R3 | Update expected `ordered` sequence |
| `scripts/earnings/test_validate_prediction_result.py` V-tests | Update positional fixtures |

**NOT touched**: 6 validate call sites, validator code, ticker.json/global.json schema.

---

### Scenario 4 — Change per-scope caps, dedupe, PIT filter, or exclusion counters

Example: raise sector cap from 4 to 6; add a recency filter to macros; change how PIT cutoff is compared.

| File | Edit |
|---|---|
| `scripts/earnings/earnings_orchestrator.py::build_learning_context` L2420-2579 | Filter / cap / counter logic |
| `scripts/earnings/earnings_orchestrator.py::build_learning_context` observability log L2562-2579 | Keep the log shape stable unless adding a new counter (new counter = new key in log fstring) |
| `scripts/earnings/test_learning_context.py` R-tests (R11-R15, R17*) | Counter & cap assertions |
| `.claude/plans/learner.md` Appendix A §4.3-§4.5 | Spec sync — filter logic, caps, observability contract |

**NOT touched**: renderer, SKILL.md (walk order unchanged), validator, 6 call sites.

---

### Scenario 5 — Add/remove a STORED-ONLY field in ticker.json or global.json (not rendered)

Example: stamp `peer_quarter_count` for later audit; store `lesson_generation_latency_s` without showing the predictor.

| File | Edit |
|---|---|
| `scripts/earnings/earnings_orchestrator.py::append_ticker_lesson` L2237-2255 OR `append_global_lessons` L2311-2327 | Add the field to the entry dict |
| `scripts/earnings/test_learning_context.py` W-tests | Writer-side stamp assertion |
| `.claude/plans/learner.md` §7 or §8 / Appendix A §4.2 | Schema doc sync |

**NOT touched**: renderer, SKILL.md, validator (the field is derived storage metadata, not learner-output contract), call sites, A/B scripts.

---

### Scenario 6 — Add/remove a TOP-LEVEL KEY in `build_learning_context` return dict

Example: return `{ticker_lessons, global_lessons, ticker_ref, global_ref, peer_lessons}`; remove `global_lessons` in favor of separate `sector_lessons` and `macro_lessons` top-level keys.

| File | Edit |
|---|---|
| `scripts/earnings/earnings_orchestrator.py::build_learning_context` | Compute and return the new key |
| `scripts/earnings/earnings_orchestrator.py::_render_learning_context` | Consume the new key (new render block + possibly new `ordered.append()` sites) |
| `.claude/skills/earnings-prediction/SKILL.md` Phase 0 "Source of truth" block (L32-34) | Update the JSON-shape description; add labeling rules for the new section |
| **A/B stripper scripts** — `scripts/run_ab_baseline.py` (L42-47), `scripts/run_nvda_ab_sequential.py` (L59-64), `scripts/run_burl_ab_sequential.py` (L63-68) | Add the new top-level key to the blanked stub inside `strip_learning_context()`. Current stub blanks **four keys** (`ticker_lessons`, `global_lessons`, `ticker_ref`, `global_ref`); any new top-level key from `build_learning_context` must be added here. Failing to do so silently leaks the new section into the WITHOUT-lessons A/B baseline. |
| `scripts/earnings/test_learning_context.py` | New reader-tests for the new key shape |
| `scripts/earnings/test_render_learning_context.py` | New R-tests for the new render block |
| `scripts/earnings/test_validate_prediction_result.py` | If labelable, new V-tests |
| `.claude/plans/learner.md` §9 "Output shape" | Doc sync — the contract for `build_learning_context` output |

**Important**: this is the only default-path scenario where A/B scripts need edits. Scenarios 1-5 leave the A/B blanking logic untouched because those changes occur inside existing `ticker_lessons[]` / `global_lessons[]` lists that are already blanked to `[]`.

**NOT touched**: `validate_prediction_result` code (positional check auto-syncs via `_render_learning_context[1]`). 6 call sites unchanged unless the call-site access pattern `(bundle or {}).get("learning_context") or {}` must change.

---

### Scenario 7 — Change schema of `attribution_result.v2` (CONDITIONAL — learner output only)

Triggered when: the learner must emit a new top-level field, rename an existing one, or change field semantics. This is NOT triggered by ordinary "feed more/less into predictor" tasks; cascades into scenarios 5 and/or 1-2 if the new field should flow through to the predictor.

| File | Edit |
|---|---|
| `.claude/skills/earnings-learner/SKILL.md` "Required top-level fields" L44-61 + "Feedback block" table L62-72 | Field definition |
| `scripts/earnings/validate_learning.py` | Validation rules (required-keys list + shape/enum/ref-resolution checks) |
| `scripts/earnings/test_validate_attribution.py` | New V-test cases |
| `.claude/hooks/validate_learning_output.py` | **NO CHANGE** — delegates to `validate_learning.validate_attribution_result` |
| `scripts/earnings/earnings_orchestrator.py::finalize_learning_result` L3009 | ONLY if the new field is Python-stamped (e.g., `sdk_session_id` pattern); skip for LLM-authored fields |
| `.claude/plans/learner.md` §6 "Full schema" + §6 "Field reference" table | Doc sync |
| Cascade to Scenario 5 | If the new field should be stored in ticker.json/global.json |
| Cascade to Scenarios 1 or 2 | If the new field should be visible to the predictor (rendered and/or labeled) |
| Cascade to Scenario 10 | If the new field should appear in the Obsidian-captured `result.md` |

---

### Scenario 8 — Change schema of `prediction_result.v1` (CONDITIONAL — predictor output only)

Triggered when: the predictor must emit a new top-level field, rename an existing one, or change field semantics. NOT a typical learner→predictor feed change.

| File | Edit |
|---|---|
| `.claude/skills/earnings-prediction/SKILL.md` "Output" JSON example L100-127 + "Field definitions" L129-149 | Schema shape |
| `scripts/earnings/earnings_orchestrator.py::validate_prediction_result` L1595-1757 | Required-keys list at L1595-1612 + new validation block (decide placement relative to T1 blocks) |
| `scripts/earnings/earnings_orchestrator.py::finalize_prediction_result` L3066-3134 | ONLY if the new field is Python-derived/stamped (buckets, predicted_at pattern); skip for LLM-authored |
| `scripts/earnings/test_validate_prediction_result.py` | New V-test cases |
| `scripts/earnings/result_md_renderer.py` | If the new field should appear in the `result.md` sidecar (see Scenario 10) |
| `scripts/earnings/thinking_harvester.py` | Reads via `.get()` + try/except — additive fields transparent; no edit required |
| 6 validate call sites | **NO CHANGE** unless a new REQUIRED kwarg is added to `validate_prediction_result`'s signature |

---

### Scenario 9 — Change scope types or routing fields (CONDITIONAL — routing taxonomy only)

Triggered when: adding a new global-lesson `scope` value (e.g., `industry`); renaming `target_sector` or `related_tickers`; changing the canonical sector enum.

| File | Edit |
|---|---|
| `config/canonical_sectors.py` | If adding/removing sector values in the 11-value enum |
| `scripts/earnings/validate_learning.py` | Scope enum + per-scope required/rejected fields |
| `scripts/earnings/earnings_orchestrator.py::append_global_lessons` L2311-2327 | Conditional-field-insertion pattern (routing fields only present on owning scope) |
| `scripts/earnings/earnings_orchestrator.py::build_learning_context` L2491-2531 | New routing branch + new exclusion counter |
| `scripts/earnings/earnings_orchestrator.py::_render_learning_context` L2658-2686 | New sub-section + `ordered.append()` at the correct traversal position |
| `.claude/skills/earnings-learner/SKILL.md` "Global observations" section L84-141 | Scope table + canonical enum list |
| `.claude/skills/earnings-prediction/SKILL.md` Phase 0 | Walk-order instruction (new scope must appear in the global-lessons walk list) |
| `scripts/earnings/test_canonical_sectors_consistency.py` | CS1 (Neo4j ↔ module) / CS2 (SKILL.md ↔ module) if enum changed |
| `scripts/earnings/test_validate_attribution.py` | V1-V20 for new routing-field rules |
| `scripts/earnings/test_learning_context.py` R3-R10 | Scope-routing tests |
| `.claude/plans/learner.md` Appendix A §3, §4.1-§4.3, §6.7 | Doc sync |

---

### Scenario 10 — Obsidian capture surface (CONDITIONAL — only when sidecar MD content must change)

Triggered when: a new field in `learning/result.json` or `prediction/result.json` should appear in the captured vault MD; the `thinking_type`, artifact directory layout, or per-quarter sidecar filenames change.

**Shape-agnostic by default.** `.claude/hooks/obsidian_capture.py` watches for writes of `result.md` and `thinking.md` under the per-quarter artifact directories (`learning/`, `prediction/`, `experiments/prediction_no_lessons/`) and copies them into the vault. The hook does NOT parse or validate content — it copies whatever file exists. This means:

- Scenarios 1-6 (default feed changes): **NO obsidian work required.** The hook captures whatever `result.md` + `thinking.md` are produced.
- Scenarios 7-8 (schema changes): **`result_md_renderer.py` edits are needed IF the new field should be visible in the vault.** Otherwise obsidian faithfully captures a sidecar that simply doesn't mention the new field — technically fine, but it won't show up in the vault.

| File | Edit |
|---|---|
| `scripts/earnings/result_md_renderer.py` | Add the new field to the appropriate section — prediction render at L124-200, learning render at L228-385. Pattern: `payload.get(new_field)` + append to `lines[]` |
| `scripts/earnings/test_result_md_renderer.py` | New R-test for the new section/line |
| `scripts/earnings/obsidian_capture_adapter.py` | Edit ONLY if the vault filename/frontmatter contract changes (e.g., new required frontmatter key); not needed for additive content |
| `.claude/hooks/obsidian_capture.py` | Edit ONLY if the artifact directory layout changes (e.g., new per-quarter sidecar type) or the path-matching pattern must expand |
| `scripts/earnings/thinking_harvester.py` | Edit ONLY if capturing a new `thinking_type` (currently `prediction`, `learning`, `guidance`) |
| `.claude/plans/obsidian_thinking.md` | Doc sync if artifact layout or capture rules change |

**NOT touched by Scenario 10 alone**: learner/predictor SKILL.md, validators, renderer of the context_bundle, `build_learning_context`.

---

## 4. When the 6 validate call sites DO need edits

These sites auto-derive `expected_lesson_texts` from `_render_learning_context(...)[1]`. They only need edits when:

1. `_render_learning_context` **signature or return shape changes** — e.g., tuple → 3-tuple, or dict return instead of tuple. All 6 sites unpack `_, _expected_lessons = ...`; a shape change breaks all.
2. The **kwarg name** `expected_lesson_texts` is renamed.
3. A site **stops delegating** to `_render_learning_context` — e.g., hand-computing the expected list.
4. The **bundle access pattern** `(bundle or {}).get("learning_context") or {}` changes — e.g., if the bundle becomes a nested structure.
5. A **new REQUIRED kwarg** is added to `validate_prediction_result`'s signature (currently only `expected_lesson_texts` is optional with `None` default).

Ordinary changes — adding/removing `ordered.append()` sites, reordering labels, changing caps, changing which text is labeled — require NO edits at the 6 sites.

---

## 5. Critical invariants (do not violate)

| # | Invariant | Guard |
|---|---|---|
| I1 | Four-surface alignment: renderer walk, SKILL.md Phase 0, LLM emission, validator positional check must agree on `ordered` set and order | Run smoke test §6; manual re-read of SKILL.md Phase 0 vs `_render_learning_context` diff |
| I2 | `_render_learning_context` is single source of truth for lesson order | Never maintain a parallel list of "labeled lessons" elsewhere; always call the function |
| I3 | Schema version strings frozen: `"attribution_result.v2"`, `"prediction_result.v1"`, `"ticker_lessons.v1"`, `"global_lessons.v1"` | Bump only when structurally breaking; additive fields do NOT require bump |
| I4 | Upsert keys: `ticker.json` = `quarter_label`; `global.json` = `(source_ticker, quarter_label)` | Changing key composition requires editing L2260-2262 and L2348-2352 simultaneously; new key-participant fields must be `src_ticker.upper().strip()`-normalized like L2295 |
| I5 | PreToolUse hook delegates via `from validate_learning import validate_attribution_result` | Do NOT duplicate schema logic in the hook; do NOT rename the function (schema name `attribution_result.v2` is preserved even though the folder is `learning/`) |
| I6 | Legacy-entry read resilience: any additive field on an upsert-persisted file must use `.get(field, default)` at read time, OR require a corpus wipe per §8.3 pattern | Test R6 (legacy `target_sector` missing), R10 (legacy `related_tickers` missing), R17_legacy (missing `source_pit_cutoff`) are the model |
| I7 | PIT filter fires BEFORE scope routing for globals (L2492-2496) | Ensures `global_post_cutoff` counter is disjoint from scope exclusion counters; any new filter must preserve disjoint counter semantics |
| I8 | Predictor reads JSON at `BUNDLE_PATH`, not the rendered text, for Phase 0 labeling | SKILL.md Phase 0 `bundle.learning_context` walk = `build_learning_context` return dict shape. The render is context-enrichment ONLY; never route structural contract through rendered text. |
| I9 | A/B scripts strip `learning_context` to **four blanked keys** — `{"ticker_lessons": [], "global_lessons": [], "ticker_ref": None, "global_ref": None}`. Any new top-level key added by `build_learning_context` must be added to this stub in `run_ab_baseline.py::strip_learning_context` (L42-47), `run_nvda_ab_sequential.py::strip_learning_context` (L59-64), and `run_burl_ab_sequential.py::strip_learning_context` (L63-68) | Otherwise the WITHOUT-lessons baseline silently leaks the new section — A/B delta is no longer a true A/B |
| I10 | `validate_prediction_result` is inline in `earnings_orchestrator.py:1575`, NOT a separate module | Imports always `from earnings_orchestrator import validate_prediction_result`; do NOT create a wrapper module |
| I11 | Obsidian capture is shape-agnostic for file COPY but not for field VISIBILITY. New fields added to learner/predictor output appear in the vault only if `result_md_renderer.py` is taught to render them (Scenario 10) | The hook does not parse JSON; it copies whatever MD exists. Silent "capture succeeds but field missing from vault" is the failure mode — not a crash |

---

## 6. Verification checklist (run before commit)

```bash
# I1 + I2 + Scenario-2/3 alignment: label emission sites in renderer match SKILL.md
grep -n "ordered.append" scripts/earnings/earnings_orchestrator.py
# Expected: 4 sites (ticker-predictor_lessons loop + sector + macro + cross_ticker).
# If a Scenario 2 change added a labelable field, this count must increase by exactly 1 per field.
# Pair-check: .claude/skills/earnings-prediction/SKILL.md Phase 0 bullets in "What to label"
# must match the set of ordered.append() sources.

# §4: 6 validate sites still wired (kwarg invocation, not def default)
grep -rn "expected_lesson_texts=_expected_lessons" scripts/ \
    --include="*.py" --exclude-dir=__pycache__ --exclude="test_*.py" | wc -l
# Expected: 6.  If you intentionally refactored the renderer signature,
# update all 6 together in the same commit.

# I3: schema version strings unchanged (unless explicit bump)
grep -n 'attribution_result\.v2\|prediction_result\.v1\|ticker_lessons\.v1\|global_lessons\.v1' \
    scripts/earnings/earnings_orchestrator.py scripts/earnings/validate_learning.py

# I5: hook still delegates
grep -n "from validate_learning import validate_attribution_result" \
    .claude/hooks/validate_learning_output.py
# Expected: 1 match (L76).

# I9: A/B stripper still blanks all four top-level keys of learning_context
grep -n 'ticker_lessons\|global_lessons\|ticker_ref\|global_ref' \
    scripts/run_ab_baseline.py scripts/run_nvda_ab_sequential.py \
    scripts/run_burl_ab_sequential.py | grep -v '#'
# Expected: at least one match per file inside each strip_learning_context().
# If you added a top-level key, that key must also appear here.

# Tests green
venv/bin/python -m pytest scripts/earnings/test_render_learning_context.py \
    scripts/earnings/test_validate_prediction_result.py \
    scripts/earnings/test_validate_attribution.py \
    scripts/earnings/test_learning_context.py \
    scripts/earnings/test_canonical_sectors_consistency.py \
    scripts/earnings/test_orchestrator_pit_mode.py \
    scripts/earnings/test_learner_outcomes.py \
    scripts/earnings/test_result_md_renderer.py

# Smoke: one historical quarter WITH prior lessons (exercises all four surfaces)
python3 scripts/earnings/earnings_orchestrator.py AVGO <accession_with_prior_lessons> \
    --save --predict --learn
# Inspect prediction/result.json:
#   jq '.lesson_labels | length' -> must equal ordered.append() site count × active labels
#   jq '[.key_drivers[] | has("cites_lesson_indices")] | all' -> true
#   jq '[.lesson_labels[].label | in({"confirmed":1,"contradicted":1,"irrelevant":1})] | all' -> true
# If Scenario 10 edits shipped, inspect:
#   ls earnings-analysis/Companies/AVGO/events/<Q>/prediction/result.md -> exists
#   grep '<new-field-header>' earnings-analysis/Companies/AVGO/events/<Q>/prediction/result.md
```

---

## 7. Common pitfalls (documented failure modes)

| # | Pitfall | Symptom |
|---|---|---|
| P1 | Scenario 2 edit forgets SKILL.md Phase 0 "What to label" update | LLM emits wrong-length `lesson_labels[]` → positional-check length mismatch → 1 retry (informed via H2) → failure if retry still wrong |
| P2 | Scenario 3 reorder forgets SKILL.md walk-order update | LLM emits correct count but wrong positions → positional-comparison mismatch error |
| P3 | Scenario 1 renders a field without adding to SKILL.md "What NOT to label" | LLM labels it anyway → `lesson_labels[]` longer than expected → length mismatch |
| P4 | Scenario 6 forgets A/B stripper update (I9) | A/B WITHOUT-lessons baseline silently leaks the new top-level key → A/B delta is not a real A/B |
| P5 | Scenario 7 adds required schema field without corpus migration | `validate_attribution_result` rejects all legacy files; derived-write recovery deletes them; ticker chain stops at every quarter |
| P6 | Ticker-case drift in upsert keys (I4) | Duplicate entries accumulate in `global.json` between runs that differ in casing. Fix: all new key-participant fields normalized via `str(x or "").upper().strip()` |
| P7 | Evidence-ledger refs introduced without ref-resolution check | Validator silently accepts references to non-existent ledger IDs; learner output appears valid but is forensically broken |
| P8 | Assuming `validate_prediction_result` is a separate module (I10) | Import errors; new call sites failing to find the function |
| P9 | Changing `_render_learning_context` return tuple-shape | All 6 validate call sites break on unpacking; signature-level change requires §4 edit |
| P10 | Editing `_render_learning_context` without updating `render_bundle_text` section placement | If Scenario 1's new bullet causes Section 10 to exceed prompt budget, truncation behaviour changes silently; currently `render_bundle_text` L1468-1506 concatenates unconditionally |
| P11 | Storing a PIT-sensitive new field without stamping `source_pit_cutoff` equivalent | Read-side PIT filter in `build_learning_context` L2420 excludes new entries in historical mode. Fix: copy the T1.5b pattern at L2242-2243 / L2319-2320 |
| P12 | Scenario 7/8 schema change without `result_md_renderer.py` update (I11) | Obsidian capture succeeds, but the new field is missing from the vault MD — silent gap, not a crash |

---

## 8. Doc-sync obligation

Any code change above MUST have a paired edit in `.claude/plans/learner.md` (the parent plan body or the relevant appendix) unless the change is explicitly scoped to internal plumbing (e.g., logging, env vars, comments). Schema- or contract-affecting changes that land without doc-sync will drift silently and cause future bots to reason against stale contracts. Scenario 10 changes must additionally doc-sync to `.claude/plans/obsidian_thinking.md` when they alter artifact layout, filenames, or per-quarter capture rules.

---

**End of Playbook.** Revisit every assertion against the data-flow map in §1 before making an edit; if your intended change doesn't cleanly fit a scenario, prefer consulting `.claude/plans/learner.md` §8 (global_observations schema) and §9 (build_learning_context filtering) before inventing a new pattern.
