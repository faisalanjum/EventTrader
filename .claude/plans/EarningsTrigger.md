# Earnings Trigger Daemon — Implementation Plan

**Status**: PLAN (v11 — 11 rounds of review, 2026-03-19)

---

## Requirements

For each ticker:

### 1. Historical Backtesting
a. Before we run this step, we need to ensure all guidance for that ticker is already extracted. See extraction_worker.py which uses guidance_trigger_daemon.py
b. Must run sequentially starting from oldest 8-K earnings report (except for the latest live earnings report which we need to trade). This helps to build the learner.
c. This sequential run for all older 8-K earnings reports must already be ready before we can run the prediction on live earnings report.
d. Can we run automatically as soon as the ticker is ingested into trade_ready but post all its guidance_status is completed.
e. This essentially has 3 components to it — see earnings-orchestrator.md in plans — for each historical report we run planner+predictor using only data on and prior to that 8-K earnings date (and that is the reason we have PIT enabled data subagents). For learner, it runs assuming it was done post 10-q/10-k relating to this specific 8-k earnings report (so the idea is learner needs to know what actually happened and by then we have more analysts and data commenting about this). As such the PIT enabled date for this learner component is the 10q/k related datetime. These 3 combined make one earnings cycle.

### 2. Live Earnings Report
a. As soon as a 8-k earnings report is ingested, we fire planner + predictor without using any PIT
b. This assumes we have already built the learner component for that ticker using historical back testing above.
c. As soon as 10k/q relating to this specific 8k is filed, we run the learner on it.

Overall we need earnings_trigger.py to have the same production finesse as guidance_trigger_daemon.py or even better since its usecase is more elaborate.

---

## `earnings_trigger_daemon.py` — Complete Architecture (v2, reviewed)

### The Core Insight

The guidance daemon is flat: discover N independent items, enqueue them all. The earnings daemon is a **linear dependency chain** per ticker. But it's still simple — 4 gates checked in order, one enqueue per sweep max per ticker. The orchestrator handles all internal complexity (sequential quarters, PIT, U1 loop). The daemon just decides **when to trigger** and **what mode**.

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

  ┌─ Phase B Step 2: MONITOR learner (independent of Query 2) ────┐
  │  (iterates watched tickers from Redis+disk — NOT fresh_8ks)    │
  │                                                                │
  │  Already learned?       ──YES──→ done (delete watch key)      │
  │  (attribution/result.json)                                     │
  │       │ NO                                                     │
  │       ▼                                                        │
  │  Prediction done?       ──NO──┐                                │
  │  (live_state.json exists)     │                                │
  │       │ YES                   ▼                                │
  │       │                  Cutoff expired? ─YES─→ log "window    │
  │       │                  (filed + cutoff)       expired" +     │
  │       │                       │ NO              delete watch   │
  │       │                       ▼                                │
  │       │                  re-enqueue LIVE (lease dedup)          │
  │       ▼                                                        │
  │  7+ days since 8-K?    ──NO──→ skip (cooling period)          │
  │  (filed_8k + 7d <= now)                                        │
  │       │ YES                                                    │
  │       ▼                                                        │
  │  10-Q/10-K available?  ──NO──→ skip (waiting for filing)      │
  │  (accession_10q in live_state                                  │
  │   OR Query 3 finds one)                                        │
  │       │ YES                                                    │
  │       ▼                                                        │
  │  In dead-letter queue? ──YES──→ skip (terminal failure)       │
  │       │ NO                                                     │
  │       ▼                                                        │
  │  enqueue LEARN → earnings:pipeline:live                       │
  └────────────────────────────────────────────────────────────────┘

  Two queues: live/learn → earnings:pipeline:live (never blocked)
              historical  → earnings:pipeline:historical (batch)

  Live predict and learn use the same SDK prompt:
    /earnings-orchestrator {TICKER} --live --accession {ACC}
  Orchestrator internally:
    prediction missing        → run predictor
    prediction done + 10-Q/K  → run learner
    both done                 → no-op
