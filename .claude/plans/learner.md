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
2. Then read only one module plan for this session: `.claude/plans/{module}.md`.
3. Do not redesign architecture; resolve only open questions in that module plan, one question at a time.
4. Follow locked priorities: reliability > required data coverage > speed > accuracy/exhaustive research; no over-engineering.
5. Before each reply, re-check parent-plan consistency and update the module doc directly.
6. Record unresolved items in that module’s open-question table; when resolved, move into main section and mark resolved.
7. Keep SDK compatibility and non-interactive execution constraints from `Infrastructure.md`.

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
| L4 | Where to enforce feedback cap validation (prompt vs post-validator vs SubagentStop hook)? | P1 | Open — three options: (a) prompt instruction only, (b) orchestrator post-validator rejects and re-invokes, (c) SubagentStop hook blocks stop and forces self-correction in-context (requires Task-spawned learner; tested in Infrastructure.md). Option (c) is cheapest retry path since learner keeps context. |
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
