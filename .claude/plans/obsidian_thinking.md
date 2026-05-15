> 📌 **Billing/no-charge note (2026-05-15):** the SDK reality this plan builds on is now governed by Anthropic's June 15 2026 subscription change. Before relying on `claude_agent_sdk` for guidance/prediction/learning, see **`.claude/plans/ANTHROPIC_BILLING_SUBSCRIPTION_CRITICAL.md`** (empirical no-charge proof, entrypoint lever, Option #6, EarningsTrigger/Guidance fix recipe).

## TODO — Fresh Guidance + Prediction + Learning Cleanup (2026-04-19)

Goal: make `thinking.md` the canonical reviewer artifact for fresh **guidance**, **prediction**, and **learning** runs with maximum clarity, zero ambiguity, minimal code, and high reliability. Favor surfacing existing transcript data over inventing new reconstruction logic.

### Shipped today (2026-04-19) — committed + pushed to `main`

Ordered by commit sha (chronological). All verified by end-to-end re-harvest of live AVGO Q2 FY2023 guidance + BURL Q3 FY2025 8-K/transcript guidance + BURL Q3 FY2025 prediction + BURL Q3 FY2025 learner. 143/143 targeted tests green after each commit.

| Commit | Fix | Evidence |
|---|---|---|
| `603d13c` | **Completion gate**: `is_session_complete` now requires the LAST `assistant` entry to have `stop_reason=="end_turn"`; stops treating mid-session `last-prompt` markers as completion. Root cause of AVGO Q1 FY2023 enrichment subagent being permanently orphaned. | Re-harvested → both primary + enrichment subagent files present, no orphan warnings |
| `ee4e51c` | **Heading downgrade in harvester**: content-authored `#/##/###` shifted +3 levels (matching hook). Eliminates outline pollution in Obsidian sidebar. | Measured — AVGO Q1 thinking_transcript.md: 6 H2s → 1 structural H2 |
| `2d4d1a5` | **Fence-safe truncation @4000 chars** in subagent text/thinking/prompt render — closes unbalanced ``` at the cut. | `_truncate_safe_fence` helper + regression test |
| `5b4fc8a` | **Fence-safe truncation @300 chars** in tool_result preview (same bug as 2d4d1a5, different call site). | Same helper |
| `6dd188a` | **Fence-safe truncation @2000 chars** in hook adapter tool_result (pre-existing hook bug). | Local `_truncate_safe_fence` in adapter |
| `0eeba9f` | **Subagent thinking coverage**: subagent frontmatter now reports `thinking_blocks` / `thinking_chars` / `redacted_thinking_blocks`. Subagent body now renders `🔒` placeholder for `thinking_redacted` (previously silently dropped). | Audit: 51% of 10k subagent JSONLs had visible thinking but were not surfaced in frontmatter |
| `13da3d1` | **Primary thinking.md `## Prompt` section**: new `_read_first_user_content` helper; primary thinking.md now shows the original user-invoked command (previously only subagent traces showed prompts). | Partial-fix for P0 "prediction prompt completeness" / "learner prompt de-noising" — raw prompt now visible but boilerplate noise still present |
| `ccb8e8a` | **Hook `fiscal_quarter` removed**: regex-based derivation deleted; zero Python consumers read this field from markdown. Negative smoke test (`test_hook_note_never_emits_fiscal_quarter_field`) locks the invariant. Vault hygiene sweep stripped the field from 1,030 pre-fix hook notes (882 `pipeline/extractions/guidance/*.md` + 148 `agents/*.md`). | P0 item below ✅ |

Guardrail held throughout: zero behaviour change for the harvester path beyond the targeted fix each commit; zero new runtime dependencies; zero new files except 1 adapter module + 3 targeted tests.

### P0 — Fix Now

- [x] **Drop hook `fiscal_quarter` for extraction notes**: the hook cannot derive source quarter reliably from agent output. Fresh proof: `pipeline/extractions/guidance/2026-04-19_0001193125-25-294501.md` stamped `Q4FY2025` for the BURL **Q3_FY2025** 8-K because the regex matched forward-guidance content before source-quarter context. Keep `source_id`; treat `Companies/.../quarter:` as authoritative. — **SHIPPED `ccb8e8a` (2026-04-19): delete-only fix in `.claude/hooks/obsidian_capture.py`, negative smoke test added, 1,030 stale notes swept.**
- [ ] **Guidance prompt rendering**: stop rendering raw `<command-message>/<command-name>/<command-args>` XML in `## Prompt`. Render a readable `/extract ...` command instead. If the immediately following user/meta entry contains the expanded extract brief, render that too in a separate section. Do not synthesize prompt text.
- [ ] **Learner prompt de-noising**: the learner `## Prompt` is currently dominated by static skill boilerplate and truncates before the actual run-specific `--- INPUTS ---` block. For learner prompts, surface the dynamic inputs (`TICKER`, `QUARTER`, `PIT_CUTOFF`, paths, etc.) instead of the static skill preamble when truncation would otherwise hide the actionable run context.
- [ ] **Prediction prompt completeness**: keep the outer wrapper prompt, but also render the predictor skill-fork's own first-user prompt in a dedicated section so reviewers can see the actual prediction contract.
- [ ] **Agent spawn rationale**: include `Agent.description` in top-level `- 🤖 Agent(...)` bullets and near the top of each subagent trace. Reviewer should see why a subagent was spawned without opening raw JSONL. This also disambiguates repeated learner subagent types such as multiple `neo4j-news` calls.
- [ ] **Guidance results section**: if the final assistant text block is an extraction summary (`Extraction Complete`, `| Pass |`, `Result written to`, etc.), promote it to a top-level `## Results` section at the end of the note instead of leaving it buried as downgraded assistant markdown inside reasoning.
- [ ] **Reviewer navigation**: keep `thinking.md` as the canonical reviewer landing page. Add a short "Subagent traces" section with Obsidian links from each top-level guidance note to its subagent trace files, and add bidirectional links between any sibling `thinking.md` and `result.md` pair that coexist (`prediction`, `learning`; `guidance` too once canonical guidance result artifacts exist).
- [ ] **Guidance title disambiguation**: include `source_asset` in the visible H1/title (`guidance / 8k`, `guidance / transcript`, etc.) so sibling notes are distinguishable in the vault.
- [ ] **FORK summary semantics**: replace misleading `Primary thinking` label with a FORK-aware summary that reflects the real split (primary redacted/meta-thinking vs skill-fork visible text reasoning). Make visible/redacted counts use one consistent scope.
- [ ] **Live guidance completeness**: write canonical `guidance/result.json` + `guidance/result.md` during the live flow if the worker already has the result payload in hand. Do this at the worker boundary; do not rebuild guidance results later from notes.

### P1 — Next, Still Worth Doing

- [ ] **Guidance outcome frontmatter**: add optional guidance-only fields such as `items_extracted`, `items_written`, and `enrichment_status` when they are derivable from the session transcript itself. Do not depend on `/tmp` files that are already deleted by the time harvest runs.
- [ ] **Prediction + learning outcome frontmatter**: when sibling `result.json` exists, copy a minimal outcome summary into `thinking.md` frontmatter. Prediction: `direction`, `confidence_score`, `expected_move_range_pct`. Learning: `direction_correct`, `primary_driver_category`, `magnitude_error_pct`. Omit fields when unavailable; source of truth remains `result.json`.
- [ ] **Primary `text_chars` frontmatter**: add `text_chars` to top-level `thinking.md` frontmatter so FORK sessions do not look "empty" when `thinking_chars=0` but visible skill-fork reasoning is large.
- [ ] **Subagent identity metadata**: add `agent_input_description` to subagent-trace frontmatter so repeated types (`neo4j-news`, `extraction-primary-agent`, etc.) are distinguishable from directory listing / properties view without changing filenames.
- [ ] **Shard migration cleanup**: when guidance is harvested into per-asset shards (`thinking_8k.md`, `thinking_transcript.md`), proactively remove stale legacy non-sharded artifacts (`thinking.md`, `subagents/`) left from pre-sharding runs so old dry-run/test notes cannot coexist under a current quarter and mislead reviewers.
- [ ] **Hook note ticker noise**: ticker tagging in `obsidian_capture.py` is still noisy on fresh notes (for example `tickers: [A, BURL, D]`). Keep hook notes supplemental until ticker extraction is tightened or reduced.

### P2 — Cosmetic / Latent

- [ ] **Spacing cleanup**: insert a blank line after tool-use bullets before the next heading/text block for easier scanning in Obsidian.
- [ ] **Subagent truncation marker parity**: when subagent text/thinking blocks are truncated at 4000 chars, append the same `*[truncated — X more chars]*` marker used in primary prompt rendering. Today subagent traces silently cut off long blocks.

### Guardrails

- [ ] Do **not** merge hook and harvester systems. Keep harvester output as the canonical reviewer artifact; link to hook notes only when useful.
- [ ] Do **not** build a generic parser framework. Implement the smallest reliable helpers for the actual transcript shapes we already see in production.
- [ ] Do **not** synthesize or paraphrase prompts when exact prompt text already exists in SDK JSONL.
- [ ] Prefer fixes in `thinking_harvester.py` and the live worker path over adding post-hoc cleanup layers.
- [ ] Do **not** broaden skill-fork handling for hypothetical multi-skill sessions unless a real occurrence appears. The current gap is latent/YAGNI.
- [ ] **Learner capture reality**: do not design reviewer UX around visible learner primary thinking. Current learner runs are arriving as `EMBED-redacted` in practice, so the durable reviewer surfaces are `result.md` plus subagent traces, not rich visible top-level reasoning.

---

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


---

# Appendix A — Obsidian Thinking Revamp (formerly `obsidian_thinking_revamp.md`)

> **Status**: Merged into this file on 2026-04-19 (was `.claude/plans/obsidian_thinking_revamp.md`).
> Section numbering below is SELF-CONTAINED to this appendix — do not confuse with obsidian_thinking.md §N.


> **STATUS: ✅ SHIPPED (2026-04-19)** — all 3 approved changes are executed on `main`; 184/184 pytest lock green; 2 orphaned `.pyc` files swept.
>
> | Change | Commit | Notes |
> |---|---|---|
> | 1. Harvester dedupe (`_first_user_matches_skill_prefix` → delegation) | `a3f2cf7` | bundled in the unified-layout feature commit |
> | 2. Orchestrator → canonical validator import | `cd33014` (T5) | **alias sunset happened earlier than this plan's text describes** — `validate_attribution.py` was DELETED (not "kept for 1 release"); orchestrator at `earnings_orchestrator.py:1812` now imports from `validate_learning` directly |
> | 3. Delete 5 dead legacy `build-*-thinking` files | `3802113` | guidance + news pairs + `build-thinking-on-complete.sh` |
> | Orphaned `.pyc` sweep | post-ship | `build-guidance-thinking.cpython-310.pyc` + `build-news-thinking.cpython-310.pyc` removed; `build-thinking-index.cpython-310.pyc` intentionally retained (live `.py` still referenced by `earnings-attribution/SKILL.md:438`) |
>
> **Reader notes:**
> - Treat body text below as HISTORICAL REFERENCE. Where Change 2 still says "keep `validate_attribution.py` in place" / "sunset after one release cycle", the shim was actually removed earlier in T5 — reality is already past the sunset point.
> - The validation grep `rg -n "build-guidance-thinking|build-news-thinking|build-thinking-on-complete" .claude scripts` now self-matches the plan file inside `.claude/plans/` and the pre-existing `.claude/archive/skills/earnings-orchestrator-v2/SKILL.md`. These are semantic hits in documentation, not live runtime references — expected.

