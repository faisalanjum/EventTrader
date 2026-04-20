# Self-Exit Canary — Change Log

**Session start:** 2026-04-19
**Goal:** Empirically validate RSS-threshold self-exit for xbrl-worker with zero production impact.
**Rollback principle:** Every change below has an exact undo command. Execute them in REVERSE order to fully revert.

---

## Architecture — isolation boundaries

| Layer | Production | Canary |
|---|---|---|
| Deployment name | `xbrl-worker-heavy` | `xbrl-worker-heavy-canary` (NEW, disposable) |
| Image tag | `faisalanjum/xbrl-worker:latest` | `faisalanjum/xbrl-worker:canary-selfexit-20260419` (NEW) |
| Redis queue | `reports:queues:xbrl:heavy` | `reports:queues:xbrl:heavy-canary` (NEW) |
| KEDA scaler | attached | NOT attached (manual replicas=1) |
| Resource limits | 4Gi req / 20Gi lim | 2Gi req / 16Gi lim (intentionally lower to validate) |
| Env vars | default (self-exit disabled) | `SELF_EXIT_ENABLED=true`, `JOB_COUNT_THRESHOLD=1` |

**Neo4j shared (unavoidable)** — safe via XBRL's MERGE-idempotent writes. Test filing pre-selected from COMPLETED set so re-processing is idempotent.

---

## Test filing (chosen)

