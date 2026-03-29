# Prediction System v2 — Baseline Design

**Created**: 2026-03-27
**Status**: BASELINE — approved for refinement
**Supersedes**: `earnings-orchestrator.md` (architecture only — schemas carried forward)

---

## 0. Design Principles

1. If a component does not clearly improve speed, required coverage, or calibration — delete it.
2. If a component can be deterministic code instead of LLM judgment — make it code.
3. Preload all 9 bundle items for now. Prune later by evidence — only drop items that calibration proves useless.
4. The planner is gone forever. Python builders replace it.
5. Start with this baseline. Improve iteratively. Only add complexity if outsized benefit.

---

## 1. Architecture Overview

```
TWO LLM COMPONENTS (irreducible):
  Predictor — Opus ultrathink, receives bundle, may ask one round of questions
  Learner   — Opus ultrathink + MCP tools, post-event causal analysis

EVERYTHING ELSE IS PYTHON:
  earnings_orchestrator.py — pipeline coordination, bundle assembly, SDK invocation
  earnings_trigger_daemon.py — 8-K detection, queue management (unchanged)
  9 builder functions — deterministic data assembly (Neo4j queries + API calls)
```

```
ON 8-K TRIGGER:
  earnings_orchestrator.py
    → Run 9 builders in parallel           (~15-20s, always fresh)
    → Merge → prediction_bundle            (~0s)
    → Invoke Predictor via SDK             (~60s typical, ~110s if questions)
    → Validate + write result.json         (~0s)
    TOTAL: ~75-130 seconds

DEFERRED:
  Learner via SDK                          (~5-10 min)
    → attribution/result.json with lessons
    → U1 feeds next cycle
```

**No pre-warming**. The 9 builders are Python functions (Neo4j queries + API calls). Run in parallel, they take ~15-20s. Pre-warming would save ~15s but add a cron job, per-ticker cache files, staleness management, and stale data risk. 75s is well within the actionable window (markets take 5-30 min to digest earnings). Always-fresh data, zero infrastructure. If rate limits bite during earnings season peaks, add selective API response caching inside the affected builder (~10 lines), not a separate system.

---

## 2. Components

### 2a. Bundle Assembly (build fresh at trigger time)

No pre-warming. The orchestrator runs all 9 builders in parallel at trigger time. Always fresh, zero infrastructure.

```python
from builder_adapters import (
    build_8k_packet, build_guidance_history, build_inter_quarter_context,
    build_peer_earnings_snapshot, build_macro_snapshot, build_consensus,
    build_prior_financials,
)

def build_prediction_bundle(ticker, quarter_info, pit_cutoff=None):
    """Assemble full 9-item bundle via standardized adapters.

    All adapters share one signature: build_X(ticker, quarter_info, pit_cutoff=None, out_path=None)
    pit_cutoff: None=live (unrestricted), str=historical (PIT-gated).
    """
    run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    def out(name): return f"/tmp/earnings/{run_id}/{name}.json"

    with ThreadPoolExecutor(max_workers=9) as pool:
        futures = {
            "8k_packet":                 pool.submit(build_8k_packet, ticker, quarter_info, pit_cutoff, out("8k_packet")),
            "guidance_history":          pool.submit(build_guidance_history, ticker, quarter_info, pit_cutoff, out("guidance_history")),
            "inter_quarter_context":     pool.submit(build_inter_quarter_context, ticker, quarter_info, pit_cutoff, out("inter_quarter_context")),
            "peer_earnings_snapshot":    pool.submit(build_peer_earnings_snapshot, ticker, quarter_info, pit_cutoff, out("peer_earnings_snapshot")),
            "macro_snapshot":            pool.submit(build_macro_snapshot, ticker, quarter_info, pit_cutoff, out("macro_snapshot")),
            "consensus":                 pool.submit(build_consensus, ticker, quarter_info, pit_cutoff, out("consensus")),
            "previous_earnings":         pool.submit(build_previous_earnings, ticker, quarter_info, pit_cutoff, out("previous_earnings")),
            "previous_earnings_lessons": pool.submit(build_previous_earnings_lessons, ticker, quarter_info, pit_cutoff, out("previous_earnings_lessons")),
            "prior_financials":          pool.submit(build_prior_financials, ticker, quarter_info, pit_cutoff, out("prior_financials")),
        }
        bundle = {k: f.result() for k, f in futures.items()}

    bundle["schema_version"] = "prediction_bundle.v1"
    bundle["ticker"] = ticker
    bundle["assembled_at"] = now_iso()
    return bundle
```

