# Trade-Ready Earnings Trigger System

---

## §1: Trade-Ready Scanner

**Status**: Phase 1+2 COMPLETE. Live in K8s since 2026-03-16.

Automated scanner polls 3 earnings calendar sources 4x/day, matches against our ~800-company universe, and accumulates a persistent Redis TradeReady list. Entries never expire — once a ticker is added, it stays forever.

---

### Architecture

```
K8s CronJob (4x/day, Sun–Fri, America/New_York)
  └─ scripts/trade_ready_scanner.py
       ├─ [PRIMARY]   Alpha Vantage EARNINGS_CALENDAR (1 bulk call → filter to next trading day)
       ├─ [SECONDARY]  earningscall.biz get_calendar(date) (1-2 calls: today + next trading day)
       ├─ [TIE-BREAK]  Yahoo Finance yfinance (only when sources disagree on date)
       ├─ Universe: Neo4j Company nodes (~796) → Redis → CSV fallback
       ├─ Merge, deduplicate, filter to universe
       └─ Write Redis (idempotent, append-only)
```

---

### Sources

| Role | Source | Calls/scan | Key field |
|---|---|---|---|
| **Primary** | Alpha Vantage `EARNINGS_CALENDAR` (paid) | 1 (bulk 3-month CSV, filter locally) | `time_of_day` (pre/post market) |
| **Secondary** | earningscall.biz `get_calendar(date)` | 1-2 (per date) | `conference_date` (exact call datetime) |
| **Tie-breaker** | Yahoo Finance `yfinance` | 0 usually, 1-5 on conflicts | `earnings_date` confirmation |

**Merge**: AV primary → earningscall adds `conference_date` + catches AV misses → Yahoo breaks date conflicts (2-of-3 majority wins, fallback: AV).

**API keys**: `ALPHAVANTAGE_API_KEY` and `EARNINGS_CALL_API_KEY` in `.env`.

---

### Redis Data Model (Persistent, No TTL, No Auto-Delete)

```
trade_ready:entries                          HASH — one key per ticker, grows monotonically
  LULU → {
    "ticker": "LULU",
    "earnings_date": "2026-03-17",
    "time_of_day": "post-market",
    "conference_date": "2026-03-17T16:30:00-04:00",
    "sources": ["alphavantage", "earningscall"],
    "date_agreement": 2,
    "added_at": "2026-03-16T23:20:18-04:00",
    "updated_at": "2026-03-16T23:29:03-04:00"
  }

trade_ready:by_date:2026-03-17               SET — {ASO, DOCU, HQY, LULU}
trade_ready:by_date:2026-03-18               SET — {FIVE, GIS, MU}
  (one set per earnings date, also persistent)

trade_ready:scan_log                         STRING — latest scan metadata only
```

Re-scans update `updated_at` and merge new data. `added_at` preserved from first discovery. Manual `--cleanup` available but never runs automatically.

---

### Schedule (Live)

| CronJob | Schedule (ET) | Purpose |
|---|---|---|
| `trade-ready-morning` | 7:00 AM Sun–Fri | Confirm today's reporters, catch overnight updates |
| `trade-ready-midday` | 12:00 PM Sun–Fri | Catch earningscall.biz mid-day refreshes |
| `trade-ready-close` | 4:30 PM Sun–Fri | End-of-day state, post-market additions |
| `trade-ready-evening` | 9:00 PM Sun–Fri | **Anchor scan** — APIs settled, tomorrow's list complete |

Sunday scans catch Monday pre-market. Saturday skipped. Each run: <15 seconds, 2-8 API calls.

Trading day logic uses `exchange_calendars` XNYS calendar (handles holidays, early closes).

---

### §1 Files

| File | Purpose |
|---|---|
| `scripts/trade_ready_scanner.py` | Scanner script (~310 lines) |
| `k8s/processing/trade-ready-scanner.yaml` | 4 CronJob manifests |

### §1 CLI

