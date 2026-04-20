# Earnings Automation Plan — Prediction + Learner

**Status**: design locked; implementation-ready (rev. 2026-04-19, post-verification pass)
**Goal**: production-grade automatic pipeline for `prediction` and `learner`, following the guidance extractor's outer pattern where useful, while preserving the earnings system's existing semantics for quarter identity, PIT, filesystem artifacts, and lesson recovery.

---

## 1. Live-Code Ground Truth

These are not proposals. These are already true in the repo today and the new pipeline should build on them rather than fight them.

1. **Quarter discovery is already canonicalized.**
   - `.claude/skills/earnings-orchestrator/scripts/get_quarterly_filings.py` is the authoritative historical quarter-discovery helper.
   - It is deterministic off `periodOfReport`, enforces `Item 2.02`, and only returns historical 8-Ks with `pf.daily_stock IS NOT NULL`.
   - `.claude/skills/earnings-orchestrator/scripts/event_json_manifest.py` is the shared semantic refresh layer for `events/event.json`.

2. **Prediction and learner already have strong artifact contracts.**
   - Prediction canonical artifact: `events/{quarter}/prediction/result.json`
   - Learner canonical artifact: `events/{quarter}/learning/result.json`
   - Learner is stronger than a plain file write: it also performs derived writes into `earnings-analysis/learnings/ticker/{TICKER}.json` and `earnings-analysis/learnings/global.json`, with recovery on re-entry.
   - The daemon still needs explicit `complete.json` sentinels for both components because `result.json` alone is not safe completion truth under automatic retries/re-entry.

3. **The orchestrator already owns the difficult semantics.**
   - `scripts/earnings/earnings_orchestrator.py` already handles:
     - quarter identity validation
     - PIT mode resolution
     - bundle assembly
     - predictor invocation + validation
     - learner PIT derivation
     - learner retry-on-validation-error
     - derived-write recovery
     - run-ledger open/close for both components
   - The daemon/worker stays thin and does not re-implement PIT or learner semantics.

4. **`live_state.json` already matters.**
   - It is the existing bridge for live-cycle quarter identity and learner PIT Tier 2 behavior.
   - We reuse it, not replace it.

5. **`scripts/earnings/run_ledger.py` already exists as durable machine state.**
   - Guidance, prediction, and learner all already fit its model.
   - Safer to extend/reuse than to invent a second durable status system.

6. **Current `scripts/earnings_trigger.py` is only a stub.**
   - Simple Redis listener that fires `/earnings-orchestrator`.
   - Does not implement gating, sequencing, leases, retries, or production-safe worker behavior.
   - Good conceptual repurpose, not a foundation to keep as-is.

7. **Guidance remains the outer-architecture reference, not the inner-semantics reference.**
   - Reuse from guidance: always-on daemon, Redis queue, KEDA-scaled worker, Redis lease-based dedup/stale recovery, centralized rate-limit guard.
   - Do **not** blindly copy: `guidance_status` as graph truth, source-node completion semantics, extraction-worker internals.

---

## 2. Requirements Now Captured

These are the requirements understood from Faisal's answers.

1. There are **two modes**: `historical` and `live`.
2. Historical is the primary seed path and must be **PIT-safe**.
3. Historical processing is **sequential by quarter**, oldest to newest.
4. The intended dependency chain is:
   - guidance for quarter `Q(n)`
   - prediction for quarter `Q(n)`
   - learning for quarter `Q(n)`
   - only then may the ticker advance to `Q(n+1)`
5. Live prediction is prioritized for TradeReady tickers with upcoming earnings.
6. Live learner is **deferred**, picked up before the next quarter's prediction cycle.
7. Trigger surface for live uses:
   - TradeReady as the candidate ticker universe
   - Neo4j 8-K ingestion completion as the actual readiness barrier
8. Queue topology: one new queue `earnings:pipeline`, one worker deployment, payload differentiates `prediction` vs `learning`.
9. Worker topology: separate `earnings-worker`, separate KEDA scaling, separate rate-limit reserve.
10. Historical + live share one overall system, each with its own rules.
11. The system is minimalistic, reliable, and production-grade from the start.

---

## 3. Recommended Production Design (v1)

### 3.1 Trigger Surface

The daemon runs two sweeps every `POLL_INTERVAL` seconds. They are composed, not alternatives.

**A. Live sweep** (always on; gated only by the master `EARNINGS_AUTOMATION_ENABLED`).

1. Read `trade_ready:entries` from Redis; restrict to tickers with `earnings_date >= today - ACTIVE_WINDOW_DAYS` (same active-window rule as guidance).
2. For each active ticker, query Neo4j for the newest earnings-8-K candidate where:
   - `formType = '8-K'` AND `items CONTAINS 'Item 2.02'`
   - ingested and queryable (row exists)
   - `daily_stock IS NULL` **AND** `filed_8k >= now() - 3 trading days` (hardened rule — §G2; implement "3 trading days" with the same XNYS `exchange_calendars` helper pattern already used in `scripts/trade_ready_scanner.py`, not a naive 72-hour subtraction)
3. Resolve quarter identity via `resolve_quarter_info(ticker, accession)`.
4. If the live prediction gate passes (§4), write/refresh `live_state.json` and enqueue **live prediction**.

**B. Historical / catch-up sweep** (two sub-functions, composed — §G3).

1. **Catch-up (always on):** iterate over every ticker covered by an existing `event.json` (filesystem glob under `earnings-analysis/Companies/*/events/event.json`) AND every TradeReady-active ticker. For each, run the first-incomplete-quarter walker (§3.6). Responsible for running deferred live-learners and cleaning up any chain hole on an active ticker. Runs **regardless of `HISTORICAL_BACKFILL_ENABLED`**.
2. **Backfill (flag-gated):** only when `HISTORICAL_BACKFILL_ENABLED=true`, union the catch-up universe with the full configured universe (~796) and run the same walker against cold tickers.

Mandatory code comment on the gating rule:
```
# HISTORICAL_BACKFILL_ENABLED gates universe-walk ONLY.
# Deferred-learner catch-up for TradeReady and event.json-covered tickers
# MUST run regardless of this flag, otherwise live predictions for cycle n+1
# block on the unrun live learner from cycle n.
```

### 3.2 Queue Topology

