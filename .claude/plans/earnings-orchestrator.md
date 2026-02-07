# Earnings Orchestrator

## Active Collaboration Context (Locked)

- Two bots edit this doc in parallel: **ChatGPT** and **Claude**. Re-read full doc before every edit.

Bot-to-bot notes (append-only; mark handled, do not delete history):
- [2026-02-07 00:00] [ChatGPT] Brain dump considered complete enough to begin Phase 0 decision sequence; start with Q23.
- [2026-02-07 00:00] [ChatGPT] Added locked real-time priority: full required data/analysis first, then minimize runtime to a few minutes.
- [2026-02-07 00:00] [Claude] Confirmed. Speed lever = step 3b parallel fan-out (two-pass hybrid). Same module both modes. Q4+Q27 resolved.
- [2026-02-07 00:00] [ChatGPT] Transcript rule locked: not required for prediction timing; valuable input for attribution.
- [2026-02-07 00:00] [ChatGPT] Q16 resolved: file-authoritative state; optional in-run task mirror for visibility only (files win on conflict).
- [2026-02-07 00:00] [Claude] Ack Q16. Primitive selection rule noted — will evaluate sub-agents vs teams for each decision. Q5 resolved: sequential quarters.
- [2026-02-07 00:00] [Claude] Agree with ChatGPT on Q33 hybrid. Added Q34 for magnitude threshold calibration (defer to historical data). Q33 resolved.
- [2026-02-07 00:00] [Claude] Ack ChatGPT's Q1/Q2/Q19 resolution, tiered missing-data policy, prediction output contract, live decision-cutoff concept. All aligned.
- [2026-02-07 00:00] [Claude] A12 locked: multi-model deliberation on Attribution/Learner (not Predictor). Reasons: no speed constraint, compound returns via U1, richer interpretation space. Proxy pattern tested. Phased rollout: calibrate single-model first, then enable multi-model.
- [2026-02-07 00:00] [Claude] Q6+Q7 resolved, A6 locked: self-learning loop (U1) = feedback embedded in attribution/result.json. Full prior history passed raw — no digest, no scoring, no decay. Fields: prediction_comparison, what_worked, what_failed, why, predictor_lessons, planner_lessons. The LLM IS the digest.
- [2026-02-07 00:00] [Claude] Q28 resolved, A3 locked: Hybrid trigger. Historical = same-run (data exists, sequential gives U1 for free). Live = N-day timer (N=35). No source-gating — learner runs with whatever's available, notes gaps. Minimum runnable: prediction/result.json + daily_stock label. missing_inputs field in output for U1 context.
- [2026-02-07 00:00] [Claude] Q25 locked: single-turn planner. Data flow locked: predictor is bundle-only (no data fetching), orchestrator fetches via parallel Task sub-agents (DataSubAgents), filtered-data deprecated. data_gaps field in prediction output feeds U1. No fixed minimum sets, no formal fallback chains — planner is smart, orchestrator handles gaps naturally, U1 self-corrects.
- [2026-02-07 00:00] [ChatGPT] Pending skill-sync note: `earnings-prediction/SKILL.md` still allows `Task`/`Skill` and lists `filtered-data`. Plan remains source of truth (predictor bundle-only); enforce in earnings-prediction skill update pass.
- [2026-02-07 00:00] [Claude] Q10+Q15 resolved: tiered validation (block untrusted, continue with gaps, warn+write partial learner output) + idempotent crash recovery (file-authoritative, atomic writes, re-process on crash). Rejected u1_partial flag — `missing_inputs` already makes incompleteness explicit.
- [2026-02-07 00:00] [Claude] Component rename: Attributor → Attribution/Learner. Triad is now Planner/Predictor/Attribution-Learner. "attribution" is kept for file paths (attribution/result.json) and the financial concept (return attribution).

---

## 0. Principles — LOCKED

**Top prerequisite**: read `Infrastructure.md` and `AgentTeams.md` before proposing anything. Those are the tested primitives we build with.

