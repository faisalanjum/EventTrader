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
2. Then read this file's Primary Context Pack in full (Infrastructure.md, DataSubAgents.md, etc.). Work on only this module per session — do not modify other module plans or the master plan.
3. Do not redesign architecture; resolve only open questions in this module plan, one question at a time.
4. Follow locked priorities: reliability > required data coverage > speed > accuracy/exhaustive research; no over-engineering.
5. Before each reply, re-check parent-plan consistency and update the module doc directly.
6. Record unresolved items in that module's open-question table; when resolved, move into main section and mark resolved.
7. Keep SDK compatibility and non-interactive execution constraints from `Infrastructure.md`.
8. Append to bot-to-bot notes at session start and when resolving questions.

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

## 4b) Prediction Context Design (decided 2026-03-15, revised 2026-03-15)

### Strategic Decision

**Do NOT pre-engineer features or build a tag/classification system for non-guidance events.** Pass raw inter-quarter events as text context. Let the LLM reason over them naturally, and let U1 discover which event types are actually predictive from real trading results.

**Reasoning**: Building a structured feature system upfront (e.g., "count of restructuring events", "net analyst sentiment score") risks: (1) engineering cost for features that may not be predictive, (2) information loss from premature categorization — the raw headline carries more signal than a tag, (3) maintenance burden for a taxonomy that may need constant revision.

**What to build later (only if U1 proves it)**: Formalize specific event types into structured features. Until then, raw context is sufficient.

### The Complete Prediction Bundle

Six inputs, each serving a distinct purpose. Total context: ~5-8K tokens. Negligible in 1M window.

**Input 1: Guidance history (extracted)**
From the extraction pipeline (transcripts + 8-K + 10-Q/10-K). The company's own forward projections across quarters. This is the core structured input.

**Input 2: Consensus estimates (AlphaVantage — structured)**

```
CRM Q1 FY26:
  EPS consensus: $2.55 (40 analysts), was $2.62 ninety days ago
  Revenue consensus: $9.75B (41 analysts)
```

Source: `EARNINGS` endpoint for PIT-safe final EPS (`estimatedEPS` frozen at reporting time). `EARNINGS_ESTIMATES` endpoint for revenue estimates and revision history (7/30/60/90 day lookbacks, analyst counts). ~100 tokens.

**PIT note**: For historical backtesting, `EARNINGS.estimatedEPS` is verified PIT-safe. `EARNINGS_ESTIMATES` revision history is LIKELY relative to reporting date (CRM evidence: 90-day-ago = $2.62 matches Feb headline) but not conclusively verified for all cases. Benzinga headlines (Input 5) provide a verified PIT backstop for both EPS and revenue via the "Vs $X.XX Est" pattern.

**Known gap**: AlphaVantage does NOT cover cash flow, EBITDA, or margin consensus. Company guidance for these metrics comes from Input 1. Street consensus for them is only available via Bloomberg/FactSet ($24K+/year). Log this — revisit if U1 flags prediction failures due to missing operating metric consensus.

**⚠️ Inputs 3-5 below are superseded by the unified `inter_quarter_context` timeline (see "Context Bundle Integration" section below and `plannerStep5.md`). The separate queries for non-earnings 8-Ks, significant moves, and channel-filtered news are replaced by one pre-assembled artifact with event-specific forward returns, exact timestamps, and stable `event_ref` IDs. The sections below are retained as historical design context.**

**Input 3: Non-earnings 8-K filings with extracted_sections (0-5 per quarter)**

```cypher
MATCH (r:Report)
WHERE r.symbols CONTAINS $ticker
  AND r.formType = '8-K'
  AND r.created > $last_earnings_date
  AND r.created < $current_earnings_date
  AND NOT r.description CONTAINS 'Item 2.02'
RETURN r.created, r.items, r.extracted_sections
ORDER BY r.created
```

**Must use `r.extracted_sections`, NOT `r.description`.** The description is just "Form 8-K - Current report - Item 7.01 Item 9.01" (useless). The extracted_sections contains the actual filing text — e.g., "Salesforce and Informatica issued a joint press release announcing a definitive agreement pursuant to which the Company will acquire Informatica." Typically 0-5 rows, 0.5-3 KB per filing.