- Queue: `earnings:pipeline` (one Redis LIST)
- Dead-letter: `earnings:pipeline:dead`
- Consumer: `earnings-worker` pods (`BRPOP`)

Payload shape:
```json
{
  "component": "prediction",
  "mode": "live",
  "ticker": "AVGO",
  "quarter_label": "Q2_FY2026",
  "accession_8k": "0001...",
  "filed_8k": "2026-05-28T16:05:00-04:00",
  "priority": "live_prediction",
  "trigger_origin": "trade_ready"
}
```

Notes:
1. Use `component`, not generic `type`, so this queue does not semantically collide with `extract:pipeline`.
2. Always stamp `mode` explicitly at enqueue time.
3. Always include `quarter_label` once known; the worker never re-discovers identity unless recovery requires it.
4. `trigger_origin` is observational only in v1.

### 3.3 Worker Topology

Use a new worker deployment:

- Deployment: `earnings-worker`
- Queue: `earnings:pipeline`
- KEDA scaled separately from `extraction-worker`
- Independent rate-limit reserve
- No shared runtime path with guidance extraction
- **`terminationGracePeriodSeconds: 7500`** — must exceed `LEARNING_SUBPROCESS_TIMEOUT` (7200s) + 300s slack so rolling updates never SIGKILL an in-flight learner. Worker code propagates SIGTERM to the subprocess (via `process.terminate()`) so the child exits gracefully before grace expires. (§G6)

**Claude Code auth contract — locked**

Must mirror the proven guidance extraction deployment pattern; must **not** use billable Anthropic API auth.

1. Mount the local Claude Code CLI at `/home/faisal/.local`
2. Mount `/home/faisal/.claude` so `~/.claude/.credentials.json` is available
3. Mount `/home/faisal/.claude.json` and copy it into writable HOME on container start **for parity with `extraction-worker.yaml`**, but treat this as optional runtime hardening, not auth truth. The real auth requirement is `~/.claude/.credentials.json`; `.claude.json` is local Claude Code state/config.
4. Set:
   - `ANTHROPIC_API_KEY=""`
   - `CLAUDE_CODE_OAUTH_TOKEN=""`
5. Invoke Claude through `/home/faisal/.local/bin/claude`
6. Preserve orchestrator's `_assert_claude_code_oauth_ready()` fail-closed behavior

This guarantees the earnings pipeline uses Claude Code Max/OAuth, not API billing.

**MCP wiring — locked (code change required, §G7)**

**Scope of this fix**:

- **Learner path (`_run_learner_via_sdk`) — MUST-FIX.** The learner's Data SubAgents explicitly call `mcp__neo4j-cypher__read_neo4j_cypher` and `mcp__neo4j-cypher__*` tools per `earnings-learner/SKILL.md` §Phase 2 source-priority table. Without the HTTP MCP override, every learner run fails inside K8s because the stdio wrapper in `.mcp.json` points at host NodePort `localhost:30687`, which does not exist inside a pod.
- **Predictor path (`_run_predictor_via_sdk`) — SYMMETRY ONLY.** The predictor SKILL.md allows only `Read, Write, Glob`; the LLM never calls any MCP tool. Applying the same override is harmless and future-proof (if we later add an MCP-consuming predictor tool), but not strictly required for v1 correctness.

Recommendation: apply the identical override to both paths so the code is symmetric and no one has to remember the asymmetry, but the true blocker is the learner.

The orchestrator's `_run_learner_via_sdk` (and `_run_predictor_via_sdk`) currently do NOT pass `mcp_servers` to `ClaudeAgentOptions`, so they fall through to `.mcp.json`, whose stdio wrapper targets the host NodePort and fails inside K8s. Setting `MCP_NEO4J_URL` alone is insufficient without a code-level override.

Required change (one place each in `_run_learner_via_sdk` and `_run_predictor_via_sdk`):

```python
sdk_kwargs = {
    **LEARNER.as_sdk_kwargs(),           # or PREDICTOR.as_sdk_kwargs()
    "setting_sources": ["project"],
    "permission_mode": "bypassPermissions",
    "stderr": _stderr_sink,
    "cli_path": cli_path,
    "env": _sdk_subprocess_env(),
}
mcp_url = os.environ.get("MCP_NEO4J_URL")
if mcp_url:
    sdk_kwargs["mcp_servers"] = {
        "neo4j-cypher": {
            "type": "http",
            "url": mcp_url,
            "headers": {"Host": "localhost:8000"},
        },
    }
options = ClaudeAgentOptions(**sdk_kwargs)
```

Matches `canary_sdk.py:48-63`. When `MCP_NEO4J_URL` is unset (operator CLI), kwarg is omitted → SDK falls through to `.mcp.json` stdio → works locally. When set (K8s pod), HTTP MCP wins → works in K8s.

Worker responsibility is intentionally narrow:

1. Pop one job
2. Acquire / verify job lease
3. Invoke the orchestrator with the correct mode + quarter context
4. Respect centralized usage guard / rate-limit guard
5. Requeue or close according to outcome

Invocation mode:

1. **Subprocess, not in-process SDK**
2. Worker runs: `venv/bin/python scripts/earnings/earnings_orchestrator.py ...`
3. Prediction timeout default: `1800s`
4. Learner timeout default: `7200s`
5. Worker subprocess env also blanks direct Anthropic auth variables as belt-and-suspenders
6. Add `--mode {historical,live}` to the orchestrator CLI and pass the payload's `mode` through unchanged. This flag is **observational only** (run ledger / logs / Obsidian) and must not override quarter identity or PIT logic.

The worker does **not** own:

- PIT derivation rules
- lesson-file semantics
- quarter sequencing logic
- quarter identity math beyond recovery assistance
- component run-ledger lifecycle (the orchestrator opens/closes prediction/learning runs)

### 3.4 Durable State / Source of Truth

**Recommendation: do not introduce `prediction_status` / `learning_status` on Neo4j in v1.**

Reason:

1. Prediction + learner already have durable filesystem artifacts.
2. Learner completion is not just a graph-style boolean; it includes derived lesson writes and recovery behavior.
3. `run_ledger.py` already exists as append-only machine state and wraps the full component execution.
4. Adding new graph statuses creates a split-brain problem between filesystem artifacts, run ledger, and graph properties.

