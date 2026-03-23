# Earnings Orchestrator

---

## 0. Principles — LOCKED

**Top prerequisite**: read `Infrastructure.md` and `AgentTeams.md` before proposing anything. Those are the tested primitives we build with.

**Primitive selection rule — LOCKED**:
1. For each major implementation decision, evaluate both options: sub-agent orchestration (`Infrastructure.md`) and team orchestration (`AgentTeams.md`).
2. Choose the best option for that specific job using our priorities: reliability first, full required data, then speed, then accuracy via comprehensive/exhaustive research.
3. Do not default blindly to one pattern; record the tradeoff in the relevant section.

**SDK-compatibility rule — LOCKED**:
1. Every component/workflow designed in this doc must remain triggerable from Claude Agent SDK in non-interactive mode.
2. Any design requiring interactive permission prompts is invalid for production automation; align with Infrastructure SDK constraints (for example `permission_mode=\"bypassPermissions\"`).
3. Before locking an implementation decision, re-check the relevant SDK-tested constraints in `Infrastructure.md` (SDK sections) to confirm triggerability is preserved.
4. **Neo4j dual-connection config**: Guidance writes use two independent Neo4j connections — MCP server (for reads) and `guidance_write.sh` (for writes via `guidance_writer.py`). Both currently hardcode `bolt://localhost:30687`. For SDK deployment, ensure both derive their connection config from the same source (e.g., a single `.env` file or SDK-injected env vars) to prevent config drift.

**What we're building**: automatic earnings prediction the moment data is available. Every data point arrives on time, complete, no noise. The system improves itself — each learning cycle makes prediction better.

**Optimization objective — LOCKED**: maximize expected trading value (risk-adjusted) by optimizing precision and recall together under explicit guardrails.
`minimum opportunity/recall floor` = do not tune so conservatively that the system generates too few actionable signals; enforce a minimum coverage/action-rate threshold during calibration.

**Real-time priority order — LOCKED**:
1. Keep all required data coverage and full-quality analysis.
2. Then optimize speed so real-time prediction completes in a few minutes.
3. Then maximize accuracy with comprehensive/exhaustive research inside the decision window.
4. Never trade required data quality or decision quality for speed.

**Prediction vs Learning philosophy — LOCKED**:
1. Historical predictor is PIT-bound at the 8-K filing timestamp. Live predictor is decision-window-bound: orchestrator may include any data available before decision cutoff in the bundle.
2. Historical predictor does **not** use current-quarter transcript/presentation/10-Q/10-K. Live mode: orchestrator may include newly available pre-cutoff data in the bundle. Predictor is always bundle-only.
3. Attribution/Learner is post-event: use full material set (transcript, presentation, 10-Q/10-K, realized move) to explain drivers.
4. Attribution/Learner must convert findings into reusable guidance that improves future planner/predictor behavior without quarter-specific overfitting.

**How we build it**: natural design — the simplest structure where the right things happen on their own. No unnecessary layers. Complexity must justify itself. Reliability wins over minimalism when they conflict.

**How we work**: question everything. All inputs preliminary. Explore alternatives, present tradeoffs, suggest improvements. One question at a time to the user. After every input or answer: re-read full doc, re-prioritize §5, ask the next most important question.

**Decision protocol — LOCKED**:
1. Reason independently before accepting any proposal (including user proposals).
2. Treat inputs as draft by default; do not auto-accept.
3. If we disagree, state it clearly with reasons and a better alternative.
4. Lock a decision only after explicit user confirmation that they have made up their mind and want to proceed with that choice.

**This doc**: sole implementation guide for a zero-context bot. Maximally concise, no information lost. Use diagrams for flows, numbered steps for implementation. Done when §5 is empty.

---

## 1. System Overview — DRAFT

### Two modes, one infrastructure

Both modes run the same pipeline. Only the trigger and PIT mode differ.

```
Historical: user/batch invokes orchestrator → loops through past quarters
Live:       Neo4j ingests 8-K → external trigger → Claude SDK → same orchestrator
```

Ingestion plumbing and SDK trigger are out of scope. We build the Claude Code module that both modes invoke.

Market-session reality (user dataset: 8,172 filings / 770 tickers): `post_market` 52.6% + `pre_market` 45.1% = 97.7%; `in_market` 1.7% and `market_closed` 0.6% are rare but must still be handled.

### Pipeline

```
8-K arrives
  │
  ├─ ORCHESTRATOR (per quarter)
  │    │
  │    ├─ 1. Planner ──── reads 8-K, returns structured fetch plan
  │    │
  │    ├─ 2. Data fetch ─ orchestrator executes fetch plan
  │    │                   parallel fan-out + sequential fallback chains
  │    │
  │    ├─ 3. Predictor ── reads 8-K + merged context bundle
  │    │                   multi-turn reasoning across core (non-exhaustive) dimensions
  │    │                   → direction + confidence + magnitude + signal
  │    │
  │    └─ 4. Attribution/Learner ─ historical: same-pass; live: deferred to next historical bootstrap
  │                        identifies primary drivers
  │                        writes feedback in result.json:
  │                          what_worked, what_failed, why,
  │                          predictor_lessons, planner_lessons
  │                        ↓
  │              ┌─────────┘
  │              │ SELF-LEARNING LOOP (U1)
  │              │ orchestrator reads ALL prior feedback raw
  │              │ passes to next quarter's planner + predictor
  │              │ guardrail: generalizable principles, not hard rules
  │              └─────────→ next quarter's planner + predictor
  │
  └─ Discovery: get_quarterly_filings → event.json (hook auto-builds)
     Filter: skip prediction for quarters with existing prediction/result.json
     Validation: outputs present + schema-valid
     ORCHESTRATOR_COMPLETE {TICKER}
```

### PIT modes

Historical needs PIT because future data already exists in the DB and could leak. Live doesn't — future data doesn't exist yet. Live may use additional data that appears before decision cutoff.

| Mode | Skill | `--pit` | Gate |
|------|-------|---------|------|
| Historical backtest | `earnings-prediction` | `--pit {filed_8k}` | Fail-closed |
| Live (SDK) | `earnings-prediction` | None | None |
| Learning | `earnings-attribution` | None | None |

SDK wrapper: top-level session, `permission_mode="bypassPermissions"`.

---

## 2. Components — DRAFT

### 2a. Orchestrator

**Purpose**: coordinate the full pipeline per ticker per quarter.

**Steps**:
1. Discovery — `get_quarterly_filings {TICKER}` → `event.json` (hook auto-builds)
2. Filter — skip prediction for quarters with existing `prediction/result.json`
3. For each pending quarter (chronological):
   a. Load all prior quarters' attribution `feedback` + guidance history (query Neo4j Guidance/GuidanceUpdate nodes for this ticker; empty if none exist — **note**: original design referenced `guidance-inventory.md` but that file does not exist; extraction pipeline writes directly to Neo4j graph via `guidance_writer.py`) and include in the context bundle.
   b. Planner (forked skill) → returns fetch plan
   c. Orchestrator executes fetch plan via parallel Task sub-agents (DataSubAgents)
   d. Predictor (forked skill) receives 8-K + merged data bundle → result.json
   e. Verify result
4. Attribution/Learner loop — for predicted quarters without attribution:
      - Historical mode: run immediately (data exists). Sequential processing ensures Q(n) attribution completes before Q(n+1) prediction, so U1 feedback is available.
      - Live mode: deferred to next historical bootstrap. The external trigger daemon (`EarningsTrigger.md`) enqueues HISTORICAL when the ticker re-enters trade_ready; the orchestrator catches the missing attribution during sequential processing. No source-gating — learner runs with whatever data is available at that time. (Original design was N=35 day timer; replaced by deferred approach to avoid live-queue token competition.)
      - Annual-quarter note: with the deferred approach, the 10-K is typically available by the time the next historical bootstrap runs (~90 days). No special exception needed. If the 10-K is still unavailable, the orchestrator runs the learner with available data and records `"10-K"` in `missing_inputs`.
      - Hard-fail gate: `prediction/result.json` + `daily_stock` label must exist. Without these, attribution cannot compare prediction vs reality. Everything else (transcript, 10-Q, 10-K, news) enriches but is not required.
      - Attribution/Learner writes `missing_inputs` array in output (e.g., `["transcript", "10-Q"]`) so U1 feedback carries context about what data was available.
5. Validation — outputs present + schema-valid
6. `ORCHESTRATOR_COMPLETE {TICKER}`

**Note**: Aggregation (cross-quarter summary CSV) is explicitly NOT orchestrator scope. See §4 aggregation tooling.

**Data integration**: Two-pass hybrid (Q4 resolved). Planner decides questions → orchestrator parallelizes fetches → predictor receives bundle.

**Speed lever**: Step 3b (parallel fan-out) is the primary speed mechanism. All independent data fetches run simultaneously via Task sub-agents. Sequential fallback chains only where required (e.g. news source A→B→C). See §0 real-time priority. **v2 optimization**: use `run_in_background` + polling with per-source timeout (30s) for live mode, so one slow source doesn't block the entire fetch step.

**Concurrency**: Sequential quarters (Q5 resolved). Attribution/Learner output from Q(n) feeds prediction for Q(n+1). Parallelism is within each quarter (step 3b data fan-out).

**State policy** (Q16 resolved): file-authoritative. Durable progress and resume are derived from filesystem outputs (`result.json`, context files). Claude Tasks are optional as an in-run progress mirror only; never source of truth. If task state and file state conflict, file state wins.

**Context bundle contract (I1 resolved)**:

The context bundle is the central data structure the orchestrator assembles and passes to the planner, predictor, and learner. Two layers: **JSON as contract** (structured, validate-able, persisted for audit) + **rendered text as delivery** (natural for LLM Skill invocation).

**JSON schema** (`context_bundle.v1`):

```json
{
  "schema_version": "context_bundle.v1",
  "ticker": "NOG",
  "quarter_label": "Q3_FY2024",
  "filed_8k": "2024-11-07T13:01:00Z",
  "mode": "historical",
  "pit_datetime": "2024-11-07T13:01:00Z",
  "decision_cutoff_ts": null,
  "context_cutoff_ts": "2024-11-07T09:00:00Z",
  "context_cutoff_reason": "historical_release_session_floor",
  "assembled_at": "2026-02-08T14:30:00Z",

  "8k_content": "(raw 8-K EX-99.1 text)",

  "guidance_history": "(structured guidance data from Neo4j Guidance/GuidanceUpdate nodes — see STALE REFERENCE note below)",
  "guidance_history_source": "neo4j:Guidance+GuidanceUpdate nodes for ticker",

  "inter_quarter_context": "(unified timeline: day-level market tape + news + filings + dividends + splits with event-specific forward returns — pre-assembled by build_inter_quarter_context(), see plannerStep5.md)",
  "inter_quarter_context_ref": "path/to/inter_quarter_context.json",

  "u1_feedback": [
    {
      "quarter": "Q2_FY2024",
      "prediction_comparison": { "predicted_signal": "lean_long", "actual_move_pct": 3.2, "correct": true },
      "what_worked": ["..."],
      "what_failed": ["..."],
      "why": "...",
      "predictor_lessons": ["..."],
      "planner_lessons": ["..."]
    }
  ],

  "fetched_data": {
    "guidance_context": {
      "sources": ["neo4j-report", "neo4j-transcript"],
      "tier_used": 0,
      "content": "(merged text from all sources in the tier that returned data)"
    },
    "consensus_context": {
      "sources": ["alphavantage-earnings", "alphavantage-estimates"],
      "tier_used": 0,
      "content": "(structured: EPS/Revenue estimate avg/high/low, analyst count, revision history)"
    }
  },

  "anchor_flags": {
    "has_consensus": true,
    "has_prior_guidance": true,
    "has_prior_financials": true,
    "has_transcript_context": false
  },

  "fetch_plan_ref": "planner/fetch_plan.json"
}
```

**Field semantics:**