This document is the **implementation authority for the current Obsidian thinking / extraction cleanup**.

It is intentionally based on the **live implemented code and current tests**, not on older plans. If this document conflicts with an older plan, **the implemented code and tests win**.

## Purpose

Give a new bot enough context to make the Obsidian extraction / thinking system leaner **without changing behavior** and without accidentally “cleaning up” code that is still live, still intentional, or still required for compatibility.

The goal is:

- production-grade
- minimal
- no over-engineering
- no behavior drift
- no speculative refactors

This is **not** a redesign. It is a **surgical cleanup guide**.

## Scope Boundary

Review and act only on the **currently implemented runtime and test surface**:

- `.claude/settings.json`
- `.claude/hooks/obsidian_capture.py`
- `.claude/hooks/obsidian_capture.sh`
- `.claude/hooks/validate_learning_output.py`
- `scripts/earnings/thinking_blocks.py`
- `scripts/earnings/obsidian_capture_adapter.py`
- `scripts/earnings/thinking_harvester.py`
- `scripts/earnings/result_md_renderer.py`
- `scripts/earnings/validate_learning.py`
- `scripts/earnings/validate_attribution.py`
- `scripts/earnings/earnings_orchestrator.py`
- `scripts/extraction_worker.py`
- `scripts/harvest_guidance_sessions.py`
- `.claude/skills/earnings-orchestrator/scripts/` (touched by Change 3)
- the relevant tests under `scripts/earnings/` and `scripts/`

Do **not** treat older plans as architecture truth. They are background only.

## Current Live Architecture

### 1. Raw hook capture is live and supplemental

`SubagentStop` in `.claude/settings.json` calls `.claude/hooks/obsidian_capture.sh`, which shells into `.claude/hooks/obsidian_capture.py`.

That hook:

- skips `earnings-prediction`, `earnings-attribution`, and `earnings-learner`
- still captures extraction agents and general agents
- writes raw reviewer-facing notes into:
  - `pipeline/extractions/guidance/`
  - `pipeline/news-impact/`
  - `agents/`

This hook is **live** and covered by smoke tests.

### 2. Transcript parsing is centralized

`scripts/earnings/thinking_blocks.py` is the shared parser.

It is currently responsible for:

- reading SDK JSONL
- turning entries into normalized block dicts
- handling redacted thinking detection
- preserving file order optionally for the hook adapter

This module is a **parser module**, not a generic formatting/utilities module.

### 3. Hook adaptation is separate on purpose

`scripts/earnings/obsidian_capture_adapter.py` converts parsed blocks into the legacy hook bucket shape.

It owns hook-specific behavior such as:

- result cleaning
- 2000-char tool_result truncation
- hook pairing semantics

This is the right boundary for hook-specific shaping.

### 4. Canonical thinking notes come from the harvester

`scripts/earnings/thinking_harvester.py` is the canonical writer for:

- `thinking.md`
- `thinking_{asset}.md`
- `subagents/*.md`
- `subagents_{asset}/*.md`

It handles the three real session patterns:

- `EMBED-visible`
- `EMBED-redacted`
- `FORK`

It also owns:

- skill-fork detection
- subagent linkage
- thinking markdown composition
- subagent trace rendering

### 5. Canonical result sidecars come from the renderer

`scripts/earnings/result_md_renderer.py` is the canonical writer for `result.md` sidecars from `result.json`.

It covers:

- prediction
- learning
- guidance
- baseline experiment

### 6. Prediction and learning are finalized inline

`scripts/earnings/earnings_orchestrator.py` is the live owner for prediction / learning finalization.

It already does:

- session-id stamping
- metadata stamping
- `result.md` render
- `thinking.md` harvest

### 7. Guidance is still split across three live pieces

Guidance is **not** fully inline yet.

Live flow today:

1. `scripts/extraction_worker.py` runs `/extract`
2. raw hook notes are produced by `obsidian_capture.py`
3. `scripts/harvest_guidance_sessions.py` post-hoc harvests canonical company-tree `thinking_{asset}.md`

This split is real and intentional for now. Do **not** mistake it for dead code.

### 8. Compatibility shims are still carrying real load

These are still intentionally present:

- `scripts/earnings/validate_attribution.py`
- `earnings_orchestrator.get_attribution_paths()`
- `earnings_orchestrator.finalize_attribution_result()`

Some helper scripts still import them. They are not dead yet.

## What Was Revalidated

The following targeted test net was run against the current repo state:

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest \
  scripts/earnings/test_thinking_blocks.py \
  scripts/earnings/test_obsidian_capture_adapter.py \
  scripts/earnings/test_obsidian_capture_hook_smoke.py \
  scripts/earnings/test_result_md_renderer.py \
  scripts/earnings/test_thinking_harvester.py \
  scripts/test_harvest_guidance_sessions.py -q
```

Result at review time:

- `184 passed`
- only Neo4j deprecation warnings from test process teardown

That test net is the behavioral lock for this cleanup.

## Approved Changes

These are the only cleanup changes that are recommended as part of this revamp.

## Change 1: Simplify `_first_user_matches_skill_prefix()`

### File

- `scripts/earnings/thinking_harvester.py`

### Current situation

There are two helpers in the harvester:

- `_read_first_user_content()`
- `_first_user_matches_skill_prefix()`

The second is a near-duplicate JSONL walker that differs only in the final predicate.

### Required change

Replace `_first_user_matches_skill_prefix()` with a tiny delegation wrapper around `_read_first_user_content()`.

Target shape:

```python
def _first_user_matches_skill_prefix(sub_jsonl: Path) -> bool:
    try:
        return _read_first_user_content(sub_jsonl).startswith(_SKILL_FORK_FIRST_USER_PREFIX)
    except Exception:
        return False
```

### Why this is good

- removes true local duplication
- reduces drift risk between two JSONL readers in the same module
- preserves current behavior

### Why this is regression-safe

- `_read_first_user_content()` already implements the same string/list handling
- wrapper keeps broad `except Exception` behavior
- no caller contract changes
- existing harvester tests already pin skill-fork behavior

### Validation

Run the full focused test net above.

## Change 2: Use the canonical validator import in core runtime code

### File

- `scripts/earnings/earnings_orchestrator.py`

### Current situation

Core runtime code still imports:

```python
from validate_attribution import validate_attribution_result
```

But the canonical module is now `validate_learning.py`, and `validate_attribution.py` is only a compatibility shim.

### Required change

Change only the **core runtime import** in `earnings_orchestrator.py` to:

```python
from validate_learning import validate_attribution_result
```

### Why this is good

- makes core runtime point at the canonical module
- leaves the alias file in place for compatibility
- reduces conceptual debt without breaking helper scripts

### Why this is regression-safe

- function name stays the same
- module contents are the same canonical validator
- compatibility shim remains for helpers/tests that still import it

### Important constraint

Do **not** remove the alias module in this revamp.

### Post-change note

After this import switch lands, the shim should have **zero core runtime consumers**.

That does **not** mean it is safe to remove immediately, because:

- helper / one-off scripts may still be migrated later
- the alias may still be intentionally referenced by dedicated compatibility tests

Treat this change as the beginning of the shim sunset, not the end of it.

## Change 3: Delete the dead legacy guidance + news thinking stack

### Files

- `.claude/hooks/build-thinking-on-complete.sh`
- `scripts/earnings/build-guidance-thinking.py`
- `.claude/skills/earnings-orchestrator/scripts/build-guidance-thinking.py`
- `scripts/earnings/build-news-thinking.py`
- `.claude/skills/earnings-orchestrator/scripts/build-news-thinking.py`

### Current situation

This stack targets the old layout:

- `Companies/{TICKER}/thinking/{QUARTER}/...`

It is not part of the active runtime path anymore. The only non-archive references are self-references and the dormant hook script itself.

The `build-news-thinking` pair is same-era as the `build-guidance-thinking` pair (identical old-layout target, same dormant-hook wiring pattern) and is only referenced by the dormant path.

### Required change

**Delete all 5 files** in the same cleanup. Do not archive in-tree.

### Why delete, not archive

Archiving in-tree was considered and **rejected**:

- whole-repo grep/search would still return hits inside `archive/`, so every future bot has to re-reason "is this live?" — exactly the fake complexity this revamp removes
- git history already is the audit trail (`git log --follow -- <path>`, `git show <sha>:<path>`); an in-tree archive adds no recovery capability that git doesn't already provide
- these files target a retired layout (`Companies/{TICKER}/thinking/{QUARTER}/...`), not a paused feature — there is no plausible resurrection path without a rewrite
- the revamp's stated goal is "the codebase reflects the real architecture instead of mixed old/new paths"; archiving violates that goal, deleting satisfies it

Archiving is therefore not an acceptable alternative for this cleanup.

### Why this is good

- removes truly obsolete code
- reduces confusion for future bots
- eliminates the biggest source of fake architectural complexity

### Why this is regression-safe

- active settings do not invoke `build-thinking-on-complete.sh`
- active runtime uses `thinking_harvester.py`, not `build-guidance-thinking.py`
- current canonical guidance path is:
  - `extraction_worker.py`
  - `harvest_guidance_sessions.py`
  - `thinking_harvester.py`

### Bytecode note

If matching orphaned bytecode files exist after removal, clean up only the stale targets, for example:

- `build-guidance-thinking*.pyc`
- `build-news-thinking*.pyc`

Do **not** blindly remove the whole `__pycache__` directory in the skill scripts folder, because it may also contain bytecode for still-live modules (notably `build-thinking-index*.pyc`, which is intentionally retained — see the matching non-goal below).

### Important constraint

This cleanup does **not** mean guidance canonicalization is inline yet. It only removes the old obsolete path.

## Explicit Non-Goals

These are the tempting changes that should **not** be part of this revamp.

## Do not move `_truncate_safe_fence()` into `thinking_blocks.py`

### Why not

Yes, it is duplicated between:

- `scripts/earnings/thinking_harvester.py`
- `scripts/earnings/obsidian_capture_adapter.py`

But `thinking_blocks.py` is the shared **parser** module. Moving markdown/fence rendering helpers there makes the module less coherent.

This would be a DRY win on paper but a boundary regression in practice.

### Keep instead

Leave the two local copies alone.

## Do not move `_yaml_scalar()` into `thinking_blocks.py`

### Why not

Yes, it is duplicated between:

- `scripts/earnings/thinking_harvester.py`
- `scripts/earnings/result_md_renderer.py`

But this is frontmatter-rendering logic, not transcript parsing logic.

If these are ever unified, they should go into a dedicated markdown/frontmatter utility module, **not** into the parser.

That is outside this cleanup.

### Keep instead

Leave the two local copies alone.

## Do not mutate `parse_session_blocks()` just to eliminate `_build_agent_linkage()`

### Why not

Adding extra outer-entry linkage metadata to parser output is possible, but it changes the shared parser contract for:

- hook adapter
- harvester
- parser tests

That is not a cleanup cut. It is a shared-module behavior extension.

Not worth the risk in this revamp.

## Do not remove `harvest_guidance_sessions.py`

### Why not

It is currently part of the real live guidance canonicalization path.

Removing it would break guidance company-tree thinking generation.

## Do not remove compatibility aliases yet

Do not remove in this revamp:

- `validate_attribution.py`
- `get_attribution_paths()`
- `finalize_attribution_result()`

They still have live helper-script/tests consumers.

### Sunset rule for `validate_attribution.py`

Safe removal target:

- after Change 2 has shipped
- after one release cycle
- and only if grep shows no remaining non-test consumers

If a dedicated alias-compatibility test is still intentionally present at that point, remove or rewrite the test in the same change that removes the shim.

## Do not refactor the defensive harvester helpers

Keep as-is:

- `_validate_harvest_args()`
- `_locate_subagent_files()`
- `_is_skill_fork()`
- `_tool_use_annotation()`

These may look verbose, but the current structure is readable and heavily exercised by tests.

## Do not “fix” guidance split ownership in this cleanup

Guidance split ownership is the main architectural rough edge, but it is a **separate structural change**, not a safe cleanup.

Do not bundle it into this revamp.

## Do not remove the `build-thinking-index` stack in this revamp

### Files intentionally retained

- `scripts/build-thinking-index.py`
- `scripts/build-thinking-index.sh`
- `.claude/skills/earnings-orchestrator/scripts/build-thinking-index.py`

### Why not

Although these files are same-era as the dead guidance/news-thinking builders, they are still referenced by the active `.claude/skills/earnings-attribution/SKILL.md:438`:

```
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/build-thinking-index.py {accession_no}
```

Removing them in this cleanup would fail the 0%-regression bar because the active attribution skill still invokes them.

If these should ever be removed, it must happen in a separate change that first retires or rewrites that skill call site.

## Do not archive the one-shot migration tooling in this revamp

### Files intentionally left in place

- `scripts/migrate_unified_layout.py`
- `scripts/earnings/test_migrate_unified_layout.py`

### Why not

Archiving them is not dangerous — they have zero live imports — but it also gives no production benefit. The move only shifts operator / test paths for historical tooling without improving live runtime behavior.

Under this revamp's strict standard (maximum minimalism, zero regression risk, production-grade), "safe but pointless" changes do not belong in the approved set. If repo-hygiene housekeeping is ever done separately, that is a different exercise.

### Keep instead

Leave both files where they are. The `.migration-manifest.json` in the vault continues to cover any reverse need.

## Do not consolidate the 3 A/B scripts

### Files

- `scripts/run_ab_baseline.py`
- `scripts/run_nvda_ab_sequential.py`
- `scripts/run_burl_ab_sequential.py`

### Why not

They look DRY-tempting at a glance, but they are not pure ticker-constant clones:

- NVDA uses `events[:5]` (oldest 5 quarters)
- BURL uses `events[-5:]` with a `base_idx = len(events) - 5` offset for `prev_8k_ts` tracking
- Event-window selection logic and index semantics differ by script

Unifying them would require a parameterization layer roughly the same total size, with added indirection. Not a lean cleanup — leave as-is.

## Recommended Implementation Order

Apply in this exact order:

1. simplify `_first_user_matches_skill_prefix()` in `thinking_harvester.py`
2. switch `earnings_orchestrator.py` to import from `validate_learning`
3. delete the dead legacy guidance + news thinking stack

## Commit Strategy

Use one commit per logical change:

1. `refactor(thinking-harvester): dedupe first-user skill prefix reader`
2. `refactor(orchestrator): import canonical learning validator directly`
3. `cleanup(obsidian): remove dead legacy guidance + news thinking builders`

This keeps every cleanup independently revertible.

## Validation Gate

After each behavior-preserving code change, run:

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest \
  scripts/earnings/test_thinking_blocks.py \
  scripts/earnings/test_obsidian_capture_adapter.py \
  scripts/earnings/test_obsidian_capture_hook_smoke.py \
  scripts/earnings/test_result_md_renderer.py \
  scripts/earnings/test_thinking_harvester.py \
  scripts/test_harvest_guidance_sessions.py -q
```