Recommended truth model:

1. **Eligibility trigger truth** — Neo4j + Redis TradeReady
2. **Dedup / in-flight truth** — Redis leases
3. **Completion truth** — per-component completion sentinel files; `run_ledger.py` for audit, history, and Obsidian surfacing

**Per-component completion and failure artifacts (locked)**:

| Component | Result file (content) | Completion sentinel | Failure sentinel |
|---|---|---|---|
| prediction | `events/{Q}/prediction/result.json` | `events/{Q}/prediction/complete.json` | `events/{Q}/prediction/failed.json` |
| learning   | `events/{Q}/learning/result.json`   | `events/{Q}/learning/complete.json`   | `events/{Q}/learning/failed.json`   |

**Prediction completion sentinel spec (§G4b)**:

- Owner: `earnings_orchestrator` — writes `prediction/complete.json` immediately AFTER `validate_prediction_result(...)` returns successfully (earnings_orchestrator.py line ~3425).
- Never written on any failure path.
- **Why required**: both `finalize_prediction_result` and `validate_prediction_result` can raise AFTER `result.json` is already on disk. Without a sentinel, a stale bad file would masquerade as complete.
  - Failure mode A: LLM output missing a required analytic field → `finalize_prediction_result:3094-3096` raises `ValueError` BEFORE the atomic metadata rewrite. Raw (incomplete) LLM file sits on disk.
  - Failure mode B: canonicalized file fails `validate_prediction_result` (e.g., lesson_labels positional mismatch, cites-wrong-label, analysis-substring violation). Canonicalized-but-invalid file sits on disk.
- Contents:
  ```json
  {"completed_at": "ISO8601", "sdk_session_id": "...", "prompt_version": "...", "schema_version": 1}
  ```

**Learning completion sentinel spec (§G4)**:

- Owner: `earnings_orchestrator.run_learner_for_quarter` — writes `learning/complete.json` in two places:
  1. After `SUCCEEDED` path (line ~2185), AFTER `append_ticker_lesson` and `append_global_lessons` both return successfully.
  2. After `RECOVERED` path (line ~2063), AFTER derived-write recovery succeeds.
- Never written on any `FAILED_*` outcome.
- **Why required**: `learning/result.json` is written mid-flow by the SDK, BEFORE derived lesson appends. Using it as completion truth would cause the daemon to treat an incomplete learner as complete.
- Contents:
  ```json
  {"completed_at": "ISO8601", "sdk_session_id": "...", "outcome": "succeeded"|"recovered", "schema_version": 1}
  ```

**Failure sentinel spec (§G5)**:

- Owner: `earnings_worker` — writes `{component}/failed.json` after:
  - `MAX_RETRIES` exhausted for any non-rate-limit failure, OR
  - A single fatal error the worker classifies as non-retryable (e.g., dead-letter conditions).
- Contents:
  ```json
  {"failed_at": "ISO8601", "error": "...(first 500 chars)...", "outcome": "...", "retry_count": N, "schema_version": 1}
  ```
- **Why required**: without it, the daemon has no way to represent "halted"; it would re-enqueue the same failing quarter on every sweep.

**Daemon eligibility check (three-state, AND-hardened)**:

```python
def is_eligible(component_dir: Path) -> str:
    # Halted trumps everything — failed.json is the authoritative halt marker.
    if (component_dir / "failed.json").exists():
        return "halted"         # chain blocked; log [HALTED] and skip

    # Completion requires BOTH the artifact AND the sentinel.
    # Sentinel-only is unsafe: if result.json is missing/corrupt (operator rm,
    # disk issue, buggy cleanup), downstream would still read a stale sentinel
    # and attempt to consume a missing artifact.
    if (component_dir / "complete.json").exists() and \
       (component_dir / "result.json").exists():
        return "complete"       # advance chain walker

    return "eligible"           # enqueue
```

Interaction with orchestrator recovery: the learner's recovery branch triggers only when `result.json` exists (`run_learner_for_quarter:2039`). If `complete.json` is present but `result.json` is missing, the AND check returns `eligible` → re-enqueue → orchestrator runs as a first-time execution (not recovery) → writes both files fresh. Self-healing without special-casing.

Operator recovery for halted quarter: `rm events/{T}/{Q}/{component}/failed.json`. Next sweep re-enqueues. Mirrors the guidance-worker manual recovery flow.

### 3.4a Leases

Lease schema is locked:

1. `earnings_lease:prediction:{accession_8k}` — TTL `2100s`
2. `earnings_lease:learning:{accession_8k}` — TTL `7500s`

Why:

1. Namespaced away from guidance leases
2. Accession is the natural event key
3. TTL must exceed subprocess timeout by a cleanup buffer, otherwise the daemon can see an expired lease while the worker is still terminating the subprocess and writing failure state
4. Prediction jobs are short
5. Learner jobs are materially longer

### 3.5 Quarter Identity and PIT

Quarter identity remains owned by the existing earnings stack:

1. Historical quarter order comes from `event.json`
2. `event.json` regeneration comes from `.claude/skills/earnings-orchestrator/scripts/event_json_manifest.py`
3. Historical event discovery comes from `.claude/skills/earnings-orchestrator/scripts/get_quarterly_filings.py`
4. Live quarter identity comes from resolving the live 8-K directly
5. Learner PIT remains owned by `derive_learner_pit()` inside the orchestrator

Most important anti-regression rule in the entire design:

> The daemon decides **when** to run. The orchestrator decides **what quarter this is** and **what PIT means**.

### 3.6 Historical Flow

For a historical ticker:

1. Read / refresh `event.json`
2. Walk quarters in chronological order
3. Find the **first incomplete quarter**
4. For that quarter:
   - if prediction not complete: enqueue historical prediction
   - else if learning not complete: enqueue historical learning
   - else continue
5. Never enqueue more than one next-step job per ticker at a time

This gives strict sequential enforcement without a heavy state machine.

`event.json` refresh policy (locked, lazy semantic):

1. Use lazy semantic refresh, matching the existing orchestrator pattern.
2. Refresh when:
   - `event.json` is missing
   - `event.json` is invalid
   - the daemon has concrete evidence a live quarter has **graduated** (`live_state.json` names an accession and Neo4j now reports `daily_stock IS NOT NULL` for that same accession) but `event.json` still lacks that quarter/accession
   - the daemon expects a just-graduated live quarter to now appear historically and it does not