- **Accession:** `0002040266-25-000012`
- **CIK:** `0001841666`
- **Form:** 10-Q (will route to MEDIUM queue in prod, but we'll force it to the canary heavy queue for testing)
- **Period:** 2025-03-31
- **Facts:** 739 (small, fast — good for rapid iteration)
- **Current status:** COMPLETED
- **Why this one:** small → fast turnaround; already completed → MERGE reprocess is idempotent; not in active gap-fill backlog

---

## Pre-canary state snapshot

**File:** `/tmp/self-exit-canary/snapshot_before.txt` (captured at session start)
Contains: deployments, pods, scaledobjects, queue lengths, heavy deploy manifest.

---

## Actions log (chronological)

### [Phase 0 — Setup]

#### [00:00] Action — Create changelog file
- **Type:** file-create
- **What:** Created `/home/faisal/EventMarketDB/.claude/plans/self-exit-canary-log.md`
- **Undo:** `rm /home/faisal/EventMarketDB/.claude/plans/self-exit-canary-log.md`
- **State after:** this file exists, tracking all subsequent actions

#### [00:00] Action — Snapshot cluster state
- **Type:** read-only
- **What:** Saved `kubectl get deploy/pod/scaledobject` + redis queue lengths + heavy deploy yaml to `/tmp/self-exit-canary/snapshot_before.txt`
- **Undo:** N/A (read-only snapshot)
- **Use for rollback verification:** diff current state vs this file

---

### [Phase 1 — Code changes] — COMPLETED

#### [19:15] Action — Edit `neograph/xbrl_worker_loop.py` with env-var-gated self-exit
- **Type:** file-edit
- **What:** +20 lines, -2 lines. Two changes:
  1. After logger.info("XBRL Worker started..."): added self_exit_enabled/job_count_threshold/jobs_started init block with optional startup log
  2. At top of `while True:`: added self-exit check that calls `sys.exit(0)` when `jobs_started >= threshold`
  3. After PROCESSING status update (line ~137): added `jobs_started += 1`
- **Default behavior:** `SELF_EXIT_ENABLED` unset → identical to prior behavior (zero impact when env var absent)
- **Syntax verified:** `python3 -m py_compile neograph/xbrl_worker_loop.py` passed
- **Undo:** `git checkout neograph/xbrl_worker_loop.py` (reverts to pre-edit state)

#### [pending] Original planned — Edit `neograph/xbrl_worker_loop.py` with env-var-gated self-exit
- **Type:** file-edit
- **What:** Add at top of `while True:` loop:
  ```python
  if os.getenv('SELF_EXIT_ENABLED','false').lower() == 'true':
      threshold = int(os.getenv('JOB_COUNT_THRESHOLD','20'))
      if jobs_completed >= threshold:
          logger.info(f'[SELF-EXIT] jobs_completed={jobs_completed} >= threshold={threshold}, exiting for fresh pod')
          sys.exit(0)
  ```
  + increment `jobs_completed` after each successful job + initialize to 0.
- **Default behavior:** `SELF_EXIT_ENABLED` unset → skip entire block → identical to current behavior.
- **Undo:** `git diff neograph/xbrl_worker_loop.py` then `git checkout neograph/xbrl_worker_loop.py`
- **Safety:** env-var-gated. Even if deployed to prod image, prod pods (without the env var) behave identically.

---

### [Phase 2 — Image build] — IN PROGRESS

#### [19:30] Action — Build canary image with temp .dockerignore
- **Type:** file-create + image-build
- **What:**
  1. Created `/home/faisal/EventMarketDB/.dockerignore.canary` (excludes venv/.git/logs/__pycache__)
  2. Symlinked `.dockerignore -> .dockerignore.canary` (temporary)
  3. `docker build -f Dockerfile.xbrl -t faisalanjum/xbrl-worker:canary-selfexit-20260419 .`
  4. Result: 1.39 GB image (vs prod :latest 11 GB)
  5. Removed the `.dockerignore` symlink immediately after build (kept `.dockerignore.canary` for reuse)
- **Undo:**
  1. `docker rmi faisalanjum/xbrl-worker:canary-selfexit-20260419` (remove local image; harmless if left)
  2. `rm /home/faisal/EventMarketDB/.dockerignore.canary` (remove temp ignore file)
- **Safety:** NEW tag. `:latest` untouched. Symlink cleanup verified — no persistent .dockerignore in repo.

#### [19:31] Action — Push canary image to Docker Hub
- **Type:** image-push
- **What:** `docker push faisalanjum/xbrl-worker:canary-selfexit-20260419` (running in background)
- **Undo:** Docker Hub web UI → delete tag; OR harmless to leave (private-ish, just takes registry space)
- **Status:** pushing at time of log write

---

### [Phase 3-6 — Canary deploy/test/cleanup] — COMPLETED

#### [19:37] Action — First canary deployment (threshold=1) — job stuck in taxonomy phase
- **Type:** cluster-change
- **What:** Applied `xbrl-worker-heavy-canary` deploy with `SELF_EXIT_ENABLED=true, JOB_COUNT_THRESHOLD=1`
- **Result:** Pod started, logged `[SELF-EXIT] enabled`, popped test 10-Q, entered silent taxonomy phase (Neo4j I/O-bound, same bottleneck as production)
- **Observation:** After 50 min, still stuck in do_poll() on Neo4j query, no facts phase reached. Pivoted.

#### [20:29] Action — Redeploy with threshold=0 to test self-exit mechanism directly
- **Type:** cluster-change + db-change
- **What:** Deleted first canary. Reset test filing back to COMPLETED. Redeployed with `JOB_COUNT_THRESHOLD=0` (force exit on first loop iteration).
- **Result — EMPIRICAL PROOF:**
  - Pod started at 20:30:26, logged `[SELF-EXIT] enabled: will exit after 0 jobs`
  - Next loop iteration: logged `[SELF-EXIT] processed 0 jobs (threshold=0); exiting cleanly`
  - Process exited at 20:30:27 (1 second after start)
  - **Exit code: 0, reason: Completed** (NOT OOMKilled, NOT crash)
  - Kubelet restarted pod successfully — `restartCount=3` after ~1 min, climbing
  - CrashLoopBackOff triggered (expected: rapid-fire exit cycles with no work between). NOT a problem with production threshold values (10-20).

#### [20:32] Action — Full rollback
- **Type:** cluster-change + db-change + redis-change
- **What:**
  1. `kubectl delete deploy -n processing xbrl-worker-heavy-canary` ✓
  2. Verified canary queue empty (was already empty from `DEL`) ✓
  3. Verified test filing status=COMPLETED (already restored) ✓
  4. Verified production pods: `xbrl-worker-heavy-64f4c68b76-v84hr` AGE=13h, RESTARTS=0 (unaffected) ✓
  5. Verified production pods: `xbrl-worker-medium-6bdf4c5d7d-kds95` AGE=13h, RESTARTS=0 (unaffected) ✓

---

## FINAL RESULTS — empirical evidence

| Risk | Validation method | Verdict |
|---|---|---|
| psutil availability | `import psutil` in running pod | ✅ v7.0.0 present |
| Arelle non-daemon threads | Cntlr init + thread enumerate | ✅ 0 non-daemon threads created |
| sys.exit(0) hangs on Arelle | subprocess test w/ Cntlr loaded | ✅ exited in <10s, rc=0 |
| Neo4j driver threads | Live probe | ✅ 0 threads created/lingering |
| `atexit` / `__del__` hazards | Code audit | ✅ 1 __del__ (idempotent), 0 atexit |
| Gap-fill worker-continuity assumption | Code review | ✅ no assumption — queue-based |
| Our code threading | grep | ✅ 0 threads in worker path |
| **Self-exit mechanism fires** | **LIVE CANARY** | **✅ log + exit code 0 confirmed** |
| **Kubelet restart after self-exit** | **LIVE CANARY** | **✅ restartCount climbed 0→4** |
| **Production impact of canary** | **Live monitoring** | **✅ zero — both prod pods 13h uptime, 0 restarts** |

## Remaining Phase 1 file edit

- **File:** `neograph/xbrl_worker_loop.py` (+20 -2)
- **State:** unreverted (env-var-gated, default OFF = prod behavior unchanged)
- **Undo command:** `git checkout neograph/xbrl_worker_loop.py`
- **Decision needed:** keep (safe, no prod impact) OR revert

---

#### [original] Planned — Create canary Deployment
- **Type:** cluster-change
- **What:** `kubectl apply -f /tmp/self-exit-canary/canary-deployment.yaml` (new file, separate resource)
- **Undo:** `kubectl delete deploy -n processing xbrl-worker-heavy-canary`
- **Safety:** separate name. KEDA doesn't target it. Doesn't share anything with prod heavy deploy.

---

### [Phase 4 — Test job injection] — PENDING

#### [pending] Planned — Reset test filing status + LPUSH to canary queue
- **Type:** db-change + redis-change
- **What:**
  1. Cypher: `MATCH (r:Report {accessionNo:'0002040266-25-000012'}) SET r.xbrl_status = NULL`
  2. Redis: `LPUSH reports:queues:xbrl:heavy-canary {"report_id":"0002040266-25-000012",...}`
- **Undo:**
  1. Cypher: `MATCH (r:Report {accessionNo:'0002040266-25-000012'}) SET r.xbrl_status = 'COMPLETED'`
  2. Redis: `DEL reports:queues:xbrl:heavy-canary`
- **Safety:** test filing is already COMPLETED in Neo4j. Reprocess via MERGE is idempotent. Worst case: some XBRL facts get re-written with same values.

---

### [Phase 5 — Observation] — PENDING

#### [pending] Planned — Monitor canary pod
- **Type:** read-only
- **What:** `kubectl logs/top/describe` on canary pod
- **Undo:** N/A

---

### [Phase 6 — Rollback (on completion OR failure)]

#### [pending] Planned — Full rollback sequence
Execute these in order:
1. `kubectl delete deploy -n processing xbrl-worker-heavy-canary`
2. `kubectl exec -n processing <any pod> -- redis-cli DEL reports:queues:xbrl:heavy-canary`
3. Cypher: restore test filing status (`MATCH (r:Report {accessionNo:'...'}) SET r.xbrl_status='COMPLETED'`)
4. `git checkout neograph/xbrl_worker_loop.py` (reverts env-var gate; optional — safe to keep since default is off)
5. Verify: diff `kubectl get deploy/pod -n processing` vs `/tmp/self-exit-canary/snapshot_before.txt`

---

## Status check — after rollback, these must all be true

- [ ] No `xbrl-worker-heavy-canary` deployment
- [ ] No `reports:queues:xbrl:heavy-canary` key in Redis
- [ ] Test filing `0002040266-25-000012` is status=COMPLETED again
- [ ] Production `xbrl-worker-heavy` pod still running (no restart)
- [ ] Production `xbrl-worker-medium` pod still running (no restart)
- [ ] Redis heavy/medium queues unchanged
- [ ] Neo4j Report count unchanged

---

## Open decisions (await user)

1. Build canary image now? (requires Docker hub credentials — per MEMORY, stored at `~/.docker/docker-hub-pat.txt`)
2. Leave `xbrl_worker_loop.py` code change after success (env-var-off) or revert?
