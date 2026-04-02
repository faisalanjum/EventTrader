# Transcript Daily Schedule Refresh — Bug Report & Fix Plan

**Date**: 2026-03-11
**Updated**: 2026-04-02
**Severity**: Critical when present (data loss)
**Status**: PARTIALLY RECONCILED — the original day-transition bug is fixed in the current code on disk; production/runtime verification still pending
**Affected files**: `redisDB/TranscriptProcessor.py`, `config/DataManagerCentral.py`

---

## Verified Facts (2026-04-02)

The following statements are confirmed directly from the current code on disk:

- `TranscriptProcessor._run_transcript_scheduling()` now checks for a New York date transition and calls `_refresh_daily_schedule(today)` when the day changes.
- `last_date` is now advanced only after `_refresh_daily_schedule(today)` returns `True`.
- The scheduler now performs periodic intra-day rescans every 2 hours during the 7AM-5PM ET window.
- `TranscriptsManager.start()` seeds today's transcript schedule at startup and sets `processor.last_date` after successful initialization.
- Therefore, the original headline bug, "the live scheduler only seeded the startup day and never scheduled future days," no longer matches the current code on disk.

What is not yet proven by this document:

- that the currently running live process has already been restarted onto this newer code
- that multi-day production runtime has been observed end-to-end with no missed transcript days
- that every historical finding below still applies unchanged to the latest code

## Historical Background

The notes below were written while auditing an earlier patch snapshot. Treat them as historical analysis unless re-verified against the current runtime and current file contents.

The transcript ingestion pipeline uses a sorted set (`admin:transcripts:schedule`) to schedule fetches
30 minutes after each earnings call's conference time. On startup, `TranscriptsManager._initialize_transcript_schedule()`
(DataManagerCentral.py:421→463) populates this set for "today" only.

A scheduling daemon thread (`TranscriptProcessor._run_transcript_scheduling()`, line 55) runs every ~1 second,
detects date transitions, and processes due items. Before this patch, the thread detected date changes but
**never repopulated the schedule for a new day**. Every transcript in Neo4j came from either:
- Historical backfill runs (`_fetch_historical_data`)
- The one-time startup schedule (good only for the day the process boots)

The process running since March 5 (PID 2343585) went 6+ days without restart — the longest ever. After March 5's
schedule was consumed, no new days were ever scheduled. March 9 (HPE) and March 10 (ABM, CASY, DOMO, KSS, ORCL, UNFI)
were all missed by the live scheduler.

**Correction**: The live scheduler DID work on March 5 — logs show successful live fetches for
KR, RGNX, BJ, CIEN, ALT, KURA, MRVL, COO. The root cause is NOT "live scheduling never worked" —
it is "live scheduling was seeded only for the startup day, then stopped advancing."

A previous bot added a `_refresh_daily_schedule()` method to address the multi-day gap. The current
code on disk now includes that method plus additional guard logic around `last_date` updates.

## Historical Patch Review

The findings below were written against an earlier patch snapshot and have not all been re-verified
against the current code on disk.

---

### Finding 1 — Critical: Failed refresh permanently skips that day

**Location**: TranscriptProcessor.py lines 78-81, 371-372

**Code (current patch)**:
```python
# Lines 78-81
today = now.date()
if self.last_date != today:
    self.last_date = today                      # ← SET BEFORE REFRESH
    self.logger.info(f"Date transition detected: {today}")
    self._refresh_daily_schedule(today)          # ← CAN FAIL SILENTLY

# Lines 371-372 (inside _refresh_daily_schedule)
except Exception as e:
    self.logger.error(f"Error refreshing daily schedule: {e}", exc_info=True)
    # ← exception swallowed, no return value
```

**Failure trace**:
1. Midnight: `self.last_date` = Mar 11, `today` = Mar 12
2. Line 78: `Mar 11 != Mar 12` → True
3. Line 79: `self.last_date = Mar 12` — **advanced before refresh executes**
4. Line 81: `_refresh_daily_schedule(Mar 12)` → API error → exception caught at 371, swallowed
5. Next iteration (~1 second later): `self.last_date == today` (both Mar 12) → **False → skipped**
6. No retry until Mar 13. Entire day of transcripts lost.