3. Do **not** refresh every active ticker on every sweep.
4. Do **not** refresh merely because `live_state.json` exists and the quarter is absent from `event.json`; that is the normal steady-state while the quarter is still live.

Keeps refresh logic consistent with `event_json_manifest.py` and avoids unnecessary steady-state Neo4j load.

### 3.7 Live Flow

For a live TradeReady ticker:

1. Detect live 8-K candidate from Neo4j after ingestion completion.
2. Resolve current live quarter identity.
3. Verify prerequisite chain across prior quarters (§4 — historical and live share all gates EXCEPT same-quarter guidance, which is historical-only per §8).
4. Before enqueue, daemon writes/upserts `events/live_state.json`.
   Locked file shape:
   ```json
   {
     "schema_version": 1,
     "ticker": "AVGO",
     "quarter_label": "Q2_FY2026",
     "accession_8k": "0001...",
     "filed_8k": "2026-05-28T16:05:00-04:00",
     "written_at": "2026-05-28T16:06:11Z"
   }
   ```
   Write atomically (`tmp` + `os.replace`), ideally via the same `atomic_write_json(...)` helper used by `event_json_manifest.py`.
5. Enqueue **live prediction**.
6. Do **not** enqueue learner immediately.
7. When that same quarter later becomes historical (`daily_stock` now available and quarter appears in refreshed `event.json`), historical catch-up sweep picks up the deferred learner.
8. Daemon deletes `live_state.json` only when:
   - **Quarter-label match required (§G14)**: daemon reads `live_state.json`, compares its stored `quarter_label` to the graduating quarter's label, and deletes only when they match. If the file contains a NEWER quarter's state (because a newer filing already overwrote it), preserve it untouched — it is still valid Tier-2 input for the graduating quarter's own deferred learner.
   - Supersession: when writing state for a newer live quarter, overwrite atomically (write-then-replace).

`live_state.json` ownership is locked: **daemon-owned for writes + deletions**, not orchestrator-owned.

### 3.8 Within-Ticker Sequential Enforcement

Daemon-owned.

> The daemon may enqueue only the next eligible missing step for a ticker. Never multiple quarters of the same ticker at once.

Specifically:

1. No `Q(n+1)` prediction if `Q(n)` learner is incomplete.
2. No learner for `Q(n)` if prediction for `Q(n)` is incomplete.
3. No duplicate quarter jobs if a lease exists.
4. Under daemon-managed automation, learner `SKIPPED_*` outcomes are treated as a gate bug, not a normal steady-state path. The daemon should only enqueue learner when prediction completion and `daily_stock` availability already make skip impossible.

Note: because live-prediction eligibility requires "all prior chain complete" (§4), a ticker is never simultaneously eligible for both a live prediction AND a historical step — the two conditions are mutually exclusive. Cross-type within-ticker precedence is therefore a non-issue.

### 3.9 Cross-Ticker Parallelism and Priority

Cross-ticker parallelism comes from KEDA replicas, not from multi-job logic inside one worker.

Operational priority (while keeping one queue) is intentionally **two-tier**, not a fake four-tier scheduler:

1. `live_prediction` — high-priority lane
2. all other jobs (`historical_prediction`, `deferred_learning`, `historical_learning`) — normal lane

Implementation is locked as a **two-lane LIST**, not a ZSET:

1. Queue is one Redis LIST: `earnings:pipeline`
2. Worker consumes with `BRPOP`
3. High-priority `live_prediction` jobs are inserted with `RPUSH`
4. Normal jobs are inserted with `LPUSH`

**Ordering semantics (explicitly called out)**:

- Within the **live-prediction lane, jobs pop in LIFO order** (newest filing first). RPUSH appends to the tail; BRPOP pops the tail.
- Within the **normal lane, jobs pop in FIFO order**. LPUSH prepends to the head; BRPOP drains tail-first once the live lane is empty, reaching older LPUSH'd items first.
- The queue itself does **not** distinguish `historical_prediction` vs `deferred_learning` vs `historical_learning`. That ordering is handled by the daemon's first-incomplete-quarter walker and per-ticker sequencing rules, not by Redis priority metadata.
- At KEDA `maxReplicas ≥ typical-concurrent-live-prediction-burst`, ordering has no observable effect — multiple pods drain in parallel.
- If strict FIFO within the live lane later becomes a requirement, upgrade paths are (a) dual queues or (b) ZSET with arrival-time score.

This v1 priority scheme is intentionally simple and gives "high before normal" behavior; it does **not** implement a strict stable four-tier scheduler inside Redis.

### 3.10 Learner-Specific Rules

1. **Historical learner** — runs when prediction is complete and `daily_stock` exists. PIT cutoff derived by existing `derive_learner_pit`.
2. **Live learner** — deferred; not triggered immediately after live prediction; picked up later by historical catch-up sweep.
3. **Deferred learner detection** — via `live_state.json` as the bridge; once the quarter graduates into `event.json`, historical catch-up resumes ownership.
4. **Skipped learner outcomes are not a normal worker state.** If the worker ever sees a learner subprocess return without `learning/complete.json`, that is treated as missing-sentinel failure/retry territory; steady-state automation should have prevented the skip with gates before enqueue.

### 3.11 Failure / Retry / Rate Limit

#### Retry policy

Same outer retry methodology as the proven guidance worker, slightly tighter:

1. Generic non-rate-limit worker failures: **`MAX_RETRIES = 2`** (original + 2 retries max).
2. Applies to: subprocess launch failure, subprocess timeout, missing completion sentinel, unexpected orchestrator crash / non-zero exit.
3. Rate limit: same as `extraction_worker.py` — requeue without retry penalty; pause 300s.
4. Dead-letter queue: `earnings:pipeline:dead`. After exhausting retries, payload is dead-lettered and the ticker chain halts via the failure sentinel.
5. Inner component semantics may still differ: predictor has its own validation contract; learner already has one internal informed retry on validation failure.

Closer to already-proven guidance-worker methodology than to a bespoke retry taxonomy.

#### Dead-letter cleanup (atomic best-effort sequence, §G10)

When `MAX_RETRIES` is exhausted, the worker runs atomically per job:

1. Write `events/{T}/{Q}/{component}/failed.json` with error + retry_count (spec per §3.4).
2. DEL `earnings_lease:{component}:{accession_8k}` — explicit lease cleanup (defense in depth; TTL would expire anyway).
3. `LPUSH earnings:pipeline:dead` with payload annotated with `_error` + `_failed_at` fields.
4. No additional worker-side `close_run(...)`. The orchestrator owns component `open_run` / `close_run`. If the subprocess never starts cleanly or dies before the orchestrator can close its run, the authoritative failure record is `failed.json` + DLQ payload + worker logs.

If any step fails mid-sequence, remaining steps still run (best-effort). The `failed.json` sentinel is the authoritative halt marker; the other three are observability.

#### Chain halt

> If a quarter reaches terminal failure after allowed retries, halt the ticker chain. Do not advance to `Q(n+1)`.

Matches the user requirement and preserves data quality. Enforced mechanically via the `failed.json` sentinel + daemon three-state eligibility check.

#### Rate limits

Centralize the usage/rate-limit guard currently embedded in `extraction_worker.py` into a shared helper, then reuse it for:

1. guidance worker
2. earnings worker prediction
3. earnings worker learner

See §G11 for module-path spec.

### 3.12 Observability and Rollout

#### Rollout

Recommended rollout switches:

1. `EARNINGS_AUTOMATION_ENABLED`
2. `HISTORICAL_BACKFILL_ENABLED`

Sufficient for safe rollout. No additional launch-phase flags.

#### Observability

Primary sources:

1. `run_ledger.jsonl`
2. `Run Index.md`
3. daemon logs
4. worker logs
5. Redis lease inspection

Recommended addition:

- `Earnings Auto Index.md` generated from run ledger + ticker-chain scan state, with explicit `mode` display (`live` vs `historical`).

---

## 4. `has_historical_gates` — Recommended Shape

For prediction of `Q(n)`, gates apply as follows. Historical and live modes share all gates EXCEPT same-quarter guidance (§8 lock).

| # | Gate | Historical prediction | Live prediction |
|---|---|---|---|
| G-1 | Current-quarter 8-K exists and is queryable in Neo4j | **REQUIRED** | **REQUIRED** |
| G-2 | 8-K `formType='8-K'` AND `items CONTAINS 'Item 2.02'` | **REQUIRED** | **REQUIRED** |
| G-3 | Quarter identity resolvable (`quarter_label`, `period_of_report`) | **REQUIRED** | **REQUIRED** |
| G-4 | Current-quarter `guidance_status='completed'` | **REQUIRED** | SKIPPED (§8) |
| G-5 | All prior `Q(1..n-1)` predictions have `prediction/complete.json` | **REQUIRED** | **REQUIRED** |
| G-6 | All prior `Q(1..n-1)` learnings have `learning/complete.json` | **REQUIRED** | **REQUIRED** |
| G-7 | Company sector present in Neo4j | **SOFT** (warn; degrade gracefully) | **SOFT** |
| G-8 | Company CIK present in Neo4j | **SOFT** | **SOFT** |

**Critical clarifications**:

1. **Prior-chain gates (G-5, G-6) apply to BOTH modes.** The user-approved asymmetry is limited to G-4 (same-quarter guidance). Any ticker with an incomplete prior quarter blocks both historical and live predictions until catch-up runs.
2. For **brand-new live tickers** with zero prior Neo4j history, prior-chain gates are vacuously satisfied (no prior rows). First-cycle empty-lessons prediction is supported — that is what O11 means.
3. For the **learner**, gates are separate and simpler:
   - Current-quarter prediction complete (`prediction/complete.json` exists)
   - `daily_stock IS NOT NULL` on the 8-K's `PRIMARY_FILER` relationship
   - No prior-chain gate on the learner itself; only the predictor-side gate for the NEXT cycle enforces the chain.

---

## 5. Decision Log

| ID | Decision | State |
|---|---|---|
| A1 | Trigger source = hybrid (`trade_ready` live + historical bootstrap universe) | **Locked** |
| A2 | New queue = `earnings:pipeline` | **Locked** |
| A3 | New worker deployment = `earnings-worker` | **Locked** |
| B1 | `has_historical_gates` should require prior prediction + learning chain completion | **Locked** |
| B2 | Same-quarter guidance gate is asymmetric: historical yes, live no | **Locked** |
| B3 | Mode stamped explicitly in payload; `daily_stock` NULL/non-NULL is an input signal, not sole truth | **Locked** |
| B4 | Universe = TradeReady for live + bootstrap universe for historical | **Locked** |
| C1 | Within-ticker sequencing enforced by daemon, one next-step job per ticker | **Locked** |
| C2 | Cross-ticker parallelism via KEDA replicas | **Locked** |
| C3 | Centralized usage guard; no per-component scheduler logic in v1 | **Locked** |
| D1 | Historical learner immediate, live learner deferred | **Locked** |
| D2 | Deferred learner detected through the same quarter reappearing in historical/event manifest flow | **Locked** |
| D3 | Historical bootstrap and live catch-up share one daemon + one worker + one queue | **Locked** |
| E1 | Worker-level retry policy shared; inner component semantics may differ | **Locked** |
| E2 | Terminal failure halts ticker chain | **Locked** |
| E3 | Rate-limit guard centralized and shared with guidance | **Locked** |
| F1 | K8s env knobs supported; redundant knobs avoided | **Locked** |
| F2 | Single stop/run flag for rollout | **Locked** |
| M1 | Obsidian view generated from machine state, not hand-maintained | **Locked** |
| M3 | `scripts/earnings_trigger.py` repurposed into the new earnings daemon path | **Locked** |
| O1 | Claude auth path = Claude Code Max/OAuth only, mirroring extraction-worker deployment | **Locked** |
| O2 | Eligibility truth = filesystem artifacts + per-component completion sentinels; ledger is observational | **Locked** |
| O3 | `event.json` refresh = lazy semantic refresh, not every-sweep rebuild | **Locked** |
| O4 | `live_state.json` owner = daemon | **Locked** |
| O5 | Lease keys = `earnings_lease:*` with component-specific TTLs | **Locked** |
| O6 | Worker invokes orchestrator via subprocess | **Locked** |
| O7 | Priority = one LIST with dual-ended push, not ZSET | **Locked** |
| O8 | Retry model follows proven guidance-worker methodology with tighter cap (`MAX_RETRIES=2`) | **Locked** |
| O9 | `ACTIVE_WINDOW_DAYS` stays single, not split | **Locked** |
| O10 | `trigger_origin` is observational only in v1 | **Locked** |
| O11 | Brand-new live tickers (zero prior history) do not force historical backfill before first live prediction; prior-chain gates are vacuously satisfied | **Locked** |
| O12 | `prediction/complete.json` sentinel required — symmetric with learner; protects against stale `result.json` after finalize/validate exceptions | **Locked** |
| O13 | `{component}/failed.json` sentinel is canonical halt marker; daemon three-state eligibility check (complete / halted / eligible) | **Locked** |
| O14 | `HISTORICAL_BACKFILL_ENABLED` gates universe-walk ONLY; catch-up sweep is always on | **Locked** |
| O15 | Live sweep uses hardened `daily_stock IS NULL AND filed_8k >= now - 3 trading days` rule, implemented with XNYS trading-day math (same helper pattern as `trade_ready_scanner.py`) | **Locked** |
| O16 | Orchestrator SDK code must conditionally inject `mcp_servers` HTTP override when `MCP_NEO4J_URL` is set. Learner path = MUST-FIX; predictor path = symmetry-only. Omit kwarg otherwise (local CLI path) | **Locked** |
| O21 | Completion truth is AND of result.json + complete.json (not sentinel-only). Defense against corruption/manual-rm of artifact | **Locked** |
| O17 | `terminationGracePeriodSeconds=7500` on earnings-worker pod; SIGTERM propagates to subprocess | **Locked** |
| O18 | Live-prediction lane is LIFO; documented + acceptable at KEDA-max ≥ typical burst | **Locked** |
| O19 | `live_state.json` delete requires `quarter_label` match against the graduating quarter | **Locked** |
| O20 | DLQ cleanup is atomic best-effort: failed.json → lease DEL → LPUSH dead. Worker does NOT call `close_run` — orchestrator owns component ledger lifecycle (§3.11) | **Locked** |