**Standardized adapter contract** (implemented in `scripts/earnings/builder_adapters.py`):
- All 7 built adapters share: `build_X(ticker, quarter_info, pit_cutoff=None, out_path=None, **kwargs) → dict`
- `pit_cutoff=None` = live (unrestricted). `pit_cutoff=str` = historical (PIT-gated).
- `source_mode` derived internally (`"historical" if pit_cutoff else "live"`), not passed.
- Output packet always includes: `schema_version`, `ticker`, `pit_cutoff`, `effective_cutoff_ts`, `source_mode`, `assembled_at`.
- Enriched packet written to disk AND returned in-memory.
- Stdout suppressed via thread-safe `_SuppressStdout` (reference-counted).

**Builder inventory**:

| # | Item | Builder | Location | Adapter | Status |
|---|------|---------|----------|---------|--------|
| 1 | 8k_packet | `build_8k_packet()` | `warmup_cache.py:463` | `builder_adapters.py` | DONE + STANDARDIZED |
| 2 | guidance_history | `build_guidance_history()` | `warmup_cache.py:701` | `builder_adapters.py` | DONE + STANDARDIZED |
| 3 | inter_quarter_context | `build_inter_quarter_context()` | `warmup_cache.py:1472` | `builder_adapters.py` | DONE + STANDARDIZED |
| 4 | peer_earnings_snapshot | `build_peer_earnings_snapshot()` | `scripts/earnings/peer_earnings_snapshot.py:154` | `builder_adapters.py` | DONE + STANDARDIZED |
| 5 | macro_snapshot | `build_macro_snapshot()` | `scripts/earnings/macro_snapshot.py:384` | `builder_adapters.py` | DONE + STANDARDIZED |
| 6 | consensus | `build_consensus()` | `scripts/earnings/build_consensus.py` | `builder_adapters.py` | DONE + STANDARDIZED |
| 7 | previous_earnings | `build_previous_earnings()` | — | — | NOT BUILT |
| 8 | previous_earnings_lessons | `build_previous_earnings_lessons()` | — | — | NOT BUILT (stub `[]`) |
| 9 | prior_financials | `build_prior_financials()` | `scripts/earnings/build_prior_financials.py` | `builder_adapters.py` | DONE + STANDARDIZED |

**Builder contract (LOCKED)**:
- Every adapter returns a **packet dict** with: `schema_version`, `ticker`, `pit_cutoff`, `effective_cutoff_ts`, `source_mode`, `assembled_at`, and the data payload.
- Every adapter accepts: `build_X(ticker, quarter_info, pit_cutoff=None, out_path=None, **kwargs)`.
- `pit_cutoff=None` = live (unrestricted). `pit_cutoff=str` = historical (PIT-gated).
- Native builders (Phase 4): all 7 now return packet dicts, no sys.exit, no stdout noise.
- Every adapter accepts `out_path` to persist the enriched packet for audit.
- Per-item metadata enables packet-level freshness tracking without a monolithic cache file.
- Enriched packets include `pit_cutoff`, `effective_cutoff_ts`, `source_mode` on disk AND in memory.

**Rate-limit note**: Most builders hit Neo4j (local, unlimited, fast). `consensus` (6) calls AlphaVantage (rate-limited, 1-2 calls per ticker). Live predictions are queued (one at a time), so no burst risk. If rate limits bite during peak earnings season, add response caching with TTL inside the builder (~10 lines).

### 2b. Python Orchestrator

**File**: `scripts/earnings/earnings_orchestrator.py`
**Invoked by**: Trigger daemon (live) or CLI (historical)
**Language**: Pure Python. Calls LLM components via Claude Agent SDK.

