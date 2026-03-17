# Learner Module Plan

**Created**: 2026-02-08  
**Status**: Planning Scaffold  
**Parent Plan**: `earnings-orchestrator.md` (source of truth)

---

## Active Collaboration Context (Locked)

- Two bots may edit this plan in parallel: **ChatGPT** and **Claude**. Re-read full doc before every edit.
- All decisions are provisional until the user explicitly confirms they are final.
- Keep tradeoffs explicit for each major decision (alternatives, choice, reason).
- If this file conflicts with `earnings-orchestrator.md`, the master plan wins.

Bot-to-bot notes (append-only; mark handled, do not delete history):
- [2026-02-08] [Claude] Initial scaffold created. L1+L2 resolved: full attribution schema locked by I6, learner inputs locked by I4 in master plan.
- [2026-03-16] [Claude] L4 resolved: hybrid 4-layer enforcement (prompt + TaskCreate + PreToolUse + SubagentStop). Empirically confirmed SubagentStop does NOT fire for Skill forks — learner must be an Agent. See §12.

---

## CHATGPT - Collaboration Guard (DO NOT DELETE)

`CLAUDE INSTRUCTION`: Do not delete this section or any `CHATGPT`-prefixed block unless the user explicitly asks.

1. Re-read full doc before every response/edit.
2. All decisions provisional until user approves.
3. If this doc conflicts with `earnings-orchestrator.md`, the master plan wins.
4. Keep open questions in the register until explicitly resolved.
5. For each major design choice, compare alternatives and record tradeoffs.
6. Ask one question at a time; reprioritize after every user answer.
7. Map each requirement to a tested primitive/pattern before accepting a design.
8. Challenge assumptions independently; do not auto-accept proposals.
9. Lock a decision only after explicit user confirmation that they have made up their mind.
10. After a decision is locked, update the relevant main section(s) and then mark the corresponding open question as resolved.

---

## Shared Project Requirements (LOCKED)

1. `earnings-orchestrator.md` is the parent source of truth; if conflicts exist, parent plan wins.
2. Priority order is fixed: reliability first, full required data coverage second, speed third, then maximum accuracy via comprehensive/exhaustive research within runtime limits.
3. No over-engineering: add complexity only when it has clear reliability or quality value.
4. One focused decision at a time; keep unresolved items in the open-questions register.
5. Reason independently before locking any decision; do not auto-accept proposals.
6. Validate choices against `Infrastructure.md`, `AgentTeams.md`, and `DataSubAgents.md` primitives.
7. Must remain SDK-triggerable and non-interactive.

---

## Session Start Rules (LOCKED)

1. Read `.claude/plans/earnings-orchestrator.md` first. It is the only parent source of truth.
2. Then read this file's Primary Context Pack in full (Infrastructure.md, DataSubAgents.md, etc.). Work on only this module per session — do not modify other module plans or the master plan.
3. Do not redesign architecture; resolve only open questions in this module plan, one question at a time.
4. Follow locked priorities: reliability > required data coverage > speed > accuracy/exhaustive research; no over-engineering.
5. Before each reply, re-check parent-plan consistency and update the module doc directly.
6. Record unresolved items in that module's open-question table; when resolved, move into main section and mark resolved.
7. Keep SDK compatibility and non-interactive execution constraints from `Infrastructure.md`.
8. Append to bot-to-bot notes at session start and when resolving questions.

---

## 0) Purpose

Define the Attribution/Learner module contract and implementation path.

Learner role: explain realized move after the event window and write reusable feedback for planner/predictor (U1 loop).

---

## 1) Primary Context Pack (LOCKED)

Every bot implementing Learner must read these first:

1. `earnings-orchestrator.md` (primary source of truth).
2. `Infrastructure.md` (execution constraints and SDK behavior).
3. `AgentTeams.md` (future multi-model pattern options).
4. `DataSubAgents.md` (data-layer assumptions).
5. `guidanceInventory.md` (guidance bridge — learner compares actuals vs historical guidance).
6. This file (`learner.md`).
7. Existing skills:
   - `.claude/skills/earnings-attribution/SKILL.md` (currently old design; rewrite target)
   - `.claude/skills/earnings-orchestrator/SKILL.md`