**Validation**: Code trace confirms. The `try/except Exception` in `_refresh_daily_schedule` catches all
runtime errors. Even if it somehow propagated to the outer catch (line 89), `last_date` was already
advanced at line 79.

**Fix**: Only advance `last_date` after confirmed success. Make `_refresh_daily_schedule` return bool.

---

### Finding 2 — High: API auth relies on invisible global side effect

**Location**: TranscriptProcessor.py lines 8, 340

**Code (current patch)**:
```python
# Line 8
from earningscall import get_calendar

# Line 340 (inside _refresh_daily_schedule)
calendar_events = get_calendar(today)
```

**The problem**: The `earningscall` library requires `earningscall.api_key` to be set. It does NOT read
the project's `EARNINGS_CALL_API_KEY` env var — it only checks `EARNINGSCALL_API_KEY` or `ECALL_API_KEY`,
neither of which exist in the environment.

**Live proof**:
```
>>> import earningscall
>>> earningscall.api_key
None

>>> import os
>>> 'EARNINGS_CALL_API_KEY' in os.environ
True
>>> 'EARNINGSCALL_API_KEY' in os.environ
False
>>> 'ECALL_API_KEY' in os.environ
False

>>> from earningscall import get_calendar
>>> get_calendar(datetime.date(2026, 3, 11))
InsufficientApiAccessError: "2026-03-11" requires an API Key for access.
```

The ONLY reason `get_calendar()` works today is because `EarningsCallProcessor.__init__`
(EarningsCallTranscripts.py:28) sets `earningscall.api_key = api_key` as a module-level global
side effect. This happens in `TranscriptsManager.__init__` (DataManagerCentral.py:408) before
the scheduling thread starts.

**Risk**: If anyone refactors the init order, removes the `EarningsCallProcessor` construction,
or imports `TranscriptProcessor` independently, `_refresh_daily_schedule` fails silently — and
per Finding 1, that failure is non-retriable for the entire day.

**Fix**: Eliminate the raw `get_calendar()` import. Pass the already-constructed `earnings_call_client`
from `TranscriptsManager` to `TranscriptProcessor`. Use `earnings_call_client.get_earnings_events()`
which explicitly manages its own API key.

---

### Finding 3 — Medium: Scheduling logic duplicated and divergent

**Locations**: DataManagerCentral.py:463 vs TranscriptProcessor.py:330

Two separate methods implement "schedule transcripts for a date":

| Aspect | `_initialize_transcript_schedule` | `_refresh_daily_schedule` |
|---|---|---|
| Location | DataManagerCentral.py:463 | TranscriptProcessor.py:330 |
| Calendar source | `earnings_call_client.get_earnings_events()` | raw `get_calendar()` + inline `.astimezone()` |
| TZ handling | Done by `get_earnings_events()` | Inline conversion |
| Clears old schedule | Yes: `pipe.delete("admin:transcripts:schedule")` (to be replaced with stale prune) | No (preserves retries) |
| Skips already processed | No | Yes: `sismember` check |
| Per-event pub notification | Yes: `pipe.publish(channel, event_key)` | No |
| API key | Explicit via `earnings_call_client` | Implicit global side effect |

**Validation**: We verified both paths produce identical keys and scores (tested with 5 events for
March 11 — all MATCH). But identical outputs today does not prevent divergence tomorrow if either
path is modified independently.

**Fix**: Use a single code path. Pass the existing `earnings_call_client` so both startup and
daily refresh use the same `get_earnings_events()` method.

---

### Finding 4 — Low: Startup double-schedules the same day

**Location**: DataManagerCentral.py:421 + TranscriptProcessor.py:27, 78-81

**Sequence**:
1. `TranscriptsManager.start()` calls `_initialize_transcript_schedule()` — schedules today (line 421)
2. Starts processor thread → starts scheduling thread
3. First scheduling loop iteration: `self.last_date` is `None` (line 27), `today` is current date
4. `None != today` → True → calls `_refresh_daily_schedule(today)` — schedules today again

**Impact**: Functionally harmless because `zadd` is idempotent (same key + same score = no-op).
But wastes one `get_calendar()` API call and one universe scan on startup.

**Fix**: After `_initialize_transcript_schedule()` succeeds, set `self.processor.last_date` to
today so the scheduling thread knows today is already seeded.

---

### Finding 5 — Medium: Late calendar additions missed entirely