Expected:

- all tests pass
- no snapshot/golden drift
- only the existing Neo4j deprecation warnings may appear

For the dead-code removal step, also run:

```bash
rg -n "build-guidance-thinking|build-news-thinking|build-thinking-on-complete" .claude scripts
```

Expected after cleanup:

- zero hits for `build-guidance-thinking`, `build-news-thinking`, and `build-thinking-on-complete` anywhere under `.claude/` or `scripts/`
- the only remaining references allowed to survive are historical doc snapshots outside these trees (e.g. `docs/claude/earnings-orchestrator-review-2026-02-01.md`), which are intentionally frozen as dated reviews
- `build-thinking-index` is intentionally NOT in this grep — it is still referenced by the active `earnings-attribution/SKILL.md` and must survive this cleanup (see non-goal)

## Success Criteria

This revamp is successful if all of the following are true:

1. active runtime behavior is unchanged
2. active tests stay green
3. dead legacy guidance- and news-thinking code + its dormant hook wrapper are no longer sitting in the live surface (`build-thinking-index` stack intentionally retained per non-goal)
4. the core runtime points at canonical modules where possible
5. no shared parser contract was changed
6. no guidance ownership rewrite was attempted

## Final Instruction To The New Bot

Be conservative.

This cleanup is **not** a “make everything DRY” exercise. The right result is:

- smaller live surface
- clearer ownership
- zero behavior drift

If a change requires touching shared parser semantics, changing guidance ownership, or removing compatibility shims that still have callers, it does **not** belong in this revamp.


---

# Appendix B — Obsidian Implementation Checklist (formerly `obsidian_implementation_checklist.md`)