```

**Key**: `stop` after enqueue means we don't advance to the next gate for this ticker this sweep. One job per ticker per sweep max. This prevents races (e.g., enqueueing live before historical worker finishes).

### Why This Is Correct

| Requirement | How it's handled |
|---|---|
| 1a. Guidance must complete first | Gate 1 — batched Neo4j query, **only for historical phase** |
| 1b. Sequential oldest-first | The orchestrator does this internally (get_quarterly_filings → process chronologically) |
| 1c. Historical before live | Phase A must complete before Phase B runs |
| 1d. Auto-trigger after TradeReady + guidance | Phase A: guidance ready triggers historical automatically |
| 1e. Predictor PIT=8K, Learner PIT=10Q | Orchestrator's concern (event.json has both accessions/dates) |
| 2a. Fire on 8-K ingestion, no PIT | Phase B — daemon detects fresh 8-K (`hourly_stock IS NULL`), enqueues live. **No guidance gate** — predictor reads raw 8-K directly |
| 2b. Historical learner already built | Phase A → Phase B ordering enforces this |
| 2c. Learner fires on 10-Q/10-K arrival | Phase B Gate 4 — daemon detects new 10-Q/10-K, re-enqueues same live command |

### Key Fixes Applied (see Review Log for full list)

**Fix 1 — Live detection via `hourly_stock IS NULL` (was: "latest 8-K" query)**

The original Query 2 found the "latest 8-K 2.02 per ticker." Before a new live 8-K arrives, this returns the previous quarter's historical 8-K — causing a fake live enqueue. Fixed: use `hourly_stock IS NULL` as the live signal. `hourly_stock` is computed ~77 minutes after filing (`event_time + 60min + 17min Polygon delay`). This gives a tight freshness window = "this 8-K literally just arrived," aligning with the time-sensitive trading use case. Historical uses `daily_stock IS NOT NULL` (`get_quarterly_filings.py:184`). The gap between hourly and daily computed (~1-24h) is bridged by the watch key. Daemon HA (2 replicas, pod anti-affinity) minimizes the risk of missing the ~77-minute detection window. Step B1.5 (recovery query) catches any that slip through.

**Fix 2 — Guidance gate scoped to historical only (was: gates everything)**

The original design gated ALL phases on guidance. Problem: the fresh live 8-K has `guidance_status IS NULL`, blocking live prediction even though historical is already done. The predictor reads the raw 8-K directly (EX-99.1 in the context bundle) — it doesn't need guidance *extracted from* the live 8-K. Fixed: guidance gate only applies to Phase A (historical bootstrap). Phase B (live) fires immediately on 8-K detection regardless of guidance status.

**Fix 3 — Filesystem for completion truth, Redis for coordination only (was: permanent Redis done markers)**

The master plan (earnings-orchestrator.md §2a, line 194) says: *"durable progress and resume are derived from filesystem outputs."* Fixed: historical done = filesystem check (event.json + all prediction/result.json + attribution/result.json). Live prediction/learner done = filesystem check in live quarter directory. Redis is only for leases and the live watch registry — never completion truth.

**Fix 4 — Live watch registry (was: relied on trade_ready persistence)**

After live prediction, the daemon needs to track the live 8-K accession for 30-60 days while waiting for the 10-Q/10-K. Trade_ready entries are persistent today (cleanup is manual-only per `trade_ready_scanner.py:399`), but coupling to that is fragile. Fixed: `earnings:watch:live:{TICKER}` Redis key captures the live 8-K info at prediction time. Decouples the learner phase from trade_ready persistence.

### Natural Historical/Live Separation

Returns are computed at different times (verified: `utils/market_session.py:281,311`):
- **`hourly_stock`**: event_time + 60min + 17min Polygon delay = **~77 minutes** after filing
- **`daily_stock`**: 5-24 hours after filing (depends on market session)

The daemon uses the tighter signal:

- **Historical** (`get_quarterly_filings.py`): `daily_stock IS NOT NULL` — all filings with fully settled returns
- **Live detection — fast path** (daemon Query 2): `hourly_stock IS NULL` — truly fresh, filed within ~77 minutes
- **Live detection — recovery** (daemon Query 2b): `daily_stock IS NULL` — wider 5-24h window, for tickers with no watch key (catches daemon outages beyond the hourly window, including after a prior cycle completed). Results filtered by accession to skip already-processed 8-Ks. Staleness cutoff (`LIVE_PREDICTION_CUTOFF_MINS`) prevents stale predictions.
- **Gap** (`hourly set, daily NULL`, ~1-24h): covered by recovery step (Query 2b) + watch key (persists through transition for learner monitoring)
- **No overlap with historical**: historical requires `daily_stock IS NOT NULL`, live queries require some stock field IS NULL. No 8-K matches both.

### Completion Truth (hybrid)

| Check | Source | Why |
|---|---|---|
| Historical done? | **Filesystem**: `event.json` exists + all quarters have `prediction/result.json` AND `attribution/result.json` | File-authoritative per master plan. Single source of truth. |
| Live prediction done? | **Filesystem**: `live_state.json` exists + `prediction/result.json` in the quarter dir it names | Orchestrator writes both. No stall: if `live_state.json` missing, prediction hasn't completed → lease expires → re-enqueue. |
| Live learner done? | **Filesystem**: `attribution/result.json` in the quarter dir named by `live_state.json` | Same principle. |
| Which accession is live? | **Redis**: `earnings:watch:live:{TICKER}` | Pure detection bookkeeping (accession, filed_8k, detected_at). Decouples from trade_ready. |
| Live quarter_label? | **Filesystem**: `live_state.json` → `quarter_label` (written by orchestrator) | Orchestrator owns quarter identity — it has full context (runs for minutes, 10-Q may arrive during run). Daemon never derives fiscal quarter. |
| Dedup enqueue? | **Redis**: leases (`earnings:lease:*`) | Coordination only, TTL'd. |

If Redis loses watch keys, daemon re-detects via Query 2 (`hourly_stock IS NULL`, ~77min window) or rebuilds learner_universe from `live_state.json` on disk. Dual-replica daemon HA prevents extended detection outages. If event.json is missing, historical is "not done" (orchestrator creates it on first run).

### Redis Keys

```
# ── Leases (TTL'd, prevent duplicate enqueue) ──
earnings:lease:historical:{TICKER}       → "1"  (ex=43200, 12h)
earnings:lease:live:{TICKER}             → "1"  (ex=3600, 1h)
earnings:lease:learn:{TICKER}            → "1"  (ex=43200, 12h)

# ── Live watch registry (set by daemon on detection) ──
# Pure detection bookkeeping. No completion state, no quarter_label.
# Quarter identity comes from live_state.json (orchestrator output).
earnings:watch:live:{TICKER}             → JSON {
    "accession_8k": "0001234-26-000123",
    "filed_8k": "2026-03-18T16:30:00-05:00",
    "detected_at": "2026-03-18T16:31:00-04:00"
}
```

No permanent `earnings:done:*` completion markers. Completion is filesystem-authoritative.

### Queue Payload (earnings:pipeline)

```json
{"ticker": "LULU", "mode": "historical", "enqueued_at": "2026-03-18T10:00:00-04:00"}

{"ticker": "LULU", "mode": "live", "accession_8k": "0001234-26-000123",
 "enqueued_at": "2026-03-18T16:31:00-04:00"}

{"ticker": "LULU", "mode": "learn", "accession_8k": "0001234-26-000123",
 "accession_10q": "0001234-26-000456",
 "enqueued_at": "2026-04-25T10:00:00-04:00"}
```

### Neo4j Queries (4 total, batched where possible)

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

**Why `hourly_stock IS NULL` not `daily_stock IS NULL`**: They are computed at fundamentally different times (verified: `MarketSessionClassifier.get_1d_impact_times()` vs `get_interval_end_time()` in `utils/market_session.py`):
- `hourly_stock`: always event_time + 60min + 17min Polygon delay = **~77 minutes** after filing
- `daily_stock`: depends on market session — **5h** (pre/in-market) to **24h** (post-market, 52.6% of filings)

Using `hourly_stock IS NULL` gives a tight ~77-minute freshness window = "this 8-K literally just arrived." This is by design for trading speed — the prediction must fire well before the 77-minute mark. Daemon HA (2 replicas, pod anti-affinity) minimizes the risk of missing the detection window; Step B1.5 catches any that slip through. Step B2 handles worker/orchestrator failures after detection (see re-enqueue fallback below).

**Historical boundary stays `daily_stock IS NOT NULL`** (`get_quarterly_filings.py:184`, unchanged). The gap (`hourly set, daily NULL`, ~1-24h) is covered by the watch key (set at detection, persists through the transition). Daemon HA minimizes the risk of missing the ~77min window; Step B1.5 catches any that slip through.

**7-day recency filter is still correctness**: Database has 104 8-K 2.02 filings across 14 tickers with both `hourly_stock IS NULL` AND `daily_stock IS NULL` dating back to 2023-01-09 (legacy filings that never got returns computed). Without the 7-day filter, these would trigger false live detection.

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

**Why `daily_stock IS NULL`**: This catches 8-Ks where the hourly detection window (~77min) passed but daily returns haven't been computed yet (5-24h). Only runs for the tiny set of `recovery_tickers` (typically 0 — only non-zero after daemon outage). The staleness cutoff (`LIVE_PREDICTION_CUTOFF_MINS`, default 60min) prevents stale predictions — 8-Ks older than the cutoff are skipped with an explicit reason log.

**Query 3 — 10-Q/10-K arrival** (per ticker, only for tickers with watch key where prediction result exists but attribution result doesn't):

```cypher
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType IN ['10-Q', '10-K']
  AND r.created > datetime($live_8k_filed)
