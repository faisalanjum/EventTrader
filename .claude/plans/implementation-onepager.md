# Earnings Orchestrator: Implementation One-Pager

**Date**: 2026-02-08
**Source of truth**: `earnings-orchestrator.md` (master plan)
**Supporting plans**: `DataSubAgents.md`, `guidanceInventory.md`, `planner.md`, `predictor.md`, `learner.md`
**Infrastructure**: `Infrastructure.md`, `AgentTeams.md`

---

## What We're Building

An automated earnings prediction system triggered by 8-K filings. It predicts stock direction (long/short/hold) with confidence and magnitude, then learns from outcomes to improve itself. Two modes (Historical backtest, Live SDK-triggered) run the identical pipeline. The system self-corrects via a U1 feedback loop where attribution writes lessons that feed the next quarter's planner and predictor.

---

## Pipeline Architecture

```
0. Guidance     guidance-inventory {TICKER} → cumulative guidance history (once per ticker)
1. Discovery    get_quarterly_filings → event.json (all 8-K filings for ticker)
2. Filter       skip quarters with existing result.json (idempotent resume)
3. Quarter Loop (sequential, chronological):
   3a. Planner       reads 8-K + U1 planner_lessons + guidance → structured fetch_plan.json
   3b. DataFetch     orchestrator executes fetch plan via parallel Task sub-agents
   3c. Predictor     reads 8-K + full context bundle → prediction/result.json
4. Attribution  post-event learner writes feedback into attribution/result.json
5. Validation   outputs present + schema-valid (inline, not JSON Schema)
6. Complete     ORCHESTRATOR_COMPLETE {TICKER}
```

Quarters are **sequential** -- Q(n) attribution must complete before Q(n+1) prediction so U1 feedback is available. Parallelism lives *within* each quarter at step 3b: the planner's `fetch` field is an array-of-arrays (tiers). Within a tier, all sources fan out as parallel Task sub-agents; across tiers, sequential fallback (tier N+1 only if tier N returned empty).

### Two Modes

| | Historical | Live |
|---|---|---|
| Trigger | User/batch invocation | Neo4j 8-K ingestion → Claude SDK |
| PIT | `--pit {filed_8k}` on all data queries, fail-closed | None needed -- future data doesn't exist yet |
| Attribution | Same-run (data already exists) | N=35 day timer after 8-K |
| SDK prompt | `/earnings-orchestrator NOG` | `/earnings-orchestrator NOG --live --accession {acc}` |

Both modes run identical pipeline code. Only PIT gating and attribution trigger timing differ.

### Context Bundle

Two-layer design: **JSON as contract** (validate-able, persisted as `prediction/context_bundle.json` for audit) + **rendered sectioned text** (natural for LLM Skill invocation).

The orchestrator assembles `context_bundle.v1` JSON with: `8k_content`, `guidance_history` (raw markdown passthrough), `u1_feedback[]` (all prior quarters' feedback), and `fetched_data{}` (keyed by planner's `output_key`, each with sources/tier metadata). It renders to fixed-order sectioned text: 8-K → Guidance → U1 Feedback → Fetched Data.

- **Planner** receives subset: 8-K + U1 planner_lessons + guidance history.
- **Predictor** receives full bundle.
- **Learner** receives NO bundle -- just 3 paths (prediction result, actual returns, context_bundle ref) and fetches its own post-event data autonomously.

### U1 Self-Learning Loop

Attribution writes a `feedback` block per quarter into `attribution/result.json`:
- `prediction_comparison` -- predicted vs actual (signal, direction, move%)
- `what_worked` (max 2), `what_failed` (max 3), `why` (1-3 sentences)
- `predictor_lessons` (max 3), `planner_lessons` (max 3)

Orchestrator reads **ALL** prior quarters' feedback and passes it **raw** into the next quarter's context bundle. No digest, no scoring, no decay. The LLM IS the digest. Caps per field enforce signal quality at write time. ~140 items across 10 quarters is trivial context.

---

## Data Layer & Platform Constraints

### Data Agents

