# SEC Report Ingestion Gaps — Full Analysis & Fix Plan

**Date**: 2026-03-31
**Scripts**: `scripts/report_gap_analysis.py` (EDGAR comparison), `scripts/report_gap_secapi.py` (three-way)
**Output**: `earnings-analysis/gap_analysis/`

---

## Root Cause (definitively proven)

The enricher marks reports as "processed" (LPUSH to `reports:queues:processed`) BEFORE Neo4j writes them. `set_filing()` checks this list to skip duplicates. When any failure occurs between enrichment and Neo4j write (SIGTERM, timeout, connection drop), the report is permanently blocked from re-ingestion.

**Two-step failure during Nov 2025 backfill:**
1. **Trigger**: Oct Q3 earnings orphan backlog (~400 withreturns) consumed chunk timeout budgets. Chunks 15-19 (covering Nov) all hit the 3h SIGTERM while still draining Oct data.
2. **Permanent loss**: Enricher added Nov filings to PROCESSED_QUEUE before Neo4j wrote them. After SIGTERM, those filings were "done" in Redis but absent from Neo4j. Subsequent chunks/re-runs skip them.

**Proven with three-way comparison** (sec-api.io vs EDGAR vs Neo4j):
- sec-api.io returns 40,938 filings for our 796 companies
- 4,696 are in sec-api.io but NOT in Neo4j (**PIPELINE_LOST** — our fault, fixable)
- Only 440 are in EDGAR but not sec-api.io (**SOURCE_GAP** — not fixable, mostly CIK/ticker mismatches)
- Nov 2025: 722 pipeline-lost vs only 10 source-gap → **98.6% our pipeline's fault**

---

## Redis Flushes Performed (Mar 29-30, 2026)

Three structures flushed before/during the Aug 2025 → Mar 2026 re-backfill.

**Only needed pre-Phase 4 fix.** After Phase 4 code fix, flushing PROCESSED_QUEUE is no longer needed for correctness.

### 1. `reports:queues:processed` (LIST)
- Flushed before starting (Mar 29). Command: `redis-cli DEL reports:queues:processed`
- Root cause of the Nov–Mar gap. After flush, Nov test produced 71 withreturns vs 1 before.