```bash
python3 scripts/trade_ready_scanner.py              # Scan + write Redis
python3 scripts/trade_ready_scanner.py --list        # Dry run (print only)
python3 scripts/trade_ready_scanner.py --show        # Show current list
python3 scripts/trade_ready_scanner.py --show --date 2026-03-17  # Filter by date
python3 scripts/trade_ready_scanner.py --source av   # Single source (av|ecall|yahoo)
python3 scripts/trade_ready_scanner.py --cleanup     # Manual purge of past entries
```

---

### §1 Reliability

- CronJob specs persist in etcd (survive restarts)
- `backoffLimit: 3`, `startingDeadlineSeconds: 600`
- 4 scans/day = any single failure caught by next run
- 3 independent API sources = single source down doesn't block
- TradeReady list fully reconstructable from APIs if Redis loses it
- Idempotent: double-firing is harmless

---
---

## §2: Guidance Auto-Trigger

**Status**: Ready for implementation

### Context

TradeReady scanner (§1, live) accumulates tickers with upcoming earnings in Redis. Guidance extraction pipeline (live) processes assets via `extract:pipeline` → KEDA workers. These two systems are disconnected. This plan connects them: when a ticker enters TradeReady, automatically extract guidance from all its historical and newly-ingested data assets.

**Goal**: By the time an earnings 8-K arrives, ALL prior transcripts, 10-Qs, 10-Ks, and relevant 8-Ks for that company have already been extracted. No racing.

---

### Design (Refined Proposal 1)

**One new always-on daemon** + **one new K8s Deployment**. Zero changes to existing files.

```
trade_ready:entries (written by scanner)
         │
         ▼
guidance_trigger_daemon.py (Deployment, 1 replica, always-on)
  │
  every 60s:
  │  1. Read active TradeReady tickers (earnings_date within active window)
  │  2. For each of 4 assets — ONE batched query per asset:
  │       WHERE ticker IN $active_tickers
  │         AND (guidance_status IS NULL OR guidance_status = 'in_progress')
  │       8-K: + item filter (2.02/7.01/8.01)
  │  3. For each NULL result:  acquire lease → if new, LPUSH extract:pipeline
  │     For each in_progress result: re-enqueue ONLY if lease expired (stale recovery)
  │  4. Sleep 60
         │
         ▼
extraction_worker.py (EXISTING, unchanged)
  BRPOP → /extract → guidance_status = completed
```

### Why This Design