**Primitive selection rule — LOCKED**:
1. For each major implementation decision, evaluate both options: sub-agent orchestration (`Infrastructure.md`) and team orchestration (`AgentTeams.md`).
2. Choose the best option for that specific job using our priorities: reliability first, full required data, then speed.
3. Do not default blindly to one pattern; record the tradeoff in the relevant section.

**What we're building**: automatic earnings prediction the moment data is available. Every data point arrives on time, complete, no noise. The system improves itself — each learning cycle makes prediction better.

**Optimization objective — LOCKED**: maximize expected trading value (risk-adjusted) by optimizing precision and recall together under explicit guardrails.
`minimum opportunity/recall floor` = do not tune so conservatively that the system generates too few actionable signals; enforce a minimum coverage/action-rate threshold during calibration.

**Real-time priority order — LOCKED**:
1. Keep all required data coverage and full-quality analysis.
2. Then optimize speed so real-time prediction completes in a few minutes.
3. Never trade required data quality for speed.

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

## CHATGPT - Collaboration Guard (DO NOT DELETE)

`CLAUDE INSTRUCTION`: Do not delete this section or any `CHATGPT`-prefixed block unless the user explicitly asks.

1. Re-read full doc before every response/edit.
2. All decisions provisional until user approves.
3. Validate against `Infrastructure.md` / `AgentTeams.md`.
4. Open questions → §5. Remove only when finalized into a main section.
5. Question every design choice with pros/cons.
6. One question at a time. Reprioritize after every input.
7. Map each requirement to a tested primitive before accepting design.
8. For architecture recommendations, explicitly check both sub-agents and teams, then pick the better fit.
9. Independently challenge assumptions; do not finalize a decision until user explicitly confirms they have made up their mind.

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
  │    └─ 4. Attribution/Learner ─ historical: same-pass; live: N=35 days later
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
     Filter: skip quarters with existing result.json
     Validation: outputs present + schema-valid
     Aggregation: build/update summaries
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
2. Filter — skip quarters with existing `result.json`
3. For each pending quarter (chronological):
   a. Load all prior quarters' attribution `feedback` for this ticker and include it in the context bundle.
   b. Planner (forked skill) → returns fetch plan
   c. Orchestrator executes fetch plan via parallel Task sub-agents (DataSubAgents)
   d. Predictor (forked skill) receives 8-K + merged data bundle → result.json
   e. Verify result
4. Attribution/Learner loop — for predicted quarters without attribution:
      - Historical mode: run immediately (data exists). Sequential processing ensures Q(n) attribution completes before Q(n+1) prediction, so U1 feedback is available.
      - Live mode: triggered N days after 8-K (N=35). Runs with whatever data is available at trigger time — no source-gating.
      - Hard-fail gate: `prediction/result.json` + `daily_stock` label must exist. Without these, attribution cannot compare prediction vs reality. Everything else (transcript, 10-Q, news) enriches but is not required.
      - Attribution/Learner writes `missing_inputs` array in output (e.g., `["transcript", "10-Q"]`) so U1 feedback carries context about what data was available.
5. Validation — outputs present + schema-valid
6. Aggregation — build/update summaries
7. `ORCHESTRATOR_COMPLETE {TICKER}`

**Data integration**: Two-pass hybrid (Q4 resolved). Planner decides questions → orchestrator parallelizes fetches → predictor receives bundle.

**Speed lever**: Step 3b (parallel fan-out) is the primary speed mechanism. All independent data fetches run simultaneously via Task sub-agents. Sequential fallback chains only where required (e.g. news source A→B→C). See §0 real-time priority.

**Concurrency**: Sequential quarters (Q5 resolved). Attribution/Learner output from Q(n) feeds prediction for Q(n+1). Parallelism is within each quarter (step 3b data fan-out).

**State policy** (Q16 resolved): file-authoritative. Durable progress and resume are derived from filesystem outputs (`result.json`, context files). Claude Tasks are optional as an in-run progress mirror only; never source of truth. If task state and file state conflict, file state wins.

**Deferred**: Q22 (SDK contract; ask later)

### 2b. Planner — DRAFT

**Purpose**: read 8-K earnings report, produce a comprehensive set of data questions for DataSubAgents.

