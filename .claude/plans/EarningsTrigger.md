# Earnings Trigger Daemon — Implementation Plan

**Status**: PLAN (v13 — trade system contract alignment, 2026-04-06)

---

## Current Reality vs Target Design (added v13)

### What's Running Today

| Component | Status | File |
|---|---|---|
| `guidance_trigger_daemon.py` | **RUNNING** on K8s | `scripts/guidance_trigger_daemon.py` (354 lines) |
| `extraction_worker.py` | **RUNNING** on K8s (KEDA 1→7) | `scripts/extraction_worker.py` (666 lines) |
| `earnings_trigger.py` | **EXISTS but NAIVE** — simple Redis listener, no gating, no modes | `scripts/earnings_trigger.py` (139 lines) |
| `earnings_orchestrator.py` | **EXISTS** — builds bundle + runs predictor. No sequential processing, no live_state.json, no learner. | `scripts/earnings/earnings_orchestrator.py` (1,677 lines) |
| `earnings-prediction` skill | **EXISTS** — outputs prediction, but schema does not match trade system contract (see below) | `.claude/skills/earnings-prediction/SKILL.md` |
| Full earnings trigger daemon (v12 plan) | **NOT CODED** — the entire two-phase architecture below is still a plan | — |

**The plan below (v12 target architecture) is CORRECT but NOT IMPLEMENTED.** Do not confuse plan with runtime.

### Minimum Upstream Contract Required for Trading

The trade execution system (`.claude/plans/trade-execution-system.md`) needs these from the upstream pipeline:

**CONTRACT BLOCKERS** (the trade daemon cannot function correctly without these):

1. **prediction/result.json** with trade-aligned schema (see Prediction Output Contract below)
2. **Deterministic `prediction_id`** in prediction output for idempotency
3. **Optional `predictor_session_id`** in prediction/result.json (for reassessment resume; absent = safe fallback)

**AUTOMATION BLOCKERS** (the trade daemon works without these but requires manual prediction triggering):

4. **Redis `trades:pending` push** after prediction completes (fast path only — trade daemon has 30s filesystem fallback)
5. **Live 8-K detection** so predictions fire automatically (not manual)
6. Watch keys + stale prediction recovery
7. `live_state.json` with quarter_label

**QUALITY BLOCKERS** (trading works but prediction quality is degraded):

8. Historical-first processing for U1 feedback
9. Deferred learner catch-up before next live cycle

### Prediction Output Contract (v13 — aligned with trade system Block 4A)

The `earnings-prediction` skill currently outputs:

```json
{
  "direction": "short",
  "confidence_score": 45,
  "expected_move_range_pct": [1.0, 3.0],
  "key_drivers": [...],
  "data_gaps": [...],
  "evidence_ledger": [...],
  "analysis": "..."
}
```

The trade system requires these fields in `prediction/result.json`:

```json
{
  "prediction_id": "AAPL_Q1_FY2026_20260406T1603",
  "ticker": "AAPL",
  "quarter_label": "Q1_FY2026",
  "filed_8k": "2026-04-06T16:03:00-04:00",
  "direction": "long",
  "confidence": 82,
  "expected_move_range": [5, 8],
  "key_drivers": [
    {"driver": "EPS beat 15%", "direction": "long"}
  ],
  "rationale_summary": "Strong beat with raised guidance in calm macro.",
  "model_version": "claude-opus-4-6",
  "prompt_version": "earnings-prediction-v3.2",
  "predicted_at": "2026-04-06T16:13:00-04:00"
}
```

**Field mapping (old → new):**

| Old field | New field | Change |
|---|---|---|
| `confidence_score` | `confidence` | Rename |
| `expected_move_range_pct` | `expected_move_range` | Rename |
| `analysis` | `rationale_summary` | Rename + shorten |
| `key_drivers` | `key_drivers` | Same ✓ |
| `data_gaps` | Keep for attribution | Not used by trade daemon |
| `evidence_ledger` | Keep for attribution | Not used by trade daemon |
| (missing) | `prediction_id` | ADD — deterministic `{ticker}_{quarter}_{filed_8k_ts}` |
| (missing) | `ticker` | ADD — from orchestrator context |
| (missing) | `quarter_label` | ADD — from orchestrator context |
| (missing) | `filed_8k` | ADD — from orchestrator context |
| (missing) | `model_version` | ADD — from runtime |
| (missing) | `prompt_version` | ADD — from skill version |
| (missing) | `predicted_at` | ADD — timestamp when prediction completes |

**Who adds the missing fields?**
- `prediction_id`, `ticker`, `quarter_label`, `filed_8k`: the **orchestrator** passes these as arguments to the prediction skill, OR the orchestrator post-processes the prediction output to inject them.
- `model_version`, `prompt_version`, `predicted_at`: the **prediction skill or orchestrator** adds these at write time.

The prediction skill itself only knows about the bundle. The orchestrator knows the event context (ticker, quarter, filing time). The orchestrator is the natural place to ensure the full contract is met.

### Predictor Session ID — Where It Lives

For trade reassessment (resuming the predictor session with new evidence):

- **Single source**: optional `predictor_session_id` field in `prediction/result.json`
  - Written by the orchestrator after the SDK prediction call completes (SDK returns the session/agent ID)
  - No sibling file (no `prediction/session.json` at launch)
  - The trade daemon reads it directly from prediction/result.json — no dependency on live_state.json
- `live_state.json` may optionally mirror it, but the canonical source is always prediction/result.json
- **If field is missing** (prediction ran before this feature, or old-format result.json): trade daemon applies no_change + no_escalation fallback — safe. Reassessment is an enhancement, not a dependency.

### trades:pending Redis Push

After a LIVE prediction completes and `prediction/result.json` is written:

```
LPUSH trades:pending {"prediction_id": "AAPL_Q1_FY2026_20260406T1603", "ticker": "AAPL", "quarter_label": "Q1_FY2026"}
```
Field name is `quarter_label` (NOT `quarter`). Consistent across both plans.

