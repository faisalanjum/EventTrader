# Predictor Module Plan

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
- [2026-02-08] [Claude] Initial scaffold created. R1 resolved: context bundle schema locked by I3 in master plan §2a.

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

Define Predictor contract and implementation requirements so a zero-context bot can implement accurately without changing system architecture.

Predictor role: read orchestrator-provided bundle and produce `prediction/result.json`.

---

## 1) Primary Context Pack (LOCKED)

Every bot implementing Predictor must read these first:

1. `earnings-orchestrator.md` (primary source of truth).
2. `Infrastructure.md` (execution constraints and SDK behavior).
3. `AgentTeams.md` (alternative primitives; use only when justified).
4. `DataSubAgents.md` (data-layer assumptions).
5. `guidanceInventory.md` (guidance bridge assumptions).
6. This file (`predictor.md`).
7. Existing skills:
   - `.claude/skills/earnings-prediction/SKILL.md` (currently out-of-sync; rewrite target)
   - `.claude/skills/earnings-orchestrator/SKILL.md`

---

## 2) SDK and Automation Contract (LOCKED)

1. Predictor must run non-interactively.
2. Predictor must not require manual permissions or runtime user decisions.
3. Predictor must accept deterministic input bundle and produce deterministic structured output.
4. Keep compatibility with SDK-triggered orchestrator runs.

---

## 3) Scope and Non-Goals

### In Scope

1. Predictor input bundle contract.
2. Predictor output contract (`prediction_result.v1`).
3. Deterministic derivation/validation rules.

### Out of Scope

1. Data fetching orchestration.
2. Guidance extraction internals.
3. Attribution/Learner internals.

---

## 4) Module Interface Contract (Current Master Snapshot)

### Caller -> Callee

- Caller: Orchestrator Step 3d.
- Callee: Predictor.

### Required Input (from orchestrator)

1. 8-K content for target quarter.
2. Merged context bundle from planner-driven data fetch.
3. Guidance history payload from Step 0.
4. Prior U1 fields (`predictor_lessons`, `what_failed`, `why`).
5. Mode metadata (`historical` or `live`) and recorded cutoff metadata for live mode.

### Required Output (to orchestrator)

- `prediction/result.json` with required fields in `prediction_result.v1`, including:
  - direction, confidence_score, confidence_bucket
  - expected_move_range_pct, magnitude_bucket, horizon
  - derived signal
  - key_drivers, data_gaps, analysis
  - predicted_at, model_version, prompt_version

### Hard Constraints

1. Bundle-only: predictor does not fetch data.
2. No return labels (`daily_stock`, `hourly_stock`) as inputs.
3. Signal is deterministic derivation, not free-form judgment.

---

## 5) Design Rules

1. Core dimensions guide reasoning; they are not rigid output fields.
2. Missing-data policy must be enforced (anchor logic and hold+low fallback).
3. Confidence is rubric-guided holistic score + bucket.
4. Keep decision output structured and machine-validated.

---

## 6) Validation and Failure Policy

### Block

1. Missing required output fields.
2. Deterministic rule violations (bucket derivation, signal derivation, invalid ranges).

### Continue (with explicit gaps)

1. Optional context missing; reflected via `data_gaps` and confidence behavior.

### Rule

Orchestrator validates; predictor must emit full required schema every run.

---

## 7) Skill Sync Requirements

Required changes vs current skill:

1. Remove `Task`, `Skill`, `filtered-data` access to enforce bundle-only behavior.
2. Replace old output shape (`up/down`, old magnitude bands) with `prediction_result.v1`.
3. Replace placeholder workflow with actual contract-driven behavior.
4. Keep file operations only (`Read`, `Write`, `Glob`, `Grep`, `Bash`, `Edit` as needed).

---

## 8) Implementation Phases

### Phase 0: Contract Lock

1. Confirm implementation mapping to locked orchestrator contracts (I3 context bundle).
2. Lock deterministic validation location (post-check implementation point).

### Phase 1: Skill Rewrite

1. Rewrite `.claude/skills/earnings-prediction/SKILL.md` to match master contract.
2. Add prompt-level rubric + missing-data policy instructions.

### Phase 2: Validation + Calibration

1. Validate outputs on historical samples.
2. Track hold+low rate due to missing anchors.

---

## 9) Open Questions Register

| ID | Question | Priority | Status |
|---|---|---|---|
| R1 | Exact orchestrator -> predictor context bundle schema? | P0 | **Resolved** — locked by I3 in `earnings-orchestrator.md §2a` (`context_bundle.v1`). |
| R2 | Where to enforce deterministic rules (orchestrator validator module path)? | P0 | Open |
| R3 | How to standardize `data_gaps` categories for better U1 learning? | P1 | Open |
| R4 | Should predictor prompt include explicit section delimiters for each bundle part? | P1 | Open |
| R5 | How to version prompt changes for reproducible calibration? | P1 | Open |

---

## 10) Done Criteria

Predictor module plan is done when:

1. P0 questions are resolved.
2. Bundle-only enforcement path is explicit and testable.
3. Output schema and deterministic rules are fully unambiguous.
4. Skill-sync requirements are complete enough for direct implementation.

---

## 11) References

1. `earnings-orchestrator.md`
2. `Infrastructure.md`
3. `AgentTeams.md`
4. `DataSubAgents.md`
5. `guidanceInventory.md`
6. `.claude/skills/earnings-prediction/SKILL.md`
7. `.claude/skills/earnings-orchestrator/SKILL.md`