**Observed**: 2026-03-11. GRPN is in the universe and on today's `get_calendar()` but was never
scheduled. Zero GRPN keys in Redis (no tracking, no processed, no raw). The schedule was populated
before GRPN appeared on the earningscall API.

**Why it matters**: The earningscall API updates dynamically as companies confirm call times. The
schedule is populated once (at startup or date transition), making it a point-in-time snapshot.
Any event added to the calendar after that snapshot is invisible to the pipeline for the entire day.

There is no automatic recovery path. A manual re-run of historical backfill covering the same
dates would catch missed transcripts, but nothing triggers that automatically.

**Fix**: Add periodic intra-day rescans every 2 hours during the 7AM-5PM ET market window.
`_refresh_daily_schedule` already uses zadd (idempotent) and sismember (skip processed), so
repeated calls are safe. Cost: up to 6 extra `get_calendar()` API calls per day.

---

### Finding 6 — High: Startup scheduling is destructive and ungated

**Location**: DataManagerCentral.py:421, 481

**Code**:
```python
# Line 421 — unconditional, no ENABLE_LIVE_DATA check
self._initialize_transcript_schedule()

# Line 481 — inside _initialize_transcript_schedule()
pipe.delete("admin:transcripts:schedule")  # ← WIPES the shared sorted set
```

**The problem**: `_initialize_transcript_schedule()` runs on EVERY startup regardless of
`ENABLE_LIVE_DATA`. It destructively deletes `admin:transcripts:schedule` before re-seeding.
Meanwhile, the scheduling THREAD already gates on `ENABLE_LIVE_DATA` (TranscriptProcessor.py:57).
This inconsistency means:

1. A historical-only gap-fill run wipes the live schedule as a side effect
2. Any pending retries from the live process are lost
3. The schedule is re-seeded for "today" even though no live thread will process it

**Log proof** — March 11, 00:31:14 (from a separate process, likely a gap-fill run):
```
config.DataManagerCentral - Scheduled CXM_2026-03-11T08.30 - Conference: 2026-03-11 08:30:00 EDT
config.DataManagerCentral - Scheduled CPB_2026-03-11T09.00 - Conference: 2026-03-11 09:00:00 EDT
config.DataManagerCentral - Scheduled PATH_2026-03-11T17.00 - Conference: 2026-03-11 17:00:00 EDT
config.DataManagerCentral - Scheduled 3 transcripts for 2026-03-11
```

This is how today's schedule (CXM, CPB, PATH) was populated — NOT by the live process (which has
old code from March 5), but by an unrelated gap-fill run that destructively overwrote the schedule.
GRPN was absent from the API at 00:31 and was added later.

**Note**: The developer left a comment at line 420 acknowledging the concern:
`# Initialize schedule at startup (Should this be conditional too? Seems safe to run always)`
It is NOT safe to run always.

**Fix**: Two changes:

1. **Gate** `_initialize_transcript_schedule()` behind `ENABLE_LIVE_DATA`. Historical-only runs
   must not touch the live schedule at all.