| Field | Required | Notes |
|-------|----------|-------|
| `schema_version` | Yes | Always `"context_bundle.v1"` |
| `ticker`, `quarter_label`, `filed_8k` | Yes | Event identifiers |
| `mode` | Yes | `"historical"` or `"live"` |
| `pit_datetime` | Yes | Historical = `filed_8k`. Live = null (no PIT gate). |
| `decision_cutoff_ts` | Live only | Auto-recorded at prediction-start. Null for historical. |
| `context_cutoff_ts` | Yes | Effective upper bound for timestamped context (inter-quarter timeline, etc.). Live = `decision_cutoff_ts`. Historical = release-session floor derived from current 8-K timestamp + market_session. See `plannerStep5.md` "Context Cutoff" section. |
| `context_cutoff_reason` | Yes | `"live_decision_cutoff"` or `"historical_release_session_floor"` |
| `assembled_at` | Yes | ISO timestamp when bundle was built |
| `8k_content` | Yes | Raw 8-K EX-99.1 text. Hard-fail if missing (§2c). |
| `guidance_history` | Yes | **STALE REFERENCE (2026-03-19)**: This field originally said "raw guidance-inventory.md file contents." Verified: **zero** `guidance-inventory.md` files exist on disk. The extraction pipeline writes structured guidance directly to Neo4j graph nodes (327 Guidance + 5,163 GuidanceUpdate + 173 GuidancePeriod nodes) via `guidance_writer.py`. The orchestrator should query Neo4j for this ticker's Guidance/GuidanceUpdate data and render it as text for the bundle. Empty if no Guidance nodes exist for the ticker. |
| `guidance_history_source` | Yes | `"neo4j"` — queried from Guidance/GuidanceUpdate graph nodes. |
| `inter_quarter_context` | Yes | Pre-assembled unified timeline (news + filings + dividends + splits with forward returns). Built by `build_inter_quarter_context()` — see `plannerStep5.md`. Top-level field, NOT inside `fetched_data`. |
| `inter_quarter_context_ref` | Yes | Relative path to persisted `inter_quarter_context.json`. |
| `u1_feedback` | Yes | Array of prior quarters' `feedback` blocks from attribution/result.json. Empty `[]` for first quarter. Chronological order. |
| `fetched_data` | Yes | Object keyed by `output_key` from fetch_plan. Each value has `sources` (agent names), `tier_used` (0-indexed, -1 if all tiers empty), `content` (merged text or null). |
| `anchor_flags` | Yes | Deterministic orchestrator-derived booleans used by predictor missing-data policy. Not LLM judgment. |
| `fetch_plan_ref` | Yes | Relative path to persisted fetch_plan.json. Audit trail: bundle → plan → planner reasoning. |

**Anchor flags (v1)**:
- `has_consensus`: `true` when a canonical consensus question returned usable pre-filing expectation data.
- `has_prior_guidance`: `true` when `guidance_history` is non-empty.
- `has_prior_financials`: `true` when the canonical `prior_financials` question returned usable data.
- `has_transcript_context`: `true` when the canonical `prior_transcript_context` question returned usable data.

These flags are deterministic convenience metadata for the predictor. They reduce accidental overconfidence by making key-anchor availability explicit instead of forcing the predictor to infer it from prose.

**Persistence**: orchestrator writes `prediction/context_bundle.json` once per quarter. This is the audit/replay artifact. Write-once, never overwrite.

**Rendering to text**: for Skill invocation, orchestrator renders the JSON to sectioned text:

```
=== CONTEXT BUNDLE: {ticker} {quarter_label} ===
Mode: {mode} | PIT: {pit_datetime} | Assembled: {assembled_at}

## 8-K CONTENT
{8k_content}

## GUIDANCE HISTORY
{guidance_history}

## INTER-QUARTER CONTEXT
{inter_quarter_context}

## ANCHOR FLAGS
has_consensus: {has_consensus}
has_prior_guidance: {has_prior_guidance}
has_prior_financials: {has_prior_financials}
has_transcript_context: {has_transcript_context}

## PRIOR FEEDBACK (U1)
### Q2_FY2024
prediction_comparison: predicted lean_long, actual +3.2%, correct
what_worked: [...]
what_failed: [...]
why: ...
predictor_lessons: [...]
planner_lessons: [...]

### Q1_FY2024
(same structure)

## FETCHED DATA: guidance_context
Sources: neo4j-report, neo4j-transcript (tier 0)
{content}

## FETCHED DATA: consensus_context
Sources: alphavantage-earnings (tier 0)
{content}
```

Rendering rules:
1. Fixed sections always present in this order: 8-K → guidance → inter-quarter context → anchor flags → U1 → fetched data.
2. U1 feedback rendered chronologically (oldest first — same as processing order).
3. Fetched data sections rendered in fetch_plan question order.
4. Each fetched data section includes source attribution line (which agents, which tier).
5. If `content` is null for a fetched data section, render `(no data returned)`.
6. Renderer is deterministic: same JSON → same text, always.

