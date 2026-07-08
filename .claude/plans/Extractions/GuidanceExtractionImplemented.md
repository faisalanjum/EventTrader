# Guidance Extraction Pipeline — Complete Code-Level Mapping

This is a complete code-level mapping of the guidance extraction pipeline with verified file:line references where practical. Code snippets are sometimes summarised for readability — the underlying source file (also cited) is the source of truth. Live numerical values are snapshots from the verification date in §25; mutable counters (queue lengths, index `readCount`, write totals) drift over time. Sections are ordered "outermost → innermost" so a reader can follow one job from trigger to graph.

Live state (verified 2026-05-22): KEDA `ScaledObject extraction-worker-scaler` is paused via `autoscaling.keda.sh/paused-replicas: "0"` AND its live in-cluster spec has `minReplicaCount: 0` (the checked-in YAML still says `1` — the live cluster was patched). `extraction-worker` Deployment is at 0 because of the pause. `guidance-trigger` Deployment is at 0 because of an independent `kubectl scale ... --replicas=0` — there is no ScaledObject targeting it. Queue empty; 5 historical items in `extract:pipeline:dead`; 8,432 GuidanceUpdate nodes already in graph.

---

## §1 — Topology

```
                       ┌─── trade_ready:entries (HASH, Redis)
                       │      ← trade_ready_scanner.py (CronJob 4×/day)
                       ↓
   guidance_trigger_daemon.py ──┐     trigger-extract.py
   (60s sweep, 4 batched queries) │   (CLI, ad-hoc)
                       │           │
                       ├── lease   │ no lease
                       ↓           ↓
                  LPUSH  extract:pipeline  (Redis LIST)
                       │
                       │  KEDA Redis trigger: listLength ≥ 1 → live spec 0..7
                       │  (checked-in YAML is 1..7; live cluster patched to 0..7)
                       ↓
              extraction-worker pod(s)   (K8s, on `minisforum`)
                       │
                       │  BRPOP → process_one(...)
                       ↓
              ClaudeAgentOptions(cli_path=/home/faisal/.local/bin/claude,
                                 model=<orchestrator>,
                                 mcp_servers={neo4j-cypher: HTTP},
                                 setting_sources=["project"],
                                 bypassPermissions, max_turns=80,
                                 max_budget_usd=15)
                       │
                       │  prompt = "/extract TICKER ASSET SOURCE_ID
                       │             TYPE=guidance MODE=write
                       │             PRIMARY_MODEL=… ENRICHMENT_MODEL=…
                       │             RESULT_PATH=/tmp/extract_result_…"
                       ↓
              /extract orchestrator (SKILL.md)
                       │
        ┌──────────────┴──────────────┐
        ↓                              ↓
  extraction-primary-agent     extraction-enrichment-agent
        │ (Sonnet/Haiku)               │ (transcript-only)
        │                              │
        │   Loads 8 instruction files (slots 1–8 per pass)
        │   ── primary-pass.md / enrichment-pass.md ──
        │       FETCH context (1A,1B) + caches (2A,2B,MEMBER_MAP)
        │       FETCH source content (asset-specific queries)
        │       EXTRACT items (LLM judgement, intersection rules)
        │       VALIDATE via Bash → guidance_ids.py (NO direct math)
        │       WRITE via Bash → guidance_write.sh → guidance_write_cli.py
        │                       → guidance_writer.py
        │                       → Neo4j MERGE (atomic per item)
        │
        └──> /tmp/extract_pass_guidance_{primary|enrichment}_{src}.json
                       │
              Orchestrator reads both, combines, writes RESULT_PATH JSON
                       │
              Worker reads RESULT_PATH, marks Neo4j source.guidance_status,
              closes run_ledger row, unlinks tmp files
```

---

## §2 — Trigger Layer

### 2.1 Manual — `scripts/trigger-extract.py` (299 LOC)

**Asset registry** (lines 47-54) — adding a new asset requires editing this AND the worker's `ASSET_LABELS`:
```python
ASSET_QUERIES = {
    "transcript": ("Transcript", "t", None,                  None),
    "8k":         ("Report",     "r", "r.formType = '8-K'",  ("PRIMARY_FILER", "out")),
    "10q":        ("Report",     "r", "r.formType = '10-Q'", ("PRIMARY_FILER", "out")),
    "10k":        ("Report",     "r", "r.formType = '10-K'", ("PRIMARY_FILER", "out")),
    "news":       ("News",       "n", None,                  ("INFLUENCES", "out")),
}
```
Note: filter is exact `formType = '10-K'`, so `10-K/A`, `10-Q/A`, `8-K/A` amendments are **never** picked up (live graph has 137+41+631 = 809 unprocessed amendment Reports — verified in Query F).

**Type discovery** (lines 56-77): scans `.claude/skills/extract/types/*/` for directories containing all three required files (`core-contract.md`, `primary-pass.md`, `{type}-queries.md`). Currently only `guidance` qualifies. Zero hardcoded list.

**Eligibility query template** (lines 99-163):
```cypher
MATCH (alias:Label) [JOIN to Company if needed]
WHERE c.ticker IN $tickers     -- or alias.symbol IN $tickers for Transcript
  AND <extra_where>              -- e.g. r.formType='10-Q'
  AND (alias.{type}_status IS NULL OR alias.{type}_status = 'failed')
RETURN alias.id AS id, ticker_expr AS symbol
ORDER BY ticker_expr, alias.id
```
The `{type}_status` is fully dynamic — `f"{extraction_type}_status"` — so a future `announcement` type would automatically use `announcement_status` on the same source nodes.

**CLI flag matrix**:
| Flag | Effect on status filter |
|---|---|
| (no flag) | `IS NULL OR = 'failed'` |
| `--force` | no filter (everything, including `completed`/`in_progress`) |
| `--retry-failed` | `= 'failed'` only |
| `--source-id ID` | single-asset lookup, skips if `completed`/`in_progress` unless `--force` |
| `--mode dry_run` | payload `mode=dry_run` → worker skips Neo4j status mutation |
| `--type all --asset all` | cross-product enumeration |

**SEC cache prefetch** (lines 269-284): for `guidance` × `{transcript,8k,10q,10k}` (NOT news), calls `sec_quarter_cache_loader.refresh_ticker(redis, ticker)` once per distinct ticker per invocation. This populates Redis keys used later by the CLI period resolver (§10).

**Redis push** (lines 166-185): one `LPUSH` per source. Payload format is the contract between trigger and worker:
```json
{"asset":"transcript","ticker":"CRM","source_id":"CRM_2026-02-25T17.00.00-04.00",
 "type":"guidance","mode":"write"}
```
Ticker is taken from the symbol returned by the eligibility query, with fallback `item['id'].split('_')[0]` (line 173) — for sources whose symbol is null but whose id starts with the ticker.

### 2.2 Automatic — `scripts/guidance_trigger_daemon.py` (353 LOC)

**Lifecycle**: K8s `Deployment` `guidance-trigger`, 1 replica in the manifest. **Currently scaled to 0 by an independent manual `kubectl scale deployment guidance-trigger --replicas=0`** — there is no ScaledObject targeting this Deployment, so the KEDA pause that holds extraction-worker at 0 has no effect here. The two zero states are independent. Per-pod main loop in `main()` (lines 289-349):
```python
while not _shutdown:
    tickers = get_active_tickers(r, args.ticker)   # filtered by ACTIVE_WINDOW_DAYS
    for route in ROUTES:                            # currently just 'guidance'
        sweep_once(r, mgr, tickers, route)
    sleep(POLL_INTERVAL = 60)                       # graceful exit on SIGTERM
```

**Active ticker filter** (lines 91-108):
- `HGETALL trade_ready:entries` (written by separate scanner).
- Filter `entry['earnings_date'] >= today - ACTIVE_WINDOW_DAYS`.
- Code default is `ACTIVE_WINDOW_DAYS=1` (just-in-time mode). **The checked-in `guidance-trigger.yaml` AND the live Deployment env both set `ACTIVE_WINDOW_DAYS=45`** (45-day backfill window covering the SEC 10-Q filing deadline). The code default is only used if someone runs the script outside K8s without env overrides.
- `--ticker LULU` override bypasses the window filter (lines 92-95).

**Eligibility query per asset** (`find_eligible`, lines 123-170):
```cypher
MATCH (alias:Label) [JOIN]
WHERE c.ticker IN $tickers
  AND <extra_where>
  AND <item_filter>                                       -- 8-K only
  AND (alias.guidance_status IS NULL OR alias.guidance_status = 'in_progress')
RETURN alias.id, ticker_expr AS symbol, alias.guidance_status AS status
```
Two key differences from the manual trigger:
1. **Includes `in_progress`** — for stale-recovery of crashed worker attempts.
2. **Excludes `failed`** — prevents infinite-retry loops. Manual `--retry-failed` is the only path back.

**8-K item filter** (lines 56-58):
```python
"8k": {..., "item_filter": ["Item 2.02", "Item 7.01", "Item 8.01"]}
```
Built into the WHERE clause as a substring OR (line 147-151):
```cypher
AND (r.items CONTAINS 'Item 2.02' OR r.items CONTAINS 'Item 7.01' OR r.items CONTAINS 'Item 8.01')
```
`Report.items` is a JSON string. CONTAINS is a substring match. Other 8-K item codes get skipped. Optimization only — extraction would correctly return `NO_GUIDANCE` for non-guidance 8-Ks anyway.

**Lease-based dedup** (`enqueue_with_lease`, lines 173-203):
```python
key = f"guidance_lease:{asset}:{source_id}"
if status is None:
    acquired = r.set(key, "1", ex=14400, nx=True)   # 4-hour atomic claim
    if not acquired: return False                    # already queued
elif status == 'in_progress':
    if r.exists(key): return False                   # worker still active
    acquired = r.set(key, "1", ex=14400, nx=True)    # stale recovery
    if not acquired: return False                    # another pod beat us
# else (status='failed'): never reached, query excludes failed
r.lpush(queue, payload)
return True
```
Why 14400s (4 hours): covers worst-case earnings-season burst (10 tickers × 40 assets ÷ 7 pods × 3 min ≈ 3h queue drain) + extraction time (~8 min) + margin (`GuidanceTrigger.md` §2 D3). On overflow, MERGE-idempotency wastes budget but doesn't break data.

**Priority sort** (lines 252-255): future/today earnings come first (`0 if earnings_date >= today else 1`), then sorted by earnings_date asc. So a freshly-arrived ticker isn't blocked behind a backfill burst.

**SEC cache pre-warm** (`_precompute_sec_refresh`, lines 206-232): once per ticker per sweep:
- If any new pending 10q/10k for this ticker → force refresh.
- Else if `fiscal_quarter:{TICKER}:last_refreshed` Redis key is missing → fill-if-missing.
- `--list` mode skips refresh (no Redis writes during dry-run).

**`ROUTES` table for future extensibility** (lines 66-69): currently just `guidance`. The commented-out `prediction` route in `GuidanceTrigger.md` §3 shows how a future predictor would plug in with a `readiness_barrier` requiring all 4 assets' `guidance_status='completed'`.

**Known bug** in `GuidanceTrigger.md` top TODO: 10-K/10-Q eligibility should also require `EXISTS { (r)-[:HAS_XBRL]->() }` to gate extraction on XBRL processing completion. Without it, a 10-Q can be extracted before XBRL processes it, fall back to month-boundary period dates, then re-extract later with exact SEC dates → duplicate `GuidancePeriod` node for the same quarter. Not yet implemented.

### 2.3 Redis Keys (full inventory)

| Key | Type | TTL | Written by | Read by |
|---|---|---|---|---|
| `extract:pipeline` | LIST | — | triggers (LPUSH) | worker (BRPOP) |
| `extract:pipeline:dead` | LIST | — | worker (3+ retries) | manual only |
| `guidance_lease:{asset}:{source_id}` | STRING | 14400s | daemon | daemon |
| `trade_ready:entries` | HASH | — | trade_ready_scanner | daemon |
| `trade_ready:by_date:{date}` | SET | — | scanner | manual `--show` |
| `trade_ready:scan_log` | STRING | — | scanner | manual |
| `fiscal_quarter:{TICKER}:{FY}:Q{N}` | STRING (JSON) | — | `sec_quarter_cache_loader` | `guidance_write_cli._lookup_sec_cache` |
| `fiscal_quarter:{TICKER}:{FY}:FY` | STRING (JSON) | — | same | same |
| `fiscal_quarter_length:{TICKER}:Q{N}` | STRING (int days) | — | same | `_predict_from_prev_quarter` |
| `fiscal_year_end:{TICKER}` | STRING (JSON) | — | same | `_get_sec_corrected_fye` |
| `fiscal_quarter:{TICKER}:last_refreshed` | STRING (ISO) | — | same | daemon (fill-check) |

---

## §3 — KEDA + K8s

### 3.1 ScaledObject (`extraction-worker.yaml:148-168`)

```yaml
# CHECKED-IN MANIFEST (extraction-worker.yaml:148-168):
scaleTargetRef:  {name: extraction-worker}
minReplicaCount: 1
maxReplicaCount: 7
cooldownPeriod: 300
pollingInterval: 30
triggers:
- type: redis
  metadata:
    address: redis.infrastructure.svc.cluster.local:6379
    listName: extract:pipeline
    listLength: "1"          # one item per pod target → 7 items = 7 pods
    databaseIndex: "0"

# LIVE CLUSTER (verified `kubectl get scaledobject ... -o jsonpath='{.spec}'`):
# minReplicaCount: 0    ← in-cluster patched (NOT what the YAML says)
# All other fields match the manifest.
```

**Checked-in `min=1` rationale** (`extraction-worker.yaml:158`): would prevent KEDA from killing a pod that just BRPOPped an item but hasn't completed yet. The live cluster overrides this to 0.

**Pause mechanism**: the annotation `autoscaling.keda.sh/paused-replicas: "0"` is set on the live ScaledObject — this forces extraction-worker to 0 regardless of queue depth. **This affects ONLY `extraction-worker`** because the ScaledObject's `scaleTargetRef` points exclusively at that Deployment. `guidance-trigger` is at 0 because of a separate manual `kubectl scale deployment guidance-trigger --replicas=0` — there is no KEDA scaler watching it.

### 3.2 Deployment (`extraction-worker.yaml:1-145`)

**Boot command** (lines 32-39):
```bash
cp /mnt/claude-json /home/faisal/.claude.json    # writable copy in emptyDir
export PATH="/home/faisal/.local/bin:$PATH"
source /home/faisal/EventMarketDB/venv/bin/activate
exec python /home/faisal/EventMarketDB/scripts/extraction_worker.py
```

**Resources** (lines 95-101): requests `cpu=250m, memory=512Mi`; limits `cpu=1, memory=2Gi`. Per pod.

