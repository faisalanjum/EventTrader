# Predictor v2 — Requirements & Design Rules

**Created**: 2026-03-31
**Status**: REQUIREMENTS LOCKED — ready for implementation
**Supersedes**: `predictor.md` (architecture only — good ideas carried forward)
**Parent**: `prediction-system-v2.md` (system-level architecture)

---

## 0. What This Document Is

Requirements, boundaries, and rules for the predictor. Build the simplest version first, iterate from real feedback.

---

## 1. Role Definition

Single-turn reasoning engine (with one optional follow-up round). Receives pre-assembled data bundle → thinks deeply → outputs structured JSON.

**What it is NOT**: data fetcher, orchestrator, research agent, interactive.

---

## 2. Hard Constraints (non-negotiable)

| # | Constraint | Rationale |
|---|-----------|-----------|
| H1 | **Bundle-only input** — predictor sees only what the orchestrator passes | PIT compliance, reproducibility |
| H2 | **No return data** — never sees daily_stock, hourly_stock, session_stock | Lookahead bias |
| H3 | **SDK-invocable, non-interactive** — works via SDK + skill fork | Production automation |
| H4 | **Deterministic signal derivation** — Python computes signal from (direction, confidence, magnitude) | Consistency |
| H5 | **Max 2 turns** — Turn 2 only if Turn 1 outputs questions. No Turn 3 | Bounds latency |
| H6 | **Max 3 questions** per round | Tight scope |
| H7 | **Turn 2 MUST predict** — no more questions | Guarantees termination |
| H8 | **Ultrathink always on** | Deep reasoning is the value-add |
| H9 | **Every numeric claim must cite source** — builder name + field | Prevents hallucinated numbers |
| H10 | **Honest confidence over false precision** — `no_call` at 25% > fabricated 70% | Trading needs calibrated signals |

---

## 3. Design Decisions

### D1: Feed all packets at once

Single SDK call. 7 packets = ~10-20K tokens in 1M window. Cross-referencing between packets is essential. Ultrathink provides reasoning depth. Multiple calls would add ~4 min latency for zero benefit.

### D2: Evidence Ledger (from attribution)

Every numeric claim grounded in builder packet + field path. Structured JSON field in output (`evidence_ledger` array). Machine-auditable.

### D3: 3-phase reasoning (not free-form)

Forced structure prevents anchoring on the first signal (usually EPS beat/miss):
1. **Extract anchors** — inventory + evidence ledger + surprise calculations
2. **Resolve tensions** — cross-reference, identify competing narratives, rank drivers
3. **Decide** — direction, confidence, magnitude, gaps, or questions

### D4: Follow-up questions via orchestrator

Predictor outputs structured questions → Python orchestrator fetches via data sub-agents → re-invokes predictor for Turn 2. Predictor never has tool access directly. PIT enforced by orchestrator.

### D5: v1 uses 7 built packets, v2 adds 2 more (9 total)

Items #8 (previous_earnings) and #9 (previous_earnings_lessons) are NOT BUILT YET. Don't build them before proving the predictor works. Add after learner exists and produces attribution data. First historical prediction for any company will have neither. **Target: 9 packets total. Do not forget.**

### D6: No pre-analysis, no planner, no analyst notes

Deleted. The predictor with ultrathink IS the analysis engine.

### D7: `no_call` is a first-class direction

Not a confidence backdoor. When evidence genuinely doesn't support a directional view, direction = `no_call`. Different from "I think long but with low confidence."

### D8: No fake per-driver impact ranges