**11 existing agents** (Neo4j + Perplexity + Alpha Vantage) all require PIT rework: each must return a standard JSON envelope with per-item `available_at` (ISO8601 datetime + timezone) and `available_at_source` provenance tag. **3 planned agents** to build: `web-search`, `sec-fulltext`, `presentations`.

### PIT Enforcement

A single deterministic gate (`pit_gate.py`, stdlib-only Python) validates publication dates -- never content dates. **Fail-closed**: missing or post-PIT `available_at` triggers block + retry (max 2), then clean gap. Runs as `type: command` PostToolUse hook with per-agent specific matchers.

Three PIT lanes feed the same gate:
1. **Internal structured (Neo4j)** -- `available_at` from known schema fields (`n.created`, `r.created`, `t.conference_datetime`); optional WHERE pre-filter.
2. **External structured-by-provider** -- provider emits per-item dates; agent maps to `available_at`; gate validates.
3. **External messy (LLM normalizer)** -- raw output normalized into JSON envelope via transform-only pass; unverifiable items dropped as gaps.

### Platform Constraints (Shape the Entire Design)

| Constraint | Impact |
|---|---|
| **Task tool BLOCKED in forked skills** | All parallel data fetch must happen at orchestrator level via Task fan-out |
| **Task→Task nesting BLOCKED** | Flat fan-out only; sub-agents cannot spawn their own sub-agents |
| **Skills are SEQUENTIAL** | No parallel Skill calls; use Task for parallelism |
| **`disallowedTools` NOT enforced on skills** | Cannot rely on frontmatter restrictions; must use structural enforcement (hooks, wrappers) |
| **SubagentStop hooks CAN block** | Useful for output validation gates before results return to caller |
| **Agent hooks require Task spawn** | `--agent` flag does NOT activate frontmatter hooks; must spawn via Task tool |

### SDK Requirements

`permission_mode="bypassPermissions"`, `tools={'type':'preset','preset':'claude_code'}`, `CLAUDE_CODE_ENABLE_TASKS=1`. All workflows fully non-interactive. No `AskUserQuestion` anywhere.

---

## Module Status & Implementation Order

### Readiness Matrix

| Module | Existing Asset | Plan Readiness | Gap Size | Key Blocker |
|--------|---------------|----------------|----------|-------------|
| **Planner** | No skill exists (`earnings-planner/` empty) | Spec ~90% done | **Small** | Prompt template + frontmatter only |
| **Predictor** | Skeleton `SKILL.md` (wrong output, wrong tools) | Spec ~85% done | **Medium** | Major skill rewrite: new `prediction_result.v1`, tool lockdown, rubric |
| **Learner** | Old `SKILL.md` v2.2 (~10% aligned) | Scaffold done | **Large** | Fundamental redesign: markdown→JSON, feedback contract, multi-model prep |
| **Guidance** | Working `SKILL.md` v1.6 + support files | 18-section framework | **Small** | Integration spec (I5 bridge) + resolve G1-G8 |

### Open Questions

| Module | P0 Open | P1 Open | P2 Open | Total |
|--------|---------|---------|---------|-------|
| Planner | 0 | 3 | 0 | **3** |
| Predictor | 1 (R2) | 3 | 0 | **4** |
| Learner | 0 | 3 | 0 | **3** |
| Guidance | 3 (G1-G3) | 4 | 1 | **8** |

**Total**: 4 P0 open, 13 P1 open, 1 P2 open = **18 open questions** across all modules.

### Critical Path

```
Phase A: Interface Contracts ──── ALL 7 RESOLVED (I1-I7) ✓
    │
Phase B: Module Implementation (sequential)
    ├─ B1: Planner + Predictor (tightly coupled core loop)
    ├─ B2: Attribution/Learner (biggest redesign, depends on B1 outputs)
    └─ B3: Guidance Integration Hardening (parallel-safe with B2)
    │
Phase C: Final Consistency Pass
    ├─ C1: Skill-sync checklist (diff current vs required frontmatter)
    ├─ C2: File layout verification (cross-module path consistency)
    └─ C3: Implementation-ready checklist
```

**Dependency chain**: DataSubAgents PIT layer must be ready before planner can be tested with real data.

---

## Build Plan

