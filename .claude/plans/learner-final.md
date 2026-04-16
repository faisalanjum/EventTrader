# Earnings Learner — Final Design

**Created**: 2026-04-16
**Status**: APPROVED — all decisions locked, ready for implementation

### Human Review Gates (must be validated by user before calibration)

1. **SKILL.md prompt quality** — every single line of `.claude/skills/earnings-learner/SKILL.md` must be reviewed and approved. This is the learner's reasoning contract — no bot-only sign-off.
2. **PIT cutoff correctness** — verify that `get_quarterly_filings()` produces the correct next-quarter boundary across all tickers, including edge cases (annual quarters, deferred learners, first/last quarter).
3. **Lesson quality and evidence surface** — validate that the learner uses the full relevant evidence surface (all Data SubAgents, context bundle, post-event data) and converts findings into reusable, high-signal guidance rather than quarter-specific summaries.
**Parent plan**: `earnings-orchestrator.md` — this file supersedes the attribution/learner sections (§2d, §4) in the parent plan for all learner contract decisions
**Replaces**: `learner.md` (planning scaffold, now superseded)

---

## 1. Purpose

The earnings learner (`/earnings-learner`) is the post-event causal attribution module. It explains **why** a stock moved after an 8-K earnings filing, compares the realized move against the prediction, and produces reusable lessons that improve future predictions.

**It is NOT**: a predictor, a planner, a trade execution component, or a parameter tuner.

**End goal**: Every lesson the learner writes should make the predictor measurably better at the next quarter's call. The entire design serves this single objective.

**Learning type**: In-context learning only (Type 1). The predictor sees accumulated lessons as part of its context bundle. No parameter auto-tuning (Type 2) is in scope.

---

## 2. Trigger & Timing

### Historical mode
Learner runs sequentially after prediction for each quarter within a ticker's historical bootstrap:
```
Q(n) prediction → Q(n) learner → Q(n+1) prediction → Q(n+1) learner → ...
```
Q(n) learner **must** complete before Q(n+1) prediction starts, ensuring U1 feedback is available.

**Historical failure policy**: If Q(n) learner fails after one retry (no valid `attribution/result.json`), the ticker's sequential processing **stops at Q(n)**. It does NOT skip to Q(n+1). The failure is logged for investigation. After the underlying issue is fixed (bad data, unusual filing format, etc.), the ticker can be re-bootstrapped. Other tickers are unaffected. There is no time pressure in historical mode — chain integrity is more important than throughput.

**Live prediction is never blocked**: The live-quarter learner is deferred (§2 Live mode), so live prediction fires regardless of any learner state. The deferred learner runs during the next historical bootstrap, where the historical failure policy above applies.

### Live mode
Live prediction fires immediately on 8-K detection (no learner gate). The live-quarter learner is **deferred** to the next historical bootstrap.

**Why deferred** (was N=35 day timer, replaced): The learner competing with live predictions on the same queue wastes urgent token budget. By deferring to the next historical bootstrap, learners run on the historical queue (batch priority) and the data is richer — 10-Q/10-K and analyst coverage are available by then. Annual quarters (10-K filed 60-90 days after 8-K) are handled naturally without special exceptions.

Detection mechanism:

```
is_historical_done() checks:
  1. event.json quarters all have prediction + attribution result files
  2. live_state.json quarter has attribution if prediction exists
  → Missing attribution returns FALSE → daemon enqueues HISTORICAL
  → Orchestrator sequential processing catches the gap
```

### Hard-fail gates (both modes)
1. `prediction/result.json` must exist — cannot compare without a prediction
2. `daily_stock` return label must exist — cannot attribute without the realized outcome

If either is missing, the learner does NOT run. These are checked by the orchestrator in Python before invocation.

### No source-gating
The learner runs with whatever post-event data is available. Missing sources go into `missing_inputs[]`. Better to write a partial attribution than to block indefinitely.

### Historical bootstrap prerequisites
The historical bootstrap itself is **guidance-gated**: it waits until guidance extraction is completed/failed for all prior quarters. By the time the learner runs for Q(n), all prior guidance and learnings are available. This gating is the daemon/orchestrator's responsibility, not the learner's.

---

## 3. PIT Gating (Information Leakage Prevention)

### The contamination vector
Q(n) learner writes lessons → Q(n+1) predictor reads them. If Q(n) learner saw data from after Q(n+1)'s 8-K filing, those lessons could leak future information into the predictor.

### PIT rule (three-tier)

| Priority | Condition | PIT cutoff |
|----------|-----------|------------|
| 1 | Q(n+1) exists in `get_quarterly_filings()` output | Q(n+1)'s `filed_8k` timestamp |
| 2 | No Q(n+1) in event list, but a live cycle exists (`live_state.json` or fresh 8-K with `daily_stock IS NULL`) | Live quarter's `filed_8k` timestamp |
| 3 | No Q(n+1) and no live cycle | Current invocation time |

For **live learner**: PIT is disabled. All sources are unrestricted.

### PIT enforcement mechanism

PIT is enforced **deterministically** via existing infrastructure, not by prompt instruction alone:

**Neo4j agents**: `[PIT: {pit_cutoff}]` prefix in subagent prompt → agents add WHERE-clause date filters. `pit_gate.py` hook validates every Neo4j read response. If any item has `available_at > PIT`, the hook blocks and the agent retries.

**External sources**: `pit_fetch.py` wrapper handles PIT filtering per source:
```bash
python3 .claude/skills/earnings-orchestrator/scripts/pit_fetch.py \
  --source alphavantage --pit 2024-05-02T16:30:00-04:00 EARNINGS symbol=AAPL
```
Each external item gets `available_at` mapped from provider metadata. Items without verifiable publication timestamps are dropped (fail-closed).

**Source priority for historical runs** (stricter sources first):

| Tier | Sources | PIT mechanism |
|------|---------|---------------|
| 0 (deterministic) | neo4j-report, neo4j-transcript, neo4j-xbrl, neo4j-news, neo4j-entity, neo4j-vector-search | WHERE clause + `pit_gate.py` |
| 1 (PIT-safe APIs) | alphavantage-earnings, yahoo-earnings, bz-news-api | `pit_fetch.py` + `available_at` validation |
| 2 (gap-fill only) | perplexity-ask, perplexity-search, perplexity-reason, perplexity-research | `pit_fetch.py` wraps API directly, excludes synthesis answer in PIT mode |