2. **Replace destructive delete+seed with additive seed + stale pruning.** Remove
   `pipe.delete("admin:transcripts:schedule")` and replace with bounded stale cleanup:
   ```python
   stale_cutoff = int(time.time()) - 48 * 3600
   pipe.zremrangebyscore("admin:transcripts:schedule", 0, stale_cutoff)
   ```
   This preserves today's in-progress retries on mid-day restarts, removes entries older than 48h,
   and uses `zadd` (idempotent) to seed today's events. Combined with the `sismember` skip in
   `_refresh_daily_schedule`, already-processed transcripts are not re-fetched.

   **Why not keep delete+seed**: If the process crashes and restarts mid-day, delete wipes today's
   active retries. Re-seeding from the calendar restores today's events at their original
   conference_time+30min (now in the past, so they'd fire immediately), but any cross-day retries
   still pending are permanently lost. With unbounded retries (see Known Limitations), entries can
   accumulate indefinitely — stale pruning at 48h bounds that growth.

---

## Proposed Fix

### Principle
Pass the existing `earnings_call_client` from `TranscriptsManager` to `TranscriptProcessor`.
Fix `last_date` ordering. Gate startup scheduling to live mode. Add intra-day rescans. Eliminate
the raw `get_calendar()` import. Add defensive `None` defaults and guard. Total: ~30 lines changed.

### Hard Rules

- **Do not change any constructor signatures.**
- **Do not touch `_fetch_and_process_transcript()` in Phase 1.**

### Changes

#### 0. TranscriptProcessor.py — `__init__` (explicit defaults)

Add explicit `None` defaults for the two attributes that `start()` will inject. This prevents
`AttributeError` if any code path reaches `_refresh_daily_schedule` before injection, and follows
Python convention that all instance attributes are declared in `__init__`.

Before (lines 26-31):
```python
        self.ny_tz = pytz.timezone('America/New_York')
        self.last_date = None

        # Scheduling thread control
        self.scheduling_thread = None
        self.scheduling_thread_running = False
```

After:
```python
        self.ny_tz = pytz.timezone('America/New_York')
        self.last_date = None
        self.earnings_call_client = None
        self._last_rescan_hour = None

        # Scheduling thread control
        self.scheduling_thread = None
        self.scheduling_thread_running = False
```

#### 1a. DataManagerCentral.py — `TranscriptsManager.start()` (gate + inject)

**Important**: `time` is already imported in this file (used by `_fetch_historical_data`).
`TranscriptProcessor.__init__` declares `earnings_call_client = None` and `_last_rescan_hour = None`
as defaults; `start()` injects the real values before threads run.

Before (lines 418-461):
```python
def start(self):
    try:
        # Initialize schedule at startup (Should this be conditional too? Seems safe to run always)
        self._initialize_transcript_schedule()

        # Start processor thread (Always needed to process potential live scheduled items)
        self.processor_thread = threading.Thread(
            target=self.processor.process_all_transcripts,
            daemon=True
        )

        # Start returns processor thread (Always needed)
        self.returns_thread = threading.Thread(
            target=self.returns_processor.process_all_returns,
            daemon=True
        )

        threads_to_start = [self.processor_thread, self.returns_thread]

        # --- CONDITIONALLY START HISTORICAL THREAD ---
        if feature_flags.ENABLE_HISTORICAL_DATA:
             self.logger.info("Historical data enabled, starting historical transcript fetch thread.")
             self.historical_thread = threading.Thread(
                 target=self._fetch_historical_data,
                 daemon=True
             )
             threads_to_start.append(self.historical_thread)
        else:
             self.logger.info("Historical data disabled, historical transcript fetch thread will not be started.")
        # ------------------------------------------

        # Start threads
        for thread in threads_to_start:
             thread.start()

        self.logger.info(f"Started transcript processing threads")
        return True

    except Exception as e:
        self.logger.error(f"Error starting {self.source_type}: {e}", exc_info=True)
        return False
```

After:
```python
def start(self):
    try:
        self.processor.earnings_call_client = self.earnings_call_client
        self.processor._last_rescan_hour = None

        if feature_flags.ENABLE_LIVE_DATA:
            if self._initialize_transcript_schedule():
                self.processor.last_date = datetime.now(
                    pytz.timezone('America/New_York')
                ).date()

        self.processor_thread = threading.Thread(
            target=self.processor.process_all_transcripts,
            daemon=True
        )

        self.returns_thread = threading.Thread(
            target=self.returns_processor.process_all_returns,
            daemon=True
        )

        threads_to_start = [self.processor_thread, self.returns_thread]

        if feature_flags.ENABLE_HISTORICAL_DATA:
            self.logger.info("Historical data enabled, starting historical transcript fetch thread.")
            self.historical_thread = threading.Thread(
                target=self._fetch_historical_data,
                daemon=True
            )
            threads_to_start.append(self.historical_thread)
        else:
            self.logger.info("Historical data disabled, historical transcript fetch thread will not be started.")

        for thread in threads_to_start:
            thread.start()

        self.logger.info("Started transcript processing threads")
        return True

    except Exception as e:
        self.logger.error(f"Error starting {self.source_type}: {e}", exc_info=True)
        return False
```

#### 1b. DataManagerCentral.py — `_initialize_transcript_schedule()` (return bool + additive prune)

Before (lines 463-506):
```python
def _initialize_transcript_schedule(self):
    """Schedule transcripts for today"""
    try:
        # Use Eastern timezone consistently
        eastern_tz = pytz.timezone('America/New_York')
        today = datetime.now(eastern_tz).date()

        # Get events (already in Eastern time) and filter to our universe
        events = self.earnings_call_client.get_earnings_events(today)
        universe = set(s.upper() for s in self.redis.get_symbols())
        relevant = [e for e in events if e.symbol.upper() in universe]

        if not relevant:
            return

        # Set up Redis pipeline and clear previous schedule
        pipe = self.redis.live_client.client.pipeline()
        notification_channel = "admin:transcripts:notifications"
        pipe.delete("admin:transcripts:schedule")

        # Schedule each relevant event
        for event in relevant:
            conf_date_eastern = event.conference_date
            process_time = int(conf_date_eastern.timestamp() + 1800)
            event_key = RedisKeys.get_transcript_key_id(event.symbol, conf_date_eastern)
            pipe.zadd("admin:transcripts:schedule", {event_key: process_time})
            self.logger.info(f"Scheduled {event_key} - Conference: {conf_date_eastern.strftime('%Y-%m-%d %H:%M:%S %Z')}, Processing: {datetime.fromtimestamp(process_time, eastern_tz).strftime('%Y-%m-%d %H:%M:%S %Z')}")
            pipe.publish(notification_channel, event_key)

        pipe.execute()
        self.redis.live_client.client.publish(notification_channel, "schedule_updated")

        self.logger.info(f"Scheduled {len(relevant)} transcripts for {today}")
    except Exception as e:
        self.logger.error(f"Error scheduling transcripts: {e}", exc_info=True)
```

After:
```python
def _initialize_transcript_schedule(self):
    """Schedule transcripts for today. Returns True on success, False on failure."""
    try:
        eastern_tz = pytz.timezone('America/New_York')
        today = datetime.now(eastern_tz).date()

        events = self.earnings_call_client.get_earnings_events(today)
        universe = set(s.upper() for s in self.redis.get_symbols())
        relevant = [e for e in events if e.symbol.upper() in universe]

        if not relevant:
            return True

        schedule_key = "admin:transcripts:schedule"
        notification_channel = "admin:transcripts:notifications"
        stale_cutoff = int(time.time()) - 48 * 3600

        pruned = self.redis.live_client.client.zcount(schedule_key, 0, stale_cutoff)
        if pruned:
            self.logger.info(f"Pruning {pruned} stale schedule entries older than 48h")

        pipe = self.redis.live_client.client.pipeline()
        pipe.zremrangebyscore(schedule_key, 0, stale_cutoff)

        for event in relevant:
            conf_date_eastern = event.conference_date
            process_time = int(conf_date_eastern.timestamp() + 1800)
            event_key = RedisKeys.get_transcript_key_id(event.symbol, conf_date_eastern)

            pipe.zadd(schedule_key, {event_key: process_time})
            self.logger.info(
                f"Scheduled {event_key} - Conference: "
                f"{conf_date_eastern.strftime('%Y-%m-%d %H:%M:%S %Z')}, "
                f"Processing: {datetime.fromtimestamp(process_time, eastern_tz).strftime('%Y-%m-%d %H:%M:%S %Z')}"
            )
            pipe.publish(notification_channel, event_key)

        pipe.execute()
        self.redis.live_client.client.publish(notification_channel, "schedule_updated")

        self.logger.info(f"Scheduled {len(relevant)} transcripts for {today}")
        return True

    except Exception as e:
        self.logger.error(f"Error scheduling transcripts: {e}", exc_info=True)
        return False
```

#### 2. TranscriptProcessor.py — scheduling loop (lines 78-81)

Before:
```python
if self.last_date != today:
    self.last_date = today
    self.logger.info(f"Date transition detected: {today}")
    self._refresh_daily_schedule(today)
```

After (fixes Findings 1 + 5, with success gating on all markers):
```python
if self.last_date != today:
    self.logger.info(f"Date transition detected: {today}")
    if self._refresh_daily_schedule(today):
        self.last_date = today
        self._last_rescan_hour = None  # Reset rescan tracker for new day

# Periodic intra-day rescan every 2 hours during market window (7 AM - 5 PM ET)
# Catches late calendar additions (GRPN scenario). zadd is idempotent.
elif (7 <= now.hour <= 17
      and now.hour % 2 == 1  # 7, 9, 11, 13, 15, 17
      and self._last_rescan_hour != now.hour):
    self.logger.info(f"Intra-day calendar rescan at {now.strftime('%H:%M %Z')}")
    if self._refresh_daily_schedule(today):
        self._last_rescan_hour = now.hour
    # If refresh fails, _last_rescan_hour stays unchanged → retries next loop
```

#### 3. TranscriptProcessor.py — `_refresh_daily_schedule()` (lines 330-372)

Before:
```python
from earningscall import get_calendar   # line 8

def _refresh_daily_schedule(self, today):
    try:
        calendar_events = get_calendar(today)
        ...
        for event in relevant:
            conf_date_eastern = event.conference_date.astimezone(self.ny_tz)
            ...
    except Exception as e:
        self.logger.error(...)
```

After:
```python
# Remove line 8: from earningscall import get_calendar

def _refresh_daily_schedule(self, today):
    """Returns True on success, False on failure."""
    if self.earnings_call_client is None:
        self.logger.error("earnings_call_client not injected")
        return False

    try:
        events = self.earnings_call_client.get_earnings_events(today)
        universe = set(s.upper() for s in self.event_trader_redis.get_symbols())
        relevant = [e for e in events if e.symbol.upper() in universe]

        if not relevant:
            self.logger.info(f"No earnings events in universe for {today}")
            return True  # Not a failure — just no events

        scheduled = 0
        pipe = self.live_client.client.pipeline()
        for event in relevant:
            conf_date_eastern = event.conference_date  # Already Eastern from get_earnings_events
            process_time = int(conf_date_eastern.timestamp() + 1800)
            event_key = RedisKeys.get_transcript_key_id(event.symbol, conf_date_eastern)

            if self.live_client.client.sismember(self.processed_set, event_key):
                continue

            pipe.zadd(self.schedule_key, {event_key: process_time})
            scheduled += 1
            self.logger.info(
                f"Scheduled {event_key} - Conference: "
                f"{conf_date_eastern.strftime('%Y-%m-%d %H:%M:%S %Z')}, "
                f"Processing: {datetime.fromtimestamp(process_time, self.ny_tz).strftime('%Y-%m-%d %H:%M:%S %Z')}"
            )

        pipe.execute()
        self.live_client.client.publish(self.notification_channel, "schedule_updated")
        self.logger.info(f"Scheduled {scheduled} transcripts for {today}")
        return True

    except Exception as e:
        self.logger.error(f"Error refreshing daily schedule: {e}", exc_info=True)
        return False
```

#### 4. TranscriptProcessor.py — cleanup imports (line 8)

Remove:
```python
from earningscall import get_calendar
```

The `EarningsCallProcessor` import (line 7) and `EARNINGS_CALL_API_KEY` import (line 9) must
be kept — `_fetch_and_process_transcript` still constructs its own client (see Phase 2).

---

## Phase 2 — Separate Follow-up Commit

### Reuse `earnings_call_client` in `_fetch_and_process_transcript()` (line 202)

**Not bundled with the schedule fix** to keep the patch surface minimal.

Before:
```python
earnings_call_client = EarningsCallProcessor(
    api_key=EARNINGS_CALL_API_KEY,
    redis_client=self.event_trader_redis,
    ttl=self.ttl
)
```

After:
```python
earnings_call_client = self.earnings_call_client
```

This eliminates 783 `get_company()` API calls PER TRANSCRIPT FETCH. The client was already
constructed once at startup. Thread-safe for concurrent fetch access: `rate_limiter` is
Lock-guarded, OpenAI client is thread-safe by design, `Company.get_transcript()` is a
stateless HTTP call (does NOT touch the `_events` lazy cache), `company_dict` is read-only
after init.

Once merged, the `EarningsCallProcessor` import (line 7) and `EARNINGS_CALL_API_KEY` import
(line 9) can also be removed.

| Risk | Reasoning |
|---|---|
| Low | Removes per-fetch construction of 783 API calls; eliminates unsynchronized module-global writes (`earningscall.api_key`) that the current per-fetch construction does |

---

## Validation Checks Performed

### Finding 1 — Code trace
- Traced the scheduling loop (lines 70-91) step by step
- Confirmed `last_date` is set at line 79, before `_refresh_daily_schedule` at line 81
- Confirmed `_refresh_daily_schedule` catches `Exception` at line 371 and does not re-raise
- Confirmed no other mechanism retries the refresh for the same day

### Finding 2 — Live env test
```
earningscall.api_key = None (before EarningsCallProcessor construction)
EARNINGS_CALL_API_KEY in env: True
EARNINGSCALL_API_KEY in env: False
ECALL_API_KEY in env: False
get_calendar() without api_key: InsufficientApiAccessError
get_calendar() with api_key: 45 events (success)
```
- Confirmed the library does NOT auto-detect the project's env var
- Confirmed the side effect chain: `TranscriptsManager.__init__` → `EarningsCallProcessor.__init__` → `earningscall.api_key = api_key`

### Finding 3 — Key format comparison
- Ran both code paths for March 11 events
- Compared keys and scores for 5 events: all MATCH
- Documented the 6 semantic differences between the two implementations (table above)

### Finding 4 — Init sequence trace
- `TranscriptsManager.start()` calls `_initialize_transcript_schedule()` synchronously (line 421)
- Then starts the processor thread (line 424-427)
- `process_all_transcripts()` starts the scheduling daemon thread (line 41)
- First loop: `self.last_date` is `None` → `None != today` → True → double-refresh
- Confirmed zadd idempotency makes this safe but wasteful

### Running process check
- PID 2343585 started March 5 — running OLD code without the fix
- Fix exists as uncommitted working-tree change (modified 2026-03-11 00:34 EDT)
- `git diff HEAD -- redisDB/TranscriptProcessor.py` confirms the patch is local only
- Process must be restarted to pick up ANY fix

### Dry-run test for tomorrow
- Exercised the full `_refresh_daily_schedule` logic for March 12 without writing to Redis
- `get_calendar(2026-03-12)` returned 104 events, 7 in universe
- Generated correct keys: OLLI, GIII, DKS, AMTX, FNKO, ADBE, HCAT
- All conference times in EDT (UTC-04:00) — correct for post-DST (DST started March 8)

---

## Risk Assessment of the Proposed Fix

| Change | Risk | Reasoning |
|---|---|---|
| Add `None` defaults in `__init__` | None | Defensive; prevents `AttributeError` if call order changes; no signature change |
| Add guard in `_refresh_daily_schedule` | None | 2-line check; returns `False` if client missing → `last_date` won't advance → retries |
| Pass `earnings_call_client` to processor | None | Injection after construction; no constructor signature change |
| Set `processor.last_date` after startup | None | Prevents harmless but unnecessary double-refresh |
| Return bool from `_refresh_daily_schedule` | None | Additive change, no callers break |
| Only advance `last_date` on success | None | Strictly safer than current behavior |
| Remove `from earningscall import get_calendar` | None | No longer referenced |
| Periodic intra-day rescan (every 2h, 7AM-5PM) | None | zadd is idempotent, sismember skips processed; up to 6 extra API calls/day |
| Gate `_initialize_transcript_schedule` to live mode | Low | Historical-only runs no longer seed the schedule; verify no downstream code depends on schedule being populated in hist-only mode |
| Replace startup delete+seed with additive+prune | Low | Preserves in-progress retries on mid-day restart; 48h stale prune bounds unbounded retry accumulation; `zadd` idempotent for re-seeding |

**Total regression risk: Low.** All changes are either additive (return value, rescan, gate) or
narrow substitutions (use passed client instead of constructing new one / importing raw function).
The gate change (Finding 6) and delete→prune change are the highest-risk items — verify that no
historical-only workflow depends on the schedule being populated, and that 48h is a safe stale
cutoff (longest observed retry cycle is ~12h).

---

## Additional Observation: GRPN Missing from Schedule

**Date**: 2026-03-11

Today's `get_calendar()` returns 4 events in the universe: GRPN (08:00), CXM (08:30), CPB (09:00),
PATH (17:00). But `admin:transcripts:schedule` only contains CXM, CPB, PATH. GRPN is absent.

**Redis state**: Zero GRPN keys anywhere — no tracking, no processed set membership, no raw keys.
GRPN was never scheduled.

**Cause**: The earningscall API updates its calendar dynamically as companies confirm call times.
Whatever process populated the current schedule ran before GRPN appeared on the API. This is NOT
a code bug but a limitation of one-shot scheduling:

- If `_initialize_transcript_schedule()` runs at midnight and GRPN is added to the calendar at 6 AM,
  GRPN is missed for the entire day
- The current fix (`_refresh_daily_schedule`) only fires once per day on date transition — it would
  NOT catch intra-day calendar additions either

**Note**: The exact claim "GRPN appeared later on the API" is an inference, not proof. But it is
the most plausible explanation — the scheduling code has no GRPN-specific filter, and both conditions
(in universe + on calendar) are met now but weren't at schedule time.

**Resolution**: Added as Finding 5. Periodic intra-day rescans (every 2 hours, 7AM-5PM ET) catch
late additions using the same idempotent `_refresh_daily_schedule()` method. See Change 2.

---

## Known Limitations (pre-existing, not addressed by this fix)

### Unbounded retries

Both retry paths have no max count or age check:

- **`_schedule_transcript_retry`** (TranscriptProcessor.py:287-299): Reschedules with
  `TRANSCRIPT_RESCHEDULE_INTERVAL` (default 5 min) via `zadd`. No counter, no max age.
  A transcript that is permanently unavailable from the provider retries forever.

- **Error handler** (TranscriptProcessor.py:234-238): On exception, reschedules 30 minutes
  later via `zadd`. Also no counter or max age.

**Impact**: Entries accumulate in `admin:transcripts:schedule` indefinitely. The 48h stale
prune on startup (introduced in this fix) provides a partial backstop — entries older than
48h are cleaned on restart. But between restarts, accumulation is unbounded.

**Recommended future fix**: Add a retry counter or max-age check. For example, store retry
metadata in a hash (`admin:transcripts:retry_counts`) and stop retrying after N attempts or
after the conference_datetime is more than 24h old.

### `processed_set` TTL

`admin:transcripts:processed` has a 2-day TTL (TranscriptProcessor.py:250). After 2 days,
a transcript key falls out of the processed set and could theoretically be re-scheduled by
an intra-day rescan. In practice this is unlikely (the calendar API drops old dates quickly),
but it is a theoretical gap.

---

## Post-Fix Verification Checklist

- [ ] Restart process with new code
- [ ] Check logs for `"Date transition detected"` message (only once per day)
- [ ] Confirm no `"Date transition detected"` on startup (Finding 4 fix)
- [ ] Check `ZRANGEBYSCORE admin:transcripts:schedule -inf +inf WITHSCORES` shows correct items
- [ ] After midnight: confirm the new/current New York day's events appear after the midnight rollover
- [ ] Force-kill network briefly during transition to test retry behavior (Finding 1 fix)
- [ ] Confirm periodic rescan logs appear every 2 hours during 7AM-5PM window
- [ ] Verify rescan fires only once per 2-hour slot (not every loop iteration)
- [ ] Verify failed rescan does NOT advance `_last_rescan_hour` (retries next loop)
- [ ] Run a historical-only process and confirm `admin:transcripts:schedule` is NOT touched (Finding 6)
- [ ] Verify live startup still seeds the schedule (gate passes when `ENABLE_LIVE_DATA=True`)
- [ ] Verify live startup failure leaves `last_date=None` so scheduler thread retries immediately
- [ ] Verify startup no longer deletes `admin:transcripts:schedule` (additive+prune replaces delete+seed)
- [ ] Verify stale entries older than 48h are pruned on startup
- [ ] Verify in-progress retries survive a mid-day restart (add a fake retry entry, restart, confirm it persists)
- [ ] Verify `_initialize_transcript_schedule` returns `True` on empty calendar (no events day)
- [ ] **Scenario A**: Live startup success → schedule populated, `last_date` set, no double-refresh
- [ ] **Scenario B**: Live startup failure → `last_date` stays None, scheduler retries on first loop
- [ ] **Scenario C**: Historical-only run while live process is up → `admin:transcripts:schedule` untouched
- [ ] **Scenario D**: Mid-day restart with active retries → retries preserved, today re-seeded additively
- [ ] Update `docs/data_flow.md` line 58 — remove "runs on startup regardless of flags (considered safe)", replace with gated behavior
- [ ] **Phase 2**: Verify `_fetch_and_process_transcript` reuse of shared client works (separate commit)
