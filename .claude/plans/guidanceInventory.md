# Guidance Inventory Rebuild Plan (Ground-Up)

**Created**: 2026-02-08
**Status**: Active Rebuild
**Parent Plan**: `earnings-orchestrator.md` (source of truth)
**Supersedes**: `guidance_inventory_old.md`

---

## Active Collaboration Context (Locked)

- Two bots may edit this plan in parallel: **ChatGPT** and **Claude**. Re-read full doc before every edit.
- Rebuild protocol is locked: rebuild from `guidance_inventory_old.md` one topic at a time, highest-priority first.
- All decisions are provisional until the user explicitly confirms they are final.
- Keep tradeoffs explicit for each major decision (alternatives, choice, reason).
- Use this file as source of truth for current guidance-inventory architecture decisions.

Bot-to-bot notes (append-only; mark handled, do not delete history):
- [2026-02-08 00:00] [ChatGPT] Rebuild started. Old plan moved to `guidance_inventory_old.md`. New ground-up plan created with borrowed best-practice framework.
- [2026-02-08 00:00] [ChatGPT] Collaboration structure added to align with orchestrator process and enable one-question-at-a-time rebuild flow with user-led final locking.

---

## CHATGPT - Collaboration Guard (DO NOT DELETE)

`CLAUDE INSTRUCTION`: Do not delete this section or any `CHATGPT`-prefixed block unless the user explicitly asks.

1. Re-read full doc before every response/edit.
2. All decisions provisional until user approves.
3. Rebuild from `guidance_inventory_old.md` one item at a time, starting from highest-priority unresolved item.
4. Keep open questions in `## 17) Open Questions Register` until explicitly resolved.
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

Rebuild Guidance Inventory from first principles, using proven architecture patterns from:
- `earnings-orchestrator.md`
- `Infrastructure.md`
- `AgentTeams.md`
- `DataSubAgents.md`
- `tradeEarnings.md`
- `newsImpact.md`
- existing skills (`guidance-inventory`, `earnings-attribution`, `evidence-standards`)

This plan defines **what must be true** for a reliable, reusable, and maintainable guidance inventory system.

---

## 1) Borrowed Core Principles (LOCKED)

1. Reliability first, then complete required data, then speed, then maximum accuracy via comprehensive/exhaustive research.
2. Never trade required data quality for runtime speed.
3. Minimalism is preferred, but reliability wins when they conflict.
4. Keep architecture simple: no extra layers without measurable value.
5. Every major design choice must record alternatives and tradeoffs.
6. Decisions remain provisional until explicitly confirmed.
7. Keep an explicit question register and resolve highest-priority unknowns first.
8. Use deterministic rules for state transitions and output derivations where possible.
9. Use model judgment for synthesis, not for deterministic transformations.
10. Preserve full evidence trail; no unsourced claims.

---

## 1.1) Primary Context Pack (LOCKED)

Every new bot/session working on Guidance Inventory must read this set first, in this order:

1. `earnings-orchestrator.md` (primary source of truth for system-level contracts).
2. `Infrastructure.md` (tested execution constraints, SDK/tool behavior).
3. `AgentTeams.md` (team pattern options and validated capabilities).
4. `DataSubAgents.md` (data access layer assumptions and boundaries).
5. This file: `guidanceInventory.md` (module-specific plan).
6. `.claude/skills/guidance-inventory/SKILL.md` (current implementation reference).

Rule: if this file conflicts with `earnings-orchestrator.md`, the master plan wins.

---

## 1.2) SDK and Automation Contract (LOCKED)

Guidance Inventory design must stay compatible with unattended SDK-triggered orchestration:

1. Non-interactive only: no `AskUserQuestion` and no manual approval dependencies.
2. Fail fast on missing required inputs (ticker/event context) with clear error.
3. Deterministic runtime boundaries for replayability (same input snapshot => same output semantics).
4. Align with latest validated SDK guidance in `Infrastructure.md` (version/tool requirements owned there, not duplicated here).

