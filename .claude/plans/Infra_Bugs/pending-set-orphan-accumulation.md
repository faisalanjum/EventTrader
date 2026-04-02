# Pending Set Orphan Accumulation

**Priority:** Low
**Status:** ⚠️ WORKAROUND APPLIED, NO PERMANENT FIX
**Discovered:** 2026-03-05
**Cleaned:** 2026-03-05 (manual one-time cleanup, 919 news + 327 reports removed)
**Also cleaned:** 2026-03-30 (`reports:pending_returns` ZSET flushed — 28 stale entries blocking chunked-historical chunks)

### Current Status (updated 2026-04-02)
- ✅ **Manual flush applied**: `reports:pending_returns` ZSET and `reports:withoutreturns:*` keys flushed during Mar 2026 backfill.
- ❌ **No permanent code fix**: When live mode resumes, stale `pending_returns` entries from after-hours/weekend filings will accumulate again. The chunk completion check (`run_event_trader.py:342` ZCARD) would block future chunked-historical runs.
- ⚠️ **BLOCKING the 7 targeted gap-fill runs**: Must flush `pending_returns` before AND between each run. Without the permanent fix, any chunk timeout leaves stale entries that block subsequent chunks. See `report-ingestion-gaps.md` for the 7-run plan.
- The `tracking:pending:*` SET accumulation (original bug) also has no permanent fix.

### How to verify / when it recurs
```bash
# Check if pending_returns has stale entries:
kubectl exec -n infrastructure redis-79d9c8d68f-z256d -- redis-cli ZCARD reports:pending_returns
# If > 0 during a chunked-historical run → flush it:
kubectl exec -n infrastructure redis-79d9c8d68f-z256d -- redis-cli DEL reports:pending_returns

# Check tracking:pending sets:
kubectl exec -n infrastructure redis-79d9c8d68f-z256d -- redis-cli SCARD tracking:pending:reports
kubectl exec -n infrastructure redis-79d9c8d68f-z256d -- redis-cli SCARD tracking:pending:news
# If growing unbounded → manual cleanup needed
```

### Permanent fix needed — WRITE BEFORE running targeted backfills or resuming live mode
The chunk completion check at `run_event_trader.py:340-346` should either:
1. Ignore `pending_returns` entries older than N hours (stale from previous live-mode sessions), or
2. Only check `pending_returns` entries that belong to the current chunk's date range, or
3. **Flush `pending_returns` automatically at chunk start in historical mode** ← simplest, recommended

Option 3 implementation (in `run_event_trader.py`, at the start of each chunk in historical mode):
```python
# At chunk start, flush stale pending_returns from previous sessions
if args.historical:
    for source in sources:
        pending_key = RedisKeys.get_returns_keys(source)['pending']
        count = redis_conn.zcard(pending_key)
        if count > 0:
            redis_conn.delete(pending_key)
            logger.info(f"Flushed {count} stale pending_returns entries from {pending_key}")
```

**Why this is safe in historical mode:** Historical chunks process date ranges sequentially. Stale `pending_returns` entries are always from a PREVIOUS session (live mode or crashed chunk). They will never be processed — their `withreturns` data has already expired or been consumed. Flushing at chunk start is equivalent to what we've been doing manually.

## What Happens

The `tracking:pending:news` and `tracking:pending:reports` Redis sets accumulate stale members over time that are never automatically removed.

### Root Cause

`redisDB/redisClasses.py` lines 490-497 manage the pending set lifecycle:

1. **Add to pending:** When `ingested_at` is written to a tracking hash, the key is added to `tracking:pending:{source_type}` via `sadd` (line 493)
2. **Remove from pending:** When `inserted_into_neo4j_at`, `filtered_at`, or `failed_at` is written, the key is removed via `srem` (line 497) — but only if `feature_flags.REMOVE_FROM_PENDING_SET` is `True` (it is, line 251 of `config/feature_flags.py`)

The race condition:

- Tracking hash keys (`tracking:meta:news:*`, `tracking:meta:reports:*`) have a TTL (typically 2 days)
- If the tracking hash expires before the Neo4j insertion step writes `inserted_into_neo4j_at`, the `srem` never fires
- The pending set itself has **no TTL**, so orphan members accumulate indefinitely
- This happens during process restarts, slow Neo4j batches, or when items take longer than the TTL to fully process

### Impact

**None.** The pending sets are observability-only — no processing logic reads them to make decisions. The actual data (news/reports) is correctly in Neo4j. The orphans are just stale references to expired tracking keys.

### Evidence (2026-03-05 audit)

```
tracking:pending:news:  919 total -> 823 orphans (key expired) + 96 confirmed in Neo4j + 0 missing
tracking:pending:reports: 327 total -> 327 orphans (key expired) + 0 alive + 0 missing
```

Zero items were actually missing from Neo4j. All 1,246 were stale.

### Manual Cleanup (safe, idempotent)

```python
import redis
r = redis.Redis(host='192.168.40.73', port=31379, decode_responses=True)

for pending_set in ['tracking:pending:news', 'tracking:pending:reports']:
    members = r.smembers(pending_set)
    # Remove orphans (tracking key expired) and confirmed (already in Neo4j)
    orphans = [m for m in members if not r.exists(m)]
    confirmed = [m for m in members if r.exists(m) and r.hget(m, 'inserted_into_neo4j_at')]
    to_remove = orphans + confirmed
    if to_remove:
        r.srem(pending_set, *to_remove)
```

### Possible Fixes (if ever prioritized)

1. **Periodic sweep:** Add cleanup to watchdog or cron — remove pending members whose tracking key no longer exists
2. **TTL on pending set:** Set `EXPIRE` on `tracking:pending:*` to match tracking key TTL (2 days)
3. **Atomic pipeline:** Ensure `srem` runs in the same pipeline as Neo4j insertion, before the tracking key can expire