**Responsibilities**:
1. Run 9 builders in parallel → assemble prediction bundle
2. Invoke predictor via SDK
3. Handle one round of questions (if predictor asks)
4. Validate prediction output (deterministic rules)
5. Write prediction/result.json
6. For historical: invoke learner, process quarters sequentially
7. For live: write live_state.json, learner is deferred

**NOT its job**: LLM reasoning, data interpretation, fetch plan generation.

### 2c. Predictor

**Invocation**: Claude Agent SDK, `model='claude-opus-4-6'`, ultrathink.
**Input**: Rendered prediction bundle (9 items as sectioned text).
**Output**: `prediction_result.v1` JSON (schema carried from `earnings-orchestrator.md §2c`).

**Behavior**:
- Receives full 9-item bundle.
- Reasons through evidence using extended thinking.
- Outputs prediction directly (most cases, ~60s).
- MAY output structured questions instead (rare, <20% of cases). See §4.
- Always records identified gaps in `data_gaps`.

**One round of questions** (§4):
- If the predictor identifies a CRITICAL gap that would likely change its direction call, it may output questions instead of a prediction.
- Questions are structured JSON: `[{"agent": "...", "query": "..."}]`
- Max 3 questions.
- Orchestrator fetches answers in parallel via data agents.
- Predictor receives bundle + answers in a second SDK call → outputs prediction.
- Total with questions: ~90-120s. Without: ~60s.

**Why not give the predictor direct tool access**: Keeps the fast path clean (~60s single turn). Tool access risks the predictor calling tools unnecessarily on every prediction. The two-call pattern only adds overhead when questions are actually needed.

### 2d. Learner

**Invocation**: Claude Agent SDK, `model='claude-opus-4-6'`, ultrathink + MCP tools.
**When**: Historical = same-run (after prediction). Live = deferred to next historical bootstrap.
**Time budget**: 5-10 minutes. No speed constraint.

**Input**:
1. prediction/result.json (what was predicted)
2. The full prediction bundle the predictor received (what it saw)
3. Any supplementary answers (if predictor asked questions)
4. Actual returns (daily_stock, hourly_stock)

**Output**: `attribution_result.v1` JSON with embedded feedback block.

**Feedback block (simple list for v1)**:

```json
{
  "feedback": {
    "prediction_comparison": {
      "predicted_signal": "strong_long",
      "actual_move_pct": -2.1,
      "correct": false
    },
    "what_worked": ["..."],
    "what_failed": ["..."],
    "why": "...",
    "predictor_lessons": ["..."],
    "data_coverage_lessons": ["..."]
  }
}
```

**Key rename**: `planner_lessons` → `data_coverage_lessons`. There is no planner. These lessons identify gaps in the prediction bundle that affected prediction quality. A human reviews them periodically and updates builder functions.

**Learner data access**: Has MCP tools available (neo4j-cypher, yahoo-finance, etc.) for post-event investigation. Fetches transcripts, 10-Q, analyst reactions autonomously. No PIT gate (post-event, uses all available data).

**Output validation**: Learner returns JSON only. Python orchestrator validates schema and writes attribution/result.json. No hooks — all validation in Python.

### 2e. Trigger Daemon (unchanged)

Same as `EarningsTrigger.md`. Detects 8-Ks, manages historical/live queues. **One change needed**: invocation wiring — the daemon currently enqueues SDK calls to `/earnings-orchestrator` (Claude Code skill). Must be updated to invoke `earnings_orchestrator.py` (Python script) instead. Detection and queue logic unchanged.

---

## 3. The 9-Item Prediction Bundle