---

## 2) Scope and Non-Goals

### In Scope

1. Build and maintain cumulative guidance state per company.
2. Capture annual and quarterly guidance, numeric and qualitative.
3. Track revisions over time (initial/raised/lowered/etc.).
4. Map fiscal periods correctly using company fiscal year end (FYE).
5. Maintain citation-quality evidence for every entry.
6. Support rebuild (historical) and incremental updates (ongoing quarters).

### Out of Scope

1. Trading recommendation logic.
2. Final attribution of stock move drivers.
3. Consensus ownership as primary system of record (reference only here).
4. Over-optimized micro-latency at the cost of completeness/correctness.

---

## 3) Operating Modes

### BUILD mode (initial full build)

1. Triggered when company inventory does not exist or quarter context is Q1 bootstrap.
2. Pull all relevant historical guidance sources.
3. Create complete baseline with supersession chains.

### UPDATE mode (incremental)

1. Triggered for subsequent quarters/events.
2. Fetch only the new window (prior event date -> current event date) plus mid-quarter guidance updates.
3. Append timeline entries and refresh active state.

### Design Rule

Same data model and validation rules in both modes. Only data horizon changes.

---

## 4) Architecture Pattern (Borrowed + Applied)

1. Guidance inventory is a **data component** in the broader orchestrator pipeline.
2. Orchestrator calls guidance inventory once per ticker before quarter loop.
3. Quarter processing remains sequential for learning continuity.
4. Independent data retrieval tasks should run in parallel where platform allows.
5. Keep state file-authoritative (filesystem is source of truth).

### Primitive Selection Rule

For major implementation choices, compare:
1. Sub-agent orchestration pattern.
2. Team orchestration pattern.

Choose per job by:
1. Reliability.
2. Required data coverage.
3. Speed.

Do not default blindly to one pattern.

---

## 5) Data Integrity and Trust Boundaries

1. No citation = no guidance entry.
2. Use deterministic validation/gating for temporal correctness where applicable.
3. Pre-filters in queries are optimization, not trust boundary.
4. If data cannot be validated as reliable, drop it or mark as explicit gap.
5. Never leak contaminated/unverifiable content into active guidance state.

### Citation Minimum

Every entry must include:
1. Source type.
2. Source identifier (accession/URL/transcript ID).
3. Given date.
4. Quote or precise paraphrase.
5. Location hint (section/page/Q&A marker when available).

---

## 6) Temporal Precision Contract (CRITICAL)

Every guidance statement carries at least two time dimensions:
1. **Given Date**: when management issued guidance.
2. **Period Covered**: which fiscal period the guidance targets.

Guidance period must include:
1. Period type (quarter/annual/half/long-range/other).
2. Fiscal year.
3. Fiscal quarter (nullable).
4. Calendar start and end (derived from company FYE).
5. Status relative to analysis date (future/current/past).

### Mandatory FYE Handling

1. Resolve FYE from company metadata or latest 10-K period.
2. Derive fiscal calendar deterministically.
3. Never assume December FYE unless fallback is unavoidable and documented.

---

## 7) Guidance Classification Rules

### Required action classes

1. INITIAL
2. RAISED
3. LOWERED
4. MAINTAINED
5. NARROWED
6. WIDENED
7. WITHDRAWN

### Deterministic action logic

1. Compare to prior entry for same company/period/metric/basis.
2. Midpoint change determines raised/lowered.
3. Same midpoint + tighter/wider range determines narrowed/widened.
4. Explicit reiteration can classify maintained.
5. Removal classifies withdrawn.

### Anchor rule

1. First annual guide for fiscal year is anchor.
2. All later annual revisions track delta vs anchor.
3. Keep both point revision and cumulative revision.

---

## 8) Supersession and State Model