RETURN r.accessionNo AS accession, r.created AS filed, r.formType AS form_type
ORDER BY r.created ASC LIMIT 1
```

Only runs for the few tickers (0-5 typically) that have a live prediction but no learner. Not batched — per-ticker is fine for tiny N.

### Live Quarter Identity — `live_state.json` (orchestrator output contract)

**The gap**: The existing discovery path (`get_quarterly_filings.py` → `event.json`) requires `daily_stock IS NOT NULL`. A fresh live 8-K has `daily_stock IS NULL`, so it never appears in event.json. Someone needs to derive the quarter_label for the live 8-K.

**Why the daemon should NOT do this**: 43.2% of matched 10-Q/10-Ks are filed >24h after the 8-K (verified: 8,491 filings). A daemon/worker trying to derive the quarter at detection time (~60s after 8-K) would fail for nearly half of all live cases. FYE-based fallback is only 73.8% accurate (verified: 107 filings, 13 tickers — COST and TSLA fail completely due to 52-week calendars).

**The solution**: The **orchestrator** derives the quarter_label (it has the best context — runs for minutes, can retry, can use multiple strategies) and **persists the mapping as a file**. The daemon just reads it.

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

**What this eliminates from the daemon/worker**:
- `discover_quarter_for_8k()` — removed (was unreliable at detection time)
- `estimate_quarter_from_filing()` — removed (73.8% accuracy, too fragile)
- `quarter_label` in Redis watch key — removed (filesystem is truth)
- The stall problem (old design: `has_live_result()` returned False when `quarter_label` was null in Redis, blocking learner forever)

**Daemon reads `live_state.json` for all live completion checks:**

```python
def get_live_state(ticker):
    """Read orchestrator's live_state.json. Returns None if not yet written or corrupt."""
    p = COMPANIES_DIR / ticker / "events" / "live_state.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return None  # partial write or corrupt — treat as not written yet

def has_live_prediction(ticker, current_accession=None):
    state = get_live_state(ticker)
    if not state: return False
    if current_accession and state.get("accession_8k") != current_accession:
        return False  # stale live_state.json from prior cycle
    ql = state["quarter_label"]
    return (COMPANIES_DIR / ticker / "events" / ql / "prediction" / "result.json").exists()

def has_live_learner(ticker, current_accession=None):
    state = get_live_state(ticker)
    if not state: return False
    if current_accession and state.get("accession_8k") != current_accession:
        return False  # stale live_state.json from prior cycle
    ql = state["quarter_label"]
    return (COMPANIES_DIR / ticker / "events" / ql / "attribution" / "result.json").exists()