| # | Item | Source | What It Provides | Usually Decisive? |
|---|------|--------|-------------------|-------------------|
| 1 | 8k_packet | `build_8k_packet()` | Current quarter earnings results, new guidance, commentary | Yes (trigger) |
| 2 | guidance_history | `build_guidance_history()` | Company guidance trajectory across quarters | Yes (~60-70%) |
| 3 | inter_quarter_context | `build_inter_quarter_context()` | Timeline of events between earnings (news, filings, analyst actions, significant moves) | Partial |
| 4 | peer_earnings_snapshot | `build_peer_earnings_snapshot()` | Sector peer results and reactions | Occasional |
| 5 | macro_snapshot | `build_macro_snapshot()` | Macro environment context | Rare at company level |
| 6 | consensus | `build_consensus()` | EPS + revenue analyst expectations, revision history | Yes (~60-70%) |
| 7 | previous_earnings | `build_previous_earnings()` | Prior quarter's complete earnings picture (results, surprise, guidance, reaction) | Moderate |
| 8 | previous_earnings_lessons | `build_previous_earnings_lessons()` | U1 feedback from prior learner output | Yes (improvement loop) |
| 9 | prior_financials | `build_prior_financials()` | Multi-quarter financial metrics (EPS, revenue, margins) for trend analysis | Moderate |

**Baseline decision**: Include ALL 9 items. The builders are Python (fast, deterministic). Run in parallel at trigger time (~15-20s). More signal with comprehensive context. Prune later if items prove useless through calibration.

**Calibration stats**: DEFERRED. Could anchor the predictor before the core system is proven. Add back later if it clearly helps calibration.

---

## 4. One Round of Questions — Design

The predictor receives the full 9-item bundle. Most of the time, this is sufficient.

For ~20% of cases (unusual 8-K content, novel situations), the predictor may identify a critical gap. Instead of degrading the prediction, it can ask for specific additional data.

### Protocol

```
TURN 1:
  Predictor receives: full bundle
  Predictor outputs:  prediction_result.v1 JSON
                      OR
                      {"needs_more_data": true, "questions": [...]}

IF QUESTIONS:
  Orchestrator: fetches answers in parallel via data agents

  TURN 2:
  Predictor receives: full bundle + supplementary answers
  Predictor outputs:  prediction_result.v1 JSON (must predict, no more questions)
```

### Question format

```json
{
  "needs_more_data": true,
  "reasoning": "8-K mentions cRPO of $51B but bundle lacks cRPO consensus",
  "questions": [
    {
      "agent": "neo4j-transcript",
      "query": "Get Q&A exchanges about cRPO from CRM's prior earnings call"
    },
    {
      "agent": "perplexity-ask",
      "query": "What was the street consensus for CRM cRPO Q1 FY2026?"
    }
  ]
}
```

### Rules

1. Max 3 questions per round.
2. Max 1 round (no iterative back-and-forth).
3. Questions only when the gap would LIKELY change the direction call.
4. Turn 2 MUST output a prediction (no more questions).
5. If the predictor doesn't need more data, it predicts directly in Turn 1 (~60s).
6. Valid `agent` values (hot-path whitelist — smaller than the full 14-agent catalog): `neo4j-report`, `neo4j-transcript`, `neo4j-xbrl`, `neo4j-news`, `alphavantage-earnings`, `perplexity-ask`, `perplexity-search`. One round is only safe if the surface area is tight.
7. PIT enforcement: orchestrator appends `--pit` to agent queries in historical mode.
8. Questions and answers are persisted in `prediction/supplementary.json` for audit.

### Speed budget

| Path | Time |
|------|------|
| No questions (typical) | ~60s |
| With questions | ~15s (Turn 1 analysis) + ~20s (parallel fetch) + ~60s (Turn 2 prediction) = ~95s |

---

## 5. Live Mode Flow

```python
# Step 1: Trigger daemon detects 8-K → enqueues LIVE

# Step 2: Orchestrator picks up job
async def run_live(ticker, accession):
    # Derive quarter identity from 8-K metadata (period_of_report + fiscal calendar)
    # The orchestrator owns this — same logic as get_quarterly_filings.py
    quarter_info = derive_quarter_from_accession(ticker, accession)

    # Build fresh bundle — all 9 items in parallel (~15-20s)
    bundle = build_prediction_bundle(ticker, accession, quarter_info)

    # Invoke predictor (Turn 1)
    result = await invoke_predictor(bundle)

    # Handle one round of questions if needed
    if result.get('needs_more_data'):
        answers = await fetch_parallel(result['questions'])
        result = await invoke_predictor(bundle, supplementary=answers)

    # Validate + write
    validate_prediction(result)
    write_result(ticker, quarter_info.label, result)
    write_live_state(ticker, accession, quarter_info.label, result)

    # Learner deferred to next historical bootstrap
```