> **Status**: Merged into this file on 2026-04-19 (was `.claude/plans/obsidian_implementation_checklist.md`).
> Section numbering below is SELF-CONTAINED to this appendix — do not confuse with obsidian_thinking.md §N or Appendix A §N.


  Plan is implementation-ready. All 10 locked decisions + the fixture/meta.json fix are in place. No structural gaps remain. Below is
  the exact TDD route — test-first for every new file, test-alongside for every edit, ending with a live end-to-end smoke test.

  ---
  TDD Route — Red → Green → Refactor, phase by phase

  Each phase has: (T) test written first → (I) implementation → (V) validation gate that MUST be green before moving to next phase.

  Phase 0 — Pre-flight snapshot + fixtures

  Actions (no tests yet):
  - git stash or confirm clean tree baseline.
  - Create scripts/earnings/tests/fixtures/.
  - Copy the 3 session JSONLs + both *.jsonl AND *.meta.json for each session's subagent tree (per fixture-completeness invariant).
  - Run find scripts/earnings/tests/fixtures -name "*.meta.json" | wc -l — expect 6 + 2 + 1 = 9 meta.json files (6 learner + 2 guidance
  + 1 predictor).

  V-gate: fixture dir exists with correct counts; no code changes yet.

  ---
  Phase 1 — config/pipeline_contracts.py (~30 lines)

  (T) Write first: 3 assertions at top of test_thinking_harvester.py (only the registry section runnable initially):
  def test_registry_has_three_types():         assert KNOWN_TYPES == frozenset({"guidance","prediction","learning"})
  def test_experiment_name_requires_prefix():  validate_experiment_name("prediction", "prediction_no_lessons")  # must not raise
  def test_unknown_type_rejected():            with pytest.raises(ValueError): validate_experiment_name("prediction",
  "learning_variant")
  Run → ImportError (expected red).

  (I) Create config/pipeline_contracts.py with KNOWN_TYPES frozenset + validate_experiment_name().

  (V-gate): 3 tests pass. Any type outside KNOWN_TYPES or any experiment_name not starting with {parent_type}_ raises ValueError.

  Edge cases covered: unknown thinking_type, missing prefix, case mismatch ("Prediction" ≠ "prediction"), empty string.

  ---
  Phase 2 — scripts/earnings/thinking_blocks.py (~60 lines)

  (T) Write first: fixture-based test cases in test_thinking_blocks.py:
  1. Parse learner fixture → 6 thinking blocks with chars totaling 17,682
  2. Parse guidance fixture → 0 visible thinking blocks, 4 redacted (thinking_redacted kind for blocks with empty content + signature
  key)
  3. Parse predictor primary → 2 thinking blocks, 177 chars
  4. Parse predictor skill-fork → 4 text blocks, largest 1,926 chars, 0 thinking
  5. Ordered by timestamp (assert strict monotonicity)
  6. tool_use + tool_result kinds both surfaced (don't lose pairing info)

  Run → ImportError (red).

  (I) Implement parse_session_blocks(jsonl_path) -> list[Block] where Block = {kind, ts, content, meta} and kind ∈ {thinking,
  thinking_redacted, text, tool_use, tool_result}.

  (V-gate): all 6 cases pass. Also run obsidian_capture.py hook against a mock SubagentStop input and diff output against a
  pre-migration golden — zero behavior change for the hook's block-parsing path (Phase 9 imports this module).

  Edge cases covered: redacted thinking detection, empty content preserved with signature, timestamp ordering, malformed JSONL lines
  skipped gracefully (don't crash on bad line).

  ---
  Phase 3 — scripts/earnings/result_md_renderer.py (~100 lines)

  (T) Write first: golden-output tests in test_result_md_renderer.py:
  1. render_prediction(json_path, md_path) — fixture JSON → exact MD (byte-for-byte)
  2. render_learning — same, from a learning/result.json fixture
  3. render_baseline_experiment — same, from experiments/prediction_no_lessons/result.json
  4. render_guidance — same, tolerating minimal Neo4j-denormalized shape
  5. Determinism: render twice, assert identical bytes
  6. Frontmatter shape: autogenerated: true, source: result.json, generator: scripts/earnings/result_md_renderer.py, correct component,
  correct experiment_name (present for experiment; null/absent for component)
  7. Read-only marker: ⚠ AUTOGENERATED FROM result.json comment block present
  8. Dataview-queryable fields: ticker, quarter, direction, confidence_score, sdk_session_id all in frontmatter

  Run → ImportError (red).

  (I) Implement renderer with 4 functions + a dispatch render(component, json_path, md_path).

  (V-gate): all 8 tests pass. Determinism verified.

  Edge cases covered: missing optional fields (sdk_session_id=null → frontmatter value is null, not "None"), experiment vs component
  frontmatter split, guidance's minimal shape.

  ---
  Phase 4 — scripts/earnings/thinking_harvester.py (~220 lines) — the most complex

  (T) Write first: 11+ test cases in test_thinking_harvester.py (extends Phase 1's file):

  ┌─────┬────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────────────────┐
  │  #  │          Case          │                                            Assertion                                             │
  ├─────┼────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ a   │ EMBED-visible (learner │ thinking_blocks=6, thinking_chars=17,682; 6 subagent files materialized; each named              │
  │     │  fixture)              │ {subagent_type}_{agentId[:8]}.md; all 6 subagents labeled correctly via agentId linkage          │
  ├─────┼────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ b   │ EMBED-redacted         │ redacted_thinking_blocks=4, falls back to 1,684 text chars; "content redacted (signed)" marker   │
  │     │ (guidance)             │ present; 2 subagent files materialized                                                           │
  ├─────┼────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ c   │ FORK (predictor)       │ skill-fork JSONL content composes thinking.md (3,604 text chars + primary's 177 thinking chars); │
  │     │                        │  NO subagents/ dir emitted                                                                       │
  ├─────┼────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ d   │ agentId linkage is     │ synthetic fixture where completion order ≠ spawn order (simulate alphavantage rate-limit         │
  │     │ load-bearing           │ fast-fail) — assert each subagent still labeled correctly via agentId, not by position           │
  ├─────┼────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ e   │ Experiment routing         │ experiment_name="prediction_no_lessons" → writes to                                          │
  │     │                            │ experiments/prediction_no_lessons/thinking.md, not prediction_no_lessons/thinking.md         │
  ├─────┼────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
  │ f   │ Idempotent re-harvest      │ run harvest twice on same session → second run overwrites cleanly, subagents/ dir contents   │
  │     │                            │ identical (no duplicates, no orphans from first run)                                         │
  ├─────┼────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
  │ g   │ Missing session_id →       │ harvest called with session_id=None → logs WARNING, returns without raising, no file written │
  │     │ WARNING                    │                                                                                              │
  ├─────┼────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
  │ h   │ Predictor FORK produces NO │ explicit negative test: assert subagents/ dir does NOT exist after FORK harvest              │
  │     │  subagents/                │                                                                                              │
  ├─────┼────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
  │ i   │ Skill-fork dual-signal     │ predictor fixture triggers both meta.json=general-purpose AND first-user="Base directory..." │
  │     │ agreement                  │  → no WARNING logged                                                                         │
  ├─────┼────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
  │ j   │ Skill-fork dual-signal     │ synthetic fixture where meta.json says "general-purpose" but first-user does NOT match →     │
  │     │ disagreement               │ WARNING logged, harvest still proceeds (don't fail)                                          │
  ├─────┼────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
  │ k   │ Missing meta.json          │ delete one fixture's meta.json → harvester falls back to first-user scan + logs WARNING      │
  │     │                            │ about missing meta; test doesn't crash                                                       │
  ├─────┼────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
  │ l   │ Orphan Agent tool_use      │ synthetic fixture: Agent tool_use without matching tool_result → WARNING in thinking.md, no  │
  │     │                            │ subagent file for it, other subagents still processed                                        │
  ├─────┼────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
  │ m   │ Fixture-completeness       │ for every agent-<id>.jsonl in fixtures, assert a sibling agent-<id>.meta.json exists (guards │
  │     │ invariant                  │  against cp-omission regression)                                                             │
  └─────┴────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────┘

  Run → ImportError (red).

  (I) Implement harvest(*, thinking_type, ticker, quarter, session_id, experiment_name=None, vault_root=None):
  - Pattern detection: Skill tool_use in primary → FORK; else Agent tool_use → EMBED (redacted vs visible determined per-block)
  - Skill-fork detection: dual-signal with WARNING on disagreement
  - Linkage: toolUseResult.agentId top-level lookup
  - Output: thinking.md with frontmatter + ordered content + tool_use annotation table
  - subagents/ only for Agent-spawned (not skill-fork content source)
  - Idempotent: clear subagents/ dir before writing

  (V-gate): all 13 tests pass. Additionally run ruff check + mypy for type safety on the harvester module.

  Edge cases covered: all 5 degraded scenarios (missing session, missing meta, dual-signal mismatch, orphan tool_use, completion-order
  skew) + happy path for all 3 patterns + experiment routing + idempotency.

  ---
  Phase 5 — scripts/migrate_unified_layout.py (~160 lines)

  (T) Write first: integration-style tests in test_migrate_unified_layout.py using a temp vault root:

  ┌─────┬──────────────────────┬────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │  #  │         Case         │                                             Assertion                                              │
  ├─────┼────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 1   │ --dry-run output   │ Prints the ops; writes no file; lists correct counts (15/30/0/45/45/1289)                            │
  ├─────┼────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 2   │ --apply happy path │ Manifest written; filesystem matches expected post-state; .migration-manifest.json schema valid      │
  ├─────┼────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 3   │ --apply            │ Running --apply twice → second run detects already-migrated + records no new ops (manifest says "0   │
  │     │ idempotency        │ steps")                                                                                              │
  ├─────┼────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 4   │ --reverse          │ After --apply then --reverse, filesystem state == pre-apply state (byte-for-byte on json files,      │
  │     │ round-trip         │ os.stat on dirs)                                                                                     │
  ├─────┼────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 5   │ Baseline-absent    │ With no ab_baseline/ in fixture vault, --apply records 0 baseline-move ops; --reverse does NOT       │
  │     │ path               │ recreate ab_baseline/                                                                                │
  ├─────┼────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 6   │ Baseline-present   │ With synthetic ab_baseline/* in fixture, --apply records the moves; --reverse restores ab_baseline/  │
  │     │ path               │ exactly                                                                                              │
  ├─────┼────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 7   │ Null-stamp scope   │ After --apply, all 45 result.json files (3 × 15) have sdk_session_id key present with value null     │
  ├─────┼────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 8   │ result.md scope    │ After --apply, all 45 result.md sidecars exist with correct frontmatter                              │
  ├─────┼────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 9   │ Extraction filter  │ 8 anomalous *_extraction-primary-agent_* files untouched; Extraction Runs.md untouched; .capture.log │
  │     │                    │  untouched                                                                                           │
  ├─────┼────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 10  │ Mid-run failure    │ Inject failure at step 20 of 1,400 → script halts, manifest has first 19 steps, remaining steps      │
  │     │                    │ printed; --reverse on partial manifest restores first 19                                             │
  └─────┴────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────────┘

  Run → ImportError (red).

  (I) Implement the migration script with all 3 modes.

  (V-gate): all 10 tests pass. Then run --dry-run against the real vault (read-only, no changes) and visually verify counts match
  addendum: 15 / 30 / 0 / 45 / 45 / 1,289.

  Edge cases covered: all 3 modes, idempotency, conditional baseline moves, partial-run recovery, anomalous-file filtering.

  ---
  Phase 6 — Edit scripts/earnings/earnings_orchestrator.py

  (T) Write first / alongside: test_orchestrator_integration.py:

  ┌─────┬─────────────────────────────────────────────┬──────────────────────────────────────────────────────────────────────────────┐
  │  #  │                    Case                     │                                  Assertion                                   │
  ├─────┼─────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────┤
  │ 1   │ get_prediction_paths() after edit           │ bundle_path == events/{Q}/context_bundle.json (quarter root), not under      │
  │     │                                             │ prediction/                                                                  │
  ├─────┼─────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────┤
  │ 2   │ get_learning_paths() (renamed)              │ base_dir ends in learning/, not attribution/                                 │
  ├─────┼─────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────┤
  │ 3   │ get_learning_paths()['context_bundle_path'] │ == events/{Q}/context_bundle.json (quarter root)                             │
  ├─────┼─────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────┤
  │ 4   │ finalize_attribution_result alias           │ Thin alias still callable; emits DeprecationWarning optionally               │
  ├─────┼─────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────┤
  │ 5   │ finalize_learning_result with session_id    │ payload.sdk_session_id stamped; result.md generated; harvest called (mock)   │
  ├─────┼─────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────┤
  │ 6   │ finalize_prediction_result with session_id  │ Same as above for prediction                                                 │
  ├─────┼─────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────┤
  │ 7   │ _run_predictor_via_sdk returns tuple        │ (result: str, session_id: str | None) — type-check the return                │
  ├─────┼─────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────┤
  │ 8   │ Harvester failure must not block finalize   │ Inject exception inside harvest call → finalize still writes result.json +   │
  │     │                                             │ result.md; WARNING logged                                                    │
  ├─────┼─────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────┤
  │ 9   │ SDK session_id hybrid capture               │ Mock messages expose .session_id directly → captured; mock with only         │
  │     │                                             │ data.get("session_id") → also captured                                       │
  └─────┴─────────────────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────┘

  (I) Make the edits per insertion-point map I compiled in the pre-flight.

  (V-gate): 9 tests pass + existing tests still pass (run full pytest scripts/earnings/).

  Edge cases covered: harvester-failure isolation, dual SDK-version capture, rename alias transparency.

  ---
  Phase 7 — Edit 3 A/B scripts identically

  (T) Write first: test_ab_baseline_paths.py:
  1. Reads attribution path from events/{Q}/learning/result.json (not attribution/)
  2. Reads context_bundle from quarter root (not under prediction/)
  3. Unpacks session_id tuple from run_predictor_via_sdk
  4. Calls harvester with experiment_name="prediction_no_lessons"

  (I) Apply 5 identical edits to each of the 3 A/B scripts.

  (V-gate): tests pass; diff the 3 scripts' delta patches — they should be structurally identical (differ only in ticker constant +
  QUARTERS list).

  ---
  Phase 8 — Validator rename + hook path update

  (T) Write first: Hook round-trip test using subprocess.run on the hook script:
  1. Input JSON with tool_input.file_path = ".../learning/result.json" + valid payload → {} (allow)
  2. Input JSON with same path + malformed payload → {"decision":"block","reason":...}
  3. Input JSON with .../attribution/result.json (OLD path) → {} (not matched — passes through, since the rename is part of the cutover)

  (I) — **MODULE rename only; function name stays `validate_attribution_result`** (it maps to schema `attribution_result.v2` which is not renamed; the function is schema-shaped, not path-shaped):
  - git mv scripts/earnings/validate_attribution.py scripts/earnings/validate_learning.py
  - Create alias scripts/earnings/validate_attribution.py with single line: `from validate_learning import *  # noqa: F401,F403 — 1-release alias` (absolute import; scripts/earnings has no __init__.py)
  - git mv .claude/hooks/validate_attribution_output.py .claude/hooks/validate_learning_output.py
  - Update hook:
      - path match: `"/attribution/result.json"` → `"/learning/result.json"`
      - import line: `from validate_attribution import validate_attribution_result` → `from validate_learning import validate_attribution_result` (module changed, function unchanged)
  - Update .claude/settings.json:79 hook command path (validate_attribution_output.py → validate_learning_output.py)

  **Why function name is NOT renamed**: the three requirements can only coexist consistently if the function name stays. (1) Alias file is `from validate_learning import *` — re-exports every public name. (2) If we renamed the function to `validate_learning_result`, then the `*` re-export would expose only that name and `from validate_attribution import validate_attribution_result` would fail — contradicting backward compat. (3) Keeping the function name as `validate_attribution_result` inside the renamed module lets the `*` re-export preserve it through the alias, all three claims hold.

  (V-gate): hook tests pass; `python -c "from validate_attribution import validate_attribution_result"` still succeeds via alias + `*` re-export; `python -c "from validate_learning import validate_attribution_result"` also succeeds (new canonical import path); existing orchestrator line `from validate_attribution import validate_attribution_result` unchanged — transparent.

  Edge cases covered: absolute-import correctness (no silent ModuleNotFoundError from attempted relative form), hook path match on new `/learning/` literal, settings.json registration points to renamed hook, schema-shaped function name preserved for 1-release overlap.

  ---
  Phase 9 — Edit .claude/hooks/obsidian_capture.py (4 changes)

  (T) Write first: test_obsidian_capture.sh or Python hook-spawner test:
  1. Agent_type=extraction-primary-agent + source_id → file lands in pipeline/extractions/guidance/{date}_{sid}.md, no _extraction_ in
  filename
  2. Agent_type=earnings-learner → hook exits 0, writes nothing (skip-list)
  3. Agent_type=earnings-attribution → hook exits 0, writes nothing (skip-list FROZEN strings)
  4. Agent_type=earnings-prediction → hook exits 0, writes nothing
  5. Agent_type=general-purpose → file lands in agents/ (fallback unchanged)
  6. Uses shared parse_session_blocks (integration — compare block counts in output to Phase 2's parser output)

  (I) Apply 4 edits:
  - FOLDER_ROUTING updates (line 379-380)
  - SKIP_AGENT_TYPES near top of main (line ~8-15)
  - filename drops _extraction_ (line 397)
  - from scripts.earnings.thinking_blocks import parse_session_blocks (replace inline loop ~76-139)

  (V-gate): 6 hook tests pass + run 1 real SubagentStop event (e.g., via a quick /extract trigger with a trivial source) and verify
  output lands correctly.

  Edge cases covered: FROZEN skip-list strings, no-source-id fallback path (the 6 anomalous historical files at `pipeline/extractions/*_extraction-primary-agent_*.md` remind us this branch has fired in production), agents/ fallback unchanged.

  ---
  Phase 10 — Skill files (4) + plan docs (12) mechanical sweep

  (T) Write first: a grep-based pre/post sanity check:
  # Before: count "attribution/" path literals in each skill file + plan doc
  # After: count should decrease OR match rewrites; prose mentions of "attribution" concept should be UNCHANGED.

  (I) Path-literal sweep per the discipline header. For each of the 16 files (4 skills + 12 plan docs):
  - Edit path literals attribution/ → learning/, prediction/context_bundle.* → context_bundle.* (quarter root)
  - LEAVE prose mentions (causal attribution, return attribution, attribution analysis, context bundle concept)

  (V-gate): git diff --stat reasonable per-file change counts; manual spot-check 3 files (learner.md, earnings-orchestrator.md,
  trade-execution-system.md — the largest) for any false-positive prose rewrites.

  ---
  Phase 11 — Migration dry-run against real vault

  Run (read-only, no state change):
  python scripts/migrate_unified_layout.py --dry-run

  (V-gate): stdout lists exact op counts reflecting the POST-WIPE state: **15 (rename_dir) / 30 (context_bundle) / 0 (ab_baseline — absent) / 33 (null-stamps: 15 pred + 3 learn + 15 exp) / 33 (result.md) / 1,289 (extractions)**. Zero unexpected files touched. Zero references to `Extraction Runs.md`, `.capture.log`, or the 6 anomalous `_extraction-primary-agent_` files. Dry-run should also LOG the 1 legacy AVGO Q2_FY2024 prediction stub as "skipped — no schema_version" + the 2 AVGO legacy quarters (Q2/Q3 FY2024) as "skipped — no context_bundle.json".

  ---
  Phase 12 — Apply migration + assert post-state

  python scripts/migrate_unified_layout.py --apply

  Run validation script (write as part of the test suite, run automatically):
  1. `find -L earnings-analysis/Companies -maxdepth 5 -type d -name "attribution"` → count **0**
  2. `find -L earnings-analysis/Companies -maxdepth 5 -type d -name "learning"` → count **15** (all 15, including 12 empty dirs that were renamed structurally)
  3. `find -L earnings-analysis/Companies -maxdepth 4 -name "context_bundle.json"` → count **15** (quarter root; 2 AVGO legacy quarters with `context.json` untouched at pre-existing locations)
  4. `find -L earnings-analysis/Companies -maxdepth 5 -path "*prediction/context_bundle.json"` → count **0** (all promoted)
  5. All **33 modern** result.json files (15 prediction + 3 learning + 15 experiment) have `sdk_session_id` field present (value = valid session id OR null). The 1 legacy AVGO Q2_FY2024 stub + the 12 empty learning dirs are NOT stamped.
  6. All **33 modern** result.md sidecars exist with `autogenerated: true` frontmatter. Legacy stub + empty dirs have NO sidecar.
  6a. Count check: `find -L earnings-analysis/Companies -maxdepth 5 -name "result.md" -type f | wc -l` == **33**.
  7. `find pipeline/extractions -maxdepth 2 -type f -name "*.md" \| wc -l` == **1,296** exactly (1,289 moved into `guidance/` + 6 anomalous `*_extraction-primary-agent_*.md` at root + 1 `Extraction Runs.md` at root). Non-`.md` files in root: 1 (`.capture.log`). Total files `-type f` in `pipeline/extractions/` tree = 1,297 (1,289 + 6 + 1 + 1). Verified pre-migration counts: 1,289 conforming + 6 anomalous + 1 manual note + 1 log = 1,297 total.
  8. .migration-manifest.json exists with expected op counts

  (V-gate): all 8 validation checks pass.

  ---
  Phase 13 — Reverse migration DRY RUN only

  python scripts/migrate_unified_layout.py --reverse --dry-run

  (V-gate): output describes exactly the inverse of the applied ops. Do not actually reverse — we want to keep the migration applied.

  This confirms reverse is wired up without disturbing state.

  ---
  Phase 14 — Live end-to-end smoke test

  Fresh BURL Q4_FY2025 end-to-end:
  python3 scripts/earnings/earnings_orchestrator.py BURL <Q4_FY2025-accession> --save --predict --learn

  Then A/B baseline:
  python3 scripts/run_burl_ab_sequential.py  # or a single-quarter variant

  Validation per the 12+ acceptance checks in the plan (now 14 with 3d/3e added):
  1-3. sdk_session_id stamped on all three fresh result.json files
  3a. result.md sidecars with marker + frontmatter
  3b-3c. Historical baseline files still intact with null session_id
  3d. 45 null-stamp coverage
  3e. 45 sidecar coverage
  4-5. prediction + experiments/prediction_no_lessons thinking.md sourced from skill-fork, NO subagents/ dir
  6-7. learning/thinking.md + learning/subagents/.md with correct agentId-based filenames
  8. No top-level attribution/, no ab_baseline/, no thinking/ parent
  9. Zero API 400s; runtime timings comparable to pre-change
  10. obsidian_capture.py: extraction captures route to guidance/ with simplified filenames; earnings- skipped
  11. No regression on AVGO/NVDA/BURL existing artifacts (git diff shows only expected files changed)
  12. pytest scripts/earnings/ all green

  (V-gate): ALL 14 acceptance checks green. If any red, halt + diagnose.

  ---
  Phase 15 — Commit

  Single commit title: feat(obsidian): unified thinking capture + events/ layout migration

  (V-gate): git diff --stat matches expected scope (7 new + ~28 edited files). Commit message body references obsidian_thinking.md plan.

  ---
  Explicit edge-case coverage matrix

  ┌──────────────────────────────────────┬───────────────────────┬─────────────────────────────────────────────────────────────────┐
  │              Edge case               │     Phase tested      │                               How                               │
  ├──────────────────────────────────────┼───────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ SDK returns session_id=None          │ 4 (case g) + 6 (case  │ Harvest called with None → WARNING, no crash                    │
  │                                      │ 9)                    │                                                                 │
  ├──────────────────────────────────────┼───────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ SDK exposes .session_id as direct    │ 6 (case 9)            │ Mock AssistantMessage; hybrid capture path primary              │
  │ attr                                 │                       │                                                                 │
  ├──────────────────────────────────────┼───────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ data.get(...)                          │                      │                                                                │
  ├────────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────┤
  │ Redacted thinking (empty + signature)  │ 2 + 4 (case b)       │ Fixture with empty thinking + signature key detected + marker  │
  │                                        │                      │ emitted                                                        │
  ├────────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────┤
  │ FORK with NO nested agents             │ 4 (case c, h)        │ Predictor fixture — no subagents/ dir                          │
  ├────────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────┤
  │ FORK with nested Agents                │ 4 (can add case n)   │ Synthetic fixture if needed                                    │
  ├────────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────┤
  │ EMBED completion order ≠ spawn order   │ 4 (case d)           │ Synthetic fixture — agentId linkage correct despite skew       │
  ├────────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────┤
  │ Orphan Agent tool_use                  │ 4 (case l)           │ Synthetic fixture — WARNING, continue                          │
  ├────────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────┤
  │ meta.json missing                      │ 4 (case k)           │ Delete meta from one fixture — fall back + WARNING             │
  ├────────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────┤
  │ meta.json + first-user disagree        │ 4 (case j)           │ Synthetic fixture — WARNING, continue                          │
  ├────────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────┤
  │ Idempotent re-harvest                  │ 4 (case f)           │ Run harvest twice, state identical                             │
  ├────────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────┤
  │ Idempotent re-migration                │ 5 (case 3)           │ --apply twice, 2nd run is no-op                                │
  ├────────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────┤
  │ Partial migration failure              │ 5 (case 10)          │ Inject failure mid-run, reverse restores                       │
  ├────────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────┤
  │ Baseline-absent quarters (current      │ 5 (case 5)           │ --apply records 0 baseline ops, --reverse leaves alone         │
  │ reality)                               │                      │                                                                │
  ├────────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────┤
  │ Baseline-present quarter (future-safe) │ 5 (case 6)           │ Synthetic ab_baseline/ → migrated + reversible                 │
  ├────────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────┤
  │ Anomalous 8 + manual notes in          │ 5 (case 9)           │ Left in place; 11 (dry-run verify)                             │
  │ extractions                            │                      │                                                                │
  ├────────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────┤
  │ Validator alias transparency           │ 8                    │ Old import path still works                                    │
  ├────────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────┤
  │ Hook skip-list for FROZEN strings      │ 9 (cases 2-4)        │ 3 earnings-* agent_types skipped                               │
  ├────────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────┤
  │ Harvester failure doesn't block        │ 6 (case 8)           │ Inject exception, finalize still writes                        │
  │ finalize                               │                      │                                                                │
  ├────────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────┤
  │ Determinism of renderer                │ 3 (case 5)           │ Run twice, assert byte-equal                                   │
  ├────────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────┤
  │ Fixture completeness invariant         │ 4 (case m)           │ Assert every .jsonl has sibling .meta.json                     │
  └────────────────────────────────────────┴──────────────────────┴────────────────────────────────────────────────────────────────┘

  ---
  Abort criteria (any of these = STOP, diagnose before proceeding)

  - Phase 1–5 gates any red → do not edit production code.
  - Phase 6–9 gates red → revert just that file, retry.
  - Phase 11 dry-run counts don't match addendum expectations → investigate BEFORE --apply.
  - Phase 12 apply produces unexpected filesystem deltas → run --reverse immediately.
  - Phase 14 acceptance checks any red → halt; do not commit; diagnose.

  ---

---

# Appendix C — Guidance Thinking Harvester Runbook (formerly `harvest-guidance-setup.md`)

> **Status**: Operational runbook merged into this file on 2026-04-19 (was `.claude/plans/harvest-guidance-setup.md`).
> Note: This appendix is a runbook (operational reference), not a design plan.
> Section numbering below is SELF-CONTAINED to this appendix.


External post-hoc harvester that captures guidance-extraction thinking into
the Obsidian vault **without touching the K8s extraction pipeline**. Runs on
the minisforum host.

## What it does

Watches `/home/faisal/.claude/projects/-home-faisal-EventMarketDB/*.jsonl`
(top-level only) for completed `/extract ... TYPE=guidance` sessions. When
one completes, it derives the quarter and writes
`earnings-analysis/Companies/{TICKER}/events/{Q}/guidance/thinking_{asset}.md`
+ `subagents_{asset}/`.

**Zero coupling to:** `scripts/extraction_worker.py`,
`scripts/trigger-extract.py`, `scripts/guidance_trigger_daemon.py`,
`k8s/processing/*.yaml`, or `.claude/settings.json`.

## Modes

```bash
# Manual single-session harvest
venv/bin/python scripts/harvest_guidance_sessions.py one <SESSION_ID>

# One-shot reconciliation (recommended via cron every 2 hours)
venv/bin/python scripts/harvest_guidance_sessions.py scan --since-hours 2

# Long-running event-driven watcher (requires watchdog package)
venv/bin/python scripts/harvest_guidance_sessions.py watch \
    --debounce-seconds 15
```

The `scan` and `one` modes have **zero Python package dependencies** beyond
what's already in the repo's venv. The `watch` mode requires the `watchdog`
package; it exits cleanly with install instructions if missing.

## Install steps (minisforum host only)

### Option 1 — Cron reconciliation (simplest, no extra packages)

Add to `/etc/cron.d/harvest-guidance`:

```cron
# Reconcile guidance thinking harvest every 2 hours
0 */2 * * * faisal cd /home/faisal/EventMarketDB && \
    venv/bin/python scripts/harvest_guidance_sessions.py scan \
    --since-hours 3 \
    >> /home/faisal/EventMarketDB/logs/harvest-guidance.log 2>&1
```

Verify:
```bash
sudo crontab -u faisal -l | grep harvest-guidance
tail -f /home/faisal/EventMarketDB/logs/harvest-guidance.log
```

**Latency:** 0–2 h. Acceptable for audit artifacts.

### Option 2 — Event-driven watcher + reconciliation backup (recommended)

1. Install `watchdog` in the project venv (one-time):
   ```bash
   /home/faisal/EventMarketDB/venv/bin/pip install watchdog
   ```

2. Create systemd service `/etc/systemd/system/harvest-guidance.service`:
   ```ini
   [Unit]
   Description=Obsidian guidance thinking harvester (event-driven)
   After=network-online.target

   [Service]
   Type=simple
   User=faisal
   Group=faisal
   WorkingDirectory=/home/faisal/EventMarketDB
   ExecStart=/home/faisal/EventMarketDB/venv/bin/python \
       /home/faisal/EventMarketDB/scripts/harvest_guidance_sessions.py watch \
       --debounce-seconds 15
   Restart=on-failure
   RestartSec=10
   StandardOutput=append:/home/faisal/EventMarketDB/logs/harvest-guidance-watch.log
   StandardError=append:/home/faisal/EventMarketDB/logs/harvest-guidance-watch.log

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable + start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now harvest-guidance.service
   sudo systemctl status harvest-guidance.service
   ```

4. Add the cron reconciliation from Option 1 as a backup (for daemon restart
   gaps / missed inotify events):
   ```cron
   0 */2 * * * faisal cd /home/faisal/EventMarketDB && \
       venv/bin/python scripts/harvest_guidance_sessions.py scan \
       --since-hours 3 \
       >> /home/faisal/EventMarketDB/logs/harvest-guidance.log 2>&1
   ```

**Latency:** ~instant (debounce 15 s after last write).
**Idle cost:** ~20 MB RAM, 0 % CPU (sleeps on kernel inotify events).

### Disable / rollback

```bash
sudo systemctl disable --now harvest-guidance.service
sudo rm /etc/cron.d/harvest-guidance
# That's it — no pipeline code is touched.
```

## Verification

After install, trigger a guidance extraction (or wait for the next K8s worker
run) and verify:

```bash
# List recent guidance harvests
ls earnings-analysis/Companies/*/events/*/guidance/thinking_*.md

# Spot-check frontmatter of a fresh harvest
head -20 earnings-analysis/Companies/BURL/events/Q4_FY2025/guidance/thinking_8k.md

# Watch the log
tail -f logs/harvest-guidance-watch.log    # if systemd service
tail -f logs/harvest-guidance.log          # if cron only
```

Expected frontmatter fields:
```yaml
component: guidance
source_asset: 8k            # or 10q / 10k / transcript
source_id: <accession>      # or transcript id
ticker: <TICKER>
quarter: <Q>_FY<YYYY>
sdk_session_id: <uuid>
session_pattern: EMBED-visible | EMBED-redacted | FORK
```

## Troubleshooting

**Nothing harvested after a live extraction:**
- Check `tail -f logs/harvest-guidance-watch.log` for skip reasons
- Common skip causes:
  - `session not complete` → session still in progress (wait for end_turn marker)
  - `not a /extract guidance session` → correctly filtered out
  - `quarter not derivable` → Neo4j query returned no rows (ticker/fiscal data missing)
  - `already harvested` → idempotency working as designed (re-run is no-op)

**Daemon keeps restarting:**
- `journalctl -u harvest-guidance.service -n 100`
- Most likely: `watchdog` not installed → install it (Option 2 step 1)
- Or: `ImportError` on `neograph.Neo4jConnection` → check `.env` loading

**Missed events:**
- Cron reconciliation catches anything missed within the last 3 hours
- Manual backfill: `python scripts/harvest_guidance_sessions.py scan --since-hours 24`

## Pipeline-pipeline isolation guarantee

| File | Touched by this tool? |
|---|---|
| `scripts/extraction_worker.py` | **NO** |
| `scripts/trigger-extract.py` | **NO** |
| `scripts/guidance_trigger_daemon.py` | **NO** |
| `k8s/processing/extraction-worker.yaml` | **NO** |
| `k8s/processing/guidance-trigger.yaml` | **NO** |
| `.claude/settings.json` | **NO** |
| `.claude/hooks/obsidian_capture.py` | **NO** |

**All changes are additive and live in new files only.** Disabling the
harvester (systemctl disable + remove cron) leaves the guidance extraction
pipeline in its exact current state.

# Appendix D — Run Ledger (formerly `run_ledger.md`)

Production-ready lifecycle index for pipeline runs.

**Status**: LOCKED — reviewed, validated, all blockers addressed. Ready to implement in one atomic commit.

**Date**: 2026-04-19

**Scope**: Guidance extraction + prediction + learner. Three pipelines, one ledger, one human-facing index note.

---

## 1. Problem Statement

The repo has three production pipelines that produce derived artifacts under
`earnings-analysis/`:

| Component | Runtime | Writes |
|---|---|---|
| **guidance** | `scripts/extraction_worker.py` (K8s, 1→7 pods) | Guidance nodes in Neo4j + hook notes in `pipeline/extractions/guidance/*.md` + harvester thinking shards |
| **prediction** | `scripts/earnings/earnings_orchestrator.py --predict` | `events/{Q}/prediction/{result.json, result.md, thinking.md}` + subagents/ |
| **learning** | `scripts/earnings/earnings_orchestrator.py --learn` | `events/{Q}/learning/{result.json, result.md, thinking.md}` + subagents/ |

**Gaps the completed-artifact surfaces do NOT cover**:

1. **No real-time lifecycle state.** `result.md` and `thinking.md` only exist AFTER success. There's no way to see queued/running/failed jobs from the vault.
2. **No cross-pipeline browsable index.** Reviewers have to walk the file tree to enumerate recent runs across all three types.
3. **Legacy CSV trackers** (`earnings-analysis/predictions.csv`, `prediction_processed.csv`) are ad-hoc, prediction-only, and don't scale to a 796-ticker universe.

The old `pipeline/extractions/Extraction Runs.md` was a Dataview index note (renders from per-extraction-note frontmatter). It worked for extractions but was never extended to prediction/learner and didn't cover in-flight state.

---

## 2. Design Principles

1. **Separation of concerns**: machine-readable state (JSONL ledger) vs human-readable view (Markdown index). Ledger is authoritative; index is a rendering.
2. **Append-only** machine store. Each state transition = one new line. Current state = last-row-wins collapse by `run_id`. No in-place mutations.
3. **Wrap real execution boundaries**, not post-hoc finalizers. `open_run` fires BEFORE the SDK call; `close_run` fires on terminal state. A running job is observable as `status="running"` from the moment it starts.
4. **Crash-safe**: tolerate malformed JSONL lines (skip silently); atomic writes (tmp + rename) for the index note.
5. **Plugin-independent**: no Dataview dependency. Index is Python-generated static Markdown tables.
6. **Minimal code, frozen schema v1**. No per-run Markdown mirror notes. No artifact frontmatter changes.

---

## 3. Architecture — Three Layers

### Layer 1 — Authoritative Ledger

```
earnings-analysis/operations/run_ledger.jsonl
```

Append-only JSONL. Each line = one state transition.

**Size budget**: ~7,500 runs/year at production scale × ~500 bytes/row × 5 years ≈ **18 MB**.
Single file for v1. Document rotation trigger: rotate to `run_ledger_YYYY.jsonl`
when file exceeds 50 MB.

### Layer 2 — Human-Facing Index Note

```
earnings-analysis/operations/Run Index.md
```

Single Markdown file. Python-generated static tables. Four sections:

```markdown
# Run Index
_Last regenerated: <ISO timestamp>_

## In Flight (status == running)
| run_id | component | ticker | quarter | started_at |
| ... | ... | ... | ... | ... |

## Recent Predictions (last 50 by started_at DESC)
| date | ticker | quarter | direction | conf | magnitude | expected | status | run_id |
| ... |

## Recent Learners (last 50)
| date | ticker | quarter | direction_correct | actual_return | magnitude_error | primary_driver | status | run_id |
| ... |

## Recent Extractions (last 50)
| date | ticker | asset | source_id | items_extracted | items_written | enrichment | status | run_id |
| ... |
```

Regenerated on BOTH `open_run` and `close_run` — otherwise In Flight is always empty.

Atomic write via `write tmp + os.replace` — crash during regeneration never leaves a half-written index.

### Layer 3 — (Not Needed in v1)

No per-run Markdown mirror notes. No artifact frontmatter changes.
Artifacts already carry `sdk_session_id` which provides a cross-lookup key.

---

## 4. Ledger Schema (frozen v1)

Every row is a complete state snapshot for one `(run_id, transition)`. Reader
collapses by `run_id`, last-row-wins.

```json
{
  "schema_version": 1,
  "run_id": "uuid4-string",
  "component": "guidance | prediction | learning",
  "status": "running | succeeded | failed | skipped | rate_limited",
  "ticker": "BURL",
  "quarter_label": "Q3_FY2025",
  "accession_8k": "0001193125-25-294501",
  "source_id": null,
  "source_asset": null,
  "experiment_name": null,
  "sdk_session_id": null,
  "started_at": "2026-04-19T12:34:56Z",
  "finished_at": null,
  "elapsed_seconds": null,
  "artifact_dir": null,
  "result_path": null,
  "thinking_path": null,
  "error": null,
  "summary": {}
}
```

### Per-component `summary` payloads

**prediction**:
```json
{
  "direction": "long|short|no_call",
  "confidence_score": 68,
  "confidence_bucket": "low|moderate|high|extreme",
  "magnitude_bucket": "small|medium|large",
  "expected_move_range_pct": [3.0, 6.5]
}
```

**learning**:
```json
{
  "direction_correct": false,
  "actual_daily_stock_pct": -12.16,
  "magnitude_error_pct": 15.16,
  "primary_driver_category": "peer_comp_gap_share_loss"
}
```

**guidance**:
```json
{
  "items_extracted": 14,
  "items_written": 14,
  "enrichment_status": "enriched",
  "items_enriched": 3,
  "items_new_secondary": 2
}
```

The `items_written` sidecar is written by `.claude/skills/earnings-orchestrator/scripts/guidance_write_cli.py` as a list of per-item audit entries; `len(list)` is authoritative for the Neo4j write count. `extraction_worker.process_one` unlinks any prior sidecar at entry (stale-guard) so a read here always reflects the current attempt.

The `enrichment_status` enum is derived purely from the combined result file counts (no external state):
- `"no_primary"` — `primary_items == 0` (nothing to enrich)
- `"no_enrichment"` — `primary_items > 0` but `enriched_items + new_secondary_items == 0`
- `"enriched"` — at least one enriched or new secondary item
- `null` — all counts absent (unknown; don't fabricate)

### Status values (all five explicit)

| Status | Meaning | Terminal? |
|---|---|---|
| `running` | `open_run` fired; SDK call in progress | No |
| `succeeded` | Run produced expected artifacts | Yes |
| `failed` | Run raised an exception or produced no result | Yes |
| `skipped` | Run deliberately not executed (e.g., preconditions unmet) | Yes |
| `rate_limited` | SDK hit API rate limit; payload was requeued for future attempt. **A new run_id is issued on retry.** | Yes (this attempt) |

Each attempt = new `run_id`. Retries don't reuse the previous run_id — audit trail stays clean.

---

## 5. Concurrency + Safety

### Writes

```python
def append(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False) + "\n"
    with open(path, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
```

**Safe for**: multiple processes on the same host accessing the same file
(e.g., K8s extraction-worker 1→7 pods via hostPath mount to a single node).

**NOT safe for**: NFS, distributed filesystems with weak locking, or
cross-host access. Document this explicitly in the module docstring.

**Rationale**: POSIX does NOT guarantee atomic appends for regular files
regardless of write size. PIPE_BUF (4096) only applies to pipes/FIFOs.
`fcntl.flock` + `fsync` provides correct coordination on a single-host
shared filesystem.

### Reads

```python
def read_all(path):
    if not path.exists():
        return []
    rows = []
    with open(path) as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows
```

Tolerating malformed lines preserves readability across crash windows.

### Index atomic write

```python
def _write_atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)
```

---

## 6. Public API

Module: `scripts/earnings/run_ledger.py`

```python
def open_run(
    component: str,
    *,
    ticker: str,
    quarter_label: str | None = None,
    accession_8k: str | None = None,
    source_id: str | None = None,
    source_asset: str | None = None,
    experiment_name: str | None = None,
    artifact_dir: str | None = None,
) -> str:
    """Append a `running` row. Returns new run_id (uuid4)."""


def close_run(
    run_id: str,
    status: str,
    *,
    sdk_session_id: str | None = None,
    result_path: str | None = None,
    thinking_path: str | None = None,
    error: str | None = None,
    summary: dict | None = None,
) -> None:
    """Append a terminal row for an existing run_id. Also refreshes Run Index.md."""


def current_state(
    *,
    component: str | None = None,
    status: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Collapse ledger by run_id (last-row-wins); apply filters; return list."""


def refresh_index(
    ledger_path: Path | None = None,
    index_path: Path | None = None,
) -> None:
    """Read ledger, build Run Index.md content, atomic-write to index_path."""
```

Each `open_run` and `close_run` call triggers `refresh_index` synchronously.
This guarantees real-time visibility — the moment a run starts, it appears
in the In Flight section.

---

## 7. Call-Site Wiring (exact execution boundaries)

**Design rule (critical)**: wrap the OUTERMOST meaningful function boundary,
NOT individual SDK `query()` calls. One ledger run = one logical pipeline
attempt. Internal retries, derived-write recovery, validation, and
side-effect writes (result.md, lesson appends) must all resolve BEFORE the
terminal close_run fires. Otherwise the ledger can record a false success
when a post-SDK step raises.

### Prediction — wraps SDK + finalize + validate in one try block

Location: `earnings_orchestrator.py` inside `if args.predict:` block (line 3181).
Wraps everything from the `query()` loop through `validate_prediction_result()`.

```python
run_id = run_ledger.open_run(
    "prediction",
    ticker=args.ticker, quarter_label=ql, accession_8k=acc,
    artifact_dir=str(paths["result_path"].parent),
)
try:
    async for msg in query(prompt=prompt, options=options):
        ...

    if not paths["result_path"].exists():
        raise RuntimeError("Predictor finished without writing result.json")

    finalize_prediction_result(...)

    with open(paths["result_path"], encoding="utf-8") as f:
        prediction = json.load(f)

    validate_prediction_result(
        prediction,
        expected_ticker=args.ticker,
        expected_quarter=quarter_info["quarter_label"],
    )

    run_ledger.close_run(
        run_id, "succeeded",
        sdk_session_id=predictor_session_id,
        result_path=str(paths["result_path"]),
        thinking_path=str(paths["result_path"].parent / "thinking.md"),
        summary={
            "direction": prediction["direction"],
            "confidence_score": prediction["confidence_score"],
            "confidence_bucket": prediction["confidence_bucket"],
            "magnitude_bucket": prediction["magnitude_bucket"],
            "expected_move_range_pct": prediction["expected_move_range_pct"],
        },
    )
except Exception as e:
    run_ledger.close_run(run_id, "failed", error=str(e)[:500])
    raise
```

### Learner — wraps the WHOLE `run_learner_for_quarter()` function

Location: `earnings_orchestrator.py` inside `if args.learn:` block, around the
`run_learner_for_quarter(...)` call. This is the natural unit of "one learner
run" — the function handles SDK invocation, derived-write recovery (no SDK
call at all if `learning/result.json` already exists), validation retry
(up to 2 SDK calls), and lesson appends to `learnings/ticker/*.json` +
`learnings/global.json`. All of that is ONE ledger run.

**Contract change (2026-04-19)**: `run_learner_for_quarter` returns
`tuple[dict | None, str]` where the second element is a
:class:`LearnerOutcome` string constant. This lets the caller distinguish
*skipped* (environmental — event not ready to learn from) from *failed*
(pipeline-level error) from *succeeded/recovered*. Before this change the
caller recorded every `None` return as `"failed"`, which polluted the audit
trail with phantom failures for quarters that had no prediction yet or no
published stock-price — neither is a defect.

```python
class LearnerOutcome:
    SUCCEEDED                 = "succeeded"
    RECOVERED                 = "recovered"
    SKIPPED_NO_PREDICTION     = "skipped_no_prediction"
    SKIPPED_NO_DAILY_STOCK    = "skipped_no_daily_stock"
    FAILED_NO_RESULT          = "failed_no_result"
    FAILED_INVALID_JSON       = "failed_invalid_json"
    FAILED_NO_RESULT_RETRY    = "failed_no_result_retry"
    FAILED_INVALID_JSON_RETRY = "failed_invalid_json_retry"
    FAILED_VALIDATION         = "failed_validation"
    FAILED_RECOVERY_APPEND    = "failed_recovery_append"
    FAILED_TICKER_APPEND      = "failed_ticker_append"
    FAILED_GLOBAL_APPEND      = "failed_global_append"

    SUCCESS = frozenset({SUCCEEDED, RECOVERED})
    SKIPPED = frozenset({SKIPPED_NO_PREDICTION, SKIPPED_NO_DAILY_STOCK})
    FAILED  = frozenset({FAILED_NO_RESULT, FAILED_INVALID_JSON,
                         FAILED_NO_RESULT_RETRY, FAILED_INVALID_JSON_RETRY,
                         FAILED_VALIDATION, FAILED_RECOVERY_APPEND,
                         FAILED_TICKER_APPEND, FAILED_GLOBAL_APPEND})
    ALL = SUCCESS | SKIPPED | FAILED
```

All 12 return sites in `run_learner_for_quarter` are tagged 1:1 with a
constant; `test_learner_outcomes.py` asserts `len(ALL) == 12`, the three
category sets are pairwise disjoint, and their union is `ALL` — so adding a
new return branch without categorizing it fails the test suite loudly.

```python
run_id = run_ledger.open_run(
    "learning",
    ticker=args.ticker, quarter_label=target_ql, accession_8k=target_acc,
    artifact_dir=str(COMPANIES_DIR / args.ticker.upper() / "events"
                     / target_ql / "learning"),
)
try:
    attribution, outcome = run_learner_for_quarter(
        ticker=args.ticker,
        quarter_info=quarter_info,
        events=events,
        current_index=current_index,
        pit_mode="historical",
        live_state_path=live_state_path,
    )
    if outcome in LearnerOutcome.SUCCESS:
        pd = attribution.get("primary_driver", {}) or {}
        fb = attribution.get("feedback", {}) or {}
        pc = fb.get("prediction_comparison", {}) or {}
        ar = attribution.get("actual_return", {}) or {}
        run_ledger.close_run(
            run_id, "succeeded",
            sdk_session_id=attribution.get("sdk_session_id"),
            result_path=str(learning_dir / "result.json"),
            thinking_path=str(learning_dir / "thinking.md"),
            summary={
                "direction_correct":       pc.get("direction_correct"),
                "magnitude_error_pct":     pc.get("magnitude_error_pct"),
                "primary_driver_category": pd.get("category"),
                "actual_daily_stock_pct":  ar.get("daily_stock_pct"),
            },
        )
    elif outcome in LearnerOutcome.SKIPPED:
        run_ledger.close_run(run_id, "skipped", error=outcome)
    else:
        run_ledger.close_run(run_id, "failed", error=outcome)
except Exception as e:
    run_ledger.close_run(run_id, "failed", error=str(e)[:500])
    raise
```

The summary fields exactly match the four keys read by
`run_ledger.py::_render_learners_section` (`direction_correct`,
`magnitude_error_pct`, `primary_driver_category`, `actual_daily_stock_pct`).
Test `test_run_ledger.py::test_16_learner_summary_has_exactly_the_four_renderer_keys`
pins this contract.

**Caller migration**: 4 other callers of `run_learner_for_quarter(...)` must
be updated to unpack `(result, outcome)`:

- `scripts/run_phase4_big.py`
- `scripts/run_calibration_sequential.py`
- `scripts/run_q3_from_existing_bundle.py`
- `scripts/calibrate_learner.py`

Minimal adaptation: if `outcome in LearnerOutcome.SKIPPED`, raise
`LearnerSkipped`; if `outcome in LearnerOutcome.FAILED`, raise `LearnerFailed`;
otherwise proceed with the returned dict.

### Guidance — wraps the whole extraction attempt in `process_one()`

Location: `scripts/extraction_worker.py::process_one`. One ledger run = one
payload attempt from queue pop through terminal disposition.

Design mapping:

- **open_run** immediately after payload parse, BEFORE `/extract`
- **succeeded** only after combined result file exists and has been parsed
- **failed** on exception or malformed/absent result file
- **rate_limited** on the existing requeue branch
- **skipped** remains available but is not expected in current extraction flow

```python
run_id = run_ledger.open_run(
    "guidance",
    ticker=ticker,
    quarter_label=quarter_label,
    accession_8k=source_id if source_asset == "8k" else None,
    source_id=source_id,
    source_asset=source_asset,
)

try:
    ... run /extract ...

    if rate_limited:
        run_ledger.close_run(run_id, "rate_limited", error="rate_limit")
        requeue(...)
        return

    if not result_path.exists():
        raise RuntimeError("extract completed without result file")

    with open(result_path, encoding="utf-8") as f:
        combined = json.load(f)

    summary = _build_guidance_summary(combined, source_id)
    run_ledger.close_run(
        run_id, "succeeded",
        result_path=str(result_path),
        summary=summary,
    )
except Exception as e:
    run_ledger.close_run(run_id, "failed", error=str(e)[:500])
    raise
```

The summary builder reads:
- `primary_items` from combined result JSON
- `enriched_items` / `new_secondary_items` from combined result JSON
- `items_written` from `/tmp/gu_written_{source_id}.json` if present

This helper must be defensive:
- missing or invalid sidecar → `items_written = None`
- missing count keys → omit / `None`
- never raise from summary extraction

### Critical stale-sidecar guard (guidance)

At the TOP of `process_one`, before any extraction starts:

```python
written_sidecar = Path(f"/tmp/gu_written_{source_id}.json")
written_sidecar.unlink(missing_ok=True)
```

Without this, a failed/retried extraction could accidentally reuse a stale
prior attempt's write-audit file and over-report `items_written`.

This guard was accepted as required during review.

---

## 8. Run Index Rendering Rules

### Sort order

- **In Flight**: `started_at DESC`
- **Recent Predictions**: `started_at DESC`, limit 50, exclude `status == running`
- **Recent Learners**: same
- **Recent Extractions**: same

### Column specifications

**In Flight** — compact, no per-component columns
| run_id | component | ticker | quarter | started_at | elapsed |

**Predictions**
| date | ticker | quarter | direction | conf | magnitude | expected | status | run_id |

**Learners**
| date | ticker | quarter | direction_correct | actual_return | magnitude_error | primary_driver | status | run_id |

**Extractions**
| date | ticker | asset | source_id | items_extracted | items_written | enrichment | status | run_id |

### Format conventions

- `date`: YYYY-MM-DD (extracted from started_at)
- `run_id`: first 8 chars (full id in ledger)
- `expected`: `"{low}–{high}%"` string
- `status`: emoji-decorated (✅ succeeded / ❌ failed / 🔄 running / ⏸ rate_limited / ⏭ skipped)
- Empty cells rendered as `—` (em-dash)

---

## 9. Corrections Accepted from Review

All four blocker issues from the first-round review:

1. ✅ **Dataview-JSONL mismatch fixed** — Python generates static Markdown tables; no Dataview dependency.
2. ✅ **Execution boundary is correct** — `open_run` wraps the SDK `query()` call, not `finalize_*_result()`.
3. ✅ **POSIX safety is correctly stated** — `fcntl.flock(LOCK_EX) + flush + fsync` on a single-host shared FS. No PIPE_BUF claim.
4. ✅ **Single path, `component` in schema, internally consistent.**

Plus three trims from the second-round review:

1. ✅ **Real-time requires refresh on open AND close.** Index is regenerated on every state transition — not just terminal.
2. ✅ **`rate_limited` status is explicit** — mapped from extraction_worker's requeue branch; audit trail shows every attempt distinctly.
3. ✅ **`run_id` NOT added to artifact frontmatter in v1.** Ledger carries `result_path`/`thinking_path`; artifacts carry `sdk_session_id`. Cross-reference is already possible.

---

## 10. Scope / File-Level Impact

| File | Action | Lines |
|---|---|---|
| `scripts/earnings/run_ledger.py` | **NEW** — append + read + collapse + refresh_index (In Flight is a DISJOINT view; per-component tables filter `status != "running"`) with atomic write | ~500 |
| `scripts/earnings/test_run_ledger.py` | **NEW** — 23 tests covering primitives, state collapse, API, renderer contracts, drift guards | ~450 |
| `scripts/earnings/test_learner_outcomes.py` | **NEW** — 10 tests pinning the 12-member outcome taxonomy + AST-level invariant that every return site is 1:1 tagged | ~140 |
| `scripts/earnings/earnings_orchestrator.py` | wrap prediction SDK + finalize + validate; wrap the WHOLE `run_learner_for_quarter()` (not just its SDK call) with `LearnerOutcome` → ledger status mapping | +~80 |
| `scripts/extraction_worker.py::process_one` | stale-sidecar guard at entry; per-exit-path close; defensive `_build_guidance_summary` | +~150 |
| `scripts/run_phase4_big.py` / `run_calibration_sequential.py` / `run_q3_from_existing_bundle.py` / `calibrate_learner.py` | unpack `(result, outcome)`; raise `LearnerSkipped`/`LearnerFailed`; outer callers log skip-vs-fail correctly | +~10 each |
| `earnings-analysis/operations/` | **NEW DIR**. `Run Index.md` seeded as an empty 4-section stub. `run_ledger.jsonl` is lazy-created on the first `_append_row` call — empty files are noise and the primitive already calls `mkdir(parents=True, exist_ok=True)`. | — |

**Net**: ~1,400 lines of new code/tests + ~40 lines modifications + 1 new vault seed file.

No frontmatter schema changes. No new runtime dependencies. No touching
existing CSVs (deprecate after 90 days of ledger being live).

---

## 11. Tests

Total shipped: **33 tests** across two files (23 in `test_run_ledger.py` +
10 in `test_learner_outcomes.py`). The 15 below are the original design
targets; additional tests beyond the first 15 are regression guards for
issues found during the audit rounds — renderer-contract drift, enum
drift, and the "running row leaks into per-component table" bug.

**Primitives**
1. `append` writes a valid JSON line ending with `\n`
2. Reader skips malformed JSON lines silently (simulated torn writes)
3. Concurrent writers (20-thread pool) produce zero corrupted lines
4. Missing ledger file → `current_state()` returns `[]` (no error)

**State collapse**
5. Single run_id with running + succeeded → collapsed state = succeeded
6. Single run_id with running only → collapsed state = running (crash-recovery)
7. Multiple interleaved run_ids collapse correctly by run_id
8. `current_state(component="prediction")` filters correctly
9. `current_state(status="running")` filters correctly

**API behaviour**
10. `open_run` returns a new run_id each call (uuid4 format)
11. `close_run` appends row with matching run_id and terminal status
12. `close_run(run_id, "rate_limited")` accepted as a valid terminal status
13. `refresh_index` writes file with 4 section headers + current timestamp
14. `refresh_index` uses atomic tmp+rename (no `.tmp.*` artifacts left)

**End-to-end**
15. `open_run` → `refresh_index` → Run Index.md "In Flight" section shows the running row; then `close_run` → `refresh_index` → same run now appears in the per-component section, no longer In Flight

---

## 12. Implementation Order (TDD)

1. Write plan file (this document) ✓
2. Create `earnings-analysis/operations/` dir + seed `Run Index.md` only.
   `run_ledger.jsonl` is intentionally lazy-created on first `_append_row`;
   the primitive already calls `path.parent.mkdir(parents=True, exist_ok=True)`.
3. Create `scripts/earnings/run_ledger.py` with full API but `pass`-body stubs
4. Write `scripts/earnings/test_run_ledger.py` with all 15 tests (they fail)
5. Implement `append`, `read_all`, `current_state` → primitive tests green
6. Implement `open_run`, `close_run` → API tests green
7. Implement `refresh_index` → rendering test green
8. Full suite green
9. Wire prediction call site in `earnings_orchestrator.py`
10. Wire learner call site in `earnings_orchestrator.py`
11. Wire guidance call site in `scripts/extraction_worker.py` (include rate_limited branch)
12. Seed `Run Index.md` with header + empty sections (auto-regenerates on first run)
13. Re-run full regression suite across all obsidian-capture + earnings tests — must stay at current pass count + 15 new
14. Commit + push

---

## 13. What Is NOT In v1

- ❌ Per-run Markdown mirror notes under `operations/runs/{run_id}.md`
- ❌ Dataview query blocks in Run Index.md (uses static tables instead)
- ❌ `run_id` in `result.md` / `thinking.md` frontmatter
- ❌ Year-rotation of the ledger file (single file for v1; rotate when > 50 MB)
- ❌ ULID run_ids (uuid4 is fine; ULID is a nice-to-have)
- ❌ Any changes to legacy `predictions.csv` / `prediction_processed.csv` (deprecate later)
- ❌ Debounced index refresh (synchronous after each transition is fine at v1 scale)
- ❌ Cross-host coordination (hostPath mount + single-host guarantee is sufficient for current deployment)
- ❌ Elasticsearch / Loki / external log aggregator integration (the JSONL IS the log; ship logs to any aggregator via filebeat later if desired)

---

## 14. Rollback Plan

Revert commit. The ledger file and index note are append-only/regenerable — deleting them is harmless. Orchestrator + extraction_worker lose the wrapping calls and return to their prior behaviour. Zero schema impact anywhere else in the repo.

---

## 15. Future Work (Explicitly Out of Scope)

- Year rotation when ledger > 50 MB
- CLI tool: `python -m run_ledger status` to print current state without opening Obsidian
- Alerting on `rate_limited` storms or consecutive `failed` runs
- Deprecation of `predictions.csv` / `prediction_processed.csv` (after 90 days of ledger being live)
- Per-run Markdown mirror notes if Obsidian browsing UX demands them
- Dataview query block embedded in Run Index.md as optional bonus view (renders only with plugin)
- ULID run_ids for chronological sorting by id

---

## Final Verdict

Architecture is tight. All review-round blockers and trims addressed. Ready to ship.