LLM can rank drivers and assign direction. It CANNOT honestly decompose "how many percent does this driver contribute." Keep overall `expected_move_range_pct` (that's the prediction). Drop per-driver `estimated_impact_pct`.

### D9: No fixed confidence arithmetic

Drop specific point penalties (-15, -10, -5). They're made up and create fake precision. Keep the rubric (what each bucket means) and the hard floor (both consensus+guidance missing → cap at 30). Let the LLM reason about actual impact of missing data, not do penalty math.

### D10: Bundle rendering = lossless tables

Render as **tables wherever possible** to reduce text for both LLM and human readability. Raw JSON only where structure is inherently nested/variable (timeline events). Metrics, summaries, peer data, financials → tables.

---

## 4. Input/Output Contracts

### 4a. Input — What the predictor receives

```
SYSTEM PROMPT:
  - Prediction instructions (3 phases, rules, output schema)

USER MESSAGE:
  - Rendered 7-item prediction bundle (sectioned text, tables)
  - [Turn 2 only] Supplementary answers to questions from Turn 1
```

**The 7 bundle items** (v1 — all built and standardized):

| # | Item | What It Provides | Builder |
|---|------|-------------------|---------|
| 1 | 8k_packet | Current quarter results, new guidance, press release | `build_8k_packet()` |
| 2 | guidance_history | Company guidance trajectory across quarters | `build_guidance_history()` |
| 3 | inter_quarter_context | Timeline: news, filings, analyst actions, significant moves, gap days | `build_inter_quarter_context()` |
| 4 | peer_earnings_snapshot | Sector peer results and stock reactions | `build_peer_earnings_snapshot()` |
| 5 | macro_snapshot | SPY, VIX, sector, indicators | `build_macro_snapshot()` |
| 6 | consensus | EPS + revenue expectations, revision history, beat/miss streak | `build_consensus()` |
| 7 | prior_financials | Multi-quarter financials (EPS, revenue, margins, 19 metrics) | `build_prior_financials()` |

**Deferred items (v2 — 9 total, do not forget)**:
- #8 `previous_earnings` — compact summary of prior quarter results + reaction (after learner exists)
- #9 `previous_earnings_lessons` — U1 feedback from prior learner output (after learner exists)

### 4b. Output — prediction_result.v1

```json
{
  "schema_version": "prediction_result.v1",
  "ticker": "CRM",
  "quarter_label": "Q4_FY2025",

  "direction": "long",
  "confidence_score": 62,
  "confidence_bucket": "moderate",
  "expected_move_range_pct": [0.5, 2.5],
  "magnitude_bucket": "small",
  "horizon": "next_session",

  "key_drivers": [
    {
      "rank": 1,
      "driver": "EPS beat with lowered bar",
      "direction": "long",
      "evidence": "8k_packet: EPS $2.58 vs consensus $2.55 (+1.2% beat). consensus: estimate revised down from $2.62 (90d ago). Bar lowered → beat rewarded."
    },
    {
      "rank": 2,
      "driver": "FY26 guidance below street",
      "direction": "short",
      "evidence": "8k_packet: FY26 EPS guidance $11.09-$11.17. inter_quarter_context: 20+ analyst PT cuts over 3 months. Guidance midpoint $11.13 likely below consensus."
    }
  ],

  "data_gaps": [
    {
      "item": "consensus",
      "gap": "No forward FY26 consensus from AlphaVantage. Using inter-quarter analyst actions as proxy."
    }
  ],

  "analysis": "3-phase reasoning summary",

  "evidence_ledger": [
    {"metric": "EPS Actual", "value": "$2.58", "source": "8k_packet/exhibits_99/EX-99.1"},
    {"metric": "EPS Consensus", "value": "$2.55", "source": "consensus/quarterly_rows[0].eps_estimate"},
    {"metric": "Revenue Actual", "value": "$9.82B", "source": "8k_packet/exhibits_99/EX-99.1"},
    {"metric": "Revenue Consensus", "value": "$9.75B", "source": "consensus/quarterly_rows[0].revenue_estimate"}
  ],

  "predicted_at": "2026-03-31T14:22:00Z",
  "model_version": "claude-opus-4-6",
  "prompt_version": "predictor.v2.0"
}
```

**Direction values**: `long` | `short` | `no_call`
- `no_call` = genuinely cannot determine direction (not low-confidence long/short)
- When direction = `no_call`: signal = `hold`, confidence/magnitude still recorded

**Confidence buckets**: `high` (70-100) | `moderate` (40-69) | `low` (1-39)

**Magnitude thresholds**: `small` (<2%) | `medium` (2-4%) | `large` (4%+)

### 4c. Output — questions (alternative Turn 1 output)

```json
{
  "needs_more_data": true,
  "reasoning": "8-K reports cRPO of $51B but bundle lacks cRPO consensus. For SaaS companies, cRPO surprise often dominates — could flip direction.",
  "questions": [
    {
      "agent": "perplexity-ask",
      "query": "What was analyst consensus for Salesforce CRM cRPO before Q1 FY2026 earnings on Feb 26, 2025?"
    }
  ]
}
```

**Whitelisted agents**: `neo4j-report`, `neo4j-transcript`, `neo4j-xbrl`, `neo4j-news`, `neo4j-entity`, `alphavantage-earnings`, `perplexity-ask`, `perplexity-search`

---

## 5. Reasoning Protocol (3 Phases)

### Phase 1: EXTRACT ANCHORS

Scan all 7 bundle items. For each: present / missing / error? Extract key metrics into evidence ledger. Calculate surprise for every metric pair (actual vs expected). Don't form opinions yet.

**Evidence ledger rule**: If you use a number in Phase 2 or 3, it MUST appear in the ledger with a source. No source → can't use it.

**Surprise formula**: `((actual - expected) / |expected|) * 100`

Also extract non-numeric signals: management tone, analyst sentiment pattern, peer reactions, guidance trajectory.

**Quality check**: When extracting metrics, assess results quality — not just magnitude. Organic revenue growth vs acquisition-driven. EPS beat from operations vs one-time items (tax benefit, restructuring). Margin trajectory (expanding from mix shift vs pricing vs cost cuts). Markets react very differently to the same headline number depending on quality.

### Phase 2: RESOLVE TENSIONS

Cross-reference ALL evidence:
1. What is the dominant narrative?
2. Are there competing narratives? Which one does the evidence favor?
3. What does the market care about for THIS company? (from inter-quarter price reactions — what moved the stock between earnings?)
4. What's the bar? (Has consensus been lowered/raised? How much is priced in from inter-quarter moves?)
5. Rank the top 3-5 drivers. Each must cite specific evidence.

**Anti-anchoring rule**: Do NOT form a directional opinion until you've worked through all 5 questions above.

### Phase 3: DECIDE

Now form the prediction:
- **Direction**: long, short, or no_call
- **Magnitude**: expected move range [low, high] %
- **Confidence**: score 0-100 with explicit reasoning
- **Data gaps**: what's missing that could change this call?
- **OR Questions**: if a gap could flip direction, ask instead of predicting

**Confidence rubric** (qualitative guardrails, not fixed arithmetic):

| Bucket | Conditions |
|--------|------------|
| high (70-100) | 3+ converging signals, dominant narrative clear, no strong counter |
| moderate (40-69) | 1-2 clear signals with ambiguity, or strong signal + notable counter |
| low (1-39) | Weak signals, significant missing data, or balanced conflicting evidence |

**Hard floor**: Both consensus AND guidance missing → max confidence 30.

**Honest uncertainty**: Missing data should meaningfully reduce confidence. But the LLM reasons about HOW MUCH based on the specific situation, not fixed point penalties.

### Signal Derivation (DETERMINISTIC — Python, not LLM)

```python
def derive_signal(direction, confidence_bucket, magnitude_bucket):
    if direction == "no_call":
        return "hold"

    strength = {
        ("high", "large"): "strong",
        ("high", "medium"): "strong",
        ("high", "small"): "moderate",
        ("moderate", "large"): "moderate",
        ("moderate", "medium"): "moderate",
        ("moderate", "small"): "weak",
        ("low", "large"): "weak",
        ("low", "medium"): "weak",
        ("low", "small"): "weak",
    }[(confidence_bucket, magnitude_bucket)]

    return f"{strength}_{direction}"
```

---

## 6. Follow-Up Question Rules

Ask ONLY when ALL of:
1. A specific data gap exists in the bundle
2. Filling it could **materially flip** the direction call (long ↔ short ↔ no_call)
3. Answerable by a whitelisted agent

**Invalid questions** (don't ask):
- Post-filing analyst reactions (PIT violation)
- Data already in the bundle (macro, peers, etc.)
- Return data or current stock price
- Full transcripts (not a targeted gap)

**Orchestrator handling**: validate questions → fetch in parallel via data sub-agents → re-invoke SDK for Turn 2 → Turn 2 MUST predict → persist in supplementary.json

---

## 7. Speed Budget

| Phase | Time |
|-------|------|
| Bundle assembly (7 builders parallel) | ~15-20s |
| SDK + predictor Turn 1 | ~50-65s |
| [If questions] Agent fetch + Turn 2 | ~50-75s |
| **Total (no questions)** | **~65-85s** |
| **Total (with questions)** | **~115-140s** |

---

## 8. PIT Compliance

| Mode | Rule |
|------|------|
| Historical | Bundle is pre-filtered by adapters. Supplementary queries get `--pit` from orchestrator |
| Live | No PIT gate. Fresh data from builders at trigger time |

Predictor has ZERO PIT responsibility. Bundle is pre-filtered. Orchestrator enforces PIT on supplementary queries.

---

## 9. Invocation Pattern (follows extraction pipeline)

Same two-layer pattern as guidance extraction:

```
earnings_orchestrator.py (Python)
  1. Build 7-item bundle (Python builders, parallel)
  2. Render bundle to disk (tables + lossless)
  3. SDK call: claude_agent_sdk.query(prompt="/earnings-prediction {bundle_path}")
     → Claude Code → Skill fork (earnings-prediction/SKILL.md)
       → Predictor reads bundle, reasons, writes result file
  4. Orchestrator reads result file
  5. If questions.json: fetch answers via data sub-agents, re-invoke SDK for Turn 2
  6. Validate + persist
```

File-based result protocol:
- Turn 1: `prediction/result.json` (prediction) OR `prediction/questions.json` (needs more data)
- Turn 2: `prediction/result.json` (must predict)

---

## 10. Implementation Components

| Component | Location | Status |
|-----------|----------|--------|
| Predictor system prompt (SKILL.md) | `.claude/skills/earnings-prediction/SKILL.md` | DRAFT v2.0 — needs finalization |
| Bundle table renderers | `scripts/earnings/earnings_orchestrator.py` | `render_bundle_text()` exists — needs decision-ordered table rendering |
| SDK invocation in orchestrator | `scripts/earnings/earnings_orchestrator.py` | EXISTS — `run_predictor_via_sdk()` + `_run_predictor_via_sdk()` at :332/:360 |
| Output validation + signal derivation | `scripts/earnings/earnings_orchestrator.py` | EXISTS — `validate_prediction_result()` at :264. Signal derivation TBD |
| Question validation + fetch | `scripts/earnings/earnings_orchestrator.py` | NOT BUILT |

---

## 11. Resolved Questions

| # | Question | Resolution |
|---|----------|------------|
| Q1 | SDK vs Skill? | SDK + Skill together (extraction pipeline pattern) |
| Q2 | Evidence ledger format? | Structured JSON field |
| Q3 | Bundle rendering? | Lossless tables wherever possible |
| Q4 | previous_earnings? | Deferred to v2 (after learner exists) |
| Q5 | Builder errors? | Show `[BUILDER ERROR: msg]` to predictor |

---

## 12. Summary of Rules

**Predictor**:
1. 3 phases in order: Extract Anchors → Resolve Tensions → Decide
2. Every number must cite source in evidence ledger
3. No directional opinion before Phase 2 complete
4. `no_call` when evidence doesn't support a direction — be honest
5. Confidence follows rubric, not fixed arithmetic
6. Questions only when gap could flip direction
7. Turn 2 must predict

**Orchestrator**:
1. Run all 7 builders, render as tables
2. Validate output schema, compute signal deterministically
3. Enforce question whitelist, max count, PIT on supplementary
4. Persist everything: bundle, supplementary, result

**Iteration principle**: Build simplest version, run on real data, improve from actual predictor feedback. No premature optimization.

---

## 13. Bundle Rendering — Deep Analysis (DOCU Q1_FY2024 case study)

### The Problem: What the predictor currently sees

Real example: `earnings-analysis/Companies/DOCU/events/Q1_FY2024/prediction/context_bundle_rendered.txt`
- **171,062 characters / 4,482 lines** of raw JSON with section headers

| Section | Lines | % of Bundle | Decision Relevance |
|---------|-------|-------------|-------------------|
| 1. 8-K (full JSON + exhibits) | 5-69 | ~65 lines structure + massive press release | **Core** — but buried in noise |
| 2. Guidance History | 71-990 | **920 lines** | High |
| 3. Inter-Quarter Events | 991-3623 | **2,633 lines (59% of bundle)** | Moderate — drowns everything else |
| 4. Peer Earnings | 3624-3843 | 220 lines | Moderate |
| 5. Macro Snapshot | 3844-4131 | 288 lines | Low-Moderate |
| 6. Consensus | 4132-4288 | 157 lines | **Critical** — but at line 4132 (92% through) |
| 7. Prior Financials | 4289-4482 | 194 lines | Moderate |

### Three accuracy problems with current rendering

**Problem 1: Most decision-relevant information is scattered and buried.**
The LLM parses 65 lines of JSON nesting, a board appointment press release (EX-99.2), legal boilerplate ("forward-looking statements..."), non-GAAP methodology explanations — before finding actual EPS and revenue numbers. The consensus (other half of the surprise equation) doesn't appear until line 4132. The LLM must hold 8-K numbers in memory across 4,000+ lines before computing surprise.

**Problem 2: LLM attention is front-loaded and back-loaded ("lost in the middle").**
What's at the top now? JSON braces and a board appointment. What SHOULD be at the top? `EPS: $0.72 actual vs $0.56 expected (+28.6% beat)`. The single most important fact for the prediction is buried.

**Problem 3: Inter-quarter events (2,633 lines) drown signal in noise.**
59% of the entire bundle. Most events are minor. Significant events (analyst upgrades/downgrades, gap days, big stock moves) are mixed in with routine news. The LLM's attention is diluted across thousands of events when only 5-10 matter.

### Proposed rendering order (by decision relevance)

Reorder by DECISION RELEVANCE, not builder execution order. Pre-compute FACTS (arithmetic, labels), not conclusions (narrative, interpretation). The LLM draws conclusions — the renderer presents data.

**1. HEADER**
Ticker, quarter, filed time, market session, mode (historical/live), PIT cutoff.

**2. EARNINGS HIGHLIGHTS + SURPRISE TABLE (pre-computed facts)**
```
DOCU Q1 FY2024 | Filed: 2023-06-08 post_market

| Metric              | Expected | Actual  | Surprise |
|---------------------|----------|---------|----------|
| EPS (Non-GAAP dil.) | $0.56    | $0.72   | +28.6%   |
| Revenue             | $641.8M  | $661.4M | +3.1%    |
```
Plus key operating metrics from 8-K that matter for this company type (e.g. billings, subscription revenue for SaaS; same-store sales for retail). Not just EPS/revenue — the compact highlights of what the company JUST reported.

This is what an analyst looks at FIRST. Pre-computing the arithmetic in Python means the LLM doesn't waste reasoning capacity on math it could get wrong. Front-loading it orients the entire thinking process.

**3. FORWARD GUIDANCE (from 8-K press release + guidance_history)**
New guidance vs prior guidance. This is often MORE important than backward results for stock direction.

**4. CONSENSUS + REVISION CONTEXT (beat/miss history, "the bar")**
Was this beat expected? Has consensus been lowered coming in? Beat/miss streak. Revision momentum.

**5. PRIOR FINANCIALS (trend table)**
Multi-quarter revenue/EPS/margin trajectory. Structured factual context before the event narrative.

**6. INTER-QUARTER CONTEXT (filtered by decision salience)**
NOT just events with big price impact. Filter by DECISION SALIENCE: analyst upgrades/downgrades (even on flat days), management changes, guidance-channel news, gap days, significant moves. Some low-price-impact events still matter enormously for earnings interpretation (e.g. dividend cut on flat day = hugely bearish signal). Compressed from 2,633 lines to the events that could actually affect the earnings call.

**7. PEER EARNINGS (compact table)**
How sector peers reacted to their earnings. Sets the tone.

**8. MACRO SNAPSHOT (compact summary)**
SPY, VIX, sector performance. Usually a minor factor at company level.

**9. REFERENCE APPENDIX (full 8-K text, minus boilerplate)**
Full EX-99.1 press release for management commentary, product details, operational highlights the LLM might want to dig into. Legal disclaimers, non-GAAP methodology explanations, "about [company]" sections, and non-financial exhibits (board appointments) stripped. The LLM already has headline numbers from section 2.

### LLM attention steering principles

1. **Front-load the decision-critical information.** Surprise summary at the very top. The first thing read sets the frame for all subsequent reasoning.

2. **Tables > JSON.** Tables are instantly parseable. JSON wastes tokens on structure characters (`{`, `"`, `:`, nested braces) that carry zero signal. Every section that CAN be a table SHOULD be.

3. **Pre-compute what Python can compute.** Surprise percentages, beat/miss flags, consensus revision direction. Don't make the LLM do arithmetic it could get wrong.

4. **Strip noise that doesn't help prediction.** Forward-looking statements disclaimers, non-GAAP methodology explanations, board appointment press releases, "about DocuSign" boilerplate. These waste tokens and dilute attention.

5. **Compress the long tail.** Inter-quarter context: surface significant events as a compact table, put full timeline in reference or omit minor events.

6. **Recency reinforcement.** Key rules and output schema should appear AFTER the bundle (end of prompt), not just before it. The LLM remembers end-of-context better than beginning-of-context when the middle is 4,000+ lines.

### Word choice in the prompt

| Instead of | Use | Why |
|-----------|-----|-----|
| "You are an earnings prediction engine" | "You are a senior earnings analyst making a one-session directional call from a prebuilt prediction bundle" | Scopes to earnings, specifies horizon + output, reinforces bundle-only |
| "Extract anchors" | "What are the key numbers?" | Direct, human language |
| "Resolve tensions" | "Where do the signals conflict? Which side wins?" | Concrete, action-oriented |
| "Build an evidence ledger" | "For every number you cite, note where it came from" | Clear instruction, no jargon |

### Key insight

**Rendering and prompt are both critical.** Rendering removes obstacles (noise, poor ordering, buried signal) so the LLM can focus on reasoning. Prompt steers reasoning toward honest, evidence-backed decisions. Neither is secondary. But the rendering is where we have the most to gain right now — the current raw JSON dump actively hurts the predictor by burying signal in noise and forcing the LLM to do extraction work instead of reasoning about direction.