```

**If `live_state.json` doesn't exist**: prediction hasn't completed yet → daemon waits (lease blocks re-enqueue). After lease expires, daemon re-enqueues. Orchestrator re-runs (idempotent). Eventually completes, writes `live_state.json`. No stall possible.

**How the orchestrator derives the quarter_label** (its problem, not the daemon's): the orchestrator runs for 5-15 minutes (planner + data fetch + predictor). It can try the 10-Q/10-K match at any point during or after the run. By then, the 10-Q may have been ingested (~57% within 24h). If still missing, the orchestrator has full context to use other strategies (FYE estimation, parsing the press release headline, etc). This is tracked in the orchestrator implementation plan (Phase B), not here.

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
    """File-authoritative: event.json exists + all resolvable quarters have both result files."""
    event_path = COMPANIES_DIR / ticker / "events" / "event.json"
    if not event_path.exists():
        return False  # orchestrator never ran
    try:
        events = json.loads(event_path.read_text())["events"]
    except (json.JSONDecodeError, KeyError):
        return False
    if not events:
        return False  # empty manifest
    resolvable = 0
    for e in events:
        q = e["quarter_label"]
        if q.startswith("8K_") or not e.get("fiscal_year") or not e.get("fiscal_quarter"):
            continue  # unmatched 8-K (no 10-Q/10-K) — skip (14 tickers, up to 12 each)
        resolvable += 1
        base = COMPANIES_DIR / ticker / "events" / q
        if not (base / "prediction" / "result.json").exists():
            return False
        if not (base / "attribution" / "result.json").exists():
            return False
    return resolvable > 0  # at least one processable quarter must exist


def get_live_state(ticker):
    """Read orchestrator's live_state.json. Returns None if not yet written or corrupt."""
    p = COMPANIES_DIR / ticker / "events" / "live_state.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return None  # partial write or corrupt — treat as not written yet


def has_live_prediction(ticker, current_accession=None):
    state = get_live_state(ticker)
    if not state: return False
    if current_accession and state.get("accession_8k") != current_accession:
        return False  # stale live_state.json from prior cycle
    ql = state["quarter_label"]
    return (COMPANIES_DIR / ticker / "events" / ql / "prediction" / "result.json").exists()


def has_live_learner(ticker, current_accession=None):
    state = get_live_state(ticker)
    if not state: return False
    if current_accession and state.get("accession_8k") != current_accession:
        return False  # stale live_state.json from prior cycle
    ql = state["quarter_label"]
    return (COMPANIES_DIR / ticker / "events" / ql / "attribution" / "result.json").exists()


def is_dead_lettered(r, mode, ticker, accession_8k=None, accession_10q=None):
    """Check if ticker+mode (optionally + specific accession) is in dead-letter queue.
    For live: pass accession_8k to scope to current cycle (prior cycle's dead-letter won't block).
    For learn: pass accession_10q to scope to specific 10-Q pairing."""
    dl_queue = f"{QUEUE_MAP[mode]}:dead"
    for raw in r.lrange(dl_queue, 0, -1):
        try:
            entry = json.loads(raw)
            if entry.get("ticker") == ticker and entry.get("mode") == mode:
                if accession_8k and entry.get("accession_8k") != accession_8k:
                    continue  # different 8-K cycle — not a match
                if accession_10q and entry.get("accession_10q") != accession_10q:
                    continue  # different 10-Q — not a match
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
        return False  # lease exists — already queued
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

    # ── Phase B: Live detection + learner monitoring (NO guidance gate) ──
    historical_done = {t for t in tickers if t not in need_historical}
    watched = get_watched_tickers(r)  # scan earnings:watch:live:* keys

    # ── Step B1: Detect new live 8-Ks (Gate 3) ──
    # Only tickers with historical done can enter live phase
    detect_tickers = historical_done | set(watched.keys())
    if detect_tickers:
        fresh_8ks = find_fresh_8ks(mgr, list(detect_tickers))  # hourly_stock IS NULL + 7d

        for t, info in fresh_8ks.items():
            acc, filed = info["accession"], info["filed"]
            watch_key = f"earnings:watch:live:{t}"
            watch_raw = r.get(watch_key)
            watch = json.loads(watch_raw) if watch_raw else None

            if not watch or watch.get("accession_8k") != acc:
                # New 8-K detected — set watch and enqueue prediction
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
    # For tickers: historical done, no watch key. These SHOULD have a watch key
    # (if detected) — absence means detection was missed OR prior cycle is complete.
    # Uses wider daily_stock IS NULL window (Query 2b). Staleness cutoff applies.
    recovery_tickers = {t for t in historical_done if t not in watched}
    if recovery_tickers:
        missed_8ks = find_missed_8ks(mgr, list(recovery_tickers))  # daily_stock IS NULL + 7d
        for t, info in missed_8ks.items():
            acc, filed = info["accession"], info["filed"]
            # Skip if this 8-K matches the existing live_state (already processed)
            ls = get_live_state(t)
            if ls and ls.get("accession_8k") == acc:
                continue
            filed_dt = datetime.fromisoformat(filed)
            mins_since = (datetime.now(timezone.utc) - filed_dt).total_seconds() / 60
            if mins_since > LIVE_PREDICTION_CUTOFF_MINS:
                log.warning(f"Skipping {t}: live prediction window expired "
                            f"(filed {filed}, {mins_since:.0f}min ago, "
                            f"cutoff={LIVE_PREDICTION_CUTOFF_MINS}min)")
                continue
            watch_key = f"earnings:watch:live:{t}"
            if is_dead_lettered(r, "live", t, accession_8k=acc):
                continue
            if not dry_run:
                r.set(watch_key, json.dumps({
                    "accession_8k": acc, "filed_8k": filed,
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                }))
            if enqueue(r, "live", t, ttl=LEASE_TTL_LIVE,
                       extra={"accession_8k": acc}, dry_run=dry_run):
                log.info(f"Recovery: detected missed live 8-K for {t} ({mins_since:.0f}min old)")
                total += 1

    # ── Step B2: Monitor watched tickers for learner triggers (Gate 4) ──
    # This loop is INDEPENDENT of Query 2 — iterates watch keys, not fresh_8ks.
    # Critical: once daily_stock is computed (~24h), ticker drops from fresh_8ks.
    # Without this separate loop, the learner would never fire.
    #
    # Filesystem fallback: if Redis lost the watch key but live_state.json exists
    # on disk, rebuild the watch handle from disk. Makes Redis truly disposable.
    learner_universe = dict(watched)  # start with Redis
    for t in (historical_done | set(watched.keys())):
        if t not in learner_universe:
            ls = get_live_state(t)
            if ls:
                learner_universe[t] = {
                    "accession_8k": ls.get("accession_8k"),
                    "filed_8k": ls.get("filed_8k"),
                }

    for t, watch in learner_universe.items():
        current_acc = watch.get("accession_8k")
        if has_live_learner(t, current_acc):
            # Fully done — clean up watch key
            r.delete(f"earnings:watch:live:{t}")
            continue

        if not has_live_prediction(t, current_acc):
            # Prediction not done — check staleness cutoff first
            filed_8k_str = watch.get("filed_8k")
            if filed_8k_str:
                filed_dt = datetime.fromisoformat(filed_8k_str)
                mins_since = (datetime.now(timezone.utc) - filed_dt).total_seconds() / 60
                if mins_since > LIVE_PREDICTION_CUTOFF_MINS:
                    log.warning(f"Skipping {t}: live prediction window expired "
                                f"(filed {filed_8k_str}, {mins_since:.0f}min ago, "
                                f"cutoff={LIVE_PREDICTION_CUTOFF_MINS}min)")
                    r.delete(f"earnings:watch:live:{t}")  # clean up — no point monitoring
                    continue
            # Re-enqueue LIVE (lease dedup prevents flooding).
            # Handles: worker/orchestrator crash, queue lost, or rare case where
            # hourly_stock computed before processing completed (filing left Query 2).
            if not is_dead_lettered(r, "live", t, accession_8k=current_acc):
                enqueue(r, "live", t, ttl=LEASE_TTL_LIVE,
                        extra={"accession_8k": current_acc}, dry_run=dry_run)
            continue

        # 7-day minimum wait after 8-K (market must settle, analysts react)
        filed_8k_str = watch.get("filed_8k")
        if filed_8k_str:
            filed_dt = datetime.fromisoformat(filed_8k_str)
            if datetime.now(timezone.utc) < filed_dt + timedelta(days=LEARNER_MIN_DAYS):
                continue  # Cooling period not elapsed

        # 10-Q/10-K detection: check live_state.json first (covers 10-Q-before-8-K, 4.9%)
        # then fall back to Query 3 (covers 10-Q-after-8-K, 95.1%)
        ls = get_live_state(t)
        tenq_acc = None
        if ls and ls.get("accession_10q"):
            tenq_acc = ls["accession_10q"]
        else:
            tenq = find_10q_for_live(mgr, t, filed_8k_str)
            if tenq:
                tenq_acc = tenq["accession"]

        if tenq_acc:
            # Dead-letter check: per-pair (8-K + 10-Q accession).
            # Only blocks if THIS specific 10-Q caused terminal failure.
            # A different 10-Q filing won't be blocked.
            # Known v1 limit: Query 3 may return the same dead-lettered 10-Q (ASC LIMIT 1).
            if is_dead_lettered(r, "learn", t, accession_10q=tenq_acc):
                continue
            acc = watch.get("accession_8k")
            if enqueue(r, "learn", t, ttl=LEASE_TTL_LEARN,
                       extra={"accession_8k": acc,
                              "accession_10q": tenq_acc},
                       dry_run=dry_run):
                total += 1

    return total
```

### Worker Routing

```python
# In earnings_orchestrator_worker.py
PROMPTS = {
    "historical": "/earnings-orchestrator {ticker}",
    "live":       "/earnings-orchestrator {ticker} --live --accession {accession_8k}",
    "learn":      "/earnings-orchestrator {ticker} --live --accession {accession_8k}",
}
```

Worker: BRPOP → format prompt → Claude SDK query. Pattern mirrors extraction_worker.py (usage-aware throttling, MCP server config, retry logic, dead-letter queue).

**No post-completion bookkeeping needed**: the orchestrator writes `live_state.json` + result files directly. The daemon reads those files. The worker just runs the SDK and confirms it returned successfully.

### Why LIVE_PREDICT and LIVE_LEARN Use the Same SDK Prompt

The orchestrator's `--live --accession {acc}` invocation is idempotent:
- First call (prediction missing) → runs planner + predictor → writes prediction/result.json
- Second call (prediction exists, 10-Q/10-K now available) → runs learner → writes attribution/result.json
- Third call (both exist) → no-op, returns instantly

No `--learn` flag needed. The daemon just re-invokes when new data (10-Q/10-K) appears. The orchestrator figures out what's left to do.

### Configuration

