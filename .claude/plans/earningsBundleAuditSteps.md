# Section Audit — Implementation Plan

Self-contained handoff. Implement exactly what is in this document. Do NOT add features beyond what is listed. The "Deliberately deferred" section names items intentionally excluded — do not add them even if they look beneficial.

---

## Goal

Add a persistent **facts-only section audit** to the earnings prediction workflow.

The earnings predictor reads a large multi-section context bundle and produces one prediction (`prediction/result.json`). We want to force the model to inspect every numbered bundle section before making the final directional call, without splitting the prediction into multiple LLM calls and without inducing premature long/short anchoring.

We achieve this by having the same single LLM call write a structured scratchpad file (`prediction/section_audit.json`) before writing `result.json`. The scratchpad enumerates facts and signals per section but is **forbidden from containing any final direction, confidence, or expected move** — those still belong only in `result.json`.

---

## Architecture (current → after)

### Current
- The orchestrator builds one full prediction bundle and writes:
  - `events/{Q}/context_bundle.json` (quarter root)
  - `events/{Q}/context_bundle_rendered.txt` (quarter root)
- It calls the `earnings-prediction` skill **once**.
- The skill reads the full bundle and writes:
  - `prediction/result.json`

### After
- Same orchestrator. Same single LLM call. Same bundle.
- Predictor now writes **two** files in this order during the same call:
  1. `prediction/section_audit.json` (new, facts-only scratchpad)
  2. `prediction/result.json` (unchanged schema)

We are NOT adding another LLM call. We are NOT changing the bundle builder. We are NOT changing the `result.json` schema.

---

## Files to touch (verified by `grep -rln --include='*.py' "run_predictor_via_sdk" scripts/ tests/`)

Five files call the predictor SDK function. All five must be updated.

| File | How it constructs paths |
|------|------------------------|
| `scripts/earnings/earnings_orchestrator.py` | Canonical caller. Uses `get_prediction_paths()`. Tuple unpack into `predictor_session_id` MUST be preserved. |
| `scripts/run_q3_from_existing_bundle.py` | Uses `get_prediction_paths()`; deletes stale prediction result before rerun. Discards SDK return value (pre-existing pattern; do not change). |
| `scripts/run_ab_baseline.py` | Constructs paths manually (`baseline_dir / "result.json"`). **Has resume logic** — needs the paired-existence resume predicate (Step 5). |
| `scripts/run_burl_ab_sequential.py` | Constructs paths manually (`baseline_dir / "result.json"`). Always reruns. |
| `scripts/run_nvda_ab_sequential.py` | Constructs paths manually (`baseline_dir / "result.json"`). Always reruns. |

Also touch:

- `.claude/skills/earnings-prediction/SKILL.md` — add `SECTION_AUDIT_PATH` to inputs and add Phase 0.5 block.
- `scripts/earnings/result_md_renderer.py` — add a one-line `section_audit.json` cross-link to prediction `result.md` files for Obsidian discoverability.

Re-run the grep before changing the function signature in case more callers have appeared since this doc was written.

---

## Implementation steps

### Step 1 — Add new path to `get_prediction_paths()`

In `scripts/earnings/earnings_orchestrator.py`, update `get_prediction_paths(...)` to include:

```python
"section_audit_path": base_dir / "section_audit.json",
```

### Step 2 — Add `SECTION_AUDIT_PATH` to predictor prompt

In `_run_predictor_via_sdk(...)`, the SDK prompt currently passes:

```
BUNDLE_PATH=...
RENDERED_BUNDLE_PATH=...
RESULT_PATH=...
```

Add:

```
SECTION_AUDIT_PATH=...
```

### Step 3 — Update predictor instruction string

Change the predictor's instruction line from:

> Read the bundle, write RESULT_PATH as JSON, and stop.

to:

> Read the bundle, write SECTION_AUDIT_PATH as facts-only JSON, then write RESULT_PATH as JSON, and stop.

**Final assembled prompt** (combining Step 2 path env-var + Step 3 instruction; preserve the existing path order with `SECTION_AUDIT_PATH` slotted directly before `RESULT_PATH`):