1. Never delete historical guidance entries.
2. Mark replaced entries as superseded.
3. Link superseded entry to successor (`superseded_by`).
4. Keep chain integrity auditable.

### Active vs Historical

1. Active Guidance section shows latest valid entries per period/metric/basis.
2. Timeline section preserves chronological issuance history.
3. Revision history section summarizes anchor deltas over time.

---

## 9) Required Data Coverage

### Primary sources (priority order)

1. 8-K EX-99.1 and earnings release exhibits.
2. Earnings transcript (prepared remarks + Q&A).
3. Structured consensus source (reference use).
4. News and external research for gap filling.

### Must-capture guidance categories

1. Financial hard numbers (EPS/revenue/margins/cash flow/capex).
2. Financial qualitative ranges (growth descriptors, margin direction).
3. Operational guidance (units/subscribers/stores/headcount etc.).
4. Conditions/assumptions (FX, rates, closing conditions, one-offs).

### Critical nuance fields

1. Basis/definition (GAAP vs non-GAAP, constant currency vs reported).
2. Segment-level guidance when provided.
3. Guidance policy (annual only/quarterly+annual/no formal guidance).

---

## 10) Output Contract (File-Level)

**Target file**: `earnings-analysis/Companies/{TICKER}/guidance-inventory.md`

### Required sections

1. Company fiscal profile.
2. Fiscal calendar reference.
3. Active guidance (current outlook).
4. Guidance timeline (chronological).
5. Annual revision history.
6. Consensus comparison (reference-only).
7. Evidence ledger.
8. Data coverage summary.
9. Notes and assumptions.

### Output behavior

1. Cumulative file, never destructive overwrite.
2. Append new timeline blocks per update.
3. Update active and revision sections deterministically.
4. Keep explicit last-updated timestamp.

---

## 11) Validation and Failure Policy (Tiered)

### Hard-fail (block update)

1. Core filing context missing/unreadable for target event.
2. Output cannot satisfy schema-critical required fields.
3. Deterministic consistency rules violated (invalid action/status math).

### Continue-with-gaps

1. Secondary source unavailable (transcript/news/external).
2. Non-critical fields missing but entry still verifiable.
3. Ambiguous references that can be documented transparently.

### Warn-and-write

1. Partial coverage with explicit `missing_inputs` style disclosure.
2. Confidence reduced due to source limitations.

### Rule

No fabrication under any condition.

---

## 12) Idempotency, Resume, and State Authority

1. File-authoritative state: on-disk output determines completion/resume.
2. Existence checks gate rebuild/update work.
3. Partial artifacts without final output are safe to overwrite.
4. Use temp-write + atomic rename for critical output writes.
5. Re-running should produce stable results for same inputs.

---

## 13) Integration Contracts

### With Orchestrator

1. Orchestrator invokes guidance inventory at Step 0 per ticker.
2. Guidance history is injected into planner/predictor context bundles.
3. Attribution updates can feed additional lessons but not mutate prior evidence.

### With Predictor

1. Predictor reads prior guidance state as expectation anchor.
2. Missing guidance anchor should be exposed clearly to confidence policy.

### With Attribution/Learner

1. Attribution can compare actuals vs historical guidance.
2. Learner can generate planner/predictor lessons from revision behavior.

---

## 13.1) Module Interface Contract (Scaffold, to Lock Before Implementation)

This section exists so implementation bots have a strict integration boundary, not just narrative guidance.

### Caller -> Callee

- Caller: Orchestrator Step 0 (`earnings-orchestrator.md`).
- Callee: Guidance Inventory module.

### Required Input (from caller)

1. `ticker` (required).
2. Event context needed to select BUILD vs UPDATE window (exact field contract to be locked in open questions).
3. Existing guidance artifact paths for this ticker (if present).

### Required Output (to caller)