---

## 6. Env Knobs — Defaults

| Var | Default | Where set | Purpose |
|---|---|---|---|
| `EARNINGS_AUTOMATION_ENABLED` | `false` | K8s env | Master stop/run flag; must flip to `true` to start |
| `HISTORICAL_BACKFILL_ENABLED` | `false` | K8s env | Universe-walk ON/OFF. Catch-up is always on, independent of this |
| `POLL_INTERVAL` | `30` | K8s env | Daemon sweep frequency (seconds) |
| `ACTIVE_WINDOW_DAYS` | `45` | K8s env | Covers SEC 10-Q filing deadline; single knob |
| `PREDICTION_LEASE_TTL` | `2100` | K8s env | 35 min — timeout + 5 min cleanup buffer |
| `LEARNING_LEASE_TTL` | `7500` | K8s env | 2h05m — timeout + 5 min cleanup buffer |
| `PREDICTION_SUBPROCESS_TIMEOUT` | `1800` | K8s env | 30 min subprocess ceiling; lease adds 5 min cleanup buffer |
| `LEARNING_SUBPROCESS_TIMEOUT` | `7200` | K8s env | 2h subprocess ceiling; lease adds 5 min cleanup buffer |
| `MAX_RETRIES` | `2` | K8s env | Original + 2 retries before DLQ + chain halt |
| `MCP_NEO4J_URL` | `http://mcp-neo4j-cypher-http.mcp-services.svc.cluster.local:8000/mcp` | K8s env | REQUIRED in K8s for learner's subagents (§G7) |
| `GUIDANCE_DAILY_INTERACTIVE_PCT` | `10` | K8s env (guidance-worker) | Guidance reserve (rename of current `DAILY_INTERACTIVE_PCT` for clarity) |
| `EARNINGS_DAILY_INTERACTIVE_PCT_LIVE` | `0` | K8s env (earnings-worker) | Live predictions never pause for budget |
| `EARNINGS_DAILY_INTERACTIVE_PCT_HISTORICAL` | `10` | K8s env (earnings-worker) | Historical prediction/learning pauses like guidance |
| `DAILY_INTERACTIVE_PCT_SONNET` | `5` | K8s env (both workers) | Global Sonnet-specific reserve |

Explicitly NOT present (considered and rejected for v1):

- `MAX_CONCURRENT_LEARNERS` — redundant with KEDA `maxReplicas` + one-job-per-worker-process.
- Split `PREDICTION_ACTIVE_WINDOW_DAYS` / `LEARNING_ACTIVE_WINDOW_DAYS` — single window is cheaper and simpler.
- `MAX_TURNS` / `MAX_BUDGET_USD` — already on the orchestrator's `config/llm_models.py::LLMRole` profile; overriding from K8s would create two-source-of-truth.

---

## 7. Recommended Simplifications / Challenges

These are the places where the simpler design is also the safer design.

1. **Do not mirror guidance's Neo4j status pattern for prediction/learning.** Same outer pipeline pattern: yes. Same graph-status truth model: no.
2. **Do not hard-gate prediction on sector/CIK presence.** Warn loudly; degrade gracefully; avoid blocking the entire chain on metadata quality.
3. **Do not build a second learner scheduler for live mode.** Let the daemon own `live_state.json`; let historical catch-up naturally pick up the deferred learner later.
4. **Do not move PIT logic into the daemon.** Keep it inside the orchestrator where it already exists and is tested by usage.
5. **Do not overcomplicate queue topology.** One queue is fine; payloads must carry explicit component + mode + quarter identity.
6. **Do not use Anthropic API auth anywhere in this pipeline.** Mirror the proven guidance extraction worker setup; Claude Code Max/OAuth only.
7. **Do not force first-time live tickers through silent backfill before their first prediction.** First live prediction may legitimately have empty `learning_context`; the next cycle naturally gets lessons.

---

## 8. Final Lock: Same-Quarter Guidance Gate

This final architectural question is resolved.

Locked behavior:

1. **Historical prediction** — hard-gated on same-quarter `guidance_status = completed`.
2. **Live prediction** — **not** hard-gated on same-quarter guidance extraction; readiness barrier is ingested/queryable raw 8-K.

Why:

1. The prediction bundle already reads the raw 8-K / EX-99 text directly.
2. Same-quarter structured guidance is helpful but not required for a viable live prediction.
3. Hard-gating live prediction on guidance would add avoidable minutes of latency.
4. Historical has no latency pressure, so the gate improves training cleanliness at near-zero cost.

Empirical evidence: all 15 AVGO/NVDA/BURL calibration quarters had `guidance_history.series = []` (task T2 in `learner.md`); the predictor still produced usable predictions by inferring guide-vs-consensus from press-release prose.

---

## 9. Residual-Doubt Answers (Locked)

These were the final operational questions raised during review; now answered.

1. `RD-1` completion truth: **AND of result.json + complete.json for each component** (`prediction/result.json` AND `prediction/complete.json`; `learning/result.json` AND `learning/complete.json`). Sentinel-only is rejected — if the artifact disappears but the sentinel survives, downstream misbehaves. Ledger remains observational.
2. `RD-2` `event.json` refresh: **Locked = lazy semantic refresh**
3. `RD-3` `live_state.json` owner: **Locked = daemon (with quarter_label-match delete)**
4. `RD-4` lease keys: **Locked**
5. `RD-5` worker invocation: **Locked = subprocess**
6. `RD-6` priority mechanism: **Locked = one LIST with dual-ended push; LIFO on live acceptable**
7. `RD-7` retry policy: **Locked = proven guidance-worker methodology, `MAX_RETRIES=2`**
8. `RD-8` active window: **Locked = single `ACTIVE_WINDOW_DAYS=45`**
9. `RD-9` `trigger_origin`: **Locked = observational only**
10. `RD-10` new TradeReady ticker behavior: **Locked = empty lessons OK for first cycle; no forced silent backfill**

---

## 10. Must-Fix Operational Gaps (Locked)

These seven items MUST be in code before the plan is implementation-ready. They are spec precision, not architectural changes.

### G2 — Hardened live-mode detection (§3.1)

**Gap**: raw `daily_stock IS NULL` as sole live filter misclassifies orphan-returns 8-Ks as "live forever".

**Fix**: augment with freshness:
```
if daily_stock IS NOT NULL                → mode = historical
elif filed_8k >= (now - 3 trading days)   → mode = live
else                                      → mode = historical (orphan-NULL; chain gates apply)
```

Implementation note: compute the 3-trading-day cutoff with XNYS sessions (`exchange_calendars`), reusing the same helper pattern already proven in `scripts/trade_ready_scanner.py`. Do not approximate with plain calendar days.

### G3 — Catch-up sweep independent of backfill flag (§3.1)

**Gap**: deferred-live-learners must always run; otherwise live cycle n+1 blocks on cycle n's unrun learner.

**Fix**: two sub-functions composed inside the daemon. Universe-walk is flag-gated; TradeReady + event.json-covered catch-up is always on (the code-comment invariant in §3.1).

### G4 — Learner completion sentinel `learning/complete.json` (§3.4)

**Fix**: orchestrator writes it after BOTH `SUCCEEDED` and `RECOVERED` paths, AFTER lesson appends succeed. Never on `FAILED_*`.

### G4b — Prediction completion sentinel `prediction/complete.json` (§3.4)

**Fix**: orchestrator writes it AFTER `validate_prediction_result` returns successfully (line ~3425). Protects against stale bad `result.json` left by `finalize_prediction_result` (missing-field raise) or `validate_prediction_result` (schema/T1 rejection) exceptions. Symmetric with G4.

### G5 — Failure sentinel `{component}/failed.json` (§3.4 + §3.11)

**Fix**: worker writes it after `MAX_RETRIES` exhausted. Daemon eligibility is a three-state check (halted / complete / eligible). Operator recovery = delete the file.

### G6 — Pod grace period + SIGTERM propagation (§3.3)

**Fix**: `terminationGracePeriodSeconds: 7500` in `earnings-worker.yaml`. Worker code propagates SIGTERM to the orchestrator subprocess via `process.terminate()` so the subprocess exits before K8s SIGKILLs.

### G7 — MCP code-level override in orchestrator SDK path (§3.3)

**Fix — scope matters**:

- **Learner path (`_run_learner_via_sdk`) — MUST-FIX.** The learner's Data SubAgents call `mcp__neo4j-cypher__*` tools directly; without the HTTP override, every K8s run fails.
- **Predictor path (`_run_predictor_via_sdk`) — SYMMETRY ONLY.** Predictor SKILL.md allows only `Read/Write/Glob`; no MCP tool invocations. Applying the override is safe + future-proof, not strictly required for v1.

Both get a ~10-line conditional injection when `MCP_NEO4J_URL` env var is set, matching `canary_sdk.py:48-63`. Apply both for code symmetry and to avoid one-sided asymmetry that a future editor could miss.

---

## 11. Should-Fix Operational Details (Locked)

Six items for operational polish. Not production-breaking, but close every hole.

### G8 — `POLL_INTERVAL` default = 30s (§6)

Balanced: 2 sweeps/min, negligible Neo4j load (2 batched Cyphers/sweep + ticker-stat cost).

### G10 — DLQ cleanup is an atomic best-effort sequence (§3.11)

Order: `failed.json` → lease DEL → LPUSH dead. If any step fails, log and continue; the sentinel is the authoritative halt marker. Worker does NOT call `close_run` — component ledger lifecycle is owned by the orchestrator (§3.11 invariant).

### G11 — Budget gate centralization

Factor `extraction_worker.is_over_usage_threshold` into `scripts/shared/budget_gate.py`. Both workers import. Env-var split:

- `GUIDANCE_DAILY_INTERACTIVE_PCT` (default 10)
- `EARNINGS_DAILY_INTERACTIVE_PCT_LIVE` (default 0 — live never pauses)
- `EARNINGS_DAILY_INTERACTIVE_PCT_HISTORICAL` (default 10)
- `DAILY_INTERACTIVE_PCT_SONNET` (default 5, shared)

### G12 — KEDA ScaledObject for `earnings-worker` (§3.3)

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: earnings-worker-scaler
  namespace: processing