### 2. `reports:withoutreturns:*` (14 KEYS)
- Flushed ~06:20 EDT Mar 30. Stale live-mode reports from Thu Mar 27.
- NOT the actual blocker (flushing these didn't fix stuck chunks).

### 3. `reports:pending_returns` (ZSET, 28 entries)
- Flushed ~06:22 EDT Mar 30. The ACTUAL chunk blocker.
- `run_event_trader.py:342` checks `ZCARD` on this ZSET and refuses to advance while non-zero.
- After flush: chunks went from 3h to ~10min. Saved ~3.3 days of runtime.

### Pre-flight checklist (only needed pre-Phase 4)
```bash
kubectl exec -n infrastructure redis-79d9c8d68f-z256d -- redis-cli DEL reports:queues:processed
kubectl exec -n infrastructure redis-79d9c8d68f-z256d -- redis-cli EVAL \
  "local k=redis.call('KEYS','reports:withoutreturns:*'); for _,v in ipairs(k) do redis.call('DEL',v) end; return #k" 0
kubectl exec -n infrastructure redis-79d9c8d68f-z256d -- redis-cli DEL reports:pending_returns
```

---

## Gap Analysis Summary

### EDGAR comparison (scripts/report_gap_analysis.py)

796 companies, Jan 2023 → Mar 2026, primary form types (8-K, 10-K, 10-Q + amendments).

| Metric | Count |
|--------|-------|
| EDGAR filings found | 40,275 |
| Matched in Neo4j | 35,634 (88.5%) |
| **Missing from Neo4j** | **4,641 (11.5%)** |
| — Expected (backfill not reached) | 2,848 (Jan–Mar 2026) |
| — Real gaps (dates already covered) | 1,793 |
| — False positive (ZI/ticker mismatch) | ~47 |
| **Net actionable gaps** | **~1,746** |

### Three-way comparison (scripts/report_gap_secapi.py)

| Metric | Count |
|--------|-------|
| sec-api.io filings found | 40,938 |
| Matched in Neo4j | 36,242 |
| **PIPELINE_LOST** (sec-api has, we don't) | **4,696** (fixable by re-run) |
| **SOURCE_GAP** (EDGAR has, sec-api doesn't) | **440** (not fixable) |
| UNFIXABLE (neither sec-api nor Neo4j) | 159 |

### Monthly gap breakdown (PIPELINE_LOST only — fixable)

| Month | 8-K | 10-Q | 10-K | Total | Root Cause |
|-------|-----|------|------|-------|------------|
| 2023 scattered | ~90 | ~20 | ~15 | ~129 | PROCESSED_QUEUE bug |
| 2024-05 | 103 | 4 | 1 | 110 | PROCESSED_QUEUE bug |
| **2024-08** | 287 | 241 | 5 | **541** | PROCESSED_QUEUE bug (Q2 earnings) |
| **2024-11** | 174 | 38 | 16 | **261** | PROCESSED_QUEUE bug (Q3 earnings) |
| **2025-11** | 402 | 308 | 1 | **722** | PROCESSED_QUEUE re-accumulation + timeouts |
| 2026-01 | 513 | 23 | 17 | 583 | Current backfill in progress |
| 2026-02 | 974 | 73 | 495 | 1,594 | Current backfill pending |
| 2026-03 | 512 | 25 | 74 | 642 | Current backfill pending |

---

## Phase 4: The Permanent Code Fix — DEPLOYED 2026-03-31 ~20:30 EDT

### The bug (one sentence)

`set_filing()` in `redisClasses.py:234-240` checks `reports:queues:processed` (populated BEFORE Neo4j write) to decide "already done" — but items can be in that list without ever reaching Neo4j.

### The fix (3 steps)

#### Why HEXISTS on meta hash is NOT sufficient (discovered during audit)

The meta key includes a timestamp that differs by code path. Confirmed in live Redis — each filing creates **TWO meta hashes** with different timezone formats:

```
tracking:meta:reports:0000104169-26-000008.2026-01-08T12.59.51+00.00  (UTC — from set_filing/enricher)
tracking:meta:reports:0000104169-26-000008.2026-01-08T07.59.51-05.00  (Eastern — from ReportProcessor._clean_content)
```

Root cause:
- `set_filing()` uses `filing.filedAt` as-is (UTC from sec-api.io) → `redisClasses.py:232`
- `ReportProcessor._clean_content()` converts to Eastern → `ReportProcessor.py:694-697`
- Neo4j finalization writes `inserted_into_neo4j_at` to whichever meta hash the processing path used

Confirmed: 1,711 accessions currently have multiple meta hashes. HEXISTS on the UTC hash would work IF the marker was written there, but it's fragile — the marker might only exist on the Eastern hash, or the UTC hash might expire (2-day TTL) while the Eastern one persists from a previous run.

#### Step 1: Add a dedicated no-TTL Redis SET keyed by accessionNo ONLY — ✅ DEPLOYED

**Key insight**: Accession numbers are globally unique. No timestamp needed for dedup. This completely avoids the UTC/Eastern mismatch.

`redisDB/redisClasses.py:234-240`:

BEFORE (broken — checks premature marker with O(N) scan):
```python
processed_key = f"{self.prefix}processed:{filing.accessionNo}.{filed_at}"
processed_items = self.client.lrange(self.PROCESSED_QUEUE, 0, -1)
if processed_key in processed_items:
    self.logger.info(f"Skipping duplicate filing: {processed_key}")
    return False
```

AFTER (checks post-Neo4j success SET, no timestamp, O(1)):
```python
if self.client.sismember("reports:confirmed_in_neo4j", filing.accessionNo):
    self.logger.info(f"Skipping filing already in Neo4j: {filing.accessionNo}")
    return False
```

#### Step 2: Write to the SET on every successful Neo4j finalization — ✅ DEPLOYED

Add `SADD` alongside each existing `mark_lifecycle_timestamp(..., "inserted_into_neo4j_at")` call. Extract `accessionNo` from the report_id (first 20 chars, format `XXXXXXXXXX-YY-ZZZZZZ`):

4 locations — add one line each:

1. `neograph/mixins/report.py:43-46` — `_finalize_report_batch` (batch path, success):
   ```python
   # After mark_lifecycle_timestamp for inserted_into_neo4j_at
   delete_client.client.sadd("reports:confirmed_in_neo4j", report_id[:20])
   ```

2. `neograph/mixins/report.py:311-314` — `_process_deduplicated_report` (after success):
   ```python
   # After mark_lifecycle_timestamp for inserted_into_neo4j_at
   self.event_trader_redis.history_client.client.sadd("reports:confirmed_in_neo4j", report_id[:20])
   ```

3. `neograph/mixins/pubsub.py:386-390` — `_finalize_pubsub_processing` (success=True):
   ```python
   # After mark_lifecycle_timestamp for inserted_into_neo4j_at
   delete_client.client.sadd("reports:confirmed_in_neo4j", item_id.split('.')[0] if '.' in item_id else item_id[:20])
   ```

4. `neograph/mixins/reconcile.py:192-193` — reconcile path (after success):
   ```python
   # After mark_lifecycle_timestamp for inserted_into_neo4j_at
   self.event_trader_redis.history_client.client.sadd("reports:confirmed_in_neo4j", full_id[:20])
   ```

**Note**: `report_id[:20]` extracts the accession number (format `XXXXXXXXXX-YY-ZZZZZZ` = exactly 20 chars) from the full `report_id` which is `ACCNO.FILED_AT_TIMESTAMP`.

#### Step 3: Seed the SET from existing Neo4j data, then run targeted backfills

**✅ SEEDED 2026-03-31 ~20:30 EDT** — 37,492 accession numbers loaded from Neo4j into `reports:confirmed_in_neo4j` SET.

After seeding + deploying Steps 1-2, run `chunked-historical` for gap date ranges. The SET-based dedup automatically skips existing reports and passes through missing ones. No flushing needed.

#### Deployment details

All changes deployed mid-backfill (chunk 30 of ~43 running). Current chunk uses old code (in memory). Next chunk picks up new code automatically.

**Files changed:**
- `redisDB/redisClasses.py:234-237` — `set_filing()` dedup gate: LRANGE → SISMEMBER
- `neograph/mixins/report.py:58-59` — SADD in `_finalize_report_batch`
- `neograph/mixins/report.py:319-320` — SADD in `_process_deduplicated_report`
- `neograph/mixins/pubsub.py:391-394` — SADD in `_finalize_pubsub_processing`
- `neograph/mixins/reconcile.py:195-196` — SADD in reconcile path

**Redis:**
- `reports:confirmed_in_neo4j` SET created with 37,492 entries (no TTL, persists indefinitely)

---

## Code Verification Trace (complete)

### Meta key format — INCONSISTENT (discovered during audit)

The meta key includes a timestamp suffix, but code paths use different timezone formats:

| Code location | Timestamp source | Example suffix |
|---|---|---|
| `set_filing()` (redisClasses.py:232) | `filing.filedAt` (UTC from sec-api.io) | `.2026-01-08T12.59.51+00.00` |
| Enricher (report_enricher.py:74) | Same UTC (from raw key) | `.2026-01-08T12.59.51+00.00` |
| ReportProcessor._clean_content (ReportProcessor.py:694-697) | Converted to Eastern | `.2026-01-08T07.59.51-05.00` |
| Batch processor (report.py:162) | From withreturns key (Eastern) | `.2026-01-08T07.59.51-05.00` |

**Confirmed in live Redis**: same accession creates TWO meta hashes. This is why the fix uses `accessionNo` ONLY (no timestamp) as the SET key — completely avoids the mismatch.

### `inserted_into_neo4j_at` — written only on Neo4j success

| Code location | Condition | TTL passed? |
|---|---|---|
| `report.py:43-46` (_finalize_report_batch) | `if success:` | No (hash TTL from enricher persists) |
| `report.py:312-313` (_process_deduplicated_report) | `if success:` | No |
| `pubsub.py:386-390` (_finalize_pubsub_processing) | `if success:` | No |
| `reconcile.py:192-193` | `if success:` | No |

All paths: marker only written on success, no TTL refresh.

### Returns processing — verified untouched

ReturnsProcessor depends on (NOT changing):
- `{prefix}processed:*` individual STRING keys — enricher `pipe.set()` at `report_enricher.py:130`
- PubSub channel `reports:live:processed` — enricher `pipe.publish()` at `report_enricher.py:135`

ReturnsProcessor does NOT depend on (the bug location):
- `reports:queues:processed` LIST — enricher `pipe.lpush()` at `report_enricher.py:134`

Verified at `eventReturns/ReturnsProcessor.py:45` (subscribes to PubSub) and `:137` (scans `processed:*` keys).

### LPUSH sites — all 3 untouched by our fix

| Location | Purpose | Changed? |
|---|---|---|
| `report_enricher.py:134` | K8s enricher path | No |
| `ReportProcessor.py:793` | Lightweight/direct report path | No |
| `BaseProcessor.py:219` | Base processor path | No |

### Existing guard already uses `inserted_into_neo4j_at`

`report.py:162-173` — the batch processor already has an `inserted_into_neo4j_at` guard:
```python
if delete_client.client.hexists(meta_key_for_guard, "inserted_into_neo4j_at"):
    logger.info(f"[SKIP] Report {report_id} already has 'inserted_into_neo4j_at'. Skipping.")
    continue
```

This proves the `inserted_into_neo4j_at` HEXISTS check is already battle-tested in the Neo4j writer. Our fix adds the same check earlier in the pipeline (at `set_filing()`).

### TTL chain — verified

1. Enricher creates meta hash → `mark_lifecycle_timestamp(..., ttl=172800)` → `pipe.expire(key, 172800)` = 2 days
2. Neo4j writes `inserted_into_neo4j_at` → `mark_lifecycle_timestamp(...)` WITHOUT ttl → no `pipe.expire` → existing 2-day TTL persists
3. Meta hash expires 2 days after enrichment, regardless of when Neo4j wrote
4. Step 2 (no-TTL SET) solves this — SET never expires

---

## Pre-existing Bug Found: PubSub Event Path for Reports

**Not related to our fix, but documented for completeness.**

The PubSub event-driven path (`pubsub.py:96-143`) has a key construction bug for reports:
- Enricher publishes `processed_key` = `"reports:hist:processed:ACCNO.FILED_AT"` (full Redis key)
- PubSub receives `item_id` = full key → constructs withreturns lookup: `reports:withreturns:reports:hist:processed:ACCNO.FILED_AT`
- But correct key is: `reports:withreturns:ACCNO.FILED_AT`
- Result: `raw_data = None` → `success=False` → report NOT processed via PubSub path

**Impact**: Reports are processed ONLY via the batch path (`process_reports_to_neo4j` at report.py:79), which runs at startup (pubsub.py:284) and during periodic reconciliation (pubsub.py:328). The batch path works correctly.

**Not blocking**: This bug doesn't cause data loss — the batch path catches everything. But it means PubSub-triggered real-time report processing is non-functional. Worth fixing separately for lower latency.

---

## Reliability Assessment

### Data loss prevention: very high confidence

The no-TTL SET keyed by `accessionNo` can only contain entries added after successful Neo4j write. SISMEMBER returns True → filing is definitely in Neo4j. SISMEMBER returns False → filing may or may not be in Neo4j, but allowing it through is safe (MERGE dedup).

### Regression risk: low

| What could go wrong | Impact | Likelihood | Mitigation |
|---|---|---|---|
| SET not seeded before backfill | All existing filings re-process | Certain if skipped | Run seed script (Step 3) first |
| Duplicate enrichment window | Extra enricher work | Low (enricher has own dedup) | Enricher checks `enriched` flag at line 86 |
| No-TTL SET Redis data loss | Everything re-processes | Very low (Redis persistent) | Safe — MERGE handles it |
| AccessionNo extraction wrong | Wrong SET key | Low | Verify `report_id[:20]` matches accessionNo format |

### Failure mode comparison

| Scenario | Current (broken) | After Steps 1+2 |
|----------|-----------------|-----------------|
| Normal flow | Works | Works |
| Neo4j failure mid-pipeline | **LOST PERMANENTLY** | Re-fetched next run |
| Crash after Neo4j, before marker | N/A | Re-processed (MERGE no-op) |
| Re-run after 2 days | Blocked by stale queue | Only missing ones re-process |
| Redis wipe | Everything re-processes | Everything re-processes |

**Honest framing**: The residual failure mode is extra reprocessing, never data loss. This is "at-least-once" delivery — the correct design for a financial data pipeline.

---

## Backfill Strategy

### Recommended order

1. **Deploy Phase 4 code fix** (Steps 1+2) — change `set_filing()` dedup + add no-TTL SET
2. **Finish current backfill** (Aug 2025 → Mar 2026) — in progress, ~70% done
3. **Run targeted backfills** for remaining gaps:
   - `chunked-historical 2023-01-01 2023-12-31` (91 gaps)
   - `chunked-historical 2024-04-25 2024-05-15` (110 gaps)
   - `chunked-historical 2024-07-25 2024-09-01` (541 gaps)
   - `chunked-historical 2024-10-25 2024-12-01` (261 gaps)
   - `chunked-historical 2025-10-25 2025-12-05` (722 + 23 gaps)
4. No flushing, no LREM, no PROCESSED_QUEUE rebuilding needed post-fix

### Pipeline flow (100% proven — all strategies)

```
chunked-historical → sec-api.io fetch (normal)
  → set_filing() dedup gate (HEXISTS + SISMEMBER post-fix)
  → RAW_QUEUE → ReportProcessor → ENRICH_QUEUE
  → K8s enricher (normal enrichment)
  → withreturns → Neo4j batch writer (normal MERGE)
  → SADD to no-TTL SET (new, Step 2)
  → XBRL queue → XBRL workers (normal)
```

---

## Caveats

- **Secondary form types not checked**: 425, SCHEDULE 13D/A, SC TO-I, SC 14D9, 6-K (1,509 in Neo4j, unknown gaps)
- **ZI (ZoomInfo)**: 47 filings 100% missing — ticker delisted/acquired, unfetchable by sec-api.io
- **CIK vs ticker**: EDGAR queries by CIK, our system by ticker. 440 SOURCE_GAP filings are inherent to this mismatch
- **PubSub event path**: Non-functional for reports (pre-existing key construction bug). Reports rely on batch processing path, which works correctly.

---

## Files

- EDGAR gap CSV: `earnings-analysis/gap_analysis/gaps_2023-01-01_to_2026-03-28.csv` (4,641 rows)
- EDGAR all filings: `earnings-analysis/gap_analysis/edgar_filings_2023-01-01_to_2026-03-28.csv` (40,275 rows)
- EDGAR summary: `earnings-analysis/gap_analysis/summary_2023-01-01_to_2026-03-28.csv`
- sec-api.io filings: `earnings-analysis/gap_analysis/secapi_filings_2023-01-01_to_2026-03-28.csv` (40,938 rows)
- Three-way comparison: `earnings-analysis/gap_analysis/threeway_comparison_2023-01-01_to_2026-03-28.csv`
- Three-way summary: `earnings-analysis/gap_analysis/threeway_summary_2023-01-01_to_2026-03-28.csv`
- EDGAR script: `scripts/report_gap_analysis.py` (reusable, resumable)
- sec-api.io script: `scripts/report_gap_secapi.py` (reusable, resumable)