---

## 6. Historical Mode Flow

```python
async def run_historical(ticker):
    quarters = get_quarterly_filings(ticker)  # chronological

    for quarter in quarters:
        if prediction_exists(ticker, quarter):
            if not attribution_exists(ticker, quarter):
                # Deferred learner from prior live cycle — run now
                await run_learner(ticker, quarter)
            continue

        # Build fresh bundle with PIT gate — all 9 items in parallel
        bundle = build_prediction_bundle(
            ticker, quarter.accession, quarter, as_of_ts=quarter.filed_8k
        )

        # Predict (with optional questions)
        result = await invoke_predictor(bundle)
        if result.get('needs_more_data'):
            answers = await fetch_parallel(result['questions'], as_of_ts=quarter.filed_8k)
            result = await invoke_predictor(bundle, supplementary=answers)

        validate_prediction(result)
        write_result(ticker, quarter.label, result)

        # Learn immediately (data exists, sequential for U1)
        await run_learner(ticker, quarter)
        # → U1 now available for next quarter
```

---

## 7. Learner Design

```python
async def run_learner(ticker, quarter):
    # Assemble learner input
    prediction = read_result(ticker, quarter)
    bundle = read_context_bundle(ticker, quarter)
    supplementary = read_supplementary(ticker, quarter)  # may be None
    actual = get_actual_returns(ticker, quarter)

    if not prediction or not actual.get('daily_stock'):
        log_error(f"Cannot learn: missing prediction or daily_stock for {ticker} {quarter}")
        return

    # Invoke learner with thinking + MCP tools
    attribution = await sdk_query(
        prompt=render_learner_prompt(prediction, bundle, supplementary, actual),
        model='claude-opus-4-6',
        tools=MCP_TOOLS,  # neo4j-cypher, yahoo-finance, etc.
        permission_mode='bypassPermissions',
    )

    validate_attribution(attribution)
    write_attribution(ticker, quarter, attribution)
```

### Learner output — simple lessons (v1)

The feedback block produces simple, actionable lists:

```json
{
  "feedback": {
    "prediction_comparison": {
      "predicted_signal": "strong_long",
      "predicted_direction": "long",
      "predicted_confidence_score": 68,
      "actual_move_pct": -2.1,
      "correct": false
    },
    "what_worked": [
      "Correctly identified EPS beat magnitude"
    ],
    "what_failed": [
      "Over-weighted EPS surprise, missed guidance cut as primary mover"
    ],
    "why": "Guidance cut dominated. Management lowered FY25 from $6.80-$7.40 to $6.00-$6.50.",
    "predictor_lessons": [
      "Weight guidance direction higher than EPS surprise when guidance revision is >5%"
    ],
    "data_coverage_lessons": [
      "Bundle lacked sector peer earnings — XOM/CVX headwind was a contributing factor"
    ]
  }
}
```

**Caps**: what_worked ≤ 2, what_failed ≤ 3, predictor_lessons ≤ 3, data_coverage_lessons ≤ 3.

**`data_coverage_lessons`**: Replaces the old `planner_lessons`. Identifies gaps in the 9-item bundle. A human reviews these periodically and updates builder functions. For now, no auto-update — lessons are advisory.

**`predictor_lessons`**: Reasoning improvement hints. Fed back to the predictor as part of `previous_earnings_lessons` in the next cycle's bundle.

---

## 8. File Layout

```
earnings-analysis/Companies/{TICKER}/
  events/
    event.json                             ← rebuilt each historical run
    live_state.json                        ← written by orchestrator in live mode
    {quarter_label}/
      prediction/
        context_bundle.json                ← the 9-item bundle the predictor received
        supplementary.json                 ← answers to predictor questions (if any)
        result.json                        ← prediction output (existence = done)
      attribution/
        result.json                        ← learner output with feedback block
```

**State policy**: File-authoritative. `result.json` existence = step complete. Crash mid-quarter → next run re-processes from scratch. Atomic writes (temp + rename).

