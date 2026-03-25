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
- [2026-03-17] [Codex] Parent-plan timing clarified: live learner timer is intended to land after normal Q1-Q3 10-Q availability; annual quarters do not block on 10-K and instead record the gap in `missing_inputs`. **SUPERSEDED 2026-03-20**: live learner timer replaced by deferred-to-next-historical-bootstrap approach. See earnings-orchestrator.md §2a/§2d and EarningsTrigger.md.

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
2. Trigger policy follows master plan: historical same-run, live deferred to next historical bootstrap (updated 2026-03-20; was 35-day timer). The daemon enqueues HISTORICAL when the ticker re-enters trade_ready; the orchestrator catches the missing attribution during sequential processing.
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
4. Annual quarters do not block learner execution on 10-K availability; if the annual filing is unavailable at trigger time, learner writes a partial result and records `"10-K"` in `missing_inputs`.

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

---

## 13) Planner Lesson Quality — Fetch Plan Audit (2026-03-22)

### Problem

Without closed-loop verification, the same vague `planner_lesson` repeats indefinitely:

1. Q(n) learner writes: "fetch analyst concerns"
2. Q(n+1) planner reads lesson, adds question, fetches from `neo4j-news` only (headlines)
3. Q(n+1) predictor still misses transcript Q&A where analyst asked about margin pressure
4. Q(n+1) learner sees same gap → writes "fetch analyst concerns" again
5. Never converges — planner keeps misinterpreting the lesson

The root cause: the learner writes lessons but never checks whether the planner **correctly implemented** its previous lessons. It only checks whether the prediction was right or wrong.

### Behavioral Requirement

Before writing `planner_lessons`, the learner MUST:

1. Read the current quarter's `planner/fetch_plan.json` (accessible via `context_bundle.json → fetch_plan_ref`)
2. Compare against prior `planner_lessons` from `u1_feedback[]` in the context bundle
3. If a prior lesson was acted on but with insufficient source coverage, write a **more specific** lesson that addresses the gap

For the first quarter of a ticker (no prior lessons), skip this step.

### Source Naming Rule

When the learner identifies a source coverage failure:

- **Expected** (common case): Name the source family or agent when the learner found the relevant data during its own analysis. The learner already queries these sources for attribution — it knows where it found the evidence.
  - Example: *"fetch analyst concerns from neo4j-transcript Q&A AND news, not just news headlines — prior quarter missed Goldman's margin pressure question (found in transcript Q&A exchange #7)"*
- **Optional** (rare case): Omit source if the learner identifies a conceptual gap but didn't find the data itself during attribution.
  - Example: *"consider adding sector peer earnings to fetch plan"*
- **Never**: Fabricate a source recommendation when unsure. A vague-but-honest lesson is better than a wrong source recommendation.

### Why This Works (No Schema Change)

The learner already has everything it needs:

1. It receives `context_bundle.json` (input #3) which contains `fetch_plan_ref` pointing to the planner's actual plan
2. `u1_feedback[]` within the bundle shows what the learner recommended last time
3. During its own analysis, the learner queries the same data sources and knows where it found evidence

This is a **prompt-level behavioral instruction**, not a structural change. `planner_lessons` stays free-text (max 3 items). The convergence guarantee comes from the learner seeing the delta between its recommendation and the planner's execution.

### Convergence Example

```
Q3 Learner:
  planner_lesson = "fetch analyst concerns"

Q4 Planner:
  reads lesson → adds question → fetches from neo4j-news only

Q4 Learner:
  reads fetch_plan.json → sees only neo4j-news was used
  reads prior planner_lesson → "fetch analyst concerns"
  found key analyst question in neo4j-transcript during own analysis
  REFINED lesson = "fetch analyst concerns from neo4j-transcript Q&A
    AND neo4j-news — prior quarter used only news and missed margin
    pressure question from Goldman analyst"

Q5 Planner:
  reads refined lesson → adds both neo4j-transcript and neo4j-news
  as parallel tier-0 sources for analyst concerns
  ✓ Converges in 2 iterations
```

### Why SHOULD, Not MUST for Source Naming

Source naming is expected behavior, not a hard gate (unlike the Layer 3-4 enforcement in §12). Reasons:

1. The learner might identify a conceptual gap without knowing the best agent (e.g., "peer earnings would help" — is that `neo4j-xbrl`, `alphavantage-earnings`, or `perplexity-search`?). Forcing a source name would produce bad recommendations.
2. The learner's primary job is causal attribution, not fetch plan architecture. Source naming is a quality bonus when naturally available from its own analysis.
3. The 4-layer enforcement (§12) already validates structural output quality. This section adds lesson *content* quality, which is inherently LLM judgment.

---

## TODO: Architecture Delta — Note Quality Feedback (2026-03-25)

**Status**: APPROVED — pending implementation. Changes below have NOT been applied to the sections above yet. When implementing, update the referenced sections and remove this TODO block.

### T1: Learner now receives `analyst_notes.json`

The learner receives `planner/analyst_notes.json` as an additional input (alongside prediction/result.json, actual returns, and context_bundle.json ref). This enables the learner to assess note quality against the actual outcome.

**Sections to update**: §4 Required Input — add `planner/analyst_notes.json` path.

### T2: Expanded `planner_lessons` scope — fetch quality + note quality

`planner_lessons` currently covers fetch plan quality only. Expand to also cover analyst note quality. The learner should assess:

- **Note usefulness**: Did the planner's domain reads (macro_read, sector_read, financial_read) correctly frame the key dynamics? Did they help or mislead the predictor?
- **Note misses**: What did the planner fail to flag that turned out to be the primary driver?
- **`what_to_verify` hit rate**: How many of the planner's verification hypotheses were confirmed by fetched data? Were the right questions asked?
- **Tension resolution**: Did `key_tensions` capture the actual tension that determined the stock reaction?

**Example planner_lessons that reference note quality**:
- "Your sector_read missed that MSFT Azure reaccelerated — peer_earnings_snapshot showed mixed signals, not uniform deceleration as your note claimed"
- "Your macro_read correctly identified risk-off regime but failed to flag the consumer confidence collapse as the dominant factor — future notes should check Econ #s data releases"
- "what_to_verify asked about cRPO — confirmed in transcript as the key metric. Good call, keep using this pattern"
- "key_tensions missed the CFO transition overhang — inter_quarter_context showed -4.9% reaction but your notes didn't flag it as unresolved"

**Sections to update**:
- §4 Required Output / feedback block: expand `planner_lessons` description to include note quality
- §13 Planner Lesson Quality: expand to cover notes — learner compares analyst_notes against actual outcome
- §3 Step 3 (Lesson Authoring Contract): planner lessons can now reference note quality

### T3: `predictor_lessons` unchanged

`predictor_lessons` still covers synthesis quality — how well the predictor reasoned over the full evidence set. No change needed. The predictor's structured engagement with notes (confirm/refute/complicate) gives the learner visibility into whether the predictor properly challenged the notes or blindly inherited them.