| Decision | Why |
|---|---|
| **Full sweep, not incremental** | `Report.created` = SEC `filedAt`, not insertion time (`ReportProcessor.py:668`). `Transcript.created` = `conference_datetime`, not insertion time (`TranscriptProcessor.py:404`). `created > last_check` silently misses late-ingested old assets. Full sweep with `guidance_status IS NULL OR = 'in_progress'` catches everything — new assets (NULL), stale crashed work (in_progress + expired lease), historical, and late-ingested. |
| **4 batched queries, not per-ticker** | `trigger-extract.py:135` already supports `ticker IN $tickers`. One query per asset with all active tickers = **4 queries per sweep**, not 40. Negligible Neo4j load. |
| **60s poll, not Neo4j hooks** | Hooks in `neograph/mixins/report.py` touch the hottest ingestion path. Saves ~0-60s latency but adds regression risk to `_finalize_report_batch()`. Extraction takes 2-5 min anyway — 60s detection lag is negligible. If sub-60s detection is later proven necessary, hooks can be added as Phase 2 with the daemon retained as safety net. |
| **`IS NULL OR in_progress`, not `= 'failed'`** | `IS NULL`: normal trigger path. `in_progress` + lease expired: **stale recovery** — worker died after BRPOP + setting `in_progress` (`extraction_worker.py:270`) but before completing. Without this, orphaned items are permanently invisible. `failed`: excluded — prevents infinite retry loops (worker dead-letters after 3 retries). Manual `trigger-extract.py --retry-failed` for failures. |
| **Lease-based dedup (`SET NX EX`)** | Between LPUSH and worker setting `in_progress`, the source sits queued with `guidance_status` still NULL. Without dedup, daemon re-pushes every 60s. `SET guidance_lease:{asset}:{source_id} NX EX 14400` is atomic, prevents this, and auto-expires for self-healing. **TTL = 14400s (4 hours)** — must cover worst-case queue wait during earnings season backfill burst (10 tickers × 40 assets = 400 items / 7 pods × 3 min = ~3h queue drain) + extraction time (~8 min) + margin. For `in_progress` items: lease absence means item has been in system >4h without completing → definitely stale → re-enqueue. **Trade-off**: stale `in_progress` recovery takes up to 4h, but earnings are 24+ hours away. On rare extreme-peak days (400+ items), some duplicates may occur after lease expiry — extraction is idempotent (MERGE), so duplicates waste budget but never break correctness. A two-phase lease (short processing TTL + long pending TTL) would solve this perfectly but requires modifying `extraction_worker.py` (violates D5). |
| **Active window filter** | `trade_ready:entries` grows monotonically (by design, no auto-cleanup per `trade_ready_scanner.py:399`). Daemon must derive an active set, not scan all historical tickers. Window policy: `earnings_date >= today - ACTIVE_WINDOW_DAYS`. |
| **No scanner modification** | 60s lag between scanner adding ticker and daemon finding it is meaningless vs hours of extraction time. Avoids coupling scanner to extraction logic. |

### Active Window Policy

`ACTIVE_WINDOW_DAYS = 45` (configurable). Tickers with `earnings_date >= today - 45 days` are active. This means:
- New tickers: picked up within 60s of scanner adding them
- 10-Q filings (40-45 days after quarter end): auto-extracted before ticker drops from active set
- Non-earnings 8-Ks filed weeks after earnings: caught during active window
- Old earnings (>45 days): dropped from active set, no longer queried

Why 45 days: covers the SEC 10-Q filing deadline for all filer categories (large accelerated: 40d, non-accelerated: 45d). Ensures complete guidance extraction across all 4 asset types. Cost: ~225 active tickers in the `IN` clause during peak season — negligible, since most have all assets completed (`guidance_status = completed` → query returns empty). Can be adjusted without code change (constant at top of script).

### 8-K Item Filter

Only in this daemon (manual `trigger-extract.py` unchanged):
```cypher
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company)
WHERE c.ticker IN $tickers
  AND r.formType = '8-K'
  AND (r.items CONTAINS 'Item 2.02' OR r.items CONTAINS 'Item 7.01' OR r.items CONTAINS 'Item 8.01')
  AND (r.guidance_status IS NULL OR r.guidance_status = 'in_progress')
RETURN r.id AS id, c.ticker AS symbol, r.guidance_status AS status
```

`Report.items` is a JSON string (e.g., `["Item 2.02", "Item 9.01"]`). `CONTAINS` does substring match. This filter prevents wasting extraction budget on non-guidance 8-Ks. The extraction pipeline also handles non-guidance 8-Ks correctly (returns NO_GUIDANCE), so this is an **optimization**, not a correctness requirement.

### Timing Analysis