---

## 9. Schemas Carried Forward

The following schemas from `earnings-orchestrator.md` are adopted unchanged:

- **`prediction_result.v1`** (§2c): direction, confidence_score, confidence_bucket, expected_move_range_pct, magnitude_bucket, horizon, signal, key_drivers, data_gaps, analysis
- **`attribution_result.v1`** (§2d): actual_return, primary_driver, contributing_factors, surprise_analysis, analysis_summary, missing_inputs, feedback block
- **Deterministic rules** (§2c): confidence_score → bucket, signal derivation from (direction, confidence_bucket, magnitude_bucket), magnitude thresholds (<2%/2-4%/4%+)
- **Missing-data policy** (§2c): hard fail if 8-K missing; directional calls need ≥1 anchor (consensus or guidance); both missing → hold+low

---

## 10. What's Deferred (v2+)

| Feature | Why Deferred |
|---|---|
| Earnings call transcript as 10th bundle item | Available ~90min after 8-K. Would require two-stage prediction or slower pipeline. #1 accuracy improvement for v2. |
| Multi-model learner (Claude + OpenAI) | Prove single model works first. |
| Auto-update templates from data_coverage_lessons | Manual review is fine for v1. Auto-update risks bad queries accumulating. |
| Judge component | U1 + calibration stats handle systematic bias. |
| Cross-ticker U1 sharing | Per-ticker lessons sufficient for v1. |
| Data agents → Python functions | Agents work, tested, PIT-compliant. Future speed optimization for historical batch. |
| Per-ticker volatility-adjusted magnitude thresholds | Fixed thresholds for v1. Recalibrate from backtest data. |
| Parallel predictions across tickers | Trigger daemon already handles this (separate queue entries). Not an orchestrator concern. |

---

## 11. What Changed From v1 Design

| Component | v1 (earnings-orchestrator.md) | v2 (this doc) |
|---|---|---|
| Planner | Forked skill (LLM, single-turn) | **DELETED** — Python builders replace it |
| Orchestrator | Claude Code skill | **Python script** via SDK |
| Data fetch | Orchestrator executes planner's fetch plan via Task sub-agents | **9 Python builders** run in parallel at trigger time |
| Predictor | Forked skill, bundle-only, no questions | **SDK-invoked**, bundle-only + optional one round of questions |
| Learner | Task-spawned agent (no thinking) | **SDK-invoked** with ultrathink + MCP tools |
| Analyst notes | Planned (TODO in predictor.md) | **DELETED** — predictor prompt handles multi-dimensional reasoning |
| Bundle items | Planner decides per quarter | **Fixed 9 items**, comprehensive by default |
| planner_lessons | Planner-targeted feedback | **data_coverage_lessons** — bundle gap feedback |
| Warm bundle | N/A | **EVALUATED AND REJECTED** — build fresh at trigger time instead |

---

## 12. Implementation Order

1. ~~**Build remaining 4 builders**~~: ~~consensus~~, ~~prior_financials~~ DONE. **previous_earnings + previous_earnings_lessons (stub)** remaining.
2. ~~**Standardize builder interfaces**~~: DONE (2026-03-29). Adapter layer + Phase 4 native cleanup. See `builder-standardisation.md`.
3. **Build earnings_orchestrator.py**: Python pipeline — run builders in parallel via adapters, invoke predictor via SDK, handle questions, validate, write
4. **Write predictor prompt**: render 9-item bundle as sectioned text + prediction instructions + question protocol
5. **Write learner prompt**: render inputs + investigation instructions + simple lesson format
6. **Historical backtest**: run on 3-5 tickers to calibrate
7. **Integrate with trigger daemon**: wire live mode

Each step is independently testable. No step requires the next to be complete.

### Builder #6 (consensus) — DONE (2026-03-28)

`scripts/earnings/build_consensus.py` — 3-source AV join (EARNINGS + ESTIMATES + INCOME_STATEMENT) with live-only Yahoo fallback. PIT-safe via session-aware MarketSessionClassifier. Fiscal date mapping via Redis SEC cache FYE month + fiscal_math (verified 1522/1522 across 28 companies). Commits: `74d8122`, `f417361`, `f837880`, `dab6ce6`.