**Input 4: Significant-move days with matched headlines (~5-6 per quarter)**

```cypher
// Significant move days (adjusted return > threshold)
MATCH (d:Date)-[r:HAS_PRICE]->(c:Company {ticker: $ticker})
WHERE d.date >= date($last_earnings) AND d.date < date($current_earnings)
MATCH (d)-[m:HAS_PRICE]->(idx:MarketIndex {ticker: 'SPY'})
WHERE r.daily_return IS NOT NULL AND m.daily_return IS NOT NULL
WITH d.date AS date, r.daily_return AS stock_return,
     r.daily_return - m.daily_return AS adj_return
WHERE abs(adj_return) >= 0.03  // or 1.5σ volatility-adjusted per newsImpact.md
RETURN date, stock_return, adj_return
ORDER BY date
```

Rendered with matched headlines from Input 5 (join on date):

```
Significant inter-quarter moves (|adj return| > 1.5σ):
  Feb 26: -4.2% — Salesforce Sees FY26 EPS $11.09-$11.17 Vs $11.19 Est
  Feb 27: -2.6% — 15 analyst PT cuts in one day
  Mar 21: +15.8% — no news
  Apr 8:  -3.1% — DA Davidson downgrades to Underperform ($200 PT)
  May 14: +2.8% — CRM acquires Convergence.ai
```

Purpose: what MOVED the stock + gap days (big moves with no news = hidden information flow). The LLM sees price impact alongside events. ~200 tokens.

**Why gap days matter**: "+15.8% with no news" is MORE informative than analyzed "Unknown driver, 0% confidence." It tells the LLM: "hidden information flow — insiders or institutions acted without public catalyst."

**Input 5: All channel-filtered news headlines (titles only, ~20-60 per quarter)**

```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WITH n, apoc.convert.fromJsonList(n.channels) AS chList
WHERE n.created > $last_earnings_date
  AND n.created < $current_earnings_date
  AND ANY(ch IN chList WHERE ch IN [
    'Analyst Ratings', 'Upgrades', 'Downgrades', 'Price Target',
    'M&A', 'Management', 'Short Sellers', 'Dividends',
    'Contracts', 'Offerings', 'Buybacks', 'Legal', 'Guidance'
  ])
RETURN n.title, n.created, chList
ORDER BY n.created
```

Purpose: the full inter-quarter narrative. This serves THREE functions:
1. **Analyst sentiment pattern** — 20+ PT cuts over 3 months is a stronger signal than "Feb 27: 15 cuts" alone. The LLM sees the sustained pattern.
2. **Non-significant events that carry signal** — a dividend raise that doesn't move the stock still signals management confidence in forward cash flows. A dividend CUT on a flat day would be an enormously bearish signal for next earnings. These only appear here, not in Input 4.
3. **Embedded consensus numbers** — Guidance-channel headlines contain "Vs $X.XX Est" (e.g., "Sees FY26 EPS $11.09-$11.17 Vs $11.19 Est."). These are PIT-safe (timestamped at publication) and give the LLM consensus for both EPS and revenue without any extraction pipeline.

~2K tokens for titles only. No bodies needed.

**Input 6: U1 feedback from prior quarters**
From the Attribution/Learner. Prior `predictor_lessons`, `what_worked`, `what_failed`. Already defined in orchestrator §2a.

### Why BOTH Input 4 AND Input 5

Input 4 (significant moves) tells the LLM what the MARKET cared about — price reactions + gap days. Input 5 (all headlines) tells the LLM what HAPPENED — the full event history including things the market may have under-reacted to.

- Gap days (+15.8% no news) are ONLY visible from Input 4
- Non-significant events (dividend raise, Guggenheim upgrade on flat day) are ONLY visible from Input 5
- Consensus numbers ("Vs $X.XX Est") in guidance headlines are ONLY visible from Input 5
- Price impact data is ONLY visible from Input 4

