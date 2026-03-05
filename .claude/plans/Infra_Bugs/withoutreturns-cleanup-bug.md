# BUG: `withoutreturns` keys never deleted after Neo4j insertion

**Discovered**: 2026-03-04
**Status**: OPEN
**Severity**: Medium — blocks chunk completion monitor, prevents batch embeddings from running

---

## Symptom

Historical backfill process (`run_event_trader.py -historical`) gets stuck in infinite chunk completion loop:

```
Chunk processing not yet complete. Status: {'news': 'WithoutReturns Namespace Not Empty', 'transcripts': 'Complete'}. Waiting 60s...
```

The process loops forever at `run_event_trader.py:358` because it scans for `*:withoutreturns:*` keys and refuses to advance if any exist.

## Root Cause

`neograph/mixins/news.py:108` — cleanup only deletes `withreturns` keys after successful Neo4j insertion:

```python
if success and namespace == RedisKeys.SUFFIX_WITHRETURNS:
    self.hist_client.client.delete(key)
```

There is **no equivalent cleanup for `withoutreturns` keys**. The data gets successfully written to Neo4j (confirmed in logs — processed twice via batch + PubSub), but the Redis key is orphaned.

Same bug likely exists in `neograph/mixins/transcript.py` — need to verify.

## Stuck Item (2026-03-04)

- **Key**: `news:withoutreturns:50599726.2026-02-12T22.23.12+00.00`
- **Ticker**: PX (P10 Inc.) — all returns `null` because Polygon has no price data for this ticker
- **Neo4j**: Successfully inserted as `bzNews_50599726` (log confirms twice)
- **Resolution**: Manually deleted the key via `redis-cli DEL` to unblock

## Impact

- Blocks the chunk completion monitor → post-chunk batch embedding step never fires
- On this occasion, 87,117 QAExchange embeddings were delayed until manual intervention
- Any future `withoutreturns` item will cause the same infinite loop

## Files to Fix

1. `neograph/mixins/news.py:108` — add `withoutreturns` key deletion after successful Neo4j insert
2. `neograph/mixins/transcript.py` — verify same pattern, fix if present
3. Consider: should `run_event_trader.py:358` chunk monitor treat `withoutreturns` differently? (e.g., skip if already in Neo4j)

## Important Nuance

Not all `withoutreturns` keys are bugs. Most are **legitimately waiting** — returns can't be calculated until the next trading day's close price is available from Polygon. On a typical earnings night, dozens of keys sit in `withoutreturns` overnight and get processed the next day. This is normal.

The actual bug is the **permanently stuck** case: tickers where Polygon has no price data at all (e.g., PX/P10 Inc.), so returns can never be calculated and the key lives forever. The fix needs to distinguish between "waiting for tomorrow's prices" and "will never get prices."

## Suggested Fix Direction

The naive `if success:` delete-all approach is too aggressive — it would delete keys that are legitimately waiting for returns. The fix likely needs some kind of staleness/age check or retry limit, but the exact approach should be determined by whoever implements it.