**Mounts** (lines 102-118):
| Mount | Source | Mode |
|---|---|---|
| `/home/faisal` | emptyDir | rw (writable home) |
| `/home/faisal/EventMarketDB` | hostPath project dir | rw (live code, no docker bake) |
| `/home/faisal/.local` | hostPath | ro (claude CLI + SDK) |
| `/home/faisal/.claude` | hostPath | rw (OAuth credentials.json) |
| `/mnt/claude-json` | hostPath `.claude.json` file | ro (copied to home on boot) |
| `/app/logs` | hostPath | rw (worker log) |
| `/home/faisal/Obsidian` | hostPath | rw (SubagentStop capture) |

**Env (critical for billing)** (lines 86-89):
```yaml
- name: ANTHROPIC_API_KEY
  value: ""                          # blanks out the one from eventtrader-secrets
- name: CLAUDE_CODE_OAUTH_TOKEN
  value: ""                          # blanks out the one from claude-auth
```
The `envFrom: secretRef` blocks at lines 90-94 mount both secrets. Because `env:` overrides `envFrom:`, the empty strings win. Result: SDK falls through to OAuth via `.credentials.json` (subscription billing) instead of per-token API billing. Per `CLAUDE.md`, this is load-bearing.

**Termination grace** (line 23): `terminationGracePeriodSeconds: 300` — 5-min window for the current extraction to finish before SIGKILL.

**Node pinning** (lines 20-21): `nodeSelector kubernetes.io/hostname: minisforum`. Required because the hostPath mounts only exist on this node.

### 3.3 guidance-trigger Deployment

Separate `k8s/processing/guidance-trigger.yaml`. 1 replica in the manifest, similar mount pattern, no KEDA (always-on, not queue-driven). **Currently scaled to 0 by manual `kubectl scale` — independent of the KEDA pause that holds extraction-worker at 0.** Restoring guidance-trigger requires `kubectl scale deployment guidance-trigger -n processing --replicas=1`. Restoring extraction-worker requires removing the KEDA pause annotation.

---

## §4 — Worker (`scripts/extraction_worker.py`, 800 LOC)

### 4.1 Boot order (lines 32-94)

```python
PROJECT_DIR = "/home/faisal/EventMarketDB"
os.chdir(PROJECT_DIR)                              # MUST happen before SDK import
sys.path.insert(0, PROJECT_DIR)
TYPE_ROOT = Path(PROJECT_DIR) / ".claude" / "skills" / "extract" / "types"

import redis.asyncio as aioredis
from claude_agent_sdk import ClaudeAgentOptions, query
from neograph.Neo4jConnection import get_manager

sys.path.insert(0, str(Path(PROJECT_DIR) / "scripts" / "earnings"))
from run_ledger import (                                # noqa: E402
    VALID_COMPONENTS as _LEDGER_COMPONENTS,
    close_run        as _ledger_close,
    open_run         as _ledger_open,
)
```
`chdir` before SDK import is required because `setting_sources=["project"]` resolves `.claude/` relative to cwd. Note the **aliased imports**: the worker uses `_LEDGER_COMPONENTS`, `_ledger_close`, `_ledger_open` throughout — the unprefixed names from `run_ledger` are NOT in scope.

### 4.2 Configuration constants (lines 66-94)

```python
REDIS_HOST      = "redis.infrastructure.svc.cluster.local"     # env override
REDIS_PORT      = 6379
QUEUE_NAME      = "extract:pipeline"
DEAD_LETTER_QUEUE = "extract:pipeline:dead"
MAX_RETRIES     = 3
MAX_TURNS       = 80                                            # env override
MAX_BUDGET_USD  = 15.0                                          # env override
DEFAULT_MODE    = "write"
MCP_NEO4J_URL   = "http://mcp-neo4j-cypher-http.mcp-services.svc.cluster.local:8000/mcp"
DAILY_INTERACTIVE_PCT        = 10                               # env override
DAILY_INTERACTIVE_PCT_SONNET = 5                                # env override
USAGE_SCRIPT          = scripts/claude_usage_fetch.py
USAGE_SUMMARY_PATH    = logs/claude-usage/claude_usage_summary.json
USAGE_CHECK_INTERVAL  = 300                                     # match script's TTL
USAGE_PAUSE_SLEEP     = 300                                     # sleep when over threshold
RATE_LIMIT_PATTERN    = "hit your limit"
```

### 4.3 Type discovery + model config (lines 163-211)