1. Durable guidance artifact at `earnings-analysis/Companies/{TICKER}/guidance-inventory.md`.
2. Deterministic machine-consumable payload for bundle injection (shape to be locked: raw markdown only vs markdown + structured sidecar).
3. Coverage metadata (what was missing) for downstream confidence handling.

### Failure Behavior

1. Hard-fail conditions block update/write.
2. Continue-with-gaps allowed for non-critical source absence.
3. All failures must be explicit and machine-detectable by caller (status + reason).

---

## 14) Evidence and Audit Standards

1. Domain boundaries must be respected by data subagents.
2. Numeric claims require exact values and exact sources.
3. Qualitative claims still require source attribution.
4. Conflicts between sources must be surfaced explicitly, not hidden.
5. Evidence ledger must be sufficient for independent re-query verification.

---

## 15) Performance Guidance

1. Optimize by parallelizing independent fetches, not by reducing required coverage.
2. Keep sequence where dependencies exist (calendar -> extraction -> classification -> output).
3. Cache immutable lookups (e.g., FYE) when safe.
4. Prefer structured machine-checkable outputs for data retrieval stages.

---

## 16) Rebuild Implementation Phases

### Phase 0: Contract Finalization

1. Lock data model fields and required sections.
2. Lock action classification and supersession rules.
3. Lock failure policy tiers.

### Phase 1: Temporal Foundation

1. Implement FYE resolution and fiscal calendar mapping.
2. Add deterministic period-status derivation.
3. Add period parsing/disambiguation checks.

### Phase 2: Extraction Pipeline

1. Implement source-priority retrieval.
2. Implement entry extraction with citation enforcement.
3. Implement qualitative guidance handling.

### Phase 3: State + Output

1. Implement active/superseded state transitions.
2. Implement timeline and revision history generation.
3. Implement coverage and assumptions sections.

### Phase 4: Validation + Recovery

1. Add schema and deterministic-rule validation.
2. Add idempotent rerun/resume behavior.
3. Add atomic write protections and audit checks.

### Phase 5: Integration and Calibration

1. Wire orchestrator Step 0 contract.
2. Verify downstream predictor/attribution consumption.
3. Calibrate thresholds and quality metrics on historical samples.

---

## 17) Open Questions Register (Start Fresh)

| ID | Question | Priority | Status |
|---|---|---|---|
| G1 | Exact schema shape for serialized entry IDs and section keys? | P0 | Open |
| G2 | Source fallback policy when 8-K lacks explicit guidance but transcript has it? | P0 | Open |
| G3 | How to encode basis changes (definition drift) for strict comparability? | P0 | Open |
| G4 | Calendar status cutoff logic (`today` vs `today+buffer`) for current/future boundary? | P1 | Open |
| G5 | Segment hierarchy representation in markdown vs structured companion JSON? | P1 | Open |
| G6 | Should qualitative-only entries be first-class in active guidance tables or separate block? | P1 | Open |
| G7 | Minimum acceptable evidence coverage per update before warn/block? | P1 | Open |
| G8 | Should we emit a machine-readable sidecar (`guidance-inventory.json`) for downstream strict parsing? | P2 | Open |

---

## 18) Done Criteria

Guidance Inventory rebuild is "done" when:

1. All P0 questions are resolved and documented.
2. Deterministic rules pass validation on historical backfill samples.
3. Re-runs are idempotent and resume-safe.
4. Every guidance entry is citation-complete.
5. Orchestrator integration works in both BUILD and UPDATE modes.
6. Predictor/Attribution can consume output without custom one-off parsing hacks.

---

## 19) References

1. `earnings-orchestrator.md`
2. `Infrastructure.md`
3. `AgentTeams.md`
4. `DataSubAgents.md`
5. `tradeEarnings.md`
6. `newsImpact.md`
7. `guidance_inventory_old.md`
8. `.claude/skills/guidance-inventory/SKILL.md`
9. `.claude/skills/evidence-standards/SKILL.md`