---

## 2) SDK and Automation Contract (LOCKED)

1. Learner must run non-interactively.
2. Trigger policy follows master plan: historical same-run, live delayed timer.
3. Missing optional sources cannot block indefinitely; gaps must be explicit.
4. Keep compatibility with SDK-triggered orchestrator automation.

---

## 3) Scope and Non-Goals

### In Scope

1. Learner input assembly from orchestrator.
2. Learner output contract (`attribution/result.json` with feedback block).
3. U1 feedback quality and guardrails.

### Out of Scope

1. Real-time prediction latency optimization.
2. Cross-company meta-learning framework beyond locked plan.
3. Full Phase-2 multi-model implementation details (unless explicitly unlocked).

---

## 4) Module Interface Contract (Current Master Snapshot)

### Caller -> Callee

- Caller: Orchestrator Step 4.
- Callee: Learner (Attribution).

### Required Input (from orchestrator)

1. `prediction/result.json` for target quarter.
2. Realized return labels (at minimum `daily_stock`).
3. `prediction/context_bundle.json` path for reference-only comparison (what predictor had).
4. Quarter/ticker metadata and timing metadata.

### Required Output (to orchestrator)

1. `attribution/result.json` (full analysis + required feedback block).
2. Required top-level `missing_inputs` array.
3. Required feedback fields:
   - `prediction_comparison`
   - `what_worked`
   - `what_failed`
   - `why`
   - `predictor_lessons`
   - `planner_lessons`

### Hard Constraints

1. Feedback must be generalizable (no quarter-specific command rules).
2. Feedback is advisory, not hard lock.
3. Preserve raw history (no lossy digest step in plan).

---

## 5) Design Rules

1. Prioritize causal clarity over verbosity.
2. Explicitly capture missing inputs to prevent silent pollution of U1.
3. Keep per-field caps to enforce signal quality.
4. Ensure output is machine-consumable for next-quarter context assembly.

---

## 6) Validation and Failure Policy

### Block

1. Missing hard gate inputs (`prediction/result.json` or `daily_stock` label).
2. Invalid required feedback structure.

### Warn + Write

1. Partial analysis due to missing optional sources.
2. Missing optional narrative sections, with explicit `missing_inputs`.

### Rule

Better to write explicit partial output than silently skip learning.

---

## 7) Skill Sync Requirements

Required changes vs current attribution skill:

1. Replace markdown-centric old report flow with JSON-first output contract.
2. Remove legacy tracking assumptions (`predictions.csv`, subagent-history as source of truth).
3. Align step flow to current orchestrator trigger policy and U1 contract.
4. Keep tested source retrieval patterns that remain relevant.

---

## 8) Implementation Phases

### Phase 0: Contract Lock

1. Confirm implementation mapping to locked orchestrator contracts (I4 learner inputs + I6 output schema).
2. Keep learner local assumptions aligned with parent-plan revisions.

### Phase 1: Skill Rewrite (single-model)

1. Rewrite `.claude/skills/earnings-attribution/SKILL.md` to master contract.
2. Implement required feedback + `missing_inputs` behavior.
3. Decide invocation pattern: if learner is Task-spawned (not Skill-forked), consider **SubagentStop hook** for output completeness validation — deterministic schema check on `attribution/result.json` that blocks stop and forces self-correction if required fields are missing or caps violated. Tested and working per `Infrastructure.md` (SubagentStop blocking confirmed). Learner has no speed constraint, so one extra turn to fix output is acceptable. See L4.

### Phase 2: Calibration

1. Validate lesson quality and consistency on historical samples.
2. Confirm U1 loop improves planner/predictor in subsequent quarters.

### Phase 3: Optional Multi-model (deferred)

1. Revisit only when explicitly unlocked in master plan.

---

## 9) Open Questions Register