**Planner vs Predictor delivery**:
- Planner receives: `8k_content` + `u1_feedback` (planner_lessons only) + `guidance_history` + `inter_quarter_context`. No `fetched_data` or `anchor_flags` (planner produces the fetch plan, doesn't consume fetched results).
- Predictor receives: full bundle, including `anchor_flags`.

**Learner does NOT receive a context bundle** (I4 resolved):
The learner is fundamentally different from the predictor — no speed constraint, no PIT, multi-turn, follows evidence trails. Pre-assembling a bundle would constrain it unnecessarily. Instead, the orchestrator passes 3 minimal inputs:
1. Path to `prediction/result.json` — to compare prediction vs reality (mandatory)
2. Actual returns (daily_stock, hourly_stock values) — the outcome being explained (mandatory)
3. Path to persisted `prediction/context_bundle.json` — for reference/comparison only ("what data did the predictor have?"), not for primary reasoning

The learner then autonomously fetches whatever post-event data it needs (transcript, 10-Q, analyst reactions, XBRL, news) via direct MCP tools and Skill calls. This aligns with: (a) no speed constraint, (b) "uses all available post-event data" (§2d), (c) Phase 2 multi-model design where autonomous teammates investigate independently.

**Why JSON + text, not text-only**: (1) JSON is validate-able — orchestrator can check required sections before passing to predictor; (2) persisted JSON gives deterministic audit/replay; (3) `fetched_data` metadata (sources, tier_used) is preserved for debugging and learner's `missing_inputs` identification; (4) new data sources = new keys, no format redesign; (5) renderer is ~20 lines of code, negligible complexity.

**SDK invocation contract (Q22 resolved)**:

The orchestrator skill must accept a single prompt string from Claude Agent SDK. Two modes:

| Mode | SDK prompt | What it does |
|------|-----------|--------------|
| Historical | `"/earnings-orchestrator NOG"` | Processes all pending quarters for ticker |
| Live | `"/earnings-orchestrator NOG --live --accession {accession_no}"` | Processes single quarter triggered by new 8-K |

SDK caller requirements (from `Infrastructure.md` Part 8 + Part 10):
```python
from claude_agent_sdk import query, ClaudeAgentOptions

async for msg in query(
    prompt='/earnings-orchestrator NOG',
    options=ClaudeAgentOptions(
        setting_sources=['project'],                          # loads .claude/ directory
        permission_mode='bypassPermissions',                  # no interactive prompts
        tools={'type': 'preset', 'preset': 'claude_code'},   # enables Task tools
        model='claude-opus-4-6',
    )
):
    pass
```

SDK/runtime rules (locked):
- Live mode is **not PIT-gated**. It may use any data available during the live run.
- For deterministic replay, orchestrator records `decision_cutoff_ts` automatically at prediction-start for that quarter and includes it in context/result metadata (no extra SDK arg required). Why: without a fixed cutoff, two live re-runs can see different late-arriving data and produce non-comparable outputs.
- **Live mode must write `live_state.json`** after prediction completes (see §4). This is the contract between orchestrator and external trigger daemon (`EarningsTrigger.md`). The daemon reads it to locate result files without deriving fiscal quarter identity. The orchestrator derives `quarter_label` internally (it has full context: Neo4j access, fiscal math, minutes of runtime for 10-Q/10-K to arrive).
- Use the **latest validated** `claude-agent-sdk` version listed in `Infrastructure.md` (must satisfy Task-tools requirements).
- Fail fast on missing/invalid required args with no partial writes:
  - Historical requires ticker.
  - Live requires ticker + accession.

Required env vars (set in `.claude/settings.json`, NOT manual export):
- `CLAUDE_CODE_ENABLE_TASKS=true` — enables TaskCreate/List/Get/Update
- `CLAUDE_CODE_TASK_LIST_ID` — remove from settings.json for per-ticker override, or set to a fixed value for shared task list

**Implementation constraint**: No `AskUserQuestion`, no interactive permission prompts, no manual approvals anywhere in the pipeline. Everything must complete unattended. If the orchestrator needs a decision, it must have a default (not prompt the user). See §0 SDK-compatibility rule.

### 2b. Planner — DRAFT

**Purpose**: read 8-K earnings report, produce a comprehensive set of data questions for DataSubAgents.

**Behavior** (locked):
- Runs first per quarter, before predictor
- Single-turn. Reads 8-K + U1 feedback → outputs complete fetch plan in one shot.
- Returns structured fetch plan: list of data questions with tiered sources (see `fetch_plan.json` contract below)
- Orchestrator (not planner) executes the fetch plan — planner cannot spawn sub-agents (§3)
- If calibration shows single-turn consistently misses critical data that U1 can't fix, revisit.

**Self-learning input**: Planner reads `planner_lessons` from all prior quarters' attribution feedback (passed by orchestrator in context bundle). Uses them to adjust fetch priorities — e.g., adding sector peer data if past feedback flagged it as a gap. Lessons are soft priors, not hard rules.

**Noise policy (Q24 resolved, both modes)**:
- Planner relevance principle (soft guidance): every fetch should be justified by an explicit 8-K claim, a core dimension (§2c), or a prior U1 `planner_lesson`. This is the planner's reasoning framework, not a validation gate.
- Hard exclusions (already locked, enforced structurally): return labels (`daily_stock`, `hourly_stock`), post-filing artifacts in historical mode (PIT).
- Always included: 8-K content (trigger, always in bundle).
- Same policy both modes. Mode differences are handled by PIT, not noise filtering.

**Planner output contract (`fetch_plan.json`)**:

Planner returns JSON only (no prose wrapper), one object:

```json
{
  "schema_version": "fetch_plan.v1",
  "ticker": "NOG",
  "quarter": "Q3_FY2024",
  "filed_8k": "2024-11-07T13:01:00Z",
  "questions": [
    {
      "id": "guidance_delta",
      "question": "Did management raise, maintain, or lower guidance vs prior?",
      "why": "8-K outlook section + prior guidance context",
      "output_key": "guidance_context",
      "fetch": [
        [
          {"agent": "neo4j-report", "query": "Fetch 8-K EX-99.1 guidance and outlook statements"},
          {"agent": "neo4j-transcript", "query": "Fetch transcript guidance discussions from prepared remarks and Q&A"}
        ],
        [
          {"agent": "perplexity-search", "query": "Find pre-cutoff official guidance references"}
        ]
      ]
    },
    {
      "id": "consensus_vs_actual",
      "question": "How did reported results compare to consensus estimates?",
      "why": "Beat/miss magnitude is primary short-term price driver",
      "output_key": "consensus_context",
      "fetch": [
        [
          {"agent": "alphavantage-earnings", "query": "Get consensus EPS and revenue estimates for this quarter"},
          {"agent": "neo4j-report", "query": "Fetch 8-K EX-99.1 reported actuals (EPS, revenue)"}
        ]
      ]
    }
  ]
}
```

**`fetch` structure — tiered array-of-arrays:**
- `fetch` is an ordered array of **tiers**. Each tier is an array of **sources**.
- **Within a tier**: all sources run in **parallel** (Task fan-out via `Task(subagent_type=agent, prompt=query)`).
- **Across tiers**: **sequential fallback** — tier N+1 runs only if ALL tier N sources returned empty.
- The `agent` field maps directly to a Task `subagent_type` (e.g., `neo4j-report`, `neo4j-transcript`, `perplexity-search`, `alphavantage-earnings`).

**Four fetch patterns the planner can express:**

| Pattern | `fetch` shape | Use case |
|---------|--------------|----------|
| Single source | `[[{A}]]` | XBRL financials: `[[{neo4j-xbrl}]]` |
| Parallel sources | `[[{A}, {B}]]` | Full picture: `[[{neo4j-report}, {neo4j-transcript}]]` |
| Sequential fallback | `[[{A}], [{B}]]` | Consensus: `[[{alphavantage}], [{perplexity-ask}]]` |
| Parallel + fallback | `[[{A}, {B}], [{C}]]` | Guidance: `[[{report}, {transcript}], [{perplexity}]]` |

Execution semantics:
1. Orchestrator executes all `questions[]` items in parallel (Task fan-out per question).
2. For each question, process `fetch` tiers in order (tier 0 first):
   a. Spawn all sources in the tier as parallel Task sub-agents.
   b. Wait for all to complete.
   c. If ANY source returned non-empty data → collect results, skip remaining tiers.
   d. If ALL sources returned empty → advance to next tier.
3. After all tiers processed, write merged results under `output_key` into the context bundle for predictor.
4. If planner output is not valid JSON or missing required fields, Q10 policy applies (block quarter, log error).
5. `questions[].id` must be unique within the plan — **block** if duplicates (ambiguous result mapping).
6. `questions[].output_key` must be unique within the plan — **block** if duplicates (silent data overwrite).
7. Max 3 tiers per question in `fetch[]` — **block** if >3 (hard cap; matches agent catalog tiers).
8. `schema_version` must equal `"fetch_plan.v1"` — **block** (catches version drift or typos).
9. `fetch` array must be non-empty; each tier must be non-empty — **block** (empty fetch/tier crashes execution).
10. Every `fetch` source must have a non-empty `query` string — **block** (empty query spawns agent with no instructions).
11. **Sanity check** (R5, lightweight, code-only — not an LLM call): verify fetch plan includes at least one question targeting consensus data and one targeting prior financials. These are core data types the predictor almost always needs. If missing, log a warning (not a block) — the planner may have valid reasons to omit them, and U1 will self-correct if it was a mistake.
12. >10 questions total — **warn** (log, not block). Target 5-8 questions. Content judgment, not structural error.
13. Canonical ID uses non-canonical output_key (e.g., `consensus_vs_actual` with output_key != `consensus_context`) — **warn** (anchor flag may not trigger; U1 self-corrects).
14. **PIT handling**: not in the schema — orchestrator concern. In historical mode, orchestrator appends `--pit {filed_8k}` to each Task sub-agent's prompt. The planner does not need to know about PIT.

**Canonical planner question IDs (v1)**:

Reuse these IDs whenever the question matches the standard family. New IDs are allowed only when no canonical family fits; they must be stable `snake_case` labels and must not encode ticker/quarter.

| ID | Use |
|----|-----|
| `guidance_delta` | Current-quarter guidance vs prior guidance |
| `consensus_vs_actual` | Current-quarter consensus expectations + reported actuals |
| `prior_financials` | Prior-quarter / historical financial baselines from XBRL |
| `prior_transcript_context` | Prior earnings-call commentary / management tone context |
| `peer_earnings` | Relevant peer earnings or peer reaction context |
| `sector_context` | Broader sector or macro context that should frame the event |

**Pre-assembled orchestrator inputs** (not planner question IDs — the planner receives these as inputs, it does not fetch them):
- `inter_quarter_context` — built by `build_inter_quarter_context()` (see `plannerStep5.md`). Passed to planner as reasoning context and to predictor in the context bundle as a top-level field.
- `guidance_history` — built by `build_guidance_history()` (see `planner.md` Step 4). Same pattern.

These are assembled by the orchestrator before the planner runs. They appear in the context bundle as top-level fields alongside `8k_content` and `u1_feedback`, NOT inside `fetched_data{}`.

`anchor_flags` derive from the canonical planner question output_keys plus `guidance_history`, so the planner should reuse canonical IDs instead of inventing near-duplicates.

**Valid `fetch.agent` values (I7 — locked catalog)**:

The planner must only use agent names from this catalog. Any other value is a validation error. Catalog is extensible — new agents are added here when built.

**Implementation ownership**: All agent implementation (rework + new builds) is owned by `DataSubAgents.md`. This catalog is the consumer-facing view; the planner references it but does not build or maintain agents.

**Available agents** (exist as `.claude/agents/*.md`; PIT compliance status per `DataSubAgents.md`):

| Agent | Domain | Returns | Typical use | PIT Status |
|-------|--------|---------|-------------|------------|
| `neo4j-news` | News articles | Fulltext search over ingested news corpus | Pre-filing news, sector events, company-specific developments | **DONE** — reference impl |
| `neo4j-vector-search` | Semantic search | Vector similarity across News + QAExchange | Find semantically similar news, analyst Q&A by meaning | **DONE** |
| `bz-news-api` | Benzinga API news | On-demand Benzinga headlines/body with channels/tags and PIT-safe envelope | Real-time macro/theme monitoring, channel/tag driven news retrieval | **DONE** |
| `neo4j-report` | SEC filings | 8-K, 10-K, 10-Q text, extracted sections, exhibits (EX-99.1) | Earnings release content, guidance statements, financial tables | **DONE** |
| `neo4j-transcript` | Earnings calls | Prepared remarks, Q&A exchanges, speaker-attributed text | Management commentary, analyst questions, tone/sentiment | **DONE** |
| `neo4j-xbrl` | Structured financials | EPS, revenue, margins, balance sheet items from 10-K/10-Q | Prior-quarter financials, YoY comparisons, trend data | **DONE** |
| `neo4j-entity` | Company metadata | Sector, industry, market cap, price series, dividends, splits | Peer identification, sector context, historical price data | **DONE** |
| `alphavantage-earnings` | Consensus estimates | EPS/revenue consensus, actuals, surprise, earnings calendar | Beat/miss analysis, expectation anchors | **DONE** |
| `yahoo-earnings` | Yahoo Finance wrapper | Earnings dates with EPS estimate/actual/surprise, analyst upgrades/downgrades | Beat/miss history, earnings date confirmation, analyst rating/PT history | **DONE** — PIT-safe for exposed ops (`earnings`, `upgrades`); current-state estimates/calendar remain excluded from the agent |
| `perplexity-search` | Web search | Raw URLs and snippets from web search | Broad coverage gap-fill, recent events not in structured sources | **DONE** |
| `perplexity-ask` | Web Q&A | Single-fact answers with citations | Quick lookups (e.g., "What is {TICKER}'s current dividend yield?") | **DONE** |
| `perplexity-reason` | Web reasoning | Multi-step analysis with chain-of-thought | "Why" questions, causal analysis, comparisons | **DONE** |
| `perplexity-research` | Deep research | Multi-source synthesis reports | Exhaustive investigation (expensive — use as last-tier fallback) | **DONE** |
| `perplexity-sec` | SEC EDGAR | Filing search (10-K, 10-Q, 8-K) from EDGAR | Fallback when Neo4j filings are missing or incomplete | **DONE** |

Alpha Vantage estimates methodology note: coarse PIT uses fixed revision buckets (7/30/60/90 days before fiscal period end). This looks true from data, but AV docs don't clearly guarantee it.

**Planned agents** (to be built as part of `DataSubAgents.md` implementation):

| Agent | Domain | Returns | Typical use |
|-------|--------|---------|-------------|
| `web-search` | General web | WebSearch + WebFetch results with citation metadata | General-purpose web research not covered by Perplexity |
| `sec-fulltext` | SEC EDGAR | Full-text search across EDGAR filings | Direct EDGAR access when Neo4j coverage is incomplete |
| `presentations` | Slide decks | Earnings presentations / investor day slides | Visual and strategic content not in filings or transcripts |
| `gemini-live-research` | Real-time web + grounding | Gemini-powered live web search with Google Search grounding | Live mode: real-time event context, breaking news synthesis, current market narrative. Uses `agent-run` with `--provider gemini` |

Note: planned agent names are provisional — final names locked when built. Current planned families: `WEB_SEARCH`, `SEC_API_FREE_TEXT_SEARCH`, `PRESENTATIONS`, `GEMINI_LIVE_RESEARCH` (and possibly more later). Working IDs above are temporary implementation names until DataSubAgents finalizes them. The planner should not reference planned agents until they appear in the "available" table above.

**Gemini live-research rationale**: In live mode, the prediction window is minutes — Perplexity is powerful but adds 30s+ latency per deep query. Gemini with Google Search grounding provides near-instant access to breaking headlines, real-time analyst commentary, and current market narrative that may not yet be in Neo4j or Benzinga. Primary use case: live-mode Tier 1 fallback for time-sensitive context that structured sources haven't ingested yet. Not useful for historical mode (no PIT guarantee from web grounding). Implementation: thin agent wrapping `agent-run --provider gemini` via the existing multi-provider CLI.

**Excluded** (not valid for `fetch.agent`):
- `news-driver-*` — composite analysis agents for news-impact workflow, not raw data fetchers
- `guidance-extract` — internal extraction agent used by guidance-inventory skill
- `test-*` — test agents

**Tier guidance** (soft — planner decides, but these are typical priority patterns):
- **Tier 0 (primary)**: `neo4j-*` and `alphavantage-earnings` — structured, fast, reliable
- **Tier 1 (fallback)**: `yahoo-earnings`, `bz-news-api`, `perplexity-search`, `perplexity-ask`, `perplexity-sec` — broader coverage or cross-checks, slower
- **Tier 2 (last resort)**: `perplexity-research`, `perplexity-reason` — expensive, use when structured sources returned empty

**Yahoo planner usage rule (v1)**:
- `yahoo-earnings` is valid for planner use, but only for the agent's exposed PIT-safe wrapper ops: `earnings` and `upgrades`.
- Do **not** use `yahoo-earnings` as the primary source for historical consensus estimates or calendar snapshots. For historical consensus, use `alphavantage-earnings`.
- In live mode, Yahoo may still be useful as a cross-check, but the planner should treat it as supplemental rather than default.

### 2c. Predictor — DRAFT

**Purpose**: the heart of the system. Predict earnings reaction using all available context.

**Behavior** (data-flow locked; reasoning style open):
- Bundle-only reasoning over pre-fetched context (no predictor data-fetch turns).
- Extended thinking (ultrathink) required — multi-dimensional reasoning across 6+ factors benefits significantly from deep chain-of-thought. Predictor emits a single final prediction output.
- Judge component deferred (Q26; U1 self-corrects systematic bias for now).

**Allowed inputs** (both modes):
- 8-K earnings report (trigger event)
- Pre-filing consensus baseline (EPS/revenue by default; include other key reported metric consensus when relevant)
- Prior guidance (from Neo4j Guidance/GuidanceUpdate nodes, or previous 8-K outlook)
- Historical financials (prior 10-K/10-Q via XBRL)
- Prior earnings transcripts (previous quarters only)
- Pre-filing news and sector context
- Self-learning feedback from previous quarters' attribution cycles (U1) — `predictor_lessons` + `what_failed` + `why` from all prior attribution/result.json feedback sections, passed raw by orchestrator

**Mode-specific expansion**:
- Historical mode: strict PIT at filing timestamp; no post-filing artifacts.
- Live mode: no PIT ceiling; orchestrator may include additional pre-cutoff data in the bundle. Predictor still does not fetch — bundle-only.

**Forbidden inputs** (both modes):
- Return data (`daily_stock`, `hourly_stock`) — that's the outcome being predicted
- Any realized outcome label or direct derivative of realized post-filing return target

**Data access policy (locked)**:
Predictor is bundle-only. It receives the 8-K + merged context bundle + U1 feedback from the orchestrator. It does not fetch data. One job: read and reason. If the predictor identifies missing context during reasoning, it records it in `data_gaps` (prediction output). Attribution/Learner reads this → `planner_lessons` → next quarter the planner includes it. Self-correction through U1, not in-flight follow-up.

**Why bundle-only is safe**: two independent safety nets. (1) Q23 missing-data policy — when context is insufficient, predictor caps confidence or forces hold. Missing data = missed opportunity, not loss. (2) U1 self-correction — predictor flags gaps in `data_gaps`, attribution converts to `planner_lessons`, planner includes it next quarter. Converges within 1-2 quarters per company. The alternative (predictor fetches its own data) costs every prediction: sequential queries (slow), two PIT surfaces (risk), LLM over-requesting (noise). Bundle-only costs only the rare first-time gap, which the safety nets handle.

**Skill config enforcement**: `earnings-prediction/SKILL.md` must remove `Skill`, `Task`, and `filtered-data` from allowed-tools/skills. Predictor keeps `Read`, `Write`, `Glob`, `Grep`, `Bash` for file operations only. This enforces bundle-only structurally, not just by instruction.

**PIT enforcement** (historical only, not live):
- Historical: `--pit {filed_8k}` gate on all data queries. Fail-closed — if gate can't verify, query is blocked.
- Live: no PIT gate needed — future data doesn't exist yet. Orchestrator includes pre-cutoff data in bundle; cutoff timestamp must be recorded in prediction context/result metadata.

**Surprise formula**:
```
surprise_pct = ((actual - consensus) / abs(consensus)) * 100
```
Edge case: if consensus is null or zero, log as missing and use fallback scoring (Q2 failure policy). Do not divide by zero.

**Invariants** (must always hold):
1. Historical queries are PIT-filtered; live queries are bounded by recorded decision cutoff time
2. Predictor never consumes return labels (`daily_stock`, `hourly_stock`)
3. Consensus from pre-filing sources only
4. Output `signal` is deterministically derived from `direction` + `confidence_bucket` + `magnitude_bucket` — never a separate LLM judgment
5. Inter-quarter context events with forward-return windows extending past `context_cutoff_ts` have those horizons nulled (return-window validation — see `plannerStep5.md`). This prevents prev-day post_market news from leaking earnings reactions via daily/session return values.
6. Live replay must reuse the persisted `inter_quarter_context.json` artifact, NOT rebuild from Neo4j. Reason: News/Report nodes have `created`/`updated` but no ingestion timestamp — a later rebuild could include items not present in Neo4j at prediction time.

**Tiered missing-data policy** (Q2/Q19/Q23 resolved):
1. Hard fail only when 8-K actuals are missing/unreadable.
2. Directional trading calls (`lean_*`, `strong_*`) require at least one expectation anchor: `consensus` or `prior guidance`.
3. If exactly one anchor is missing, predictor may proceed, but `extreme` confidence is not allowed.
4. If both anchors are missing, force `direction=hold` and `confidence_bucket=low` (no directional trade).

**Calibration metric**: track `% predictions forced to hold+low due to missing anchors`. If high → planner defaults need improvement. If low → bundle-only design validated.

**Core dimensions (not exhaustive; priority order, all preliminary)**:

1. **Quantitative surprise** — EPS & revenue vs consensus, magnitude vs company's historical range
2. **Guidance change** — raised/maintained/lowered, delta vs prior (~60-70% of reaction)
3. **Quality of beat** — organic vs one-time, margin expansion vs cost cuts
4. **Sector context** — peer trends, headwinds/tailwinds, macro (pre-8-K)
5. **Historical pattern** — similar setups, attribution feedback from prior quarters (U1)
6. **Output** — direction/action + confidence + expected move framing

Core dimensions are the predictor's reasoning framework, not a rigid checklist. Output extensibility is handled by `key_drivers` (any number of factors, any content) and `analysis` (free-form). No separate "additional signals" structure needed (Q30 resolved).

**Prediction output contract (Q1 resolved)**:

```json
{
  "schema_version": "prediction_result.v1",
  "ticker": "NOG",
  "quarter": "Q3_FY2024",
  "filed_8k": "2024-11-07",
  "direction": "long",
  "confidence_score": 68,
  "confidence_bucket": "high",
  "expected_move_range_pct": { "min": 2.0, "max": 4.0 },
  "magnitude_bucket": "large",
  "horizon": "first_full_trading_session_close_to_close",
  "signal": "strong_long",
  "key_drivers": [
    "Beat consensus EPS by 15% — largest surprise in 8 quarters",
    "FY guidance raised, first time in 3 quarters"
  ],
  "data_gaps": ["peer_earnings", "transcript_context"],
  "analysis": "Free-form synthesis. No forced dimensions.",
  "predicted_at": "2024-11-07T14:30:00Z",
  "model_version": "claude-opus-4-6",
  "prompt_version": "prediction_result.v1"
}
```

Required fields: all fields above are required. `data_gaps` is required but can be empty (`[]`).

**Canonical `data_gaps` values (v1)**:
- `consensus`
- `prior_guidance`
- `prior_financials`
- `transcript_context`
- `peer_earnings`
- `sector_context`
- `inter_quarter_context`
- `operating_metric_consensus`

Use these exact strings where applicable. Avoid prose in `data_gaps`; free-form explanation belongs in `analysis`.

Deterministic rules (must hold):
1. `confidence_bucket` from `confidence_score`: `low 0-24`, `moderate 25-49`, `high 50-74`, `extreme 75-100`.
2. `expected_move_range_pct` is absolute unsigned move; `0 <= min <= max`; precision capped at 0.5% increments.
3. `magnitude_bucket` is derived from midpoint of `expected_move_range_pct` vs Q34 thresholds: `<2%`=`small`, `2-4%`=`moderate`, `4%+`=`large`. Symmetric (same thresholds up and down). Fixed for v1; consider per-ticker volatility-adjusted thresholds in v2.
4. `horizon` fixed to first full trading session close-to-close (Q31).
5. `signal` derived only from (`direction`, `confidence_bucket`, `magnitude_bucket`):
   - if `direction=hold` or `confidence_bucket=low` → `hold`
   - else if `confidence_bucket in {high, extreme}` and `magnitude_bucket in {moderate, large}` → `strong_long` / `strong_short`
   - else → `lean_long` / `lean_short`

**Scoring method** (Q20 resolved — rubric-guided holistic):

The predictor reasons through core dimensions naturally, then assigns `confidence_score` (0-100) as its holistic conviction level. No weighted formula — the score reflects the LLM's overall assessment after considering all evidence. Rubric anchors calibrate what each bucket means:

| Bucket | Score | Evidence pattern |
|--------|-------|-----------------|
| `low` | 0-24 | Weak or contradictory evidence. Missing key anchors. No clear directional signal. |
| `moderate` | 25-49 | Directional evidence from 1-2 dimensions, but offsetting factors or missing context. Reasonable case but not compelling. |
| `high` | 50-74 | Strong multi-dimension alignment. Both anchors available with clear surprise direction. Quality of results supports the direction. |
| `extreme` | 75-100 | Overwhelming evidence across nearly all dimensions. Large unambiguous surprise + guidance confirmation + sector tailwind. Requires both anchors present (§2c invariant). |

Why not weighted formula: (1) "core dimensions are reasoning framework, not rigid checklist" — a formula contradicts this; (2) LLM scoring individual dimensions numerically (e.g., "sector context = 72") is false precision; (3) novel situations (one-time events, unusual market conditions) need flexible weighting the LLM provides naturally; (4) U1 self-correction handles systematic bias across quarters — if the predictor consistently over-scores, `what_failed` + `predictor_lessons` will recalibrate.

The rubric is embedded in the predictor prompt, not in code. Calibration (Phase 1 historical runs) may tighten anchor descriptions based on observed score distributions.

### 2d. Attribution/Learner — DRAFT

**Purpose**: post-event analysis. Identify what drove the move. Update planner + predictor so next iteration improves.

**Behavior** (preliminary):
- Historical mode: run in same orchestrator pass when data exists.
- Live mode: deferred to next historical bootstrap (originally N=35 day timer; see `EarningsTrigger.md` for rationale).
- Extended thinking (ultrathink) required — causal analysis of multi-factor market reactions benefits from deep reasoning. No speed constraint (batch mode).
- No PIT gate — uses all available post-event data
- Job 1: identify primary driver(s) of actual move
- Job 2: distill generalized feedback for planner + predictor (next quarter)
- Guardrail: feedback must generalize, not overfit to one quarter

**Inputs** (rich post-event set):
- Everything the predictor had (8-K, consensus, guidance, historical)
- Earnings call transcript + presentations
- 10-Q/10-K for the quarter
- Actual stock price movement + settled returns
- Post-event news/analysis

**Reaction label (daily_stock)**: close-to-close return, `(end_price - start_price) / start_price * 100`, over the first full reaction session after filing.
Session-aware window: pre/in-market filings use prior close→same-day close; post-market/weekend/holiday use filing-day (or latest) close→next trading-day close.
**Auxiliary metric (hourly_stock)**: same formula over a 60-minute window; active sessions use filing_time→+60m, market_closed uses next trading day pre-market 4:00→5:00 ET.
Use `hourly_stock` as a contextual calculation for immediacy analysis/attribution; keep `daily_stock` as the primary reaction label for prediction quality and calibration.

**Self-learning loop (U1) — LOCKED**:

The core of the system's ability to improve. Each attribution writes a `feedback` section inside its `result.json`. The orchestrator reads ALL prior quarters' feedback and passes it raw to the planner and predictor. No digest, no filtering, no separate files. The LLM does the pattern recognition.

**Attribution/Learner output contract (`attribution_result.v1`)** — full schema (I6 resolved):

```json
{
  "schema_version": "attribution_result.v1",
  "ticker": "NOG",
  "quarter_label": "Q3_FY2024",
  "filed_8k": "2024-11-07T13:01:00Z",
  "attributed_at": "2026-02-08T16:00:00Z",
  "model_version": "claude-opus-4-6",
  "prompt_version": "attribution_result.v1",

  "actual_return": {
    "daily_stock_pct": -2.1,
    "hourly_stock_pct": -1.8,
    "market_session": "post_market"
  },

  "primary_driver": {
    "summary": "Guidance cut to FY25 EPS $6.00-$6.50 (prior: $6.80-$7.40) overshadowed Q3 EPS beat",
    "evidence_refs": ["8-K EX-99.1 outlook section", "Prior Q2 guidance: $6.80-$7.40 (8-K 0001234-24-000050)"]
  },

  "contributing_factors": [
    {
      "summary": "Broader energy sector weakness (XOM -1.2%, CVX -0.8% same day)",
      "evidence_refs": ["Neo4j daily returns for XOM, CVX on 2024-11-08"]
    },
    {
      "summary": "Production guidance narrowed lower (prior 98-102K, now 95-100K BOE/d)",
      "evidence_refs": ["8-K EX-99.1 operations section"]
    }
  ],

  "surprise_analysis": {
    "eps_surprise_pct": 7.56,
    "revenue_surprise_pct": 2.1,
    "guidance_surprise_pct": -8.2
  },

  "analysis_summary": "Guidance cut was the primary mover despite a strong EPS beat. The Q3 EPS of $1.85 beat consensus $1.72 by 7.6%, but the FY25 guidance cut from $6.80-$7.40 to $6.00-$6.50 (midpoint -8.2%) dominated the reaction. This aligns with NOG's historical pattern where guidance direction has been the primary driver in 3 of the last 4 quarters. Sector headwinds from same-day energy weakness (OPEC+ production announcement) amplified the negative reaction by ~0.5%.",

  "missing_inputs": ["transcript", "10-Q"],

  "feedback": {
    "prediction_comparison": {
      "predicted_signal": "strong_long",
      "predicted_direction": "long",
      "predicted_confidence_score": 68,
      "predicted_confidence_bucket": "high",
      "actual_move_pct": -2.1,
      "correct": false
    },
    "what_worked": [
      "Correctly identified EPS beat magnitude"
    ],
    "what_failed": [
      "Over-weighted EPS surprise, missed guidance cut",
      "Did not account for sector headwind from peer earnings"
    ],
    "why": "Guidance cut was the primary mover; EPS beat was noise due to one-time gain. Broader energy sector downturn (OPEC+ announcement) amplified negative reaction.",
    "predictor_lessons": [
      "Weight guidance direction higher than EPS surprise for NOG (guidance dominated in 3/4 quarters)"
    ],
    "planner_lessons": [
      "Include sector peer earnings in fetch plan (XOM/CVX headwind missed in Q3)"
    ]
  },

  "context_bundle_ref": "prediction/context_bundle.json",
  "prediction_result_ref": "prediction/result.json"
}
```

**Top-level field semantics:**

| Field | Required | Notes |
|-------|----------|-------|
| `schema_version` | Yes | Always `"attribution_result.v1"` |
| `ticker`, `quarter_label`, `filed_8k` | Yes | Event identifiers (match prediction) |
| `attributed_at` | Yes | ISO timestamp when attribution completed |
| `model_version`, `prompt_version` | Yes | Reproducibility metadata |
| `actual_return` | Yes | `daily_stock_pct` (primary label), `hourly_stock_pct` (auxiliary), `market_session` |
| `primary_driver` | Yes | Object: `summary` (1-2 sentences) + `evidence_refs` (brief source citations) |
| `contributing_factors` | Yes | Array of objects (same shape as primary_driver). Max 3. Can be `[]`. |
| `surprise_analysis` | Yes | `eps_surprise_pct`, `revenue_surprise_pct`, `guidance_surprise_pct` — all nullable (null if data unavailable, not fabricated) |
| `analysis_summary` | Yes | 1-3 paragraphs. Full reasoning narrative. Preserves nuance beyond headline fields. |
| `missing_inputs` | Yes | Array of strings. What data was unavailable at attribution time. Can be `[]`. |
| `context_bundle_ref` | Yes | Relative path to prediction's context_bundle.json (audit trail) |
| `prediction_result_ref` | Yes | Relative path to prediction/result.json (what's being compared) |

**Feedback block fields and caps (per quarter):**

| Field | Required | Max | Purpose |
|-------|----------|-----|---------|
| `prediction_comparison` | Yes | 1 object | `predicted_signal`, `predicted_direction`, `predicted_confidence_score`, `predicted_confidence_bucket`, `actual_move_pct`, `correct`. Field names aligned with predictor output contract. |
| `what_worked` | Yes | 2 items | What the predictor got right (prevents over-correction) |
| `what_failed` | Yes | 3 items | Diagnosis: where the prediction went wrong |
| `why` | Yes | 1-3 sentences | Causal context: macro events, one-time items, external factors. Helps predictor judge whether past lessons apply to current quarter |
| `predictor_lessons` | Yes | 3 items | Prescriptions for the predictor (soft priors, not hard rules) |
| `planner_lessons` | Yes | 3 items | Prescriptions for the planner (fetch priority adjustments) |

Caps enforce signal quality — force the learner to prioritize the most important observations rather than dumping everything.
Required array fields may be empty when no valid item exists; do not add filler just to hit caps.

**Canonical `missing_inputs` values (v1)**:
- `transcript`
- `10-Q`
- `10-K`
- `presentation`
- `post_event_news`
- `peer_reactions`
- `sector_context`
- `xbrl_actuals`

Use these exact strings for optional unavailable learner inputs. Hard blockers (`prediction/result.json`, `daily_stock`) should block execution rather than appear in `missing_inputs`.

Flow:
```
Q(n) attribution/result.json [with feedback]
Q(n-1) attribution/result.json [with feedback]
...all prior quarters...
        │
        ▼
Q(n+1) orchestrator reads ALL prior feedback, passes raw into context bundle
        │
    ┌───┴───┐
    ▼       ▼
 Planner  Predictor
 reads     reads
 planner_  predictor_lessons
 lessons   + what_failed + why
```

Guardrails:
1. Lessons must be generalizable principles, not quarter-specific commands. ("Weight guidance higher for NOG" not "In Q3, guidance was cut to $4.50")
2. Feedback is guidance, never hard lock. Current-quarter evidence can override any past lesson.
3. No lossy compression. Pass all raw feedback — the LLM weights repeated patterns, discounts stale info, and identifies contradictions naturally.
4. Contradictions are allowed. The model weighs evidence.

Why no digest/scoring/decay:
- 10 quarters × ~14 items each = ~140 items. Still trivial context for an LLM.
- The LLM IS the digest — it naturally weights repeated patterns and discounts stale info.
- A digest is lossy compression that could throw away useful lessons.
- `why` captures rich context (macro events, external factors) that a digest would strip.
- Per-field caps handle signal quality; no additional filtering needed.

PIT safety: reading Q(n-1)'s attribution (including actual returns) while predicting Q(n) is historical data, not lookahead. PIT-safe by definition.

**Reference files** (early versions, ~5-10% reusable, review later when relevant):
- `.claude/skills/earnings-attribution`
- `.claude/archive/skills/_old-earnings-orchestrator`
- `.claude/archive/skills/earnings-attribution-v1-monolithic`
- `.claude/archive/skills/earnings-orchestrator-v2`

**Multi-model learning (LOCKED — phased rollout after single-model calibration)**:

Why learner, not predictor:
1. No speed constraint — learner runs in batch 20-30 days later; predictor must finish in minutes.
2. Compound returns — better attribution → better feedback (U1) → better predictions across ALL future quarters. Multiplicative, not additive.
3. Richer interpretation space — learner works with qualitative data (transcript tone, management commentary, analyst reactions) where model diversity adds genuine value. Predictor inputs are more structured (beat/miss numbers).

Mechanism: Agent Teams proxy pattern (tested, bidirectional).
- Claude teammate: runs native Claude Opus learning
- OpenAI teammate: proxies to ChatGPT via `./agent --provider openai`
- Both independently attribute, then deliberate via peer-to-peer messaging
- Shared task list for coordination; each writes to separate files (last-write-wins rule)
- Lead (orchestrator) synthesizes or applies deterministic merge rule

Guardrails (keep it simple):
- Maximum one critique round, then finalize (avoid debate loops).
- If workers still disagree, emit both hypotheses + confidence and default to conservative feedback updates (no forced single-cause certainty).

Tested capabilities (from AgentTeams.md):
- `./agent --provider openai` from teammate: WORKS
- Claude-worker ↔ OpenAI-worker peer messaging: BIDIRECTIONAL, WORKS
- Shared task list claim/complete: WORKS
- Multi-turn exchange (not just one-shot): WORKS

Phase 1: single-model learning (Claude Opus). Get calibration data, measure quality.
Phase 2: add OpenAI as parallel independent learner + deliberation. Measure if feedback quality improves.

**Learning trigger (Q28 resolved, updated 2026-03-20)**:
- Historical: same-run (data exists, sequential quarters give U1 for free)
- Live: **deferred to next historical bootstrap** (originally N=35 day timer; replaced to avoid live-queue token competition — see `EarningsTrigger.md`). The daemon enqueues HISTORICAL when the ticker re-enters trade_ready; the orchestrator catches the missing attribution during sequential processing.
- No source-gating — run with whatever's available, note gaps
- Hard-fail gate: `prediction/result.json` + `daily_stock` label
- `missing_inputs` array in learner output for U1 context

Why deferred (was N=35): learner competing with live predictions on the same queue wastes urgent token budget. By deferring to the next historical bootstrap, learners run on the historical queue (batch priority) and the data is richer — 10-Q/10-K and analyst coverage are available by then. Annual quarters (10-K filed 60-90 days) are handled naturally without special exceptions.

**Failure policy (Q10+Q15 resolved)**:

Validation (Q10) — block when output can't be trusted for its purpose, continue when partial value exists:
| What fails | Action |
|---|---|
| 8-K unreadable/missing | Block — hard fail, skip quarter, log error |
| Data sub-agent returns malformed/empty | Continue with gap — predictor gets bundle with source marked missing. Q23 policy handles the rest. |
| Planner returns unparseable fetch plan | Block — can't fetch without a plan. Log error, skip quarter. |
| Predictor output missing required fields | Block — can't trade on incomplete output. No result.json written. |
| Predictor output fails deterministic rules | Block — internally inconsistent. No result.json written. |
| Attribution/Learner output missing feedback fields | Warn + write — output still provides value. `missing_inputs` makes gaps explicit. |

Crash recovery (Q15) — file-authoritative state makes this simple:
- Per-step completion: `prediction/result.json` = prediction done, `attribution/result.json` = attribution done. A quarter with prediction but no attribution is partially done — orchestrator runs the missing attribution (this is how deferred live learners are caught during the next historical bootstrap).
- Crash mid-quarter → next run re-processes from scratch (planner → fetch → predictor). Idempotent.
- `context_bundle.json` without `result.json` = partial state, safe to overwrite.
- Write result.json via temp file + atomic rename to prevent half-written files.

---

## 3. Constraints & References — LOCKED

### Platform constraints

| Capability | Status |
|-----------|--------|
| Task parallel from main | Works |
| Task in forked skill | Blocked |
| Task→Task nesting | Blocked |
| Task→Skill nesting | Works (sequential) |
| Skill calls | Sequential only |
| Agent Teams | Works (optional) |
| TaskCreate/List/Get/Update from forked skills | Works |
| Task tool (sub-agent spawn) from forked skills | Blocked |
| Agent Teams proxy (Claude ↔ OpenAI via `./agent`) | Works (bidirectional, tested) |
| filtered-data skill | Deprecated (legacy; superseded by DataSubAgents + pit_gate.py hooks) |

Source: `Infrastructure.md`, `AgentTeams.md`

### Data layer — IN PROGRESS, out of scope for this doc

How data is fetched, sources available, PIT enforcement: see `DataSubAgents.md`. Status: Phase 0-2 DONE, Phase 3 DONE (all 5 Neo4j agents PIT-complete), Phase 4 DONE (all 5 Perplexity + 1 Alpha Vantage agents PIT-complete). 13 of 13 agents fully PIT-compliant. Exhaustive testing: 60/60 passed (56 individual + 4 cross-agent) + 52/52 pit_fetch tests. pit_gate.py: 41/41 tests. This doc only defines how components integrate with that layer.

---

## 4. File Layout — DRAFT

```
earnings-analysis/Companies/{TICKER}/events/
  event.json                         ← rebuilt each run (historical discovery via get_quarterly_filings)
  live_state.json                    ← written by orchestrator in live mode after prediction completes
  {quarter_label}/
    planner/fetch_plan.json          ← persisted for debugging/auditing what data was requested vs received
    prediction/context_bundle.json   ← written once, never overwritten
    prediction/result.json           ← existence = done
    attribution/context.json
    attribution/result.json          ← contains embedded `feedback` block consumed in later-quarter planner/predictor context
```

**`live_state.json`** (live mode only): Written by the orchestrator after live prediction completes. Maps the live 8-K accession to the derived quarter_label so the external trigger daemon (`EarningsTrigger.md`) can locate result files without deriving fiscal quarter identity itself.

```json
{
    "accession_8k": "0001234-26-000123",
    "quarter_label": "Q1_FY2026",
    "filed_8k": "2026-03-18T16:30:00-05:00",
    "predicted_at": "2026-03-18T16:45:00Z",
    "accession_10q": "0001234-26-000100"  // filled if 10-Q already existed at prediction time, null if not yet filed (4.9% of cases have 10-Q before 8-K)
}
```

Not written in historical mode (historical uses `event.json` for quarter identity). Write-once per live cycle; overwritten if a new live 8-K triggers a new prediction.

**Aggregation tooling (Q8+Q9 resolved — separate from orchestrator)**:

The orchestrator's job is predict + learn. Aggregation (building cross-quarter summary views) is a separate concern, not coupled to the orchestrator workflow.

- **Source of truth**: per-quarter `result.json` files (above). These are authoritative.
- **Summary CSV**: a standalone script reads all `result.json` files across tickers/quarters → builds a flat CSV for calibration analysis. Not built by the orchestrator.
  - Script location (when built): `scripts/earnings/build_summary.py`
  - Output: `earnings-analysis/summary.csv` (single file, all tickers, all quarters)
  - Fields: `ticker|quarter|direction|confidence_score|confidence_bucket|magnitude_bucket|signal|actual_return|correct`
  - Invoke: `python3 scripts/earnings/build_summary.py` (no args = all tickers, or `--ticker NOG`)
  - Build timing: implement this early, before predictor/learner calibration work. Measurement should come before prompt iteration.
- **Automation hook (future)**: a PostToolUse or Stop hook on the orchestrator could auto-trigger `build_summary.py` after each run. Not required for v1 — run manually when needed.

**Legacy file status**:
- `earnings-analysis/predictions.csv` — **OLD DESIGN**. Created during ad-hoc prediction runs before this plan existed. Not maintained by the new orchestrator. Do not depend on it. Will be superseded by `summary.csv` when the aggregation script is built.
- `earnings-analysis/prediction_processed.csv` — **OLD DESIGN**. Same status.
- `earnings-analysis/guidance_processed.csv` — **OLD DESIGN**. Superseded by Neo4j Guidance/GuidanceUpdate nodes (written by `guidance_writer.py`).
- `earnings-analysis/news_processed.csv` — **OLD DESIGN**. Superseded by per-quarter context bundles.

---

## 5. Question Register — OPEN

One question at a time. Reprioritize after every input.

**Next question**: All Phase A interface contracts (I1-I7) resolved. Remaining deferred/non-blocking items: Q17 (P2, multi-ticker) and Q26 (deferred, judge). Next work: Phase B module plan files (see §8).

| ID | Question | Pri | Status |
|----|----------|-----|--------|
| Q1 | `result.json` schemas for prediction and attribution? | P0 | **Resolved**: Prediction schema locked in §2c (`prediction_result.v1`) with deterministic derivation rules. Attribution schema fully locked in §2d (`attribution_result.v1`) including top-level analysis fields plus `feedback` block (`prediction_comparison`, `what_worked`, `what_failed`, `why`, `predictor_lessons`, `planner_lessons`). |
| Q2 | Incomplete data — skip, predict with gaps, or error? | P0 | **Resolved**: Tiered policy. Hard fail only if 8-K actuals missing/unreadable. Otherwise predict with constraints from anchor availability (consensus/prior guidance). See §2c. |
| Q3 | Partial runs — stop/resume? | P1 | **Resolved**: No explicit stop/resume logic. File-authoritative state (Q16) + idempotent re-process (Q15) + Step 2 filter = automatic resume. Re-run orchestrator and it skips completed quarters. Scope-limiting (run N quarters, stop at X) deferred to SDK contract (Q22). |
| Q4 | DataSubAgent integration under fork constraints — invocation pattern? | P0 | **Resolved**: Two-pass hybrid. Planner returns fetch plan; orchestrator executes via parallel Tasks. See §2a, §2b. |
| Q5 | Quarter concurrency — parallel or sequential? | P0 | **Resolved**: Sequential. Attribution/Learner output from Q(n) feeds Q(n+1) prediction via self-learning loop. Parallel data fetches within each quarter. |
| Q6 | Feedback target — prompt, per-company file, or pattern library? | P0 | **Resolved**: Per-company, embedded in `attribution/result.json` feedback section. Orchestrator passes ALL prior quarters' feedback raw into planner + predictor context bundle. No separate files, no digest, no pattern library. See §2d U1. |
| Q7 | Attribution output format consumable by planner + predictor? | P0 | **Resolved**: `attribution/result.json` includes `feedback` block with `prediction_comparison`, `what_worked`, `what_failed`, `why`, `predictor_lessons`, `planner_lessons`. See §2d U1. |
| Q8 | Aggregated views for v1? | P1 | **Resolved**: Not orchestrator scope. Separate `build_summary.py` script reads all `result.json` → flat CSV. Automatable via hook later. See §4 aggregation tooling. |
| Q9 | Aggregate location + format? | P1 | **Resolved**: `earnings-analysis/summary.csv`, pipe-delimited. Built by standalone script, not orchestrator. Legacy `predictions.csv` is old design — superseded. See §4. |
| Q10 | Validation — block or warn? | P0 | **Resolved**: Tiered — block when output can't be trusted (8-K missing, unparseable plan, invalid prediction), continue with gap for data sources, warn+write for incomplete learner output. See §2d failure policy. |
| Q11 | Schema enforcement — JSON Schema or inline? | P1 | **Resolved**: Inline validation for v1. Deterministic derivation rules (score→bucket, direction+confidence→signal) are already code logic that JSON Schema cannot express. Inline checks cover: required fields present, types correct, cross-field consistency (5 deterministic rules in §2c). Extract JSON Schema later if needed for external tool sharing. |
| Q12 | Confidence representation: bucket-only or numeric+bucket? (prediction and attribution) | P0 | **Resolved**: Numeric conviction score (0-100) + bucket (`low` 0-24, `moderate` 25-49, `high` 50-74, `extreme` 75-100). Score is ranking, not probability. Bucket drives action; score enables calibration and within-bucket ranking. |
| Q13 | `guidance-inventory` wired in or gap? | P1 | **Resolved**: Decoupled. Orchestrator queries Neo4j Guidance/GuidanceUpdate nodes at bundle assembly time (§2a step 3a). Original design referenced `guidance-inventory.md` but that file does not exist — extraction pipeline writes directly to Neo4j via `guidance_writer.py`. Empty if no Guidance nodes exist. |
| Q14 | Skip historical pattern when no prior attribution? | P1 | **Resolved**: No special handling. First quarter for a ticker simply has empty U1 arrays (no `predictor_lessons`, no `planner_lessons`). Planner and predictor already handle empty feedback naturally — they reason from 8-K + available data alone. No skip logic needed. |
| Q15 | Crash mid-quarter — retry or cleanup? | P0 | **Resolved**: File-authoritative = idempotent. No result.json = not done → re-process from scratch. context_bundle.json without result.json = safe to overwrite. Atomic write (temp + rename) prevents half-written files. See §2d failure policy. |
| Q16 | State — file-based or hybrid with Claude Tasks? | P0 | **Resolved**: File-authoritative state. Claude Tasks optional as in-run mirror only; files are the durable source of truth and win on conflict. See §2a, §6. |
| Q17 | Multi-ticker — batch or single? | P2 | Open |
| Q18 | Prediction call enum — `up/down/flat` or `long/short/hold` (or both)? | P0 | **Resolved**: `long/short/hold` — trading action language, not market description. |
| Q19 | No guidance — neutral, bearish, or separate class? | P1 | **Resolved**: Missing guidance is allowed (not hard-fail). Treat as one missing expectation anchor; do not allow `extreme` confidence unless both anchors are present. If both anchors missing, force `hold`+`low`. See §2c. |
| Q20 | Scoring — weighted or qualitative rubric? | P1 | **Resolved**: Rubric-guided holistic. No weighted formula — LLM reasons through dimensions naturally, assigns confidence_score as holistic conviction. Rubric anchors per bucket prevent drift. See §2c scoring method. |
| Q21 | Reliability vs minimalism tie-break | — | Resolved: reliability wins |
| Q22 | SDK contract — exact args historical vs live? | P0 | **Resolved**: Historical = `"/earnings-orchestrator {TICKER}"` (all pending quarters). Live = `"/earnings-orchestrator {TICKER} --live --accession {accession_no}"` (single quarter). SDK requires `setting_sources=["project"]`, `permission_mode="bypassPermissions"`, `tools` preset, latest validated SDK version from `Infrastructure.md`. Live is not PIT-gated; orchestrator auto-records `decision_cutoff_ts` at prediction-start. Missing required args fail fast (no partial writes). See §2a. |
| Q23 | On-time + right-signal contract: trigger/SLA and minimum signal set? | P0 | **Resolved**: 8-K actuals are mandatory. For directional calls, require at least one expectation anchor (`consensus` or `prior guidance`); if both missing, force `hold`+`low`. Historical mode enforces PIT at filing. Live mode may use additional data before decision cutoff. See §2c, §2d. |
| Q24 | Noise policy: excluded vs required for predictor? | P0 | **Resolved**: Planner relevance principle — every fetch justified by 8-K claim, core dimension, or U1 planner_lesson. Soft guidance, not validation gate. Hard exclusions (return labels, PIT) enforced structurally. Same policy both modes. See §2b. |
| Q25 | Planner: single-turn or multi-turn? | P0 | **Resolved**: Single-turn. Reads 8-K + U1 feedback, outputs complete fetch plan. U1 planner_lessons handles gaps across quarters. See §2b. |
| Q26 | Judge component — which modules need one, what does it check? | P1 | **Deferred**: Reconsider later after additional calibration data. |
| Q27 | Task creation from forked skills — validate against Infrastructure.md | P0 | **Resolved**: TaskCreate/List/Get/Update works; Task spawn blocked. See §3. |
| Q28 | Attribution trigger policy — same run, delayed scheduled run (20-30d), or hybrid? | P0 | **Resolved**: Hybrid. Historical = same-run (data exists). Live = ~~35-day timer~~ **deferred to next historical bootstrap** (updated 2026-03-20, see `EarningsTrigger.md`). No source-gating; Attribution/Learner runs with available data, writes `missing_inputs` array. Hard-fail gate: `prediction/result.json` + `daily_stock` label. See §2a step 4, §2d. |
| Q29 | Transcript requirement by phase | — | **Resolved**: not required for prediction; useful for attribution. |
| Q30 | Dimensions model: fixed closed set or core set + extensible additional signals? | P0 | **Resolved**: Core dimensions are soft reasoning guidance. Output extensibility handled by existing fields (`key_drivers`, `analysis`). No separate structure needed. See §2c. |
| Q31 | Prediction horizon contract: fixed (e.g., 24h) or multi-horizon output? | P0 | **Resolved**: First full trading session (close-to-close, session-aware). Measured by `daily_stock_return` in DB. Max hold = session close (4 PM ET). Handles pre/in/post market + weekends. |
| Q32 | Magnitude contract for trading: quantitative expected move, qualitative buckets, or both? | P0 | **Resolved**: Both. `expected_move_range_pct: { "min": N, "max": N }` + `magnitude_bucket` (`small/moderate/large`). Bucket derived deterministically from midpoint vs Q34 thresholds (`<2%`/`2-4%`/`4%+`). Range precision: 0.5% increments max. |
| Q33 | Output contract shape: single combined 5-band signal only, or decomposed fields (`direction` + `confidence` + `magnitude` + `horizon`) with optional derived band? | P0 | **Resolved**: Hybrid — decomposed fields (direction, confidence, magnitude, horizon) + derived 5-band signal. Signal = deterministic f(fields), not separate LLM judgment. |
| Q34 | Magnitude band thresholds: what % cutoffs, symmetric or asymmetric, fixed or per-ticker? | P1 | **Resolved**: `<2%`=small, `2-4%`=moderate, `4%+`=large. Symmetric, fixed for v1. Derived from midpoint of `expected_move_range_pct`. Recalibrate from backtest data; consider per-ticker volatility-adjusted in v2. |
| Q35 | News-driver node trigger: should we run a real-time post-move workflow that creates `NewsDriver` nodes when realized return exceeds a threshold? | P1 | Open |

---

## 6. Architecture Decisions — OPEN

| # | Decision | Options | Current | Qs |
|---|----------|---------|---------|-----|
| A1 | State | File / Tasks / Hybrid | **File-authoritative** (optional in-run task mirror) | Q16 |
| A2 | Concurrency | Sequential / Parallel-quarter / Parallel-ticker | **Sequential** (locked) | Q5 |
| A3 | Learning trigger | Same run / Delayed / Hybrid | **Hybrid** (historical=same-run, live=~~35-day timer~~ **deferred to next historical bootstrap**, no source-gating) | Q28 |
| A4 | Validation | JSON Schema / Inline / Hook | **Tiered + inline** (block untrusted, continue with gaps, warn+write partial; inline code checks for cross-field deterministic rules) | Q10 Q11 |
| A5 | Aggregation | CSV / JSON / Both / Separate | **Separate tooling** (standalone script + optional hook; not orchestrator scope) | Q8 Q9 |
| A6 | Feedback loop | Prompt / Files / Library | **Embedded in attribution result.json** (all raw, no digest, no curation) | Q6 Q7 |
| A7 | Error handling | Retry / Skip+log / Manual / Tiered | **Tiered + idempotent** (block critical, continue with gaps, atomic writes, re-process on crash) | Q15 Q10 |
| A8 | SDK contract | Minimal / Rich | **Minimal** (single prompt string per mode; SDK params locked) | Q22 |
| A9 | Planner turns | Single / Multi | **Single-turn** (locked; U1 for gaps) | Q25 |
| A10 | Judge pattern | None / Per-component / Shared | **Deferred** (reconsider later) | Q26 |
| A11 | Prediction output shape | Combined band / Decomposed / Hybrid | **Hybrid** (decomposed + derived signal) | Q33 Q18 Q12 Q31 Q32 |
| A12 | Multi-model deliberation | Predictor / Attribution-Learner / Both / None | **Attribution-Learner only (locked)** (Phase 2; proxy pattern via Agent Teams) | — |
| A13 | Scoring method | Weighted formula / Qualitative rubric / Rubric-guided holistic | **Rubric-guided holistic** (no formula; LLM holistic conviction + bucket rubric anchors; U1 self-corrects) | Q20 |

---

## 7. Implementation Phases — OPEN

**Phase 0 — decisions** (before code):

1. Q21 — resolved: reliability wins (see §0)
2. Q4 + Q5 + Q16 — resolved: two-pass hybrid + sequential quarters + file-authoritative state.
3. Output contract core resolved: Q1 + Q12 + Q18 + Q31 + Q32 + Q33 (Q34 remains threshold calibration)
4. Q15 + Q10 — resolved: tiered validation + idempotent crash recovery. See §2d failure policy.
5. Q6 + Q7 — resolved: feedback embedded in attribution result.json, all raw, no digest. See §2d U1.
6. Q25 + Q23 + Q24 — resolved: single-turn planner, tiered missing-data, relevance-based noise policy. See §2b, §2c.
7. Q28 — resolved: hybrid trigger (historical=same-run, live=deferred to next historical bootstrap). See §2a, §2d.
8. Q13 — updated: guidance data from Neo4j Guidance/GuidanceUpdate nodes (original guidance-inventory.md file does not exist). See §2a.
9. Q14 — resolved: first quarter has empty U1 arrays, no special handling.
10. Q20 — resolved: rubric-guided holistic scoring. See §2c scoring method.
11. Q3 — resolved: no explicit stop/resume; file-authoritative = automatic resume.
12. Q26 — deferred: reconsider later.
13. Q11 — resolved: inline validation. Deterministic rules are code logic; JSON Schema can't express cross-field constraints.
14. R1-R5 refinements locked: extended thinking (predictor + attribution), persist fetch plan, model/prompt version metadata, background sub-agents with timeout (v2), planner sanity check.
15. Q34 resolved: magnitude thresholds `<2%`/`2-4%`/`4%+`, symmetric, fixed for v1. Per-ticker in v2.
16. Q8+Q9 resolved: aggregation = separate tooling (build_summary.py + optional hook), not orchestrator scope. Legacy CSV files marked old design. Orchestrator Step 6 (aggregation) removed.
17. Planner output contract finalized: tiered array-of-arrays `fetch` schema. Replaces ChatGPT draft (`source_chain` + `execution` field). Informed by analysis of all codebase data-fetching patterns (news-impact, news-driver, guidance-inventory, filtered-data, DataSubAgents). See §2b.

Ready-to-build = all above done + §8 interface contracts resolved (I1-I7 complete) + module plan files complete.

---

## 8. Planning Roadmap — What Remains Before Implementation

**Status**: All P0/P1 architecture decisions resolved. OUTPUT contracts locked (fetch_plan.json, prediction/result.json, attribution/result.json feedback block). What remains: lock INPUT assembly contracts, then fill module implementation details.

**Principle**: Interface-first. Lock all boundaries between modules before filling internals. This prevents rework.

### Phase A: Lock Remaining Interface Contracts (BLOCKERS)

These are boundaries between modules. Until locked, module internals can't be finalized. Resolve in master plan (this doc).

Note: Interface contracts use I-prefix (I1-I7) to avoid collision with §6 Architecture Decisions (A1-A13).

| # | Contract | Gap | Status |
|---|----------|-----|--------|
| I1 | **Context bundle format** | JSON contract + rendered text delivery. Schema, persistence, rendering rules. | **Resolved** — `context_bundle.v1` in §2a. |
| I2 | **Orchestrator → Planner input** | Planner receives subset: 8k_content + u1_feedback (planner_lessons) + guidance_history + inter_quarter_context. | **Resolved** — delivery spec in §2a. |
| I3 | **Orchestrator → Predictor input** | Predictor receives full bundle (all sections). | **Resolved** — delivery spec in §2a. |
| I4 | **Orchestrator → Learner input** | Learner does NOT get a bundle. 3 minimal inputs: prediction/result.json path, actual returns, context_bundle.json path (reference only). Fetches its own data. | **Resolved** — spec in §2a. |
| I5 | **Guidance → Orchestrator bridge** | Query Neo4j Guidance/GuidanceUpdate nodes, render as text for `guidance_history`. Empty if no nodes exist. Original design referenced `guidance-inventory.md` (file does not exist). | **Resolved** — spec in §2a. |
| I6 | **Full attribution/result.json schema** | Full `attribution_result.v1` schema: actual_return, primary_driver (with evidence_refs), contributing_factors, surprise_analysis (nullable), analysis_summary, missing_inputs, feedback block, audit refs. | **Resolved** — full schema in §2d. |
| I7 | **Planner agent catalog** | 14 valid agents across 5 domains (Neo4j 6, Alpha Vantage 1, Yahoo 1, Benzinga API 1, Perplexity 5). Tier guidance for priority patterns. Exposed Yahoo ops are PIT-safe; Yahoo consensus/calendar remain excluded from historical use. | **Resolved** — catalog in §2b. |

### Phase B: Module Implementation Details (one at a time, in order)

Each module gets its own plan file. Fill details there, not in this master doc.

**B0: Summary / Evaluation Tooling** (do early)

Build this before calibration-heavy prompt iteration so improvements can be measured immediately.

Key items to resolve:
- Implement `scripts/earnings/build_summary.py`
- Define the minimal eval view built from `prediction/result.json` + `attribution/result.json`
- Ensure summary generation is deterministic and rerunnable from files alone

**B1: Planner + Predictor** (together — tightly coupled core loop)

Plan files: `planner.md` + `predictor.md` (created).

Key items to resolve:
- Prompt templates for both modules
- Extended thinking configuration
- Planner: question taxonomy (canonical IDs or free-form?)
- Planner: 8-K content delivery (raw text? structured sections? truncation?)
- Planner: error handling (empty 8-K, malformed content)
- Planner: single-turn enforcement mechanism
- Planner: sanity check R5 — code logic or prompt instruction?
- Predictor: deterministic rule enforcement — prompt vs post-validation hook?
- Predictor: data_gaps identification (how does it know what's missing from a bundle?)
- Predictor: missing-data policy prompt implementation (how to ensure hold+low)
- Predictor: inline validation — where does checking code live?
- Skill frontmatter for both (new for planner, rewrite for predictor)

**B2: Attribution/Learner** (biggest redesign — old skill is ~10% aligned with plan)

Plan file: `learner.md` (created).

Key items to resolve:
- Full result.json schema (I6 feeds this, but also internal structure decisions)
- Prompt template and reasoning structure
- Phase 1 scope (single-model) — exactly what gets built now
- Phase 2 boundary (multi-model) — what to design now for compatibility
- Prediction comparison method (how it consumes prediction/result.json)
- Actual returns delivery format (daily_stock, hourly_stock)
- missing_inputs identification method
- Feedback cap enforcement — prompt instruction vs post-validation
- Generalizability guardrail — "no quarter-specific commands"
- Skill frontmatter (complete rewrite)
- Old attribution report migration policy (existing markdown reports)

**B3: Guidance Integration Hardening**

Plan file: `guidanceInventory.md` (exists — 18-section framework, 8 open questions G1-G8).

Key items to resolve:
- Orchestrator bridge format (I5 resolution feeds this)
- BUILD vs UPDATE trigger rule — how orchestrator determines which mode
- Resolve remaining open questions G1-G8 (see `guidanceInventory.md §17`)
- Verify sub-files exist and are current (QUERIES.md, OUTPUT_TEMPLATE.md, FISCAL_CALENDAR.md)
- Skill frontmatter review

**B4: News Driver Trigger + Node Integration**

Plan file: `newsDriver.md` (to create).

Key items to resolve:
- Trigger condition: exact return metric and threshold (`daily_stock`, `hourly_stock`, or both), plus comparison rule (`abs(return) >= threshold` vs directional thresholds).
- Trigger timing: when the check runs in live mode (intraday vs close), and when it runs in historical replay.
- Data dependency gate: required labels and inputs before running news-driver (`daily_stock`/`hourly_stock`, event metadata, ticker).
- Workflow ownership: orchestrator-initiated vs separate event-driven workflow; idempotency and retry policy.
- Node contract: canonical `NewsDriver` node schema, provenance/evidence links, and relationship model to `News`, `Company`, and quarter/event.
- Existing asset reuse: how `.claude/agents/news-driver-bz.md` is invoked in the new trigger flow, including runtime/tool constraints.
- PIT and audit semantics: live cutoff behavior, historical replay determinism, and persisted artifacts for traceability.

### Phase C: Final Consistency Pass

Do this AFTER all module details are locked. Mechanical, not architectural.

| # | Item |
|---|------|
| C1 | **Skill-sync checklist** — diff current vs required frontmatter for all skills (orchestrator, planner, predictor, learner, guidance-inventory) |
| C2 | **File layout verification** — all paths referenced across modules are consistent |
| C3 | **Implementation-ready checklist** — completion criteria, what implementing bot verifies before starting |

### Module Readiness Snapshot

| Module | Plan file | Code state | Gap |
|--------|-----------|------------|-----|
| Planner | `planner.md` (exists) | No skill exists | Small — §2b spec is 90% complete, needs prompt/frontmatter |
| Predictor | `predictor.md` (exists) | Skeleton SKILL.md, wrong output/tools | Medium — major skill rewrite |
| Attribution/Learner | `learner.md` (exists) | Old-design SKILL.md (~10% aligned) | Large — fundamental redesign |
| Guidance Inventory | `guidanceInventory.md` (exists) | Working SKILL.md + extraction agent | Small — integration spec + G1-G8 |

### Changelog

18. §8 added: planning roadmap with Phase A (interface contracts), Phase B (module details), Phase C (consistency pass). Driven by gap analysis of what's locked (outputs) vs what's missing (inputs, prompts, frontmatter).
19. I1-I6 resolved (renamed from A-prefix to I-prefix to avoid collision with §6 Architecture Decisions). `context_bundle.v1` JSON schema locked in §2a. Planner receives subset (8k + u1 + guidance). Predictor receives full bundle. Learner does NOT get a bundle — receives 3 minimal inputs (prediction result, actual returns, context_bundle ref) and fetches its own data. Guidance bridge (I5): raw markdown passthrough. Full `attribution_result.v1` schema locked in §2d (I6): primary_driver + contributing_factors with evidence_refs, nullable surprise_analysis, analysis_summary (1-3 paragraphs), prediction_comparison fields aligned with predictor output. "Ready-to-build" line updated (was stale).
20. I7 resolved: Planner agent catalog locked in §2b. 14 valid agents across 5 domains (Neo4j 6, Alpha Vantage 1, Yahoo 1, Benzinga API 1, Perplexity 5). Added `neo4j-vector-search` (semantic similarity across News + QAExchange) and later confirmed `yahoo-earnings` is planner-safe for exposed wrapper ops (`earnings`, `upgrades`). Source: DataSubAgents.md matcher table + actual `.claude/agents/*.md` files. Tier guidance included. Excluded agents listed. **All Phase A interface contracts (I1-I7) now resolved.** §5 next-question pointer updated to Phase B.

### Open Items (migrated from audit-fixes.md 2026-02-15)

- [ ] **I17**: Fill in `get_presentations_range.py` — currently a 14-line stub that returns "No presentations found". File: `scripts/earnings/get_presentations_range.py`
- [ ] **I18**: Fill in orchestrator placeholder steps (3, 5, 6, 7) in `earnings-orchestrator/SKILL.md`:
  - Step 3 (line 84): Task creation / deterministic task graph
  - Step 5 (line 114): Cross-tier polling / spawn downstream work
  - Step 6 (line 117): Validation gate
  - Step 7 (line 120): Aggregation (cumulative CSVs / indices)

---

## 9. TradeReady → Planner Integration (Future Options)

**Context**: The Trade-Ready Scanner (`TRIGGER.md`) runs 4x/day and maintains a persistent Redis list of upcoming earnings tickers with `earnings_date`, `time_of_day`, and `conference_date`. Two enhancement options below could feed richer data directly to the planner, potentially eliminating redundant fetches at prediction time.

### Option A: Pre-fetch consensus estimates into TradeReady entries

Currently the scanner captures only the earnings date/time. AV and Yahoo both provide consensus data that the planner/predictor currently fetches at game time via the `alphavantage-earnings` agent. If we pre-fetch into TradeReady, the planner could read consensus directly from Redis — zero API calls at prediction time.

**Available consensus fields (complete inventory):**

| Field | AV `EARNINGS_ESTIMATES` | Yahoo `get_calendar` | AV `EARNINGS_CALENDAR` |
|---|---|---|---|
| EPS avg | `estimatedAvg` | `Earnings Average` | `estimate` (single value) |
| EPS high | `estimatedHigh` | `Earnings High` | — |
| EPS low | `estimatedLow` | `Earnings Low` | — |
| Revenue avg | `revenueAvg` | `Revenue Average` | — |
| Revenue high | `revenueHigh` | `Revenue High` | — |
| Revenue low | `revenueLow` | `Revenue Low` | — |
| Analyst count (EPS) | `numberAnalysts` | — | — |
| Analyst count (revenue) | `revenueAnalysts` | — | — |
| Revision 7d ago | `eps_7_days_ago` | — | — |
| Revision 30d ago | `eps_30_days_ago` | — | — |
| Revision 60d ago | `eps_60_days_ago` | — | — |
| Revision 90d ago | `eps_90_days_ago` | — | — |
| YoY growth | `estimatedChangePercent` | — | — |
| Year-ago EPS | `yearAgoEPS` | — | — |

**AV `EARNINGS_ESTIMATES` is the richest source** — everything Yahoo has plus analyst counts, revision drift, and YoY growth. Yahoo is a strict subset.

**API cost strategy**: AV Estimates requires per-ticker calls. Fetch once on discovery, refresh once/day on 9 PM anchor scan only. Other 3 scans skip estimate calls. Cost: ~5-15 AV calls/day (paid quota).

**Enriched TradeReady entry would look like:**

```json
{
  "ticker": "LULU",
  "earnings_date": "2026-03-17",
  "time_of_day": "post-market",
  "conference_date": "2026-03-17T16:30:00-04:00",
  "sources": ["alphavantage", "earningscall"],
  "date_agreement": 2,
  "added_at": "2026-03-16T23:20:18-04:00",
  "updated_at": "2026-03-16T23:29:03-04:00",
  "reported_at": null,
  "consensus": {
    "eps_avg": 2.55,
    "eps_high": 2.62,
    "eps_low": 2.48,
    "revenue_avg": 9750000000,
    "revenue_high": 9900000000,
    "revenue_low": 9600000000,
    "analyst_count": 40,
    "revision_7d": 2.55,
    "revision_30d": 2.57,
    "revision_60d": 2.60,
    "revision_90d": 2.62,
    "yoy_growth_pct": 12.5,
    "year_ago_eps": 2.27,
    "fetched_at": "2026-03-16T21:00:05-04:00",
    "source": "alphavantage_estimates"
  }
}
```

**Rethink for planner/predictor design**: If consensus is pre-fetched into TradeReady, the planner may not need to request `alphavantage-earnings` agent at all for consensus data. The orchestrator could inject `consensus` from the Redis entry directly into the context bundle. This simplifies the fetch plan (one fewer agent call) and guarantees consensus is always available (no fetch failure risk). Requires revisiting `predictor.md` §4b Input 2 and the planner's default consensus question. Not a locked decision — evaluate when implementing the planner.

**PIT safety**: Scanner fetches consensus the night before earnings → naturally PIT-safe for live mode (earnings haven't been reported yet). `consensus.fetched_at` records the exact capture time for audit.

**PIT caveat for historical backtesting**: Pre-fetched consensus from the scanner is only PIT-safe for LIVE predictions (fetched before earnings drop). For HISTORICAL backtesting, the planner/predictor still needs PIT-gated consensus — i.e., "what was the street estimate at the time of the 8-K filing?" This is already handled by the `alphavantage-earnings` agent with `--pit` mode (AV revision buckets are coarsely PIT-safe). Yahoo is now more nuanced than the old design: the `yahoo-earnings` wrapper exposes PIT-safe `earnings` and conservative PIT-safe `upgrades`, but Yahoo **current-state** estimates/calendar still have no as-of-date query. AV's revision buckets (7/30/60/90d) remain the only PIT-verifiable consensus source for historical mode.

### Option B: Track `reported_at` for downstream consumers

Add `reported_at: null` to every TradeReady entry. The scanner always sets it to `null`. A separate downstream process updates it when the 8-K is detected.

**Detection methods (for the future downstream process):**

| Method | Source | Reliability |
|---|---|---|
| Neo4j 8-K check | `MATCH (r:Report {formType:'8-K'})-[:PRIMARY_FILER]->(c {ticker:$t}) WHERE r.created > $earnings_date` | **Best** — definitive |
| AV `EARNINGS` | `reportedEPS` becomes non-null after report | Good, slight delay |
| Yahoo `get_earnings_dates` | `Reported EPS` becomes non-null | Free but less reliable |

**Use case**: When `reported_at` is set, downstream can auto-trigger the earnings orchestrator (`earnings:trigger` queue push) for that ticker. This bridges the TradeReady scanner (Phase 1-2, live) to the orchestrator pipeline (Phase 3, future).

---

## 8. MCP Server Access from K8s Workers (2026-03-17)

### Problem

All SDK-spawned Claude Code instances (extraction worker, future orchestrator/planner/learner/predictor workers) use `ClaudeAgentOptions.mcp_servers` which **overrides** the project `.mcp.json` entirely. Only servers explicitly listed in the `mcp_servers` dict are available — the stdio entries in `.mcp.json` are ignored.

The extraction worker currently only lists `neo4j-cypher`. Any future worker that follows the same SDK pattern will face the same limitation.

### Available In-Cluster MCP Servers

| Server | K8s Service | In-Cluster URL | What it provides |
|--------|-------------|----------------|------------------|
| Neo4j Cypher | `mcp-neo4j-cypher-http.mcp-services` | `http://mcp-neo4j-cypher-http.mcp-services.svc.cluster.local:8000/mcp` | Graph reads/writes (Cypher) |
| Yahoo Finance | `mcp-yahoo-finance.mcp-services` | `http://mcp-yahoo-finance.mcp-services.svc.cluster.local:8000/mcp` | 20 tools: quotes, estimates, financials, options, news, SEC filings (live, no API key) |

All require `{"Host": "localhost:8000"}` header (StreamableHTTP routing).

### What Each Module Needs

| Module | Neo4j | Yahoo Finance | Notes |
|--------|-------|---------------|-------|
| `/extract` (extraction worker) | **Yes** (reads graph, writes via scripts) | No | Extraction is graph-in, graph-out. No live market data needed. |
| Planner | **Yes** (reads 8-K, guidance history) | Maybe | Planner reads graph context. Yahoo is valid as a supplemental data agent for earnings history and upgrades; use AV, not Yahoo, for historical consensus. |
| Predictor | No (bundle-only, doesn't fetch) | No | Receives pre-assembled context bundle. No direct data access. |
| Learner/Attribution | **Yes** (reads realized returns, transcripts) | **Yes** | Post-event analysis benefits from live analyst targets, recommendations, earnings history, institutional holder changes. |
| Orchestrator | **Yes** (status tracking, discovery) | Maybe | Step 3b data fetch fan-out may use Yahoo as a data source via sub-agents. |

### How to Wire It

Each worker's SDK call needs its own `mcp_servers` dict. Pattern from extraction worker (`scripts/extraction_worker.py:299-305`):

```python
options = ClaudeAgentOptions(
    ...
    mcp_servers={
        "neo4j-cypher": {
            "type": "http",
            "url": os.environ.get("MCP_NEO4J_URL",
                "http://mcp-neo4j-cypher-http.mcp-services.svc.cluster.local:8000/mcp"),
            "headers": {"Host": "localhost:8000"},
        },
        "yahoo-finance": {
            "type": "http",
            "url": os.environ.get("MCP_YAHOO_URL",
                "http://mcp-yahoo-finance.mcp-services.svc.cluster.local:8000/mcp"),
            "headers": {"Host": "localhost:8000"},
        },
    },
)
```

**Options for centralizing** (decide at implementation time):

- **Option A: Shared config module** — `scripts/mcp_k8s_config.py` exports `MCP_SERVERS` dict. Each worker imports it. One edit to add a new server → all workers get it. Trade-off: all workers get all servers (harmless — deferred tools only load schemas on invocation, zero overhead if unused).
- **Option B: Per-worker config** — each worker explicitly lists only the MCP servers it needs. More control, more places to edit.
- **Option C: Hybrid** — shared config module with per-worker filtering: `mcp_servers={k: v for k, v in MCP_SERVERS.items() if k in needed}`.

**Recommendation**: Option A for simplicity unless a worker has a specific reason to exclude a server. The extraction worker doesn't need Yahoo but there's no harm in it being available.

### PIT Constraint (Critical)

Yahoo Finance is split into two classes of behavior:

- `yahoo-earnings` wrapper ops `earnings` and `upgrades` are PIT-safe for historical use. `earnings` uses `Earnings Date <= PIT` and excludes upcoming rows; `upgrades` uses a conservative date-only filter that excludes the PIT day.
- Yahoo current-state estimates/calendar tools remain non-PIT for historical use because they do not provide an as-of-date query.

This means:

- **Live mode**: Yahoo data is PIT-safe by definition (future data doesn't exist yet). Safe for planner, predictor, learner.
- **Historical backtesting**: Yahoo wrapper ops `earnings` and `upgrades` are safe. Yahoo current-state estimates/calendar are **NOT** PIT-safe. Alpha Vantage revision buckets (7/30/60/90d) remain the only PIT-verifiable consensus source for historical mode.
- **Learner**: Always post-event, so PIT is not a constraint. Yahoo is fully safe here.

Any worker using Yahoo Finance in historical mode must either (a) use only the PIT-safe wrapper ops (`earnings`, `upgrades`), or (b) gate current-state Yahoo tools behind `mode == "live"`.

### K8s Deployment Status

Yahoo Finance MCP server deployed 2026-03-17:
- Pod: `mcp-yahoo-finance` in `mcp-services` namespace, `minisforum` node
- Resources: 100m/256Mi → 250m/512Mi (matches neo4j-cypher-http)
- Health: TCP liveness/readiness probes on port 8000
- Server: `mcp_servers/yahoo_finance_server.py` — single-file FastMCP, 20 tools, yfinance 1.2.0
- Manifest: `k8s/mcp-services/mcp-yahoo-finance-deployment.yaml`

---

*Refs: `DataSubAgents.md` · `Infrastructure.md` · `AgentTeams.md` · `guidanceInventory.md` · `TRIGGER.md`*