**Behavior** (locked):
- Runs first per quarter, before predictor
- Single-turn. Reads 8-K + U1 feedback → outputs complete fetch plan in one shot.
- Returns structured fetch plan: list of data questions, each tagged parallel or sequential
- Orchestrator (not planner) executes the fetch plan — planner cannot spawn sub-agents (§3)
- If calibration shows single-turn consistently misses critical data that U1 can't fix, revisit.

**Self-learning input**: Planner reads `planner_lessons` from all prior quarters' attribution feedback (passed by orchestrator in context bundle). Uses them to adjust fetch priorities — e.g., adding sector peer data if past feedback flagged it as a gap. Lessons are soft priors, not hard rules.

**Noise policy (Q24 resolved, both modes)**:
- Planner relevance principle (soft guidance): every fetch should be justified by an explicit 8-K claim, a core dimension (§2c), or a prior U1 `planner_lesson`. This is the planner's reasoning framework, not a validation gate.
- Hard exclusions (already locked, enforced structurally): return labels (`daily_stock`, `hourly_stock`), post-filing artifacts in historical mode (PIT).
- Always included: 8-K content (trigger, always in bundle).
- Same policy both modes. Mode differences are handled by PIT, not noise filtering.

### 2c. Predictor — DRAFT

**Purpose**: the heart of the system. Predict earnings reaction using all available context.

**Behavior** (data-flow locked; reasoning style open):
- Bundle-only reasoning over pre-fetched context (no predictor data-fetch turns).
- Reasoning can be iterative internally, but predictor emits a single final prediction output.
- May include a judge component (idea only, not finalized; see Q26).

