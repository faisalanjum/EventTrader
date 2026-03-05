# Pending Set Orphan Accumulation

**Priority:** Low
**Status:** Documented (not blocking anything)
**Discovered:** 2026-03-05
**Cleaned:** 2026-03-05 (manual one-time cleanup, 919 news + 327 reports removed)

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