Historical learner should exhaust Tier 0-1 before using Tier 2. Live learner has no tier restriction.

### Traced example

```
Ticker AAPL, historical bootstrap:
  get_quarterly_filings() returns:
    Q1_FY2024: filed_8k=2024-02-01T16:30
    Q2_FY2024: filed_8k=2024-05-02T16:30
    Q3_FY2024: filed_8k=2024-08-01T16:30
    Q4_FY2024: filed_8k=2024-11-01T16:30
    Q1_FY2025: filed_8k=2025-02-01T16:30

  Sequential processing:
    Q1 prediction (PIT=Q1 filed_8k) → Q1 learner (PIT=Q2 filed_8k: 2024-05-02T16:30)
      → Learner sees: transcript, 10-Q, all news between Q1 and Q2 earnings
      → Learner does NOT see: anything from Q2's 8-K day onward
      → Writes attribution/result.json → Python appends to ticker.json, global.json

    Q2 prediction (PIT=Q2 filed_8k, reads Q1 lessons) → Q2 learner (PIT=Q3 filed_8k)
    ...
    Q1_FY2025 prediction → Q1_FY2025 learner (PIT=now, no Q2_FY2025 yet)
```

---

## 4. Inputs

The orchestrator assembles these inputs and passes them to the learner.

**Design choice: no pre-assembled bundle.** Unlike the predictor (which receives a pre-built 8-section bundle), the learner does NOT get a pre-assembled data bundle. The learner is fundamentally different — no speed constraint, multi-turn, follows evidence trails. Pre-assembling a bundle would constrain its investigation. Instead, the learner receives targeted inputs (prediction result, actual returns, metadata) and a **reference** to the predictor's context_bundle.json (to see what the predictor had). The learner then autonomously fetches whatever post-event data it needs via Data SubAgents or direct MCP access.

### Pre-fetched by orchestrator (Python)

| Input | Source | Required |
|-------|--------|----------|
| `prediction/result.json` | Filesystem | **Yes** (hard gate) |
| `actual_return` packet | Neo4j PUBLISHED_AS relationship on 8-K | **Yes** (hard gate, validated before invocation) |
| `prediction/context_bundle.json` path | Filesystem | Yes (reference only — what predictor saw) |
| Quarter metadata: `ticker`, `quarter_label`, `filed_8k`, `accession_8k` | event.json | Yes |
| `pit_cutoff` | Derived from get_quarterly_filings() per §3 rules | Yes (null for live) |
| `pit_mode` | `"historical"` or `"live"` | Yes |
| Prior lessons: `learnings/ticker/{TICKER}.json` path | Filesystem | Yes (may not exist for first quarter) |

### Normalized `actual_return` packet

Orchestrator queries Neo4j and normalizes field names before passing to learner:

```json
{
  "daily_stock_pct": -5.28,
  "hourly_stock_pct": -3.12,
  "session_stock_pct": -4.1,
  "daily_macro_pct": -0.5,
  "daily_sector_pct": -1.2,
  "daily_industry_pct": null,
  "market_session": "after_hours"
}
```

Field mapping from Neo4j: `daily_stock` → `daily_stock_pct`, `hourly_stock` → `hourly_stock_pct`, `daily_macro` → `daily_macro_pct`, etc. Null when the relationship property is absent.

### Self-fetched by learner (Data SubAgents)

The learner autonomously queries additional sources using PIT-enabled Data SubAgents. Available sources:

**Neo4j (Tier 0)**:
- `neo4j-report` — 8-K filing details, exhibits (EX-99.1), return data
- `neo4j-transcript` — Earnings call transcript, prepared remarks, Q&A exchanges
- `neo4j-xbrl` — 10-Q/10-K financial statement data (EPS, revenue, margins, segments)
- `neo4j-news` — News articles with channel filtering (earnings, analyst, corporate, legal, notable) and stock return impact
- `neo4j-entity` — Company info, price series, dividends, splits, sector/industry
- `neo4j-vector-search` — Semantic search across news and transcript Q&A

**External APIs (Tier 1)**:
- `alphavantage-earnings` — Consensus estimates, actuals, earnings calendar
- `yahoo-earnings` — Earnings history, analyst ratings/price targets, upgrades/downgrades
- `bz-news-api` — Benzinga news with channel-filtered pre/post-event coverage

**Web/Research (Tier 2 — historical gap-fill only, live unrestricted)**:
- `perplexity-ask` — Quick factual Q&A with citations
- `perplexity-search` — Web search for analyst commentary, market reactions
- `perplexity-reason` — Multi-step reasoning for complex attribution
- `perplexity-research` — Deep investigation (live only, or rare historical gap-fill)

The learner should investigate exhaustively within its max_turns guardrail (40-50 turns). It is free to query any source, follow leads, and iterate until confident in its attribution.

---

## 5. What the Learner Does

### Five-phase workflow

**Phase 1 — Load Context**
1. **Read prediction + actuals**: Load `prediction/result.json` and `actual_return` to establish the gap (what was predicted vs what happened)
2. **Scan prediction context bundle**: Read `prediction/context_bundle.json` to understand what data the predictor had access to. Essential for distinguishing "predictor never had this signal" (→ data_lessons: "fetch X") from "predictor had it but underweighted it" (→ data_lessons: "weight X more")
3. **Read prior lessons**: Load `learnings/ticker/{TICKER}.json` if it exists — review own prior advice for refinement