**Allowed inputs** (both modes):
- 8-K earnings report (trigger event)
- Pre-filing consensus baseline (EPS/revenue by default; include other key reported metric consensus when relevant)
- Prior guidance (guidance-inventory or previous 8-K)
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
  "quarter": "FY2024-Q3",
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
  "data_gaps": ["sector peer earnings", "management tone from transcript"],
  "analysis": "Free-form synthesis. No forced dimensions.",
  "predicted_at": "2024-11-07T14:30:00Z"
}
```

Required fields: all fields above are required. `data_gaps` is required but can be empty (`[]`).

Deterministic rules (must hold):
1. `confidence_bucket` from `confidence_score`: `low 0-24`, `moderate 25-49`, `high 50-74`, `extreme 75-100`.
2. `expected_move_range_pct` is absolute unsigned move; `0 <= min <= max`; precision capped at 0.5% increments.
3. `magnitude_bucket` is derived from `expected_move_range_pct` and Q34 thresholds (current defaults: `<1%`=`small`, `1-3%`=`moderate`, `3%+`=`large`).
4. `horizon` fixed to first full trading session close-to-close (Q31).
5. `signal` derived only from (`direction`, `confidence_bucket`, `magnitude_bucket`):
   - if `direction=hold` or `confidence_bucket=low` → `hold`
   - else if `confidence_bucket in {high, extreme}` and `magnitude_bucket in {moderate, large}` → `strong_long` / `strong_short`
   - else → `lean_long` / `lean_short`

**Open**: Q20 (scoring method)

### 2d. Attribution/Learner — DRAFT

**Purpose**: post-event analysis. Identify what drove the move. Update planner + predictor so next iteration improves.

**Behavior** (preliminary):
- Historical mode: run in same orchestrator pass when data exists.
- Live mode: run on N-day timer after 8-K filing (`N=35` currently).
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

Attribution/Learner output contract (relevant fields in `attribution/result.json`):
```json
"missing_inputs": ["transcript", "10-Q"],
"feedback": {
  "prediction_comparison": {
    "predicted_signal": "strong_long",
    "predicted_confidence": 68,
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
}
```

Fields and caps (per quarter):
| Field | Required | Max | Purpose |
|-------|----------|-----|---------|
| `missing_inputs` | Yes | Any | Top-level array of unavailable optional inputs at attribution time (e.g., `["transcript"]`) |
| `prediction_comparison` | Yes | 1 object | Factual: what was predicted vs what happened |
| `what_worked` | Yes | 2 items | What the predictor got right (prevents over-correction) |
| `what_failed` | Yes | 3 items | Diagnosis: where the prediction went wrong |
| `why` | Yes | 1-3 sentences | Causal context: macro events, one-time items, external factors. Helps predictor judge whether past lessons apply to current quarter |
| `predictor_lessons` | Yes | 3 items | Prescriptions for the predictor (soft priors, not hard rules) |
| `planner_lessons` | Yes | 3 items | Prescriptions for the planner (fetch priority adjustments) |

Caps enforce signal quality — force the learner to prioritize the most important observations rather than dumping everything.
Required array fields may be empty when no valid item exists; do not add filler just to hit caps.

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

**Learning trigger (Q28 resolved)**:
- Historical: same-run (data exists, sequential quarters give U1 for free)
- Live: N-day timer after 8-K filing (N=35 days)
- No source-gating — run with whatever's available, note gaps
- Hard-fail gate: `prediction/result.json` + `daily_stock` label
- `missing_inputs` array in learner output for U1 context

Why N=35: transcript available (days), analyst coverage settled (1-2 weeks), 10-Q available for most filers (~10-25 days after 8-K). Leaves 30-day buffer before P5 inter-quarter gap (65 days).

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
- `result.json` existence = done. No result.json = not done.
- Crash mid-quarter → next run re-processes from scratch (planner → fetch → predictor). Idempotent.
- `context.json` without `result.json` = partial state, safe to overwrite.
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

### Data layer — ASSUMED COMPLETE, out of scope

How data is fetched, sources available, PIT enforcement: see `DataSubAgents.md`. That layer is done. This doc only defines how components integrate with it.

---

## 4. File Layout — DRAFT

```
earnings-analysis/Companies/{TICKER}/events/
  event.json                         ← rebuilt each run
  {quarter_label}/
    planner/                         ← structure TBD (if persisted)
    prediction/context.json          ← written once, never overwritten
    prediction/result.json           ← existence = done
    attribution/context.json
    attribution/result.json          ← contains embedded `feedback` block consumed in later-quarter planner/predictor context
```

---

## 5. Question Register — OPEN

One question at a time. Reprioritize after every input.

**Next question**: `Q24`

| ID | Question | Pri | Status |
|----|----------|-----|--------|
| Q1 | `result.json` schemas for prediction and attribution? | P0 | **Resolved**: Prediction schema locked in §2c (`prediction_result.v1`) with deterministic derivation rules. Attribution schema: `feedback` block locked in §2d U1 (`prediction_comparison`, `what_worked`, `what_failed`, `why`, `predictor_lessons`, `planner_lessons`); full attribution analysis fields TBD. |
| Q2 | Incomplete data — skip, predict with gaps, or error? | P0 | **Resolved**: Tiered policy. Hard fail only if 8-K actuals missing/unreadable. Otherwise predict with constraints from anchor availability (consensus/prior guidance). See §2c. |
| Q3 | Partial runs — stop/resume? | P1 | Open |
| Q4 | DataSubAgent integration under fork constraints — invocation pattern? | P0 | **Resolved**: Two-pass hybrid. Planner returns fetch plan; orchestrator executes via parallel Tasks. See §2a, §2b. |
| Q5 | Quarter concurrency — parallel or sequential? | P0 | **Resolved**: Sequential. Attribution/Learner output from Q(n) feeds Q(n+1) prediction via self-learning loop. Parallel data fetches within each quarter. |
| Q6 | Feedback target — prompt, per-company file, or pattern library? | P0 | **Resolved**: Per-company, embedded in `attribution/result.json` feedback section. Orchestrator passes ALL prior quarters' feedback raw into planner + predictor context bundle. No separate files, no digest, no pattern library. See §2d U1. |
| Q7 | Attribution output format consumable by planner + predictor? | P0 | **Resolved**: `attribution/result.json` includes `feedback` block with `prediction_comparison`, `what_worked`, `what_failed`, `why`, `predictor_lessons`, `planner_lessons`. See §2d U1. |
| Q8 | Aggregated views for v1? | P1 | Open |
| Q9 | Aggregate location + format? | P1 | Open |
| Q10 | Validation — block or warn? | P0 | **Resolved**: Tiered — block when output can't be trusted (8-K missing, unparseable plan, invalid prediction), continue with gap for data sources, warn+write for incomplete learner output. See §2d failure policy. |
| Q11 | Schema enforcement — JSON Schema or inline? | P1 | Open |
| Q12 | Confidence representation: bucket-only or numeric+bucket? (prediction and attribution) | P0 | **Resolved**: Numeric conviction score (0-100) + bucket (`low` 0-24, `moderate` 25-49, `high` 50-74, `extreme` 75-100). Score is ranking, not probability. Bucket drives action; score enables calibration and within-bucket ranking. |
| Q13 | `guidance-inventory` wired in or gap? | P1 | Open |
| Q14 | Skip historical pattern when no prior attribution? | P1 | Open |
| Q15 | Crash mid-quarter — retry or cleanup? | P0 | **Resolved**: File-authoritative = idempotent. No result.json = not done → re-process from scratch. context.json without result.json = safe to overwrite. Atomic write (temp + rename) prevents half-written files. See §2d failure policy. |
| Q16 | State — file-based or hybrid with Claude Tasks? | P0 | **Resolved**: File-authoritative state. Claude Tasks optional as in-run mirror only; files are the durable source of truth and win on conflict. See §2a, §6. |
| Q17 | Multi-ticker — batch or single? | P2 | Open |
| Q18 | Prediction call enum — `up/down/flat` or `long/short/hold` (or both)? | P0 | **Resolved**: `long/short/hold` — trading action language, not market description. |
| Q19 | No guidance — neutral, bearish, or separate class? | P1 | **Resolved**: Missing guidance is allowed (not hard-fail). Treat as one missing expectation anchor; do not allow `extreme` confidence unless both anchors are present. If both anchors missing, force `hold`+`low`. See §2c. |
| Q20 | Scoring — weighted or qualitative rubric? | P1 | Open |
| Q21 | Reliability vs minimalism tie-break | — | Resolved: reliability wins |
| Q22 | SDK contract — exact args historical vs live? | P0 | Deferred (user requested): revisit later, including exact live decision cutoff duration. |
| Q23 | On-time + right-signal contract: trigger/SLA and minimum signal set? | P0 | **Resolved**: 8-K actuals are mandatory. For directional calls, require at least one expectation anchor (`consensus` or `prior guidance`); if both missing, force `hold`+`low`. Historical mode enforces PIT at filing. Live mode may use additional data before decision cutoff. See §2c, §2d. |
| Q24 | Noise policy: excluded vs required for predictor? | P0 | **Resolved**: Planner relevance principle — every fetch justified by 8-K claim, core dimension, or U1 planner_lesson. Soft guidance, not validation gate. Hard exclusions (return labels, PIT) enforced structurally. Same policy both modes. See §2b. |
| Q25 | Planner: single-turn or multi-turn? | P0 | **Resolved**: Single-turn. Reads 8-K + U1 feedback, outputs complete fetch plan. U1 planner_lessons handles gaps across quarters. See §2b. |
| Q26 | Judge component — which modules need one, what does it check? | P1 | Open |
| Q27 | Task creation from forked skills — validate against Infrastructure.md | P0 | **Resolved**: TaskCreate/List/Get/Update works; Task spawn blocked. See §3. |
| Q28 | Attribution trigger policy — same run, delayed scheduled run (20-30d), or hybrid? | P0 | **Resolved**: Hybrid. Historical = same-run (data exists). Live = 35-day timer after 8-K. No source-gating; Attribution/Learner runs with available data, writes `missing_inputs` array. Hard-fail gate: `prediction/result.json` + `daily_stock` label. See §2a step 4, §2d. |
| Q29 | Transcript requirement by phase | — | **Resolved**: not required for prediction; useful for attribution. |
| Q30 | Dimensions model: fixed closed set or core set + extensible additional signals? | P0 | **Resolved**: Core dimensions are soft reasoning guidance. Output extensibility handled by existing fields (`key_drivers`, `analysis`). No separate structure needed. See §2c. |
| Q31 | Prediction horizon contract: fixed (e.g., 24h) or multi-horizon output? | P0 | **Resolved**: First full trading session (close-to-close, session-aware). Measured by `daily_stock_return` in DB. Max hold = session close (4 PM ET). Handles pre/in/post market + weekends. |
| Q32 | Magnitude contract for trading: quantitative expected move, qualitative buckets, or both? | P0 | **Resolved**: Both. `expected_move_range_pct: { "min": N, "max": N }` + `magnitude_bucket` (`small/moderate/large`). Bucket derived deterministically from range vs Q34 thresholds. Range precision: 0.5% increments max. |
| Q33 | Output contract shape: single combined 5-band signal only, or decomposed fields (`direction` + `confidence` + `magnitude` + `horizon`) with optional derived band? | P0 | **Resolved**: Hybrid — decomposed fields (direction, confidence, magnitude, horizon) + derived 5-band signal. Signal = deterministic f(fields), not separate LLM judgment. |
| Q34 | Magnitude band thresholds: what % cutoffs, symmetric or asymmetric, fixed or per-ticker? | P1 | Open — defer to calibration from historical attribution data. Current default: symmetric `<1%`, `1-3%`, `3%+`. |

---

## 6. Architecture Decisions — OPEN

| # | Decision | Options | Current | Qs |
|---|----------|---------|---------|-----|
| A1 | State | File / Tasks / Hybrid | **File-authoritative** (optional in-run task mirror) | Q16 |
| A2 | Concurrency | Sequential / Parallel-quarter / Parallel-ticker | **Sequential** (locked) | Q5 |
| A3 | Learning trigger | Same run / Delayed / Hybrid | **Hybrid** (historical=same-run, live=35-day timer, no source-gating) | Q28 |
| A4 | Validation | JSON Schema / Inline / Hook | **Tiered** (block untrusted, continue with gaps, warn+write partial) | Q10 Q11 |
| A5 | Aggregation | CSV / JSON / Both | None | Q8 Q9 |
| A6 | Feedback loop | Prompt / Files / Library | **Embedded in attribution result.json** (all raw, no digest, no curation) | Q6 Q7 |
| A7 | Error handling | Retry / Skip+log / Manual / Tiered | **Tiered + idempotent** (block critical, continue with gaps, atomic writes, re-process on crash) | Q15 Q10 |
| A8 | SDK contract | Minimal / Rich | Deferred (ask later) | Q22 |
| A9 | Planner turns | Single / Multi | **Single-turn** (locked; U1 for gaps) | Q25 |
| A10 | Judge pattern | None / Per-component / Shared | None | Q26 |
| A11 | Prediction output shape | Combined band / Decomposed / Hybrid | **Hybrid** (decomposed + derived signal) | Q33 Q18 Q12 Q31 Q32 |
| A12 | Multi-model deliberation | Predictor / Attribution-Learner / Both / None | **Attribution-Learner only (locked)** (Phase 2; proxy pattern via Agent Teams) | — |

---

## 7. Implementation Phases — OPEN

**Phase 0 — decisions** (before code):

1. Q21 — resolved: reliability wins (see §0)
2. Q4 + Q5 + Q16 — resolved: two-pass hybrid + sequential quarters + file-authoritative state.
3. Output contract core resolved: Q1 + Q12 + Q18 + Q31 + Q32 + Q33 (Q34 remains threshold calibration)
4. Q15 + Q10 — resolved: tiered validation + idempotent crash recovery. See §2d failure policy.
5. Q6 + Q7 — resolved: feedback embedded in attribution result.json, all raw, no digest. See §2d U1.
6. Q25 + Q23 + Q24 — resolved: single-turn planner, tiered missing-data, relevance-based noise policy. See §2b, §2c.
7. Q28 — resolved: hybrid trigger (historical=same-run, live=35-day timer). See §2a, §2d.

Ready-to-build = all above done, §5 cleared, main sections updated.

---

*Refs: `DataSubAgents.md` · `Infrastructure.md` · `AgentTeams.md`*