```python
prompt = (
    "Run /earnings-prediction with these exact paths:\n"
    f"BUNDLE_PATH={bundle_path}\n"
    f"RENDERED_BUNDLE_PATH={rendered_path}\n"
    f"SECTION_AUDIT_PATH={section_audit_path}\n"
    f"RESULT_PATH={result_path}\n"
    "Read the bundle, write SECTION_AUDIT_PATH as facts-only JSON, then write RESULT_PATH as JSON, and stop."
)
```

### Step 4 — Confirm full caller list

Before changing the function signature, run:

```bash
grep -rln --include='*.py' "run_predictor_via_sdk" scripts/ tests/
```

The `--include='*.py'` filter restricts the search to Python source (skips reading `__pycache__/*.pyc` and any other binary artifacts that may sit alongside the source). The `tests/` path is included for future-proofing — currently no test there references the predictor SDK, but adding it costs nothing.

Expected output: 5 files (the orchestrator + 4 ad-hoc callers listed above). If the grep returns more files, update those too. The "Files to touch" list in this doc is not guaranteed to remain exhaustive.

Also run, for awareness:

```bash
grep -rln --include='*.py' "get_prediction_paths" scripts/ tests/
```

This will surface a 6th file — `scripts/run_calibration_sequential.py` — which consumes `get_prediction_paths()` but does NOT call `run_predictor_via_sdk` directly (it shells out to the orchestrator CLI for full pipelines). It receives the new `section_audit_path` key in the dict for free, never reads it, and requires no code change. Confirm this is still the case for any additional `get_prediction_paths()` consumers the grep surfaces.

### Step 5 — Update function signatures and call sites

Change function signatures:

```python
_run_predictor_via_sdk(bundle_path, rendered_path, section_audit_path, result_path)
run_predictor_via_sdk(bundle_path, rendered_path, section_audit_path, result_path)
```

> ⚠ **CRITICAL — preserve the tuple unpack at every call site.** `run_predictor_via_sdk(...)` returns `tuple[str | None, str | None]` — `(final_result, session_id)`. The orchestrator unpacks it into `predictor_session_id` which then flows into `finalize_prediction_result(sdk_session_id=...)`, `_close_run(sdk_session_id=...)`, and the thinking-harvester linkage. If you collapse the call to a bare positional invocation that discards the return value, all three downstream consumers silently receive `None`. Keep the unpack.

**Orchestrator caller** (`scripts/earnings/earnings_orchestrator.py` — preserves the existing tuple unpack):

```python
_pred_result, predictor_session_id = run_predictor_via_sdk(
    paths["bundle_path"],
    paths["rendered_path"],
    paths["section_audit_path"],
    paths["result_path"],
)
```