```python
POLL_INTERVAL = 60                              # seconds between sweeps
LEASE_TTL_HISTORICAL = 43200                    # 12h (may process 10+ quarters)
LEASE_TTL_LIVE = 3600                           # 1h (single quarter prediction)
LEASE_TTL_LEARN = 43200                         # 12h (learner is thorough)
LEARNER_MIN_DAYS = int(os.environ.get(          # 7 days minimum wait after 8-K
    "LEARNER_MIN_DAYS", "7"))                   # before learner fires (even if 10-Q exists)
ACTIVE_WINDOW_DAYS = int(os.environ.get(        # 90 days: covers earnings +
    "ACTIVE_WINDOW_DAYS", "90"))                # 10-Q filing window (45d)
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))  # worker retries before dead-letter
LIVE_PREDICTION_CUTOFF_MINS = int(os.environ.get(     # max minutes after 8-K filing to attempt
    "LIVE_PREDICTION_CUTOFF_MINS", "60"))              # live prediction — after this, skip with reason

# Two queues — live is never blocked by slow historical runs
QUEUE_LIVE = "earnings:pipeline:live"           # live predict + learn (urgent)
QUEUE_HISTORICAL = "earnings:pipeline:historical"  # historical backfill (batch)
DEAD_LETTER_LIVE = f"{QUEUE_LIVE}:dead"         # terminal failures — daemon skips these
DEAD_LETTER_HISTORICAL = f"{QUEUE_HISTORICAL}:dead"
QUEUE_MAP = {
    "historical": QUEUE_HISTORICAL,
    "live": QUEUE_LIVE,
    "learn": QUEUE_LIVE,
}
```

**Two separate queues**: A historical backfill (hours) must never block a live prediction (minutes). The daemon pushes to the appropriate queue based on mode. Two KEDA ScaledObjects listening on their respective queues. Same worker image, different `QUEUE_NAME` env var.

**KEDA scaling rule** (carried from existing workers — `claude-code-worker.yaml:140-142`, `extraction-worker.yaml:146`):
- `minReplicaCount: 1` — KEDA's Redis trigger only sees queue depth, not in-flight work. With min=0, KEDA kills pods mid-processing once the queue empties. min=1 guarantees the last pod stays alive.
- `maxReplicaCount: 2` — two workers per queue. Parallel tickers in historical, parallel live predictions on heavy earnings days. Env vars `MAX_REPLICAS_LIVE` / `MAX_REPLICAS_HISTORICAL` in KEDA manifests for tuning.
- `cooldownPeriod: 300` — only governs scale-down above minReplicas, never kills last pod.

**Daemon high availability**: Unlike the guidance daemon (single replica), the earnings daemon runs **2 replicas** with pod anti-affinity (prefer different nodes). The daemon is stateless — Redis leases prevent duplicate enqueues, so concurrent instances are safe. This minimizes the risk of missing the tight ~77-minute `hourly_stock IS NULL` detection window — survives single-node failures without widening the detection query. Step B1.5 (recovery via `daily_stock IS NULL`) provides a safety net for any events that slip through. At default cutoff (60min), missed events are logged explicitly rather than silently dropped; set `LIVE_PREDICTION_CUTOFF_MINS` > 77 for actual recovery processing.

**Cross-pipeline throttling**: All workers share the same Claude API quota and the same `is_over_usage_threshold()` mechanism (`extraction_worker.py:99`). Priority is achieved through **differential `DAILY_INTERACTIVE_PCT` env vars** per K8s deployment — lower value = more aggressive (pauses later, consumes more budget):

```
extraction-worker (guidance):      DAILY_INTERACTIVE_PCT=10    ← unchanged (0% regression)
earnings-worker-historical:        DAILY_INTERACTIVE_PCT=7.5   ← slightly aggressive (has deadline)
earnings-worker-live:              DAILY_INTERACTIVE_PCT=2     ← most aggressive (trade signal)
```

Effect at 55% usage, 5 days left: live threshold=90% (runs), guidance threshold=50% (pauses), historical threshold=62.5% (runs). Live almost always runs. Historical gets more room than guidance (it has a deadline — must finish before 8-K arrives). Within each pipeline, both daemons sort enqueue order by nearest earnings date, so imminent tickers' prerequisite chains complete first. Rate limit detection (`RATE_LIMIT_PATTERN`) is the universal safety net if all thresholds are exceeded.

**Dead-letter queue**: Worker retries up to `MAX_RETRIES` (default 3). After exhaustion, payload goes to `{queue}:dead`. Daemon checks dead-letter before enqueueing all modes (historical, live, learn) — skips tickers with terminal failures. For learn mode, dead-letter matching is per-pair (8-K + 10-Q accession) so a different 10-Q filing won't be blocked. `--force` flag overrides all dead-letter checks. Mirrors `extraction_worker.py:61-62,621-630`.

**Learner 7-day minimum**: Learner never fires earlier than 7 days after 8-K, even if 10-Q already exists. Ensures market settled, analyst coverage published, post-event news available. Rule: `max(filed_8k + 7d, 10-Q arrival)`. Configurable via `LEARNER_MIN_DAYS`.

**10-Q detection**: Two paths: (1) orchestrator writes `accession_10q` in `live_state.json` if 10-Q already existed at prediction time (covers 4.9% of cases where 10-Q filed before 8-K). (2) Query 3 detects new 10-Q/10-K filed after the 8-K (covers 95.1%). Both gates also require 7-day minimum elapsed.

`ACTIVE_WINDOW_DAYS = 90` because the live learner fires when the 10-Q/10-K arrives, which can be 35-60 days after earnings. With a 90-day window, the daemon keeps watching for the 10-Q/10-K. Trade_ready entries are persistent (cleanup is manual-only per `trade_ready_scanner.py:399-420`), so 90 days is safe.

### Risk: Failed Guidance Due to Rate Limits

The extraction worker has rate limit detection (`extraction_worker.py:86`: `RATE_LIMIT_PATTERN = "hit your limit"`) and pauses on rate limits — NOT marks as failed. Only genuine extraction failures (malformed content, no guidance in source) get `guidance_status = 'failed'`. So `failed` = "genuinely couldn't extract" not "hit a rate limit." The `--force` flag on the guidance daemon can re-process manually if a failure was misclassified. Acceptable for v1.

### Edge Cases Addressed