### Builder #9 (prior_financials) — DONE (2026-03-28)

`scripts/earnings/build_prior_financials.py` — XBRL Fact graph → FSC fallback → Yahoo opt-in. 19 metrics + 7 computed ratios, 4-8 prior quarters, per-metric amendment overlay. See `build-prior-financials.md`.

### Builder standardisation — DONE (2026-03-29)

`scripts/earnings/builder_adapters.py` — 7 uniform adapters wrapping all built builders. `scripts/earnings/test_builder_validation.py` (130 tests) + `scripts/earnings/test_adapter_validation.py` (511 tests). See `builder-standardisation.md` for full plan + Phase 1 findings.

Key fixes applied during standardisation:
- **C1**: PIT forward-return nulling used string comparison → fixed to datetime comparison (`warmup_cache.py`, `peer_earnings_snapshot.py`)
- **H5**: macro_snapshot silent SPY data loss → added `gaps` field with structured warnings
- **Phase 4**: 3 legacy builders now return packet dicts natively (no sys.exit, no stdout noise)

---

## 13. Report Backfill & Guidance Pipeline Controls

Reports stopped at August 29, 2025 in Neo4j (7-month gap). Historical backfill needed before `build_prior_financials()` can use XBRL ground-truth data.

### To enable report backfill

**Two lines in `scripts/run_event_trader.py`** (add `RedisKeys.SOURCE_REPORTS` to monitoring):

Line 200:
```python
# WAS:  sources = [RedisKeys.SOURCE_NEWS, RedisKeys.SOURCE_TRANSCRIPTS]
# NOW:  sources = [RedisKeys.SOURCE_NEWS, RedisKeys.SOURCE_REPORTS, RedisKeys.SOURCE_TRANSCRIPTS]
```

Line 306: same change.

Note: `DataManagerCentral.py` already initializes `ReportsManager` (line 641). Reports are only excluded from the completion-check loop in `run_event_trader.py`.

### Guidance extraction controls (K8s scale to 0)

Guidance extraction must be paused during backfill to avoid ~287 Claude API calls for 29 trade_ready tickers × 7 months of new filings.

| Step | Command | Reversible? |
|---|---|---|
| Stop guidance trigger | `kubectl scale deployment guidance-trigger -n processing --replicas=0` | `kubectl scale deployment guidance-trigger -n processing --replicas=1` |
| Stop extraction worker | `kubectl scale deployment extraction-worker -n processing --replicas=0` | `kubectl scale deployment extraction-worker -n processing --replicas=1` |

**What keeps running** (unaffected):
- Report fetching (SEC API → Redis)
- Report section extraction (Redis → Neo4j)
- XBRL processing (10-Q/10-K → Neo4j financial data via `xbrl-worker-heavy` + `xbrl-worker-medium` pods)
- Report enrichment (returns calculation via `report-enricher` pod)
- News and transcripts (independent pipelines)

### Backfill command

```bash
# 1. Stop guidance + extraction
kubectl scale deployment guidance-trigger -n processing --replicas=0
kubectl scale deployment extraction-worker -n processing --replicas=0

# 2. Kill current live process
kill <PID>

# 3. Start historical backfill (all 3 sources on, reports re-enabled)
source venv/bin/activate
nohup python scripts/run_event_trader.py --from-date 2025-08-15 --to-date 2026-03-28 -historical > /tmp/backfill.log 2>&1 &

# 4. After backfill completes — re-enable guidance + extraction + live mode
kubectl scale deployment guidance-trigger -n processing --replicas=1
kubectl scale deployment extraction-worker -n processing --replicas=1
nohup python scripts/run_event_trader.py --from-date 2026-03-28 --to-date 2026-03-28 -live --ensure-neo4j-initialized > /dev/null 2>&1 &
```

### XBRL processing estimate

~2,000 10-Q/10-K filings in the gap. Each takes ~30-60s. Total: ~25 hours via the K8s workers (single-pod each, sequential). Cluster (48 CPU, 253 GB RAM) handles this without issue.