**Who pushes?** The **orchestrator** — the component that writes and validates `prediction/result.json` is the sole pusher. It pushes immediately after confirming the prediction file is valid. NOT the prediction skill (no Redis access) and NOT the earnings trigger daemon (it doesn't know when prediction completes).

**Trade daemon consumes** via BRPOP (fast path). Filesystem scan every 30s is the fallback.

### Guidance Gate Resolution (v13)

**Resolved ambiguity**: completed AND failed both count as "ready enough" for the guidance gate.

- `guidance_status IS NULL` = not ready (never attempted)
- `guidance_status = 'in_progress'` = not ready (still running)
- `guidance_status = 'completed'` = ready
- `guidance_status = 'failed'` = ready (extraction was attempted; predictor handles any data gaps)

A broken guidance extraction should NOT deadlock live prediction forever.

**Note**: XBRL extraction readiness is a separate concern. The guidance gate checks `guidance_status`, not XBRL completeness. If XBRL is needed for guidance quality, that dependency is inside the guidance extraction pipeline, not at the earnings trigger level. See `.claude/plans/GuidanceTrigger.md` for XBRL-related TODOs.

---

*The target architecture below (v12) remains unchanged. It is the correct design — just not yet implemented.*

---

## Requirements

For each ticker:

### 1. Historical Backtesting
a. Before we run this step, we need to ensure all guidance for that ticker is already extracted. See extraction_worker.py which uses guidance_trigger_daemon.py
b. Must run sequentially starting from oldest 8-K earnings report (except for the latest live earnings report which we need to trade). This helps to build the learner.
c. This sequential run for all older 8-K earnings reports must already be ready before we can run the prediction on live earnings report.
d. Can we run automatically as soon as the ticker is ingested into trade_ready but post all its guidance_status is completed.
e. This essentially has 3 components to it — see earnings-orchestrator.md in plans — for each historical report we run planner+predictor using only data on and prior to that 8-K earnings date (and that is the reason we have PIT enabled data subagents). The learner has **no PIT gate** — it uses all available data for the richest possible causal analysis. The predictor's PIT gate is the contamination boundary: lessons only affect attention allocation, the predictor can only act on PIT-safe data. Richer learner context → better lessons → better live predictions (historical lessons carry forward into live U1). Deferred timing naturally ensures 10-Q/10-K availability. These 3 combined make one earnings cycle.

### 2. Live Earnings Report
a. As soon as a 8-k earnings report is ingested, we fire planner + predictor without using any PIT
b. This assumes we have already built the learner component for that ticker using historical back testing above.
c. The learner for the live quarter is deferred — it runs during the NEXT historical bootstrap when the ticker re-enters trade_ready. The orchestrator's sequential processing naturally catches the missing attribution (prediction exists but no attribution/result.json). This ensures U1 feedback is available before the next quarter's prediction without competing with live predictions for Claude API tokens.

Overall we need earnings_trigger.py to have the same production finesse as guidance_trigger_daemon.py or even better since its usecase is more elaborate.

---

## `earnings_trigger_daemon.py` — Complete Architecture

### The Core Insight

The guidance daemon is flat: discover N independent items, enqueue them all. The earnings daemon is a **linear dependency chain** per ticker. But it's still simple — the daemon only decides two things: **HISTORICAL** or **LIVE**. The orchestrator handles all internal complexity (sequential quarters, PIT, U1 loop, learners). The daemon just decides **when to trigger** and **what mode**.

### Dependency Chain (per ticker, every 60s sweep)

```
  ┌─ Phase A: HISTORICAL BOOTSTRAP (guidance-gated) ──────────────┐
  │                                                                │
  │  Historical done? ──YES──→ skip to Phase B                    │
  │       │ NO                                                     │
  │       ▼                                                        │
  │  Guidance complete? ──NO──→ skip ticker (waiting)             │
  │       │ YES                                                    │
  │       ▼                                                        │
  │  enqueue HISTORICAL ──→ stop (one job per ticker per sweep)   │
  └────────────────────────────────────────────────────────────────┘

  ┌─ Phase B Step 1: DETECT live 8-K (NO guidance gate) ────────────┐
  │  (iterates fresh_8ks from Query 2)                             │
  │                                                                │
  │  Fresh 8-K exists?      ──NO──→ skip (waiting for earnings)   │
  │  (hourly_stock IS NULL + 7d)                                   │
  │       │ YES                                                    │
  │       ▼                                                        │
  │  Watch key matches?     ──YES──→ skip (already detected)      │
  │       │ NO                                                     │
  │       ▼                                                        │
  │  set watch key + enqueue LIVE → earnings:pipeline:live        │
  └────────────────────────────────────────────────────────────────┘

  ┌─ Phase B Step 1.5: RECOVER missed live 8-Ks (Query 2b) ───────┐
  │  (only for historical_done tickers with NO watch key)           │
  │                                                                │
  │  Recent 8-K 2.02 exists?  ──NO──→ skip (no missed event)      │
  │  (daily_stock IS NULL + 7d)                                    │
  │       │ YES                                                    │
  │       ▼                                                        │
  │  Within cutoff?           ──NO──→ skip + log "window expired"  │
  │  (filed_8k + cutoff_mins)                                      │
  │       │ YES                                                    │
  │       ▼                                                        │
  │  set watch key + enqueue LIVE (same as Step B1)                │
  └────────────────────────────────────────────────────────────────┘

  ┌─ Phase B Step 2: MONITOR prediction completion ────────────────┐
  │  (iterates watched tickers from Redis)                         │
  │                                                                │
  │  Prediction done?       ──YES──→ delete watch key, done       │
  │  (live_state.json exists,                                      │
  │   accession matches)                                           │
  │       │ NO                                                     │
  │       ▼                                                        │
  │  Cutoff expired?        ──YES──→ log "window expired" +       │
  │  (filed_8k + cutoff_mins)        delete watch key              │
  │       │ NO                                                     │
  │       ▼                                                        │
  │  re-enqueue LIVE (lease dedup)                                 │
  └────────────────────────────────────────────────────────────────┘

  Two queues: live → earnings:pipeline:live (predictions only, never blocked)
              historical → earnings:pipeline:historical (batch + deferred learners)

  Orchestrator prompt:
    Historical: /earnings-orchestrator {TICKER}
    Live:       /earnings-orchestrator {TICKER} --live --accession {ACC}
```

**Key**: `stop` after enqueue means we don't advance to the next gate for this ticker this sweep. One job per ticker per sweep max. This prevents races (e.g., enqueueing live before historical worker finishes).

### Why This Is Correct

| Requirement | How it's handled |
|---|---|
| 1a. Guidance must complete first | Gate 1 — batched Neo4j query, **only for historical phase** |
| 1b. Sequential oldest-first | The orchestrator does this internally (get_quarterly_filings → process chronologically) |
| 1c. Historical before live | Phase A must complete before Phase B runs |
| 1d. Auto-trigger after TradeReady + guidance | Phase A: guidance ready triggers historical automatically |
| 1e. Predictor PIT=8K, Learner no PIT | Predictor PIT is the contamination boundary. Learner uses all available data — richer context produces better U1 lessons without leaking into PIT-gated predictions. |
| 2a. Fire on 8-K ingestion, no PIT | Phase B — daemon detects fresh 8-K (`hourly_stock IS NULL`), enqueues live. **No guidance gate** — predictor reads raw 8-K directly |
| 2b. Historical learner already built | Phase A → Phase B ordering enforces this |
| 2c. Learner for live quarter | Deferred to next historical bootstrap. Orchestrator processes sequentially: finds prediction without attribution → runs learner → U1 available for next prediction. |

### How The Deferred Learner Works

The daemon does NOT monitor for 10-Q/10-K arrival or fire a separate learner job. Instead:

```
Q1 cycle:
  Jan 15: Q1 8-K files → daemon enqueues LIVE → prediction runs → watch key deleted
  Jan 15: live_state.json written (Q1_FY2026). attribution/result.json does NOT exist. That's fine.

Q2 cycle (3 months later):
  Apr 10: Ticker re-enters trade_ready
  Apr 10: is_historical_done() checks:
          1. event.json (stale — Q1 not in it yet) → all old quarters done ✅
          2. live_state.json → Q1 → prediction exists ✅, attribution missing ❌ → returns FALSE
  Apr 10: Daemon enqueues HISTORICAL
  Apr 10: Orchestrator runs get_quarterly_filings → rebuilds event.json (Q1 now in it)
          Processes sequentially:
          Q1: prediction exists (skip). Attribution missing → RUN LEARNER → U1 written
          All done → is_historical_done() → TRUE (both checks pass)
  Apr 15: Q2 8-K files → daemon enqueues LIVE
          Orchestrator has Q1 U1 feedback → better Q2 prediction ✅
```

**Key**: The trigger is `is_historical_done()` checking `live_state.json` for the deferred learner — NOT event.json (which is stale between cycles). The orchestrator rebuilds event.json only after being enqueued.

**Why this is better than same-cycle learner monitoring:**
1. **No token competition**: Learners run on the HISTORICAL queue. Live predictions have the live queue entirely to themselves.
2. **Simpler daemon**: No Query 3 (10-Q detection), no LEARNER_MIN_DAYS, no 10-Q/10-K monitoring, no learn dead-letter. Step B2 is 3 checks instead of 7.
3. **Same U1 outcome**: Feedback is available before the next prediction (just-in-time during historical bootstrap).
4. **Q4/10-K works correctly**: No special handling for annual filings. The 10-K will have been filed by the time the next historical bootstrap runs. Assumes `MAX_LAG_HOURS=90` in `get_quarterly_filings.py` (now in place; see note below).

**Implemented prerequisite**: `get_quarterly_filings.py` now uses `MAX_LAG_HOURS=90` so Q4 quarters (where the 10-K files 60-90 days after the 8-K) are properly matched. This preserves Q1-Q3 behavior while covering slow annual-file timing.

### Key Design Decisions

**Fix 1 — Live detection via `hourly_stock IS NULL` (was: "latest 8-K" query)**

The original Query 2 found the "latest 8-K 2.02 per ticker." Before a new live 8-K arrives, this returns the previous quarter's historical 8-K — causing a fake live enqueue. Fixed: use `hourly_stock IS NULL` as the live signal. `hourly_stock` is computed ~77 minutes after filing (`event_time + 60min + 17min Polygon delay`). This gives a tight freshness window = "this 8-K literally just arrived," aligning with the time-sensitive trading use case. Historical uses `daily_stock IS NOT NULL` in the canonical orchestrator discovery script [`get_quarterly_filings.py`](/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts/get_quarterly_filings.py#L328). The gap between hourly and daily computed (~1-24h) is bridged by the watch key. Daemon HA (2 replicas, pod anti-affinity) minimizes the risk of missing the ~77-minute detection window. Step B1.5 (recovery query) detects any that slip through (processes if within cutoff, logs skip if expired).

**Fix 2 — Guidance gate scoped to historical only (was: gates everything)**

The original design gated ALL phases on guidance. Problem: the fresh live 8-K has `guidance_status IS NULL`, blocking live prediction even though historical is already done. The predictor reads the raw 8-K directly (EX-99.1 in the context bundle) — it doesn't need guidance *extracted from* the live 8-K. Fixed: guidance gate only applies to Phase A (historical bootstrap). Phase B (live) fires immediately on 8-K detection regardless of guidance status.

**Fix 3 — Filesystem for completion truth, Redis for coordination only (was: permanent Redis done markers)**

The master plan (earnings-orchestrator.md §2a, line 194) says: *"durable progress and resume are derived from filesystem outputs."* Fixed: historical done = filesystem check (event.json quarters + live_state.json deferred learner — see `is_historical_done()` pseudocode). Live prediction done = filesystem check (live_state.json + prediction/result.json). Redis is only for leases and the live watch registry — never completion truth.

**Fix 4 — Live watch registry for prediction tracking**

The daemon needs to track which 8-K was detected for prediction re-enqueue and cutoff checking. `earnings:watch:live:{TICKER}` Redis key captures the live 8-K info at detection time. Watch key is deleted once prediction completes (live_state.json written) or cutoff expires. Short lifecycle — prediction tracking only, not learner monitoring.

### Natural Historical/Live Separation

Returns are computed at different times (verified: `utils/market_session.py:281,311`):
- **`hourly_stock`**: event_time + 60min + 17min Polygon delay = **~77 minutes** after filing
- **`daily_stock`**: 5-24 hours after filing (depends on market session)

The daemon uses the tighter signal:

- **Historical** (`get_quarterly_filings.py`): `daily_stock IS NOT NULL` — all filings with fully settled returns
- **Live detection — fast path** (daemon Query 2): `hourly_stock IS NULL` — truly fresh, filed within ~77 minutes
- **Live detection — recovery** (daemon Query 2b): `daily_stock IS NULL` — wider 5-24h window, for tickers with no watch key (catches daemon outages beyond the hourly window, including after a prior cycle completed). Results filtered by accession to skip already-processed 8-Ks. Staleness cutoff (`LIVE_PREDICTION_CUTOFF_MINS`) prevents stale predictions.
- **No overlap with historical**: historical requires `daily_stock IS NOT NULL`, live queries require some stock field IS NULL. No 8-K matches both.

### Completion Truth

| Check | Source | Why |
|---|---|---|
| Historical done? | **Filesystem**: `event.json` quarters all have both result files + `live_state.json` deferred learner check (if prediction exists without attribution → not done) | File-authoritative. Two checks: event.json for known quarters, live_state.json for deferred learner from prior live cycle. See `is_historical_done()` pseudocode. |
| Live prediction done? | **Filesystem**: `live_state.json` exists + `prediction/result.json` in the quarter dir it names | Orchestrator writes both. No stall: if `live_state.json` missing, prediction hasn't completed → lease expires → re-enqueue. |
| Which accession is live? | **Redis**: `earnings:watch:live:{TICKER}` | Pure detection bookkeeping (accession, filed_8k, detected_at). Short-lived — deleted on prediction completion or cutoff. |
| Live quarter_label? | **Filesystem**: `live_state.json` → `quarter_label` (written by orchestrator) | Orchestrator owns quarter identity — it has full context. Daemon never derives fiscal quarter. |
| Dedup enqueue? | **Redis**: leases (`earnings:lease:*`) | Coordination only, TTL'd. |

If Redis loses watch keys, daemon re-detects via Query 2 (`hourly_stock IS NULL`, ~77min window) or Step B1.5 recovery (`daily_stock IS NULL`). If event.json is missing, historical is "not done" (orchestrator creates it on first run).

### Redis Keys

```
# ── Leases (TTL'd, prevent duplicate enqueue) ──
earnings:lease:historical:{TICKER}       → "1"  (ex=43200, 12h)
earnings:lease:live:{TICKER}             → "1"  (ex=3600, 1h)

# ── Live watch registry (set by daemon on detection, deleted on prediction completion) ──
earnings:watch:live:{TICKER}             → JSON {
    "accession_8k": "0001234-26-000123",
    "filed_8k": "2026-03-18T16:30:00-05:00",
    "detected_at": "2026-03-18T16:31:00-04:00"
}
```

No permanent completion markers. Completion is filesystem-authoritative. Watch keys are short-lived (prediction tracking only).

### Queue Payload (earnings:pipeline)

```json
{"ticker": "LULU", "mode": "historical", "enqueued_at": "2026-03-18T10:00:00-04:00"}

{"ticker": "LULU", "mode": "live", "accession_8k": "0001234-26-000123",
 "enqueued_at": "2026-03-18T16:31:00-04:00"}
```

Two modes only. No `learn` mode — learners run inside historical orchestrator jobs.

### Neo4j Queries (3 total, batched where possible)

**Query 1 — Guidance gate** (batched, 2 round-trips, **only for tickers needing historical**):

```cypher
-- Reports with pending guidance (same filter as guidance daemon ASSET_CONFIGS)
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company)
WHERE c.ticker IN $tickers
  AND (r.guidance_status IS NULL OR r.guidance_status = 'in_progress')
  AND (
    r.formType IN ['10-Q', '10-K'] OR
    (r.formType = '8-K' AND (
      r.items CONTAINS 'Item 2.02' OR
      r.items CONTAINS 'Item 7.01' OR
      r.items CONTAINS 'Item 8.01'))
  )
WITH c.ticker AS ticker, count(r) AS pending WHERE pending > 0
RETURN ticker, pending
```
```cypher
-- Transcripts with pending guidance
MATCH (t:Transcript)
WHERE t.symbol IN $tickers
  AND (t.guidance_status IS NULL OR t.guidance_status = 'in_progress')
WITH t.symbol AS ticker, count(t) AS pending WHERE pending > 0
RETURN ticker, pending
```

Tickers appearing in either result → guidance not ready. `completed` and `failed` both count as done (extraction tried; predictor handles gaps).

**Query 2 — Fresh 8-K detection** (batched, for live detection — **`hourly_stock IS NULL`**):

```cypher
-- Find fresh 8-K 2.02 filings where hourly return not yet computed (~77min window), one per ticker (oldest first)
MATCH (r:Report)-[pf:PRIMARY_FILER]->(c:Company)
WHERE c.ticker IN $tickers
  AND r.formType = '8-K' AND r.items CONTAINS 'Item 2.02'
  AND pf.hourly_stock IS NULL
  AND r.created > datetime() - duration('P7D')
WITH c.ticker AS ticker, r ORDER BY r.created ASC
WITH ticker, collect({accession: r.accessionNo, filed: toString(r.created)})[0] AS first
RETURN ticker, first.accession AS accession, first.filed AS filed
```

**Why `hourly_stock IS NULL`**: Tight ~77-minute freshness window for trading speed. Daemon HA (2 replicas) minimizes missed-window risk; Step B1.5 detects any that slip through.

**Historical boundary stays `daily_stock IS NOT NULL`** in the canonical orchestrator discovery script [`get_quarterly_filings.py`](/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts/get_quarterly_filings.py#L328). Daemon HA minimizes the risk of missing the ~77min window; Step B1.5 detects any that slip through.

**7-day recency filter is correctness**: Prevents false live detection of legacy NULL-return 8-Ks in the database.

**Query 2b — Missed-window recovery** (batched, for historical-done tickers with no watch key; results filtered by accession):

```cypher
-- Recovery: recent 8-K 2.02 with daily return not yet computed (wider window than hourly)
MATCH (r:Report)-[pf:PRIMARY_FILER]->(c:Company)
WHERE c.ticker IN $tickers
  AND r.formType = '8-K' AND r.items CONTAINS 'Item 2.02'
  AND pf.daily_stock IS NULL
  AND r.created > datetime() - duration('P7D')
WITH c.ticker AS ticker, r ORDER BY r.created ASC
WITH ticker, collect({accession: r.accessionNo, filed: toString(r.created)})[0] AS first
RETURN ticker, first.accession AS accession, first.filed AS filed
```

**Why `daily_stock IS NULL`**: Catches 8-Ks where the hourly detection window (~77min) passed but daily returns haven't been computed yet (5-24h). Staleness cutoff (`LIVE_PREDICTION_CUTOFF_MINS`, default 60min) prevents stale predictions.

### Live Quarter Identity — `live_state.json` (orchestrator output contract)

**The gap**: The existing discovery path (`get_quarterly_filings.py` → `event.json`) requires `daily_stock IS NOT NULL`. A fresh live 8-K has `daily_stock IS NULL`, so it never appears in event.json. Someone needs to derive the quarter_label for the live 8-K.

**Why the daemon should NOT do this**: 43.2% of matched 10-Q/10-Ks are filed >24h after the 8-K. FYE-based fallback is only 73.8% accurate (COST and TSLA fail completely due to 52-week calendars).

**The solution**: The **orchestrator** derives the quarter_label and **persists the mapping as a file**. The daemon just reads it.

**Contract**: After processing a live 8-K, the orchestrator writes:

```
earnings-analysis/Companies/{TICKER}/events/live_state.json
{
    "accession_8k": "0001234-26-000123",
    "quarter_label": "Q1_FY2026",
    "filed_8k": "2026-03-18T16:30:00-05:00",
    "predicted_at": "2026-03-18T16:45:00Z",
    "accession_10q": "0001234-26-000100"  // filled if 10-Q already exists at prediction time, null if not
}
```

**Daemon reads `live_state.json` for prediction completion check:**

```python
def get_live_state(ticker):
    """Read orchestrator's live_state.json. Returns None if not yet written or corrupt."""
    p = COMPANIES_DIR / ticker / "events" / "live_state.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return None

def has_live_prediction(ticker, current_accession=None):
    state = get_live_state(ticker)
    if not state: return False
    if current_accession and state.get("accession_8k") != current_accession:
        return False  # stale live_state.json from prior cycle
    ql = state["quarter_label"]
    return (COMPANIES_DIR / ticker / "events" / ql / "prediction" / "result.json").exists()
```

**If `live_state.json` doesn't exist**: prediction hasn't completed yet → daemon waits (lease blocks re-enqueue). After lease expires, daemon re-enqueues. Orchestrator re-runs (idempotent). Eventually completes, writes `live_state.json`. No stall possible.

### Sweep Pseudocode

```python
COMPANIES_DIR = Path("earnings-analysis/Companies")

def get_watched_tickers(r):
    """Scan earnings:watch:live:* keys. Returns dict of ticker → watch_data."""
    watched = {}
    for key in r.scan_iter("earnings:watch:live:*"):
        ticker = key.split(":")[-1]
        raw = r.get(key)
        if raw:
            watched[ticker] = json.loads(raw)
    return watched

def is_historical_done(ticker):
    """File-authoritative: event.json + live_state.json checked for completeness.
    Two checks:
    1. All resolvable quarters in event.json have both prediction + attribution result files.
    2. If live_state.json exists, its quarter also has attribution (deferred learner check).
    The deferred learner check is critical: event.json is stale between live cycles (only
    rebuilt when orchestrator runs get_quarterly_filings). Without this check, a prior live
    quarter's missing attribution would never trigger a historical catch-up."""
    event_path = COMPANIES_DIR / ticker / "events" / "event.json"
    if not event_path.exists():
        return False
    try:
        events = json.loads(event_path.read_text())["events"]
    except (json.JSONDecodeError, KeyError):
        return False
    if not events:
        return False
    resolvable = 0
    for e in events:
        q = e["quarter_label"]
        if q.startswith("8K_") or not e.get("fiscal_year") or not e.get("fiscal_quarter"):
            continue  # unmatched 8-K (no 10-Q/10-K) — skip
        resolvable += 1
        base = COMPANIES_DIR / ticker / "events" / q
        if not (base / "prediction" / "result.json").exists():
            return False
        if not (base / "attribution" / "result.json").exists():
            return False
    if resolvable == 0:
        return False
    # Deferred learner check: if a prior live cycle left prediction without attribution,
    # historical is NOT done — orchestrator needs to run learner for that quarter.
    # This catches the case where event.json is stale (doesn't include the live quarter yet).
    ls = get_live_state(ticker)
    if ls:
        ql = ls.get("quarter_label")
        if ql:
            attr = COMPANIES_DIR / ticker / "events" / ql / "attribution" / "result.json"
            pred = COMPANIES_DIR / ticker / "events" / ql / "prediction" / "result.json"
            if pred.exists() and not attr.exists():
                return False  # deferred learner pending
    return True


def get_live_state(ticker):
    """Read orchestrator's live_state.json. Returns None if not yet written or corrupt."""
    p = COMPANIES_DIR / ticker / "events" / "live_state.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def has_live_prediction(ticker, current_accession=None):
    state = get_live_state(ticker)
    if not state: return False
    if current_accession and state.get("accession_8k") != current_accession:
        return False  # stale live_state.json from prior cycle
    ql = state["quarter_label"]
    return (COMPANIES_DIR / ticker / "events" / ql / "prediction" / "result.json").exists()


def is_dead_lettered(r, mode, ticker, accession_8k=None):
    """Check if ticker+mode (optionally + specific 8-K cycle) is in dead-letter queue."""
    dl_queue = f"{QUEUE_MAP[mode]}:dead"
    for raw in r.lrange(dl_queue, 0, -1):
        try:
            entry = json.loads(raw)
            if entry.get("ticker") == ticker and entry.get("mode") == mode:
                if accession_8k and entry.get("accession_8k") != accession_8k:
                    continue  # different 8-K cycle — not a match
                return True
        except (json.JSONDecodeError, TypeError):
            continue
    return False


def enqueue(r, mode, ticker, ttl, extra=None, dry_run=False):
    """Lease-based dedup + LPUSH to mode-specific queue. Returns True if enqueued."""
    lease_key = f"earnings:lease:{mode}:{ticker}"
    if dry_run:
        return not r.exists(lease_key)
    if not r.set(lease_key, "1", ex=ttl, nx=True):
        return False
    payload = {"ticker": ticker, "mode": mode,
               "enqueued_at": datetime.now(timezone.utc).isoformat()}
    if extra:
        payload.update(extra)
    r.lpush(QUEUE_MAP[mode], json.dumps(payload))
    return True


def sweep_once(r, mgr, tickers, dry_run=False):
    total = 0

    # ── Phase A: Historical bootstrap (guidance-gated) ──
    need_historical = {t for t in tickers if not is_historical_done(t)}

    if need_historical:
        guidance_pending = check_guidance_pending(mgr, list(need_historical))
        guidance_ready = need_historical - guidance_pending

        if guidance_pending:
            log.debug(f"Guidance pending ({len(guidance_pending)}): {sorted(guidance_pending)}")

        # Enqueue historical (priority: nearest earnings first)
        for t in sorted(guidance_ready, key=lambda t: tickers[t]):
            if is_dead_lettered(r, "historical", t):
                continue  # terminal failure — skip until --force
            if enqueue(r, "historical", t, ttl=LEASE_TTL_HISTORICAL, dry_run=dry_run):
                total += 1
            # Don't check live gates — historical must finish first

    # ── Phase B: Live detection + prediction monitoring (NO guidance gate) ──
    historical_done = {t for t in tickers if t not in need_historical}
    watched = get_watched_tickers(r)

    # ── Step B1: Detect new live 8-Ks ──
    detect_tickers = historical_done | set(watched.keys())
    if detect_tickers:
        fresh_8ks = find_fresh_8ks(mgr, list(detect_tickers))  # hourly_stock IS NULL + 7d

        for t, info in fresh_8ks.items():
            acc, filed = info["accession"], info["filed"]
            watch_key = f"earnings:watch:live:{t}"
            watch_raw = r.get(watch_key)
            watch = json.loads(watch_raw) if watch_raw else None

            if not watch or watch.get("accession_8k") != acc:
                if is_dead_lettered(r, "live", t, accession_8k=acc):
                    continue  # terminal failure — skip until --force
                if not dry_run:
                    r.set(watch_key, json.dumps({
                        "accession_8k": acc, "filed_8k": filed,
                        "detected_at": datetime.now(timezone.utc).isoformat(),
                    }))
                if enqueue(r, "live", t, ttl=LEASE_TTL_LIVE,
                           extra={"accession_8k": acc}, dry_run=dry_run):
                    total += 1

    # ── Step B1.5: Recover missed live events (daemon outage > hourly window) ──
    recovery_tickers = {t for t in historical_done if t not in watched}
    if recovery_tickers:
        missed_8ks = find_missed_8ks(mgr, list(recovery_tickers))  # daily_stock IS NULL + 7d
        for t, info in missed_8ks.items():
            acc, filed = info["accession"], info["filed"]
            ls = get_live_state(t)
            if ls and ls.get("accession_8k") == acc:
                continue  # already processed
            filed_dt = datetime.fromisoformat(filed)
            mins_since = (datetime.now(timezone.utc) - filed_dt).total_seconds() / 60
            if mins_since > LIVE_PREDICTION_CUTOFF_MINS:
                log.warning(f"Skipping {t}: live prediction window expired "
                            f"(filed {filed}, {mins_since:.0f}min ago, "
                            f"cutoff={LIVE_PREDICTION_CUTOFF_MINS}min)")
                continue
            if is_dead_lettered(r, "live", t, accession_8k=acc):
                continue
            if not dry_run:
                r.set(f"earnings:watch:live:{t}", json.dumps({
                    "accession_8k": acc, "filed_8k": filed,
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                }))
            if enqueue(r, "live", t, ttl=LEASE_TTL_LIVE,
                       extra={"accession_8k": acc}, dry_run=dry_run):
                log.info(f"Recovery: detected missed live 8-K for {t} ({mins_since:.0f}min old)")
                total += 1

    # ── Step B2: Monitor prediction completion ──
    # Simple: check if prediction completed, re-enqueue if not, respect cutoff.
    # No learner monitoring — learner deferred to next historical bootstrap.
    for t, watch in watched.items():
        current_acc = watch.get("accession_8k")

        if has_live_prediction(t, current_acc):
            # Prediction done — delete watch key, daemon's job is complete for this cycle.
            # Learner will run during next historical bootstrap (orchestrator catches
            # missing attribution when processing event.json sequentially).
            r.delete(f"earnings:watch:live:{t}")
            continue

        # Prediction not done — check cutoff
        filed_8k_str = watch.get("filed_8k")
        if filed_8k_str:
            filed_dt = datetime.fromisoformat(filed_8k_str)
            mins_since = (datetime.now(timezone.utc) - filed_dt).total_seconds() / 60
            if mins_since > LIVE_PREDICTION_CUTOFF_MINS:
                log.warning(f"Skipping {t}: live prediction window expired "
                            f"(filed {filed_8k_str}, {mins_since:.0f}min ago, "
                            f"cutoff={LIVE_PREDICTION_CUTOFF_MINS}min)")
                r.delete(f"earnings:watch:live:{t}")
                continue

        # Re-enqueue LIVE (lease dedup prevents flooding)
        if not is_dead_lettered(r, "live", t, accession_8k=current_acc):
            enqueue(r, "live", t, ttl=LEASE_TTL_LIVE,
                    extra={"accession_8k": current_acc}, dry_run=dry_run)

    return total
```

### Worker Routing

```python
# In earnings_orchestrator_worker.py
PROMPTS = {
    "historical": "/earnings-orchestrator {ticker}",
    "live":       "/earnings-orchestrator {ticker} --live --accession {accession_8k}",
}
```

Worker: BRPOP → format prompt → Claude SDK query. Pattern mirrors extraction_worker.py (usage-aware throttling, MCP server config, retry logic, dead-letter queue).

**No post-completion bookkeeping needed**: the orchestrator writes `live_state.json` + result files directly. The daemon reads those files. The worker just runs the SDK and confirms it returned successfully.

### Configuration

```python
POLL_INTERVAL = 60                              # seconds between sweeps
LEASE_TTL_HISTORICAL = 43200                    # 12h (may process 10+ quarters + deferred learners)
LEASE_TTL_LIVE = 3600                           # 1h (single quarter prediction)
ACTIVE_WINDOW_DAYS = int(os.environ.get(        # 90 days: covers earnings +
    "ACTIVE_WINDOW_DAYS", "90"))                # re-entry for next quarter's historical bootstrap
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))  # worker retries before dead-letter
LIVE_PREDICTION_CUTOFF_MINS = int(os.environ.get(     # max minutes after 8-K filing to attempt
    "LIVE_PREDICTION_CUTOFF_MINS", "60"))              # live prediction — after this, skip with reason

# Two queues — live is never blocked by slow historical runs
QUEUE_LIVE = "earnings:pipeline:live"           # live predictions only (urgent)
QUEUE_HISTORICAL = "earnings:pipeline:historical"  # historical backfill + deferred learners (batch)
DEAD_LETTER_LIVE = f"{QUEUE_LIVE}:dead"
DEAD_LETTER_HISTORICAL = f"{QUEUE_HISTORICAL}:dead"
QUEUE_MAP = {
    "historical": QUEUE_HISTORICAL,
    "live": QUEUE_LIVE,
}
```

**Two separate queues**: Historical (hours, includes deferred learners) must never block live predictions (minutes). Same worker image, different `QUEUE_NAME` env var.

**KEDA scaling rule** (carried from existing workers — `claude-code-worker.yaml:140-142`, `extraction-worker.yaml:146`):
- `minReplicaCount: 1` — prevents KEDA killing pods mid-processing.
- `maxReplicaCount: 2` — parallel tickers in historical, parallel live predictions on heavy earnings days.
- `cooldownPeriod: 300` — only governs scale-down above minReplicas.

**Daemon high availability**: 2 replicas with pod anti-affinity (prefer different nodes). Stateless — Redis leases prevent duplicate enqueues. Minimizes risk of missing the ~77-minute detection window. Step B1.5 provides a safety net for any that slip through.

**Cross-pipeline throttling**: All workers share the same Claude API quota via `is_over_usage_threshold()` (`extraction_worker.py:99`). Priority via **differential `DAILY_INTERACTIVE_PCT` env vars**:

```
extraction-worker (guidance):      DAILY_INTERACTIVE_PCT=10    ← unchanged (0% regression)
earnings-worker-historical:        DAILY_INTERACTIVE_PCT=7.5   ← slightly aggressive (has deadline)
earnings-worker-live:              DAILY_INTERACTIVE_PCT=2     ← most aggressive (trade signal)
```

Live predictions almost always run. Historical/learners get more room than guidance (deadline pressure). Within each pipeline, daemons sort by nearest earnings date.

**Dead-letter queue**: Worker retries up to `MAX_RETRIES` (3), then dead-letters. Daemon checks dead-letter before enqueueing both modes — skips tickers with terminal failures. Live dead-letter is cycle-scoped (matches `accession_8k`). `--force` flag overrides. Mirrors `extraction_worker.py:61-62,621-630`.

### Risk: Failed Guidance Due to Rate Limits

The extraction worker has rate limit detection (`extraction_worker.py:86`: `RATE_LIMIT_PATTERN = "hit your limit"`) and pauses on rate limits — NOT marks as failed. Only genuine extraction failures get `guidance_status = 'failed'`. The `--force` flag on the guidance daemon can re-process manually if a failure was misclassified.

### Edge Cases Addressed

| Edge Case | Handling |
|---|---|
| **Guidance stuck in_progress** | Guidance daemon's stale recovery (lease expiry → re-enqueue). If genuinely stuck: `--skip-guidance` flag |
| **Historical too slow for live** | Start early — TradeReady gives 1-3 day warning. `daily_stock IS NOT NULL` provides natural ~24h separation |
| **Worker crashes mid-historical** | Lease expires → re-enqueue → orchestrator re-runs → file-authoritative skips done quarters |
| **Multiple 8-K 2.02 same quarter** | Deduped by get_quarterly_filings (USE_FIRST_TICKERS). For live: Query 2 collapses to oldest fresh 8-K per ticker. |
| **8-K/A amendments** | Ignored (query: `formType = '8-K'`, not `'8-K/A'`) |
| **Redis data loss** | Within ~77min: daemon re-detects via Query 2. After: Step B1.5 recovery. Watch keys are short-lived (prediction only), so loss is bounded. |
| **Daemon restarts** | No in-memory state. Redis watch keys + filesystem results persist. Picks up exactly where it left off |
| **Same 8-K in historical AND live** | Impossible: historical uses `daily_stock IS NOT NULL`, live uses `hourly_stock IS NULL`. Cannot match both. |
| **N/A quarters stall is_historical_done()** | Quarters with `quarter_label.startswith("8K_")` or missing fiscal data are skipped. `resolvable > 0` required. |
| **Guidance gate blocks live prediction** | Guidance gate only applies to Phase A. Phase B has no guidance gate. |
| **event.json missing on first run** | `is_historical_done()` returns False → enqueue historical → orchestrator creates event.json on first run |
| **Terminal failure — infinite retry** | Worker dead-letters after MAX_RETRIES (3). Daemon checks dead-letter before enqueueing (cycle-scoped for live). `--force` overrides. |
| **Daemon down >77min during live 8-K** | Step B1.5 recovery: Query 2b catches 8-Ks missed during hourly window. Staleness cutoff applies. Daemon HA minimizes this. |
| **Live prediction cutoff expired** | Step B2 logs "prediction window expired", deletes watch key. No silent miss — always logged. |
| **Deferred learner for Q1-Q3** | 10-Q files within 45 days. By next historical bootstrap (~90 days), 10-Q is available. Orchestrator runs learner with full post-event data. |
| **Deferred learner for Q4 (10-K)** | 10-K files within 90 days. `get_quarterly_filings.py` uses `MAX_LAG_HOURS=90`, so by next historical bootstrap the 10-K is available. |
| **Cross-cycle stale live_state.json** | `has_live_prediction()` compares `current_accession` with `live_state.json.accession_8k`. Prior cycle's data doesn't confuse current cycle. |
| **Cross-cycle stale dead-letter** | `is_dead_lettered()` for live mode matches on `accession_8k`. Prior cycle's dead-letter doesn't block current cycle. |
| **Learner fails during historical** | Orchestrator's attribution failure policy: "warn + write" for incomplete output. Partial attribution with `missing_inputs` is written → `is_historical_done()` sees the file → proceeds. |

### CLI Parity with Guidance Daemon

```bash
python3 scripts/earnings_trigger_daemon.py                    # Daemon mode (60s loop)
python3 scripts/earnings_trigger_daemon.py --list             # Dry run: show what would queue
python3 scripts/earnings_trigger_daemon.py --once             # Single sweep, exit
python3 scripts/earnings_trigger_daemon.py --ticker LULU MU   # Scope to specific tickers
python3 scripts/earnings_trigger_daemon.py --skip-guidance    # Bypass guidance gate
python3 scripts/earnings_trigger_daemon.py --force            # Re-enqueue even if filesystem says done
```

### Files to Create (5 new)

| File | Lines (est) | Purpose |
|---|---|---|
| `scripts/earnings_trigger_daemon.py` | ~220 | Polling daemon (mirrors guidance_trigger_daemon.py structure) |
| `scripts/earnings_orchestrator_worker.py` | ~180 | Queue consumer → Claude SDK (mirrors extraction_worker.py, parameterized by QUEUE_NAME) |
| `k8s/processing/earnings-trigger-daemon.yaml` | ~50 | Always-on Deployment, 2 replicas with pod anti-affinity |
| `k8s/processing/earnings-worker-live.yaml` | ~80 | Deployment + KEDA ScaledObject on `earnings:pipeline:live` (maxReplicas: 2) |
| `k8s/processing/earnings-worker-historical.yaml` | ~80 | Deployment + KEDA ScaledObject on `earnings:pipeline:historical` (maxReplicas: 2) |

### Files NOT Modified by Daemon Implementation

- `scripts/guidance_trigger_daemon.py` — untouched
- `scripts/extraction_worker.py` — untouched
- `.claude/skills/earnings-orchestrator/scripts/get_quarterly_filings.py` — already updated separately (`MAX_LAG_HOURS=90`); daemon assumes current behavior
- `.claude/hooks/build_orchestrator_event_json.py` — untouched
- Any Neo4j schema — no new properties

### Prerequisite: Orchestrator Implementation

The current `.claude/skills/earnings-orchestrator/SKILL.md` is v1.0 (2026-02-04) with placeholder steps and no live mode. The daemon design assumes the orchestrator will support:
- **Historical**: `"/earnings-orchestrator {TICKER}"` → processes all pending quarters with PIT, including deferred learners (prediction exists but no attribution → run learner)
- **Live**: `"/earnings-orchestrator {TICKER} --live --accession {ACC}"` → runs prediction if missing, no-op if already done

Additionally, the orchestrator must write `live_state.json` after live prediction with the derived `quarter_label`. This is the contract between orchestrator and daemon.

**Note**: Non-earnings 8-Ks (e.g., leadership changes filed shortly before earnings) are NOT detected by this daemon — it only triggers on Item 2.02. These filings reach the predictor through the orchestrator's unified inter-quarter timeline (`inter_quarter_context`, pre-assembled by `build_inter_quarter_context()` — see `plannerStep5.md` and `earnings-orchestrator.md` §2b).

**Cutoff clarification**: The daemon's `LIVE_PREDICTION_CUTOFF_MINS` is only an enqueue staleness window — it controls how long after an 8-K filing the daemon will still attempt to enqueue a live prediction. It is NOT the LLM context cutoff. The orchestrator computes `context_cutoff_ts` independently (see `plannerStep5.md` "Context Cutoff" section).

This is a prerequisite tracked separately in `earnings-orchestrator.md` (Phase B). The daemon design is correct regardless — when the orchestrator is built to spec, the daemon will drive it.

**Sync note**: `earnings-orchestrator.md` has been updated to reflect the deferred learner design (2026-03-20). Both plans are aligned.

### What I Deliberately Did NOT Include

| Temptation | Why not |
|---|---|
| Same-cycle live learner monitoring | Competes with live predictions for Claude tokens. Learner runs during next historical bootstrap instead — same U1 outcome, zero token competition. |
| Per-quarter state tracking in daemon | Orchestrator handles this (file-authoritative + internal sequential loop) |
| NATS event-driven live detection | 60s polling is simple and adequate (97.7% of earnings are pre/post market) |
| Neo4j `earnings_status` property | Would require schema changes; filesystem + Redis is sufficient |
| Unified daemon with guidance | Different sweep logic (flat vs. dependency chain); coupling risks regressions |
| Complex retry/backoff in daemon | Worker handles retries; daemon just re-enqueues after lease expiry |
| Permanent Redis completion markers | Filesystem is completion truth; Redis is coordination only |
| Daemon-side quarter_label derivation | Unreliable at detection time (43.2% of 10-Qs filed >24h after 8-K, FYE fallback only 73.8%). Orchestrator owns this. |

---

## Summary: What Makes This Work

The entire design rests on **5 properties**:

1. **Orchestrator idempotency** (file-authoritative): re-running any command is always safe — it skips completed work
2. **Two-tier live detection**: fast path `hourly_stock IS NULL` (~77min, trading speed) + recovery `daily_stock IS NULL` (5-24h, catches daemon outages). Staleness cutoff prevents stale predictions. Historical boundary `daily_stock IS NOT NULL` (shared with `get_quarterly_filings.py`).
3. **Everything on disk, nothing in Redis except disposable coordination**: `event.json` + `result.json` for historical. `live_state.json` + `result.json` for live. Redis has only leases (TTL'd) and short-lived watch keys (prediction tracking).
4. **Daemon never derives fiscal quarter identity**: historical quarter_labels from `event.json`. Live quarter_label from `live_state.json`. Zero fiscal math in daemon.
5. **Deferred learner, zero token competition**: Live predictions have the live queue entirely to themselves. Learners run during the next historical bootstrap on the historical queue. Same U1 outcome (feedback available before next prediction), simpler daemon, no cross-pipeline contention.

The daemon is ~220 lines. Two modes: HISTORICAL and LIVE. Phase A checks guidance + filesystem. Phase B checks Neo4j (`hourly_stock IS NULL` + 7d) + filesystem + Redis watch. The orchestrator does all the hard work — including learners. The daemon just decides **when to trigger** and **what mode**.

---

## Design History

This plan evolved through 12 rounds of review (Claude + ChatGPT + user). Key milestones:
- v1-v4: Core architecture established (dependency chain, file-authoritative, watch keys)
- v5-v8: Live detection refined (hourly_stock IS NULL, two-tier detection, staleness cutoff)
- v9-v11: Cycle-scoping, dead-letter for all modes, cross-pipeline throttling, daemon HA
- v12: Simplified from 3-mode to 2-mode design (deferred learner via historical bootstrap)

Full review log with 28 fixes preserved in git history (`74ada65`).