`discover_allowed_types()` scans `types/` directory (defense-in-depth). `load_type_config(type)` reads `types/{type}/config.yaml`. `resolve_models(config, asset)` (extraction_worker.py:203-211) merges type-level defaults from the config with per-asset overrides — falling back to literal `'sonnet'` only when neither the type config nor the asset block specifies a value:
```python
defaults = {
    "orchestrator": config.get("orchestrator", "sonnet"),
    "primary":      config.get("primary",      "sonnet"),
    "enrichment":   config.get("enrichment",   "sonnet"),
}
asset_overrides = config.get("assets", {}).get(asset, {})
return {k: asset_overrides.get(k, v) for k, v in defaults.items()}
```
For `guidance/news`: returns `{orchestrator: "haiku", primary: "haiku", enrichment: "sonnet"}` (enrichment falls back because news doesn't override it AND news has no enrichment pass anyway).

### 4.4 Usage throttling (lines 96-157, 698-707)

Before every BRPOP:
1. If `claude_usage_summary.json` is stale (>5 min), `claude_usage_fetch.py --json` runs (15-second timeout).
2. For both `seven_day` (all-models) and `seven_day_sonnet` buckets:
   ```
   days_left = max((reset_dt - now_utc) / 86400, 0)
   threshold = max(100 - reserve_pct * days_left, 10)
   if current_pct >= threshold: pause USAGE_PAUSE_SLEEP=300s
   ```
3. Returns `(over, reason)`. On over: log + `asyncio.wait_for(shutdown_event.wait(), timeout=300)`, then `continue` (re-check) or `break` (shutdown).

Net effect: reserves DAILY_INTERACTIVE_PCT% per remaining day for interactive use. Tighter early in the week, relaxes near reset.

### 4.5 `process_one` — atomic per-attempt boundary (lines 411-653)

```
1. Open run-ledger row if type in VALID_COMPONENTS={'guidance','prediction','learning'}
   → run_id (uuid4)
   On exception: log warning, ledger_run_id stays None (non-fatal)

2. STALE-SIDECAR UNLINK (line 458):
   Path(f"/tmp/gu_written_{source_id}.json").unlink(missing_ok=True)
   
   Why: guidance_write_cli.py writes this sidecar but NEVER cleans it up.
   If a previous attempt wrote it and THIS attempt is dry_run (or errors
   before write CLI runs), the stale file would poison items_written in
   the ledger summary. Entry-time unlink guarantees freshness.

3. mark_status('in_progress') on Neo4j source (write mode only)

4. type_config = load_type_config('guidance')
   models = resolve_models(type_config, asset)
   result_path = f"/tmp/extract_result_{type}_{source_id}_{uuid4().hex[:8]}.json"

5. prompt = "/extract {ticker} {asset} {source_id} TYPE={type} MODE={mode}"
          + " PRIMARY_MODEL={primary} ENRICHMENT_MODEL={enrichment}"
          + " RESULT_PATH={result_path}"

6. options = ClaudeAgentOptions(
       cli_path="/home/faisal/.local/bin/claude",
       setting_sources=["project"],
       cwd=PROJECT_DIR,
       permission_mode="bypassPermissions",
       model=models["orchestrator"],
       max_turns=80, max_budget_usd=15,
       stderr=lambda line: stderr_lines.append(line),
       mcp_servers={
         "neo4j-cypher": {
           "type": "http",
           "url": MCP_NEO4J_URL,
           "headers": {"Host": "localhost:8000"}    # required for in-cluster routing
         }
       }
   )

7. async for msg in query(prompt=prompt, options=options):
     msg_type = type(msg).__name__
     
     # Rate-limit scan: every message, content lowercased contains "hit your limit"
     if not rate_limit_detected:
         msg_content = str(getattr(msg, "content", ""))
         if RATE_LIMIT_PATTERN in msg_content.lower():
             rate_limit_detected = True
     
     # Logging:
     if SystemMessage init: log model, apiKeySource, version
     elif ResultMessage: capture result_msg + result_text
     elif AssistantMessage: log model + first 200 chars
     else if hasattr(msg, "content"): log first 200 chars

8. Final rate-limit check on result_text too.

9. If rate_limit_detected:
   - unlink result_path
   - _close_ledger("rate_limited")
   - return "rate_limited"   → caller re-queues without retry penalty

10. If result_text is None: 
    - log stderr_lines[-20:]
    - mark_status('failed', error='No result returned from SDK')
    - _close_ledger("failed", ...)
    - return False

11. read_result_file(result_path, type, source_id):
    - check file exists, parseable JSON
    - require fields {type, source_id, status}
    
    If status='completed': mark_status('completed'), _close_ledger("succeeded", summary=...)
    Else: mark_status('failed', error=result_data.error)
          _close_ledger("failed", error=...)
          return False
    
    On file/parse error: mark_status('failed', error=str(e))
                         _close_ledger("failed", error=str(e))
                         return False
    
    Finally: unlink result_path

12. Build ledger summary (defensive — never demotes success on summary bug):
    {
      items_extracted = primary_items from result file,
      items_written = len(/tmp/gu_written_{source_id}.json),
      enrichment_status ∈ {None, "no_primary", "no_enrichment", "enriched"},
      items_enriched, items_new_secondary    # audit-only
    }
    
13. _close_ledger("succeeded", summary=_summary)
    return True
```

### 4.6 Main loop (lines 696-785)

```python
while not shutdown_event.is_set():
    refresh_usage_cache()
    if is_over_usage_threshold(): pause 300s, re-check
    
    result = await r.brpop(QUEUE_NAME, timeout=5)
    if result is None: continue
    
    # PARSE — bad JSON / non-object payloads are LOGGED AND DROPPED (not dead-lettered).
    try:
        payload = parse_payload(raw_payload)
    except ValueError as e:
        log.error("Payload parse error: %s", e)
        continue                                       # extraction_worker.py:720
    
    # VALIDATE — missing-field / disallowed-type errors ARE dead-lettered.
    try:
        validate_payload(payload)
    except ValueError as e:
        log.error("Payload validation error: %s — dead-lettering", e)
        payload["_error"] = str(e)
        payload["_failed_at"] = utcnow().isoformat() + "Z"
        await r.lpush(DEAD_LETTER_QUEUE, json.dumps(payload))
        continue                                       # extraction_worker.py:731
    
    outcome = await process_one(...)
    
    if outcome == "rate_limited":
        r.lpush(QUEUE_NAME, json.dumps(payload))       # re-queue, no retry++
        await wait_for(shutdown_event, timeout=300); continue
    
    if not outcome:
        retry_count = payload.get('_retry', 0) + 1
        if retry_count <= 3:
            payload['_retry'] = retry_count
            r.lpush(QUEUE_NAME, json.dumps(payload))
        else:
            payload['_retry'] = retry_count
            payload['_error'] = error_message
            payload['_failed_at'] = utcnow().isoformat() + "Z"
            r.lpush(DEAD_LETTER_QUEUE, json.dumps(payload))
            mark_status('failed', error='Exhausted 3 retries')
```

### 4.7 `mark_status` (lines 261-280)

```cypher
MATCH (alias:Label {id: $sid})
SET alias.{type}_status = $status [, alias.{type}_error = $error]
RETURN count(alias) AS affected
```
Raises if `affected != 1`. Dynamic property name from `f"{type_name}_status"`.

### 4.8 `_build_guidance_summary` (lines 349-405)

```python
items_written = len(json.loads(Path(f'/tmp/gu_written_{source_id}.json').read_text()))
                # None if file missing or malformed (won't fabricate)

if all (primary_items, enriched_items, new_secondary_items) None:
    enrichment_status = None
elif primary_items == 0:
    enrichment_status = "no_primary"
elif (enriched_items or 0) + (new_secondary_items or 0) == 0:
    enrichment_status = "no_enrichment"
else:
    enrichment_status = "enriched"
```
The freshness guarantee comes from the stale-sidecar unlink at the start of `process_one`.

### 4.9 Graceful shutdown (lines 244-255)

```python
signal.SIGTERM → shutdown_event.set()
signal.SIGINT  → shutdown_event.set()
```
Loop drops out, current `process_one` continues. K8s 300s grace covers ~one full extraction (~3-8 min typical).

---

## §5 — Orchestrator: `/extract` skill (`.claude/skills/extract/SKILL.md`, 64 LOC)

```yaml
description: "Generic extraction orchestrator..."
disable-model-invocation: true                  # Claude can't auto-call /extract
argument-hint: "TICKER ASSET SOURCE_ID TYPE= MODE= PRIMARY_MODEL= ENRICHMENT_MODEL="
```

Body:
1. **Step 1**: Spawn `extraction-primary-agent`. Pass `model=PRIMARY_MODEL` only if provided (else agent frontmatter default `sonnet` applies). Read `/tmp/extract_pass_{TYPE}_primary_{SOURCE_ID}.json`. If status=failed → skip enrichment.
2. **Step 2 — Enrichment gate**: run enrichment ONLY IF BOTH files exist:
   - `types/{TYPE}/enrichment-pass.md`
   - `types/{TYPE}/assets/{ASSET}-enrichment.md`

   Only `guidance/transcript-enrichment.md` exists → enrichment only fires for transcripts.
3. **Step 3**: combine results. If `RESULT_PATH=` was provided (worker invocation), write the combined JSON. Else (manual invocation), report as text. Clean up `/tmp/extract_pass_*` files.

Top of body says `ALWAYS use ultrathink` — verbal cue for max reasoning depth.

---

## §6 — Agent Shells (`.claude/agents/extraction-{primary,enrichment}-agent.md`)

Both identical structure (66/69 LOC):
```yaml
tools:
  - mcp__neo4j-cypher__read_neo4j_cypher       # READ-ONLY MCP
  - Bash
  - TaskList, TaskGet, TaskUpdate
  - Write
  - Read
model: sonnet                                    # fallback when orchestrator doesn't pass model=
permissionMode: dontAsk
```

Guardrails (in agent body):
1. **NEVER** call `mcp__neo4j-cypher__write_neo4j_cypher` — graph writes go through Bash → `guidance_write.sh`.
2. **MUST** invoke deterministic Python scripts via Bash — never compute IDs/units/periods manually.
3. Enrichment agent has additional rule: **ONLY write changed/new items** (not unchanged readback).

The lack of `write_neo4j_cypher` in `tools:` is the **primary** guardrail keeping agents from direct graph mutation. The Pre-tool hook `guard_neo4j_delete.sh` (§22) is defense-in-depth — won't fire here because the tool isn't even available.

---

## §7 — 8-Slot Loader (the architectural keystone)

Both agents load these 8 files before any work. **Slot 4 is optional** — silently skipped if missing.

| Slot | File path template | Scope | What it provides |
|---|---|---|---|
| 1 | `types/{TYPE}/core-contract.md` | type | Reference: schema, IDs, fields, validation |
| 2 | `types/{TYPE}/{primary,enrichment}-pass.md` | type×pass | **Working brief — follow start to finish** |
| 3 | `assets/{ASSET}.md` | asset | Data structure (nodes, properties, layers, fetch order) |
| 4 | `types/{TYPE}/assets/{ASSET}-{pass}.md` | type×asset×pass | Intersection rules (extraction rules for THIS type on THIS asset) |
| 5 | `queries-common.md` | global | Shared Cypher (context, caches, inventory, fulltext) |
| 6 | `assets/{ASSET}-queries.md` | asset | Asset-specific source fetch queries |
| 7 | `types/{TYPE}/{TYPE}-queries.md` | type | Type-specific lookup queries |
| 8 | `evidence-standards.md` | global | 4 anti-hallucination rules |

**Slot 4 decouples extraction rules from asset structure**. Asset profiles (slot 3) describe HOW to read; intersection files (slot 4) describe WHAT to extract for a given type×asset combination. Without slot 4, the system would have to contaminate asset profiles with type-specific rules and lose reusability for future types.

---

## §8 — Guidance Type — Complete Schema

### 8.1 Node types

| Label | Created by pipeline? | id formula | Notes |
|---|---|---|---|
| `Guidance` | yes (MERGE) | `"guidance:" + slug(label)` | one per metric |
| `GuidanceUpdate` | yes (MERGE) | slot ID — §9 | one per deterministic slot (source × metric × period × basis × segment); duplicate mentions within the same source MERGE into one node |
| `GuidancePeriod` | yes (MERGE) | calendar dates or sentinel | calendar-based, company-agnostic |
| `Company`, `Concept`, `Member`, `Report`, `Transcript`, `News` | no (MATCH only) | — | pre-existing graph entities |

### 8.2 Edges (6 total)

```
(GuidanceUpdate)-[:UPDATES]->(Guidance)                          # always
(GuidanceUpdate)-[:FROM_SOURCE]->(Report|Transcript|News)        # always (provenance)
(GuidanceUpdate)-[:FOR_COMPANY]->(Company)                       # always (direct, no Context)
(GuidanceUpdate)-[:HAS_PERIOD]->(GuidancePeriod)                 # always (1:1)
(GuidanceUpdate)-[:MAPS_TO_CONCEPT]->(Concept)                   # 0..1 (multi-taxonomy: 1 chosen)
(GuidanceUpdate)-[:MAPS_TO_MEMBER]->(Member)                     # 0..N (multi-dimensional segments)
```

### 8.3 Live constraints + indexes (verified 2026-05-22)

```cypher
-- CONSTRAINTS (created in guidance_writer.create_guidance_constraints, lines 492-524)
CREATE CONSTRAINT guidance_update_id_unique         -- present ✓
CREATE CONSTRAINT guidance_period_id_unique         -- present ✓
CREATE CONSTRAINT constraint_guidance_id_unique     -- present ✓ (live name has 'constraint_' prefix)
```

**Naming note**: the `guidance_id_unique` constraint declared at `guidance_writer.py:499-501` shows up in the live graph under the name `constraint_guidance_id_unique` (the live Neo4j instance prefixed it). All three uniqueness constraints are enforced — `count(g)=548, count(DISTINCT g.id)=548` confirms zero duplicate Guidance.id values.

**Small denormalization drift**: `count(DISTINCT gu.label)=552` but `count(g)=548` — 4 distinct `GuidanceUpdate.label` values exist that don't have a matching Guidance node with the same exact label. This is denormalization drift on the GU side (likely casing/spacing variants), NOT a constraint issue. The Guidance side is clean.

**Indexes** (all ONLINE):
```
guidance_update_id_unique     (backing constraint)
guidance_period_id_unique     (backing constraint)
gu_label_slug                 (RANGE on GuidanceUpdate.label_slug)
gu_segment_slug               (RANGE on GuidanceUpdate.segment_slug)
```

### 8.4 Sentinel GuidancePeriod nodes (verified live)

Created idempotently by `create_guidance_constraints` (`guidance_writer.py:512-521`):
```cypher
MERGE (gp:GuidancePeriod {id: 'gp_ST'})     SET gp.u_id='gp_ST',    gp.start_date=null, gp.end_date=null
MERGE (gp:GuidancePeriod {id: 'gp_MT'})     SET gp.u_id='gp_MT',    ...
MERGE (gp:GuidancePeriod {id: 'gp_LT'})     SET gp.u_id='gp_LT',    ...
MERGE (gp:GuidancePeriod {id: 'gp_UNDEF'})  SET gp.u_id='gp_UNDEF', ...
```
All 4 present in live graph ✓.

### 8.5 GuidanceUpdate properties (full inventory)

| Property | Type | Source | Notes |
|---|---|---|---|
| `id` | String | CLI | `gu:{source_id}:{label_slug}:{period_u_id}:{basis_norm}:{segment_slug}` |
| `evhash16` | String | CLI | SHA-256 first 16 hex chars |
| `label` | String | agent | Human-readable metric name |
| `label_slug` | String | CLI | `slug(label)` |
| `segment` | String | agent | "Total" default |
| `segment_slug` | String | CLI | `slug(segment)` |
| `given_date` | String | writer | Derived from source node (transcript→conference_datetime; else created) — UTC normalized in Cypher: `toString(datetime({epochMillis: datetime(raw).epochMillis}))` |
| `period_scope` | enum | CLI | quarter/annual/half/monthly/long_range/short_term/medium_term/long_term/undefined |
| `time_type` | enum | CLI | duration/instant |
| `fiscal_year` | Integer | agent | — |
| `fiscal_quarter` | Integer/null | agent | 1-4 |
| `low`, `mid`, `high` | Float/null | CLI (canonicalized) | mid auto-computed if low+high given |
| `canonical_unit` | enum | CLI | usd/m_usd/percent/percent_yoy/percent_points/basis_points/x/count/unknown |
| `unit_raw` | String/null | writer | Set only when canonical_unit='unknown' (`guidance_writer.py:347`) |
| `basis_norm` | enum | agent | gaap/non_gaap/constant_currency/unknown |
| `basis_raw` | String/null | agent | Verbatim qualifier |
| `derivation` | enum | agent | explicit/calculated/point/implied/floor/ceiling/comparative |
| `qualitative` | String/null | agent | "low to mid single digits" |
| `quote` | String | agent | ≤500 chars, with `[PR]`/`[Q&A]`/`[8-K]`/`[10-Q]`/`[10-K]`/`[News]` prefix |
| `section` | String | agent | location within source |
| `source_key` | String | agent | sub-document key |
| `source_type` | String | agent | matches `{ASSET}` |
| `conditions` | String/null | agent | "assumes no further rate hikes" |
| `xbrl_qname` | String/null | CLI | XBRL concept, CLI-resolved |
| `concept_family_qname` | String/null | CLI | Family anchor for derived metrics |
| `source_refs` | String[] | agent | Sub-source IDs (PreparedRemark/QAExchange IDs), accumulated via SET reduce |
| `created` | String | writer | ON CREATE SET only |
| `resolved_kind` | enum/null | CLI v2 | money/ratio/count/multiplier/unknown |
| `resolved_money_mode` | enum/null | CLI v2 | aggregate/price_like/unknown |
| `resolved_ratio_subtype` | enum/null | CLI v2 | percent/percent_yoy/percent_points/basis_points |
| `resolution_version` | "v2"/null | CLI v2 | Marker — only on V2-written rows |

**Live distribution of resolution_version**: 8,198 null (V1 legacy) vs 234 v2. Only 2.8% of GU rows are V2-resolved — historical data was written before V2.

---

## §9 — Naming Logic (`guidance_ids.py:21-26`, `core-contract.md` §4)

### 9.1 `slug()` function
```python
def slug(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = re.sub(r'_+', '_', s)
    return s.strip('_')
```
Examples: `"Operating Margin"` → `"operating_margin"`, `"D&A"` → `"d_a"`, `"FCF (non-GAAP)"` → `"fcf_non_gaap"`.

### 9.2 How agents pick `label`

Constrained by 4 mechanisms in this order:
1. **Reuse existing tags** — query 7A (`guidance-queries.md:13-18`) loads all distinct `Guidance.label` values for the company. Brief explicitly tells agent to reuse canonical names (`primary-pass.md:22`).
2. **12-metric canonical table** — `core-contract.md` §4 lists Revenue/EPS/Gross Margin/Operating Margin/Operating Income/Net Income/OpEx/Tax Rate/CapEx/FCF/OINE/D&A with aliases. Non-exhaustive — agent creates new base metrics freely.
3. **Metric decomposition** (`core-contract.md` §4 lines 222-237):
   - Decompose when qualifier is a business dimension: "iPhone Revenue" → label=Revenue, segment=iPhone
   - Don't decompose when qualifier changes the metric: "Cost of Revenue" → label="Cost of Revenue", segment="Total"
   - Test: "Could you have this metric for iPhone AND for Total?" If yes → segment.
4. **Default segment** = "Total". Always present. `segment_slug = "total"`.

### 9.3 GuidanceUpdate slot ID

```
gu:{source_id}:{label_slug}:{period_u_id}:{basis_norm}:{segment_slug}
```
Canonicalization before concat (`guidance_ids.py:607-609` and elsewhere):
- `source_id`: `.strip().replace(':', '_')` for delimiter safety
- `label_slug`: `slug(label)`
- `period_u_id`: `gp_YYYY-MM-DD_YYYY-MM-DD` or sentinel `gp_ST/MT/LT/UNDEF`
- `basis_norm`: enum value `gaap|non_gaap|constant_currency|unknown` as-is
- `segment_slug`: `slug(segment)` or `"total"` if empty

### 9.4 Evidence hash (`guidance_ids.py:583-602`)
```python
parts = [
    _normalize_numeric(low),      # int(x) if x.is_integer() else f"{x:g}", null→'.'
    _normalize_numeric(mid),
    _normalize_numeric(high),
    canonical_unit,                 # enum value
    _normalize_text(qualitative),   # lowercase + collapse-whitespace, null→'.'
    _normalize_text(conditions),
]
sha256('|'.join(parts).encode('utf-8')).hexdigest()[:16]
```
Stored as property, **not in ID**. Change detection without affecting slot.

### 9.5 Idempotency invariant

Same slot ID = same node. `MERGE` matches, `SET` overwrites all properties. Re-running with richer data → same ID, better properties.

---

## §10 — Period Resolution (`guidance_write_cli.py:_ensure_period` lines 203-292)

The agent only emits LLM period fields (`fiscal_year`, `fiscal_quarter`, `half`, `month`, `long_range_*_year`, `calendar_override`, `sentinel_class`, `time_type`). The CLI runs a **4-step cascade**:

```python
def _ensure_period(item, fye_month, ticker=None):
    if item.get('period_u_id'): return item        # pre-computed → trust it
    
    is_standard_period = (
        item.get('time_type') != 'instant'
        and not item.get('half')
        and not item.get('month')
        and not item.get('sentinel_class')
        and not item.get('long_range_end_year')
    )
    
    # Step A — Reuse existing (first-write-wins dedup)
    if is_standard_period and ticker and fiscal_year:
        existing = _lookup_existing_period(ticker, fy, fq)
        # Cypher: MATCH (gu)-[:FOR_COMPANY]->(c:Company {ticker})
        #         WHERE gu.fiscal_year=$fy AND gu.fiscal_quarter=$fq
        #         MATCH (gu)-[:HAS_PERIOD]->(gp)
        #         WITH gp, count(gu) AS ref_count
        #         ORDER BY ref_count DESC, gp.end_date DESC, gp.u_id
        #         LIMIT 1
        if existing: return item  # populated with existing dates
    
    # Step B — SEC cache (exact dates from real SEC filings)
    if is_standard_period and ticker and fy:
        suffix = f"Q{fq}" if fq else "FY"
        sec_dates = _lookup_sec_cache(ticker, fy, suffix)
        # Redis: GET fiscal_quarter:{ticker}:{fy}:{suffix}
        if sec_dates:
            item['period_u_id'] = f"gp_{start}_{end}"
            return item
    
    # Step C — Predict from previous quarter (unfiled quarters)
    if is_standard_period and ticker and fy and fq:
        predicted = _predict_from_prev_quarter(ticker, fy, fq)
        # prev_q_data = Redis GET fiscal_quarter:{ticker}:{prev_fy}:Q{prev_q}
        # length = Redis GET fiscal_quarter_length:{ticker}:Q{fq}
        # start = prev.end + 1d
        # end = start + length - 1
        if predicted:
            item['period_u_id'] = f"gp_{start}_{end}"
            return item
    
    # Step D — FYE math (last resort: sentinels, long_range, half, monthly, uncached)
    effective_fye = fye_month
    if ticker:
        sec_fye = _get_sec_corrected_fye(ticker)
        # Redis: GET fiscal_year_end:{ticker} → {month_adj: ...}
        # month_adj handles 52/53-week calendars: DD<=5 → prior month
        if sec_fye is not None:
            effective_fye = sec_fye
    
    period = build_guidance_period_id(
        fye_month=effective_fye, fiscal_year=..., fiscal_quarter=..., 
        half=..., month=..., long_range_start_year=..., long_range_end_year=...,
        calendar_override=..., sentinel_class=..., time_type=..., label_slug=...
    )
```

### 10.1 `build_guidance_period_id` (`guidance_ids.py:688-789`)

Priority order (first match wins):
1. `sentinel_class` set → `gp_{ST|MT|LT|UNDEF}`, null dates
2. `long_range_end_year` set → FY-based dates (uses `long_range_start_year` if also set, else single year)
3. `month` set → `{year}-{month:02d}-01` to `{year}-{month:02d}-{last_day:02d}` (no FYE needed)
4. `half` set → Q1.start to Q2.end (H1) or Q3.start to Q4.end (H2) via `_compute_fiscal_dates`
5. `fiscal_quarter` set → `_compute_fiscal_dates(fye, fy, f"Q{q}")`
6. `fiscal_year` set (only) → `_compute_fiscal_dates(fye, fy, "FY")`
7. Fallthrough → `gp_UNDEF` + warning

### 10.2 Instant items (`guidance_ids.py:675-678`, `791-809`)

```python
KNOWN_INSTANT_LABELS = {'cash_and_equivalents', 'total_debt', 'long_term_debt',
                        'shares_outstanding', 'book_value', 'net_debt'}
is_instant = (time_type == 'instant') or (label_slug in KNOWN_INSTANT_LABELS)
```
For instant: `start_date = end_date` (collapse to single day) → `gp_{end_date}_{end_date}`.

### 10.3 `_compute_fiscal_dates` (`fiscal_math.py:102-140`)

Pure deterministic FYE → calendar mapping. No DB calls. Q1 starts at `(fye_month % 12) + 1`. Returns ISO-format `(start, end)` tuple, with month-end accuracy via `calendar.monthrange`.

### 10.4 SEC cache loader (`scripts/sec_quarter_cache_loader.py`, 338 LOC)

**Source**: SEC EDGAR XBRL `companyconcept` endpoint, polled at ≤10 req/sec with 0.12s sleep (line 62). User-Agent required.

**Cascade for primary concept** (lines 237-243):
1. `EarningsPerShareBasic` (most companies report this)
2. Fallback: `NetIncomeLoss`

**Pipeline** (lines 246-251):
```
_parse_concept_units      → list of {fy, fp, start, end, filed, span}
_filter_and_dedupe        → Q1-Q3 (60-130d), FY (300-400d); keep latest (end, filed) per (fy,fp)
_derive_q4                → Q4.start = Q3.end + 1d; Q4.end = FY.end; validate 60-130d span
_compute_median_lengths   → for each Q_N: median(end - start + 1) across years
_apply_fye_adjustment     → "0201" raw FYE + DD<=5 → month_adj=1 (handles 52-week)
```

**Writes** (lines 259-267):
```python
SET fiscal_quarter:{TICKER}:{FY}:{Q1..Q4|FY}      = {"start": ..., "end": ...}
SET fiscal_quarter_length:{TICKER}:Q{N}            = "91"
SET fiscal_year_end:{TICKER}                       = {"raw":"0201","month_adj":1}
SET fiscal_quarter:{TICKER}:last_refreshed         = iso utc now
```

---

## §11 — Unit Resolution (V1 + V2)

### 11.1 V1 path (`guidance_ids.py:461-548`)

```python
def canonicalize_unit(unit_raw, label_slug):
    u = unit_raw.lower().strip()
    if u in CANONICAL_UNITS:           # already canonical
        canonical = u
    elif u in UNIT_ALIASES:            # look up alias map
        canonical = UNIT_ALIASES[u]
    else:
        canonical = 'unknown'
    
    # Per-share override: per-share labels force usd, never m_usd
    if canonical == 'm_usd' and _is_per_share_label(label_slug):
        return 'usd'
    
    # Share-count override: share-count labels with scale words → count, not m_usd
    if canonical == 'm_usd' and _is_share_count_label(label_slug):
        return 'count'
    
    return canonical
```

**Per-share detector** (`guidance_ids.py:67-84`):
```python
def _is_per_share_label(label_slug):
    return (label_slug in ('eps', 'dps')
            or label_slug.startswith(('eps_', 'dps_'))
            or label_slug.endswith(('_eps', '_dps'))
            or 'per_share' in label_slug
            or 'per_unit' in label_slug)
```
**⚠️ Known gap** (`guidance-upstream-unit-misclassification.md` Trace A, **2026-04-02 snapshot from the Infra_Bugs doc — re-verify before acting on it**): misses **infix** variants like `adjusted_eps_diluted` because the slug doesn't end in `_eps` and doesn't start with `eps_`. At that snapshot, 141 rows were incorrectly stored as `m_usd`, split as: **75 share-count rows that should be `count`**, **10 count-like rows that should be `count`**, and **56 per-unit-price rows that should be `usd`**. The graph has grown since (8,291 → 8,432 rows); the misclassified-`m_usd` total has likely drifted slightly. See §27.2 for the most recent test-script verification.

**Share-count detector** (`guidance_ids.py:99-116`):
```python
def _is_share_count_label(label_slug):
    return (label_slug in {'share_count', 'shares_outstanding'}
            or label_slug.endswith('_share_count')
            or label_slug.endswith('_shares'))
```
**⚠️ Known gap**: misses `weighted_average_basic_shares_outstanding` (ends in `_outstanding` not `_shares`), `loyalty_members`, `hsa_count`, `total_accounts`, `community_count`.

**Canonicalize value** (`guidance_ids.py:495-548`):
- If canonical=`count` and share-count label and scale word present → `value * multiplier * 1e6`
- Else if not currency → passthrough
- If per-share → no scaling (already in face dollars)
- If aggregate currency → `value * multiplier_to_millions`
- Pre-scale guard: `multiplier>1 and value>999` → raise ValueError (catches double-scaling)

### 11.2 V2 path (`guidance_ids.py:119-373`, env `GUIDANCE_UNIT_RESOLUTION_MODE=v2`)

3-axis evidence resolution:

**Axis 1 — `resolved_kind`** (`_resolve_kind`, lines 254-299):
```
P1: ratio surface in unit_raw (%, "basis point", "year over year", pct, yoy, bp, bps, pp, ppts)
P2: multiplier surface (x, "2.5x", times, multiple)
P3: money surface ($, usd, dollar, cent)
P4-P5: XBRL evidence (count via SharesOutstanding/ShareCount/WeightedAverage*Shares; money via PerShare markers)
hard_evidence = {P1, P2, P3, P4, P5 hits}
if |hard_evidence| > 1: return 'unknown'  # contradiction → fail-closed
if hard_evidence: return hard_evidence.pop()
P6: label evidence (precedence only — eps/dps token, per_share/per_unit in slug)
P7: LLM unit_kind_hint
P8: count prior (shares_outstanding, share_count, headcount)
P9: fallback 'unknown'
```

**Axis 2 — `resolved_money_mode`** (`_resolve_money_mode`, lines 302-326): only runs when `resolved_kind='money'`:
```
P1-P2: XBRL per-share markers OR surface "per X" → 'price_like'
P3: hard label signal (per/eps/dps token, per_share/per_unit) → 'price_like'
P4: LLM money_mode_hint
P5: narrow priors {asp, adr, arpu, revpar} → 'price_like'
P6: fallback 'aggregate'
```

**Axis 3 — `resolved_ratio_subtype`** (`_resolve_ratio_subtype`, lines 329-359): only when `resolved_kind='ratio'`:
```
P1: bps markers (bp, bps, "basis point") → 'basis_points'
P2: points markers (pp, ppt, ppts, point, points, "percentage point") → 'percent_points'
P3: YoY markers (yoy, y/y, yr/yr, year-over-year) in unit_raw → 'percent_yoy'
P3-secondary: YoY markers in quote → 'percent_yoy'  (quote ONLY for temporal context)
P4: fallback 'percent'
```

**Axes → canonical_unit** (`_combine_resolved_unit`, lines 362-373):
```
money + price_like  → usd
money + aggregate   → m_usd
ratio + subtype     → subtype value
count               → count
multiplier          → x
unknown             → unknown
```

**Scale functions** (lines 376-415):
- `_scale_aggregate_money`: factor / 1e6 (cents not allowed); pre-scaled guard `factor>1 and value>999` → raise
- `_scale_price_like_money`: factor as-is (no millions); no pre-scaled guard (per-share can legitimately be large)
- `_scale_count_absolute`: factor as-is; pre-scaled guard `factor>1e6 and value>999` → raise

### 11.3 Existing-axis fallback (V2 only, lines 896-903)

If current resolution returns `unknown` but row has prior `resolution_version='v2'` AND same `guidance_id` AND existing `resolved_kind != 'unknown'` → inherit prior resolved values. Stabilizes re-extractions.

### 11.4 Pre-V2 readback skip (`guidance_write_cli.py:330-338`)

In v2 mode, items with `payload_origin='readback'` that lack hints AND lack unit_raw AND aren't already v2 → skipped with error `"pre_v2_readback_skip"`. Protects historical V1 data from being corrupted by V2 re-resolution.

### 11.5 Validation hints (`guidance_write_cli.py:307-327`)

For `payload_origin='extract_v2'`:
- `unit_kind_hint` REQUIRED, must be in `{money, ratio, count, multiplier, unknown}`
- If `unit_kind_hint='money'`: `money_mode_hint` REQUIRED in `{aggregate, price_like, unknown}`
- `money_mode_hint` only allowed when kind is money
- Numeric items (any of low/mid/high non-null) must have non-empty `unit_raw` (not literal "unknown")

### 11.6 Live coverage (verified 2026-05-22)

```
Total GuidanceUpdate:       8,432
canonical_unit='unknown':   1,671 rows (19.8%)
canonical_unit='m_usd':     2,860 rows
resolution_version='v2':      234 (2.8%)
resolution_version IS NULL: 8,198 (legacy V1 writes)
```
**Bug** documented in `guidance-upstream-unit-misclassification.md` (snapshot 2026-04-02 — counts have drifted slightly since): 472 numeric "unknown" rows have inferable types (EPS 72, Dividend Per Share 64, Adjusted EPS 50, etc.). Many have unit_raw="per share" but `per share` isn't in `UNIT_ALIASES` so it falls through to `unknown`. Per-share override only fires when canonical is already `m_usd`, not when canonical is `unknown`.

---

## §12 — Concept Resolution (`concept_resolver.py`, 442 LOC)

### 12.1 Registries

**`CONCEPT_CANDIDATES`** (lines 23-254): **65 entries** (doc says 49 — stale). Ordered tuple per label_slug. Example:
```python
'capex': ('PaymentsToAcquirePropertyPlantAndEquipment',
          'CapitalExpenditure',
          'PaymentsToAcquireProductiveAssets'),
```

**`NULL_QNAME_LABELS`** (lines 257-263): forces `xbrl_qname=None`. **5 entries**:
```python
{'adjusted_ebitda', 'ebitda', 'fcf', 'free_cash_flow', 'operating_margin'}
```

**`NULL_QNAME_SUFFIXES`** (lines 265-269): forces null for slugs ending in:
```python
('_change', '_growth', '_yoy')
```

**`CONCEPT_FAMILY`** (lines 375-402): **19 entries**, maps derived metric label_slug → canonical XBRL anchor.

**`FAMILY_PREFIXES`** (line 404): `('adjusted_', 'non_gaap_', 'gaap_', 'basic_', 'diluted_')`
**`FAMILY_SUFFIXES`** (line 405): `('_growth', '_change', '_yoy')`

### 12.2 `resolve_xbrl_qname` (lines 294-324)

```
if label_slug in NULL_QNAME_LABELS: return FORCE_NULL_CONCEPT
if label_slug.endswith(NULL_QNAME_SUFFIXES): return FORCE_NULL_CONCEPT
candidates = CONCEPT_CANDIDATES.get(label_slug)
if not candidates: return UNHANDLED_CONCEPT  # preserve agent's value
for candidate in candidates:
    hits = [row for row in concept_rows if _local_name(row.qname) == candidate]
    if not hits: continue
    hits.sort(key=lambda r: (-int(r.usage or 0), r.qname))
    if len(hits) > 1 and hits[0].usage == hits[1].usage:
        return None  # ambiguity → fail-closed
    return hits[0].qname  # full namespaced form, e.g. 'us-gaap:Revenues'
return None  # all candidates exhausted
```

### 12.3 `apply_concept_resolution` (lines 327-367)

```
if not concept_rows: return items                # no cache → no-op (no fallback)

cache_qnames = {row['qname'] for row in concept_rows}

for item in items:
    label_slug = item.get('label_slug') or slug(item.get('label', ''))
    resolved = resolve_xbrl_qname(label_slug, concept_rows)
    
    if resolved is UNHANDLED_CONCEPT: continue       # keep agent qname
    
    current = item.get('xbrl_qname')
    
    if resolved is FORCE_NULL_CONCEPT:
        item['xbrl_qname'] = None                    # always null
        continue
    
    if resolved is None:                              # reviewed label, no winner
        if not current or current not in cache_qnames:
            item['xbrl_qname'] = None
        # else: preserve "survivor" (agent found valid concept resolver doesn't know)
        continue
    
    if current != resolved:
        if current and current in cache_qnames:
            log_warning(f"overwriting agent qname '{current}' with '{resolved}'")
        item['xbrl_qname'] = resolved
```

### 12.4 Concept inheritance (`guidance_write_cli.py:527-535`)

```python
concept_map = {}
for item in period_items:
    label_key = item.get('label_slug') or slug(item.get('label', ''))
    if item.get('xbrl_qname') and label_key:
        concept_map.setdefault(label_key, item['xbrl_qname'])  # first-wins

for item in period_items:
    label_key = item.get('label_slug') or slug(item.get('label', ''))
    if not item.get('xbrl_qname') and label_key in concept_map:
        item['xbrl_qname'] = concept_map[label_key]
```
If Revenue/iPhone resolves but Revenue/Mac doesn't → Mac inherits. **Same metric label = same concept regardless of segment.**

### 12.5 `resolve_concept_family` (lines 408-442)

```
if label_slug in CONCEPT_FAMILY: return CONCEPT_FAMILY[label_slug]  # direct
base = label_slug
for suffix in FAMILY_SUFFIXES:                            # strip _growth/_change/_yoy
    if base.endswith(suffix): base = base[:-len(suffix)]; break
for prefix in FAMILY_PREFIXES:                            # strip adjusted_/non_gaap_/etc.
    if base.startswith(prefix): base = base[len(prefix):]; break
if base != label_slug and base in CONCEPT_FAMILY: return CONCEPT_FAMILY[base]
return xbrl_qname                                         # metric is its own family
```

### 12.6 Live coverage

```
CONCEPT_CANDIDATES = 65, CONCEPT_FAMILY = 19

GuidanceUpdate (8,432 total):
  with xbrl_qname property:    4,148 (49.19%)
  with MAPS_TO_CONCEPT edge:    4,155 (49.28%)  -- edge slightly higher: 7 stale edges
  with concept_family_qname:    5,160 (61.20%)

Bucket breakdown (from guidance-xbrl-reviewed-coverage-gaps.md, 2026-04-02):
  reviewed labels with non-null qname:  2,643
  reviewed labels with null qname:        128
  force-null-by-policy with non-null:       4  (Guard misses)
  force-null-by-policy with null:       1,390  (correct)
  unhandled with non-null qname:        1,276  (agent survivors)
  unhandled with null qname:            2,850  (long tail not in registry)
```

**4,797 `:MAPS_TO_CONCEPT` edges total**: more edges than GU-with-qname because some GUs are linked to multiple Concept nodes (multi-taxonomy years).

**Known gaps** (`guidance-xbrl-reviewed-coverage-gaps.md`):
1. `adjusted_eps`, `non_gaap_eps`, `effective_tax_rate`, `net_sales`, `diluted_share_count` all have high volume but aren't in `CONCEPT_CANDIDATES` — they resolve via agent survivors only.
2. **Reviewed survivors**: agent found valid qnames the resolver doesn't know (e.g., `capex` → `nfe:CapitalExpenditures`).
3. **No live fallback** when cache is missing or empty. Member resolution has a live fallback; concept does not.
4. **Cache scope limited to 10-K + 10-Q + numeric facts + consolidated contexts**. 8-K-driven guidance with metrics not in those filings can't resolve.

---

## §13 — Member Resolution (`guidance_write_cli.py:405-453`, `563-602`)

### 13.1 Warmup builds map (`warmup_cache.py:178-200`)

```cypher
-- QUERY_MEMBER_MAP — CIK-prefix lookup, handles zero-padding
MATCH (c:Company {ticker: $ticker})
WITH toString(c.cik) AS cik
WITH cik, CASE WHEN cik =~ '^0+[1-9].*' THEN toString(toInteger(cik)) ELSE cik END AS cik_stripped
MATCH (m:Member)
WHERE m.u_id STARTS WITH cik_stripped + ':' OR m.u_id STARTS WITH cik + ':'
RETURN m.label, m.qname, head(collect(m.u_id)) AS u_id
```
Then `_build_member_map`:
```python
member_map = {}
for row in rows:
    norm = normalize_for_member_match(row['label'])
    if norm: member_map.setdefault(norm, []).append(row['u_id'])
```
Written to `/tmp/member_map_{TICKER}.json`.

### 13.2 `normalize_for_member_match` (`guidance_ids.py:553-559`)

```python
def normalize_for_member_match(s):
    n = re.sub(r'[^a-z0-9]', '', s.lower().replace('&', 'and'))
    n = n.replace('member', '').replace('segment', '')
    if n.endswith('s'): n = n[:-1]  # singularization
    return n
```
"Cloud Services Member" → "cloudservice". "iPhone Segment" → "iphone".

### 13.3 `_apply_member_map` (lines 405-423)

```python
for item in items:
    seg = item.get('segment', 'Total')
    if seg and seg != 'Total':
        item['member_u_ids'] = []                  # CLEAR — agent claims discarded
        norm_seg = normalize_for_member_match(seg)
        if norm_seg not in member_map:
            norm_seg = aliases.get(norm_seg, norm_seg)  # per-ticker alias overrides
        if norm_seg in member_map:
            item['member_u_ids'] = member_map[norm_seg]   # ALL u_ids for this label
```

### 13.4 Per-ticker aliases (`guidance_write_cli.py:393-402`)

`/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts/segment_aliases/{TICKER}.json` — optional `{normalized_seg: alias}` map. If file missing/malformed → empty dict (graceful).

### 13.5 Live fallback (write mode only, lines 426-453)

When `/tmp/member_map_{TICKER}.json` is missing in write mode → `_build_live_member_map` runs the same CIK query against Neo4j and builds the map in-memory.

### 13.6 Dry-run + missing map = graceful skip

Member edges silently absent. No Neo4j fallback in dry-run mode.

### 13.7 Live coverage

```
Total GuidanceUpdate:       8,432
Non-Total segments:           912 (10.82%)
With MAPS_TO_MEMBER edge:     387 (42.43% of non-Total, 4.59% of total)
Total :MAPS_TO_MEMBER edges:  460   -- some GUs have multi-dim segments
```

---

## §14 — Asset Profiles + Queries

### 14.1 Transcript (`assets/transcript.md` + `transcript-queries.md`)

**Node structure**:
- `Transcript-[:HAS_PREPARED_REMARKS]->PreparedRemark` (single content blob)
- `Transcript-[:HAS_QA_EXCHANGE]->QAExchange` (array, with sequence)
- `Transcript-[:HAS_QA_SECTION]->QuestionAnswer` (fallback for **88** transcripts, verified 2026-05-22)
- `Transcript-[:HAS_FULL_TEXT]->FullTranscriptText` (**68** nodes, last-resort, verified 2026-05-22)

**Queries**:
- 3A: list all transcripts for ticker (date-range optional)
- 3B: **primary fetch** — JOIN prepared remarks + Q&A exchanges, sorted by sequence
- 3C: Q&A Section fallback (when 3B has empty qa_exchanges)
- 3D: full text fallback (when both 3B and 3C empty)
- 3E: latest transcript
- 3F: Q&A only (re-scan)
- 3G: Q&A by analyst name

**`given_date`**: `t.conference_datetime`. **`source_key`**: `"full"`.

### 14.2 8-K (`assets/8k.md` + `8k-queries.md`)

**Layers**: `ExhibitContent` (EX-99.x narrative, EX-10.x contracts), `ExtractedSectionContent` (item bodies), `FinancialStatementContent` (rare), `FilingTextContent` (raw, ~690KB avg).

**Queries**:
- 4A: 8-Ks with Item 2.02
- 4B: 8-Ks with Item 7.01 OR 8.01
- 4C: exhibit by exact `exhibit_number`
- 4D: all exhibits for a report (discovery)
- 4E: section by exact `section_name`
- 4F: filing text fallback
- 4G: content inventory (lists all layers + their counts)
- 4H: generic item-code parameter
- 4I: financial statements (rare for 8-K)
- 4J: **all sections** in one query
- 4K: **all EX-99.x** in one query
- 4L: EX-10.x previews (first 2500 chars)

Section names use **no-space format** (`ResultsofOperationsandFinancialCondition`).

Dirty exhibit numbers exist: `EX-99.01` alongside `EX-99.1`. Query 4D handles discovery.

**Amendments** `8-K/A` have `isAmendment=true`. Queries 4A/4B/4H filter exact `formType='8-K'` and miss them — currently 631 8-K/A amendments unprocessed in live graph.

**`given_date`**: `r.created`. **`source_key`**: `"EX-99.1"`/`"EX-99.2"`/`"Item 2.02"`/etc.

### 14.3 10-Q + 10-K (`assets/10q.md`, `10k.md` + queries)

Both share identical schema (`Report` label, `ExtractedSectionContent`, `FinancialStatementContent`, `FilingTextContent`, `ExhibitContent`). Same query set (5A-5I).

Canonical MD&A section names differ:
- 10-Q: `ManagementDiscussionandAnalysisofFinancialConditionandResultsofOperations` (no apostrophe)
- 10-K: `Management’sDiscussionandAnalysisofFinancialConditionandResultsofOperations` (**curly apostrophe U+2019** — verified via `xxd` on `.claude/skills/extract/assets/10k.md:85` showing bytes `e2 80 99 73`)

Query 5B handles both via `WHERE s.section_name STARTS WITH 'Management' AND s.section_name CONTAINS 'DiscussionandAnalysisofFinancialCondition'`.

Live coverage (verified 2026-05-22):
- 10-Q: **7,301** reports, **7,224** have canonical MD&A, avg ~56.6KB
- 10-K: **2,993** reports, **2,976** have canonical MD&A, avg ~71.8KB

Queries 5C (financial statements), 5D (section discovery), 5E (Risk Factors), 5F (inventory), 5G (filing text fallback), 5H (exhibit), 5I (any section by name).

**`given_date`**: `r.created`. **`source_key`**: layer-specific (MD&A=`"MD&A"`, section=`section_name`, statement=`statement_type`, exhibit=`exhibit_number`, filing text=`"filing_text"`).

### 14.4 News (`assets/news.md` + `news-queries.md`)

**Flat node** — no child content. Fields: `title` (always populated), `body` (~10% empty), `teaser`, `created`, `updated`, `url`, `authors` (JSON), `channels` (JSON), `tags` (JSON), `market_session`, `returns_schedule` (JSON).

**Queries**:
- 6A: payload by ID
- 6B: date-range search (required dates — result sets are huge)
- 6C: channel-filtered (`channels CONTAINS '"$channel"'` — exact JSON-encoded match)
- 6D: influence context
- 6E: by market_session

**`given_date`**: `n.created`. **`source_key`**: `"title"` (canonical, even when content came from body/teaser). **`section`**: `"title"`/`"body"`/`"teaser"` distinguishes the actual location.

Live status: **0 News nodes processed for guidance** (348,670 total, all `guidance_status=null`). The trigger explicitly includes `news` in `ASSET_QUERIES`, but the trade-ready daemon's `ASSET_CONFIGS` (lines 53-63 of `guidance_trigger_daemon.py`) only includes `transcript`, `8k`, `10q`, `10k` — news must be triggered manually.

---

## §15 — Intersection Files (`types/guidance/assets/`)

Six files, all loaded at slot 4 by the appropriate agent:

### 15.1 `transcript-primary.md` (76 LOC)

Loaded by primary agent for transcripts.
- **Scan scope**: prepared remarks only. Q&A fallback if PR empty.
- **Speaker hierarchy** (priority for conflict resolution, NOT scope):
  1. CFO prepared remarks (formal guidance)
  2. CFO Q&A (handled in enrichment)
  3. CEO prepared remarks (strategic)
  4-5. CEO Q&A, other executives (enrichment)
  - Skip: Operator (procedural only)
- **Quote prefix**: `[PR]`. Q&A fallback: `[Q&A]`.
- **Q&A fallback analyst-framing rule**: don't extract analyst-wording numbers unless management restates/affirms.
- **Basis context trap**: CFO can switch GAAP↔non-GAAP within paragraph; determine basis per quoted metric span.
- **`source_refs`**: `["{SOURCE_ID}_pr"]` for primary. For Q&A fallback: `["{SOURCE_ID}_qa__{sequence}"]`. For 3C QuestionAnswer fallback: `qa.id` directly.
- **`section`**: speaker's section label (`"CFO Prepared Remarks"`, `"CEO Prepared Remarks"`).

### 15.2 `transcript-enrichment.md` (114 LOC)

Loaded by enrichment agent for transcripts. **ONLY enrichment file in the system.**
- **Scan scope**: Q&A only.
- **Analyst-framing rule** (verbatim from file): "Do not extract a numeric or qualitative guidance anchor from analyst wording unless management explicitly restates or clearly affirms it in the answer. The supporting quote must be management-answer text only."
  - Positive: "yes", "that's right", "we're comfortable with that" → extractable
  - Negative: "we'll see", "it depends" → NO GUIDANCE
- **Quote prefix**: `[Q&A]`. Enriched items: append `[Q&A] additional detail...` to existing quote. **Never rewrite `[Q&A]` → `[PR]`.**
- **`section` format**: enriched → `"CFO Prepared Remarks + Q&A #3 (analyst)"`. New: `"Q&A #N (analyst)"`.
- **`source_refs`**: array of QAExchange IDs. Format: `{SOURCE_ID}_qa__{sequence}`.

### 15.3 `8k-primary.md` (126 LOC)

- **Content fetch**: ALWAYS use `warmup_cache.sh --8k ACCESSION` (Bash → `/tmp/8k_content_{accession}.json`) for sections + EX-99. Don't fetch ONLY EX-99.1 — multi-item filings spread guidance across exhibits.
- **Item-level routing**:
  - 2.02 (94% in exhibit), 7.01 (85%) → exhibit first
  - 5.07 (>99% section), 2.06 (98% section) → section first
  - 1.01, 5.02, 8.01 → check both
- **GAAP/non-GAAP table columns**: extract BOTH.
- **Safe harbor proximity**: filter pure disclaimers but keep adjacent concrete guidance.
- **Quote prefix**: `[8-K]`.
- **`source_key`**: actual layer (`"EX-99.1"`, `"Item 2.02"`, etc.).
- **Dedup rule**: same metric in exhibit + section → exhibit is primary (more detailed).

### 15.4 `10q-primary.md` + `10k-primary.md` (90 LOC each)

Nearly identical, differ in:
- 10-K: includes multi-year targets explicitly (`"By fiscal 2028"` → long_range period)
- Canonical MD&A name varies (no apostrophe vs curly apostrophe)

Both:
- Always use Bash + `warmup_cache.sh --mda` for MD&A.
- Skip RiskFactors, LegalProceedings, ControlsandProcedures, Exhibits, Signatures.
- Forward-looking strictness: target period must be AFTER `r.created`. Periodic filings are mostly retrospective — zero guidance is valid.
- Filing text fallback: bound via keyword seed before model input.
- Cross-asset dedup: never suppress because of 8-K/transcript overlap — IDs handle this.
- Quote prefix: `[10-Q]` or `[10-K]`.
- `source_refs`: `[]`.

### 15.5 `news-primary.md` (79 LOC)

- **Attribution rule**: extract only management/company statements. Skip analyst/consensus/Street/price targets/ratings/third-party. Ambiguous → skip.
- **Reaffirmation handling**: `reaffirms`/`maintains`/`reiterates`/`unchanged` → extract values stated in THIS source, add `conditions = "reaffirmed"`. Don't reuse prior values.
- **Withdrawn**: `qualitative = "withdrawn"`, numerics null. Don't reuse prior.
- **Prior period values** in headline (`"(Prior $X)"`): extract NEW value only.
- **Title/body/teaser**: don't duplicate when restating same guidance.
- **Quote prefix**: `[News]`.
- **`source_key`**: always `"title"`. **`section`**: `"title"`/`"body"`/`"teaser"`.
- **`source_refs`**: `[]`.

---

## §16 — Common Queries (`queries-common.md`, 312 LOC)

### 16.1 Context (1A-1D)

- **1A**: Company + CIK lookup `MATCH (c:Company {ticker: $ticker}) RETURN c.ticker, c.name, c.cik, c.sector, c.industry, c.mkt_cap`
- **1B**: FYE derivation from latest 10-K `periodOfReport`
- **1C**: Period pre-fetch (Context-based; XBRL pipeline only — NOT used by guidance)
- **1D**: All 10-K/10-Q periods (alternative pre-fetch)

### 16.2 Warmup Caches (2A, 2B)

- **2A**: Concept usage cache — most recent 10-K + subsequent 10-Qs, numeric facts, consolidated contexts only. Returns `(qname, label, usage)` sorted by usage desc. → `/tmp/concept_cache_{TICKER}.json`
- **2B**: Member profile cache — Context-based. **DIAGNOSTIC ONLY**. The authoritative member source is `QUERY_MEMBER_MAP`. → `/tmp/member_cache_{TICKER}.json`

### 16.3 Inventory (8A)

Company asset counts (8-K, transcript, news, XBRL reports).

### 16.4 Fulltext (9A-9F)

12 extraction-relevant fulltext indexes (verified live 2026-05-22):
```
qa_exchange_ft           QAExchange.exchanges
prepared_remarks_ft      PreparedRemark.content
full_transcript_ft       FullTranscriptText.content
question_answer_ft       QuestionAnswer.content        ← used by 3C QA-Section fallback
exhibit_content_ft       ExhibitContent.{content, exhibit_number}
extracted_section_content_ft  ExtractedSectionContent.{content, section_name}
news_ft                  News.{title, body, teaser}
concept_ft               Concept.{label, qname}
fact_textblock_ft        Fact.{value, qname}
financial_statement_content_ft  FinancialStatementContent.{value, statement_type}
filing_text_content_ft   FilingTextContent.{content, form_type}
company_ft               Company.{name, displayLabel}
```
The live database also has `abstract_ft` and `search` — **14 fulltext indexes total**. Those two are unrelated to extraction and not used by any pipeline query.

### 16.5 Schema Rules (top of file)

Critical traps documented:
- All timestamps are Strings (not native datetime)
- Returns live on relationships (PRIMARY_FILER, INFLUENCES), not nodes
- XBRL booleans are Strings ('0'/'1')
- `Fact.value` is String even for numeric facts; `toFloat()` when `is_numeric='1'`
- `Report.items` is JSON string; use `CONTAINS` for substring match
- `Period.end_date` can be string 'null' for instant periods
- `NaN` exists; filter with `isNaN()`
- News timestamp is `n.created` (NOT `n.published_utc`)
- INFLUENCES carries return properties — DON'T select them in extraction queries (wastes context)
- Transcript has both `INFLUENCES` (with returns) and `HAS_TRANSCRIPT` (navigation only) — extraction listing uses `INFLUENCES`
- `QAExchange.sequence` is String — use `toInteger()` for ordering
- `ExhibitContent.exhibit_number` has dirty variants (`EX-99.01` alongside `EX-99.1`)
- `ExtractedSectionContent.section_name` uses no-space format
- `PreparedRemark.content` is a single text blob, not an array
- `FinancialStatementContent.value` is JSON string — needs parsing

---

## §17 — Type Queries (`guidance-queries.md`, 134 LOC)

- **7A**: Existing guidance tags for company (used by both passes to reuse canonical names)
- **7B**: Latest guidance per metric
- **7C**: Check existing GuidanceUpdate by ID (idempotency check)
- **7D**: All GuidanceUpdates for source (prior extraction warning)
- **7E**: Full readback for source — used by enrichment agent as base for Q&A enrichment. Returns all 20+ properties + `period_u_id`, `gp_start_date`, `gp_end_date`, `member_u_ids[]`.
- **7F**: Prior-source baseline — all labels this company has guided on from this asset type with frequency + last_seen, where `given_date < current_given_date`. Used in completeness check (Step 5 of enrichment).
- **8B**: Existing guidance node count.
- **10**: Extraction keywords (categories: Forward-looking, Guidance, Periods, Metrics, Revisions, Qualitative, Conditional).

---

## §18 — Warmup (`scripts/earnings/builders/warmup_cache.py`, 460 LOC; shim at `.claude/skills/earnings-orchestrator/scripts/warmup_cache.py`)

Direct Bolt connection — bypasses MCP persisted-output ~50KB truncation. CLI invocation via `warmup_cache.sh` wrapper.

**Modes**:
| Flag | Function | Writes to |
|---|---|---|
| (no flag) | `run_warmup(ticker)` | 2A + 2B + MEMBER_MAP to `/tmp/concept_cache_{T}.json`, `/tmp/member_cache_{T}.json`, `/tmp/member_map_{T}.json` |
| `--transcript TID` | `run_transcript` | 3B → `/tmp/transcript_content_{TID}.json` |
| `--mda ACCESSION` | `run_mda` | 5B → `/tmp/mda_content_{ACC}.json` |
| `--8k ACCESSION` | `run_8k` | 4J + 4K → `/tmp/8k_content_{ACC}.json` (sections + exhibits) |

Plus modes for the predictor/learner (out of scope for extraction): `--8k-packet`, `--guidance-history`, `--inter-quarter`.

**Critical**: the python file at `.claude/skills/earnings-orchestrator/scripts/warmup_cache.py` is now a **66-line shim** that re-exports from `scripts/earnings/builders/warmup_cache.py`. The shim preserves identity contract (all symbols same Python object) for back-compat.

---

## §19 — Write Path (`guidance_write_cli.py:main`, 456-656)

### 19.1 Input contract

```json
{
  "source_id": "AAPL_2025-07-31T17.00.00-04.00",
  "source_type": "transcript",                  // matches {ASSET}
  "ticker": "AAPL",
  "fye_month": 9,                                // required when items lack period_u_id
  "payload_origin": "extract_v2",                // extract_v2 | readback | legacy_extract
  "items": [ { ...extraction fields... } ]
}
```
Top-level field validation (lines 484-489): missing fields → error with hint about nested `company`/`source` objects (common LLM mistake).

### 19.2 Phase A — Period + label_slug + hint validation (lines 502-520)

For each item:
1. Inject `source_id` from top-level.
2. Compute `label_slug = slug(item.label)`.
3. `_ensure_period(item, fye_month, ticker)` → 4-step cascade (§10).
4. `_validate_item_hints(item, payload_origin)` → V2 hint rules (§11.5).
On `ValueError`: append to `errors` list, item excluded from `period_items`.

### 19.3 Concept repair (lines 523-535)

```python
concept_rows = load_concept_cache(ticker)   # /tmp/concept_cache_{ticker}.json
apply_concept_resolution(period_items, concept_rows, logger)
# + concept inheritance across segments
```

### 19.4 Phase B — Skip gate + ID computation (lines 538-554)

```python
for item in period_items:
    if _should_skip_pre_v2_readback(item, payload_origin, resolution_mode):
        errors.append({..., "error": "pre_v2_readback_skip"})
        continue
    _ensure_ids(item, fye_month=fye_month, ticker=ticker, resolution_mode=mode)
    # → build_guidance_ids() runs V2 axes resolver, computes canonical_unit,
    #   canonical_low/mid/high, evhash16, guidance_id, guidance_update_id
    valid_items.append(item)
```

### 19.5 Concept family resolution (lines 557-561)

After IDs computed (so xbrl_qname is finalized): `resolve_concept_family(label_slug, xbrl_qname)`.

### 19.6 Member resolution (lines 563-572)

```python
try: member_map = json.load(open(f'/tmp/member_map_{ticker}.json'))
except: member_map = None
segment_aliases = _load_segment_aliases(ticker)
if member_map is not None: _apply_member_map(valid_items, member_map, ...)
```

### 19.7 Write dispatch (lines 574-617)

**Dry-run**: per item, call `write_guidance_item(None, item, ..., dry_run=True)` — runs 8 validation guards but no Neo4j writes.

**Write**:
```python
manager = get_manager()                                  # Neo4j Bolt connection
if member_map is None:                                   # live fallback
    live_map = _build_live_member_map(manager, ticker)
    if live_map: _apply_member_map(valid_items, live_map, "live CIK fallback", ...)
create_guidance_constraints(manager)                     # idempotent — 3 constraints, 2 indexes, 4 sentinels
summary = write_guidance_batch(manager, valid_items, source_id, source_type, ticker, ...)
manager.close()
```

### 19.8 Observability sidecar (lines 620-650)

```python
written_summary = []
for i, item in enumerate(valid_items):
    result = results_list[i] if i < len(results_list) else {}
    entry = {
        'label': item.get('label'), 'segment': item.get('segment'),
        'canonical_unit': item.get('canonical_unit'),
        'low': item.get('canonical_low'), 'mid': ..., 'high': ...,
        'was_created': result.get('was_created'),
        'error': result.get('error'),
    }
    if resolution_mode in ('v2', 'shadow'):
        entry.update({k: item.get(k) for k in (
            'unit_kind_hint','money_mode_hint',
            'resolved_kind','resolved_money_mode','resolved_ratio_subtype',
            'resolution_version'
        )})
    if resolution_mode == 'shadow' and item.get('shadow_v2'):
        entry['shadow_v2'] = item['shadow_v2']
    written_summary.append(entry)
Path(f'/tmp/gu_written_{source_id}.json').write_text(json.dumps(written_summary, default=str))
```
Not cleaned up by CLI — worker handles stale-guard.

### 19.9 stdout JSON

Prints final summary: `{mode, resolution_mode, payload_origin, total, valid, id_errors, results, created, updated, skipped, errors, concept_links, member_links}`.

---

## §20 — Atomic Cypher Write (`guidance_writer.py`)

### 20.1 Per-item atomic query (lines 191-259)

```cypher
// MATCH pre-existing (label-specific source, company by ticker)
MATCH (source:{Report|Transcript|News} {id: $source_id})
MATCH (company:Company {ticker: $ticker})

// Snapshot existing GuidanceUpdate (for was_created)
OPTIONAL MATCH (existing:GuidanceUpdate {id: $guidance_update_id})

// Derive given_date from source (writer-authoritative, UTC-normalized)
WITH source, company, existing,
     CASE $source_type
       WHEN 'transcript' THEN source.conference_datetime
       ELSE source.created
     END AS raw_given_ts

// MERGE Guidance node
MERGE (g:Guidance {id: $guidance_id})
  ON CREATE SET g.label = $label, g.aliases = $aliases, g.created_date = $today
  ON MATCH SET g.aliases = reduce(
    acc = [], a IN (coalesce(g.aliases, []) + coalesce($aliases, []))
    | CASE WHEN a IS NULL OR a IN acc THEN acc ELSE acc + a END)

// MERGE GuidancePeriod (calendar-based, company-agnostic)
MERGE (gp:GuidancePeriod {id: $period_u_id})
  ON CREATE SET gp.u_id=$period_u_id, gp.start_date=$gp_start_date, gp.end_date=$gp_end_date

// MERGE GuidanceUpdate (slot-based)
MERGE (gu:GuidanceUpdate {id: $guidance_update_id})
  ON CREATE SET gu.created = $created_ts
  SET gu.evhash16 = $evhash16,
      gu.given_date = toString(datetime({epochMillis: datetime(raw_given_ts).epochMillis})),
      gu.period_scope = $period_scope,
      gu.time_type = $time_type,
      gu.fiscal_year = $fiscal_year,
      gu.fiscal_quarter = $fiscal_quarter,
      gu.segment = $segment,
      gu.low = $low, gu.mid = $mid, gu.high = $high,
      gu.canonical_unit = $canonical_unit,
      gu.basis_norm = $basis_norm, gu.basis_raw = $basis_raw,
      gu.derivation = $derivation,
      gu.qualitative = $qualitative, gu.quote = $quote,
      gu.section = $section, gu.source_key = $source_key,
      gu.source_type = $source_type,
      gu.conditions = $conditions,
      gu.xbrl_qname = $xbrl_qname, gu.unit_raw = $unit_raw,
      gu.label = $label, gu.label_slug = $label_slug, gu.segment_slug = $segment_slug,
      gu.source_refs = CASE WHEN gu.source_refs IS NULL THEN $source_refs
                            ELSE gu.source_refs + [x IN $source_refs WHERE NOT x IN gu.source_refs] END,
      gu.concept_family_qname = $concept_family_qname
      [, gu.resolved_kind=..., gu.resolved_money_mode=..., gu.resolved_ratio_subtype=..., gu.resolution_version=$resolution_version
        when resolution_mode='v2']

// Core 4 edges
MERGE (gu)-[:UPDATES]->(g)
MERGE (gu)-[:FROM_SOURCE]->(source)
MERGE (gu)-[:FOR_COMPANY]->(company)
MERGE (gu)-[:HAS_PERIOD]->(gp)

RETURN gu.id AS id, existing IS NULL AS was_created
```

Note `unit_raw` is only set when `canonical_unit='unknown'` (line 347):
```python
'unit_raw': item.get('unit_raw') if item.get('canonical_unit') == 'unknown' else None,
```
So canonical rows don't carry the original unit string. The fallback hazard described in `guidance-upstream-unit-misclassification.md` Trace A (`unit_raw=item.get('unit_raw') or item.get('canonical_unit') or 'unknown'`) has been **fixed** — current code at `guidance_write_cli.py:374` reads `unit_raw=item.get('unit_raw') or 'unknown'` (no `canonical_unit` stand-in). `grep "or item.get('canonical_unit')"` returns nothing in the CLI source.

### 20.2 Concept edge (lines 262-279)

Only runs when `xbrl_qname` non-null:
```cypher
MATCH (gu:GuidanceUpdate {id: $guidance_update_id})
MATCH (con:Concept {qname: $xbrl_qname})
WITH gu, con LIMIT 1                              // multi-taxonomy: pick one
MERGE (gu)-[:MAPS_TO_CONCEPT]->(con)
RETURN con.qname AS linked_qname
```

### 20.3 Member edges (lines 282-296)

Only runs when `member_u_ids` non-empty:
```cypher
MATCH (gu:GuidanceUpdate {id: $guidance_update_id})
UNWIND $member_u_ids AS member_u_id
MATCH (m:Member {u_id: member_u_id})
MERGE (gu)-[:MAPS_TO_MEMBER]->(m)
RETURN count(*) AS linked
```
Per-element MATCH failures silently skipped. **Not gated on `was_created`** — re-runs self-heal missing edges.

### 20.4 Feature flag gate (lines 401-407)

```python
ENABLE_GUIDANCE_WRITES env var (true|1|yes|false|0|no) → otherwise config.feature_flags default False
```
Agent passes `ENABLE_GUIDANCE_WRITES=true` explicitly in the write-mode shell call.

---

## §21 — 8 Validation Guards (`guidance_writer._validate_item`, lines 59-158)

| Guard | Trigger | Reject |
|---|---|---|
| **R** | required fields empty | missing required field |
| **A** | per-share label + `canonical_unit='m_usd'` | per-share values must not be millions |
| **B** | xbrl_qname contains `PerShare\|PerUnit\|PerDilutedShare\|PerBasicShare` + `m_usd` | XBRL says per-share but unit says m_usd |
| **C** | share-count label + `m_usd` | share-count must be `count`, not `m_usd` |
| **D** (V2) | numeric per-share label + `canonical_unit='unknown'` | V2 should resolve to usd |
| **E** (V2) | resolved_kind=money, money_mode=price_like, `canonical_unit='m_usd'` | price_like must be usd, not m_usd |
| **F** (V2) | resolved_kind=money, money_mode=aggregate, unit_raw contains 'cent'/'cents' | aggregate money can't use cents scale |
| **G** (V2) | resolved_kind=ratio + canonical_unit in {`m_usd`,`usd`,`count`} | ratio must be percent/percent_yoy/percent_points/basis_points |
| **H** (V2) | resolved_kind=count + `canonical_unit='m_usd'` | count must be `count` |

Guards A/B/C are V1-era catastrophic-corruption blockers. Guards D-H are V2 fail-closed on resolved-axis contradictions. Note: D-H **only fire when `resolved_kind` is set AND item has numeric values** (line 113), so V1 historical rows pass through unaffected.

**Per `guidance-upstream-unit-misclassification.md`**: numeric per-share rows with `canonical_unit='unknown'` AND legacy mode (no `resolved_kind`) are NOT caught — **273 such rows in the live graph today** (re-verified 2026-05-22 against the current `_is_per_share_label` logic; the Infra_Bugs doc snapshot from 2026-04-02 reported 285). This is a moving target and should be re-counted before remediation.

---

## §22 — Settings Hooks (`.claude/settings.json` + `.claude/hooks/`)

### 22.1 Active hooks (from settings.json lines 24-91)

```
PreToolUse[Write]    → validate_gx_output.sh         (matches /earnings-analysis/.../gx/*.tsv only)
                    → validate_judge_output.sh       (matches /earnings-analysis/.../judge/*.tsv only)
                    → validate_learning_output.py    (matches /learning/result.json only)
PreToolUse[Edit|Write] → block_env_edits.sh           (blocks any *.env or */.env*)
PreToolUse[mcp__neo4j-cypher__write_neo4j_cypher]
                    → guard_neo4j_delete.sh          (blocks DELETE/DETACH DELETE/DROP/REMOVE/CALL apoc.*.{delete,drop,remove})
PostToolUse[Write]  → cleanup_after_ok.sh            (removes per-task gx_dir/judge_dir on .ok marker)
Stop                → notify_done.sh                  (paplay done.wav)
SubagentStop        → obsidian_capture.sh             (captures agent output + thinking to Obsidian vault)
```

### 22.2 Critical hook behavior for guidance extraction

**`validate_gx_output.sh`** — only fires on `*/earnings-analysis/Companies/*/manifests/*/gx/*.tsv` paths. The current pipeline writes to `/tmp/gu_*.json` and `/tmp/extract_pass_*.json` — **none of these match the gx/*.tsv pattern, so the hook never fires** for guidance extraction. It's for a legacy manifest-based pipeline.

**`block_env_edits.sh`** — actively prevents agent from editing `.env` files. Defense-in-depth (the Anthropic API key billing safety).

**`guard_neo4j_delete.sh`** — never fires for extraction because agents don't have `write_neo4j_cypher` in their tool list. Defense-in-depth.

**`cleanup_after_ok.sh`** — fires on `.ok` markers in legacy manifest dirs. Never fires for current pipeline.

**`obsidian_capture.sh`** — fires on every SubagentStop. Captures agent transcript to Obsidian vault. Skips `earnings-prediction`, `earnings-attribution`, `earnings-learner` agent types (those have dedicated capture). Tags include `extraction`, `guidance` keywords automatically.

### 22.3 Inactive hooks present in folder but not in settings.json

`block_bash_guard.sh`, `pit_gate.py`, `guard_task_delete.sh`, `obsidian_capture.py` (called by .sh). Not loaded.

---

## §23 — Result Protocol

### 23.1 Three-file handoff

```
extraction-primary-agent  →  /tmp/extract_pass_guidance_primary_{SOURCE_ID}.json
extraction-enrichment-agent → /tmp/extract_pass_guidance_enrichment_{SOURCE_ID}.json
orchestrator combines  →  RESULT_PATH (passed in via prompt by worker)
```

### 23.2 Primary agent result schema

```json
{"status":"completed","items_extracted":N,"items_written":N,"errors":0}
// or
{"status":"failed","error":"ERROR_CODE","message":"..."}
```

### 23.3 Enrichment agent result schema

```json
{"status":"completed","items_enriched":N,"new_secondary_items":N,"errors":0}
// or NO_PRIMARY_ITEMS / PHASE_DEPENDENCY_FAILED / NO_SECONDARY_CONTENT messages
```

### 23.4 Worker-bound result schema

```json
{"type":"guidance","source_id":"...","status":"completed",
 "primary_items":N,"enriched_items":N,"new_secondary_items":N}
```

### 23.5 Sidecar — `/tmp/gu_written_{source_id}.json`

Written by CLI per successful item. Worker reads it for ledger summary. Stale-guard via worker unlink at attempt entry.

**Critical nuance**: BOTH primary and enrichment passes write the **same** sidecar path, in `'w'` mode (`guidance_write_cli.py:647`) — enrichment overwrites primary. So when the worker reads the sidecar at end-of-job, it sees the **last batch only**:
- Single-pass (e.g. 8-K/10-Q/10-K/news): sidecar = primary's items.
- Two-pass (transcript): sidecar = enrichment's items (just the changed + new ones, NOT the full primary set).

Therefore `items_written` in the ledger summary equals **the most recent CLI batch's count**, not the cumulative write across both passes. To get true cumulative write count, the code would have to either (a) aggregate per-pass sidecars or (b) re-query Neo4j after both passes complete.

### 23.6 Source node status property

`{type}_status` ∈ {NULL, `in_progress`, `completed`, `failed`}. Optional `{type}_error` carries error string. Per-type, independent.

---

## §24 — Run Ledger (`scripts/earnings/run_ledger.py`, 525 LOC)

### 24.1 Schema (lines 55-60)

```
SCHEMA_VERSION = 1
VALID_COMPONENTS = {'guidance', 'prediction', 'learning'}
TERMINAL_STATUSES = {'succeeded', 'failed', 'skipped', 'rate_limited'}
ALL_STATUSES = TERMINAL_STATUSES | {'running'}
```

### 24.2 Storage

```
LEDGER_PATH = <repo>/earnings-analysis/operations/run_ledger.jsonl    (authoritative)
INDEX_PATH  = <Obsidian vault>/.../earnings-analysis/operations/Run Index.md
              (falls back to repo if vault not present)
```

JSONL append-only. Each line = one state transition. Current state = last-row-wins by `run_id`.

### 24.3 Concurrency safety (lines 65-81)

`fcntl.flock(LOCK_EX) + flush + fsync` on every append. Safe for multi-pod on single-host (the K8s hostPath). NOT safe for NFS.

Atomic writes for the index Markdown: `write to {path}.tmp.{pid}` + `os.replace`. Crash during regeneration never leaves a half-written index.

### 24.4 `open_run` (lines 111-166)

Appends one row with `status='running'`, returns uuid4. Refreshes index (errors swallowed — never blocks caller). Fires at OUTERMOST execution boundary of an attempt — BEFORE the SDK call.

### 24.5 `close_run` (lines 169-257)

Appends terminal-status row reusing same `run_id`. Computes `elapsed_seconds` from the running row if findable. Copies identifying fields from opening row so each closed row is self-describing.

Error string truncated to 500 chars (line 249).

### 24.6 Index render (lines 444-495)

Regenerated on every state transition. 4 sections:
- **In Flight** (status=running across all components)
- Recent Predictions (last 50, component=prediction, terminal)
- Recent Learners (last 50, component=learning, terminal)
- Recent Extractions (last 50, component=guidance, terminal)

Extractions section columns (line 421): `date | ticker | asset | source_id | items_extracted | items_written | enrichment | status | run_id`.

---

## §25 — Live Neo4j State

### 25.1 Verified constraints (2026-05-22)

```
guidance_update_id_unique           ✓ ONLINE
guidance_period_id_unique           ✓ ONLINE
constraint_guidance_id_unique       ✓ ONLINE  (live name has 'constraint_' prefix; declared
                                              as 'guidance_id_unique' at guidance_writer.py:499)
```
All three uniqueness constraints are enforced live. `count(g)=548, count(DISTINCT g.id)=548` — no duplicate Guidance.id values.

### 25.2 Verified indexes

All ONLINE at 2026-05-22. **`readCount` is a mutable live counter — values drift every query** and are omitted here on purpose; query `SHOW INDEXES YIELD name, readCount` if you need the current snapshot.

```
gu_label_slug                    RANGE on GuidanceUpdate.label_slug
gu_segment_slug                  RANGE on GuidanceUpdate.segment_slug
guidance_period_id_unique        RANGE (backing constraint)
guidance_update_id_unique        RANGE (backing constraint)
constraint_guidance_id_unique    RANGE (backing constraint)
```

### 25.3 Sentinels (all 4 present)

```
gp_ST, gp_MT, gp_LT, gp_UNDEF — all with start_date=null, end_date=null
```

### 25.4 Fulltext indexes (14 total live; 12 extraction-relevant)

12 extraction-relevant indexes present (see §16.4 for the full list including `question_answer_ft` used by the 3C fallback). Live database also has `abstract_ft` and `search` — 14 total — both unrelated to extraction.

### 25.5 Asset population

```
Reports:   8-K 29,672  10-Q 7,301  10-K 2,993  (excludes /A amendments)
Transcripts: 9,608
News:    348,670
```

### 25.6 Processing status

```
TRANSCRIPT:   completed=19   failed=3   in_progress=1   null=9,585
REPORT 8-K:   completed=266  failed=8   null=29,398
REPORT 10-Q:  completed=69   null=7,232
REPORT 10-K:  completed=27   null=2,966
REPORT 8-K/A: null=631       (amendments never picked up)
REPORT 10-Q/A: null=41
REPORT 10-K/A: null=137
NEWS:         null=348,670   (never processed automatically)
```

The lone `in_progress` Transcript is exactly the stale-recovery use case the daemon's lease-based dedup handles.

### 25.7 Resolution version distribution

```
v2:    234 (2.8%)
NULL: 8,198 (legacy V1 writes)
```

### 25.8 Edge totals

```
:MAPS_TO_CONCEPT  4,797 edges  (4,155 distinct GUs, some multi-taxonomy)
:MAPS_TO_MEMBER     460 edges  (387 distinct GUs, some multi-dimensional)
```

---

## §26 — Edge Cases (the unobvious ones)

| # | Edge case | How handled |
|---|---|---|
| 1 | Rate limit mid-extraction | `"hit your limit"` substring scan on every SDK message → re-queue without `_retry++` + 5-min sleep |
| 2 | Worker dies after BRPOP but before status='in_progress' | Status stays NULL. **DAEMON-triggered jobs**: the 4-hour Redis lease was set when the daemon enqueued, so the next sweep's `SET NX` fails → re-enqueue blocked until lease TTL expires (up to 4h). **MANUAL `trigger-extract.py` jobs**: no lease was ever set → next manual invocation re-queues immediately. |
| 3 | Worker dies after status='in_progress' | Status stuck → lease expires (4h) → daemon detects stale + re-enqueues |
| 4 | 3 retries exhausted | Dead-letter queue + status='failed' → manual `--retry-failed` required |
| 5 | Stale `/tmp/gu_written_*.json` from prior attempt | Worker unlinks at process_one entry (extraction_worker.py:458) |
| 6 | Result file missing or malformed | mark_status('failed', error=str(e)), close ledger 'failed', return False |
| 7 | SDK returns None result | mark_status('failed', error='No result returned from SDK') |
| 8 | dry_run mode | Worker skips Neo4j status mutation; CLI runs all validation but no graph writes; sidecar still written |
| 9 | Concept cache missing | concept_resolver no-op (no live fallback — known gap) |
| 10 | Member map missing in write mode | Live CIK fallback runs (guidance_write_cli.py:599-602) |
| 11 | Member map missing in dry-run mode | Member edges silently absent |
| 12 | Same metric in 8-K + transcript + 10-Q | Different `source_id` → different slot IDs → 3 separate GUs (correct) |
| 13 | Per-segment guidance (iPhone/Mac/Total Revenue) | Different `segment_slug` → 3 distinct slots (correct, not duplicate) |
| 14 | Two basis values for same metric | Different `basis_norm` → 2 distinct slots (correct) |
| 15 | Multi-taxonomy Concept (qname exists in multiple year nodes) | `LIMIT 1` in concept edge query picks one; `gu.xbrl_qname` property carries stable string |
| 16 | XBRL Concept node doesn't exist for qname | MATCH fails silently, no edge, property still written |
| 17 | Member u_id in agent's claim doesn't exist | UNWIND MATCH fails silently for that element, no edge |
| 18 | Ambiguous concept candidates (multiple top hits with equal usage) | `resolve_xbrl_qname` returns None → fail-closed |
| 19 | Source node not found (`MATCH (source:Label {id: $source_id})` fails) | Cypher returns None → `error='source_or_company_not_found'`, item skipped |
| 20 | Pre-V2 readback in V2 mode | Skip gate fires: `pre_v2_readback_skip` error |
| 21 | Numeric per-share `unit_raw="per share"` in V1 | Canonicalizes to `unknown` (known bug — "per share" not in UNIT_ALIASES) |
| 22 | `adjusted_eps_diluted` label | `_is_per_share_label` misses infix; if `m_usd` slipped in, can persist (known bug) |
| 23 | Wgted avg shares outstanding label | `_is_share_count_label` misses `_outstanding` suffix; can be `m_usd` (known bug) |
| 24 | Calendar-override (text says "calendar year/quarter") | `calendar_override: true` → `fye=12` for period math |
| 25 | Instant-time balance-sheet item | `start_date=end_date` → single-day window |
| 26 | Pre-scaled value double-scaling guard | `multiplier>1 and value>999` → raise ValueError |
| 27 | `cents per share` for aggregate money | Guard F rejects (aggregate money can't have cents) |
| 28 | Amendment `/A` filings | Never picked up by trigger (formType filter is exact) |
| 29 | Multiple companies share same calendar quarter | Same GuidancePeriod node (calendar-based, company-agnostic) — by design |
| 30 | Re-running same source with richer data | Same slot ID → MERGE matches → properties update (latest wins) |
| 31 | Source has prior items (query 7D returns >0) | Warning logged, but re-extraction proceeds with MERGE+SET |
| 32 | Enrichment finds 0 primary items in 7E + 0 items written in result | Returns `NO_PRIMARY_ITEMS` cleanly |
| 33 | Enrichment finds 0 primary items + result claims items_written>0 | Returns `PHASE_DEPENDENCY_FAILED` (data inconsistency) |
| 34 | Source_refs array merge | Cypher: `gu.source_refs + [x IN $source_refs WHERE NOT x IN gu.source_refs]` — dedupes |
| 35 | Aliases array merge | Cypher reduce-dedupe (writer.py:211-213) |
| 36 | `Report.id` vs `Report.accessionNo` | Same value — `id` is canonical, accessionNo is alias |
| 37 | Transcript `given_date` derivation | Cypher: `source.conference_datetime` (UTC-normalized via epochMillis trick) |
| 38 | News `INFLUENCES` carries return data | Don't select it in extraction queries (waste of context) |
| 39 | `QAExchange.sequence` is String type | Always `toInteger()` when ordering |
| 40 | 3C QuestionAnswer fallback for 88 transcripts (live count, verified 2026-05-22) | `content` and `speaker_roles` are JSON strings (need parsing); `speaker_roles` nullable |

---

## §27 — Open Issues (from `Infra_Bugs/`)

### 27.1 `guidance-xbrl-reviewed-coverage-gaps.md` (OPEN, 2026-04-02)

**Problem**: hybrid concept system — partly reviewed, partly agent survivors, partly absent.
- High-volume unreviewed labels: `adjusted_eps`, `non_gaap_eps`, `effective_tax_rate`, `net_sales`, `diluted_share_count`, `weighted_average_basic_shares_outstanding`.
- Reviewed survivors that need one-by-one validation: `capex` → `nfe:CapitalExpenditures`; `tax_rate` → `IncomeTaxExpenseBenefit` (risky); `interest_expense` → multiple variants; `operating_cash_flow` → `NetCashProvidedByUsedInOperatingActivities` variants; `opex` → `SellingGeneralAndAdministrativeExpense` (risky); `restructuring_charges` → `RestructuringSettlementAndImpairmentProvisions`.
- Concept cache scope doesn't include 8-K. SMTC: cache empty → concept repair is no-op for that ticker.
- Concept matching has no live fallback (unlike member matching).

**Proposed fixes**:
1. Add 7 high-confidence reviewed labels.
2. Validate survivor qnames one by one.
3. Add live fallback when cache is missing/empty.
4. Reconsider cache scope for 8-K guidance.
5. Backfill historical rows after registry expands.

### 27.2 `guidance-upstream-unit-misclassification.md` (OPEN, 2026-03-31)

**Problem (2026-04-02 Infra_Bugs snapshot)**: 1,813 / 8,291 rows (21.9%) had unit-classification problems. These are the snapshot numbers from the source document — the graph and breakdown have drifted since (see §11.6 for current live unit distribution and the bottom of this section for the most recent test-script result).

**Buckets at the 2026-04-02 snapshot**:
1. Misclassified `m_usd` (141 rows, 1.7%): share counts, count-like, per-unit prices stored as money.
2. Unknown unit (1,672 rows, 20.2%): 472 numeric rows with inferable types (EPS 72, Dividend Per Share 64, Adjusted EPS 50, etc.).
3. Duplicate display rows: 20+ metrics appear under multiple `canonical_unit` values.

**Root causes**:
1. `UNIT_ALIASES` missing strings the extractor already emits: `per share`, `per diluted share`, `dollars per share`, `cents`, `million shares`, `members`, `communities`, `clients`, etc.
2. `_is_per_share_label` misses infix variants (`adjusted_eps_diluted`).
3. `_is_share_count_label` misses `_outstanding` and count-like labels.
4. ~~`guidance_write_cli.py:328` uses `unit_raw=item.get('unit_raw') or item.get('canonical_unit') or 'unknown'`~~ — **FIXED**: current code at `guidance_write_cli.py:374` reads `unit_raw=item.get('unit_raw') or 'unknown'`; the `canonical_unit` stand-in has been removed.
5. Writer Guards only fail-close the old `m_usd` corruption, not the dominant new `unknown` population.

**3 detailed traces** show exact line-by-line failure paths for `adjusted_eps_diluted` (Trace A), `unit_raw='per share'` (Trace B), and `weighted_average_basic_shares_outstanding` (Trace C).

**Validation script**: `scripts/earnings/test_guidance_unit_safety.py`. Live results 2026-05-22 (refreshed): **PASS 2, FAIL 4** — 8,432 total rows; `no_unknown_units` FAIL (1,671 unknown); `per_share_metrics_use_usd` FAIL (325 mismatches); `share_count_metrics_use_count` FAIL (2 mismatches); `count_like_metrics_not_money` FAIL (10 mismatches). The 2026-04-02 Infra_Bugs run reported the same 6-check verdict pattern with marginally different counts (1,672 unknown / 324 per_share_bad / 2 / 10) on the 8,291-row snapshot.

### 27.3 Period race (TODO at top of `GuidanceTrigger.md`)

10-K/10-Q eligibility queries should require `EXISTS { (r)-[:HAS_XBRL]->() }`. Without it: extraction can fire before XBRL processing, fall back to month-boundary dates, then re-extract later → duplicate `GuidancePeriod` for same quarter.

### 27.4 ~~Missing `guidance_id_unique` constraint~~ — RESOLVED

The constraint exists live as `constraint_guidance_id_unique` on `Guidance(id)` — the live Neo4j prefixed the name. `count(g)=548, count(DISTINCT g.id)=548` confirms zero duplicates. The original audit missed it because the filter used `name STARTS WITH 'guidance'` which excludes the `constraint_`-prefixed live name. Not an open issue.

### 27.5 News asset never auto-processed

`ASSET_CONFIGS` in `guidance_trigger_daemon.py:53-63` doesn't include `news`. The manual `trigger-extract.py` does include it (5 assets). All 348,670 News nodes have `guidance_status=null`.

### 27.6 Validation hook scope mismatch

`validate_gx_output.sh` only matches `/earnings-analysis/.../gx/*.tsv` paths — never fires for current pipeline's `/tmp/gu_*.json` outputs. The Pre-Write validation hooks are inactive for guidance extraction.

---

## §28 — Complete File Inventory

```
TRIGGER LAYER
  scripts/trigger-extract.py                          299 LOC   Manual CLI
  scripts/guidance_trigger_daemon.py                  353 LOC   Auto daemon
  scripts/trade_ready_scanner.py                      —         Upstream scanner
  scripts/sec_quarter_cache_loader.py                 338 LOC   SEC Redis cache populator

WORKER
  scripts/extraction_worker.py                        800 LOC   K8s worker
  scripts/claude_usage_fetch.py                       —         Usage throttle source

K8S MANIFESTS
  k8s/processing/extraction-worker.yaml               168 LOC   Deployment + ScaledObject
  k8s/processing/guidance-trigger.yaml                —         Daemon Deployment
  k8s/processing/trade-ready-scanner.yaml             —         4 CronJob manifests

ORCHESTRATOR + AGENTS
  .claude/skills/extract/SKILL.md                      64 LOC   /extract orchestrator
  .claude/agents/extraction-primary-agent.md           66 LOC   Primary shell
  .claude/agents/extraction-enrichment-agent.md        69 LOC   Enrichment shell
  .claude/skills/extract/evidence-standards.md         12 LOC   4 anti-hallucination rules
  .claude/skills/extract/queries-common.md            312 LOC   1A-1D, 2A-2B, 8A, 9A-9F

ASSET PROFILES + QUERIES
  .claude/skills/extract/assets/transcript.md         138 LOC
  .claude/skills/extract/assets/transcript-queries.md 104 LOC   3A-3G
  .claude/skills/extract/assets/8k.md                 169 LOC
  .claude/skills/extract/assets/8k-queries.md         146 LOC   4A-4L
  .claude/skills/extract/assets/10q.md                162 LOC
  .claude/skills/extract/assets/10q-queries.md        142 LOC   5A-5I
  .claude/skills/extract/assets/10k.md                162 LOC
  .claude/skills/extract/assets/10k-queries.md        142 LOC   5A-5I
  .claude/skills/extract/assets/news.md               122 LOC
  .claude/skills/extract/assets/news-queries.md       103 LOC   6A-6E

GUIDANCE TYPE
  .claude/skills/extract/types/guidance/config.yaml    17 LOC   model overrides
  .claude/skills/extract/types/guidance/core-contract.md  746 LOC  Schema, IDs, fields
  .claude/skills/extract/types/guidance/primary-pass.md   244 LOC  Working brief
  .claude/skills/extract/types/guidance/enrichment-pass.md 207 LOC  Working brief
  .claude/skills/extract/types/guidance/guidance-queries.md 134 LOC  7A-7F, 8B, §10

INTERSECTION FILES
  .claude/skills/extract/types/guidance/assets/transcript-primary.md    76 LOC
  .claude/skills/extract/types/guidance/assets/transcript-enrichment.md 114 LOC
  .claude/skills/extract/types/guidance/assets/8k-primary.md           126 LOC
  .claude/skills/extract/types/guidance/assets/10q-primary.md           90 LOC
  .claude/skills/extract/types/guidance/assets/10k-primary.md           90 LOC
  .claude/skills/extract/types/guidance/assets/news-primary.md          79 LOC

DETERMINISTIC SCRIPTS
  .claude/skills/earnings-orchestrator/scripts/guidance_write.sh             23 LOC  venv + env wrapper
  .claude/skills/earnings-orchestrator/scripts/guidance_write_cli.py        656 LOC  CLI entry
  .claude/skills/earnings-orchestrator/scripts/guidance_writer.py           524 LOC  Cypher writer + 8 guards
  .claude/skills/earnings-orchestrator/scripts/guidance_ids.py             1000 LOC  IDs + V2 resolver
  .claude/skills/earnings-orchestrator/scripts/concept_resolver.py          442 LOC  CONCEPT_CANDIDATES + family
  .claude/skills/earnings-orchestrator/scripts/fiscal_math.py               140 LOC  Calendar math
  .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh               34 LOC  bash wrapper
  .claude/skills/earnings-orchestrator/scripts/warmup_cache.py               66 LOC  shim → canonical
  .claude/skills/earnings-orchestrator/scripts/segment_aliases/{TICKER}.json —      optional per-ticker
  scripts/earnings/builders/warmup_cache.py                                 460 LOC  CANONICAL warmup

LEDGER
  scripts/earnings/run_ledger.py                                            525 LOC  Append-only JSONL + Markdown index

SETTINGS + HOOKS
  .claude/settings.json                                                      —       Hook wiring
  .claude/hooks/validate_gx_output.sh                                        —       Legacy gx/*.tsv guard
  .claude/hooks/validate_judge_output.sh                                     —       Legacy judge/*.tsv guard
  .claude/hooks/validate_learning_output.py                                  —       learning/result.json
  .claude/hooks/block_env_edits.sh                                           —       Pre-write .env block
  .claude/hooks/guard_neo4j_delete.sh                                        —       Defense-in-depth (agents lack tool)
  .claude/hooks/cleanup_after_ok.sh                                          —       Legacy .ok cleanup
  .claude/hooks/notify_done.sh                                               —       Stop chime
  .claude/hooks/obsidian_capture.sh / obsidian_capture.py                    —       SubagentStop capture

INFRA BUGS (open)
  .claude/plans/Infra_Bugs/guidance-xbrl-reviewed-coverage-gaps.md           341 LOC
  .claude/plans/Infra_Bugs/guidance-upstream-unit-misclassification.md       448 LOC

REFERENCE
  .claude/plans/Extractions/extraction-pipeline-reference.md                 632 LOC  Canonical reference
  .claude/plans/Extractions/{10k,8k,10q,news}_reference.md                   —       Pre-consolidation
  .claude/plans/Extractions/8k_strategy.md                                   —       Strategy doc
  .claude/plans/Extractions/guidance-extraction-plan.md                      —       Pre-consolidation
  .claude/plans/GuidanceTrigger.md                                            469 LOC  Daemon design + verification
```

---

## §29 — Quick Reference: One-Job Walkthrough

```
1. trade_ready_scanner adds AAPL to trade_ready:entries (Redis HASH)
2. guidance_trigger_daemon sweep (60s tick):
   - HGETALL trade_ready:entries; filter earnings_date >= today-ACTIVE_WINDOW_DAYS
   - For asset transcript: find AAPL transcripts with guidance_status IN (NULL, in_progress)
   - SET NX EX 14400 guidance_lease:transcript:AAPL_2025-07-31T17.00.00-04.00
   - LPUSH extract:pipeline {asset, ticker, source_id, type, mode}
   - Pre-warm SEC cache for AAPL
3. KEDA sees listLength >= 1 → scales extraction-worker per current live spec (0..7).
   **NB**: this only happens if the ScaledObject is unpaused. Today the live cluster
   has `autoscaling.keda.sh/paused-replicas: "0"` set, so scaling is suppressed and
   extraction-worker stays at 0 regardless of queue depth. Remove the annotation to
   re-enable.
4. extraction-worker pod:
   - usage threshold check → BRPOP
   - mark Transcript.guidance_status='in_progress'
   - unlink /tmp/gu_written_AAPL_2025-07-31T17.00.00-04.00.json
   - open run_ledger row 'running' (component=guidance)
   - load types/guidance/config.yaml → {orchestrator: sonnet, primary: sonnet, enrichment: sonnet}
   - prompt: /extract AAPL transcript AAPL_2025-07-31T17.00.00-04.00 TYPE=guidance MODE=write
              PRIMARY_MODEL=sonnet ENRICHMENT_MODEL=sonnet RESULT_PATH=/tmp/extract_result_…
   - SDK call: cli_path=/home/faisal/.local/bin/claude, OAuth via .credentials.json,
               bypassPermissions, max_turns=80, max_budget_usd=15,
               MCP=mcp-neo4j-cypher-http (HTTP)
5. /extract orchestrator (Sonnet):
   - Step 1: spawn extraction-primary-agent (Sonnet)
6. Primary agent loads 8 files (slots 1-8):
   - 1A → CIK=0000320193
   - 1B → periodOfReport 2024-09-28 → fye_month=9
   - Bash warmup_cache.sh AAPL → /tmp/concept_cache_AAPL.json + /tmp/member_map_AAPL.json (+ 2B)
   - Bash warmup_cache.sh AAPL --transcript AAPL_…→ /tmp/transcript_content_AAPL_….json
   - 7A → existing Guidance labels for AAPL
   - Parse JSON, identify CFO section, extract items (e.g. Revenue qualitative "low single digits", GM 45.5-46.5% GAAP)
   - Build JSON payload to /tmp/gu_AAPL_AAPL_….json with all items, payload_origin='extract_v2'
   - Bash: ENABLE_GUIDANCE_WRITES=true guidance_write.sh /tmp/gu_AAPL_….json --write
7. guidance_write_cli main:
   - Phase A: for each item — inject source_id, slug label, _ensure_period (4-step cascade — Step B SEC cache hit)
   - apply_concept_resolution (Revenue → us-gaap:Revenues; Gross Margin / label_slug=gross_margin → us-gaap:GrossProfit via CONCEPT_CANDIDATES). Note: `operating_margin` would force-null (in NULL_QNAME_LABELS) but is not in this example.
   - Concept inheritance across segments
   - Phase B: skip-gate, _ensure_ids (V2 resolver: Revenue ratio+percent_yoy/null; GM ratio+percent 45.5/46.0/46.5)
   - resolve_concept_family (Revenue → us-gaap:Revenues; GM → us-gaap:GrossProfit)
   - Member resolution: Total → no member edges
   - create_guidance_constraints (idempotent, ensures 3 constraints, 2 indexes, 4 sentinels)
   - write_guidance_batch:
     - per item, 8 validation guards
     - atomic MERGE Cypher (Guidance + GuidancePeriod + GuidanceUpdate + 4 edges)
     - concept edge (LIMIT 1) if xbrl_qname set
     - member edges via UNWIND if non-empty
   - Write /tmp/gu_written_AAPL_2025-07-31T17.00.00-04.00.json (sidecar)
   - Print JSON summary to stdout
8. Primary agent reads CLI output, writes /tmp/extract_pass_guidance_primary_AAPL_….json
   {"status":"completed","items_extracted":12,"items_written":12,"errors":0}
9. Orchestrator checks enrichment gate: both files exist → spawn extraction-enrichment-agent
10. Enrichment agent:
    - Same 8 slots loaded (slot 2 = enrichment-pass; slot 4 = transcript-enrichment)
    - 7E readback: 12 items from primary
    - 7F baseline: 50 historical labels with frequency
    - Q&A 3F: full Q&A
    - Per exchange: ENRICHES / NEW ITEM / NO GUIDANCE
    - Completeness check vs 7F → re-scan if missing
    - Build enrichment JSON to /tmp/gu_AAPL_AAPL_…_enrichment.json
    - Bash guidance_write.sh ... --write → CLI writes/updates
    - Writes /tmp/extract_pass_guidance_enrichment_AAPL_….json
      {"status":"completed","items_enriched":3,"new_secondary_items":4,"errors":0}
11. Orchestrator writes RESULT_PATH JSON
12. Worker reads RESULT_PATH:
    - mark Transcript.guidance_status='completed'
    - close run_ledger row 'succeeded' with summary {items_extracted:12, items_written:4, enrichment_status:'enriched'}
      ▲ Note: items_written reads /tmp/gu_written_*.json which was overwritten by enrichment's
        CLI invocation. Enrichment wrote only the 4 changed+new items, so the sidecar — and
        the ledger summary — reflects 4, NOT 12+4=16. Primary's 12 writes happened (visible
        in Neo4j) but are invisible in this summary field. See §23.5.
    - unlink result_path
    - loop back to next BRPOP
13. Daemon's next sweep skips this source (status='completed').
```

That is the complete code-level mapping. Sections are intentionally non-redundant; cross-reference via the §-numbers when reading. Live numerical values reflect the verification snapshot in §25 — mutable counters (queue lengths, index read counts, edge totals, write counts) drift over time and should be re-verified before acting on them.