**`run_q3_from_existing_bundle.py` caller** (this script's pre-existing pattern discards the tuple and never passes `sdk_session_id` to `finalize_prediction_result` — preserve that pre-existing behavior; do NOT introduce session_id capture as part of this change):

```python
run_predictor_via_sdk(
    paths["bundle_path"],
    paths["rendered_path"],
    paths["section_audit_path"],
    paths["result_path"],
)
```

**Simple manual-path callers** (`run_burl_ab_sequential.py`, `run_nvda_ab_sequential.py`) — these always delete `result.json` and rerun (no resume logic). Add the symmetric audit deletion:

```python
section_audit_path = baseline_dir / "section_audit.json"
if section_audit_path.exists():
    section_audit_path.unlink()
```

And update the call (preserve the existing tuple unpack):

```python
_pred_result, baseline_session_id = run_predictor_via_sdk(
    stripped_bundle, stripped_rendered, section_audit_path, test_result_path
)
```

**Resume-aware caller** (`run_ab_baseline.py`) — this script has resume logic: if a baseline `result.json` already exists from a prior run, the script REUSES it and SKIPS the predictor entirely. The simple "delete then run" pattern above would silently delete the audit and then resume on the old result, leaving a permanent class of records on disk with `result.json` but no `section_audit.json`. The central existence check inside `run_predictor_via_sdk(...)` (Step 7) does NOT fire on resume because the SDK call is skipped.

Replace the existing resume block (around line 104–118 of `run_ab_baseline.py`) with a paired-existence predicate so resume only fires when BOTH artifacts exist; otherwise both are deleted and the predictor reruns. Preserve the existing timing/logging/`try/except` scaffolding:

```python
test_result_path = baseline_dir / "result.json"
section_audit_path = baseline_dir / "section_audit.json"
baseline_session_id = None

if test_result_path.exists() and section_audit_path.exists():
    log.info("  Reusing existing NO_LESSONS prediction (resume): %s", test_result_path)
else:
    if test_result_path.exists():
        test_result_path.unlink()
    if section_audit_path.exists():
        section_audit_path.unlink()
    t0 = datetime.now()
    try:
        _pred_result, baseline_session_id = run_predictor_via_sdk(
            stripped_bundle, stripped_rendered, section_audit_path, test_result_path
        )
    except Exception as e:
        log.error("  Predictor SDK call failed: %s", e)
        continue
    dt = (datetime.now() - t0).total_seconds()
    log.info("  Predictor done in %.1fs", dt)
```

Migration consequence (intentional): on the first re-execution after this change, any pre-existing baseline `result.json` files that lack a `section_audit.json` will be re-predicted. This is necessary — it brings the A/B baseline corpus into a clean state where every result has a matching audit.

### Step 6 — Delete stale audit before rerun

Wherever a caller deletes a stale `result.json` before re-running prediction, also delete the stale audit. This includes the canonical orchestrator and `scripts/run_q3_from_existing_bundle.py`; the manual baseline callers are covered in Step 5.

```python
if paths["section_audit_path"].exists():
    paths["section_audit_path"].unlink()
```

### Step 7 — Require both files after predictor runs (central check)

Add the existence checks inside the **sync wrapper** `run_predictor_via_sdk(...)` — after `asyncio.run(...)` returns and before the wrapper returns its tuple — so every caller that actually invokes the SDK is protected by one central check. Check `result_path` first (canonical output → more informative error if both missing), then `section_audit_path`:

```python
def run_predictor_via_sdk(bundle_path: Path,
                          rendered_path: Path,
                          section_audit_path: Path,
                          result_path: Path) -> tuple[str | None, str | None]:
    try:
        result = asyncio.run(_run_predictor_via_sdk(
            bundle_path, rendered_path, section_audit_path, result_path
        ))
    except ImportError as e:
        raise RuntimeError(
            "claude_agent_sdk is not available; cannot run --predict"
        ) from e

    if not result_path.exists():
        raise RuntimeError(f"Predictor finished without writing {result_path}")
    if not section_audit_path.exists():
        raise RuntimeError(f"Predictor finished without writing {section_audit_path}")

    return result
```

Preserve the existing wrapper docstring (`Sync wrapper for the one-turn predictor SDK call. Returns (final_result, session_id) tuple.`) — the example code block above shows only the body change, not a full replacement.

**Also remove** the existing redundant `if not paths["result_path"].exists(): raise RuntimeError(...)` block in `earnings_orchestrator.py` (currently around line 2561, immediately after the predictor SDK call) — it is now covered by the central check inside the wrapper. Leaving it in place is harmless duplication but bot should remove it for clarity.

**Caveat (intentional):** the central check does NOT fire for `run_ab_baseline.py`'s resume branch because that branch skips the SDK call entirely. The paired-existence resume predicate added in Step 5 is what protects that path.

### Step 8 — Cross-link audit from `result.md` for Obsidian discoverability

The vault is the same directory as `earnings-analysis/Companies/` (verified symlink target: `~/Obsidian/EventTrader/Earnings/earnings-analysis/Companies/`). The new `section_audit.json` therefore appears in Obsidian's file tree automatically the moment the predictor writes it — no sync step required. But a user browsing predictions in Obsidian opens `result.md` (the rendered sidecar), not the raw file tree. Without a cross-link in `result.md`, the audit JSON sits orphaned beside it.

In `scripts/earnings/result_md_renderer.py`, modify both `render_prediction` and `render_baseline_experiment` to append a one-line cross-link if the audit exists alongside `result.json`:

```python
def render_prediction(json_path: Path, md_path: Path) -> None:
    """Render a prediction result.json to its result.md sidecar."""
    payload = _read_json(json_path)
    extras = {
        "direction": payload.get("direction", ""),
        "confidence_score": payload.get("confidence_score", ""),
        "sdk_session_id": _session_id_value(payload),
    }
    fm = _build_frontmatter(
        component="prediction",
        ticker=str(payload.get("ticker", "")),
        quarter=str(payload.get("quarter_label", "")),
        extras=extras,
    )
    body = _prediction_body(payload, is_experiment=False)

    # Cross-link to section_audit.json if it exists alongside result.json.
    # The audit is raw-JSON-only by design (no audit.md sidecar — see deferred
    # list); this link makes the JSON discoverable from the prediction note.
    audit_path = json_path.with_name("section_audit.json")
    if audit_path.exists():
        body += (
            "\n\n## Section Audit\n\n"
            "→ [section_audit.json](section_audit.json) — facts-only scratchpad: "
            "per-section bullish/bearish signals, missing data, source IDs.\n"
        )

    _write_md(md_path, fm + _READONLY_MARKER + "\n\n" + body + "\n")
```

Apply the same `audit_path` existence check + cross-link append to `render_baseline_experiment` (the no_lessons experiment also produces an audit per Step 5).

**Do NOT** add the cross-link to `render_learning` or `render_guidance` — those components have no audit.

**Do NOT** add an `"audit"` key to the dispatch table — the audit is still NOT a renderable component, only a linked-to artifact.

**Pre-feature backward compatibility:** the existence check (`if audit_path.exists()`) means historical predictions written before the audit feature shipped (no audit on disk) get rendered without the cross-link, exactly as today. No broken links.

### Step 9 — Update `.claude/skills/earnings-prediction/SKILL.md`

**Input section edit (~line 23):** In the existing `## Input` block, find the exact sentence `Write your result to RESULT_PATH.` (currently the last sentence of the *first paragraph* of `## Input`; subsequent paragraphs about `learner_result:` and related-filing allowlists are unchanged). Change that sentence to:

> Write your section audit to `SECTION_AUDIT_PATH` first, then write your result to `RESULT_PATH`.

**Phase 0.5 block insertion:** Insert a new top-level section between the existing `## Phase 0 — Label Prior Lessons` block (ends ~line 89) and the `## Reasoning` block (begins ~line 91). Use a `##` heading to match the level of `## Phase 0` and `## Reasoning`. Do NOT use `####` (the four-hash heading shown in earlier drafts of this plan was illustrative only and would break the section hierarchy).

> **Verbatim insert boundary:** The block below — starting at `## Phase 0.5 — Facts-Only Section Audit` and ending at the closing `}` of the suggested-shape JSON — is the exact text to paste into SKILL.md. The `---` markdown horizontal rules that appear immediately above and below this block in *this plan document* are local visual delimiters only and must NOT be inserted into SKILL.md (which uses headings, not horizontal rules, to delimit its sections).

---

## Phase 0.5 — Facts-Only Section Audit

Before making the final directional call, write `SECTION_AUDIT_PATH` as JSON.

**Order:** Phase 0 (lesson labels) → Phase 0.5 (this audit) → Phases 1–4 (key numbers, tensions, stress-test, call). Writing `SECTION_AUDIT_PATH` does not replace Phases 1–4.

**The audit is fact-gathering only. It does NOT replace Phase 3 stress-testing.** Phase 3 must still independently build the strongest long case and the strongest short case against the full bundle, not just tally the audit's `bullish_signals` vs. `bearish_signals`.

**Coverage:** Include one entry for every numbered rendered bundle section §2 through §9 when present. (The unnumbered `## Evidence Source IDs` catalog that appears immediately after the header is not audited.) If a section has no material content for this prediction, still include the entry with empty content arrays and a short `not_material_reason` string. Silent omission is not allowed.

For each entry include:
- `section`
- `key_facts`
- `bullish_signals`
- `bearish_signals`
- `missing_or_unclear`
- `source_ids`
- `not_material_reason` — required ONLY when the section has no material content (i.e., `key_facts`, `bullish_signals`, `bearish_signals`, AND `missing_or_unclear` are ALL empty arrays); omit this field otherwise. (`source_ids` is excluded from this test — a section may have catalog IDs available but nothing material to say about them.)

Do NOT include `direction`, `confidence_score`, `expected_move_range_pct`, `final_call`, or any final prediction in `SECTION_AUDIT_PATH`.

After writing `SECTION_AUDIT_PATH`, complete Phases 1–4 against the full bundle and write `RESULT_PATH`.

**Suggested audit shape:**

```json
{
  "sections": [
    {
      "section": "Results & Expectations",
      "key_facts": [],
      "bullish_signals": [],
      "bearish_signals": [],
      "missing_or_unclear": [],
      "source_ids": []
    },
    {
      "section": "Forward Guidance",
      "key_facts": [],
      "bullish_signals": [],
      "bearish_signals": [],
      "missing_or_unclear": [],
      "source_ids": []
    }
  ]
}
```

---

## Hard constraints

- Do NOT change `prediction/result.json` schema.
- Do NOT add another LLM call.
- Do NOT let `section_audit.json` contain final direction, confidence, expected move, or final prediction.
- The final result must still be based on the full bundle, not only the audit.
- Raw bundle evidence overrides the audit if they conflict.
- The audit is a scratchpad, NOT a substitute for Phase 3 stress-testing.

## Why these constraints (do not relax without measuring)

- **Single LLM call** preserves holistic reasoning across all bundle sections in one extended-thinking pass. Splitting into multiple calls fragments the thinking budget and forces premature commitments on partial data.
- **Facts-only audit** prevents the model from anchoring to a directional call before it has stress-tested both sides. Classifying a fact under `bullish_signals` is a soft signal; writing "I lean long" is a hard commitment that biases later synthesis.
- **Forced coverage of every section §2–§9** is the entire point of the audit. Allowing the model to pre-decide a section is "not predictive" and skip it defeats the feature. The `not_material_reason` field is the only sanctioned escape: the entry must still exist.
- **Audit ≠ Phase 3** must be stated explicitly or the model will treat its bullish/bearish enumeration as if it had already done the adversarial pass, and Phase 3 silently shrinks to a tally. Bullet-counting is not stress-testing.

## Cross-cutting interactions verified (do NOT add defensive code for these)

The audit feature was traced end-to-end against `scripts/earnings/earnings_orchestrator.py`. The following interactions are correct as-is and require NO additional handling:

- **`finalize_prediction_result` (line 2209) has its own `if not result_path.exists()` check at line 2229.** This is redundant with the new central wrapper check (Step 7) for the orchestrator path, but is intentional defense-in-depth — `run_q3_from_existing_bundle.py` and other callers that finalize without going through the wrapper's check still benefit from it. Leave the finalize-side check in place.
- **`_render_and_harvest_best_effort` (line 2279) generates `result.md` sidecar + `thinking.md` harvest.** It is invoked only with `result_path` and never sees the audit. The audit is **intentionally not** given an `audit.md` sidecar or its own thinking harvest — it is raw JSON for model scratchpad / debug inspection. However, per Step 8, `result.md` does add a one-line cross-link to `section_audit.json` so Obsidian users can navigate from the prediction sidecar to the raw JSON. Do NOT extend this to a full `.md` rendering or add an `"audit"` key to `scripts/earnings/result_md_renderer.py`'s `dispatch` table at line ~536 (currently `{"prediction", "learning", "guidance", "prediction_no_lessons"}`) — even "harmless registration" of an audit handler is out of scope; only the cross-link in Step 8 is sanctioned.
- **Obsidian capture hooks (`.claude/hooks/obsidian_capture.{sh,py}`) are unaffected.** The hook is a `SubagentStop` event handler that processes the agent's transcript stream — it never reads or writes prediction artifact files. Line 20 of the hook explicitly skip-lists `{"earnings-prediction", "earnings-attribution", "earnings-learner"}`, and the audit feature does not change the predictor agent type. Existing tests (`test_obsidian_capture_adapter.py`, `test_obsidian_capture_hook_smoke.py`, `test_thinking_harvester.py`) continue to pass without modification.
- **The vault is `earnings-analysis/Companies/`** (verified symlink: `~/Obsidian/EventTrader/Earnings/earnings-analysis/Companies/`). New `section_audit.json` files appear in the vault automatically — no separate sync step. The Step 8 cross-link is the only code change needed for Obsidian users to discover them from `result.md`.
- **`scripts/earnings/builders/*` and `scripts/earnings/renderer/*` are completely uninvolved.** Builders construct the bundle JSON from data sources; the renderer turns bundle JSON into text. The audit is written by the LLM AFTER rendering, lives outside the bundle, and never round-trips through either layer. The renderer-golden hash test (`test_renderer_golden_full.py`) computes a SHA-256 of `render_bundle_text(bundle)` — bundle JSON is byte-identical pre/post-feature, so the hash is unchanged and the golden test continues to pass.
- **No production script auto-scans the `prediction/` directory for artifacts.** `migrate_unified_layout.py` iterates ticker/quarter dirs but acts only on specific filenames (`result.json`, `context_bundle.{json,txt}`); `calibrate_learner.py` constructs explicit paths; the obsidian capture adapter processes session messages, not filesystem artifacts. New `section_audit.json` files therefore introduce no auto-discovery side effects.
- **Test fixtures use literal `prompt_version` strings**, not computed SKILL.md hashes. Step 9's SKILL.md edit will bump the live `_hash_prompt_version()` output for new predictions, but no existing test asserts a specific hash value, so no test breaks.
- **Quarantine logic (line 2620–2629) renames `result.json` → `.json.rejected` on validation failure** but does not touch the audit. This is **intentional** — keeping the audit alongside the rejected result is exactly what is wanted for post-mortem debugging. Do NOT add audit quarantine logic.
- **`validate_prediction_result` (line 595) operates on the in-memory payload dict** — it does not touch the audit file at all. No validator-side change is needed for the audit.
- **The learner (`run_learner_for_quarter`, line 1065) reads only `prediction_result_path` (i.e., `result.json`)** at line 1132. It does NOT consume the audit. Audit-missing edge cases therefore do NOT propagate downstream into the learning pipeline — even on the `run_ab_baseline.py` resume branch where an audit might briefly be missing pre-migration.
- **`_atomic_write_json` (line 1297) is used by `finalize_prediction_result` for `result.json`** but the audit is written by the LLM via the SDK Write tool, not by this helper. Partial-write risk for the audit is bounded by the deferred-validator policy (parser validator can be added later if drift is observed).
- **`_hash_prompt_version` (line 2142) hashes `_PREDICTOR_SKILL_PATH`.** Step 9's edits to SKILL.md will bump this hash on next run — this is correct behavior (the prompt changed; the version should change). No action needed.
- **`_close_run` summary at line 2598** includes `thinking_path` but not `audit_path`. The audit is **intentionally not** added to the run-ledger summary — the ledger tracks high-level prediction outcomes, not debug scratchpads. Do NOT add audit_path to the ledger summary.

---

## Tests to update / add

- Extend `scripts/earnings/test_orchestrator_paths_u65.py` to assert `paths["section_audit_path"]` resolves under both `save_dir` and the canonical `Companies/.../events/{Q}/prediction/section_audit.json` layout.
- Refactor the SDK prompt construction in `_run_predictor_via_sdk` into a tiny pure helper `_build_predictor_prompt(bundle_path, rendered_path, section_audit_path, result_path) -> str` (one-line move, no behavior change), then unit-test that the returned string contains `f"SECTION_AUDIT_PATH={section_audit_path}"` and the new instruction line. This is the only safe way to assert prompt content without mocking the SDK.
- `run_predictor_via_sdk(...)` raises `RuntimeError` if either `section_audit.json` or `result.json` is missing after the SDK call (covers Step 7's central check).
- AST guard: parse each of the 5 caller files (use the Step 4 grep result as the source of truth), find every `Call` node where `func.id == "run_predictor_via_sdk"`, and assert each has exactly 4 positional arguments and 0 keyword arguments. This catches arity mismatches that a plain import smoke test would miss — Python checks function arity at call time, not at import time, so an under-arity call inside `main()` would import cleanly and only blow up when `main()` is actually invoked.
- `run_ab_baseline.py` resume guard: a unit test that constructs a baseline directory containing only `result.json` (no `section_audit.json`), invokes the resume predicate, and asserts the predictor IS called (resume does not fire). Conversely, with both files present, asserts the predictor is NOT called.
- **Orchestrator tuple-unpack AST guard** (closes the highest-impact silent-failure mode): scoped specifically to `scripts/earnings/earnings_orchestrator.py`, parse the file, find the `Call` node where `func.id == "run_predictor_via_sdk"`, walk up to its enclosing statement, and assert the statement is `ast.Assign` with a tuple target of length 2 (i.e., `_pred_result, predictor_session_id = run_predictor_via_sdk(...)`). The plain arity guard above passes both `f(a,b,c,d)` and `_p, _s = f(a,b,c,d)` — this test is what actually enforces the ⚠ CRITICAL warning in Step 5. Other callers (e.g., `run_q3_from_existing_bundle.py`) may still discard the tuple per their pre-existing pattern; only the orchestrator must unpack.
- **SKILL.md content sanity test**: read `.claude/skills/earnings-prediction/SKILL.md` and assert (a) a `## Phase 0.5 — Facts-Only Section Audit` heading exists at `##` level, NOT `####`; (b) Phase 0.5's heading appears between `## Phase 0 — Label Prior Lessons` and `## Reasoning` in file order; (c) `SECTION_AUDIT_PATH` is mentioned in the `## Input` section; (d) Phase 0.5's field list contains all 7 expected fields (`section`, `key_facts`, `bullish_signals`, `bearish_signals`, `missing_or_unclear`, `source_ids`, `not_material_reason`); (e) Phase 0.5 explicitly forbids `direction`, `confidence_score`, `expected_move_range_pct`, and `final_call`. For (d) and (e), extract only the Phase 0.5 block (from its `##` heading up to the next `## ` heading) before asserting; do not scan the whole SKILL.md, because result-schema terms like `direction` legitimately appear elsewhere. Without this test, a SKILL.md misedit (wrong heading level, wrong location, omitted field, broken Input prose) would silently corrupt every audit forever with no error signal — the model just produces malformed JSON that no validator catches per the deferred-validator policy.
- **Audit cross-link test** (Step 8 verification): extend `scripts/earnings/test_result_md_renderer.py`. Per render function (`render_prediction` and `render_baseline_experiment`), assert two cases: (a) when `section_audit.json` exists alongside `result.json`, the rendered `result.md` contains the substring `[section_audit.json](section_audit.json)`; (b) when the audit file does NOT exist, the rendered `result.md` does NOT contain that substring (backward compat for pre-feature predictions). Also assert `render_learning` and `render_guidance` outputs NEVER contain that substring regardless of audit presence.

---

## Deliberately deferred (do NOT add now)

These items were considered and intentionally excluded to keep the implementation minimal. They do not move accuracy today and would be bloat until production data justifies them. Add only if observed audit behavior across 20–30 events shows drift.

- Strict audit content validator (parse JSON, regex-block directional keys).
- Source_id catalog enforcement on audit entries.
- Controlled section-name vocabulary.
- `cross_section_tensions` field in audit.
- Audit ↔ evidence_ledger relationship clarification sentence.
- Full `audit.md` sidecar rendering (an `"audit"` key in `result_md_renderer.py`'s dispatch table). Step 8 ships only a one-line cross-link from `result.md` to the raw JSON; full markdown rendering of the audit content is intentionally out of scope. Re-evaluate only if Obsidian users report needing structured browsing of audit contents (per-section bullish/bearish bullets, etc.) that the raw JSON view doesn't satisfy.

If you find yourself wanting to add any of these "while you're in there," resist. Ship the minimum first.

---

## Expected complexity

~45–75 lines of Python across the 5 predictor-call files plus `result_md_renderer.py`, plus focused tests and the SKILL.md Phase 0.5 block. One pass, reversible.

---

## Definition of done

- All 5 callers updated to the 4-arg signature.
- Callers that delete stale `result.json` before rerun also delete stale `section_audit.json`.
- `run_predictor_via_sdk(...)` raises if either `section_audit.json` or `result.json` is missing after the SDK call.
- SKILL.md contains the Phase 0.5 block as written above.
- A live prediction run produces both `prediction/section_audit.json` and `prediction/result.json`.
- In production layout, `prediction/section_audit.json` is visible inside the Obsidian vault via the existing `earnings-analysis/Companies` symlink; no Obsidian hook or sync change is needed.
- `section_audit.json` contains entries for every numbered section §2–§9 present in the bundle (with `not_material_reason` for empty ones).
- `section_audit.json` does NOT contain `direction`, `confidence_score`, `expected_move_range_pct`, or `final_call`.
- `result.json` schema is unchanged from before.
- `result.md` rendered by `render_prediction` and `render_baseline_experiment` contains a `[section_audit.json](section_audit.json)` cross-link when the audit file exists alongside (Step 8). `render_learning` and `render_guidance` do NOT add this link.
- Obsidian capture hooks (`.claude/hooks/obsidian_capture.{sh,py}`) and `thinking_harvester.py` are NOT modified — verified by inspection that they have no interaction surface with the audit feature.
- Existing tests pass; new tests listed in "Tests to update / add" all pass.