**Phase 2 — Investigate**
4. **Fetch post-event evidence** via PIT-gated Data SubAgents (or direct MCP). Exhaust Tier 0-1 before Tier 2. Sources:
   - Earnings transcript Q&A (what did analysts focus on? what did management hedge on?)
   - 10-Q/10-K XBRL actuals (margin trends, segment breakdowns, cash flow changes)
   - Post-event news (analyst reactions, upgrades/downgrades, rating changes)
   - Pre-event news (expectations setup, channel-filtered for earnings/analyst/corporate)
   - Entity data (inter-quarter price action, dividends, splits)
   - Consensus verification (AlphaVantage for historical; Perplexity for live)
   - Peer/sector reactions (same-sector companies' returns around the event)

**Phase 3 — Attribute**
5. **Identify primary driver** and contributing factors — each with `summary`, `category`, and `evidence_refs` (ledger IDs)
6. **Compare predicted vs actual**: What worked, what failed, and why — populate `prediction_comparison`

**Phase 4 — Distill Lessons**
7. **Write predictor lessons**: Capped (≤3), specific, actionable — how should the predictor reason differently?
8. **Write data lessons**: Capped (≤3) — what data signals should the predictor have fetched or weighted more heavily?
9. **Write global observations**: Sector, macro, or cross-ticker insights (0-3 entries)
10. **Refine prior lessons**: If prior advice was too vague or misdirected, write a more specific replacement in this quarter's entry

**Phase 5 — Finalize**
11. **Record gaps**: Any unavailable sources go to `missing_inputs[]`
12. **Write `attribution/result.json`**: Single output file containing all of the above. Python handles derived writes (ticker.json, global.json).

### Key principles

- **Evidence-based claims only**: Every attribution claim must cite a source in the evidence ledger. No unsourced assertions.
- **Causal, not correlational**: The primary driver should explain the mechanism (e.g., "guidance cut overshadowed EPS beat because forward outlook worsened by -8.2%"), not just note co-occurrence.
- **Lesson specificity**: "Weight guidance more" is too vague. "When management narrows guidance range downward while EPS beats, guidance dominates for this ticker (3/4 quarters)" is actionable.
- **Generalizability guardrail**: Lessons must be reusable across future quarters. No quarter-specific command rules (e.g., NOT "in Q3 FY2024 always go short on NOG"). Lessons are advisory soft priors, not hard rules. The learner converts findings into guidance that improves predictor behavior without overfitting to a single event.
- **Predictor-facing output**: Everything the learner writes should be optimized for making the NEXT prediction better. Forensic detail exists for audit, but lessons exist for improvement.
- **Caps enforce signal quality**: The learner must prioritize the most important observations rather than dumping everything. Capped arrays force ruthless prioritization.

---

## 6. Output Contract: `attribution/result.json`

**Schema version**: `attribution_result.v2`
**File path**: `earnings-analysis/Companies/{TICKER}/events/{quarter_label}/attribution/result.json`

### Full schema

```json
{
  "schema_version": "attribution_result.v2",
  "ticker": "AAPL",
  "quarter_label": "Q1_FY2025",
  "filed_8k": "2025-05-01T16:30:00-04:00",
  "accession_8k": "0000320193-25-000055",
  "attributed_at": "2026-04-16T14:30:00-04:00",
  "model_version": "claude-opus-4-6",
  "pit_mode": "historical",
  "pit_cutoff": "2025-07-31T16:00:00-04:00",
  "pit_boundary_source": "next_quarter",

  "actual_return": {
    "daily_stock_pct": -5.28,
    "hourly_stock_pct": -3.12,
    "session_stock_pct": -4.1,
    "daily_macro_pct": -0.5,
    "daily_sector_pct": -1.2,
    "daily_industry_pct": null,
    "market_session": "after_hours"
  },

  "evidence_ledger": [
    {"id": "E1", "claim": "EPS Actual", "value": "$1.65", "source": "8K:EX-99.1", "date": "2025-05-01"},
    {"id": "E2", "claim": "EPS Consensus", "value": "$1.63", "source": "AlphaVantage:EARNINGS", "date": "pre-filing"},
    {"id": "E3", "claim": "Tariff Cost Guidance", "value": "$900M for Q3", "source": "Transcript:PreparedRemarks", "date": "2025-05-01"},
    {"id": "E4", "claim": "Gross Margin Guidance Cut", "value": "-60 to -160 bps", "source": "8K:EX-99.1", "date": "2025-05-01"},
    {"id": "E5", "claim": "Greater China Revenue", "value": "$16.0B vs $16.4B PY (-2.3% YoY)", "source": "8K:EX-99.1", "date": "2025-05-01"},
    {"id": "E6", "claim": "Analyst Reaction — Goldman", "value": "Downgraded to Neutral", "source": "News:AnalystRatings", "date": "2025-05-02"}
  ],

  "primary_driver": {
    "summary": "$900M tariff cost warning — first quantification by management, drove gross margin guidance cut",
    "category": "guidance_change",
    "evidence_refs": ["E3", "E4"]
  },

  "contributing_factors": [
    {
      "summary": "Greater China revenue decline continuing 3-quarter deceleration trend",
      "category": "segment_performance",
      "evidence_refs": ["E5"]
    },
    {
      "summary": "Post-earnings analyst downgrades amplified negative sentiment",
      "category": "analyst_sentiment",
      "evidence_refs": ["E6"]
    }
  ],

  "feedback": {
    "prediction_comparison": {
      "predicted_direction": "long",
      "predicted_confidence_score": 72,
      "predicted_move_range_pct": [2.0, 5.0],
      "predicted_key_drivers": ["Services revenue momentum", "EPS beat expectations"],
      "actual_direction": "short",
      "direction_correct": false,
      "magnitude_error_pct": 7.28,
      "comment": "Overweighted EPS beat, missed tariff cost quantification as dominant driver"
    },
    "what_worked": [
      "EPS beat direction correctly identified from strong Services momentum"
    ],
    "what_failed": [
      "Missed tariff cost quantification as primary driver — management had not quantified before this call",
      "Underweighted Greater China deceleration despite 3-quarter declining trend"
    ],
    "why": "Predictor had no signal on tariff cost magnitude (first-time disclosure). Post-event transcript and EX-99.1 revealed this as the dominant market narrative, confirmed by analyst downgrades next day.",
    "predictor_lessons": [
      "When macro trade tensions are elevated, weight management cost-impact commentary over EPS beat magnitude — first-time quantifications often dominate reactions",
      "Greater China revenue trajectory shows 3-quarter structural decline — treat as ongoing headwind, not one-time miss"
    ],
    "data_lessons": [
      "Fetch sector peer tariff exposure data (MSFT/GOOG tariff guidance) to calibrate tariff risk severity — peer context was absent from prediction bundle",
      "Weight Transcript Q&A analyst focus areas: 6/10 questions targeted tariff impact, signaling market concern the predictor missed"
    ]
  },

  "global_observations": [
    {
      "scope": "sector",
      "scope_key": "Technology",
      "lesson": "Tariff cost quantification dominated tech reactions in Q1 FY2025 — first-time management disclosures of cost magnitude were primary drivers"
    },
    {
      "scope": "macro",
      "scope_key": "trade_tensions",
      "lesson": "During elevated trade tensions, forward cost guidance dominates backward EPS beats by ~2x in attribution weight"
    }
  ],

  "missing_inputs": ["10-K"],

  "data_sources_used": [
    "neo4j-report", "neo4j-transcript", "neo4j-news",
    "neo4j-xbrl", "neo4j-entity", "alphavantage-earnings"
  ],

  "context_bundle_ref": "prediction/context_bundle.json",
  "prediction_result_ref": "prediction/result.json"
}
```

### Field reference

| Field | Required | Notes |
|-------|----------|-------|
| `schema_version` | Yes | `"attribution_result.v2"` |
| `ticker`, `quarter_label`, `filed_8k`, `accession_8k` | Yes | Event identifiers (match prediction) |
| `attributed_at` | Yes | ISO timestamp when attribution completed |
| `model_version` | Yes | Model that ran the attribution |
| `pit_mode` | Yes | `"historical"` or `"live"` |
| `pit_cutoff` | Yes | ISO timestamp or `null` (live mode) |
| `actual_return` | Yes | Normalized return packet (§4) |
| `evidence_ledger` | Yes | Array of `{id, claim, value, source, date}`. Every numeric or factual assertion cited here. Required non-empty for any valid attribution. |
| `primary_driver` | Yes | `summary` (free text) + `category` (snake_case string, see below) + `evidence_refs` (array of ledger IDs). Drivers may cite current-quarter filings, prior-quarter filings, peer returns, transcript passages, predictor context bundle evidence, and post-event coverage — but every cited claim must resolve to a ledger ID. |
| `contributing_factors` | Yes | Array (max 3, same shape as primary_driver). Can be `[]`. |
| `feedback` | Yes | Nested block — see below |
| `global_observations` | Yes | Array (max 3) of `{scope, scope_key, lesson}` for cross-ticker learning. Can be `[]`. Python extracts these and appends to `global.json`. |
| `missing_inputs` | Yes | Array of canonical strings. Can be `[]`. |
| `data_sources_used` | Yes | Array of agent names actually queried |
| `context_bundle_ref` | Yes | Relative path to prediction's context bundle |
| `prediction_result_ref` | Yes | Relative path to prediction result |
| `pit_boundary_source` | Yes | `"next_quarter"`, `"live_cycle"`, or `"invocation_time"` — which §3 tier determined the PIT cutoff |

**Feedback block caps:**

| Field | Max | Purpose |
|-------|-----|---------|
| `prediction_comparison` | 1 object | Predicted vs actual comparison. Fields copied from `prediction/result.json`: `predicted_direction` (← `direction`), `predicted_confidence_score` (← `confidence_score`), `predicted_move_range_pct` (← `expected_move_range_pct`), `predicted_key_drivers` (← `key_drivers`). `actual_direction` derived from `daily_stock_pct` sign (positive = long, negative = short). `magnitude_error_pct` = distance from `actual_daily_stock_pct` to nearest bound of directionally-signed predicted range; 0 if actual is within range. Example: predicted long [+2.0, +5.0], actual -5.28% → nearest bound +2.0 → \|(-5.28) - 2.0\| = 7.28. |
| `what_worked` | 2 items | What the predictor got right (prevents over-correction) |
| `what_failed` | 3 items | Where the prediction went wrong |
| `why` | 1-3 sentences | Causal context explaining the gap |
| `predictor_lessons` | 3 items | How to reason differently next time (soft priors) |
| `data_lessons` | 3 items | What data to seek or weight more heavily. Covers both "fetch X" (predictor never had it — confirmed by scanning context_bundle.json) and "weight X more" (predictor had it but underweighted it) |

Caps enforce signal quality. Required arrays may be empty when no valid item exists; do not add filler. All lesson fields (`predictor_lessons`, `data_lessons`, `global_observations`) must be generalizable heuristics reusable across future quarters — not quarter-specific commands (see Generalizability guardrail in §5).

**Driver `category` field**: Free-form snake_case label for the dominant reaction mechanism. Advisory for grouping and pattern analysis only — `summary` + `evidence_refs` remain authoritative. Use a familiar label when it cleanly fits. Otherwise create a precise new snake_case label (e.g., `credit_loss_reserve_build`, `fleet_utilization`, `subscriber_churn`). If several mechanisms matter, choose the one that best explains the market reaction and capture the rest in `summary` or `contributing_factors`. Do not validate against a fixed enum.

Illustrative example labels (non-exhaustive):

| Label | Typical use |
|-------|-------------|
| `eps_surprise` | EPS beat or miss was dominant |
| `revenue_surprise` | Revenue beat or miss was dominant |
| `guidance_change` | Forward guidance raise, cut, narrowing, or maintained |
| `margin_shift` | Gross/operating/net margin expansion or compression |
| `segment_performance` | Specific segment strength/weakness (geo, product, business unit) |
| `macro_environment` | Macro conditions dominated (rates, trade, geopolitical) |
| `sector_momentum` | Sector-wide move, not company-specific |
| `management_action` | Leadership change, restructuring, M&A, capital allocation |
| `analyst_sentiment` | Analyst upgrades/downgrades, target revisions |
| `product_cycle` | Product launch, delay, demand signals |
| `regulatory` | FDA, antitrust, trade tariff, compliance |
| `clinical_trial_readout` | Biotech: trial data release |
| `nim_compression` | Banks: net interest margin change |
| `occupancy_decline` | REITs: occupancy or same-store metrics |
| `production_guidance` | Energy/industrials: output volume guidance |

If none of these fit, coin a precise new label — there is no `other` category.

**Canonical `missing_inputs` values:**
`transcript`, `10-Q`, `10-K`, `presentation`, `post_event_news`, `peer_reactions`, `sector_context`, `xbrl_actuals`

### Changes from `attribution_result.v1` (master plan §2d)

| Change | Rationale |
|--------|-----------|
| Dropped `surprise_analysis` | Predictor already computes EPS/revenue/guidance surprise |
| Dropped `analysis_summary` | Machine-readable output; causal narrative captured in `primary_driver.summary` + `feedback.why` |
| Replaced `planner_lessons` with `data_lessons` | Planner removed from pipeline; data lessons cover both "fetch this" and "weight this more" |
| Added `evidence_ledger` with ID refs | Centralized citations, no duplication across driver sections |
| Added `pit_mode`, `pit_cutoff` | Audit: which PIT boundary was enforced |
| Expanded `actual_return` | Added `session_stock_pct`, `daily_macro_pct`, `daily_sector_pct`, `daily_industry_pct` |
| Added `accession_8k` | Direct filing identifier for audit |
| Added `pit_boundary_source` | Audit: which §3 tier determined PIT cutoff (`next_quarter`, `live_cycle`, `invocation_time`) |
| Added `global_observations[]` | Learner writes cross-ticker insights here; Python extracts and appends to `global.json` |
| Write ownership: learner writes only `result.json` | Python orchestrator handles `ticker.json` and `global.json` appends — safer for atomic writes and concurrent ticker processing |
| `predicted_confidence` → `predicted_confidence_score` | Aligned with predictor contract field name `confidence_score` |

---

## 7. Ticker Lessons: `learnings/ticker/{TICKER}.json`

**File path**: `earnings-analysis/learnings/ticker/{TICKER}.json`
**Write mode**: Append-only. The learner does NOT write this file. The orchestrator Python extracts feedback from `attribution/result.json` and atomically appends one entry to the `lessons[]` array.
**Read-time cap**: `build_learning_context()` selects the most recent **8 entries** for predictor context.

### Schema

```json
{
  "schema_version": "ticker_lessons.v1",
  "ticker": "AAPL",
  "updated_at": "2026-04-16T14:30:00-04:00",
  "lessons": [
    {
      "quarter_label": "Q4_FY2024",
      "attributed_at": "2026-03-15T10:00:00-04:00",
      "direction_correct": true,
      "actual_daily_pct": 3.2,
      "predicted_direction": "long",
      "predicted_confidence_score": 65,
      "primary_driver_summary": "Services revenue acceleration + strong iPhone demand",
      "primary_driver_category": "revenue_surprise",
      "what_worked": ["Revenue beat identification", "Services momentum flagged correctly"],
      "what_failed": [],
      "predictor_lessons": ["Services mix shift increasingly drives AAPL reaction — weight segment breakdown higher than hardware revenue"],
      "data_lessons": [],
      "why": "Direction correct. Confidence was conservative — could have been higher given strong Services signal."
    },
    {
      "quarter_label": "Q1_FY2025",
      "attributed_at": "2026-04-16T14:30:00-04:00",
      "direction_correct": false,
      "actual_daily_pct": -5.28,
      "predicted_direction": "long",
      "predicted_confidence_score": 72,
      "primary_driver_summary": "$900M tariff cost warning — first quantification by management",
      "primary_driver_category": "guidance_change",
      "what_worked": ["EPS beat identified from Services momentum"],
      "what_failed": ["Missed tariff cost as primary driver", "Underweighted China deceleration"],
      "predictor_lessons": [
        "When macro trade tensions elevated, weight management cost-impact commentary over EPS beat",
        "China revenue 3-quarter decline is structural — treat as ongoing headwind"
      ],
      "data_lessons": [
        "Fetch sector peer tariff exposure data for context",
        "Weight Transcript Q&A analyst focus areas — 6/10 questions targeted tariff impact"
      ],
      "why": "Tariff magnitude was unknown pre-filing. When macro regime is adversarial, look harder for management cost quantification in forward guidance."
    }
  ]
}
```

### What goes into each entry

Each entry is a compact extract from `attribution/result.json`'s feedback block plus key metadata. It contains exactly the information the predictor needs to learn from this quarter — no evidence ledger, no full analysis. The `primary_driver_category` enables the predictor to see driver-type patterns across quarters (e.g., "guidance_change dominated 3/4 AAPL quarters").

### Lesson refinement

When writing a new entry, the learner reads prior entries and checks:
- Did the predictor follow prior advice? (Compare predicted vs actual against prior predictor_lessons)
- Was prior advice too vague? If so, write a more specific version.
- Was prior advice wrong? If so, explicitly note the correction.

Example refinement:
```
Q3 wrote: "weight China revenue decline"
Q4 predictor still missed China impact
Q4 writes: "China revenue requires 4-quarter trend analysis — deceleration
            from $18B→$17B→$16.4B→$16B shows structural decline, not just
            QoQ miss. Prior lesson was correct but insufficiently specific."
```

---

## 8. Global Lessons: `learnings/global.json`

**File path**: `earnings-analysis/learnings/global.json`
**Write mode**: Append-only. The learner does NOT write this file directly. The orchestrator Python extracts `global_observations[]` from `attribution/result.json`, enriches each entry with `source_ticker`, `quarter_label`, and `attributed_at` from the result metadata, and atomically appends to this file. This prevents data loss from concurrent ticker processing.
**Read-time cap**: `build_learning_context()` selects the most recent **10 entries** filtered by relevance to the current ticker's sector.

### Schema

```json
{
  "schema_version": "global_lessons.v1",
  "updated_at": "2026-04-16T14:30:00-04:00",
  "entries": [
    {
      "scope": "sector",
      "scope_key": "Technology",
      "source_ticker": "AAPL",
      "quarter_label": "Q1_FY2025",
      "attributed_at": "2026-04-16T14:30:00-04:00",
      "lesson": "Tariff cost quantification dominated tech reactions in Q1 FY2025 — management first-time disclosures of cost magnitude were primary drivers across AAPL and MSFT"
    },
    {
      "scope": "macro",
      "scope_key": "trade_tensions",
      "source_ticker": "AAPL",
      "quarter_label": "Q1_FY2025",
      "attributed_at": "2026-04-16T14:30:00-04:00",
      "lesson": "During elevated trade tension regime, forward cost guidance dominates backward-looking EPS beats by ~2x in attribution weight"
    },
    {
      "scope": "cross_ticker",
      "scope_key": "MSFT",
      "source_ticker": "AAPL",
      "quarter_label": "Q1_FY2025",
      "attributed_at": "2026-04-16T14:30:00-04:00",
      "lesson": "MSFT guided cautiously on Azure capex 2 weeks before AAPL's filing — this was a leading signal for AAPL tariff exposure that the predictor missed"
    }
  ]
}
```

### Scope types

| Scope | Purpose | `scope_key` | When to write |
|-------|---------|-------------|---------------|
| `sector` | Sector-wide pattern | Sector name (e.g., "Technology", "Energy") | When the learner identifies a pattern that likely applies to other companies in the same sector |
| `macro` | Macro-regime observation | Regime/indicator label (e.g., "risk_off", "rate_hike", "trade_tensions") | When macro conditions were a significant driver or amplifier |
| `cross_ticker` | Peer/competitor signal | Related ticker symbol | When another company's earnings/news was a leading signal for this ticker |

### Guidelines for global entries

- Write 0-3 global entries per attribution. Most quarters will have 1-2.
- Each entry should be a **generalizable observation**, not ticker-specific detail.
- Do NOT write a global entry if the observation is only relevant to this specific ticker — that belongs in ticker.json.
- Keep `lesson` text concise (1-2 sentences). It's a signal, not an essay.

### Why global.json matters for sequential processing

When processing multiple tickers sequentially, global.json accumulates cross-ticker insights:
```
Process AAPL Q2 → learner writes: "Tech: AI capex concerns dominated Q2 reactions"
Process MSFT Q2 → predictor reads global.json → sees AAPL's sector insight → better informed
```

---

## 9. `build_learning_context()` Adapter

**Location**: `scripts/earnings/earnings_orchestrator.py` (not `builder_adapters.py` — this is a lightweight local file read, not a parallel builder that hits Neo4j/APIs)
**Role**: Read-time compatibility layer that transforms append-only lesson files into predictor-ready compact context.

### Interface

```python
def build_learning_context(ticker: str, sector: str = None,
                           base_dir: Path = None) -> dict:
    """Build learning context for predictor consumption.

    Reads ticker lessons and global lessons, filters by recency and relevance,
    returns compact context suitable for inclusion in the prediction bundle.
    """
```

### Filtering logic

**Ticker lessons** (`learnings/ticker/{TICKER}.json`):
- Read all entries from `lessons[]`
- Select most recent **8 entries** (by `attributed_at`)
- Return as `ticker_lessons[]`

**Global lessons** (`learnings/global.json`):
- Read all entries from `entries[]`
- Filter by relevance:
  - `scope=sector` where `scope_key` matches current ticker's sector → include
  - `scope=macro` → always include (regime matters for all tickers)
  - `scope=cross_ticker` where `scope_key` is a ticker in the same sector → include
- Deduplicate: within each scope, skip entries whose `lesson` text is an exact match after lowercase + whitespace normalization against an already-selected entry (deterministic, no fuzzy/semantic matching needed — per-scope caps handle the rest)
- Per-scope cap: max **4 sector** + **4 macro** + **2 cross_ticker** = **10 entries** total
- Sort by recency within each scope bucket
- Return as `global_lessons[]`

### Output shape

```json
{
  "ticker_lessons": [
    {
      "quarter_label": "Q1_FY2025",
      "direction_correct": false,
      "actual_daily_pct": -5.28,
      "primary_driver_summary": "...",
      "predictor_lessons": ["..."],
      "data_lessons": ["..."],
      "why": "..."
    }
  ],
  "global_lessons": [
    {
      "scope": "sector",
      "scope_key": "Technology",
      "source_ticker": "AAPL",
      "lesson": "..."
    }
  ],
  "ticker_ref": "earnings-analysis/learnings/ticker/AAPL.json",
  "global_ref": "earnings-analysis/learnings/global.json"
}
```

When neither file exists (first-ever ticker prediction), returns:
```json
{
  "ticker_lessons": [],
  "global_lessons": [],
  "ticker_ref": null,
  "global_ref": null
}
```

### Integration with predictor bundle

`BUNDLE_ITEM_ORDER` remains the 7 parallel builders (Neo4j/API). `learning_context` is the logical 8th bundle field, added after builder execution in `build_prediction_bundle()` as a lightweight file read:

```python
# In build_prediction_bundle(), after parallel builders complete:
bundle["learning_context"] = build_learning_context(ticker, sector=sector)
```

Corresponding renderer `_render_learning_context()` formats ticker + global lessons as Section 10 in the prediction bundle text.

---

## 10. Invocation Pattern — LOCKED

### Decision: Skill authored, SDK main-session executed

The learner is **authored** in `.claude/skills/earnings-learner/SKILL.md` but **executed** in a fresh main-session SDK call — not via `/earnings-learner` fork and not as a Task-spawned agent.

**Why this pattern (validated 2026-04-16):**

| Invocation mode | Data SubAgents accessible | Thinking | Verdict |
|---|---|---|---|
| `/earnings-learner` fork (Skill tool) | 6/14 — neo4j-*, yahoo, bz-news-api are agents not skills | Yes | ❌ Missing 8 critical agents |
| Task-spawned agent (Agent tool) | 0/14 — Agent tool absent from all subagent tiers | No | ❌ No spawning, no thinking |
| **SDK embed (main session)** | **14/14** — Agent tool available (27 built-in tools) | **Yes** (via prompt + SDK options) | ✅ **Production path** |

**How it works:**

```python
# _run_learner_via_sdk() in earnings_orchestrator.py
learner_instructions = load_skill_content("earnings-learner")  # reads SKILL.md, strips frontmatter
prompt = f"{learner_instructions}\n\n--- INPUTS ---\n{assembled_inputs}"

async for msg in query(
    prompt=prompt,
    options=ClaudeAgentOptions(
        model="claude-opus-4-6",           # full model ID (not short "opus")
        effort="high",                      # reasoning depth
        thinking={"type": "adaptive"},      # Claude decides when to use extended thinking
        setting_sources=["project"],        # load project settings (MCP servers, hooks)
        permission_mode="bypassPermissions",
        max_turns=50,                       # safety guardrail, not a target
    ),
):
    ...
```

All SDK options verified against installed `claude_agent_sdk==0.1.44` (2026-04-16). The prompt body should also include "ultrathink" as a belt-and-suspenders instruction alongside the SDK `effort`/`thinking` parameters.

**Model ID pinning (not "latest" aliases)**: The SDK does NOT accept `"opus"` or `"claude-opus-latest"` for `ClaudeAgentOptions.model` — only full version IDs like `"claude-opus-4-7"`. Production code pins to a specific version. Rationale: (1) **audit trail** — the `model_version` field in attribution/result.json records exactly which model produced each lesson; (2) **U1 loop integrity** — silently swapping models mid-loop breaks lesson-chain attribution; (3) **validator stability** — new models may shift JSON shapes, and pinning means breakage is caught at version-bump time, not silently. When a new Opus ships, update `PREDICTOR_MODEL_ID` constant and the learner `model=` string (two-line change).

This is operationally similar to the predictor SDK path but NOT the same runtime path. The predictor uses `"Run /earnings-prediction ..."` which triggers a Skill tool fork (14 tools, sufficient for read-bundle-write-result). The learner embeds SKILL.md content directly as prompt text, staying in the main session with full tools (27 built-in + MCP), enabling Agent tool access for all 14 Data SubAgents.

### Critical caveat: frontmatter is documentation, not runtime enforcement

Because the SKILL.md content is embedded as prompt text (not invoked via Skill tool), **frontmatter fields are not processed at runtime**:

| Frontmatter field | Runtime effect | Replacement |
|---|---|---|
| `model: opus` | None | `ClaudeAgentOptions(model="claude-opus-4-6")` — full model ID required, not short alias |
| `effort: high` | None | `ClaudeAgentOptions(effort="high", thinking={"type": "adaptive"})` + "ultrathink" in prompt body |
| `context: fork` | None (runs as main session) | This is the desired behavior |
| `allowed-tools` | None | Main session has all tools; no restriction needed |
| `skills:` | Not auto-loaded | Data SubAgents load their own skills when spawned |
| Skill-scoped hooks | Don't fire | Global hooks (pit_gate.py, PreToolUse Write validation) fire normally |

The SKILL.md frontmatter serves as **documentation of intent** (model, effort level, tools needed) even though Python SDK options are the actual enforcement mechanism. Global hooks in `settings.json` remain the validation boundary.

### Data SubAgent access from main session

The learner spawns Data SubAgents via Agent tool in the main session. Each agent (`.claude/agents/*.md`) loads its own skills, hooks, and PIT infrastructure. No wrapper skills or agent modifications needed — the existing 14 agents work as-is:

- 6 Neo4j agents: `neo4j-report`, `neo4j-transcript`, `neo4j-xbrl`, `neo4j-news`, `neo4j-entity`, `neo4j-vector-search`
- 3 external API agents: `alphavantage-earnings`, `yahoo-earnings`, `bz-news-api`
- 5 Perplexity agents: `perplexity-ask`, `perplexity-search`, `perplexity-reason`, `perplexity-research`, `perplexity-sec`

### Dev testing note

SDK sessions cannot nest inside Claude Code sessions (`CLAUDECODE` env var check). Production runs from cron/daemon/terminal (no issue). For dev testing from within Claude Code: `! unset CLAUDECODE && python3 scripts/run_learner.py AAPL Q1_FY2025`

### Write ownership model

The learner writes **only** `attribution/result.json`. The orchestrator Python handles all derived writes:

1. **Learner** writes `attribution/result.json` (validated by PreToolUse Write hook before disk write)
2. **Python** reads result.json after learner returns → validates schema
3. **Python** extracts `feedback` block + metadata → atomic append to `learnings/ticker/{TICKER}.json`
4. **Python** extracts `global_observations[]` → atomic append to `learnings/global.json`

This separation ensures: atomic file operations, safe concurrent ticker processing (global.json), simpler learner prompt (no file I/O instructions), and keeps the Skill vs Agent decision independent of file management.

**Completion semantics (happy path)**: When the learner produces valid output, a quarter is learner-complete only after: (1) `attribution/result.json` is validated, AND (2) ticker.json append succeeds, AND (3) global.json append succeeds. The next quarter's prediction must not proceed until all three are confirmed — otherwise lessons are "written" but not actually available. If a derived write fails (e.g., ticker.json append), retry the append (not the full learner) — the valid result.json is the source of truth.

**Completion semantics (failure path)**: If the learner itself fails (no valid result.json after one retry), the historical failure policy in §2 applies: the ticker's sequential processing stops at this quarter. The failure is logged. Re-bootstrap after investigation.

**Atomic append pattern**: `fcntl.flock()` exclusive lock + write to temp file + `os.replace()`. Required for `global.json` (concurrent ticker processing). Recommended for `ticker.json` (crash safety, no concurrency risk for single-ticker sequential processing).

### Validation strategy regardless of choice

**Layer 3 — PreToolUse Write hook** (works for both Skill and Agent):
Validates `attribution/result.json` JSON before disk write. Checks:
- JSON parseable
- All required fields present
- `feedback` block has all 6 sub-fields
- Array caps respected (what_worked ≤ 2, what_failed ≤ 3, predictor_lessons ≤ 3, data_lessons ≤ 3)
- `missing_inputs` is an array
- `evidence_ledger` is non-empty and all driver `evidence_refs` resolve to ledger IDs
- `global_observations` array present (may be empty)

**Post-return validation** (orchestrator Python):
After learner returns, orchestrator checks:
- `attribution/result.json` exists at expected path
- JSON valid and schema matches
- If validation fails: log warning, re-invoke with corrective prompt (max 1 retry). If still invalid, stop ticker's bootstrap per §2 historical failure policy

### Max turns guardrail

Set `max_turns: 50` as a guardrail. This is a safety cap, not a target. The learner should use as many turns as needed (typically 15-30) and stop when confident, well before the cap.

---

## 11. What to Reuse from Old Attribution Skill

**Borrow (reasoning quality)**:
- Evidence-based methodology: every claim must cite source → retained as `evidence_ledger` with ID refs
- Data inventory first: know what data exists before making claims → retained as investigation step 1
- Source priority hierarchy: primary filings > transcript > official news > analyst coverage > general news → guidance for causal weight
- Conflict resolution: note conflicts explicitly rather than silently choosing → retained as principle
- Neo4j subagent spawning patterns: parallel fetch, PIT-aware, resume for follow-up → retained

**Discard (stale contract)**:
- Markdown report output → replaced by JSON-first `attribution/result.json`
- `subagent-history.csv` tracking → no longer needed
- `predictions.csv` / `8k_fact_universe.csv` tracking → no longer needed
- Step 10 (mark completed in CSV) → orchestrator handles completion tracking
- Step 11 (Obsidian thinking index build) → out of scope
- `learnings.md` per-company file → replaced by `learnings/ticker/{TICKER}.json`
- Pattern-matching categories (Beat-and-Raise, etc.) → derived from evidence, not pre-defined
- Surprise calculation formulas → predictor already handles; learner does causal attribution
- Human-readable confidence assessment section → replaced by `feedback.why` + lesson quality

---

## 12. Dependencies (NOT in learner scope)

These must exist for the learner to function but are built elsewhere:

| Dependency | Owner | Status |
|------------|-------|--------|
| Sequential quarter processing (Q(n) before Q(n+1)) | Orchestrator SKILL.md / earnings_orchestrator.py | **Not implemented** — orchestrator handles one quarter via CLI |
| `is_historical_done()` deferred learner check | Trigger daemon (EarningsTrigger.md) | **Not implemented** — pseudocode only. Note: daemon must distinguish "daily_stock not settled yet" (learner ineligible) from "daily_stock exists, learner eligible but missing" (enqueue historical) to avoid pointless re-enqueues |
| Guidance gate for historical bootstrap | Trigger daemon | **Not implemented** — pseudocode only |
| `get_quarterly_filings()` returning filed_8k timestamps | `scripts/get_quarterly_filings.py` | **Implemented** |
| PIT gate + fetch infrastructure | `pit_gate.py`, `pit_fetch.py` | **Implemented** |
| Neo4j Data SubAgents | `.claude/agents/neo4j-*.md` | **Implemented** |
| External API Data SubAgents | alphavantage, yahoo, bz-news-api agents | **Implemented** |
| prediction/result.json written by predictor | earnings-prediction skill | **Implemented** |
| PUBLISHED_AS return data on 8-K reports | Neo4j ingestion pipeline | **Implemented** |

---

## 13. Implementation Checklist

### Phase 1: Learner Contract

- [ ] Create `.claude/skills/earnings-learner/SKILL.md` — compact prompt with 5-phase workflow, evidence rules, generalizability guardrail. Frontmatter documents intent (`model: opus`, `effort: high`) but is not runtime enforcement (§10). **⚠️ HUMAN REVIEW GATE — every line must be approved before proceeding**
- [ ] Add `get_attribution_paths()` and learning-file path helpers in `earnings_orchestrator.py` (deterministic result locations from day one)
- [ ] Add `validate_attribution_result()` in Python — canonical schema check (required fields, feedback sub-fields, array caps, evidence_refs resolution, non-empty evidence_ledger). The PreToolUse hook mirrors this contract
- [ ] Create PreToolUse validation hook for `attribution/result.json` writes (shell script calling the same checks)
- [ ] Create `_run_learner_via_sdk()` in `earnings_orchestrator.py` — loads SKILL.md content, strips frontmatter, embeds as prompt text with runtime inputs, invokes via SDK with `model="claude-opus-4-6"`, `effort="high"`, `thinking={"type": "adaptive"}`, `max_turns=50`

### Phase 2: Lesson Infrastructure

- [x] Create `earnings-analysis/learnings/` directory structure
- [x] Implement ticker.json atomic append in `earnings_orchestrator.py` (extract feedback, temp file + `os.replace` — no flock needed, single-ticker sequential)
- [x] Implement global.json atomic append in `earnings_orchestrator.py` (extract global_observations, enrich metadata, `fcntl.flock` + atomic write for concurrency safety)
- [x] Add `build_learning_context()` in `earnings_orchestrator.py` (lightweight file read, not in `builder_adapters.py` — no external deps). Per-scope caps, exact-text dedupe, quarter_label dedupe for rerun idempotency
- [x] Add `_render_learning_context()` in `earnings_orchestrator.py`
- [x] Wire `learning_context` as logical 8th bundle field in `build_prediction_bundle()` (post-build, not in `BUNDLE_ITEM_ORDER` which stays at 7 parallel builders)

### Phase 3: Orchestrator Inputs + Integration

- [x] Add `derive_learner_pit()`: three-tier PIT rule (next_quarter → live_cycle → invocation_time). Verified on 11 AAPL quarters. **⚠️ HUMAN REVIEW GATE — must verify correctness across all tickers**
- [x] Add `normalize_actual_return()` + `fetch_actual_return()`: Neo4j PUBLISHED_AS query + field name mapping to `_pct` suffix + daily_stock hard gate
- [x] Add `run_learner_for_quarter()`: full pipeline with hard gates, PIT derivation, existing-result recovery (derived-write recovery before Neo4j fetch), SDK invocation, post-return validation (1 retry), ticker+global lesson appends
- [x] Add `--learn` CLI flag to `main()` — single-quarter learner invocation (loads event.json for PIT derivation)
- [x] Update orchestrator SKILL.md invariants to reflect derived-write recovery behavior

### Pending (separate from Phase 3)

- [ ] Wire deferred learner detection in trigger daemon (`is_historical_done()` checks attribution/result.json existence)

### Phase 4: Calibration — **⚠️ HUMAN REVIEW GATE**

Manual single-quarter runs via CLI: `python3 scripts/earnings/earnings_orchestrator.py TICKER ACCESSION --save --predict --learn`. Full sequential automation is pending (daemon, §12).

**Sequential execution is REQUIRED for calibration**: Quarters must run one-at-a-time in chronological order (Q1 → Q2 → Q3 → …). This is not optional — each quarter's learner writes lessons that the NEXT quarter's predictor reads via `learning_context`. Running in parallel or out of order breaks the U1 loop (Q(n) predictor would miss Q(n-1)'s lessons). For a batch run, shell-chain commands: `cmd1 && cmd2 && cmd3` (AND-chain so a failure stops the chain). Never `&` (background) or multi-terminal parallel runs.

**Progress (AVGO sequential calibration, 2026-04-16):**
- Q1_FY2023: learner-only (legacy prediction), schema-valid, primary_driver=`ai_narrative_rerating`, direction_correct=False. Uncovered real predictor data-freshness bug via investigation.
- Q2_FY2023: **first clean full-pipeline end-to-end success.** Bundle 7/7, predict+learn via SDK on Opus 4.7, predictor validation passed, learner validation passed, U1 loop verified (Q1 lesson flowed into Q2 bundle, Q2 direction_correct=True, magnitude_error=0.0 with actual inside predicted range).

- [ ] Run learner on 3-5 historical quarters for one ticker
- [ ] Verify lesson quality — learner uses full evidence surface and produces reusable high-signal guidance, not quarter-specific summaries
- [ ] Verify PIT enforcement (no post-boundary evidence in historical runs)
- [ ] Verify `build_learning_context()` produces useful predictor context
- [ ] Run predictor WITH lessons vs WITHOUT — compare prediction quality

---

## Appendix: Canonical Filing Structure

```
earnings-analysis/
  Companies/
    AAPL/
      events/
        event.json                          ← rebuilt by get_quarterly_filings
        Q1_FY2025/
          prediction/
            context_bundle.json             ← predictor input bundle
            result.json                     ← predictor output
          attribution/
            result.json                     ← LEARNER OUTPUT (this plan)
        Q2_FY2025/
          ...
  learnings/
    ticker/
      AAPL.json                             ← TICKER LESSONS (this plan)
      MSFT.json
    global.json                             ← GLOBAL LESSONS (this plan)
```