| Asset | Appears right before earnings? | 60s lag acceptable? |
|---|---|---|
| 10-K | No (filed 60-90d after FYE) | N/A |
| 10-Q | No (filed 40-45d after quarter end) | N/A |
| Transcript | No (this quarter's call is AFTER the event we predict) | N/A |
| 8-K (non-earnings) | Rarely (same-day 7.01/8.01 is uncommon) | Yes — extraction takes 2-5 min anyway |

---

### §2 Implementation

#### File 1: `scripts/guidance_trigger_daemon.py` (~150 lines)

```python
POLL_INTERVAL = 60           # seconds between sweeps
LEASE_TTL = 14400            # 4-hour enqueue lease (covers earnings-season backfill burst + extraction)
ACTIVE_WINDOW_DAYS = 45      # covers SEC 10-Q filing deadline (40-45d after quarter end)
QUEUE_NAME = "extract:pipeline"
EXTRACTION_TYPE = "guidance"

ASSET_CONFIGS = {
    "transcript": {"label": "Transcript", "alias": "t", "extra_where": None,
                   "company_join": None, "item_filter": None},
    "8k":         {"label": "Report", "alias": "r", "extra_where": "r.formType = '8-K'",
                   "company_join": ("PRIMARY_FILER", "out"),
                   "item_filter": ["Item 2.02", "Item 7.01", "Item 8.01"]},
    "10q":        {"label": "Report", "alias": "r", "extra_where": "r.formType = '10-Q'",
                   "company_join": ("PRIMARY_FILER", "out"), "item_filter": None},
    "10k":        {"label": "Report", "alias": "r", "extra_where": "r.formType = '10-K'",
                   "company_join": ("PRIMARY_FILER", "out"), "item_filter": None},
}

# Future route table (only guidance enabled now)
ROUTES = [
    {"name": "guidance", "queue": "extract:pipeline", "status_prop": "guidance_status",
     "assets": ASSET_CONFIGS},
    # Future: uncomment when predictor is ready + worker manifest fixed
    # {"name": "prediction", "queue": "earnings:trigger", "status_prop": "prediction_status",
    #  "assets": {"8k": {**ASSET_CONFIGS["8k"], "item_filter": ["Item 2.02"]}},
    #  "readiness_barrier": "all guidance_status = 'completed' for ticker's 4 assets"},
]
```

**Core functions** (reuse patterns from `trigger-extract.py:80-185`):

- `get_active_tickers(r)` → HGETALL `trade_ready:entries`, parse JSON, filter `earnings_date >= today - ACTIVE_WINDOW_DAYS`, return `set[str]`
- `find_eligible(mgr, asset_cfg, tickers, status_prop)` → **ONE batched Cypher query** per asset: `WHERE ticker IN $tickers AND ({status_prop} IS NULL OR {status_prop} = 'in_progress')` + optional item filter. Returns `[{id, symbol, status}]`. Reuses `_company_join_clause()` pattern from `trigger-extract.py:80-96`.
- `enqueue_with_lease(r, source_id, asset, ticker, status)` → Route-scoped lease key: `guidance_lease:{asset}:{source_id}`. For `NULL` status: `SET NX EX 14400` → if acquired, LPUSH. For `in_progress` status: check if lease EXISTS → if absent (stale, >4h), set new lease + LPUSH (recovery). If present (active), skip.
- `sweep_once(r, mgr)` → for each asset config: `find_eligible()` → for each result: `enqueue_with_lease()`. Returns count queued.
- `main()` → **read `REDIS_HOST`/`REDIS_PORT` from `os.environ.get()` FIRST** (captures manifest values), then `load_dotenv(override=True)` for Neo4j credentials (`.env` must NOT override Redis in-cluster DNS). Connect Redis + Neo4j. Signal handling (SIGTERM/SIGINT for graceful shutdown). Daemon loop: `sweep_once()` + `sleep(POLL_INTERVAL)`.

**CLI flags** (for testing):
- `--list` — dry run: show what would be queued, don't push
- `--once` — single sweep, print results, exit
- `--ticker LULU` — scope to specific ticker(s), overrides active-window filter

**Payload format** (exact match to `trigger-extract.py:174`):
```json
{"asset": "8k", "ticker": "LULU", "source_id": "0001234-25-000027", "type": "guidance", "mode": "write"}
```

#### File 2: `k8s/processing/guidance-trigger.yaml` (~40 lines)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: guidance-trigger
  namespace: processing
  labels:
    app: guidance-trigger
spec:
  replicas: 1
  selector:
    matchLabels:
      app: guidance-trigger
  template:
    metadata:
      labels:
        app: guidance-trigger
    spec:
      nodeSelector:
        kubernetes.io/hostname: minisforum
      containers:
      - name: daemon
        image: python:3.11-slim
        command: ["/project/venv/bin/python3", "/project/scripts/guidance_trigger_daemon.py"]
        env:
        - name: REDIS_HOST
          value: "redis.infrastructure.svc.cluster.local"
        - name: REDIS_PORT
          value: "6379"
        resources:
          requests: {cpu: "50m", memory: "128Mi"}
          limits: {cpu: "250m", memory: "256Mi"}
        volumeMounts:
        - name: project
          mountPath: /project
      volumes:
      - name: project
        hostPath:
          path: /home/faisal/EventMarketDB
```

---

### §2 Files

| File | Action | Lines |
|---|---|---|
| `scripts/guidance_trigger_daemon.py` | **Create** | ~150 |
| `k8s/processing/guidance-trigger.yaml` | **Create** | ~40 |

**Zero existing files modified.**

### §2 Reuse

| What | From | How |
|---|---|---|
| Batched ticker query | `trigger-extract.py:135-141` | `ticker IN $tickers` pattern |
| Company join clause | `trigger-extract.py:80-96` | `_company_join_clause()` logic |
| Payload format | `trigger-extract.py:174` | Exact JSON: `{asset, ticker, source_id, type, mode}` |
| Signal handling | `extraction_worker.py:410-430` | SIGTERM/SIGINT graceful shutdown |
| Redis connection | `trade_ready_scanner.py:get_redis()` | Same host/port env vars |
| Neo4j connection | `trigger-extract.py:238` | `get_manager()` from `neograph.Neo4jConnection` |

### §2 Redis Keys (New)

| Key pattern | Type | TTL | Purpose |
|---|---|---|---|
| `guidance_lease:{asset}:{source_id}` | STRING | 14400s (4h) | Atomic enqueue dedup + stale `in_progress` recovery. Auto-expires. Self-healing. |

No persistent Redis state. No cleanup jobs. No permanent SETs.

### §2 Credentials

**Redis**: `REDIS_HOST` and `REDIS_PORT` from K8s manifest env vars (in-cluster DNS: `redis.infrastructure.svc.cluster.local:6379`). Read via `os.environ.get()` before `load_dotenv`, so manifest values win.

**Neo4j**: `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` from `.env` file on the mounted hostPath, loaded via `load_dotenv(override=True)` (same pattern as `trigger-extract.py:30-31`). NOT set in the K8s manifest — `.env` is the single authoritative source for Neo4j credentials. `get_manager()` from `neograph.Neo4jConnection` reads these env vars.

---

### §2 Race Condition Analysis

| Scenario | Outcome |
|---|---|
| Scanner writes ticker while daemon is mid-sweep | Next sweep picks it up (≤60s) |
| Same source queued twice (race between LPUSH and worker `in_progress`) | Lease prevents: `SET NX` is atomic. Even if it slips, extraction is idempotent (MERGE). |
| Worker dies after BRPOP, before setting `in_progress` | `guidance_status` stays NULL. Lease expires (4h). Daemon re-queues on next sweep. **Self-healing.** |
| Worker dies AFTER setting `in_progress`, before completing | `guidance_status` stuck as `in_progress`. Lease expires (4h). Daemon detects stale `in_progress` + no lease → re-enqueues. **Self-healing.** Recovery takes up to 4h — acceptable (earnings 24+ hours away). |
| Worker fails, dead-letters, marks `failed` | Daemon skips `failed`. Manual `trigger-extract.py --retry-failed` to re-process. |
| Daemon pod killed mid-push | K8s restarts (Deployment). Incomplete pushes caught on next sweep. |
| Neo4j temporarily down | Sweep fails gracefully (catch/log). Next sweep retries. |

---

### §2 Verification

```bash
# 1. Dry run — show what would be queued across all active tickers
python3 scripts/guidance_trigger_daemon.py --list

# 2. Single sweep for specific ticker
python3 scripts/guidance_trigger_daemon.py --once --ticker LULU

# 3. Verify queue populated
redis-cli -h 192.168.40.72 -p 31379 LLEN extract:pipeline

# 4. Verify lease keys created
redis-cli -h 192.168.40.72 -p 31379 KEYS "guidance_lease:*"

# 5. Verify idempotency (run again, leases block re-push)
python3 scripts/guidance_trigger_daemon.py --once --ticker LULU
# Should show 0 new items

# 6. Verify 8-K filter: non-2.02/7.01/8.01 8-Ks skipped

# 7. Deploy and monitor
kubectl apply -f k8s/processing/guidance-trigger.yaml
kubectl logs -f -l app=guidance-trigger -n processing

# 8. End-to-end: verify extraction worker picks up and processes
kubectl logs -f -l app=extraction-worker -n processing

# 9. Stop extraction (queue items persist in Redis, resume anytime)
kubectl scale deployment guidance-trigger -n processing --replicas=0   # stop queuing
kubectl scale deployment extraction-worker -n processing --replicas=0  # stop processing

# 10. Resume (daemon re-sweeps, skips completed, re-queues expired leases)
kubectl scale deployment guidance-trigger -n processing --replicas=1
kubectl scale deployment extraction-worker -n processing --replicas=1   # KEDA auto-scales from here
```

---

### §2 Explicitly Locked Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | `IS NULL OR in_progress` (not `= 'failed'`) | NULL = normal trigger. `in_progress` + expired lease = stale recovery (worker crash). `failed` excluded = prevents infinite retry loops. |
| D2 | 4 batched queries per sweep (not per-ticker) | `ticker IN $tickers` = 4 queries total. Same Neo4j load as one manual trigger-extract run. |
| D3 | Lease-based dedup with 14400s (4h) TTL | Atomic (`SET NX`), self-healing (TTL expires). Covers earnings-season backfill burst (400 items / 7 pods = ~3h) + extraction + margin. Two-phase lease (separate pending/processing TTLs) would be ideal but requires worker modification (violates D5). |
| D4 | `ACTIVE_WINDOW_DAYS = 45` | Covers SEC 10-Q filing deadline (40-45d). Ensures complete guidance extraction including late 10-Q filings. Configurable constant. |
| D5 | No changes to existing files | Zero regression risk. Daemon is fully additive. |
| D6 | No incremental `created > last_check` | Broken for this data model (timestamps ≠ insertion time). |
| D7 | No Neo4j hooks | Lowest risk. Add as Phase 2 only if sub-60s detection proven necessary. |
| D8 | Route table for future predictor | Structural extensibility. Not enabled until worker manifest fixed + readiness barrier implemented. |

---
---

## §3: Future — Predictor Trigger

When planner/predictor are ready, add a second route to `ROUTES`:
```python
{
    "name": "prediction",
    "queue": "earnings:trigger",
    "status_prop": "prediction_status",
    "assets": {
        "8k": {"label": "Report", "alias": "r", "extra_where": "r.formType = '8-K'",
               "company_join": ("PRIMARY_FILER", "out"),
               "item_filter": ["Item 2.02"]},
    },
    "readiness_barrier": {
        "check": "all_completed",
        "status_prop": "guidance_status",
        "assets": ["transcript", "8k", "10q", "10k"],
    },
}
```

**Readiness barrier**: predictor only fires when ALL eligible guidance assets for that ticker have `guidance_status = 'completed'`. Any non-completed state blocks firing: `NULL` (not yet extracted), `in_progress` (actively processing or stale), `failed` (broken, needs manual intervention). This prevents the predictor from running with incomplete guidance data.

**Prerequisites before enabling**: fix the worker manifest mismatch between `earnings_trigger.py` and `claude-code-worker.yaml`. Same daemon, same loop, one config entry.