| ID | Question | Priority | Status |
|---|---|---|---|
| L1 | Full `attribution/result.json` schema beyond feedback block? | P0 | **Resolved** — locked by I6 in `earnings-orchestrator.md` (§2d schema). |
| L2 | Exact orchestrator -> learner input bundle schema? | P0 | **Resolved** — locked by I4 in `earnings-orchestrator.md §2a` (3 minimal inputs; learner fetches autonomously). |
| L3 | How to normalize `missing_inputs` categories for downstream use? | P1 | Open |
| L4 | Where to enforce feedback cap validation (prompt vs post-validator vs SubagentStop hook)? | P1 | **Resolved** — Approach C (hybrid 4-layer). SubagentStop requires Task-spawned agent, NOT Skill-fork (**empirically confirmed 2026-03-16**: SubagentStop does not fire for Skill forks). See §12. |
| L5 | What migration policy for legacy markdown attribution outputs? | P1 | Open |

---

## 10) Done Criteria

Learner module plan is done when:

1. P0 questions are resolved.
2. Full output schema is unambiguous and machine-validated.
3. U1 feedback quality constraints are explicit and testable.
4. Skill-sync requirements are complete enough for direct implementation.

---

## 11) References

1. `earnings-orchestrator.md`
2. `Infrastructure.md`
3. `AgentTeams.md`
4. `DataSubAgents.md`
5. `.claude/skills/earnings-attribution/SKILL.md`
6. `.claude/skills/earnings-orchestrator/SKILL.md`

---

## 12) Step Enforcement Architecture (L4 Resolved, 2026-03-16)

### Empirical Finding

**SubagentStop does NOT fire for Skill-forked contexts. Only for Task-spawned agents.**

| Test | Invocation | SubagentStop fired? |
|---|---|---|
| `/test-v176-stop-on-skill` via Skill tool | Skill fork | **NO** — marker file not created |
| `test-hook-stop-block` via Task tool | Task spawn | **YES** — marker created with full JSON (`agent_id`, `agent_type`, `last_assistant_message`) |

Test date: 2026-03-16. Global SubagentStop hook in `settings.json` with marker script writing to `/tmp/`. Definitive: the hook fires for Task-spawned agents only.

**Consequence**: The learner must be defined as an **agent** (`.claude/agents/earnings-learner.md`) and invoked via Task tool — not the current Skill-forked `earnings-attribution` pattern. This also fixes the existing design mismatch where the attribution skill lists `Task` (agent spawner) in allowed-tools but the agent spawner is blocked in forks.

### The 4-Layer Pattern

| Layer | What | Enforces | Deterministic? |
|---|---|---|---|
| 1. Prompt checklist | Instructions in agent body | Step ordering, investigation depth | No (LLM honor) |
| 2. TaskCreate/TaskUpdate | Tool-based progress tracking | Visibility, compaction-proof state | Partially (claims not validated) |
| 3. PreToolUse on Write | Hook validates JSON before write | Schema, required fields, array caps | **Yes** (shell script, external) |
| 4. SubagentStop hook | Hook validates before agent can complete | File existence, final schema check, one retry | **Yes** (shell script, external) |

Layer 1 guides. Layer 2 tracks. Layer 3 blocks bad writes. Layer 4 blocks bad completions.

Layers 3-4 run **outside** the LLM context as shell scripts — the LLM cannot skip, override, or hallucinate past them. This is what no prompt-level pattern (including LangChain TodoListMiddleware) can provide.

### What's deterministic vs what's LLM judgment

**Enforced by code** (Layers 3-4):
- `attribution/result.json` exists before completion
- JSON parseable, all required fields present
- `feedback` block has all 6 sub-fields
- Array caps (what_worked ≤ 2, what_failed ≤ 3, predictor_lessons ≤ 3, planner_lessons ≤ 3)
- `missing_inputs` is an array
- `schema_version` matches expected

**LLM judgment only** (no hook can validate):
- Causal correctness of attribution
- Lesson quality and generalizability
- Investigation depth within each source

### Cost

~3,500 tokens overhead (~2% of learner budget). One SubagentStop retry adds ~1,000 tokens. Learner has no speed constraint.

### Existing patterns to reuse

| Pattern | File | Reuse for |
|---|---|---|
| PreToolUse Write validation | `.claude/hooks/validate_gx_output.sh` | Attribution output validation hook |
| Agent with Stop hook in frontmatter | `.claude/agents/test-hook-stop-block.md` | Learner agent frontmatter |
| SubagentStop global hook | `.claude/settings.json` (obsidian_capture.sh) | Coexists — learner uses agent-scoped Stop hook |
