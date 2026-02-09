# Planner Module Plan

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
- [2026-02-08] [Claude] Initial scaffold created. I7 resolved: agent catalog locked in master plan §2b. P0, P1, P5 marked resolved.

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

Define the Planner module contract and implementation decisions so a zero-context bot can implement it without ambiguity.

Planner role: read 8-K plus prior learning context, output one `fetch_plan.json` for orchestrator execution.

---

## 0.1) I7 Status: RESOLVED

**I7 (Planner agent catalog) is locked in `earnings-orchestrator.md §2b`.**

12 available agents across 4 domains (Neo4j 5, Alpha Vantage 1, Benzinga API 1, Perplexity 5) + planned families (`WEB_SEARCH`, `SEC_API_FREE_TEXT_SEARCH`, `PRESENTATIONS`; IDs provisional and may expand). Any `fetch.agent` value not in the catalog is a validation error. Tier guidance for priority patterns included.

**Key dependency**: All 12 existing agents need rework (PIT compliance, JSON envelope, `available_at` fields) and all 3 planned agents need to be built. This work is owned by `DataSubAgents.md` implementation — not by the planner or orchestrator. The planner consumes the catalog; it does not maintain agents. As agents are reworked/built under DataSubAgents, they become available to the planner automatically.

Planner should only reference agents in the "available" table. Planned agents are not valid `fetch.agent` values until they are built and moved to "available."

---

## 1) Primary Context Pack (LOCKED)

Every bot implementing Planner must read these first:

1. `earnings-orchestrator.md` (primary source of truth).
2. `Infrastructure.md` (execution constraints and SDK behavior).
3. `AgentTeams.md` (alternative primitives; use only when justified).
4. `DataSubAgents.md` (data access layer assumptions).
5. `guidanceInventory.md` (guidance bridge assumptions).
6. This file (`planner.md`).
7. Existing skills:
   - `.claude/skills/earnings-orchestrator/SKILL.md`
   - `.claude/skills/earnings-planner/` (currently empty; target location)

---

## 2) SDK and Automation Contract (LOCKED)

1. Planner must be non-interactive (no user prompts, no manual approval logic).
2. Planner must produce machine-parseable JSON only.
3. Missing required inputs must fail fast with explicit error.
4. Keep compatibility with SDK-triggered orchestration defined in `earnings-orchestrator.md`.

---

## 3) Scope and Non-Goals

### In Scope

1. Planner input assembly contract.
2. Planner output contract (`fetch_plan.v1`).
3. Single-turn behavior and validation boundaries.

### Out of Scope

1. Executing data fetches (orchestrator owns execution).
2. Predictor scoring logic.
3. Attribution/Learner logic.

---

## 4) Module Interface Contract (Current Master Snapshot)

### Caller -> Callee

- Caller: Orchestrator Step 3b.
- Callee: Planner.

### Required Input (from orchestrator)

1. `ticker`
2. `quarter`
3. `filed_8k`
4. 8-K content/context for target quarter
5. Prior U1 `planner_lessons` for this ticker
6. Guidance history payload (from Step 0 guidance inventory)
7. Agent catalog (valid values for `fetch[].agent`) — see `earnings-orchestrator.md §2b` for locked catalog

### Required Output (to orchestrator)

- `fetch_plan.json` using `fetch_plan.v1` contract from master plan:
  - `schema_version`, `ticker`, `quarter`, `filed_8k`
  - `questions[]` entries with `id`, `question`, `why`, `output_key`, `fetch`
  - `fetch` as tiered array-of-arrays:
    - within tier: parallel
    - across tiers: sequential fallback

### Hard Constraints

1. Planner is single-turn.
2. Planner does not fetch data itself.
3. PIT handling remains orchestrator concern, not planner concern.

---

## 5) Design Rules

1. Planner relevance principle: each fetch request should map to 8-K claim, core dimension, or U1 lesson.
2. Keep schema deterministic and simple for parsing.
3. Prefer over-fetch to under-fetch when uncertain (orchestrator parallelizes).
4. Avoid free-form prose outputs.

---

## 6) Validation and Failure Policy

### Block

1. Invalid JSON output.
2. Missing required top-level schema fields.

### Warn

1. Missing common families (e.g., no consensus/prior-financial coverage) if allowed by context.

### Rule

Validation lives in orchestrator pipeline; planner output must be machine-checkable.

---

## 7) Implementation Phases

### Phase 0: Contract Lock

1. Confirm implementation mapping to locked orchestrator contracts (I2 + I7).
2. Keep planner local assumptions aligned with parent-plan revisions.

### Phase 1: Skill Build

1. Create `.claude/skills/earnings-planner/SKILL.md`.
2. Implement single-turn JSON output behavior.

### Phase 2: Validation

1. Add parser/validator checks in orchestrator.
2. Test 3-5 representative earnings quarters.

---

## 8) Open Questions Register

| ID | Question | Priority | Status |
|---|---|---|---|
| P0 | I7 Planner agent catalog: exact allowed `fetch.agent` values + purpose + invalid-name behavior | P0 | **Resolved** — 12 agents locked in `earnings-orchestrator.md §2b`. Invalid name = validation error (block). |
| P1 | Exact planner input payload schema from orchestrator? | P0 | **Resolved** — locked by I2 in `earnings-orchestrator.md §2a`. |
| P2 | Agent catalog delivery: static list in prompt or external file? | P1 | Open — catalog locked (P0); delivery mechanism TBD. Recommend static embed (12 agents, changes rarely). |
| P3 | Canonical question IDs vs free-form IDs? | P1 | Open |
| P4 | 8-K truncation/sectioning rules for large filings? | P1 | Open |
| P5 | Sanity check policy: warn-only or block in edge cases? | P1 | **Resolved** — master plan R5: log warning, not block. Planner may have valid reasons to omit common data types; U1 self-corrects. |

---

## 9) Done Criteria

Planner module plan is done when:

1. P0 questions are resolved.
2. Input and output contracts are unambiguous and testable.
3. Planner skill frontmatter + behavior requirements are locked.
4. Orchestrator integration is deterministic and parse-safe.

---

## 10) References

1. `earnings-orchestrator.md`
2. `Infrastructure.md`
3. `AgentTeams.md`
4. `DataSubAgents.md`
5. `guidanceInventory.md`
6. `.claude/skills/earnings-orchestrator/SKILL.md`