| Edge Case | Handling |
|---|---|
| **Guidance stuck in_progress** | Guidance daemon's stale recovery (lease expiry → re-enqueue). If genuinely stuck: `--skip-guidance` flag |
| **Historical too slow for live** | Start early — TradeReady gives 1-3 day warning. `daily_stock IS NOT NULL` provides natural ~24h separation |
| **Worker crashes mid-historical** | Lease expires → re-enqueue → orchestrator re-runs → file-authoritative skips done quarters |
| **Multiple 8-K 2.02 same quarter** | Deduped by get_quarterly_filings (USE_FIRST_TICKERS). For live: Query 2 explicitly collapses to oldest fresh 8-K per ticker (`ORDER BY r.created ASC ... [0]`). |
| **8-K/A amendments** | Ignored (query: `formType = '8-K'`, not `'8-K/A'`) |
| **10-Q/10-K for wrong quarter** | Daemon picks first filing after live 8-K. If wrong quarter, orchestrator validates period alignment → fails → dead-letters with specific accession pair. Per-pair matching means a different 10-Q won't be blocked. Known v1 limitation: Query 3 (`ASC LIMIT 1`) may keep returning the dead-lettered 10-Q — requires manual investigation. |
| **Redis data loss (leases/watch)** | Within ~77min: daemon re-detects via Query 2 (`hourly_stock IS NULL`). After: `live_state.json` fallback rebuilds learner_universe from disk. If prediction not done: Step B2 re-enqueues LIVE. Dual-replica daemon HA prevents extended detection outages. |
| **Daemon restarts** | No in-memory state. Redis watch keys + filesystem results persist. Picks up exactly where it left off |
| **Same 8-K in historical AND live** | Impossible: historical uses `daily_stock IS NOT NULL`, live uses `hourly_stock IS NULL`. Cannot match both simultaneously. |
| **Ticker fully done, daemon keeps polling** | Phase A: `is_historical_done()` returns True (fast filesystem check). Phase B Step 1: no fresh 8-K found. Step 2: `has_live_learner()` returns True. Cost: 1 filesystem scan + 1 Neo4j query per ticker per sweep |
| **Learner stalls after daily_stock computed** | **Fixed (v6)**: Step B2 iterates watched tickers (Redis), not fresh_8ks (Query 2). Once daily_stock is computed, ticker drops from Query 2 but watch key persists. Learner monitoring continues independently. |
| **Historical blocks live prediction** | **Fixed (v6)**: Two separate queues. `earnings:pipeline:live` for live/learn, `earnings:pipeline:historical` for backfill. Each has its own KEDA worker. Slow historical never blocks urgent live. |
| **N/A quarters stall is_historical_done()** | **Fixed (v6)**: 14 tickers have 8-Ks that can't match a 10-Q/10-K (up to 12 each). These produce `quarter_label = "8K_{accession}"`. `is_historical_done()` now skips these unresolvable quarters. |
| **Guidance gate blocks live prediction** | **Fixed (v2)**: guidance gate only applies to Phase A. Phase B has no guidance gate — predictor reads raw 8-K directly |
| **Latest 8-K = previous quarter** | **Fixed (v2)**: live detection uses `hourly_stock IS NULL`, not "latest 8-K." Only matches genuinely fresh filings |
| **event.json missing on first run** | `is_historical_done()` returns False → enqueue historical → orchestrator creates event.json on first run |
| **Watch key lifecycle** | Daemon sets watch key on fresh 8-K detection (Step B1). Worker does NOT update watch — it writes `live_state.json` + result files. Daemon reads filesystem for completion. Watch key deleted when learner completes. |
| **Terminal failure — infinite retry** | **Fixed (v8+v9)**: Worker retries up to MAX_RETRIES (3), then dead-letters. Daemon checks dead-letter before enqueueing ALL modes (historical, live, learn). Learn uses per-pair matching (8-K + 10-Q accession). `--force` overrides. |
| **10-Q filed before 8-K (4.9%)** | **Fixed (v8)**: Orchestrator writes `accession_10q` in `live_state.json` if 10-Q already existed. Daemon reads it — no Query 3 needed. Covers 419 historical cases (282 same-day, 137 up to 30 days before). |
| **Learner fires too early** | **Fixed (v8)**: 7-day minimum wait (`LEARNER_MIN_DAYS`). Rule: `max(filed_8k + 7d, 10-Q arrival)`. Ensures market settled and analyst reactions available. |
| **Redis "fully disposable" edge** | Redis is disposable for detection (daemon re-detects from Neo4j within ~77min window) and for learner monitoring (fallback rebuilds from `live_state.json` on disk). Only true gap: ticker outside ACTIVE_WINDOW_DAYS with lost watch key AND no live_state.json — extremely unlikely with 90-day window and no auto-cleanup. |
| **Daemon down >77min during live 8-K** | Step B1.5 recovery: Query 2b (`daily_stock IS NULL`) catches 8-Ks missed during hourly window (5-24h wider window). Staleness cutoff applies — 8-Ks older than `LIVE_PREDICTION_CUTOFF_MINS` are skipped with explicit log. Daemon HA (2 replicas) minimizes this scenario. |
| **Live prediction cutoff expired** | Step B2 checks `filed_8k + LIVE_PREDICTION_CUTOFF_MINS`. If expired: logs "prediction window expired", deletes watch key, moves on. No silent miss — always an explicit log entry. Trading window has closed; stale prediction has no value. |

### CLI Parity with Guidance Daemon

```bash
python3 scripts/earnings_trigger_daemon.py                    # Daemon mode (60s loop)
python3 scripts/earnings_trigger_daemon.py --list             # Dry run: show what would queue
python3 scripts/earnings_trigger_daemon.py --once             # Single sweep, exit
python3 scripts/earnings_trigger_daemon.py --ticker LULU MU   # Scope to specific tickers
python3 scripts/earnings_trigger_daemon.py --skip-guidance    # Bypass guidance gate
python3 scripts/earnings_trigger_daemon.py --force            # Re-enqueue even if filesystem says done
```

### Files to Create (5 new, 0 modified)

| File | Lines (est) | Purpose |
|---|---|---|
| `scripts/earnings_trigger_daemon.py` | ~260 | Polling daemon (mirrors guidance_trigger_daemon.py structure) |
| `scripts/earnings_orchestrator_worker.py` | ~180 | Queue consumer → Claude SDK (mirrors extraction_worker.py, parameterized by QUEUE_NAME env var) |
| `k8s/processing/earnings-trigger-daemon.yaml` | ~50 | Always-on Deployment, 2 replicas with pod anti-affinity (HA for ~77min detection window) |
| `k8s/processing/earnings-worker-live.yaml` | ~80 | Deployment + KEDA ScaledObject on `earnings:pipeline:live` (maxReplicas: 2) |
| `k8s/processing/earnings-worker-historical.yaml` | ~80 | Deployment + KEDA ScaledObject on `earnings:pipeline:historical` (maxReplicas: 2) |

### Files NOT Modified (0% regression risk)

- `scripts/guidance_trigger_daemon.py` — untouched
- `scripts/extraction_worker.py` — untouched
- `scripts/earnings/get_quarterly_filings.py` — untouched
- `.claude/hooks/build_orchestrator_event_json.py` — untouched
- Any Neo4j schema — no new properties

### Prerequisite: Orchestrator Implementation

The current `.claude/skills/earnings-orchestrator/SKILL.md` is v1.0 (2026-02-04) with placeholder steps and no live mode. The daemon design assumes the orchestrator will support:
- **Historical**: `"/earnings-orchestrator {TICKER}"` → processes all pending quarters with PIT
- **Live**: `"/earnings-orchestrator {TICKER} --live --accession {ACC}"` → runs prediction if missing, learner if prediction exists + 10-Q/10-K available, no-op if both done

