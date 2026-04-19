# Labeled Lesson Consumption — Template-Overfit Mitigation (T1)

**Created**: 2026-04-19 (rev 3)
**Status**: DESIGN — production-grade, zero-fat, ready for implementation
**Scope**: Predictor-side. Make `key_drivers[]` lesson citations **structurally enforced** by the validator; the `analysis` free-text field retains a narrow, explicitly acknowledged paraphrase residual (§2.2). Not prompt-governed for citations; honestly scoped for analysis.

**Revisions history**:
- Rev 1 (earlier 2026-04-19) — introduced `lesson_labels[]`; citation discipline was prompt-only → insufficient.
- Rev 2 (earlier 2026-04-19) — added `cites_lesson_indices[]` + two-layer validation; 4 residual gaps identified on audit.
- **Rev 3 (THIS FILE)** — drops hook (pure fat), restores bundle_evidence sentinel check (rev-1 regression), collapses extractor into renderer (zero drift surface), adds analysis-field substring floor, pre-enumerates all call sites, anchors to structured `bundle["learning_context"]` not prose render.

**Parent plan**: `.claude/plans/learner.md` §13 Phase 4. This file is the authoritative spec.

**Prerequisites** (from `learner.md`'s "🔴 Next up" backlog):
1. ✅ T1.5a + T1.5b (PIT correctness) — commits `1b79614`, `fe0326a`
2. ✅ T3 (`8k_packet.sector` at source) — commit `c73599d`
3. ⏳ **Task #356** — corpus wipe + 15-quarter rerun — REQUIRED before T1 A/B is meaningful
4. ⏳ T1 (this plan)
5. ⏳ T4 — A/B evaluation on post-T1 corpus
6. ⏳ Audit script (deferred from T1; ships after ≥10 T1 quarters exist)

**NO backward compatibility.** Corpus will be wiped before T1 ships. `lesson_labels` is strictly required on every new `prediction_result.v1`. The optional `expected_lesson_texts` kwarg exists only for offline audit reads where the bundle isn't available — explicitly an offline concession, not a runtime fallback.

---

## 0. TL;DR

**Bug**: The predictor treats past lessons as soft triggers and applies them on surface keyword matches without checking whether each lesson's mechanism is present in the current bundle. AVGO Q3_FY2023 and BURL Q1_FY2025 were mis-called specifically because of this over-application.

**Fix (rev 3 — key_drivers citation structurally enforced; analysis residual explicit)**:

1. The predictor emits a `lesson_labels[]` entry for every lesson in `bundle["learning_context"]`, labeling each `confirmed` / `contradicted` / `irrelevant` with a `bundle_evidence` citation from the current quarter.
2. Every `key_drivers[i]` entry carries `cites_lesson_indices: list[int]` into `lesson_labels[]`. The validator rejects any index that does not resolve to a `confirmed` label.
3. The Python validator enforces four structural guards:
   - shape + enum + non-empty-text + bundle_evidence sentinel discipline
   - positional equality between `lesson_labels[*].lesson_text` and an orchestrator-computed expected list (no empty-list escape, no fabrication, no misordering)
   - `cites_lesson_indices` → confirmed-only enforcement
   - `analysis` field substring floor (rejects verbatim quote of any non-confirmed `lesson_text`)
4. The expected list is produced by `_render_learning_context` which now returns `(rendered_text, ordered_lesson_texts)` as a tuple. **The renderer is the single source of truth for lesson order** — the validator compares against the exact list the renderer emitted, so drift between "what LLM saw" and "what validator expects" is structurally impossible.

**No PreToolUse hook.** Python post-return validator is authoritative and runs before any **business-logic consumer** reads the result. Sidecar artifacts (`result.md`, `thinking.md`) can be generated pre-validation as diagnostic capture — acceptable and explicitly scoped in §6.1; no business-logic consumer reads them. The learner has a hook only because it has a derived-write-recovery path; the predictor has none. Asymmetry is correct, not oversight.

**Delta** (per §7 file inventory, authoritative — all numbers reconciled including import lines at non-orchestrator sites): ~164 lines of code changes across 8 source files:

| File | Lines | Contents |
|---|---:|---|
| `earnings_orchestrator.py` | +75 | validator blocks (+60), renderer tuple refactor (+8), `_normalize_lesson_text` (+4), `render_bundle_text` unpacking (+1), Site A wiring (+2) |
| `earnings-prediction/SKILL.md` | +65 | Phase 0 (+45), Output JSON example (+10), field definitions (+10) |
| `run_ab_baseline.py` | +4 | Site B wiring (3) + import (1) |
| `run_burl_ab_sequential.py` | +4 | Site C wiring (3) + import (1) |
| `run_calibration_sequential.py` | +4 | Site D wiring (3) + import (1) |
| `run_nvda_ab_sequential.py` | +4 | Site E wiring (3) + import (1) |
| `run_q3_from_existing_bundle.py` | +4 | Site F wiring (3) + import (1) |
| `.claude/plans/learner.md` | +4 | plan-doc sync |
| **Total source** | **~164** | |
| Tests (`test_validate_prediction_result.py` V1–V24 +130, `test_render_learning_context.py` R1–R4 +35) | ~165 | |
| **Grand total** | **~329** | |

**All 6 validator call sites are uniformly wired** with the `expected_lesson_texts` kwarg — no active/paused split. A/B test RUNS remain paused per user directive (2026-04-19); the A/B scripts are dormant-but-fully-wired, ready to reactivate without further code change. Total touched: 10 files. Zero fat.

**Deferred to separate PR**: audit script (~130 lines). Threshold calibration requires real T1-quarter distribution.

---

## 1. The bug (with empirical evidence)

### 1.1 Confirmed cases

**AVGO Q3_FY2023** (`Companies/AVGO/events/Q3_FY2023/learning/result.json`):
- Prior lesson (Q1): *"When a company first quantifies AI revenue, treat as narrative re-rating → long bias."*
- Q3 reality: AI was quantified in Q1 AND Q2. Q3 is the *third* disclosure — lesson's "first-time" trigger is absent.
- Predictor output: `long(40)`. Lesson applied on keyword match.
- Actual: **−5.38% SHORT**. Real signal was non-AI segment weakness.

**BURL Q1_FY2025** (`Companies/BURL/events/Q1_FY2025/learning/result.json`):
- Prior lesson (Q4): *"Compressed-spring pattern — guide-below-consensus + cautious management + clean beat → reversal rally."*
- Q1 reality: margin pressure + execution risk. "Clean beat" prerequisite absent.
- Predictor: `long(52)`.
- Actual: **−4.54% SHORT**.

### 1.2 Impact at n=15 calibration quarters

| | Correct | Rate |
|---|---|---|
| WITH lessons | 9/15 | 60% |
| WITHOUT lessons | 10/15 | 67% |
| **Delta** | **−1** | near-breakeven, asymmetric over-commitment |

### 1.3 Why prompting alone cannot fix this

SKILL.md at time of bug-observation explicitly describes lessons as "soft priors, not hard rules." Overfit still happened. LLMs are unreliable at soft meta-rules in prose. The fix must bind behavior to validator-enforced structural constraints.

---

## 2. The fix (one sentence)

Every atomic lesson in `bundle["learning_context"]` gets a `{lesson_text, label, bundle_evidence}` entry in `prediction_result.v1::lesson_labels[]` (emitted in the order the renderer emits them), every `key_drivers[i]` names the lessons it cites via `cites_lesson_indices`, and the Python validator enforces: positional equality of lesson_texts, citation-confirmed-only, bundle_evidence sentinel discipline, and an analysis-field substring floor against verbatim quotes of non-confirmed lessons.

### 2.1 Mechanism trace — AVGO Q3 after T1 ships

1. **Orchestrator** calls `_render_learning_context(bundle["learning_context"])` which returns `(rendered_text, expected_lesson_texts)`. For AVGO Q3, `expected_lesson_texts = ["<Q1 AI lesson>", "<Q2 thin-beat lesson>", ...]` in traversal order.
2. **LLM** reads `bundle.learning_context` directly from the JSON file at `BUNDLE_PATH`. Walks `ticker_lessons[*].predictor_lessons[]` then scope-ordered `global_lessons[*].lesson`. For the Q1 AI lesson: *"does Q3 bundle show FIRST AI quantification?"* → No. Emits `{lesson_text: "<verbatim>", label: "irrelevant", bundle_evidence: "AI revenue was quantified in Q1 and Q2 earnings releases; Q3 is the third consecutive disclosure."}`.
3. **LLM** decides direction from bundle evidence alone. `key_drivers = [{"driver": "Non-AI segment deceleration", ..., "cites_lesson_indices": []}, ...]`. No citation to index 0.
4. **Validator** fires:
   - Shape/enum ✓
   - `bundle_evidence != "no relevant evidence"` for `irrelevant` → OK (sentinel only rejects that string on `confirmed`/`contradicted`)
   - `lesson_labels[0].lesson_text` matches `expected_lesson_texts[0]` post-normalization ✓
   - `cites_lesson_indices` all empty or reference `confirmed` labels ✓
   - `analysis` does not contain verbatim `lesson_text` of index 0 ✓
5. **Result**: valid SHORT call. The irrelevant AI lesson is structurally barred from appearing in `key_drivers[].cites_lesson_indices`. Verbatim quotes in `analysis` (for lesson_texts ≥30 chars) are also caught by the substring floor. The residual surfaces are: (a) *paraphrased* references in `analysis` free-text (§2.2); (b) verbatim quotes of lessons <30 chars (below substring floor threshold — see §3 invariant 6).

### 2.2 Residual risk — paraphrased leak in `analysis`

**What is NOT enforced**: the LLM paraphrasing an irrelevant lesson's content into `analysis` free-text without verbatim quoting. Example: if the Q1 AI lesson text is *"first-time AI quantification drives re-rating"*, the LLM could write `analysis: "The company's re-rating prospects hinge on how investors digest this AI disclosure..."` — not a substring match but semantically citing the lesson.

**Why not fixed structurally**: catching paraphrase requires semantic comparison, which would need a second LLM call per validation — reintroduces confirmation bias and cost.

**Structural floor**: the validator rejects any `analysis` text containing the verbatim normalized `lesson_text` of a non-confirmed label. Catches the laziest leak pattern; raises the bar against rubber-stamping.

**Explicit acceptance**: this is the only prompt-governed surface in rev 3. Acknowledged, not pretended away. Detection happens offline via future audit.

---

## 3. Design invariants (MUST hold in every future change)

1. **Structural, not prose.** Labels and citation-sets are machine-readable enums/lists. Never parsed from free text.
2. **Positional integrity by construction.** `lesson_labels[i].lesson_text` corresponds to `expected_lesson_texts[i]` — same order, content-equal after whitespace normalization. Both produced by the same `_render_learning_context` call — the renderer is the single source of truth.
3. **No escape via empty.** If `expected_lesson_texts` is non-empty, `lesson_labels` must match it exactly.
4. **Citation ⇒ confirmed.** Every `key_drivers[i].cites_lesson_indices[j]` must resolve to `label == "confirmed"`.
5. **Sentinel discipline.** `bundle_evidence = "no relevant evidence"` is valid ONLY for `label == "irrelevant"`. `confirmed` and `contradicted` require specific evidence — validator rejects the sentinel for them.
6. **Analysis-field substring floor.** `analysis` must not contain the verbatim normalized `lesson_text` of any non-confirmed label **whose normalized length is ≥ 30 characters**. Shorter lessons are skipped by the substring check to prevent innocent-collision false positives on common short phrases (e.g., *"margin pressure continued"*). Real learner lessons are 80–150 chars per §1 observations; 30-char threshold is conservative and documented in §8.4 implementation.
7. **Scope is directional.** `predictor_lessons[]` + `global_lessons[].lesson` labeled. `data_lessons[]` rendered but NOT labeled (fetch/weight heuristics, not directional templates).
8. **No backward compat at runtime.** `lesson_labels` is strictly required on every new prediction. `expected_lesson_texts=None` kwarg is for offline audit only.
9. **Structured-bundle anchoring.** The LLM reads `bundle["learning_context"]` from `BUNDLE_PATH` (JSON) for label emission. The render is context for directional reasoning, not the authority on lesson text.
10. **No PreToolUse hook.** Python validator is the single validation layer. Defensive hook can be added later if derived-write recovery is introduced.

---

## 4. Schema contract — exact shape

### 4.1 Additions to `prediction_result.v1` (additive; no version bump)

```json
{
  "schema_version": "prediction_result.v1",
  "ticker": "AVGO",
  "quarter_label": "Q3_FY2023",
  "direction": "short",
  "confidence_score": 58,
  "expected_move_range_pct": [3.0, 6.0],

  "lesson_labels": [
    {
      "lesson_text": "<verbatim from bundle.learning_context>",
      "label": "irrelevant",
      "bundle_evidence": "AI revenue was quantified in Q1 and Q2 earnings releases; Q3 is the third consecutive disclosure."
    }
  ],

  "key_drivers": [
    {
      "driver": "Non-AI segment deceleration",
      "direction": "short",
      "evidence": "Infrastructure segment QoQ −4.1% per EX-99.1",
      "cites_lesson_indices": []
    },
    {
      "driver": "Thin-beat + rally-into-print",
      "direction": "short",
      "evidence": "5-day pre-print +7.2%; revenue beat 0.4%",
      "cites_lesson_indices": [1]
    }
  ],

  "data_gaps": [],
  "evidence_ledger": [ /* existing shape */ ],
  "analysis": "<free text; must not contain verbatim lesson_text of any non-confirmed label>"
}
```

### 4.2 `lesson_labels[]` — field rules

| Field | Type | Rules |
|---|---|---|
| `lesson_text` | string | Verbatim copy of the lesson string from `bundle.learning_context`. Non-empty after `.strip()`. |
| `label` | string | **Strictly** one of `"confirmed"` / `"contradicted"` / `"irrelevant"`. Lowercase, no synonyms. |
| `bundle_evidence` | string | Non-empty after `.strip()`. For `irrelevant`: `"no relevant evidence"` is allowed (sentinel). For `confirmed`/`contradicted`: must NOT be the sentinel; must be a specific citation from the current bundle. |

### 4.3 `key_drivers[i].cites_lesson_indices` — field rules

| Field | Type | Rules |
|---|---|---|
| `cites_lesson_indices` | `list[int]` | **Required** on every driver. May be empty `[]` (bundle-derived, no lesson support). Each index: `0 <= idx < len(lesson_labels)` AND `lesson_labels[idx].label == "confirmed"`. |

### 4.4 What gets labeled — scope

| Source | Labeled? |
|---|---|
| `ticker_lessons[i].predictor_lessons[]` (each string) | ✅ YES |
| `ticker_lessons[i].data_lessons[]` | ❌ NO — fetch/weight heuristics, not directional |
| `ticker_lessons[i].why` | ❌ NO — metadata |
| `ticker_lessons[i]` parent (quarter header info) | ❌ NO — metadata |
| `global_lessons[i].lesson` (scope=sector) | ✅ YES |
| `global_lessons[i].lesson` (scope=macro) | ✅ YES |
| `global_lessons[i].lesson` (scope=cross_ticker) | ✅ YES |

### 4.5 Empty / degenerate cases

| Situation | `lesson_labels` | every `cites_lesson_indices` |
|---|---|---|
| First quarter of a ticker (no prior lessons exist anywhere) | `[]` | `[]` |
| A/B baseline (learning_context intentionally blanked) | `[]` | `[]` |
| 3 ticker + 2 global lessons rendered | array of length 5 in render-order | 0–5 indices each |

---

## 5. Render contract — single source of truth

### 5.1 Current state of `_render_learning_context`

At `scripts/earnings/earnings_orchestrator.py:2485`, returns `str` (rendered text). Called from `render_bundle_text` at line 1502. Render order:

1. Ticker lessons (recency-sorted by `build_learning_context`):
   - For each ticker_lesson, emit `**{quarter_label}** — ...` header
   - For each `predictor_lessons[*]`: `  - Predictor: <text>`  ← LABELED
   - For each `data_lessons[*]`: `  - Data: <text>`  ← NOT labeled
   - `  - Why: <why>` ← NOT labeled
2. Global lessons by scope:
   - `scope == "sector"` → `- [sector:{ts}] ({src}) {lesson}`  ← LABELED
   - `scope == "macro"` → `- [macro] ({src}) {lesson}`  ← LABELED
   - `scope == "cross_ticker"` → `- [cross:{rt}] ({src}) {lesson}`  ← LABELED

### 5.2 Refactor: renderer returns tuple

**Change**: `_render_learning_context(ctx: dict) -> tuple[str, list[str]]` — returns `(rendered_text, ordered_lesson_texts)`.

**Impact**:
- Single source of truth: the same function that emits the render also emits the expected list. By construction, render order == list order. **Zero drift surface.**
- `render_bundle_text` at line 1502 unpacks: `text, _expected = _render_learning_context(learning_ctx)` — keeps the text, discards the list (its own callers don't need it yet). Signature of `render_bundle_text` unchanged.
- New callers (the validate call sites) call `_render_learning_context(bundle["learning_context"])[1]` directly to get the list.

**Why this is strictly better than rev-2's separate `_extract_expected_lesson_texts` helper**: two functions producing "the same list in the same order" is an invariant that must be maintained forever. One function producing both eliminates the invariant.

### 5.3 Whitespace normalization helper

Add module-level helper `_normalize_lesson_text` for stable positional comparison AND the analysis substring floor:

```python
def _normalize_lesson_text(s: str) -> str:
    """Whitespace-collapse + strip + case-fold for stable comparison.

    Used for (a) positional equality between LLM-emitted lesson_text and the
    renderer's expected list, and (b) the analysis-field substring floor.
    Case-folding absorbs harmless capitalization drift without weakening
    either check meaningfully — LLMs do not reliably preserve case, and an
    intentional verbatim quote survives case folding.
    """
    return " ".join((s or "").strip().split()).lower()
```

Used on both sides of the positional check and in the analysis-leak check.

### 5.4 SKILL.md order instruction

Because the LLM reads `bundle.learning_context` from JSON (§9), its emission order must match the renderer's traversal. SKILL.md instructs the order explicitly (see §8.1).

---

## 6. Validation (single layer — Python post-return)

### 6.1 Why no PreToolUse hook

The learner has `validate_learning_output.py` because the learner's derived-write recovery path (orchestrator line 1865-1889) reuses an existing `learning/result.json` if present. A malformed write caught at disk-write time prevents the recovery path from ever seeing bad data.

The **predictor has no such recovery path**. Its flow at `earnings_orchestrator.py:3284-3299`:
1. SDK call writes `result.json`
2. `finalize_prediction_result` loads + enriches + writes back; also calls `_render_and_harvest_best_effort` at line 3005 which generates `result.md` sidecar and captures `thinking.md`
3. `validate_prediction_result` runs on the loaded payload

**Honest scoping**: sidecar artifacts (`result.md`, `thinking.md`) can be generated *before* validation rejects malformed content. These are **diagnostic/viewing artifacts only** — no business-logic consumer reads them to make decisions. Downstream readers of predictions (A/B analysis, trade execution, audit tooling) all read `result.json` which is validator-gated. For failed quarters, run_ledger (#362) records the `FAILED_VALIDATION` outcome; a human reviewer can see the sidecar exists alongside that status.

So the tight claim is: **no business-logic consumer reads an unvalidated result.** Sidecar generation for failed predictions is an acceptable trade-off — the thinking capture is often MORE valuable for a failed prediction (aids post-mortem debugging). A hook would prevent this diagnostic capture for zero business-logic benefit.

If this ever becomes a concern (e.g., a new consumer reads `result.md` as an input), add a hook at that time — by delegating to `validate_prediction_result` the same way `validate_learning_output.py` delegates to `validate_attribution_result`.

### 6.2 New signature of `validate_prediction_result`

```python
def validate_prediction_result(
    payload: dict[str, Any],
    expected_ticker: str,
    expected_quarter: str,
    *,
    expected_lesson_texts: list[str] | None = None,
) -> None:
```

**Backward-compatible**: 6 existing call sites (§7.3) pass only the first 3 args today. Adding a new kwarg with `None` default does NOT break them — but without the kwarg, the positional cross-check is skipped. All NEW runtime call sites MUST pass the kwarg for the structural contract to hold. This plan wires all 6 sites; `None` remains only for offline audit use.

### 6.3 Validation order

1. Existing validations (unchanged)
2. `lesson_labels` shape + enum + non-empty strings
3. Bundle_evidence sentinel discipline (sentinel only for `irrelevant`)
4. Positional content equality (iff `expected_lesson_texts is not None`)
5. `cites_lesson_indices` shape + range + confirmed-only
6. Analysis-field substring floor (rejects verbatim quote of non-confirmed `lesson_text`)

---

## 7. File-by-file change inventory (single atomic commit)

| # | File | Action | Lines (approx) |
|---|---|---|---|
| 1 | `.claude/skills/earnings-prediction/SKILL.md` | **Modify** — add Phase 0 (+45), extend Output JSON example (+10), add field definitions (+10). | +65 |
| 2 | `scripts/earnings/earnings_orchestrator.py` — `_render_learning_context` | **Modify** — change signature to return `tuple[str, list[str]]`; append `predictor_lessons[*]` and scope-ordered `global_lessons[*].lesson` to a local list as they are emitted. | +8 / −1 |
| 3 | `scripts/earnings/earnings_orchestrator.py` — `render_bundle_text` line 1502 | **Modify** — unpack tuple: `text, _expected = _render_learning_context(learning_ctx)`; use `text`. | +1 / −1 |
| 4 | `scripts/earnings/earnings_orchestrator.py` — `_normalize_lesson_text` helper | **New** — module-level. | +4 |
| 5 | `scripts/earnings/earnings_orchestrator.py` — `validate_prediction_result` | **Modify** — add kwarg + 6 validation blocks per §6.3. | +60 |
| 6 | Caller wiring at **all 6** validate call sites (§7.3) | **Modify** — extract list, pass kwarg. Site A: 2 lines (bundle in scope). Sites B, C, D, E, F: 3 lines each (bundle-load + renderer + kwarg) + 1 import line each. | +22 (2 + 3×5 + 5 imports) |
| 7 | `.claude/plans/learner.md` — §13 Phase 4 + backlog row | **Modify** — retire "NOT YET implemented" framing; point to this file. | +4 / −4 |
| 8 | `scripts/earnings/test_validate_prediction_result.py` | **NEW** (verified absent) — V1–V24. | +130 |
| 9 | `scripts/earnings/test_render_learning_context.py` | **NEW** (verified absent) — R1–R4 renderer tuple tests. | +35 |
| **Total source** | | | **~164** |
| **Total incl. tests** | | | **~329** |

**Deferred (separate PR after ≥10 T1 quarters)**:
- `scripts/earnings/audit_lesson_labels.py` + test (~130 lines)
- `scripts/earnings/result_md_renderer.py` label section (~15 lines)

### 7.1 Regression surface

Consumers of `prediction_result.v1`:
- `earnings_orchestrator.py` (validator + finalizer — this plan)
- `scripts/run_ab_baseline.py`, `run_nvda_ab_sequential.py`, `run_burl_ab_sequential.py`, `run_calibration_sequential.py`, `run_q3_from_existing_bundle.py` — existing readers use `.get()` per inspection; additive fields transparent; this plan wires the kwarg at their validate sites.
- `result_md_renderer.py` — unaware of new fields is safe; sidecar just lacks labels section until the deferred PR adds it.
- `thinking_harvester.py` — reads via try/except; additive fields transparent.

Zero other readers. Grep after commit: `grep -rn "prediction_result\|lesson_labels\|cites_lesson_indices" scripts/ .claude/` to verify no hidden consumer.

Consumers of `_render_learning_context`:
- `render_bundle_text` line 1502 — only caller today. Tuple unpacking is 1-line change.

### 7.2 Consumers of `render_bundle_text`
- `run_core_flow` at `earnings_orchestrator.py:1517` — uses only the text. Unaffected by internal tuple change.

### 7.3 Concrete call sites of `validate_prediction_result` (enumerated — all 6 wired)

All 6 sites empirically verified via `grep -rn "validate_prediction_result(" scripts/earnings/ scripts/run_*.py`. **T1 wires all 6 uniformly** — no active/paused split. The A/B scripts are wired while paused so that A/B reactivation requires zero additional code work. A/B test *runs* remain paused per user directive; the wiring is dormant and benign when those scripts aren't executed.

| Site | File:Line | Bundle source | Wiring (T1) |
|---|---|---|---|
| A | `scripts/earnings/earnings_orchestrator.py:3295` | `bundle` dict in scope from `run_core_flow` | 2 lines: renderer call + kwarg |
| B | `scripts/run_ab_baseline.py:134` | `stripped_bundle: Path` at line 93 → load JSON | 3 lines: `json.loads(stripped_bundle.read_text())` + renderer + kwarg |
| C | `scripts/run_burl_ab_sequential.py:117` | `stripped_bundle: Path` declared at line 95 → load JSON | 3 lines: same pattern as B |
| D | `scripts/run_calibration_sequential.py:76` | `paths["bundle_path"]: Path` via `get_prediction_paths` → load JSON | 3 lines: `json.loads(paths["bundle_path"].read_text())` + renderer + kwarg |
| E | `scripts/run_nvda_ab_sequential.py:112` | `stripped_bundle: Path` declared at line 91 → load JSON | 3 lines: same pattern as B |
| F | `scripts/run_q3_from_existing_bundle.py:84` | `paths["bundle_path"]: Path` at line 58 → load JSON | 3 lines: same pattern as D |

**Universal wiring pattern** (site-specific variable names):
```python
from earnings_orchestrator import _render_learning_context  # add to imports if not already
# Site A: bundle is already in scope (skip the next line)
bundle = json.loads(<bundle_path_var>.read_text(encoding="utf-8"))
_, expected_lessons = _render_learning_context((bundle or {}).get("learning_context") or {})
validate_prediction_result(payload, ticker, quarter_label,
                           expected_lesson_texts=expected_lessons)
```

Where `<bundle_path_var>` is:
- B/C/E: `stripped_bundle`
- D: `paths["bundle_path"]`
- F: `paths["bundle_path"]`

**A/B WITHOUT-lessons semantics**: sites B/C/E run against bundles with `learning_context.ticker_lessons = []` and `global_lessons = []` (stripped). Therefore `expected_lessons = []` at those sites, and the positional check trivially passes. Shape/enum/citation-confirmed/analysis-floor all still fire on any predictor output. Structural coverage is universal.

---

## 8. Implementation details (exact snippets — bot-ready)

### 8.1 `earnings-prediction/SKILL.md` — exact block to insert

**Insert BEFORE current `## Reasoning` at line 30:**

````markdown
## Phase 0 — Label Prior Lessons (MANDATORY before any reasoning)

**Source of truth**: read `bundle.learning_context` from the JSON at `BUNDLE_PATH`. This is a dict with two keys:
- `ticker_lessons: list[dict]` — each with `predictor_lessons: list[str]`, `data_lessons`, `why`, `quarter_label`, etc.
- `global_lessons: list[dict]` — each with `scope` (one of `sector`/`macro`/`cross_ticker`), `lesson: str`, etc.

**What to label**:
- Every string in `ticker_lessons[i].predictor_lessons[j]` (walk `i` in array order, then `j` in array order)
- Every `global_lessons[i].lesson` where `global_lessons[i].scope == "sector"` (in array order)
- Every `global_lessons[i].lesson` where `scope == "macro"` (in array order)
- Every `global_lessons[i].lesson` where `scope == "cross_ticker"` (in array order)

**What NOT to label** (these exist in the bundle/render but are NOT in your label list):
- `ticker_lessons[i].data_lessons[]` — fetch/weight heuristics
- `ticker_lessons[i].why` — metadata
- Quarter header metadata (direction_correct, actual_daily_pct, primary_driver_category)

**Emission order MUST match the traversal above** — the validator compares positionally against an orchestrator-computed expected list. Misordering fails validation.

**For each labeled lesson, answer one question**:

> Does the CURRENT bundle independently show evidence that this lesson's specific mechanism applies?

Emit a label entry with exactly three fields:

- `lesson_text` — the verbatim lesson string, copied from `predictor_lessons[j]` or `global_lessons[i].lesson` with NO paraphrasing
- `label` — strictly one of `"confirmed"` / `"contradicted"` / `"irrelevant"` (lowercase only)
  - `confirmed`: the current bundle independently shows the lesson's mechanism is present
  - `contradicted`: the current bundle shows evidence of the *opposite*
  - `irrelevant`: the lesson's mechanism is absent from the current bundle
- `bundle_evidence` — a 1-sentence citation from the current bundle justifying the label
  - For `irrelevant`: you MAY use the literal string `"no relevant evidence"` or a specific explanation
  - For `confirmed` and `contradicted`: MUST be specific evidence (section/field name + value or quote). The string `"no relevant evidence"` is rejected by the validator for these labels.

**Citation rule (structural)**: every `key_drivers[i]` MUST include `cites_lesson_indices: list[int]` (may be empty `[]`). Each integer references a position in your `lesson_labels[]` array. You may cite a lesson ONLY if its `label == "confirmed"`. The validator rejects citation of `contradicted` or `irrelevant` labels.

**Empty case**: if `bundle.learning_context.ticker_lessons` and `bundle.learning_context.global_lessons` are both empty, emit `"lesson_labels": []` and ensure every `cites_lesson_indices` is `[]`. Do not omit.

**`analysis` field constraint**: your `analysis` free-text must not contain the verbatim normalized `lesson_text` of any lesson whose label is `contradicted` or `irrelevant`. You may paraphrase or omit — not quote. The validator performs a substring check.

**Example** (shape only — do NOT copy phrasings; label based on YOUR current bundle):

```json
"lesson_labels": [
  {
    "lesson_text": "<first labeled lesson, verbatim from learning_context>",
    "label": "irrelevant",
    "bundle_evidence": "no relevant evidence"
  },
  {
    "lesson_text": "<second labeled lesson, verbatim>",
    "label": "confirmed",
    "bundle_evidence": "<1-sentence citation from THIS quarter's bundle>"
  }
],
"key_drivers": [
  { "driver": "<bundle-derived driver>", "direction": "short", "evidence": "<bundle citation>", "cites_lesson_indices": [] },
  { "driver": "<driver supported by lesson>", "direction": "short", "evidence": "<bundle citation>", "cites_lesson_indices": [1] }
]
```
````

**Modify the `## Output` JSON example** (lines 42–59 of current SKILL.md):

Add `"lesson_labels": [...]` before `"key_drivers"`. Add `"cites_lesson_indices": []` inside every example `key_drivers` entry.

**Add two entries to `### Field definitions`** (after existing `evidence_ledger`, before `analysis`):

```markdown
**`lesson_labels`** — required, array (may be `[]` only when `bundle.learning_context.ticker_lessons` and `global_lessons` are both empty). One entry per labeled lesson per §Phase 0. Schema: `{lesson_text, label, bundle_evidence}`.

**`cites_lesson_indices`** (on every `key_drivers[i]`) — required, `list[int]` (may be `[]`). Each integer is a position in `lesson_labels[]`; cited position MUST have `label == "confirmed"`.
```

### 8.2 `_render_learning_context` — tuple refactor

**Current** (line 2485):
```python
def _render_learning_context(learning_ctx: dict) -> str:
    """Render learning context into a readable section for the prediction bundle."""
    parts: list[str] = []
    parts.append("## Prior Lessons (from learner)")

    ticker_lessons = learning_ctx.get("ticker_lessons", [])
    global_lessons = learning_ctx.get("global_lessons", [])

    if not ticker_lessons and not global_lessons:
        parts.append("\nNo prior lessons available (first prediction for this ticker).")
        return "\n".join(parts)

    # … existing body …

    return "\n".join(parts)
```

**New**:
```python
def _render_learning_context(learning_ctx: dict) -> tuple[str, list[str]]:
    """Render learning context and emit the ordered list of LABELED lesson texts.

    Returns (rendered_text, ordered_lesson_texts). The list is the authoritative
    source of truth for T1 lesson_labels positional validation — by construction,
    it is emitted in the same traversal order the render emits. Excludes
    data_lessons and metadata (why, quarter headers) per T1 scope rules.
    """
    parts: list[str] = []
    ordered: list[str] = []  # T1: labeled lesson texts in render order

    parts.append("## Prior Lessons (from learner)")

    ticker_lessons = learning_ctx.get("ticker_lessons", [])
    global_lessons = learning_ctx.get("global_lessons", [])

    if not ticker_lessons and not global_lessons:
        parts.append("\nNo prior lessons available (first prediction for this ticker).")
        return "\n".join(parts), ordered

    if ticker_lessons:
        parts.append(f"\n### Ticker Lessons ({len(ticker_lessons)} most recent quarters)\n")
        for lesson in ticker_lessons:
            ql = lesson.get("quarter_label", "?")
            correct = lesson.get("direction_correct")
            actual = lesson.get("actual_daily_pct")
            pred_dir = lesson.get("predicted_direction", "?")
            cat = lesson.get("primary_driver_category", "?")
            icon = "correct" if correct else "wrong"
            parts.append(f"**{ql}** — prediction {icon} ({pred_dir}), actual {actual:+.2f}%, driver: {cat}")
            for pl in lesson.get("predictor_lessons", []):
                parts.append(f"  - Predictor: {pl}")
                if isinstance(pl, str) and pl.strip():
                    ordered.append(pl)                     # T1: LABELED
            for dl in lesson.get("data_lessons", []):
                parts.append(f"  - Data: {dl}")            # T1: NOT labeled
            why = lesson.get("why")
            if why:
                parts.append(f"  - Why: {why}")            # T1: NOT labeled
            parts.append("")

    if global_lessons:
        by_scope: dict[str, list[dict]] = {"sector": [], "macro": [], "cross_ticker": []}
        for entry in global_lessons:
            by_scope.setdefault(entry.get("scope"), []).append(entry)

        if by_scope["sector"]:
            parts.append(f"\n### Sector Lessons ({len(by_scope['sector'])} entries)\n")
            for entry in by_scope["sector"]:
                ts = entry.get("target_sector") or "?"
                src = entry.get("source_ticker") or "?"
                lesson_text = entry.get("lesson", "")
                parts.append(f"- [sector:{ts}] ({src}) {lesson_text}")
                if isinstance(lesson_text, str) and lesson_text.strip():
                    ordered.append(lesson_text)            # T1: LABELED

        if by_scope["macro"]:
            parts.append(f"\n### Macro Lessons ({len(by_scope['macro'])} entries)\n")
            for entry in by_scope["macro"]:
                src = entry.get("source_ticker") or "?"
                lesson_text = entry.get("lesson", "")
                parts.append(f"- [macro] ({src}) {lesson_text}")
                if isinstance(lesson_text, str) and lesson_text.strip():
                    ordered.append(lesson_text)            # T1: LABELED

        if by_scope["cross_ticker"]:
            parts.append(f"\n### Cross-Ticker Lessons ({len(by_scope['cross_ticker'])} entries)\n")
            for entry in by_scope["cross_ticker"]:
                rt = entry.get("related_tickers") or []
                src = entry.get("source_ticker") or "?"
                lesson_text = entry.get("lesson", "")
                parts.append(f"- [cross:{','.join(rt)}] ({src}) {lesson_text}")
                if isinstance(lesson_text, str) and lesson_text.strip():
                    ordered.append(lesson_text)            # T1: LABELED
        parts.append("")

    return "\n".join(parts), ordered
```

**Update caller** at line 1502:
```python
# BEFORE:
sections.append(_render_learning_context(learning_ctx))
# AFTER:
_text, _ = _render_learning_context(learning_ctx)
sections.append(_text)
```

### 8.3 `_normalize_lesson_text` helper

Insert at module level near the top of the validator section (e.g., just above `validate_prediction_result`):

```python
def _normalize_lesson_text(s: str) -> str:
    """Whitespace-collapse + strip + case-fold for stable comparison.

    Used for both (a) positional equality and (b) analysis substring floor.
    Case-folding absorbs harmless capitalization drift; LLMs do not reliably
    preserve case, and an intentional verbatim quote survives case folding.
    """
    return " ".join((s or "").strip().split()).lower()
```

### 8.4 `validate_prediction_result` — exact additions

**Current state** (line 1574): see §4.2 of rev 2 for the existing body.

**Signature change**: add `, *, expected_lesson_texts: list[str] | None = None`.

**Add `"lesson_labels"`** to the `required` list at line 1578–1594. Insert it right after `"analysis"` (which is the last LLM-written field) and before `"predicted_at"` (the first Python-owned metadata field). This keeps the list's logical grouping intact: identity → LLM-analytic → Python metadata.

**INSERT new validation blocks** after the existing `analysis` non-empty check (line 1639):

```python
# ══════════════════════════════════════════════════════════════════
# T1 — lesson_labels validation (template-overfit mitigation)
# ══════════════════════════════════════════════════════════════════
_LABEL_ENUM = {"confirmed", "contradicted", "irrelevant"}

labels = payload.get("lesson_labels")
if labels is None:
    raise ValueError("lesson_labels must be a list, got null")
if not isinstance(labels, list):
    raise ValueError(f"lesson_labels must be a list, got {type(labels).__name__}")

# ─ Shape + enum + non-empty + sentinel discipline ─
for i, entry in enumerate(labels):
    if not isinstance(entry, dict):
        raise ValueError(f"lesson_labels[{i}] must be an object")
    for req in ("lesson_text", "label", "bundle_evidence"):
        if req not in entry:
            raise ValueError(f"lesson_labels[{i}] missing required field: {req}")
    lbl = entry["label"]
    if lbl not in _LABEL_ENUM:
        raise ValueError(
            f"lesson_labels[{i}].label must be one of {sorted(_LABEL_ENUM)}, got {lbl!r}"
        )
    for sf in ("lesson_text", "bundle_evidence"):
        if not isinstance(entry[sf], str):
            raise ValueError(f"lesson_labels[{i}].{sf} must be a string")
    if not entry["lesson_text"].strip():
        raise ValueError(f"lesson_labels[{i}].lesson_text must be non-empty")
    evidence = entry["bundle_evidence"].strip()
    if not evidence:
        raise ValueError(f"lesson_labels[{i}].bundle_evidence must be non-empty")
    # Sentinel discipline: 'no relevant evidence' is reserved for irrelevant
    if lbl in ("confirmed", "contradicted") and evidence.lower() == "no relevant evidence":
        raise ValueError(
            f"lesson_labels[{i}]: {lbl!r} requires specific bundle_evidence; "
            f"'no relevant evidence' sentinel is reserved for 'irrelevant'"
        )

# ─ Positional equality against orchestrator-computed expected list ─
if expected_lesson_texts is not None:
    if len(labels) != len(expected_lesson_texts):
        raise ValueError(
            f"lesson_labels has {len(labels)} entries; "
            f"expected {len(expected_lesson_texts)} (from bundle.learning_context render order)"
        )
    for i, (got, want) in enumerate(zip(labels, expected_lesson_texts)):
        if _normalize_lesson_text(got["lesson_text"]) != _normalize_lesson_text(want):
            raise ValueError(
                f"lesson_labels[{i}].lesson_text does not match expected "
                f"(normalized comparison failed at position {i})"
            )

# ─ cites_lesson_indices: confirmed-only ─
for i, kd in enumerate(payload["key_drivers"]):
    if "cites_lesson_indices" not in kd:
        raise ValueError(f"key_drivers[{i}].cites_lesson_indices is required (may be empty list)")
    cites = kd["cites_lesson_indices"]
    if not isinstance(cites, list):
        raise ValueError(f"key_drivers[{i}].cites_lesson_indices must be a list")
    for j, idx in enumerate(cites):
        # Reject bool-as-int (Python quirk: isinstance(True, int) is True)
        if not isinstance(idx, int) or isinstance(idx, bool):
            raise ValueError(
                f"key_drivers[{i}].cites_lesson_indices[{j}] must be int, got {type(idx).__name__}"
            )
        if not (0 <= idx < len(labels)):
            raise ValueError(
                f"key_drivers[{i}].cites_lesson_indices[{j}] = {idx} out of range "
                f"(len(lesson_labels)={len(labels)})"
            )
        if labels[idx]["label"] != "confirmed":
            raise ValueError(
                f"key_drivers[{i}].cites_lesson_indices[{j}] = {idx} cites lesson with "
                f"label={labels[idx]['label']!r}; only 'confirmed' labels may be cited"
            )

# ─ Analysis-field substring floor: reject verbatim quote of non-confirmed lesson ─
# Length guard at 30 chars: below this, substring match risks innocent
# collision on common short phrases (e.g. "margin pressure continued").
# Real learner lessons are 80–150 chars — guard is cheap insurance.
# Case-fold is applied by _normalize_lesson_text for both sides.
_ANALYSIS_MIN_LEN = 30
analysis_norm = _normalize_lesson_text(payload["analysis"])
for i, entry in enumerate(labels):
    if entry["label"] == "confirmed":
        continue
    lt_norm = _normalize_lesson_text(entry["lesson_text"])
    if len(lt_norm) < _ANALYSIS_MIN_LEN:
        continue  # too short for reliable substring match; paraphrase-evasion already acknowledged (§2.2)
    if lt_norm in analysis_norm:
        raise ValueError(
            f"analysis contains verbatim lesson_labels[{i}].lesson_text "
            f"(label={entry['label']!r}); paraphrase or omit — may not quote"
        )
```

### 8.5 Caller wiring at 6 sites

For each site in §7.3, add **2 or 3 lines** just before the `validate_prediction_result(...)` call:
- **Site A** (`earnings_orchestrator.py`): **2 lines** — bundle dict is already in scope; just call renderer + pass kwarg.
- **Sites B, C, D, E, F** (runner scripts): **3 lines** — bundle is a `Path` (not a dict); add one `json.loads(...read_text())` before the renderer call + pass kwarg.

**Pattern** (adjust `bundle`/`<bundle_path_var>` per site — Site A omits the first line since `bundle` is already in scope):
```python
bundle = json.loads(<bundle_path_var>.read_text(encoding="utf-8"))  # Sites B/C/D/E/F only
_, _expected_lessons = _render_learning_context((bundle or {}).get("learning_context") or {})
validate_prediction_result(
    payload, ticker, quarter_label,
    expected_lesson_texts=_expected_lessons,
)
```

**Import note** (all 6 sites): `_render_learning_context` must be importable at each caller.
- Site A (same module): no import needed.
- Sites B/C/D/E/F: add `from earnings_orchestrator import _render_learning_context` at the top if not already imported.

**Per-site wiring** (all 6 sites — uniform coverage):

- **Site A** (`earnings_orchestrator.py:3295`): `bundle` dict in scope. Import already in-module:
  ```python
  _, _expected_lessons = _render_learning_context((bundle or {}).get("learning_context") or {})
  validate_prediction_result(prediction, expected_ticker=args.ticker,
                             expected_quarter=quarter_info["quarter_label"],
                             expected_lesson_texts=_expected_lessons)
  ```

- **Site B** (`run_ab_baseline.py:134`): `stripped_bundle` is a `Path` at line 93. Wire before the existing validate call:
  ```python
  bundle = json.loads(stripped_bundle.read_text(encoding="utf-8"))
  _, _expected_lessons = _render_learning_context((bundle or {}).get("learning_context") or {})
  validate_prediction_result(no_lessons, "AVGO", ql,
                             expected_lesson_texts=_expected_lessons)
  ```
  Add `from earnings_orchestrator import _render_learning_context` to existing imports. `_expected_lessons` will be `[]` because the A/B path strips `learning_context`.

- **Site C** (`run_burl_ab_sequential.py:117`): `stripped_bundle: Path` at ~line 105. Same pattern as B with `TICKER="BURL"`:
  ```python
  bundle = json.loads(stripped_bundle.read_text(encoding="utf-8"))
  _, _expected_lessons = _render_learning_context((bundle or {}).get("learning_context") or {})
  validate_prediction_result(json.loads(test_result_path.read_text()), TICKER, label,
                             expected_lesson_texts=_expected_lessons)
  ```

- **Site D** (`run_calibration_sequential.py:76`): inside `finalize_and_learn`, bundle NOT in scope. `paths["bundle_path"]` provides it. After `prediction = json.loads(paths["result_path"].read_text())` at line 75:
  ```python
  bundle = json.loads(paths["bundle_path"].read_text(encoding="utf-8"))
  _, _expected_lessons = _render_learning_context((bundle or {}).get("learning_context") or {})
  validate_prediction_result(prediction, TICKER, quarter_label,
                             expected_lesson_texts=_expected_lessons)
  ```
  Add `from earnings_orchestrator import _render_learning_context` to existing imports.

- **Site E** (`run_nvda_ab_sequential.py:112`): `stripped_bundle: Path` at ~line 100. Same pattern as B with `TICKER="NVDA"`:
  ```python
  bundle = json.loads(stripped_bundle.read_text(encoding="utf-8"))
  _, _expected_lessons = _render_learning_context((bundle or {}).get("learning_context") or {})
  validate_prediction_result(json.loads(test_result_path.read_text()), TICKER, label,
                             expected_lesson_texts=_expected_lessons)
  ```

- **Site F** (`run_q3_from_existing_bundle.py:84`): `paths["bundle_path"]` in scope at line 58:
  ```python
  bundle = json.loads(paths["bundle_path"].read_text(encoding="utf-8"))
  _, _expected_lessons = _render_learning_context((bundle or {}).get("learning_context") or {})
  validate_prediction_result(prediction, TICKER, quarter_info["quarter_label"],
                             expected_lesson_texts=_expected_lessons)
  ```
  Add import if missing.

**All 6 sites pass `expected_lesson_texts` → positional enforcement is universal across the repo's entire validate surface.** A/B sites (B/C/E) have `expected = []` because the A/B path strips the learning_context — positional check trivially satisfied; shape/enum/citation/analysis-floor still fire.

### 8.6 Plan-doc sync — `learner.md`

At the "🔴 Next up" backlog table, update the T1 row to:
```
| T1 | … | ✅ **shipped in commit <hash>** — see `.claude/plans/labeled-lesson-consumption.md` (rev 3) |
```

At §13 Phase 4's "Proposed mitigation for template overfit" heading, add one line near the top:
```
> **STATUS**: shipped <date> as `.claude/plans/labeled-lesson-consumption.md` (rev 3). Spec below retained as historical design context only.
```

---

## 9. Test matrix

### 9.1 Validator tests — `test_validate_prediction_result.py`

| # | Test | Expected |
|---|---|---|
| V1 | All required fields valid; `lesson_labels=[]`, `expected=[]`, every driver `cites_lesson_indices=[]` | passes |
| V2 | 3 labels in order; `expected` matches positionally; drivers cite only `confirmed` indices | passes |
| V3 | `lesson_labels` field absent | raises `lesson_labels` missing |
| V4 | `lesson_labels: null` | raises |
| V5 | `lesson_labels` is a string | raises type |
| V6 | Entry missing `label` | raises `label` missing |
| V7 | `label="maybe"` | raises enum |
| V8 | `label="CONFIRMED"` (wrong case) | raises enum |
| V9 | `lesson_text=""` | raises non-empty |
| V10 | `bundle_evidence=""` | raises non-empty |
| V11 | `expected` has 3, `lesson_labels` has 2 | raises length mismatch |
| V12 | `expected` has 3, `lesson_labels` has 4 (fabrication) | raises length mismatch |
| V13 | Length matches but `lesson_labels[1].lesson_text` differs post-normalization | raises positional mismatch |
| V14 | Trailing/interior whitespace diff between text and expected (post-normalize equal) | passes |
| V15 | `key_drivers[i]` missing `cites_lesson_indices` | raises |
| V16 | `cites_lesson_indices=[0]` where `lesson_labels[0].label="irrelevant"` | raises "only 'confirmed' may be cited" |
| V17 | `cites_lesson_indices=[0]` where `lesson_labels[0].label="contradicted"` | raises |
| V18 | `cites_lesson_indices=[5]` but `len(labels)=3` | raises out of range |
| V19 | `cites_lesson_indices=[True]` (bool) | raises type |
| V20 | `expected_lesson_texts=None` (audit mode); shape valid; skip positional | passes |
| V21 | `label="confirmed"` + `bundle_evidence="no relevant evidence"` | raises sentinel violation |
| V22 | `analysis` contains verbatim normalized lesson_text of an `irrelevant` label | raises analysis leak |
| V23 | `analysis` contains verbatim normalized lesson_text of a `confirmed` label | passes (citation allowed) |
| V24 | `analysis` paraphrases an `irrelevant` lesson but never quotes it verbatim | passes (substring floor acknowledges paraphrase-evasion) |

### 9.2 Renderer tests — `test_render_learning_context.py`

| # | Test | Expected |
|---|---|---|
| R1 | Empty `learning_context` | returns `(text_with_first_prediction_message, [])` |
| R2 | Ticker lessons with `predictor_lessons + data_lessons + why` — list excludes data + why | list length = sum of predictor_lessons only |
| R3 | Globals: 2 sector + 1 macro + 2 cross_ticker — list order is sector, sector, macro, cross, cross | exact list match |
| R4 | Mixed ticker + global — render text contains all bullets; list contains only labeled lessons in order | pass |

### 9.3 Integration tests

| # | Test | Expected |
|---|---|---|
| I1 | Full predict flow with mocked SDK producing valid labels matching renderer's list | writes valid `prediction/result.json`; validator passes |
| I2 | SDK emits `lesson_labels=[]` when renderer listed 3 lessons | validator rejects length mismatch |
| I3 | SDK cites `irrelevant` lesson in `cites_lesson_indices` | validator rejects |
| I4 | A/B baseline (WITHOUT-lessons): bundle has blanked learning_context; LLM must emit `lesson_labels=[]` and every `cites_lesson_indices=[]` | validator passes with `expected=[]` |
| I5 | Re-validation of written result.json with `expected=None` (audit mode) | passes shape, skips positional |
| I6 | SDK's `analysis` quotes an `irrelevant` lesson verbatim | validator rejects; retry fires |

---

## 10. Deferred — audit script

Per rev-2 reasoning: zero T1 quarters exist at ship time. Threshold calibration (70%/85%) is a priori guessing until real distribution is observed.

**When to ship**: after ≥10 T1 quarters on the post-wipe corpus.

**Draft spec** (retained for future implementer):
- `scripts/earnings/audit_lesson_labels.py`
- Walks `Companies/*/events/*/prediction/result.json`
- Per-ticker aggregates: `quarters_scored`, label-count distribution, `confirmed_rate`
- Sample guard: `status = "INSUFFICIENT_DATA"` if `quarters_scored < 3` OR `total_labels < 10`
- Thresholds (calibrate against real data): tentative WARN > 70%, FLAG > 85%
- Output: text (default), `--json`, `--ticker <TICKER>`
- Companion test `test_audit_lesson_labels.py`
- If FLAG triggers on ≥3 tickers: escalate to label-only-LLM (design sketch in `learner.md` §13 Phase 4)

---

## 11. Rollout — single atomic commit

### 11.1 Pre-commit checklist

- [ ] **Task #356 corpus wipe complete** (or explicit acceptance of caveat)
- [ ] All new/modified files `py_compile` clean
- [ ] V1–V24 + R1–R4 + I1–I6 green
- [ ] Existing predictor tests still pass (regression check)
- [ ] Grep confirms **all 6** call sites are wired with `expected_lesson_texts=`:
  ```bash
  # NOTE: --exclude-dir=__pycache__ + --exclude=test_*.py (file-level exclude, NOT
  # line-level `-v test_` — line-level filter accidentally drops lines containing
  # the `test_result_path` variable name used in A/B runners).
  grep -rn "validate_prediction_result(" scripts/ \
      --include="*.py" --exclude-dir=__pycache__ --exclude="test_*.py" \
    | grep -v "def validate"
  ```
  must return exactly 6 lines (line numbers may shift ± a few):
  1. `scripts/earnings/earnings_orchestrator.py:<~3295>`
  2. `scripts/run_ab_baseline.py:<~134>`
  3. `scripts/run_burl_ab_sequential.py:<~117>`
  4. `scripts/run_calibration_sequential.py:<~76>`
  5. `scripts/run_nvda_ab_sequential.py:<~112>`
  6. `scripts/run_q3_from_existing_bundle.py:<~84>`

  **Universal-wiring assertion** — every one of these call sites must pass the kwarg as a real argument (not the function-def default):
  ```bash
  # Match the KWARG invocation pattern 'expected_lesson_texts=_expected_lessons'
  # explicitly — this excludes the function-def default (which uses
  # ': list[str] | None = None' with a colon type annotation and NO equals-sign
  # directly after the identifier). Excludes test files via --exclude.
  grep -rn "expected_lesson_texts=_expected_lessons" scripts/ \
      --include="*.py" --exclude-dir=__pycache__ --exclude="test_*.py" \
    | wc -l
  ```
  must return `6` (one invocation per call site, exactly 6).
- [ ] Each runner script (5 sites outside the orchestrator) has the specific new bundle-load line introduced by T1 (not pre-existing `read_text()` calls for other purposes):
  - For A/B runners (B, C, E) — bundle source is `stripped_bundle`:
    ```bash
    grep -c "stripped_bundle\.read_text" scripts/run_ab_baseline.py scripts/run_burl_ab_sequential.py scripts/run_nvda_ab_sequential.py
    ```
    must return `1` for each (exactly the new T1 bundle-load line).
  - For orchestrator-path runners (D, F) — bundle source is `paths["bundle_path"]`:
    ```bash
    grep -c 'paths\["bundle_path"\]\.read_text' scripts/run_calibration_sequential.py scripts/run_q3_from_existing_bundle.py
    ```
    must return `1` for each.
  - Combined: total new bundle-load lines across runner files = 5 (one per site B/C/D/E/F).
- [ ] Grep confirms no `_extract_expected_lesson_texts` helper introduced (rev-3 uses renderer tuple, not a separate extractor)
- [ ] Grep confirms no PreToolUse hook file created for predictor: `ls .claude/hooks/validate_prediction*` returns "no such file"
- [ ] Dry-run one AVGO quarter via CLI: `python3 scripts/earnings/earnings_orchestrator.py AVGO <accession> --save --predict --learn` → inspect `prediction/result.json` for valid `lesson_labels` + `cites_lesson_indices`
- [ ] **A/B smoke SKIPPED** — running A/B is paused per user directive (2026-04-19), but sites B/C/E are nonetheless wired in T1 per §7.3 so positional enforcement is universal. A/B scripts are dormant-but-ready; when A/B reactivates, zero additional code work is needed — just start running them. Re-add a dry-run check for WITHOUT-lessons path when that happens.
- [ ] `jq '.lesson_labels | length' earnings-analysis/Companies/AVGO/events/<Q>/prediction/result.json` matches the expected lesson count for that quarter
- [ ] `jq '[.key_drivers[] | has("cites_lesson_indices")] | all' ...` returns `true` (every driver has the field)

### 11.2 Commit

Title: `feat(predictor): T1 — structurally-enforced labeled lesson consumption`

Body references this plan. Includes:
- Empirical cases (AVGO Q3, BURL Q1)
- Structural over prompt enforcement (cites_lesson_indices + positional + sentinel + analysis-floor)
- No hook; renderer is single source of truth
- Corpus prerequisite (#356)

### 11.3 Post-commit smoke

**Scope note**: A/B testing RUNS are paused (user directive 2026-04-19), but all 6 sites are wired. Smoke exercises Sites A and D; Sites B/C/E/F remain dormant but wiring is static-asserted by §11.1 pre-commit greps.

1. Run one AVGO WITH-lessons quarter via orchestrator CLI on the post-wipe corpus (exercises Site A):
   ```bash
   python3 scripts/earnings/earnings_orchestrator.py AVGO <AVGO_accession_8k> --save --predict --learn
   ```
2. Inspect `prediction/result.json`: label distribution not all-`confirmed`; `cites_lesson_indices` present on every driver and references only `confirmed` labels; `analysis` has no verbatim non-confirmed quotes of lessons ≥30 chars.
3. Deliberately corrupt via manual edit (e.g., set a `label` to `"MAYBE"`) and re-invoke the validator directly from a Python REPL on the modified file — confirm rejection.
4. Re-run the full 3-AVGO quarters via the calibration harness (exercises Site D including its bundle-load):
   ```bash
   python3 scripts/run_calibration_sequential.py
   ```
   Confirm: all 3 quarters validate cleanly; Site D's bundle-load path fires on each.
5. **Sites not exercised by T1 ship smoke** (B/C/E are A/B runners currently paused; F is an on-demand diagnostic): wiring is static-asserted via §11.1 pre-commit greps (`expected_lesson_texts=` present at each call site). Dynamic exercise happens when A/B is reactivated (B/C/E) or when the operator next invokes the Q3 diagnostic (F).

### 11.4 Rollback — honest version

If systemic label-dishonesty emerges (retry-rate > 30% sustained across ≥5 quarters):

**What rollback actually requires** (there is no SKILL-only shortcut — structural enforcement lives in the validator):

1. **SKILL.md** — downgrade Phase 0's "MUST NOT cite contradicted/irrelevant" language to advisory ("should avoid citing"). ~5 lines.
2. **Validator** — concurrently relax the citation-confirmed check from `raise ValueError` to `log.warning` (one 3-line edit at the `cites_lesson_indices` block). Optionally gate behind an env var `T1_STRICT_CITATIONS=false`.

**Both changes must land in the same commit.** Reverting SKILL.md alone leaves the validator enforcing — the validator still rejects, the LLM output is rejected, the quarter still fails. Rollback is a ~20-line coordinated edit, not a 5-line SKILL-only nudge.

**Schema (`lesson_labels`, `cites_lesson_indices`) stays in all rollback scenarios.** Audit-only metadata is strictly better than pre-T1.

**What to preserve in rollback**: shape + enum + non-empty + sentinel + positional equality + analysis substring floor. These are observability and data-integrity — not part of the template-overfit hypothesis being rolled back.

---

## 12. Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | **Paraphrased prose-leak in `analysis`** — LLM mentions an irrelevant lesson without verbatim quoting | Medium | Low | Substring floor catches verbatim; paraphrase requires semantic comparison (out of scope). Explicit residual per §2.2. Detectable offline by future audit. |
| R2 | **Confirmation bias in self-labeling** — same LLM decides if its own lesson applies | Medium | Medium | Deferred audit flags >70% confirmed-rate. Escalation to label-only LLM per learner.md §13 Phase 4. |
| R3 | **Order drift** — LLM emits labels in different order than renderer produced | Low | Low | Renderer is single source of truth — LLM reads same JSON, follows same traversal. Positional check catches any drift with descriptive error; retry self-corrects. |
| R4 | **Whitespace/unicode drift** between bundle text and label entry | Low | Low | `_normalize_lesson_text` handles whitespace. Paraphrasing fails → retry. |
| R5 | **Transient retry-rate increase** during first N T1 quarters | Certain (early) | Low | Existing 1-retry path in orchestrator. LearnerOutcome-style observability via run_ledger (task #362 pattern). |
| R6 | **A/B WITHOUT-lessons path regression** — validator requires `lesson_labels` even when bundle is blanked | Low | Medium | LLM must emit `lesson_labels=[]`; expected=[]. I4 test covers explicitly. |
| R7 | **Legacy/audit callers without bundle** | Certain | None | `expected_lesson_texts=None` skips positional check; shape/enum/citation still enforced. |
| R8 | **Thinking harvester compatibility** | Low | Low | Harvester uses `.get()` + try/except. Additive fields transparent. Verify in 11.1 smoke. |
| R9 | **finalize_prediction_result overwrites LLM fields** | Low | High | Verified at line 2944: field-by-field `payload[k]=...` pattern. Additive fields survive. |
| R10 | **Renderer tuple caller miss** | Low | Medium | Only 1 caller today (line 1502). Change is 2 lines. Grep `_render_learning_context(` after commit confirms all callers unpack. |

---

## 13. Pre-verified implementation facts (resolved during rev-3 authoring)

All items below were empirically checked against live code before rev-3 finalization. No open questions remain for the implementer.

| # | Fact | Verified by |
|---|---|---|
| 1 | **Predictor retry path**: The predictor flow at `earnings_orchestrator.py:3284-3299` has no informed-retry (unlike the learner's H2 path at lines ~2019-2053). Validator failure raises and stops the quarter. **Do NOT add informed-retry in this PR** — orthogonal to T1 and potentially scope-creep. | `grep -n "retry" earnings_orchestrator.py` shows retry logic only in builder transient-failure helper and in `run_learner_for_quarter` |
| 2 | **finalize_prediction_result preservation**: line 2944+ uses field-by-field `payload[k] = ...` (no dict-replacement pattern). `lesson_labels` and `cites_lesson_indices` written by the LLM survive finalize. | `grep -n "payload\[" earnings_orchestrator.py` at lines 2954-2979 confirms additive assignment only |
| 3 | **Site D bundle scope**: NO bundle in scope at the validate call (inside `finalize_and_learn`). Resolved via `json.loads(paths["bundle_path"].read_text())` per §8.5 wiring snippet. | Read of `run_calibration_sequential.py:57-79` confirmed |
| 4 | **Test-file existence**: `test_validate_prediction_result.py` and `test_render_learning_context.py` do NOT exist today. Create both as NEW files per §7 inventory. | `ls scripts/earnings/test_validate_prediction_result.py scripts/earnings/test_render_learning_context.py` returns "no such file" |
| 5 | **`_render_learning_context` import** for scripts/run_*.py: existing convention is `from earnings_orchestrator import <symbol>` (via the sys.path insert in each script's header). Add `_render_learning_context` to existing import lines per site. | `head -30 scripts/run_ab_baseline.py` shows import style |
| 6 | **`BUNDLE_PATH` resolves to `context_bundle.json` (JSON, not rendered text)**: orchestrator passes `bundle_path=context_bundle.json` via the `BUNDLE_PATH=` line in the predictor prompt (line 3081). SKILL.md Phase 0's "read `bundle.learning_context` from the JSON" instruction is accurate. | Read of `earnings_orchestrator.py:3079-3085` confirmed |
| 7 | **AVGO-specific sequential A/B**: no dedicated `run_avgo_ab_sequential.py` exists. Use `run_ab_baseline.py` (which is AVGO-specific) or the orchestrator CLI per §11.3. | `ls scripts/run_avgo_*` returns "no such file" |

---

## 14. Dependencies

| Dep | Status |
|---|---|
| T1.5a + T1.5b PIT correctness | ✅ shipped |
| T3 sector-at-source | ✅ shipped |
| Corpus wipe + 15-quarter rerun (#356) | ⏳ pending |
| Existing `validate_prediction_result` at line 1574 | ✅ |
| Existing `_render_learning_context` at line 2485 | ✅ — gets refactored |
| LearnerOutcome / run_ledger (#362) | ✅ — reuse for retry observability |

---

## 15. Rejected alternatives (pruned from rev-2; only decision-relevant kept)

| Alternative | Why rejected |
|---|---|
| Add PreToolUse Write hook for predictor | Zero unique reliability vs Python validator; no derived-write recovery path (learner's reason doesn't apply); adds ~65 lines incl tests + settings registration + drift surface. |
| Separate `_extract_expected_lesson_texts` helper (rev-2) | Two functions that must stay in sync with each other is a forever-invariant. Renderer-returns-tuple eliminates the invariant by construction. |
| Dedicated `lesson_id` field (hash/UUID) | Positional indices with verbatim `lesson_text` are already unambiguous. IDs add schema + hash-stability rules for zero gain. |
| Label `data_lessons[]` as well | Non-directional (fetch/weight); would inflate confirmed-rate + add token cost without overfit-reduction benefit. |
| Top-level `applied_lesson_ids[]` | Per-driver `cites_lesson_indices` is strictly more structural — binds citation to a specific driver. |
| Additional SKILL.md prose "don't over-apply" | Rev-1's approach; empirically failed (AVGO Q3, BURL Q1). Soft rules don't stably change LLM behavior. |
| Semantic analysis-field check via second LLM | Reintroduces confirmation bias + 2x cost. Substring floor is the cheap-structural-signal; paraphrase evasion accepted per R1. |
| Ship audit script with T1 | Premature — thresholds are a priori guesses until real T1 distribution. |
| Backward-compat default (missing `lesson_labels` → `[]`) at runtime | Corpus is being wiped; would let a forgetful LLM pass silently. |

---

## 16. References

- `scripts/earnings/earnings_orchestrator.py:1574-1639` — current `validate_prediction_result`
- `scripts/earnings/earnings_orchestrator.py:2485-2547` — current `_render_learning_context`
- `scripts/earnings/earnings_orchestrator.py:2921-3003` — `finalize_prediction_result` (additive-field-safe)
- `scripts/earnings/earnings_orchestrator.py:3295` — main predict-flow validate call
- `.claude/skills/earnings-prediction/SKILL.md` — current predictor contract
- `.claude/hooks/validate_learning_output.py` — hook pattern (NOT mirrored; kept for learner only)
- `.claude/settings.json:29-48` — PreToolUse hook registration (not extended by this plan)
- `.claude/plans/learner.md` §13 Phase 4 — original design sketch (historical)
- Task #362 (LearnerOutcome) — retry-observability pattern

---

## 17. Final sign-off checklist

- [ ] Two structural fixes understood — positional equality (via renderer tuple return) + `cites_lesson_indices` (confirmed-only) — these are what make T1 structural, not prompt-governed
- [ ] `data_lessons[]` exclusion accepted as deliberate scoping (directional template overfit is the bug)
- [ ] Audit script deferred to post-T1 data collection
- [ ] Corpus wipe (#356) prerequisite accepted
- [ ] No PreToolUse hook — accepted as correct minimalism (asymmetry with learner is deliberate)
- [ ] Renderer-returns-tuple pattern accepted — single source of truth for lesson order
- [ ] `bundle_evidence` sentinel check restored (rev-1 regression fixed)
- [ ] Analysis-field substring floor added; residual paraphrase-evasion accepted explicitly (§2.2, R1)
- [ ] All 6 validate call sites pre-enumerated (§7.3)
- [ ] Rollback = ~20-line coordinated SKILL.md + validator edit (per §11.4 honest rewrite); schema never reverts; no SKILL-only shortcut exists (validator enforcement lives in Python, not prompt)

---

**End of plan (rev 3).**

**Author**: Claude session 2026-04-19, rev 3. Empirically verified every claim in ChatGPT's and Claude's critiques against live code at `.claude/hooks/validate_learning_output.py`, `.claude/settings.json:29-48`, `scripts/earnings/earnings_orchestrator.py:1574,2485,3295`, all 6 `validate_prediction_result` call sites, A/B scripts at `scripts/run_ab_baseline.py:134`, `run_burl_ab_sequential.py:117`, `run_calibration_sequential.py:76`, `run_nvda_ab_sequential.py:112`, `run_q3_from_existing_bundle.py:84`. Every design decision traced to either a structural invariant or an explicitly-acknowledged residual risk.