Together: ~2.5K tokens. The LLM gets both the market's revealed preferences AND the complete information set.

### Channel Selection Rationale

The 12 channels carry **company-specific fundamental information** that could shift earnings expectations:

| Channel | Why included |
|---|---|
| `Analyst Ratings` / `Upgrades` / `Downgrades` / `Price Target` | Street sentiment shifts |
| `M&A` | Revenue/cost structure changing |
| `Management` | Leadership stability |
| `Short Sellers` | Bearish thesis active |
| `Dividends` / `Buybacks` | Capital allocation signals (confidence or desperation) |
| `Contracts` / `Offerings` | Business activity |
| `Legal` | Risk factors |
| `Guidance` | Forward-looking statements + embedded consensus numbers ("Vs $X Est") |

Excluded: `News` (too generic, on 75% of articles), `Movers`/`Trading Ideas`/`General` (stock movement without fundamental content), `Options` (flow data), `Earnings` (would pull other companies' results), sector tags (`Tech`, `Biotech`).

**REVISIT NOTE**: After 50-100 predictions with U1 attribution, check if:
- Any included channel is consistently irrelevant (drop it)
- Any excluded channel (e.g., `Analyst Color`, `Earnings Beats/Misses`) shows up in attributor feedback as missing context (add it)
- Whether dropping the channel filter entirely performs comparably (~3K tokens for 200 titles is still negligible)

### Context Bundle Integration

`inter_quarter_context` is a **top-level field** in the context bundle (alongside `8k_content`, `guidance_history`, `u1_feedback`), NOT inside `fetched_data`. It is pre-assembled by the orchestrator via `build_inter_quarter_context()`.

Planner-fetched results go in `fetched_data` (orchestrator §2a):

```json
{
  "consensus_context": {
    "sources": ["alphavantage-earnings", "alphavantage-estimates"],
    "content": "(structured: EPS/Revenue estimate avg/high/low, analyst count, revision history)"
  }
}
```

All are **optional context** — if empty, the predictor proceeds without them. They feed reasoning but do not gate the prediction.

Note: `inter_quarter_context` replaces the old separate `inter_quarter_8k`, `significant_moves`, and `inter_quarter_news` fields. It is one pre-assembled rendered timeline with exact timestamps, forward returns, and stable `event_ref` IDs for follow-up.

**Nulled return horizons**: In historical mode, some events may have individual forward_returns horizons set to `null` (e.g., `daily: null` while `hourly` is kept). This means that horizon's measurement window extends past the PIT cutoff and would leak the earnings reaction. The predictor should treat these as "return not available for PIT reasons" — not as missing data. The event itself is legitimate pre-cutoff context; only the contaminated return window is suppressed.

**Live replay**: For exact reproducibility, the predictor should consume the persisted `inter_quarter_context.json` artifact, not a rebuilt query. The graph has no ingestion timestamps, so a later rebuild could include items that arrived after the original prediction.

**Render detail level**: The default rendered text uses compact 1-line news returns (best safe horizon only) and full 3-line filing returns. This is optimized for the planner's needs (significance detection, fetch-plan decisions). A separate predictor-optimized renderer may be added later to show full 3-horizon detail on all events — the canonical JSON already contains all horizons, so this is a pure rendering change with no data or pipeline impact.

### CRM Example (Feb 26 → May 28, 2025)

**Without context:** "CRM guided FY26 EPS $11.09-$11.17 vs $11.19 consensus" → coin flip.

**With all 6 inputs, the LLM sees:**
- Guidance below street → consensus has been dropping (AV: was $2.62, now $2.55)
- 20+ analyst PT cuts over 3 months → sustained bearish pressure
- DA Davidson downgraded to Underperform ($200 PT) → outlier bear
- BUT: Guggenheim flipped Sell→Neutral → contrarian turn
- Dividend raised 4% → management confident in cash flows
- Convergence.ai acquisition → investing in AI narrative
- Gap day: +15.8% with no news → hidden positive information flow
- Net: the bar has been LOWERED → beat more likely

**Actual result:** CRM reported $2.58 vs $2.55 consensus → beat by $0.03 (+1.2% surprise). Stock moved accordingly.

### Decisions Log (2026-03-15)

| Decision | Answer | Reasoning |
|---|---|---|
| News guidance extraction | **Skip** | Reports ON guidance, doesn't create it. 8-K + transcript + 10-Q/10-K cover 99%+. Headlines provide consensus via "Vs $X Est" pattern for free. |
| News consensus extraction | **Skip** | AlphaVantage covers EPS + Revenue. Headlines carry embedded consensus naturally. No extraction pipeline needed. |
| Operating metric consensus (CF, EBITDA, margins) | **Known gap** | No source available outside Bloomberg/FactSet. Company guidance extracted; street consensus unavailable. Revisit if U1 flags it. |
| News-impact analyzed output | **Don't feed to predictor** | Raw data > pre-analyzed interpretation. Feed returns + headlines (Input 4+5), not LLM-generated "driver: X, confidence: Y". Keep news-impact as standalone research tool. |
| Non-significant events | **Include** | A dividend raise/cut that doesn't move the stock still signals management outlook. The LLM should see all events and weigh them itself. Cost: ~2K tokens. |
| 8-K tag system (24 Haiku tags) | **Defer for non-guidance tags** | Only FINANCIAL_GUIDANCE + INVESTOR_PRESENTATION Haiku classification needed now (for guidance extraction routing). Other tags can be retroactively classified anytime — data isn't going anywhere. |

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

---

## TODO: Architecture Delta — Analyst Notes Engagement (2026-03-25)

**Status**: APPROVED — pending implementation. Changes below have NOT been applied to the sections above yet. When implementing, update the referenced sections and remove this TODO block.

### T1: New predictor input — `analyst_notes.json`

Predictor receives `planner/analyst_notes.json` in addition to the current bundle (pre-assembled data + fetched data). The notes contain the planner's pre-fetch observations: `macro_read`, `sector_read`, `financial_read`, `key_tensions`, `what_to_verify_after_fetch`, `attention_priorities`, `confidence_flags`. No directional lean.

**Sections to update**: §4 Required Input — add analyst_notes.json (from planner).

### T2: New predictor behavior — structured engagement

Before forming its prediction, the predictor MUST explicitly engage with the analyst notes. This is the mechanism that turns notes from passive context into active reasoning improvement.

**Required prompt structure**:

```
STEP 1: Engage with planner's analyst notes.

For each domain read (macro_read, sector_read, financial_read):
  - State the planner's pre-fetch hypothesis
  - State whether fetched data CONFIRMED, REFUTED, or COMPLICATED it
  - State what the fetched data ADDED that the planner didn't have

For each key_tension:
  - Which side does the full evidence favor?
  - Is it resolved or still ambiguous?

For each what_to_verify_after_fetch item:
  - Was it verified? What did you find?
  - Did the verification change your view?

STEP 2: Form independent prediction.
  - Synthesize all evidence (pre-assembled + fetched + notes engagement)
  - Output prediction/result.json per prediction_result.v1 contract
```

**Why this structure matters**: Without it, the predictor skims notes passively — minimal benefit. With it, the predictor is forced to address each domain perspective and resolve tensions explicitly. This reduces anchoring on a single signal (e.g., EPS beat) by forcing multi-dimensional engagement.

**Guardrail**: The predictor may DISAGREE with any note. Notes are hypotheses the planner wrote before seeing fetched data. The predictor has strictly more information and should override notes when the evidence warrants it.

**Sections to update**: §4b (new subsection for Analyst Notes Engagement), §7 Skill Sync Requirements (predictor prompt must include engagement structure).

### T3: New input — `peer_earnings_snapshot`

Predictor also receives `peer_earnings_snapshot` as part of the pre-assembled bundle. This provides sector peer context (beat/miss, guidance direction, stock reactions) that informs the predictor's sector reasoning.

**Sections to update**: §4 Required Input, §4b Prediction Context Design (add peer context as a data source alongside existing inputs).