### Reusable Assets

- **guidance-inventory skill v1.6** -- Production-ready with support files (QUERIES, OUTPUT_TEMPLATE, FISCAL_CALENDAR). ~80% reusable.
- **11 data sub-agents** in `.claude/agents/` -- All functional, need PIT-compliance rework (JSON envelope, `available_at`).
- **`get_quarterly_filings.py`** -- Working discovery script, feeds Step 1.
- **`build_orchestrator_event_json.py` hook** -- Auto-builds `event.json` from filing discovery.
- **Evidence standards + Neo4j cookbooks** -- Shared reference files for citation and query patterns.

### Must Build From Scratch

| Component | Purpose |
|-----------|---------|
| **Planner skill** (`earnings-planner/SKILL.md`) | Reads 8-K + U1 feedback, emits `fetch_plan.v1` JSON. Single-turn, no data fetching. |
| **`pit_gate.py` + `pit_fetch.py`** | PIT enforcement layer -- fail-closed gate for historical mode. Foundation dependency. |
| **Context bundle renderer** | Converts `context_bundle.v1` JSON to sectioned text (~20 lines, deterministic). |
| **`build_summary.py`** | Aggregation: reads per-quarter `result.json` → summary CSV. Not orchestrator scope. |
| **Inline validation logic** | 5 deterministic rules (bucket derivation, signal derivation, range precision). Code-only. |

### Must Rewrite

- **Orchestrator skill** -- 4 of 8 steps are placeholders; needs full wiring of planner, data fan-out, predictor, attribution loop.
- **Predictor skill** -- Wrong output schema, wrong tool access (allows Task/Skill/filtered-data; must be bundle-only).
- **Attribution/Learner skill** -- ~10% aligned. New `attribution_result.v1` schema, U1 feedback block, autonomous data fetching, Phase 2 multi-model readiness.

### Recommended Build Order

| Step | Component | Rationale |
|------|-----------|-----------|
| 1 | `pit_gate.py` + `pit_fetch.py` | Foundation -- everything depends on PIT enforcement |
| 2 | Reference agent rework (neo4j-news as template) | Establish JSON envelope + `available_at` pattern for all 11 agents |
| 3 | Planner skill (new) | Unblocks predictor testing via `fetch_plan.v1` generation |
| 4 | Predictor skill rewrite | Lock tool access, implement `prediction_result.v1`, add inline validation |
| 5 | Orchestrator skill rewrite | Wires planner + data fan-out + predictor + validation (core integration) |
| 6 | Learner skill rewrite | Biggest effort, least dependency on others. New schema + U1 feedback |
| 7 | Guidance integration hardening | Resolve G1-G8, lock BUILD/UPDATE trigger, verify sub-files |
| 8 | `build_summary.py` + consistency pass | Aggregation tooling + cross-module contract verification |

---

## Key Design Decisions (Locked)

| Decision | Choice | Why |
|----------|--------|-----|
| State management | File-authoritative (result.json existence = done) | Idempotent resume, crash recovery for free |
| Quarter processing | Sequential | U1 feedback chain requires Q(n) attribution before Q(n+1) prediction |
| Planner turns | Single-turn | U1 self-corrects gaps across quarters |
| Predictor data access | Bundle-only (no fetching) | Speed + single PIT surface + clean separation |
| Scoring method | Rubric-guided holistic (no weighted formula) | LLM reasons naturally; U1 corrects drift |
| Signal derivation | Deterministic f(direction, confidence, magnitude) | Not a separate LLM judgment |
| Multi-model learning | Attribution/Learner only (Phase 2, deferred) | No speed constraint + compound U1 returns |
| Aggregation | Separate tooling (not orchestrator scope) | Clean separation of concerns |
| Validation | Inline code (not JSON Schema) | Cross-field rules (score→bucket, signal derivation) need code logic |

---

*Built by one-pager-team: pipeline-writer, module-writer, infra-writer, buildplan-writer*
*Source plans: earnings-orchestrator.md, DataSubAgents.md, Infrastructure.md, AgentTeams.md, planner.md, predictor.md, learner.md, guidanceInventory.md*
