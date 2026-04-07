# Pending Set Orphan Accumulation

## Conclusion

The chunk timeout bug is real, but the exact cause is slightly different from "the old live `ReturnsProcessor` died, so its entries can never be removed."

The exact cause is:

1. Historical chunk completion checks `ZCARD reports:pending_returns` and requires it to be zero.
2. `reports:pending_returns` is a single global set for the whole source, not scoped by live vs historical and not scoped by chunk.
3. Both live and historical processing write into that same global pending set and the same global `reports:withoutreturns:*` / `reports:withreturns:*` namespaces.
4. Shutdown preserves those keys across runs.
5. The `ReturnsProcessor` only drains pending entries whose score is `<= now`.
6. Therefore any unrelated pending live item that is still scheduled for the future keeps `ZCARD > 0`, so the historical chunk monitor waits even when the current chunk is otherwise done.

That is the direct bug.

The "orphan accumulation" part is still true in the sense that old pending state survives across runs and piles up, but the hard blocker is not "no processor exists anymore." The blocker is "the monitor is counting a global mixed-mode pending set, while the worker only consumes due items."

## Code Proof

### 1. The monitor blocks on raw `ZCARD`, not due items and not chunk-local items

In `scripts/run_event_trader.py:339-345`:

- it reads `pending_key = RedisKeys.get_returns_keys(source)['pending']`
- that resolves to `reports:pending_returns`
- it calls `zcard(...)`
- if the count is non-zero, the chunk is marked incomplete immediately

Relevant lines:

- `scripts/run_event_trader.py:339-345`
- `redisDB/redis_constants.py:43-49`

### 2. The pending set is global for the source

`RedisKeys.get_returns_keys(source_type)` returns:

- `pending: f"{source_type}:pending_returns"`
- `withreturns: f"{source_type}:withreturns"`
- `withoutreturns: f"{source_type}:withoutreturns"`

There is no `live` or `hist` prefix in those return-stage keys.

Relevant lines:

- `redisDB/redis_constants.py:43-49`

### 3. Historical processing writes into the same global return-stage keys

In historical mode, `_process_hist_news()`:

- scans `reports:hist:processed:*`
- schedules pending returns through `_schedule_pending_returns(...)`
- writes output to `reports:withreturns:{id}` or `reports:withoutreturns:{id}`

So historical items leave the `hist:` namespace before the completion loop checks return-stage keys.

Relevant lines:

- `eventReturns/ReturnsProcessor.py:148-245`
- especially `eventReturns/ReturnsProcessor.py:203-218`

### 4. Scheduling uses timestamps, and pending items are only processed when due

`_schedule_pending_returns()` stores each member in the ZSET with score:

- `scheduled_return_time + polygon_subscription_delay`

`_process_pending_returns()` only fetches:

- `zrangebyscore(self.pending_zset, 0, current_time)`

So future-dated members stay in the set by design.

Relevant lines:

- `eventReturns/ReturnsProcessor.py:716-742`
- `eventReturns/ReturnsProcessor.py:750-776`

### 5. A new historical run does start a `ReturnsProcessor`

So the statement "entries are never removed because that live session's `ReturnsProcessor` is gone" is not fully correct.

In historical runs, `ReportsManager.start()` still starts:

- `processor_thread`
- `returns_thread`
- `historical_thread`

Relevant lines:

- `config/DataManagerCentral.py:280-296`

What this means:

- old entries that are already due can be drained by the new historical `ReturnsProcessor`
- old entries that are not due yet remain in `reports:pending_returns`
- the monitor still blocks on them because it only uses raw `ZCARD`

### 6. Shutdown preserves pending/withreturns/withoutreturns across runs

`ReportsManager.stop()` calls:

- `self.redis.clear(preserve_processed=True)`

`EventTraderRedis.clear()` delegates to each prefixed client.

`RedisClient.clear(preserve_processed=True)` only deletes:

- `"{prefix}raw:*"`

It does not delete:

- `reports:pending_returns`
- `reports:withreturns:*`
- `reports:withoutreturns:*`

Relevant lines:

- `config/DataManagerCentral.py:363-389`
- `redisDB/redisClasses.py:100-104`
- `redisDB/redisClasses.py:350-360`

## Empirical Proof

I ran a small isolated reproduction against the real class methods with fake Redis plumbing.

### Reproduction setup

State:

- fetch-complete flag is set for the historical chunk
- raw queue is empty
- no `reports:hist:raw:*` or `reports:hist:processed:*` keys exist
- one unrelated future pending item exists in `reports:pending_returns`
- matching `reports:withoutreturns:*` exists

### Output

```text
SCENARIO_A_MONITOR_COMPLETE False
SCENARIO_A_PENDING_ZCARD 1
SCENARIO_A_PROCESSED_CALLS []
SCENARIO_A_PENDING_AFTER_PROCESS 1
SCENARIO_B_PROCESSED_CALLS [('reports:withoutreturns:LIVEACC.2026-04-01T16.05.00-04.00', 'daily')]
SCENARIO_B_PENDING_AFTER_PROCESS 0
SCENARIO_C_KEYS_AFTER_CLEAR ['reports:pending_returns', 'reports:pending_returns_shadow', 'reports:withoutreturns:ACC', 'reports:withoutreturns:LIVEACC.2026-04-01T16.05.00-04.00', 'reports:withreturns:ACC']
```

### What that proves

`SCENARIO_A` proves:

- the historical chunk monitor reports incomplete solely because `reports:pending_returns` has one member
- the real `_process_pending_returns()` does not touch that member when its score is in the future

`SCENARIO_B` proves:

- once that same old member becomes due, a newly started `ReturnsProcessor` can process and remove it
- so the exact problem is not "the old live processor is gone, therefore the entry is inherently unremovable"

`SCENARIO_C` proves:

- shutdown-style cleanup leaves `reports:pending_returns`, `reports:withreturns:*`, and `reports:withoutreturns:*` behind
- so old mixed-mode pending state accumulates across runs

## Exact Root Cause Statement

The chunk completion loop is using a global, cross-run, cross-mode `reports:pending_returns` cardinality check as if it represented "pending work belonging to this historical chunk."

That assumption is false.

`reports:pending_returns` contains:

- live items
- historical items
- items from earlier runs
- items whose scheduled return time is still in the future

Because the monitor checks `ZCARD` instead of "due items for this chunk" or "items created by this run," historical chunks can block for hours on unrelated future-scheduled entries that survived shutdown.

That is the exact reason the bug happens.

## What This Means For The Proposed Fixes

### Option 1: flush at chunk start

This works because it removes cross-run contamination from the global pending set before the historical monitor starts using it.

It is a blunt fix, but it directly addresses the proven failure mode.

### Option 2: age-based cleanup

This can also work, but only if you are comfortable using timestamp age as a proxy for "not part of this run."

It is more surgical, but it is not the core semantic fix.

### Option 3: scope by chunk/run identity

This is the most correct design, because the real bug is lack of scope.

The completion check should be based on work created by the current chunk, not on a global source-wide pending set.

## Final Verdict

With 100% confidence from the code and the reproduction:

- yes, stale pending state survives across runs
- yes, that accumulation is part of the problem
- but the exact bug is broader and more precise:

The historical completion loop waits on a global `pending_returns` count, while the returns worker only drains entries that are already due, so unrelated future-scheduled live entries can keep every historical chunk stuck until timeout.