spec:
  scaleTargetRef:
    name: earnings-worker
  minReplicaCount: 1      # keeps one worker warm; grace period handles in-flight jobs during scale-down
  maxReplicaCount: 3      # conservative; learner is expensive
  cooldownPeriod: 600     # 10 min
  pollingInterval: 30
  triggers:
    - type: redis
      metadata:
        address: redis.infrastructure.svc.cluster.local:6379
        listName: earnings:pipeline
        listLength: "1"
        databaseIndex: "0"
```

### G13 — Complete env var defaults table (§6) — filled in table above

### G14 — `live_state.json` quarter-label-match check on delete (§3.7)

Daemon reads `quarter_label` from file before deleting; deletes only on match. Prevents destroying a newer quarter's state that legitimately overwrote the prior one.

---

## 12. File / Manifest Implementation Checklist

Implementation order (dependencies first; each step independently deployable):

| # | Action | Path | LOC | Depends on |
|---|---|---|---|---|
| 1 | CREATE | `scripts/shared/__init__.py` | 1 | — |
| 2 | CREATE | `scripts/shared/budget_gate.py` (factor from `extraction_worker.is_over_usage_threshold`) | ~120 | 1 |
| 3 | MODIFY | `scripts/extraction_worker.py` (import shared module; drop local duplicate) | −40 / +5 | 2 |
| 4 | MODIFY | `scripts/earnings/earnings_orchestrator.py` — add MCP override to `_run_learner_via_sdk` + `_run_predictor_via_sdk` (G7); add `prediction/complete.json` write (G4b); add `learning/complete.json` write in both SUCCEEDED + RECOVERED paths (G4); add optional `--mode {historical,live}` plumbing for run-ledger/observability only | ~80 | — |
| 5 | CREATE | `scripts/earnings_trigger_daemon.py` (new daemon, mirrors `guidance_trigger_daemon.py` + earnings-specific gates/walker) | ~400 | 2, 4 |
| 6 | CREATE | `scripts/earnings_worker.py` (new worker: subprocess dispatcher + lease + DLQ + sentinel writes G5/G10) | ~450 | 2, 4 |
| 7 | DELETE | `scripts/earnings_trigger.py` (legacy naive listener; no shared code with new daemon) | −139 | 5, 6 |
| 8 | MODIFY | `scripts/earnings/run_ledger.py` — add nullable `mode` field to `open_run`/`close_run` + Obsidian renderer column (`guidance` may leave it null; `prediction`/`learning` set it from the orchestrator's `--mode` arg, which is sourced from worker payload) | +40 | — |
| 9 | CREATE | `k8s/processing/earnings-trigger.yaml` (Deployment) | ~70 | 5 |
| 10 | CREATE | `k8s/processing/earnings-worker.yaml` (Deployment + KEDA ScaledObject; G6/G12 specs) | ~170 | 6 |
| 11 | UPDATE | This plan file → mark all Opens resolved | — | all |

**Net**: 4 new modules, 2 K8s manifests, 3 modified files, 1 deleted, ~1,300 lines net new code. Zero changes to:

- `earnings-prediction` / `earnings-learner` SKILL.md
- `prediction_result.v1` / `attribution_result.v2` validators
- `earnings_orchestrator.py` core flow (only adds sentinel writes + MCP override)
- Guidance pipeline behavior (only factors out the shared budget module)

### Implementation ordering (safe rollout)

1. **Steps 1-3 first**: shared budget gate lands on main; extraction-worker rollout verifies no regression.
2. **Step 4**: orchestrator sentinel writes + MCP override. Safe because the orchestrator's CLI is idempotent; sentinels are additive; MCP override is only active when env var is set.
3. **Steps 5-6 in parallel**: daemon and worker code development. They talk via Redis only, so either can be tested in isolation.
4. **Step 7**: delete old `earnings_trigger.py` only after 5-6 are merged.
5. **Steps 8-10**: observability + K8s manifests. Apply the two K8s manifests with `replicas: 0` first; verify they deploy cleanly; then scale up.
6. **Step 11**: mark plan implementation-complete.

### Verification runbook (mirrors guidance §2)

```bash
# A. Dry run (no enqueue)
python3 scripts/earnings_trigger_daemon.py --list

# B. Single sweep, specific tickers
python3 scripts/earnings_trigger_daemon.py --once --ticker AVGO NVDA

# C. Queue inspection
redis-cli -h 192.168.40.72 -p 31379 LLEN earnings:pipeline
redis-cli -h 192.168.40.72 -p 31379 KEYS "earnings_lease:*"

# D. Idempotency (re-run should enqueue 0)
python3 scripts/earnings_trigger_daemon.py --once --ticker AVGO

# E. Deploy
kubectl apply -f k8s/processing/earnings-trigger.yaml
kubectl apply -f k8s/processing/earnings-worker.yaml
kubectl set env deployment/earnings-trigger -n processing EARNINGS_AUTOMATION_ENABLED=true
kubectl set env deployment/earnings-worker  -n processing EARNINGS_AUTOMATION_ENABLED=true

# F. Enable historical backfill (after catch-up has drained)
kubectl set env deployment/earnings-trigger -n processing HISTORICAL_BACKFILL_ENABLED=true

# G. Monitor
kubectl logs -f -l app=earnings-trigger -n processing
kubectl logs -f -l app=earnings-worker  -n processing

# H. DLQ inspection
redis-cli -h 192.168.40.72 -p 31379 LLEN earnings:pipeline:dead
redis-cli -h 192.168.40.72 -p 31379 LRANGE earnings:pipeline:dead 0 -1

# I. Operator recovery (halted quarter)
rm earnings-analysis/Companies/AVGO/events/Q3_FY2023/learning/failed.json
# Next sweep re-enqueues; log shows the HALTED state has cleared.

# J. Scale-down procedure (pause KEDA first — same dance as guidance)
kubectl annotate scaledobject earnings-worker-scaler -n processing \
    autoscaling.keda.sh/paused-replicas="0" --overwrite
kubectl scale deployment earnings-trigger -n processing --replicas=0
kubectl scale deployment earnings-worker  -n processing --replicas=0

# K. Resume
kubectl annotate scaledobject earnings-worker-scaler -n processing \
    autoscaling.keda.sh/paused-replicas-
kubectl scale deployment earnings-trigger -n processing --replicas=1
kubectl scale deployment earnings-worker  -n processing --replicas=1
```

---

_End of plan. All decisions locked. Implementation-ready._
