# Obsidian Thinking Capture — Standardization Plan

**Created**: 2026-04-17
**Status**: LOCKED — reviewed + empirically validated + cold-handoff spec'd. Ready for implementation (follow the "Build order" in the Implementation reference section)
**Scope**: Unified redesign of thinking capture + runtime artifact organization. Three real pipeline components (**guidance**, **prediction**, **learning**) plus their experimental variants land in per-component self-contained folders under `events/{Q}/`. Ships as **one implementation**. The only carve-out is the K8s extraction-worker auto-trigger for guidance, which needs a separate pod-rebuild + rollout.

**This plan supersedes the earlier Part 1 / Part 2 split.** Everything (thinking harvest + `sdk_session_id` + `result.md` sidecars + baseline flatten + `attribution/` → `learning/` rename + `context_bundle.json` promotion + `obsidian_capture.py` extraction-type subdirs + skip-list) goes in one cohesive change. The K8s guidance auto-trigger is a separate deploy step documented at the bottom. **The unified result envelope was dropped after review** — `sdk_session_id` is added as a top-level field on the existing flat payload; no envelope wrapping, no back-compat shim.

**Honest scope qualification** — the harvester + renderer + registry work for all three components on day one. For **prediction**, **learning**, and the **prediction_no_lessons** experiment, auto-trigger wiring lives inside the Python orchestrator and A/B scripts (in scope here). For **guidance**, the harvester is CLI-invokable day one (`python thinking_harvester.py guidance TICKER QUARTER SESSION_ID`); the auto-trigger inside the extraction-worker pod is a separate ~10-line change in a separate K8s rollout window (called out explicitly in the "Separate deploy step" section at the bottom).

---

## Pre-flight Verification Addendum (2026-04-17) — decisions locked pre-implementation

Before implementation, the plan was empirically verified against actual repo + vault state + live SDK. The verification produced several state-vs-plan gaps and decision points that are now locked into the spec below. **These supersede any conflicting detail in the sections that follow.**

**State findings (empirical)**:
- All 3 session-pattern fixtures verified — EMBED-visible (learner 17,682 thinking chars / 6 Agent + 0 Skill / 6/6 agentId linkage), EMBED-redacted (guidance 0 visible + 4 redacted with `signature` key / 2 Agent), FORK (predictor 177 primary meta-thinking + skill-fork 3,604 text chars / largest text 1,926 / 1 Skill + 0 Agent).
- **Zero `prediction/ab_baseline/` dirs exist** in the vault — all 15 quarters already have `events/{Q}/experiments/prediction_no_lessons/{result.json, context_bundle.json, context_bundle_rendered.txt}` in the canonical new location (A/B scripts were pre-updated). The plan's baseline-relocation steps therefore become conditional/idempotent no-ops today.
- **1,289** `pipeline/extractions/*_extraction_*.md` files exist (plan originally said 1,282); **6** anomalous `*_extraction-primary-agent_*.md` files exist from a bug-fallback path + `Extraction Runs.md` (manual note) + `.capture.log` (hook log).
- **No `__init__.py`** in `scripts/` or `scripts/earnings/` — they are NOT packages. All imports are top-level via `sys.path`.
- **SDK v0.1.61** exposes `.session_id` as a direct attribute on every message class (`AssistantMessage`, `ResultMessage`, `SessionMessage`, `SystemMessage.data`, `Task*Message`); `ResultMessage.session_id` is non-optional.
- **Skill-fork double-signal** — `meta.json.agentType == "general-purpose"` AND first-user starts with `"Base directory for this skill:"` — verified agreement 100% across fixtures (the predictor fork triggers both; all 8 non-fork subagents trigger neither).
- **POST-WIPE STATE (verified 2026-04-17 pre-implementation)** — another bot cleaned up most of the derived data. Current vault state:
  - `attribution/result.json`: **3 files only** (AVGO Q1/Q2/Q3 FY2023) — the other 12 `attribution/` dirs exist but are EMPTY.
  - `prediction/result.json`: **15 modern + 1 legacy stub**. The legacy stub is AVGO Q2_FY2024 (254 bytes, pre-schema, no `schema_version` key). AVGO Q3_FY2024 has no `prediction/result.json` at all.
  - `experiments/prediction_no_lessons/result.json`: **15** (unchanged across the wipe).
  - **2 AVGO legacy quarters** (Q2_FY2024, Q3_FY2024) have only `prediction/context.json` (old pre-learner filename, NOT `context_bundle.json`) — these are pre-learner-era artifacts and MUST be skipped by the migration.
  - `pipeline/extractions/`: intact — 1,289 conforming + 6 anomalous + `Extraction Runs.md` + `.capture.log`.
  - Session fixture JSONLs + subagent trees + meta.json files: ALL intact under `~/.claude/projects/-home-faisal-EventMarketDB/` (learner 6/6, guidance 2/2, predictor 1/1 meta-pair counts verified).
  - `learnings/` aggregate: `global.json` + `ticker/AVGO.json` only (no BURL.json, no NVDA.json).
  - **`learner-edits` plan is SHIPPED** — commits `ef1f907`, `a31d9ed`, `ca6a3c1`, `0ebb478`, `9627d38` are in `main`; `config/canonical_sectors.py` committed; working tree is clean on all learner-edits-touched files.

**Locked decisions**:

1. **Null-stamp coverage**: Migration stamps `sdk_session_id: null` on **all 45 historical `result.json` files** (15 prediction + 15 learning + 15 experiment), not just the 15 experiments. Consistency principle — every existing result.json gets the new field.
2. **Sidecar generation coverage**: Migration generates `result.md` for **all 45 historical result artifacts**, not just experiments. Renderer is already implemented; incremental cost is trivial; avoids asymmetric vault state where some quarters have human-readable md and others don't.
3. **Baseline relocate is idempotent**: If `events/{Q}/prediction/ab_baseline/` is absent (current reality for all 15 quarters), the script SKIPS the relocate steps for that quarter. No error, no manifest entry, no reverse action. If (future) a quarter has `ab_baseline/`, the move runs normally and is recorded for reverse.
4. **Reverse is manifest-driven only**: `--reverse` walks the `.migration-manifest.json` steps backward and inverts exactly what was applied. It does NOT reach into the filesystem to "restore" anything not recorded. Concretely: if an apply run skipped the baseline relocate for a quarter, `--reverse` does NOT recreate `prediction/ab_baseline/` for that quarter.
5. **Extractions migration scope**: Move ONLY files matching `{date}_extraction_{source_id}.md` into `pipeline/extractions/guidance/`. **LEAVE IN PLACE**: the 6 anomalous `*_extraction-primary-agent_*` files, `Extraction Runs.md`, and `.capture.log`.
6. **session_id capture is hybrid**: Use the simpler `getattr(msg, "session_id", None)` as the primary path (works against SDK v0.1.61 which exposes `.session_id` on every message type), **but retain** the `data.get("session_id") or data.get("sessionId")` fallback for SDK-version resilience. Both paths coexist; first non-None wins. Cost is ~3 lines; benefit is forward-compat.
7. **Skill-fork detection is dual-signal**: Primary = `meta.json.agentType == "general-purpose"` (cheap — one tiny JSON read). Confirmation = first-user content starts with `"Base directory for this skill:"`. Log a WARNING if the two signals disagree (indicates SDK behaviour drift — don't fail, just surface).
8. **Validator alias is absolute, not relative**: `scripts/earnings/validate_attribution.py` (the thin 1-release alias left behind after rename) uses `from validate_learning import *` — NOT `from .validate_learning import *`. Reason: `scripts/earnings/` has no `__init__.py`, so the relative form would silently fail; all existing imports already use the top-level absolute form via `sys.path`.
9. **All 3 A/B scripts get symmetric treatment**: `scripts/run_ab_baseline.py`, `scripts/run_nvda_ab_sequential.py`, `scripts/run_burl_ab_sequential.py` each receive the identical set of edits — `attribution/result.json` → `learning/result.json`, `prediction/context_bundle.{json,txt}` → quarter-root `context_bundle.{json,txt}`, capture `session_id` from `run_predictor_via_sdk` return tuple, post-baseline call to `thinking_harvester.harvest(thinking_type="prediction", experiment_name="prediction_no_lessons", ...)`. No script-specific branching.
10. **Manifest covers every created artifact**: Because decisions #1 + #2 generate 45 null-stamps and 45 result.md files (not 15 + 15), the manifest must record every one of those ops. `--reverse` then deletes each generated `result.md` and removes the `sdk_session_id` field from each stamped JSON. Schema is unchanged; coverage expands.

**Effective migration ops (locked)**:

| Op | Original plan count | **POST-WIPE REVISED count** | Note |
|---|---|---|---|
| `rename_dir attribution → learning` | 15 | **15** | All 15 quarters have `attribution/` dirs (12 are empty, 3 have result.json — the rename works on empty dirs too) |
| `rename_file prediction/context_bundle.* → <Q>/context_bundle.*` | 30 | **30** (15 × 2) | Only the 15 modern quarters with `context_bundle.json` are matched; the 2 AVGO legacy quarters (Q2/Q3 FY2024) with pre-schema `context.json` don't match the pattern and are naturally skipped |
| `rename_file ab_baseline/*_NO_LESSONS.* → experiments/prediction_no_lessons/*` | 0 (conditional) | **0** | `ab_baseline/` still absent across all quarters — no-op |
| `remove_dir_if_empty prediction/ab_baseline` | 0 (conditional) | **0** | Same condition |
| `stamp_null_session_id` | 45 | **33** | 15 prediction + **3** learning (only 3 quarters have learning/result.json; 12 learning/ dirs will be empty after rename) + 15 experiment. **EXCLUDES** the 1 legacy AVGO Q2_FY2024 prediction stub (pre-schema, no `schema_version` key) |
| `generate_result_md` | 45 | **33** | Same scope as null-stamp; skip legacy stubs via schema_version filter |
| `rename_file pipeline/extractions/{date}_extraction_{sid}.md → guidance/{date}_{sid}.md` | 1,289 | **1,289** | Unchanged — extractions dir intact |

**Migration script invariant**: pattern-matching is authoritative. The script never touches files that don't match the expected pattern. Specifically it MUST detect:
- `prediction/context_bundle.json` presence → promote (skips the 2 AVGO legacy quarters with only `prediction/context.json`)
- `schema_version == "prediction_result.v1"` in a result.json → eligible for null-stamp + md-render (skips the 1 AVGO Q2_FY2024 legacy stub)
- Empty directories still get renamed structurally (`attribution/` → `learning/` even when empty — keeps layout consistent)

Non-conforming files in `pipeline/extractions/` (6 anomalous + `Extraction Runs.md` + `.capture.log` = 8 items total) are left untouched. A/B scripts already write to `experiments/prediction_no_lessons/` directly; historical path no longer a hot path.

---

## Implementation (ships in one commit)

### Target layout (locked) — per-component self-contained folders

Every component and every experiment is ONE folder containing ALL its artifacts. No `thinking/` parent dir; no split between runtime and reasoning.

```
Companies/{TICKER}/events/{QUARTER}/
│
├── context_bundle.json                ← PROMOTED to quarter level (was under prediction/)
├── context_bundle_rendered.txt        ← PROMOTED to quarter level
│
├── guidance/
│   ├── result.json                    ← produced by K8s worker (auto-trigger in separate deploy)
│   ├── result.md                      ← autogenerated view
│   ├── thinking.md                    ← reasoning (harvester, from session transcript)
│   └── subagents/
│       └── {agent_type}_{short_id}.md
│
├── prediction/
│   ├── result.json                    ← machine canonical (+sdk_session_id field)
│   ├── result.md                      ← autogenerated view (read-only marker)
│   └── thinking.md                    ← reasoning sourced from skill-fork JSONL (FORK pattern — no data subagents)
│
├── learning/                          ← RENAMED from attribution/ in this commit
│   ├── result.json                    ← +sdk_session_id field
│   ├── result.md                      ← autogenerated view
│   ├── thinking.md                    ← reasoning
│   └── subagents/
│       └── {agent_type}_{short_id}.md
│
└── experiments/
    └── prediction_no_lessons/         ← FLATTENED from prediction/ab_baseline/
        ├── result.json                ← +sdk_session_id field; was result_NO_LESSONS.json
        ├── result.md                  ← autogenerated view
        ├── thinking.md                ← reasoning sourced from skill-fork JSONL (FORK pattern — no data subagents)
        ├── context_bundle.json        ← stripped input (learning_context blanked); was context_bundle_NO_LESSONS.json
        └── context_bundle_rendered.txt ← was context_bundle_rendered_NO_LESSONS.txt
```

**Key structural changes vs. today**:
- `attribution/` → `learning/` (path rename; affects every reader — see Files to Change for the full list)
- `context_bundle.{json,txt}` move from `prediction/` up one level to `events/{Q}/` (shared by all downstream components, predictor + learner + future readers)
- `prediction/ab_baseline/result_NO_LESSONS.json` → `experiments/prediction_no_lessons/result.json` (flatten)
- All `result.json` files gain a new top-level `sdk_session_id` field (flat addition — no envelope wrapping). Existing readers keep working unchanged; schema_version strings stay as-is for the component the file belongs to.
- Every `result.json` gains a deterministic `result.md` sidecar (read-only, autogenerated).
- New `thinking.md` in each component folder (Python-owned harvester). `subagents/` dir is emitted **only when the component spawned real `Agent`-tool Data SubAgents** — learner has it, guidance has it, predictor + experiments/prediction_no_lessons/ do NOT (skill-fork JSONL is the thinking source, not a sibling artifact).

### Why co-located (not under a `thinking/` parent)

| Concern | Co-located | Split `thinking/` parent (rejected) |
|---|---|---|
| "Where is everything about prediction?" | One folder: `prediction/` | Two folders: `prediction/` + `thinking/prediction.md` |
| Harvester path logic | `{component}/thinking.md` — trivial | `thinking/{component}.md` — extra path computation |
| Clean up a component | `rm -rf prediction/` removes everything | Must also clean up `thinking/prediction.md` + `thinking/subagents/prediction/` |
| Symmetry across components + experiments | Identical shape everywhere | Runtime + thinking use different parent dirs |
| Obsidian "browse by quarter" | Open any component dir → see reasoning + output + subagents | Traverse two dir trees |

**Guidance handling**: on day one of this commit, `events/{Q}/guidance/` can receive `thinking.md` + `subagents/` via CLI harvest. Auto-populate of `result.json` + `result.md` waits on the K8s extraction-worker rollout (see "Separate deploy step" at the bottom).

### Migration of old baseline files (handled by the migration script)

**Current reality (verified 2026-04-17 pre-flight)**: **zero** `events/{Q}/prediction/ab_baseline/` dirs exist. All 15 quarters already have the canonical `events/{Q}/experiments/prediction_no_lessons/{result.json, context_bundle.json, context_bundle_rendered.txt}` files (the A/B scripts were updated earlier to write to the new location directly). Baseline relocation is therefore **conditional and idempotent**: if `ab_baseline/` exists for a quarter, the migration moves it; otherwise the move steps are SKIPPED for that quarter and NOT recorded in the manifest (so `--reverse` cannot recreate `ab_baseline/` for a quarter the apply never touched).

The historical baseline JSONs are still useful audit artifacts; whenever they are present they migrate (not delete) so A/B history stays browseable.

| Historical baseline artifact | Migration result (conditional on source existence) |
|---|---|
| `prediction/ab_baseline/result_NO_LESSONS.json` | moved to `experiments/prediction_no_lessons/result.json` |
| `prediction/ab_baseline/context_bundle_NO_LESSONS.json` | moved to `experiments/prediction_no_lessons/context_bundle.json` |
| `prediction/ab_baseline/context_bundle_rendered_NO_LESSONS.txt` | moved to `experiments/prediction_no_lessons/context_bundle_rendered.txt` |
| Human-readable baseline view | generated as `experiments/prediction_no_lessons/result.md` (unconditional — generated for all 15 quarters whether the baseline was migrated now or pre-existed) |
| Missing `sdk_session_id` on any historical `result.json` | stamped as `null` during migration (unconditional across all 45 historical result files — see locked decision §1 in the pre-flight addendum above) |
| Historical reasoning transcript | **not** auto-harvested; can be re-harvested later only if a transcript can be matched confidently |

**Migration behavior** (performed by `scripts/migrate_unified_layout.py`, not a standalone `rm` command):
1. Create `events/{Q}/experiments/prediction_no_lessons/` if missing.
2. **If `prediction/ab_baseline/result_NO_LESSONS.json` exists**: move → `experiments/prediction_no_lessons/result.json`. Else skip + do not record in manifest.
2a. **If `prediction/ab_baseline/context_bundle_NO_LESSONS.json` exists**: move → `experiments/prediction_no_lessons/context_bundle.json` (strip `_NO_LESSONS` suffix — folder already encodes the variant). Else skip.
2b. **If `prediction/ab_baseline/context_bundle_rendered_NO_LESSONS.txt` exists**: move → `experiments/prediction_no_lessons/context_bundle_rendered.txt`. Else skip.
3. Stamp `sdk_session_id: null` on **every** historical `result.json` that lacks the field — covers all 15 `prediction/result.json`, all 15 `learning/result.json` (post-rename), and all 15 `experiments/prediction_no_lessons/result.json`. Total expected: up to 45 entries. Each stamp recorded in the manifest for reverse.
4. Generate `result.md` for **every** historical `result.json` — same 45-file scope as step 3 — using `result_md_renderer`. Each generate recorded in the manifest so `--reverse` can delete it.
5. **If** the legacy `prediction/ab_baseline/` dir is empty after the moves (step 2/2a/2b succeeded), remove it. Else skip.

Follow-up: update `.claude/plans/learner.md` Calibration Artifacts Index to reference the new canonical path (`events/{Q}/experiments/prediction_no_lessons/result.json`) for both future runs and the 15 migrated historical baseline artifacts.

### result.md sidecar pattern (new)

**Rule**: every review-surface `result.json` gets a deterministic autogenerated markdown sidecar. The JSON stays machine-canonical; the markdown is human-canonical for vault reading.

**Read-only marker** — every `result.md` opens with an explicit warning AND a frontmatter flag so both humans and Dataview can filter out autogenerated files:

```markdown
---
autogenerated: true
source: result.json
generator: scripts/earnings/result_md_renderer.py
component: prediction
ticker: BURL
quarter: Q4_FY2025
direction: long
confidence_score: 68
sdk_session_id: f128475b-...
---

<!--
⚠ AUTOGENERATED FROM result.json — DO NOT EDIT MANUALLY
Any manual edits will be overwritten on the next finalize_*_result() run.
To change content, update result.json (via the predictor/learner) or the
renderer itself at scripts/earnings/result_md_renderer.py.
-->

# Prediction — BURL Q4_FY2025

**Direction**: long @ confidence 68
**Expected move**: 2.0 – 5.5%
**Model**: claude-opus-4-7 (effort=xhigh)

## Key Drivers
1. …
2. …
```

The renderer is deterministic — same JSON produces identical MD. Regenerated on every `finalize_*_result()` call; manual edits are destroyed on next run by design. This is the file's contract, not a bug.

**Which artifacts get a sidecar**:

| Artifact | Sidecar? | Rationale |
|---|---|---|
| `prediction/result.json` | ✅ | Review surface — direction + drivers |
| `learning/result.json` | ✅ | Review surface — drivers, lessons, feedback (renamed from `attribution/`) |
| `experiments/prediction_no_lessons/result.json` | ✅ | A/B comparison needs human view |
| `guidance/result.json` | ✅ | Populated after K8s extraction-worker rollout (separate deploy step) |
| `context_bundle.json` | ❌ | Too large; `context_bundle_rendered.txt` already serves the human-review role |
| `ticker_lessons/*.json`, `global.json` | ❌ | Already human-readable short JSON; sidecar adds no value |

**Why co-located under `events/{QUARTER}/`**: one quarter container for everything. Every component folder holds its own `result.json` (when applicable) + `result.md` + `thinking.md` + `subagents/` — no separate `thinking/` parent, no split container shapes. `events/` is the existing production dir name; keeping it unchanged (vs renaming to `quarters/`) avoids a gratuitous rename that buys nothing.

**Components vs experiments — explicit**: the pipeline has exactly three real components — **guidance**, **prediction**, **learning**. Anything that is a *variant* of a component (lessons stripped, different model, different prompt) is not a sibling component; it is an experiment that lives under `experiments/`. Future variants slot in as `experiments/{parent_type}_{tag}/` (e.g. `experiments/prediction_opus_4_6/`, `experiments/learning_v2_prompt/`).

Component folder contents (`events/{Q}/{component}/`) materialize as needed: `result.json` + `result.md` when the component has a runtime artifact, `thinking.md` when the component session was captured, and `subagents/` **only if the component session spawned Agent-tool Data SubAgents** (learner + guidance) — **NOT** for FORK-pattern components (predictor + experiments/prediction_no_lessons/) whose skill-fork JSONL IS the thinking source. `experiments/` only appears when a variant was run.

**Readers relying on `events/{Q}/*/result.json` glob patterns** (current code uses explicit paths, not globs) will see the same shape as before plus new component dirs (`guidance/`, `learning/`, `experiments/`) — all with `result.json` inside. No breaking side effect for glob-based readers.

### Organizing principle (what lives where across the whole system)

Two-layer model, natural key determines home:

**Layer 1 — Raw operational capture (`pipeline/`)**: source-oriented, date-oriented, job-oriented. Extraction agents and similar per-source processes write here. These may or may not ever map to a specific earnings quarter — that's fine.

**Layer 2 — Canonical promoted artifacts (`Companies/{TICKER}/events/{QUARTER}/`)**: only material that is confidently bound to a specific ticker + quarter gets **promoted** up into the quarter container. Raw pipeline captures get linked by reference, never duplicated.

| Artifact shape | Natural key | Home | Example |
|---|---|---|---|
| Quarter-bound reasoning | `(ticker, quarter, component)` | `events/{Q}/{component}/thinking.md` (+ optional `subagents/` only when Agent-spawned Data SubAgents exist) | predictor/learner/guidance-summary thinking |
| Per-source raw extraction | `source_id` | `pipeline/extractions/{type}/{date}_{source_id}.md` | per-source-id × pass-type guidance captures |
| Cross-cutting extraction (spans tickers/quarters) | `source_id` / `article_id` | `pipeline/extractions/{type}/` only — no per-quarter home | news articles, macro events |

**Final rule (three lines)**:
1. If an artifact belongs to exactly one ticker + quarter + component → `events/{Q}/{component}/thinking.md` (or its component folder's sibling files).
2. If its true identity is a `source_id`, `article_id`, or similar extraction key → `pipeline/extractions/{type}/{date}_{id}.md`.
3. Quarter files MAY reference/link raw extraction artifacts; they MUST NOT duplicate the content.

Why this works:
- Easy quarter navigation for humans — one folder per (ticker, quarter) with links out to cited raw captures
- Easy archival/debugging for raw pipeline output — one folder per extraction type, flat by source_id
- No fake quarter assignment for news/macro artifacts
- No duplication; raw is the source of truth, quarter is a curated view

Filename simplification in `pipeline/extractions/{type}/`: since the folder already encodes the type, the filename drops redundant words. `{date}_extraction_{source_id}.md` → `{date}_{source_id}.md`. Applied in this commit alongside the extraction-type-subdir rework.

### Current layout vs. after this commit (side-by-side)

```
=== CURRENT ===                             === AFTER UNIFIED COMMIT ===
events/{Q}/                                 events/{Q}/
  prediction/                                 context_bundle.json         ← PROMOTED up one level
    result.json                               context_bundle_rendered.txt ← PROMOTED
    context_bundle.json                       guidance/                   ← NEW component folder
    context_bundle_rendered.txt                 result.json               ← (populated after K8s rollout)
    ab_baseline/                                result.md                 ← autogen view
      result_NO_LESSONS.json                    thinking.md               ← reasoning
                                                subagents/
  attribution/                                prediction/                   ← FORK pattern: no subagents/
    result.json                                 result.json               (+sdk_session_id field)
                                                result.md                 ← autogen view
                                                thinking.md               ← sourced from skill-fork JSONL
                                              learning/                   ← RENAMED from attribution/ (EMBED: has subagents/)
                                                result.json               (+sdk_session_id field)
                                                result.md
                                                thinking.md
                                                subagents/
                                              experiments/                ← FLATTENED from ab_baseline/
                                                prediction_no_lessons/    ← FORK: no subagents/
                                                  result.json             (+sdk_session_id field)
                                                  result.md
                                                  thinking.md             ← sourced from skill-fork JSONL

pipeline/extractions/*.md (flat)            pipeline/extractions/        ← TYPE-SHARDED
                                                guidance/
                                                news/   (placeholder dir; fills when news extraction wires up)
                                                risk/   (placeholder)
                                              (filenames simplified: {date}_extraction_{sid}.md → {date}_{sid}.md)
agents/*.md (raw SubagentStop)              agents/*.md                   (unchanged)
                                              obsidian_capture.py SKIPS earnings-prediction / attribution /
                                              learner agent types — harvester owns those now
```

**One-shot migration covers** (exact ops + today's counts per locked decisions in the pre-flight addendum):
- Rename `events/{Q}/attribution/` → `events/{Q}/learning/` for all **15** existing quarters
- Move `events/{Q}/prediction/context_bundle.{json,txt}` → `events/{Q}/context_bundle.{json,txt}` (30 files across 15 quarters)
- **Conditional** baseline relocation — for any quarter where `events/{Q}/prediction/ab_baseline/` exists, move its 3 `*_NO_LESSONS.*` files → `events/{Q}/experiments/prediction_no_lessons/*` (strip `_NO_LESSONS`), then remove the empty `ab_baseline/` dir. **Today's count: 0** (all quarters already have the canonical experiment path in place; these ops are idempotent no-ops and are NOT recorded in the manifest).
- Stamp `sdk_session_id: null` on **all 45** historical `result.json` files that lack the field (15 prediction + 15 learning + 15 experiment). Every stamp recorded in the manifest.
- Generate `result.md` via `result_md_renderer` for **all 45** historical `result.json` files. Every generate recorded in the manifest.
- Move `pipeline/extractions/{date}_extraction_{source_id}.md` → `pipeline/extractions/guidance/{date}_{source_id}.md` — **1,289** conforming files. **Leave in place**: 6 anomalous `{date}_extraction-primary-agent_{agent_id8}.md` files (older hook-fallback naming), `Extraction Runs.md` (manual Obsidian note), `.capture.log` (hook append log). Total non-conforming = 8 items (6 + 1 + 1).

### Files I will add (7 files after two rounds of consolidation — merged `thinking_types.py` + `result_envelope.py` into `pipeline_contracts.py`; dropped `test_pipeline_contracts.py` with its assertions absorbed into `test_thinking_harvester.py`)

| File | ~Lines | Purpose |
|---|---|---|
| `config/pipeline_contracts.py` | ~30 | Minimal registry + helper: (1) `KNOWN_TYPES = {"guidance","prediction","learning"}`, (2) `validate_experiment_name()` enforcing `{parent_type}_{tag}` prefix. No envelope schema — the envelope was dropped; `sdk_session_id` is added as a flat top-level field on each existing `result.json`. |
_(`config/test_pipeline_contracts.py` REMOVED after over-engineering audit — testing a 30-line module of "a set + a 5-line validator" is marginal value. The 3 tiny registry assertions fold into `test_thinking_harvester.py` instead: `test_registry_has_three_types`, `test_experiment_name_requires_prefix`, `test_unknown_type_rejected`.)_
| `scripts/earnings/thinking_harvester.py` | ~220 | Single `harvest(thinking_type, ticker, quarter, session_id, experiment_name=None)` function + CLI. Uses `thinking_blocks.py` for parsing. **Handles 3 empirically-verified patterns**: (1) **EMBED-visible** (learner): primary session JSONL has rich visible thinking + Agent-tool-spawned Data SubAgents; (2) **EMBED-with-redacted-thinking** (guidance via `/extract`): primary has `type=thinking` blocks with `signature` field + empty content (not a distinct block type — harvester detects via `block["type"]=="thinking" AND not block.get("thinking","") AND "signature" in block`, emits `"content redacted (signed)"` marker, falls back to text blocks); (3) **FORK** (predictor via `Run /earnings-prediction`): primary has `Skill` tool_use + 1 skill-fork JSONL; reasoning lives in text blocks. **Scans for BOTH `Agent` and `Skill` tool_use in primary** (never `Task`). **Linkage strategy — direct `agentId`**: for each Agent tool_use in primary, find the corresponding `tool_result` entry and read top-level `toolUseResult.agentId` on the JSONL entry (6/6 learner + 2/2 guidance sessions cross-checked — 100% correct). Replaces brittle order/prompt schemes (alphavantage rate-limit completed 1st despite spawning 4th; guidance prompts identical across subagents). **Skill-fork detection (dual-signal — per locked decision §7 in the pre-flight addendum)**: primary signal = subagent's sidecar `agent-<id>.meta.json` has `agentType == "general-purpose"` (cheap one-JSON-read); confirmation signal = subagent JSONL's first-user content starts with `"Base directory for this skill:"`. Both signals verified 100% agreement across all fixtures (the single predictor fork triggers both; the 8 non-fork subagents in learner + guidance trigger neither). **Log a WARNING if the two signals disagree** (do NOT fail — surfaces SDK behaviour drift). The detected skill-fork JSONL is the content source for thinking.md; any OTHER subagent JSONL in the same session is an Agent-spawned sibling and goes into `subagents/`. **Degraded cases**: if an Agent tool_use has no matching tool_result (spawn crash / rate-limit before return), emit WARNING in thinking.md (`"Agent spawn with subagent_type=X had no tool_result"`) and skip; harvester never crashes on missing linkage. Output: `subagents/` dir ONLY materializes when real Agent-spawned Data SubAgents exist (learner, guidance, or FORK-with-nested-Agents). Subagent JSONLs land FLAT at `<session>/subagents/agent-*.jsonl`. Subagent output filenames: `{subagent_type}_{agent_id[:8]}.md` (first 8 chars of agentId — deterministic, human-short, no collisions). `subagent_type` is resolved from three interchangeable sources that empirically agree: (a) primary tool_use `input.subagent_type`, (b) primary `toolUseResult.agentType`, (c) subagent `meta.json.agentType` — the harvester prefers (c) as most localized. **`thinking.md` composition**: thinking blocks + text blocks + abbreviated tool_use annotations (one line each, e.g. `🔧 Read(path/to/file)`, `🔧 Agent(neo4j-news)`) in session-timestamp order. Full tool_use input + tool_result content go to subagents/*.md traces, not thinking.md. **`thinking.md` frontmatter** is self-describing: `component`, `ticker`, `quarter`, `sdk_session_id`, `session_pattern` (EMBED-visible / EMBED-redacted / FORK), `thinking_blocks`, `thinking_chars`, `redacted_thinking_blocks`, `subagents_count`, `generated_at`, `harvester_version: v1`. **For experiments**, `component` holds the PARENT component name (e.g. `prediction`) and a separate `experiment_name` field holds the variant tag (e.g. `prediction_no_lessons`) — this lets Dataview filter "all prediction artifacts including experiments" via `component: prediction`, while still distinguishing variants. For non-experiment components `experiment_name` is omitted (or `null`). |
| `scripts/earnings/thinking_blocks.py` | ~60 | Shared block-parser extracted from `obsidian_capture.py` so hook + harvester use one code path. Zero behaviour change for the hook. |
| `scripts/earnings/test_thinking_harvester.py` | ~130 | Fixture-based tests covering all 3 verified patterns: (a) EMBED-visible (learner fixture): primary thinking block count + chars + Agent-spawned subagents discovered via top-level `toolUseResult.agentId` on the JSONL entry lookup + labeled by `subagent_type`, (b) EMBED-with-redacted-thinking (guidance fixture): primary has `type=thinking` blocks with empty content + `signature` key → harvester emits "content redacted (signed)" marker + falls back to text blocks, (c) FORK (predictor fixture): `Skill` tool_use in primary → skill-fork JSONL becomes thinking.md source + NO `subagents/` dir emitted (skill-fork is the thinking source, not a sibling), (d) **`agentId` linkage is load-bearing**: fixture with completion order ≠ spawn order (simulating alphavantage rate-limit fast-fail) — asserts direct agentId lookup still labels each subagent correctly, where order-based matching would mislabel, (e) experiment routing writes to `experiments/{name}/` not `{name}/`, (f) idempotent re-harvest (overwrites cleanly), (g) missing-session-id WARNING, (h) predictor fixture produces NO `subagents/` dir, **plus three small registry assertions absorbed from the dropped `config/test_pipeline_contracts.py`**: (i) `KNOWN_TYPES == {"guidance","prediction","learning"}`, (j) `validate_experiment_name("prediction", "prediction_no_lessons")` accepts, (k) `validate_experiment_name("prediction", "learning_variant")` rejects. Fixtures: trimmed copies of real SDK session JSONLs (BURL Q4_FY2025 learner + BURL guidance extract + BURL Q4 predictor) so tests exercise the exact block shapes the harvester will see in production. |
| `scripts/earnings/result_md_renderer.py` | ~100 | Pure JSON→MD renderer. Four render functions: `render_prediction`, `render_learning`, `render_baseline_experiment`, **and `render_guidance` (implemented now, even though guidance runtime artifact lands with the K8s deploy step)** — so when the K8s worker is updated it can `from result_md_renderer import render_guidance` without needing another repo change. `render_guidance` uses the same frontmatter + read-only marker + rendered-table pattern as the others, tolerating a generic/minimal `guidance/result.json` shape (Neo4j-denormalized summary). Returns deterministic markdown. |
| `scripts/earnings/test_result_md_renderer.py` | ~50 | Golden-output tests: fixture JSON → expected MD. Determinism, read-only marker, frontmatter shape, Dataview-queryable fields. |
| `scripts/migrate_unified_layout.py` | ~160 | **One-shot atomic migration** with `--dry-run`, `--apply`, and `--reverse` modes, writing a `.migration-manifest.json` recording every action for reverse-playback (manifest-driven reverse — see Rollback plan). Each step uses `os.rename` (atomic same-filesystem move); a mid-run failure halts the script, leaves partial state visible, and prints the remaining steps. Handles: (a) `attribution/` → `learning/` rename per quarter (15 unconditional), (b) `prediction/context_bundle.*` → `events/{Q}/context_bundle.*` (30 unconditional), (c) **CONDITIONAL** — for any quarter where `prediction/ab_baseline/` exists, move its three `*_NO_LESSONS.{json,txt}` files → `events/{Q}/experiments/prediction_no_lessons/*` with `_NO_LESSONS` suffix dropped, then remove the empty legacy `ab_baseline/` dir. If absent for a quarter (today's state for all 15), skip silently + record nothing. (d) Stamp `sdk_session_id: null` on **every** historical `result.json` that lacks the field — 15 prediction + 15 learning + 15 experiment = 45 entries (each recorded). (e) Generate `result.md` via `result_md_renderer` for **all 45** historical `result.json` files (each recorded). (f) `pipeline/extractions/{date}_extraction_{sid}.md` → `pipeline/extractions/guidance/{date}_{sid}.md` for **1,289 conforming files only** — pattern match required; **leave in place** the 6 anomalous `{date}_extraction-primary-agent_{aid8}.md` files, `Extraction Runs.md`, and `.capture.log` (8 non-conforming items total). Idempotent — skips already-migrated paths; skips files matching new-path pattern on re-run. Short_ids for subagent filenames use first 8 chars of the agentId (deterministic). Run once after commit with `--dry-run` first; inspect output; then `--apply`. |

**Dropped from the plan** (file-count hygiene):
- `config/thinking_types.py` + `config/result_envelope.py` → collapsed into `config/pipeline_contracts.py` (30 lines), and the envelope itself dropped after review (zero concrete benefit, real back-compat cost). `sdk_session_id` is now just a flat top-level field on each `result.json`.
- `scripts/backfill_thinking.py` → dropped. Predates-sdk_session_id backfill adds complexity for dubious value (the 15 A/B quarters don't have session IDs stamped at write time; post-hoc matching is fuzzy). Add later if ever needed as ~30 lines.

### Files I will change (comprehensive — per consumer audit)

**Production code (must update, blocks commit if missed):**

| File | Change |
|---|---|
| `scripts/earnings/earnings_orchestrator.py` | (a) Capture `session_id` in `_run_predictor_via_sdk()` + `_run_learner_via_sdk()` with defensive key lookup. (b) Add `finalize_learning_result()` (rename of `finalize_attribution_result`; old name kept as a thin alias for 1 release). Both finalizers accept `sdk_session_id` and stamp it as a top-level field on the existing flat payload, write `result.json` + `result.md` via `result_md_renderer`, then call `thinking_harvester.harvest()` — all in try/except so harvest/renderer failures don't block the write. (c) Update every `attribution/` path → `learning/`. (d) Promote `context_bundle.{json,txt}` writes from `prediction/` → quarter root. |
| `scripts/run_ab_baseline.py` | **Symmetric edits with the other two A/B scripts** (per locked decision §9 in the pre-flight addendum — no script-specific branching). Five changes: (1) attribution result read path: `events/{Q}/attribution/result.json` → `events/{Q}/learning/result.json`; (2) context_bundle source path: `pred_dir / "context_bundle.json"` → `ev_dir / "context_bundle.json"` (quarter root); (3) baseline write path already `events/{Q}/experiments/prediction_no_lessons/result.json` — no change; (4) capture `session_id` from the new `(result, session_id)` tuple returned by `run_predictor_via_sdk`; (5) post-baseline call `thinking_harvester.harvest(thinking_type="prediction", experiment_name="prediction_no_lessons", ticker=T, quarter=Q, session_id=sid)` in a try/except WARNING block. Also update `strip_learning_context()` helper's source path to quarter root. |
| `scripts/run_nvda_ab_sequential.py` | **Identical 5-change edit set to `run_ab_baseline.py` above.** Ticker variable is NVDA; logic is identical. |
| `scripts/run_burl_ab_sequential.py` | **Identical 5-change edit set to `run_ab_baseline.py` above.** Ticker variable is BURL; logic is identical. |
| `scripts/earnings/validate_attribution.py` → `validate_learning.py` | **MODULE rename only — function name `validate_attribution_result` stays unchanged** (it maps to schema `attribution_result.v2`, which also stays per the "schema_version strings stay as-is" rule). Payload shape unchanged (flat); validator just gets path + docstring updates. **Thin alias at the old module name for 1 release — must use ABSOLUTE import, not package-relative** (per locked decision §8 in the pre-flight addendum): the alias file content is exactly `from validate_learning import *  # noqa: F401,F403 — 1-release alias; scripts/earnings/ has no __init__.py so relative form would silently fail`. The `*` re-export preserves the unchanged `validate_attribution_result` symbol, so existing callers `from validate_attribution import validate_attribution_result` (orchestrator + hook + tests) continue to work unchanged. The hook's import line becomes `from validate_learning import validate_attribution_result` (module changed, function unchanged). |
| `.claude/hooks/validate_attribution_output.py` → `validate_learning_output.py` | Rename. `.claude/settings.json` hook path updated. |
| `.claude/hooks/obsidian_capture.py` | (a) FOLDER_ROUTING → `pipeline/extractions/{guidance,news,risk}/` type-sharded. (b) Skip-list for `earnings-prediction`/`earnings-attribution`/`earnings-learner` agent types (harvester owns them now). (c) Filename: drop `_extraction_` segment. (d) Import shared block-parser from `scripts/earnings/thinking_blocks.py`. |
| `.claude/settings.json` | Hook command path updated for `validate_learning_output.py` rename. |

**Skills (must update — prompt contracts consumed at runtime):**

| File | Change |
|---|---|
| `.claude/skills/earnings-learner/SKILL.md` | `attribution/result.json` → `learning/result.json`. `events/{Q}/prediction/context_bundle.*` → `events/{Q}/context_bundle.*`. |
| `.claude/skills/earnings-prediction/SKILL.md` | Same `context_bundle.*` path promotion. |
| `.claude/skills/earnings-orchestrator/SKILL.md` | `attribution/` references → `learning/`; `context_bundle.*` promotion. |
| `.claude/skills/FLOW.md` | `attribution/` refs → `learning/`. |

**Plan docs (maintained reference material; must update):**

> **Sweep discipline for all 12 plan docs below** — the phrase "`attribution/` sweep" in this table means **update path literals only** (e.g., `events/{Q}/attribution/` → `events/{Q}/learning/`, `attribution/result.json` → `learning/result.json`, any filesystem-shaped reference to an `attribution/` directory). **Leave prose mentions of "attribution" as a concept unchanged** — "causal attribution", "return attribution", "attribution analysis", and similar domain-language uses describe the *financial analysis activity*, not the folder, and must be preserved. Same rule for `context_bundle.*` rows: update path references (`prediction/context_bundle.json` → `context_bundle.json` at quarter root) but don't rewrite prose that happens to mention "context bundle" as a concept. When in doubt, re-read the full sentence: if it describes the old folder structure, update it; if it describes the analytical concept, leave it.

| File | Change |
|---|---|
| `.claude/plans/learner.md` | Update `attribution/` path literals → `learning/` (prose about causal attribution untouched). Calibration Artifacts Index: baseline paths → `experiments/prediction_no_lessons/`. Note: 15 existing quarters' baseline JSONs migrated to the canonical experiment path. |
| `.claude/plans/earnings-orchestrator.md` | Same path-literal sweep (`attribution/` → `learning/`) + `context_bundle.*` path promotion to quarter root. Prose mentions of attribution-as-concept left alone. |
| `.claude/plans/planner.md` | Path-literal sweep (`attribution/` → `learning/`) + `context_bundle.*` promotion. Prose untouched. |
| `.claude/plans/predictor-revamp.md` | `context_bundle.*` path-literal promotion to quarter root. |
| `.claude/plans/prediction-system-v2.md` | Path-literal sweep (`attribution/` → `learning/`) + `context_bundle.*` promotion. Prose untouched. |
| `.claude/plans/Infrastructure.md` | Path-literal sweep (`attribution/` → `learning/`). Prose untouched. |
| `.claude/plans/EarningsTrigger.md` | Path-literal sweep (`attribution/` → `learning/`). Prose untouched. |
| `.claude/plans/trade-execution-system.md` | Path-literal sweep (`attribution/` → `learning/`) + `context_bundle.*` promotion. Prose untouched. |
| `.claude/plans/DataSubAgents.md` | Path-literal sweep (`attribution/` → `learning/`). Prose untouched. |
| `.claude/shared/earnings/subagent-history.md` | Path-literal sweep (`attribution/` → `learning/`). Prose untouched. |
| `.claude/filters/GAP_ANALYSIS.md` | Path-literal sweep (`attribution/` → `learning/`). Prose untouched. |
| `docs/claude/skills-reference.md` | Path-literal sweep (`attribution/` → `learning/`). Prose untouched. |

**Explicitly NOT touched (historical / ephemeral):**

| Path | Reason |
|---|---|
| `.claude/plans/done_fixes/*` | Historical incident records — document what happened at the time. Leaving old paths is correct. |
| `earnings-analysis/test-outputs/onepager-*.md` | Ephemeral test outputs. Not worth editing. |
| Anthropic SDK / Claude Code CLI / MCP servers | External; not part of this commit. |
| K8s extraction-worker pod image | Separate deploy step (see "Separate deploy step" section). |

_(Earlier drafts accidentally listed the three A/B scripts + `thinking_blocks.py` helper here — corrected; they are in the Files-to-change and Files-to-add tables respectively.)_

**What's explicitly NOT touched in this commit**: the K8s extraction-worker pod image (separate deploy step) and `result.json` payload schemas beyond adding the flat `sdk_session_id` field + the `attribution` → `learning` path-component rename. `obsidian_capture.py`, validators, SKILL.md files, `settings.json` hook paths, and plan docs ARE edited (comprehensively) — see the Files I will change table above. MCP servers are untouched.

### sdk_session_id flow

1. **Capture (hybrid — per locked decision §6 in the pre-flight addendum)** — in `_run_predictor_via_sdk()` / `_run_learner_via_sdk()`. **Primary path**: `getattr(msg, "session_id", None)` — empirically verified on SDK v0.1.61, every message class (`AssistantMessage`, `ResultMessage`, `SessionMessage`, `SystemMessage`, `Task*Message`) exposes `.session_id` as a direct attribute; `ResultMessage.session_id` is non-optional. **Fallback path**: the older `subtype="init"` + `data.get("session_id") or data.get("sessionId")` branch, preserved for SDK-version resilience. First non-None wins; either path is sufficient on its own.
   ```python
   session_id: str | None = None
   async for msg in query(prompt=prompt, options=options):
       # Primary: direct attribute (SDK ≥ 0.1.61 — all message classes expose it)
       if session_id is None:
           session_id = getattr(msg, "session_id", None) or getattr(msg, "sessionId", None)
       # Fallback: init-subtype SystemMessage with data dict (older SDK shapes)
       if session_id is None and getattr(msg, "subtype", "") == "init":
           data = getattr(msg, "data", {}) or {}
           session_id = data.get("session_id") or data.get("sessionId")
       # existing handling…
   return final_result, session_id
   ```
   The harvester treats missing session_id as a WARNING (not failure) — write remains non-blocking.

2. **Stamp** — `finalize_prediction_result(..., sdk_session_id=session_id)` writes `payload["sdk_session_id"] = session_id` as a top-level field (flat, no envelope). Same pattern in `finalize_learning_result()` (renamed from `finalize_attribution_result`; old name kept as a thin alias for 1 release). Field is optional in schema — existing readers that don't know about it just ignore it.

3. **Use (live)** — orchestrator calls `harvest(type, ticker, quarter, session_id)` immediately after finalize. Harvester opens `~/.claude/projects/-home-faisal-EventMarketDB/{session_id}.jsonl`, extracts primary thinking blocks (detects redacted-thinking case: `type=thinking` + empty content + `signature` field → emit "content redacted (signed)" marker, keep block in count), text, and tool_use blocks. It detects pattern via tool presence: `Skill` tool_use → FORK (skill-fork JSONL is the thinking.md source; NO subagents/ dir emitted); else `Agent` tool_use → EMBED (primary is thinking.md source, Agent subagents go into `subagents/`). For EMBED linkage: for each Agent tool_use, scan forward in the transcript for the matching `tool_result` and read top-level `toolUseResult.agentId` on the JSONL entry — that agentId maps directly to the subagent JSONL filename (`agent-<agentId>.jsonl`). This is O(1) lookup, empirically verified 100% correct (6/6 learner + 2/2 guidance). For each subagent, extracts execution trace (text + tool_use + tool_result; thinking usually absent per empirical data). Writes primary's reasoning (thinking + text blocks merged) to `{component}/thinking.md`. For FORK: thinking.md sources from the skill fork's text + thinking blocks (empirically text-heavy — the predictor's ~1,900-char walkthrough lives in a text block, not a thinking block).

4. **Use (re-harvest)** — the harvester CLI accepts `(thinking_type, ticker, quarter, session_id)` directly, so any future re-harvest just reads `sdk_session_id` from the relevant `result.json` and calls the CLI. No dedicated `backfill_thinking.py` needed; no scanning, no fuzzy matching.

### How all three components + experiments use the same shared system

Every call goes through the same shape. Components pass `thinking_type`; experiments pass `thinking_type` AND `experiment_name`:

```python
# Post-finalize in each callsite — COMPONENTS:
thinking_harvester.harvest(thinking_type="guidance",   ticker=T, quarter=Q, session_id=sid)
thinking_harvester.harvest(thinking_type="prediction", ticker=T, quarter=Q, session_id=sid)
thinking_harvester.harvest(thinking_type="learning",   ticker=T, quarter=Q, session_id=sid)

# Post-finalize in A/B baseline callsite — EXPERIMENT:
thinking_harvester.harvest(
    thinking_type="prediction",              # parent component
    experiment_name="prediction_no_lessons", # variant tag; routes to experiments/
    ticker=T, quarter=Q, session_id=sid,
)
```

Harvester routes by presence of `experiment_name`:
- `None` → `events/{Q}/{thinking_type}/thinking.md` + `events/{Q}/{thinking_type}/subagents/*` **only if** that component session actually spawned real Agent-tool Data SubAgents (learner + guidance — both EMBED with Agent children). For FORK-pattern components (predictor today), emits `thinking.md` only; no `subagents/` dir.
- set (experiment) → `events/{Q}/experiments/{experiment_name}/thinking.md` + `events/{Q}/experiments/{experiment_name}/subagents/*` **only if** that experiment session actually spawned Agent-tool Data SubAgents. For FORK-pattern experiments (`prediction_no_lessons` today), emits `thinking.md` only; no `subagents/` dir.

Validation: `experiment_name` MUST start with `{thinking_type}_` to keep it traceable to its parent component. Adding a new component later = add the name to `KNOWN_TYPES` + one `harvest(...)` call at the new pipeline's finalize site. Adding a new experimental variant = no code change at all; just call `harvest()` with a fresh `experiment_name`. No architectural change either way.

**Guidance** is the one caller outside `earnings_orchestrator.py`. It lives in the extraction-worker (K8s). This commit ships the harvester + CLI; the ~10-line auto-trigger inside the worker pod is a separate deploy step (see "Separate deploy step" at the bottom). Worker rebuild + `kubectl rollout restart` is a different risk profile from a Python-only repo commit, so it stays out-of-band.

---

## Inspections (done in this session) and write-path verification

### Inspection results (already acted on in this session)

| Path | Finding | Status |
|---|---|---|
| `Companies/helper.md` | Jan 29 reference doc for `get_earnings.py` + `news_processed.csv`. Zero code refs to it. | **Deleted** (confirmed obsolete) |
| `claude-logs/` | 5 POC scratch files from 2026-03-09. `cli-test.md`, `proof-cli-exists.md`, etc. | **Deleted** |
| `test-folder/` | Empty. | **Deleted** |
| `Companies/AAPL/` | 72 KB Feb-2026 early exploratory. Has `events/Q1_FY2024/{prediction,attribution}/` + `learnings.md`. | **Deleted** (approved) |
| `Companies/CCL/` | Apr-2 incomplete run (only prediction, no attribution). | **Deleted** (approved) |
| `Companies/CRM/` | Mar-30 with bug-shaped accession-as-quarter subdir. | **Deleted** (approved) |
| `Companies/DOCU/` | Aborted run (no result.json). | **Deleted** (approved) |
| `Companies/TEST/` | Empty. | **Deleted** |

### Write-path verification (verified directly this session)

| Concern | Finding |
|---|---|
| Symlink: `earnings-analysis/Companies/` | `→ /home/faisal/Obsidian/EventTrader/Earnings/earnings-analysis/Companies` — writes through to vault |
| Vault is git-backed? | **No** — `git rev-parse` returns fatal at every level under `/home/faisal/Obsidian` |
| Cloud-sync mounts (Dropbox/iCloud/OneDrive)? | **None** — regular Linux filesystem (inode 29643692) |
| Obsidian app file locks? | **No files open** in workspace.json; safe to write |
| MCP Obsidian server | Running (PID 387320) — read/write adapter, no lock semantics |
| **Syncthing** | **ACTIVE**: folder id `p5w6c-x2227`, `sendreceive` type, `fsWatcherEnabled=true`, `fsWatcherDelayS=10`. `/home/faisal/Obsidian` is paired with whatever peers you have. |

**Concrete risks flagged**:
1. **Syncthing deletion propagation** — any `rm` we do propagates to paired devices within ~10s. Already relevant to the cleanup we've done. No way around it except pausing peers.
2. **No write contention** — harvester produces ≤6 small markdown files per quarter (rate: one batch per learner run, ~once per 10-14 min). Syncthing handles this volume trivially.
3. **Obsidian Dataview plugin** is enabled but no active queries left after our cleanup — won't conflict.

Net: write path is safe. No hidden gotchas.

---

## Acceptance checks

Run a fresh BURL Q4_FY2025 end-to-end after implementation, verify:

1. `earnings-analysis/Companies/BURL/events/Q4_FY2025/prediction/result.json` contains a `sdk_session_id` field that matches an existing `~/.claude/projects/.../{sid}.jsonl`.
2. Same for `events/Q4_FY2025/learning/result.json` (renamed from `attribution/` in this commit).
3. Same for `events/Q4_FY2025/experiments/prediction_no_lessons/result.json` (new flattened path).
3a. `result.md` sidecar exists next to each of the three `result.json` files above, with (i) the `⚠ AUTOGENERATED` marker comment, (ii) `autogenerated: true` frontmatter, (iii) frontmatter fields matching the JSON (direction, confidence_score, sdk_session_id).
3b. A known historical baseline quarter, e.g. `Companies/BURL/events/Q1_FY2025/experiments/prediction_no_lessons/result.json`, exists after migration with the original prediction fields preserved, `sdk_session_id: null` stamped. **Reality today: these files already exist in the canonical new location** (no `ab_baseline/` dir to remove); the migration only null-stamps + md-renders them. If a future apply run encounters a quarter with `prediction/ab_baseline/`, that quarter's `ab_baseline/` is removed after the move.
3c. The same quarter's `experiments/prediction_no_lessons/context_bundle.json` AND `experiments/prediction_no_lessons/context_bundle_rendered.txt` both exist. **Reality today: these were written directly to the canonical path by the A/B scripts; migration touches neither.** (If a future quarter has legacy `ab_baseline/*_NO_LESSONS.*` files, migration moves them with `_NO_LESSONS` suffix stripped; verify content unchanged.)
3d. **Null-stamp coverage (per locked decision §1, REVISED post-wipe)**: all **33** historical `result.json` files that exist and match schema (15 modern `prediction/` + 3 `learning/` + 15 `experiments/prediction_no_lessons/`) have the `sdk_session_id` field present, value either a valid session id (from subsequent live runs) or `null` (from migration). The 1 legacy AVGO Q2_FY2024 prediction stub (pre-schema, 254 bytes, no `schema_version` key) is intentionally NOT stamped. Empty `learning/` dirs (12 of 15) have nothing to stamp.
3e. **Sidecar coverage (per locked decision §2, REVISED post-wipe)**: all **33** modern `result.json` files have a sibling `result.md` generated by the migration. Each sidecar carries the read-only marker + `autogenerated: true` frontmatter + correct `component` / `experiment_name` per the file's parent dir. Legacy stub + empty dirs produce NO sidecar.
4. `Companies/BURL/events/Q4_FY2025/prediction/thinking.md` exists with **predictor reasoning sourced from the skill-fork JSONL** (text blocks — the predictor's ~1,900-char walkthrough + ~1,500-char synthesis — plus any thinking blocks if present; primary's minimal meta-thinking also included). **No `subagents/` dir** (FORK pattern).
5. `Companies/BURL/events/Q4_FY2025/experiments/prediction_no_lessons/thinking.md` exists with **baseline predictor reasoning sourced from the skill-fork JSONL** (same text-block composition as #4). **No `subagents/` dir** (FORK pattern).
6. `Companies/BURL/events/Q4_FY2025/learning/thinking.md` exists with primary learner thinking (renamed from `attribution/` in this commit).
7. `Companies/BURL/events/Q4_FY2025/learning/subagents/*.md` contains one file per `Agent`-tool-spawned Data SubAgent (co-located with the learner's result.json). Each file captures the subagent's execution trace (prompt + tool_use calls + tool_results + text blocks). Data SubAgents do not use thinking; these files are a trace not a reasoning dump. Subagent→primary linkage verified via direct top-level `toolUseResult.agentId` on the JSONL entry lookup (not `parentToolUseID`, not call-order, not prompt-match — all three are either absent or unreliable for SDK subprocess sessions).
8. `events/Q4_FY2025/` contains component dirs (`prediction/`, `learning/`, optionally `guidance/`) + `experiments/` subtree. No top-level `attribution/`, no `prediction_baseline/`, no `thinking/` dir — confirms co-located per-component layout with attribution→learning rename applied.
9. Zero new API 400 errors; predictor + learner runtime behavior identical.
10. `obsidian_capture.py` behaves correctly after the updates: routes `extraction-*` agent types to `pipeline/extractions/{guidance,news,risk}/` (type-sharded), simplifies filenames (no `_extraction_` segment), and the skip-list suppresses duplicate captures for `earnings-prediction`/`earnings-attribution`/`earnings-learner` (harvester owns those). `agents/` fallback continues to receive non-pipeline subagent captures.
11. No regression in existing `Companies/{AVGO,NVDA,BURL}/events/*/` artifacts.
12. `pytest scripts/earnings/` all passes (new `test_thinking_harvester.py` — which now includes 3 absorbed registry-test assertions from the dropped `test_pipeline_contracts.py` — and `test_result_md_renderer.py`, plus any existing tests that still run).

---

## Rollback plan

**Impact radius is larger than a typical additive change** — this commit touches production Python, hooks, skills, plan docs, and executes a filesystem migration across `events/`, `pipeline/extractions/`, and runtime paths. The rollback plan has to cover all of that.

**Reverse is MANIFEST-DRIVEN ONLY** (per locked decision §4 in the pre-flight addendum). `--reverse` walks the `.migration-manifest.json` backward and inverts **exactly the ops that the corresponding `--apply` run recorded**. It does NOT touch the filesystem for anything not in the manifest. Concretely: because `ab_baseline/` does not exist on disk today for any quarter, an apply run today will NOT record any `rename_file ab_baseline/*` ops — so `--reverse` will NOT recreate `ab_baseline/` for any quarter. If some quarter in a future apply run DID have `ab_baseline/` at apply time, that quarter's moves get recorded, and only that quarter's `ab_baseline/` is recreated on reverse. Never reverse more than was applied.

1. `git revert` the implementation commit. This restores every edited file: `earnings_orchestrator.py`, A/B scripts, validators, `obsidian_capture.py`, skills, plan docs, `settings.json` hook path.
2. Run the migration script in **reverse mode**: `python scripts/migrate_unified_layout.py --reverse`. This inverts every manifest-recorded op (and only those ops). Expected inversions for an apply run executed today:
   - `rename_dir attribution → learning`: 15 entries → restore to `attribution/`
   - `rename_file prediction/context_bundle.* → <Q>/context_bundle.*`: 30 entries → restore under `prediction/`
   - `rename_file ab_baseline/* → experiments/prediction_no_lessons/*`: **0 entries today** (conditional) → no-op
   - `remove_dir_if_empty ab_baseline`: **0 entries today** (conditional) → no-op
   - `stamp_null_session_id`: **45 entries** → remove the `sdk_session_id` field from each JSON (only on entries actually stamped — if a file already had a non-null value from a re-run during the lifetime of the apply, the manifest preserves whatever state to restore; simplest rule: unstamp only exact `null`s we wrote)
   - `generate_result_md`: **45 entries** → delete each generated `result.md` file
   - `rename_file pipeline/extractions/{date}_extraction_{sid}.md → guidance/{date}_{sid}.md`: 1,289 entries → restore to flat root with `_extraction_` re-inserted
3. Delete new files the commit added that `git revert` didn't touch: `thinking.md` + `subagents/` dirs inside `events/{Q}/{component}/` that the harvester wrote post-migration during live runs. Not in the manifest (they're runtime output, not migration output) — clean up manually if desired (harmless to leave; no code reads them after revert).
4. `kubectl rollout undo` on the K8s extraction-worker IF the separate deploy step had already shipped — restores the pre-auto-trigger image.
5. Run the test suite to verify nothing from the old code is now broken after the double-revert (rare but possible if a test referenced a path that the rollback re-created).

Net: one `git revert` + one manifest-driven migration `--reverse` restores the pre-commit state. Use `--dry-run` to preview the reverse before executing.

---

## What I am intentionally NOT building (lean gate)

- **No `_index.md` files anywhere** — the directory listing + `result.md` frontmatter is the index. Static index pages can be added later as a small harvester extension if wanted.
- **No K8s extraction-worker auto-trigger wiring for guidance** — harvester is CLI-invokable day one; the ~10-line change inside the extraction-worker pod is a separate deploy step documented below.
- **No fuzzy-match backfill of the 15 existing A/B quarters** — the migration preserves and relocates their baseline JSONs, but their thinking isn't harvested because they predate `sdk_session_id`. A followup `backfill_thinking.py` can use best-effort transcript matching if ever needed.
- **No Dataview-dependent index pages** — directory listings + `result.md` frontmatter already give Obsidian + Dataview enough to browse. Static index pages can be added later as a small harvester extension if wanted.
- **No `_timeline.md` / `_summary.md`** — per requirement.
- **No `config/thinking_phases.py`** — earlier proposed then retracted. Just a set of valid names in `config/pipeline_contracts.py`.
- **No unified result envelope** — earlier proposed then dropped after review. `sdk_session_id` is a flat top-level field on existing `result.json` files. No `{envelope, payload}` wrapper, no back-compat shim.
- **No Data SubAgent "thinking" capture** — empirically verified across 5 learner sessions (6 subagents each) + 1 guidance session (extraction-primary + extraction-enrichment): all Data SubAgents produce 0 thinking blocks. They run with thinking disabled by default in SDK subprocess sessions. The harvester captures their execution trace (prompt + tool_use + tool_result + text) instead. This is a finding, not a limitation — the trace IS the interesting artifact for tool-calling subagents.
- **No reconstruction of redacted thinking content** — guidance session (`/extract`) produces `type=thinking` blocks with `signature` field and ZERO readable chars (Claude's cryptographically-signed thinking). This is NOT a separate block type — it's a regular thinking block with empty `thinking` string + a `signature` key. Harvester detects via `(block["type"]=="thinking" and not block.get("thinking","") and "signature" in block)` → reports block count + notes "content redacted (signed)" + falls back to text blocks. Not recoverable client-side by design.

---

## Separate deploy step: K8s extraction-worker auto-trigger for guidance

Everything else ships in one commit. This one item is separate because it requires a pod rebuild + `kubectl rollout restart` — different risk profile from a Python-only change.

### What changes

Inside the extraction-worker image (`k8s/processing/extraction-worker.yaml` + `scripts/extraction_worker.py`):

```python
# After guidance extraction writes to Neo4j + writes result.json
from scripts.earnings.thinking_harvester import harvest
try:
    harvest(
        thinking_type="guidance",
        ticker=ticker,
        quarter=quarter,
        session_id=sdk_session_id,   # captured from the SDK init message in worker code
    )
except Exception as e:
    log.warning(f"guidance harvest failed for {ticker} {quarter}: {e}")
```

~10 lines added. No behaviour change for extraction itself — only adds the harvest call after successful write.

### Why separate

1. Pod image rebuild required (`docker build` + push)
2. `kubectl rollout restart` on `extraction-worker` deployment
3. Different change control — repo commit lands immediately; K8s change needs deploy window
4. Day-one coverage via CLI (`python thinking_harvester.py guidance TICKER QUARTER SESSION_ID`) — no functional gap

### Acceptance for this step

- Next guidance extraction run auto-populates `events/{Q}/guidance/thinking.md` + `subagents/`
- `kubectl logs extraction-worker` shows harvest success log line
- No regression in extraction itself

---

## Boundaries

| Category | Scope |
|---|---|
| **In this commit** | Thinking harvester + registry + renderer; `sdk_session_id` capture + flat-field stamping; `result.md` sidecars; baseline flatten; `attribution/` → `learning/` rename; `context_bundle.json` promotion to quarter level; `obsidian_capture.py` extraction-type subdirs + filename simplification; skip-list for earnings-* agent types; one-shot migration script. |
| **Separate deploy step** | K8s extraction-worker pod rebuild + rollout to add the ~10-line guidance harvest auto-trigger. CLI-invokable day one; automatic after deploy. |
| **Why this boundary** | Everything in the first row is Python + filesystem changes ship-able in one commit with one migration script. The second row requires a container rebuild + `kubectl rollout restart` — different risk profile, different approval path, no reason to hold the commit on it. |

---

## Small design decisions worth calling out

1. **Shared block-extraction helper**: pull block-parsing out of `obsidian_capture.py` into `scripts/earnings/thinking_blocks.py` (~60 lines) so the harvester doesn't duplicate it. The old hook keeps working identically by importing from the new location. Small, DRY, no behaviour change.
2. **Harvester idempotency**: re-running overwrites the type's file + clears its subagents subdir first. Safe to re-harvest after a bug fix.
3. **Silent-fail semantics on harvest**: if harvester throws (missing transcript, malformed session), log WARNING and continue. Predictor/learner writes MUST complete regardless. Zero runtime coupling.
4. **`agents/` unchanged; `pipeline/extractions/` now type-sharded with simplified filenames** — raw capture keeps flowing to `agents/` unchanged; `pipeline/extractions/` gets the `{guidance,news,risk}/` subdirs + filename cleanup in this commit (via `obsidian_capture.py` FOLDER_ROUTING update + migration script).

---

## Implementation reference (for the engineer building this)

This section removes implementation ambiguity — it's the concrete spec for each piece the prose above describes.

### 1. Build order (do NOT deviate — imports require it)

1. `config/pipeline_contracts.py` (standalone, no imports from new code)
2. `scripts/earnings/thinking_blocks.py` (standalone; stdlib only)
3. `scripts/earnings/result_md_renderer.py` (stdlib only)
4. `scripts/earnings/thinking_harvester.py` (imports `pipeline_contracts` + `thinking_blocks`)
5. `scripts/earnings/test_thinking_harvester.py` + `scripts/earnings/test_result_md_renderer.py`
6. `scripts/migrate_unified_layout.py` (imports `result_md_renderer`)
7. Edit `scripts/earnings/earnings_orchestrator.py` (imports `thinking_harvester`, `result_md_renderer`, `pipeline_contracts`)
8. Edit the 3 A/B scripts (imports `thinking_harvester`)
9. Rename `validate_attribution.py` → `validate_learning.py`. **Keep old name as a thin alias with ABSOLUTE import** (per locked decision §8 in the pre-flight addendum — `scripts/earnings/` is not a package; relative `from .validate_learning import *` would silently fail). Alias file content is exactly one line: `from validate_learning import *  # noqa: F401,F403 — 1-release alias after rename`.
10. Rename `.claude/hooks/validate_attribution_output.py` → `validate_learning_output.py`; update `.claude/settings.json` hook path
11. Edit `.claude/hooks/obsidian_capture.py` (3 changes — see §3 below)
12. Edit 4 SKILL.md files (path refs only)
13. Sweep 12 plan docs (path refs; prose mentions of "attribution" left in place unless context demands otherwise)
14. Run `pytest scripts/earnings/`
15. Run `migrate_unified_layout.py --dry-run`, inspect output, then `--apply`
16. Run one fresh BURL quarter end-to-end to smoke-test the full flow

### 2. Python function signatures

```python
# config/pipeline_contracts.py
KNOWN_TYPES: frozenset[str]  # = frozenset({"guidance", "prediction", "learning"})

def validate_experiment_name(thinking_type: str, experiment_name: str) -> None:
    """Raises ValueError if experiment_name does not start with f'{thinking_type}_'."""

# scripts/earnings/thinking_blocks.py
def parse_session_blocks(jsonl_path: Path) -> list[Block]:
    """Returns ordered list of Block dicts: {kind, ts, content, meta}.
       kind ∈ {'thinking', 'thinking_redacted', 'text', 'tool_use', 'tool_result'}."""

# scripts/earnings/thinking_harvester.py
def harvest(
    *, thinking_type: str, ticker: str, quarter: str,
    session_id: str, experiment_name: str | None = None,
    vault_root: Path | None = None,  # defaults to repo's earnings-analysis/Companies/
) -> None:
    """Writes thinking.md (+ subagents/ when Agent-spawned children exist) for one session.
       Idempotent (overwrites). Raises nothing on missing session_id — logs WARNING and returns."""

# scripts/earnings/result_md_renderer.py
def render(component: str, result_json_path: Path, md_out_path: Path) -> None:
    """Deterministic JSON→MD. component ∈ KNOWN_TYPES ∪ {'prediction_no_lessons'}.
       Writes frontmatter + read-only marker + rendered tables."""

# scripts/migrate_unified_layout.py
def main(argv: list[str]) -> int:
    """CLI: --dry-run, --apply, --reverse, --only TICKER. Returns 0 on success, non-zero on failure."""
```

### 3. `obsidian_capture.py` — exact 4 changes

**(a) FOLDER_ROUTING** — change the dict:
```python
# BEFORE:
'extraction-primary-agent':    'pipeline/extractions',
'extraction-enrichment-agent': 'pipeline/extractions',
# AFTER:
'extraction-primary-agent':    'pipeline/extractions/guidance',
'extraction-enrichment-agent': 'pipeline/extractions/guidance',
# (news, risk, etc. get their own subfolders when those extraction types land;
#  the router can map by type-name prefix OR by hook on extraction `TYPE=` arg)
```

**(b) Skip-list** — add near the top of `main()` in `obsidian_capture.py`, right after `agent_type` is parsed:
```python
SKIP_AGENT_TYPES = {"earnings-prediction", "earnings-attribution", "earnings-learner"}
if agent_type in SKIP_AGENT_TYPES:
    sys.exit(0)  # thinking_harvester owns these now
```

> **DO NOT rename these strings as part of the `attribution/` → `learning/` path sweep.** `earnings-attribution` is a live runtime `agent_type` identifier registered in the Claude Code agent definitions and emitted by the SDK at SubagentStop time — it is **not** a filesystem path. The skip-list matches on exact string equality, so renaming the agent_type (or the skip-list entry) would silently break this hook. Keep all three values exactly as `earnings-prediction`, `earnings-attribution`, `earnings-learner`. Renaming the `earnings-attribution` agent itself is a separate, out-of-scope change that would require coordinated edits to the agent definition file, every skill/orchestrator that spawns it, and this skip-list together.

**(c) Filename simplification** — where the extraction filename is built, drop the `_extraction_` segment:
```python
# BEFORE: filename = f"{date}_extraction_{source_id}.md"
# AFTER:  filename = f"{date}_{source_id}.md"
# (folder name already encodes the extraction type)
```

**(d) Shared block-parser import** — replace the inline block-parsing loop with:
```python
from scripts.earnings.thinking_blocks import parse_session_blocks
blocks = parse_session_blocks(transcript_path)
```

### 4. `thinking.md` tool_use annotation table

One line per tool_use block, in session-timestamp order. Formulas:

| Tool name | Annotation line format | Example |
|---|---|---|
| `Bash` | `🔨 Bash({description or first 60 chars of command})` | `🔨 Bash(ls earnings-analysis/...)` |
| `Read` | `📖 Read({basename})` | `📖 Read(result.json)` |
| `Write` | `✏️  Write({basename})` | `✏️  Write(result.json)` |
| `Edit` | `✏️  Edit({basename})` | `✏️  Edit(orchestrator.py)` |
| `Glob` | `🔎 Glob({pattern})` | `🔎 Glob(**/*.json)` |
| `Grep` | `🔎 Grep({pattern})` | `🔎 Grep(attribution)` |
| `Agent` | `🤖 Agent({subagent_type})` | `🤖 Agent(neo4j-news)` |
| `Skill` | `🔩 Skill({skill_name})` | `🔩 Skill(earnings-prediction)` |
| `mcp__neo4j-cypher__read_neo4j_cypher` | `🗃  Cypher(read)` | `🗃  Cypher(read)` |
| Any other | `🔧 {ToolName}` | `🔧 ToolSearch` |

Tool_result content does NOT appear in thinking.md — it goes in `subagents/*.md` traces (for Agent-spawned) or is simply skipped (for primary tool_uses like Read/Write where the result is the side-effect on disk).

### 5. `migrate_unified_layout.py` — `.migration-manifest.json` schema

Written by `--apply`, read by `--reverse`. Schema shape is stable across coverage expansions — only the number of entries changes. For today's apply run, expected entry counts: 15 `rename_dir`, 30 `rename_file` (context_bundle), 0 `rename_file` (ab_baseline — conditional, skipped today), 45 `stamp_null_session_id`, 45 `generate_result_md`, 0 `remove_dir_if_empty` (conditional, skipped today), 1,289 `rename_file` (extractions).

```json
{
  "schema_version": "migration.v1",
  "started_at": "2026-04-17T20:15:00Z",
  "completed_at": "2026-04-17T20:15:42Z",
  "steps": [
    // (a) attribution → learning rename — 15 entries (unconditional)
    {"op": "rename_dir",  "from": "events/Q4_FY2025/attribution", "to": "events/Q4_FY2025/learning"},

    // (b) context_bundle promotion — 30 entries (unconditional, 15 JSON + 15 txt)
    {"op": "rename_file", "from": "events/Q4_FY2025/prediction/context_bundle.json",         "to": "events/Q4_FY2025/context_bundle.json"},
    {"op": "rename_file", "from": "events/Q4_FY2025/prediction/context_bundle_rendered.txt", "to": "events/Q4_FY2025/context_bundle_rendered.txt"},

    // (c) baseline relocate — CONDITIONAL on source existence. ZERO entries on today's run. Example of what would be
    //     recorded IF a quarter had ab_baseline/ (preserved for reverse symmetry):
    //   {"op": "rename_file", "from": "events/{Q}/prediction/ab_baseline/result_NO_LESSONS.json", "to": "events/{Q}/experiments/prediction_no_lessons/result.json"},
    //   {"op": "remove_dir_if_empty", "path": "events/{Q}/prediction/ab_baseline"},

    // (d) null-stamp sdk_session_id — 45 entries (15 prediction + 15 learning + 15 experiment)
    {"op": "stamp_null_session_id", "path": "events/Q4_FY2025/prediction/result.json"},
    {"op": "stamp_null_session_id", "path": "events/Q4_FY2025/learning/result.json"},
    {"op": "stamp_null_session_id", "path": "events/Q4_FY2025/experiments/prediction_no_lessons/result.json"},

    // (e) generate result.md sidecars — 45 entries (same scope as null-stamp)
    {"op": "generate_result_md", "source": "events/Q4_FY2025/prediction/result.json",                          "target": "events/Q4_FY2025/prediction/result.md"},
    {"op": "generate_result_md", "source": "events/Q4_FY2025/learning/result.json",                            "target": "events/Q4_FY2025/learning/result.md"},
    {"op": "generate_result_md", "source": "events/Q4_FY2025/experiments/prediction_no_lessons/result.json",   "target": "events/Q4_FY2025/experiments/prediction_no_lessons/result.md"},

    // (f) pipeline/extractions flat → guidance/ — 1,289 entries (conforming pattern only; leaves anomalous 8 + manual notes untouched)
    {"op": "rename_file", "from": "pipeline/extractions/2026-03-17_extraction_0001234.md", "to": "pipeline/extractions/guidance/2026-03-17_0001234.md"}
  ]
}
```
`--reverse` walks `steps` in reverse order and inverts each op:
- `rename_dir`/`rename_file` → rename back
- `stamp_null_session_id` → remove the `sdk_session_id` field from the JSON (only if still `null` — preserves any non-null value written by a subsequent live run)
- `generate_result_md` → delete the target file
- `remove_dir_if_empty` → `mkdir` back

`--reverse` NEVER fabricates ops — if the manifest doesn't record a baseline-relocate for a quarter (because `ab_baseline/` didn't exist at apply time), `--reverse` leaves that quarter's filesystem alone.

### 6. Test fixtures — exactly how to create them

Fixtures live at `scripts/earnings/tests/fixtures/` and are **committed to the repo** (not gitignored). Create by:

```bash
# Copy the 3 known-good session JSONLs (identified in this session's live validation):
cp ~/.claude/projects/-home-faisal-EventMarketDB/98984e15-2570-425a-9429-dec0c3dbf7ff.jsonl      scripts/earnings/tests/fixtures/learner_session.jsonl
cp ~/.claude/projects/-home-faisal-EventMarketDB/235cf379-282f-4637-9c30-7cf19c43a85d.jsonl      scripts/earnings/tests/fixtures/guidance_session.jsonl
cp ~/.claude/projects/-home-faisal-EventMarketDB/374b1345-411b-46cc-a363-3cce54db33a6.jsonl      scripts/earnings/tests/fixtures/predictor_session.jsonl

# Subagent trees for all three sessions — MUST copy BOTH the .jsonl AND the .meta.json sidecar files.
# The .meta.json carries agentType, which is the PRIMARY signal for skill-fork detection AND the
# preferred source for subagent_type filename resolution (per locked decision §7 in the addendum).
# Copying only *.jsonl would silently make tests exercise the fallback path instead of the happy path.
mkdir -p scripts/earnings/tests/fixtures/learner_session/subagents
cp ~/.claude/projects/-home-faisal-EventMarketDB/98984e15-2570-425a-9429-dec0c3dbf7ff/subagents/*.jsonl      scripts/earnings/tests/fixtures/learner_session/subagents/
cp ~/.claude/projects/-home-faisal-EventMarketDB/98984e15-2570-425a-9429-dec0c3dbf7ff/subagents/*.meta.json  scripts/earnings/tests/fixtures/learner_session/subagents/

mkdir -p scripts/earnings/tests/fixtures/guidance_session/subagents
cp ~/.claude/projects/-home-faisal-EventMarketDB/235cf379-282f-4637-9c30-7cf19c43a85d/subagents/*.jsonl      scripts/earnings/tests/fixtures/guidance_session/subagents/
cp ~/.claude/projects/-home-faisal-EventMarketDB/235cf379-282f-4637-9c30-7cf19c43a85d/subagents/*.meta.json  scripts/earnings/tests/fixtures/guidance_session/subagents/

mkdir -p scripts/earnings/tests/fixtures/predictor_session/subagents
cp ~/.claude/projects/-home-faisal-EventMarketDB/374b1345-411b-46cc-a363-3cce54db33a6/subagents/*.jsonl      scripts/earnings/tests/fixtures/predictor_session/subagents/
cp ~/.claude/projects/-home-faisal-EventMarketDB/374b1345-411b-46cc-a363-3cce54db33a6/subagents/*.meta.json  scripts/earnings/tests/fixtures/predictor_session/subagents/
```

**Fixture-completeness invariant** — a test MUST exist asserting that for every `agent-<id>.jsonl` in each fixture `subagents/` dir, a sibling `agent-<id>.meta.json` also exists. This prevents silent fixture drift where a future `cp` omission would re-introduce the fallback-path-only test behavior.

Optional trimming: each session JSONL is ≤529 KB as-is; committing whole is fine. `.meta.json` files are tiny (<100 bytes each). If size becomes a concern, the test setup can copy + truncate to first 50 lines of each JSONL (sufficient to cover all 3 patterns' block types + linkage structure); never truncate the `.meta.json` files.

The tests construct a temporary vault-root dir per run and pass it as `vault_root=` to `harvester.harvest()`, so fixtures don't need to mirror the full `events/{Q}/...` layout.

---

## Review checklist (ratified 2026-04-17 after pre-flight verification)

- [x] Target thinking layout approved (section "Target layout (locked)")
- [x] Files-to-add list approved (each of the 7 new files)
- [x] Files-to-change list approved (the full production + skills + plan-docs sweep, ~28 files)
- [x] sdk_session_id capture + stamp approach approved (hybrid per addendum §6)
- [x] Inspection results + write-path verification read
- [x] Syncthing propagation risk acknowledged
- [x] Acceptance checks approved (including expanded 3d/3e)
- [x] Rollback plan approved (manifest-driven per addendum §4)
- [x] "What I am intentionally NOT building" list approved (gates the lean scope)
- [x] Separate deploy step (K8s extraction-worker) reviewed
- [x] K8s deploy step kept separate (not folded into the commit) — rationale accepted
- [x] Pre-flight verification addendum (10 locked decisions) accepted

**Status**: plan is locked. Awaiting explicit "go implement" from user before any code/filesystem changes. Implementation proceeds in the build order specified in the Implementation reference section.