Additionally, the orchestrator must write `live_state.json` after live prediction with the derived `quarter_label`. This is the contract between orchestrator and daemon — the daemon reads it for all live completion checks.

This is a prerequisite tracked separately in `earnings-orchestrator.md` (Phase B). The daemon design is correct regardless — when the orchestrator is built to spec, the daemon will drive it.

**Sync note**: `earnings-orchestrator.md` still references a "delayed N=35 day timer" for live learner triggering (§2a step 4, Q28). The daemon now owns live learner trigger timing (event-driven: 10-Q arrival + 7-day minimum). The orchestrator should consume this trigger, not redefine it. Update the orchestrator plan during implementation.

### What I Deliberately Did NOT Include

| Temptation | Why not |
|---|---|
| Per-quarter state tracking in daemon | Orchestrator handles this (file-authoritative + internal sequential loop) |
| NATS event-driven live detection | 60s polling is simple and adequate (97.7% of earnings are pre/post market) |
| Neo4j `earnings_status` property | Would require schema changes; filesystem + Redis watch is sufficient |
| Unified daemon with guidance | Different sweep logic (flat vs. dependency chain); coupling risks regressions |
| Complex retry/backoff in daemon | Worker handles retries; daemon just re-enqueues after lease expiry |
| Cron-based 35-day learner timer | Replaced by event-driven 10-Q/10-K detection (more responsive, simpler) |
| Permanent Redis completion markers | Filesystem is completion truth (aligned with master plan); Redis is coordination only |
| Redis predicted/learned booleans | Creates dual-truth with filesystem. Watch key stores only detection bookkeeping (accession, filed). |
| Daemon-side quarter_label derivation | Unreliable at detection time (43.2% of 10-Qs filed >24h after 8-K, FYE fallback only 73.8%). Orchestrator owns this — writes `live_state.json`. |

---

## Summary: What Makes This Work

The entire design rests on **4 properties**:

1. **Orchestrator idempotency** (file-authoritative): re-running any command is always safe — it skips completed work
2. **Two-tier live detection**: fast path `hourly_stock IS NULL` (~77min, trading speed) + recovery `daily_stock IS NULL` (5-24h, catches daemon outages). Staleness cutoff (`LIVE_PREDICTION_CUTOFF_MINS`) prevents stale predictions — expired events are logged explicitly, never silently missed. Historical boundary `daily_stock IS NOT NULL` (shared with `get_quarterly_filings.py`). 7-day filter is correctness (104 legacy NULL-return 8-Ks exist in DB).
3. **Everything on disk, nothing in Redis except disposable coordination**: `event.json` + `result.json` for historical. `live_state.json` + `result.json` for live. Redis has only leases (TTL'd) and watch keys (detection bookkeeping). No completion state in Redis.
4. **Daemon never derives fiscal quarter identity**: historical quarter_labels come from `event.json` (via `get_quarterly_filings`). Live quarter_label comes from `live_state.json` (written by orchestrator). The daemon reads both. Zero fiscal math in the daemon.
5. **No silent misses**: every live 8-K is either predicted (within cutoff), explicitly skipped (cutoff expired + logged), or dead-lettered (terminal failure + logged). The daemon never silently drops an event.

The daemon is ~280 lines. Phase A checks guidance + filesystem. Phase B checks Neo4j (fast: `hourly_stock IS NULL`, recovery: `daily_stock IS NULL`, both + 7d recency) + filesystem + Redis watch. The orchestrator does all the hard work. The daemon just decides **when to call it**.

---

## Review Log

| Date | Reviewer | Finding | Action |
|---|---|---|---|
| 2026-03-18 | ChatGPT | "Latest 8-K" query returns historical 8-K before live arrives | **Fix 1**: Use `daily_stock IS NULL` + 7-day recency |
| 2026-03-18 | ChatGPT | Guidance gate blocks live prediction (fresh 8-K has NULL guidance) | **Fix 2**: Guidance gate only for Phase A (historical) |
| 2026-03-18 | ChatGPT | Redis permanent markers conflict with file-authoritative design | **Fix 3**: Filesystem for completion, Redis for coordination only |
| 2026-03-18 | ChatGPT | Scanner auto-deletes trade_ready entries | **Refuted**: cleanup is manual-only (`--cleanup` flag). But added live watch registry as defensive design |
| 2026-03-18 | ChatGPT | Orchestrator SKILL.md doesn't support live mode | **Acknowledged**: SKILL.md is v1. Live mode is a prerequisite, not a daemon concern |
| 2026-03-18 | Claude | Verified all claims against actual codebase | 3 genuine fixes, 1 factual error caught, 1 prerequisite acknowledged |
| 2026-03-18 | ChatGPT (round 2) | Live quarter identity not solved by current discovery path | **Fix 5**: Added `discover_quarter_for_8k()` shared helper. Same fiscal math as get_quarterly_filings, no daily_stock filter. Verified: AAPL test produces identical quarter_label. |
| 2026-03-18 | ChatGPT (round 2) | Redis predicted/learned booleans recreate dual-truth | **Fix 6**: Removed booleans from watch key. Watch stores only bookkeeping (accession, filed, quarter_label). Filesystem is sole completion truth. |
| 2026-03-18 | ChatGPT (round 2) | 7-day recency guard should not be correctness logic | **Refuted**: 104 8-K 2.02 filings across 14 tickers have `daily_stock IS NULL` dating back to 2023-01-09 (legacy, never got returns). Without 7-day filter, these are false live detections. Filter is correctness, not safety. |
| 2026-03-18 | ChatGPT (round 3) | Live quarter_label derivation wrong when 10-Q not yet filed | **Valid but not a blocker**: 43.2% of 10-Qs filed >24h after 8-K. FYE fallback 73.8% accurate. Impact: misnamed directory, not wrong prediction. Self-corrects when 10-Q arrives. Documented as v1 limitation. |
| 2026-03-18 | ChatGPT (round 3) | Watch keys not in sweep universe — learner monitoring breaks if ticker drops from trade_ready | **Fix 7**: Phase B universe = active tickers UNION watched tickers via `get_watched_tickers()`. |
| 2026-03-18 | ChatGPT (round 3) | Stale comment references predicted=true/learned=false after booleans removed | **Fix 8**: Updated Query 3 description text. |
| 2026-03-18 | ChatGPT (round 4) | Live quarter_label path still not live-safe (discover_quarter_for_8k unreliable at detection time) | **Fix 9**: Removed `discover_quarter_for_8k()` and `estimate_quarter_from_filing()` entirely. Replaced with `live_state.json` — orchestrator writes quarter_label, daemon reads it. Zero fiscal math in daemon. |
| 2026-03-18 | ChatGPT (round 4) | Watch key stall: if quarter_label never filled, has_live_result() always returns False, learner never advances | **Fixed by Fix 9**: `has_live_prediction()` now reads `live_state.json` (orchestrator output), not Redis `quarter_label`. If `live_state.json` missing → prediction not done → lease expires → re-enqueue. No stall possible. |
| 2026-03-18 | ChatGPT (round 4) | discover_quarter_for_8k is "too clever" — should let orchestrator persist the mapping | **Agreed**: removed shared helper. Orchestrator owns quarter identity. Daemon is now simpler (4 files instead of 5, ~250 lines instead of ~280). |
| 2026-03-18 | Claude + ChatGPT (round 5) | **Critical**: Learner gate hangs off fresh_8ks loop — once daily_stock computed, ticker drops from Query 2, learner never fires | **Fix 10**: Split Phase B into Step B1 (detection, iterates fresh_8ks) and Step B2 (learner monitoring, iterates watched tickers independently). Gate 4 no longer depends on Query 2. |
| 2026-03-18 | ChatGPT (round 5) | Single queue: slow historical blocks urgent live prediction for different ticker | **Fix 11**: Two queues — `earnings:pipeline:live` (live+learn) and `earnings:pipeline:historical`. Two KEDA workers (same image, different QUEUE_NAME env var). Live is never blocked. |
| 2026-03-18 | Claude (round 5) | is_historical_done() stalls on N/A quarters (14 tickers, up to 12 unmatched 8-Ks each) | **Fix 12**: Skip quarters with `quarter_label.startswith("8K_")` or missing fiscal_year/quarter. Require `resolvable > 0`. |
| 2026-03-18 | ChatGPT (round 6) | Redis watch keys are load-bearing for learner — if Redis loses them after daily_stock computed, learner stalls even though live_state.json exists on disk | **Fix 13**: Step B2 `learner_universe` built from Redis UNION filesystem fallback (rebuild from live_state.json for `historical_done` tickers). Watch keys now truly disposable. |
| 2026-03-18 | ChatGPT (round 6) | KEDA minReplicaCount:1 rule not carried from existing workers | **Fix 14**: Explicitly documented `minReplicaCount: 1` with rationale from `claude-code-worker.yaml:140-142`. KEDA kills pods mid-processing with min=0. |
| 2026-03-18 | ChatGPT (round 6) | Watch keys accumulate forever, never cleaned up | **Fix 15**: Delete `earnings:watch:live:{TICKER}` when `has_live_learner()` returns True. |
| 2026-03-19 | User + ChatGPT (round 7) | Guidance data is in Neo4j not guidance-inventory.md | Updated `earnings-orchestrator.md` §2a context bundle + step 3a. Stale reference flagged. |
| 2026-03-19 | User (round 7) | Learner should wait min 7 days after 8-K even if 10-Q exists | **Fix 16**: Added `LEARNER_MIN_DAYS=7` env var. Step B2 checks `filed_8k + 7d <= now`. Rule: `max(filed_8k + 7d, 10-Q arrival)`. |
| 2026-03-19 | User (round 7) | 10-Q filed before 8-K (4.9% = 419 cases) not handled | **Fix 17**: Orchestrator writes `accession_10q` in `live_state.json` if 10-Q already exists. Daemon checks this before Query 3. |
| 2026-03-19 | User (round 7) | Start with 2 pods per queue | **Fix 18**: `maxReplicaCount: 2` for both live and historical. Env var for tuning. |
| 2026-03-19 | ChatGPT (round 7) | No terminal failure brake — daemon retries forever | **Fix 19**: Dead-letter queues (`{queue}:dead`). Worker dead-letters after MAX_RETRIES=3. Daemon checks before enqueueing. `--force` overrides. |
| 2026-03-19 | ChatGPT (round 7) | Multiple fresh 8-Ks per ticker ambiguous | **Fix 20**: Query 2 explicitly collapses to one per ticker (`ORDER BY created ASC ... [0]`). Oldest fresh 8-K = actual earnings release. |
| 2026-03-19 | ChatGPT (round 7) | Edge case table says worker updates watch key | **Fix 21**: Corrected — daemon sets watch, worker writes `live_state.json`, no post-completion bookkeeping on watch key. |
| 2026-03-19 | ChatGPT (round 7) | GuidanceTrigger.md ACTIVE_WINDOW_DAYS=45 vs actual default=1 | **Fix 22**: Updated GuidanceTrigger.md to note actual deployed default is 1. |
| 2026-03-19 | ChatGPT (round 7) | "Redis fully disposable" slightly overstated | **Softened**: Edge case table now notes the one gap (ticker outside window + lost watch + no live_state.json) as "extremely unlikely." |
| 2026-03-19 | User (round 8) | Should use `hourly_stock IS NULL` not `daily_stock IS NULL` for live freshness | **Fix 23**: Switched Query 2 to `hourly_stock IS NULL` (~77min window vs 5-24h). Step B2 re-enqueues LIVE when prediction not done (handles worker/orchestrator crash). Verified: `hourly_stock` computed at `event_time + 60min + 17min` (`market_session.py:281`), `daily_stock` at close-to-close (`market_session.py:311`). |
| 2026-03-19 | ChatGPT (round 9) | `hourly_stock IS NULL` creates ~77min blind spot if daemon down | **Fix 24**: Daemon HA (2 replicas, pod anti-affinity) + **Fix 28** (round 10): Step B1.5 recovery query using `daily_stock IS NULL` (wider window) for tickers with no watch + no live_state.json. Staleness cutoff prevents stale predictions. Tight hourly window preserved for trading speed. |
| 2026-03-19 | ChatGPT (round 9) | Dead-letter only checked for learn mode, not historical/live | **Fix 25**: Added `is_dead_lettered()` checks before ALL enqueue calls (historical at Phase A, live at Step B1, live re-enqueue at Step B2). Terminal failures no longer loop forever for any mode. |
| 2026-03-19 | ChatGPT (round 9) | Learner dead-letter too coarse (per-ticker blocks all future 10-Qs) | **Fix 26**: Per-pair dead-letter matching for learn mode — keyed on `accession_10q`. A different 10-Q filing won't be blocked. Known v1 limitation: Query 3 (`ASC LIMIT 1`) may keep returning the same dead-lettered 10-Q. Requires manual investigation. |
| 2026-03-19 | Claude (round 9) | 5 stale `daily_stock IS NULL` references after Fix 23 + maxReplicas file table inconsistency | **Fix 27**: Updated lines 108, 154, 404, 573, 645 to `hourly_stock IS NULL`. Updated file table from maxReplicas: 1 to maxReplicas: 2 (matching Fix 18 config). |
| 2026-03-19 | User + ChatGPT (round 10) | Need staleness cutoff + missed-window recovery path | **Fix 28**: Added `LIVE_PREDICTION_CUTOFF_MINS` env var (default 60). Step B1.5 recovery query (Query 2b: `daily_stock IS NULL`) catches 8-Ks missed during hourly window. Staleness cutoff applied in Step B1.5 and Step B2 — expired events logged explicitly, watch key cleaned up. No silent misses: every live 8-K is either predicted, cutoff-skipped (logged), or dead-lettered (logged). |
