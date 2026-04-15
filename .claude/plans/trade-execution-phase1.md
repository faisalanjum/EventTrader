# Trade Execution System — Phase 1

This file is the implementation spec for the first build. If it conflicts with `trade-execution-system.md`, this file wins.

## 1. Scope

Implement only:

1. one daemon
2. filesystem detection
3. one canonical signal contract emitted by the producer
4. confidence/magnitude gate
5. ATR-based sizing
6. bracket entry with stop protection
7. stop / max-hold / account-kill-switch exits
8. restart recovery
9. `trade/plan.json`, `trade/result.json`, `trade/skipped.json`

Do not implement:

- Redis fast-trigger
- spread gate
- chase gate
- sector ETF logic
- SPY macro logic
- gap fade
- session reversal
- transcript/news reassessment
- streaming quotes
- learner inputs in TES / trade_daemon
- learner `auto_tune`
- realtime mode
- take-profit

## 2. Files To Implement

Required:

- `scripts/trade/trade_daemon.py`

Required reusable dependency:

- `scripts/trade/ibkr_client.py`

Optional helper modules are allowed, but not required.

## 2A. Locked Interfaces

These are the architecture invariants for Phase 1 and later phases. Everything
else may be revised as implementation evolves.

1. Canonical TES input contract
   - TES consumes one canonical signal contract only
   - any source, including earnings, news, momentum, or a future live agent,
     must emit that contract
   - the source of truth for this contract is Section 3 in this file

2. TES ownership boundary
   - TES is the only component allowed to place, cancel, or flatten broker
     orders
   - no predictor, learner, trigger, monitor, or reassessment engine may bypass
     TES

3. Future monitoring boundary
   - any future monitor/reassessment component must return a generic decision
     packet rather than broker instructions
   - the source of truth for that packet is Section 22.3 in this file

4. Learner boundary
   - learner outputs may influence prediction context immediately
   - TES parameter changes may not auto-apply unless explicitly enabled by
     config
   - the source of truth for this rule is Sections 21 and 22.4 in this file

## 3. Canonical Signal Contract

TES consumes this shape:

```json
{
  "signal_id": "AAPL_Q1_FY2026_2026-04-08T20:15:00Z",
  "source_type": "earnings",
  "symbol": "AAPL",
  "event_id": "Q1_FY2026",
  "issued_at": "2026-04-08T20:15:30Z",
  "event_time": "2026-04-08T20:15:00Z",
  "direction": "long",
  "confidence": 78,
  "expected_move_range": [4.0, 6.0],
  "thesis_summary": null,
  "context_ref": null,
  "session_id": null
}
```

TES parses only these canonical fields. Any source-specific payload stays behind `context_ref`.

Phase 1 rule:

- the producer must emit the canonical TES signal contract directly
- `trade_daemon.py` reads those canonical fields directly from `prediction/result.json`
- TES never translates field names; the producer is responsible for emitting the canonical contract

If any required field is missing, TES skips the prediction and logs an error. The producer is responsible for fallbacks (e.g., deriving `issued_at` from filesystem modification time if the upstream source omits it).

## 4. Paths

Scan:

```text
earnings-analysis/Companies/*/events/*/prediction/result.json
```

Per event (event_id = quarter_label for earnings, article_id for news, etc.):

```text
earnings-analysis/Companies/{TICKER}/events/{event_id}/trade/
  plan.json
  result.json
  skipped.json
```

Global files:

```text
earnings-analysis/trade_daemon.lock
earnings-analysis/trade_daemon_state.json
```

## 5. Required Input Fields From Current Producer

`prediction/result.json` must provide:

```json
{
  "signal_id": "AAPL_Q1_FY2026_2026-04-08T20:15:00Z",
  "source_type": "earnings",
  "symbol": "AAPL",
  "event_id": "Q1_FY2026",
  "event_time": "2026-04-08T20:15:00Z",
  "issued_at": "2026-04-08T20:15:30Z",
  "direction": "long",
  "confidence": 78,
  "expected_move_range": [4.0, 6.0]
}
```

TES reads these fields directly. Future signal sources must emit the same canonical contract.

Optional:

```json
{
  "thesis_summary": null,
  "context_ref": null,
  "session_id": null
}
```

## 6. Fixed Config

```text
ACCOUNT_MODE = paper
DATA_MODE = delayed

CONFIDENCE_THRESHOLD = 75
MAGNITUDE_THRESHOLD = 3.0
MAX_POSITIONS = 2

RISK_PER_TRADE_PCT = 2.0
ATR_MULTIPLIER = 2.0
MIN_STOP_PCT = 3.0
MAX_STOP_PCT = 15.0
EXECUTION_BUFFER_PER_SHARE = 0.30
LIMIT_BUFFER_PCT = 0.15

ACCOUNT_KILL_SWITCH_PCT = 15.0

SCAN_INTERVAL_SEC = 30
BROKER_RESPONSE_TIMEOUT_SEC = 60
ENTRY_FILL_TIMEOUT_SEC = 300
TIMEZONE = America/New_York
NYSE_CALENDAR = XNYS
```

Phase 1 requires an IBKR account whose base currency is USD.

- `AccountSummary.base_currency` must equal `"USD"`
- if the connected account base currency is not USD, the daemon must refuse to start
- no implicit CAD/USD mixing is allowed in phase 1 sizing, buying-power checks, or kill-switch logic

## 7. Exact Formulas

### 7.1 Edge

```text
edge_pct = expected_move_range[0]
```

### 7.2 ATR-14

```text
TR = max(high - low, abs(high - prev_close), abs(low - prev_close))
ATR_14 = simple average of the last 14 TR values from the last 15 daily bars
```

Use daily OHLC ending on the most recent completed trading day before `event_time`.

Source:

- primary: Neo4j/Polygon daily OHLC
- no fallback in phase 1
- reference implementation: `scripts/atr_compare_sources.py` (has working Neo4j query)

Neo4j connection:

```python
from neo4j import GraphDatabase
# Env vars: NEO4J_URI (bolt://minisforum3:30687), NEO4J_USER, NEO4J_PASSWORD
# Reuse the same env vars already used by other scripts in this repo.
driver = GraphDatabase.driver(os.environ["NEO4J_URI"],
                              auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]))
```

Session-cutoff rule for the `before` parameter:

```python
def trading_date_cutoff(event_time: datetime) -> date:
    """Convert event_time to the last completed trading day's date.
    If event_time is after 4:00 PM ET (post-market), the SAME calendar date
    is a completed trading day. If before 4:00 PM ET, use the previous trading day.
    Use exchange_calendars to handle weekends/holidays."""
    # Convert to America/New_York first.
    # Then return the correct completed trading date using the rule above.
```

Neo4j query pattern (Company node → HAS_PRICE → DailyBar):

```cypher
MATCH (c:Company {ticker: $symbol})-[:HAS_PRICE]->(bar:DailyBar)
WHERE bar.date <= date($cutoff_date)
ORDER BY bar.date DESC
LIMIT 15
RETURN bar.date, bar.open, bar.high, bar.low, bar.close
```

Note: uses `<=` not `<`. For an 8:15 PM filing, `cutoff_date` = that same day (trading is complete). For a 2:00 PM filing, `cutoff_date` = previous trading day.

Node properties: `bar.open`, `bar.high`, `bar.low`, `bar.close` (floats), `bar.date` (date).

Implement in `scripts/trade/trade_daemon.py` (or a helper module imported by it):

```python
def load_daily_bars(symbol: str, cutoff_date: date, limit: int = 15) -> list[dict]:
    """Query Neo4j for daily OHLC bars where bar.date <= cutoff_date.
    Returns list of {date, open, high, low, close}, newest first.
    Returns empty list if no data."""
    # Implement with the Cypher query above.

def compute_atr14(bars: list[dict]) -> float | None:
    """Compute ATR-14 from bars. Returns None if fewer than 15 bars."""
    # bars arrive newest first from load_daily_bars().
    # Reverse them to oldest first before computing TR because TR uses prev_close.
    # Then use the TR and ATR formulas defined in Section 7.2.

def load_atr14(symbol: str, event_time: datetime) -> float | None:
    cutoff = trading_date_cutoff(event_time)
    bars = load_daily_bars(symbol, cutoff, limit=15)
    return compute_atr14(bars)

If fewer than 15 valid daily bars exist, `compute_atr14` returns `None`.

### 7.3 Entry reference price

```text
entry_reference_price = ask if ask is not null and ask > 0
                     else last if last is not null and last > 0
                     else null
```

Quote validity rule:

- valid quote = `entry_reference_price` is not `null`
- invalid quote = both `ask` and `last` are missing, zero, or negative

### 7.4 Stop distance and shares

```text
raw_stop_distance = ATR_MULTIPLIER * ATR_14
min_stop_distance = MIN_STOP_PCT * entry_reference_price / 100
max_stop_distance = MAX_STOP_PCT * entry_reference_price / 100
stop_distance = clamp(raw_stop_distance, min_stop_distance, max_stop_distance)

per_share_risk = stop_distance + EXECUTION_BUFFER_PER_SHARE
account_equity = AccountSummary.net_liquidation
dollar_risk = account_equity * RISK_PER_TRADE_PCT / 100
shares = floor(dollar_risk / per_share_risk)
stop_price = entry_reference_price - stop_distance
```

If `shares < 1`, skip.

### 7.5 Entry limit

Use the same marketable-limit rule as `scripts/trade/ibkr_client.py`:

```text
one_tick = contract.minTick if available
         else 0.0001 if entry_reference_price < 1.0
         else 0.01
limit_buffer = max(one_tick, entry_reference_price * LIMIT_BUFFER_PCT / 100)
entry_limit_price = round_to_tick(entry_reference_price + limit_buffer)
```

## 8. IBKR

Read `scripts/trade/ibkr_client.py` for all return types, dataclass definitions, and error handling. Key classes:

- `BracketPlacementResult` — returned by `place_entry_with_stop()`. Fields: `status` ("filled", "partial_fill", "timeout_no_fill", "entry_rejected", "filled_stop_inactive"), `filled_quantity`, `intended_quantity`, `stop_active`, `entry` (OrderResult), `stop` (OrderResult), `message`. Properties: `needs_flatten` (filled but no stop), `needs_stop_qty_adjustment` (partial fill), `needs_parent_remainder_cancel` (partial fill with working parent remainder), `needs_bracket_cancellation` (zero-fill timeout/reject)
- `AccountSummary` — returned by `get_account_summary()`. Fields: `net_liquidation`, `available_funds`, `buying_power`, `base_currency`
- `Position` — returned by `get_positions()`. Fields: `symbol`, `con_id`, `quantity`, `avg_cost`
- `QuoteSnapshot` — returned by `get_quote()`. Fields: `bid`, `ask`, `last`, `spread_pct`, `close`
- `OrderResult` — returned by `get_open_orders()` and `flatten_position()`. Fields: `symbol`, `con_id`, `order_id`, `action`, `order_type`, `quantity`, `status`, `avg_fill_price`

Create client:

```python
config = IBKRConfig.from_account_mode("paper", data_mode="delayed")
client = TradeDaemonIBClient(config)
await client.connect()
```

Use:

- `await client.get_quote(symbol)`
- `await client.qualify_stock(symbol)`
- `await client.get_account_summary()`
- `await client.get_positions()`
- `await client.get_open_orders()`
- `await client.place_entry_with_stop(symbol, "BUY", shares, entry_limit_price, stop_price, fill_timeout=BROKER_RESPONSE_TIMEOUT_SEC)`
- `await client.modify_stop_quantity(order_id, new_quantity)`
- `await client.cancel_order(order_id)`
- `await client.flatten_position(symbol, quantity, action="SELL")`
- `await client.verify_stop_active(order_id)`
- `await client.shutdown()`

Phase 1 is long-only. Every manual flatten call uses `action="SELL"`.

Before any entry:

- qualify the stock contract
- persist `contract.conId` as `plan.con_id`
- if qualification fails, skip with reason `contract_unavailable`

Flatten quantity rule:

- if a current broker position exists, use `int(abs(position.quantity))`
- otherwise, in immediate post-entry failure handling, use `int(BracketPlacementResult.filled_quantity)`

## 9. Singleton

Use local file locking only.

Lock file:

```text
earnings-analysis/trade_daemon.lock
```

Implementation:

- open file
- acquire `fcntl.flock(fd, LOCK_EX | LOCK_NB)`
- if lock fails, exit
- keep file descriptor open for process lifetime

## 10. Atomic Writes

Every JSON write must use:

1. write to `path + ".tmp"`
2. flush
3. `os.fsync()`
4. `os.replace(tmp_path, final_path)`

Implement:

```python
def atomic_write_json(path: Path, data: dict) -> None: ...
```
Implement exactly with the 4 steps listed above.

All timestamps persisted in JSON files must be UTC ISO-8601 strings with trailing `Z`.

- Use `America/New_York` only for exchange-calendar calculations.
- Before writing any timestamp field to JSON, convert it to UTC and serialize with trailing `Z`.

## 10a. Result File Write-Once Rule

`trade/result.json` is write-once.

Rules:

- If `trade/result.json` does not exist, the daemon may write it.
- If `trade/result.json` already exists, the daemon must NOT rewrite or replace it.
- Terminal retry/recovery paths must be idempotent:
  - they may continue canceling lingering orders
  - they may continue updating `trade/plan.json` to `closed`
  - they must not create a second terminal result record
- All terminal branches should use one helper:

```python
def write_result_if_missing(path: Path, data: dict) -> None:
    """Write trade/result.json only if it does not already exist.
    Uses atomic_write_json internally. No-op if path already exists."""
```

`trade/skipped.json` follows the same write-once rule. All terminal branches that write `trade/skipped.json` should use:

```python
def write_skipped_if_missing(path: Path, data: dict) -> None:
    """Write trade/skipped.json only if it does not already exist.
    Uses atomic_write_json internally. No-op if path already exists."""
```

## 11. Daemon State

`earnings-analysis/trade_daemon_state.json`

```json
{
  "started_at": "2026-04-08T15:30:00Z",
  "starting_equity": 100000.0,
  "account_mode": "paper"
}
```

Rules:

- if file exists, reuse `starting_equity`
- if file does not exist and there are no open trades (`entering` or `open` plan.json files), create it from current `AccountSummary.net_liquidation`
- if file does not exist BUT open trades exist: log CRITICAL and refuse to start. The operator must manually create the file with the correct `starting_equity` before restarting. Reason: current equity may already reflect trade losses, so using it as `starting_equity` would silently reset the kill-switch baseline.
- do not reset it automatically while daemon is active

## 12. Deadlines

### 12.1 Exchange calendar usage

```python
import exchange_calendars as xcals
nyse = xcals.get_calendar("XNYS")

def next_close(after: datetime) -> datetime:
    """Return the next NYSE regular-session close at or after `after`."""
    # If `after` is during a session, return that session's close.
    # If `after` is after close or on a non-trading day, return the next session's close.
    # Return a timezone-aware America/New_York datetime.
```

### 12.2 Entry deadline

Orders are placed immediately with `outsideRth=True`.

If the market is not currently matching the order, queued entry is allowed only for a short bounded window.

Entry deadline rule:

- `entry_deadline_at` = `order_placement_time + timedelta(seconds=ENTRY_FILL_TIMEOUT_SEC)`

If the bracket has zero fills at `entry_deadline_at`, cancel it and call `write_skipped_if_missing(...)` with reason `entry_timeout`.

`BROKER_RESPONSE_TIMEOUT_SEC` means only:

- how long to wait for the initial broker response before returning control to the daemon

It is **not** the final entry deadline.

### 12.3 Max-hold deadline

Use `exchange_calendars.get_calendar("XNYS")`.

Rule (based on entry fill time, not event_time):

- `exit_deadline_at` = `next_close(entry_fill_time)`
- if fill is during a session → that session's close
- if fill is after close → next session's close

Timezone: `America/New_York`

## 13. Persistent States

Persist only:

- `entering`
- `open`
- `closed`

`skipped` is represented by `trade/skipped.json`, not `plan.json`.

`pending_terminal_reason` is a nullable field on `trade/plan.json`.

- `null` = no manual terminal action is in progress
- non-null = the daemon has decided on a manual terminal outcome and must keep driving that same outcome across retries/restarts until `trade/result.json` is written

Protected manual-exit retry policy:

- applies only when the daemon is trying to manually flatten a position for `max_hold` or `account_killswitch` and the broker-native stop is still active
- keep `manual_flatten_retry_count` in memory only for phase 1
- after 3 consecutive failed flatten attempts for the same trade, log `CRITICAL: MANUAL INTERVENTION REQUIRED`
- after that CRITICAL log, stop automatic flatten retries for that protected manual-exit path
- unprotected-position cases such as `stop_placement_failed` or `stop_repair_failed` must keep retrying every cycle; do not cap those retries

## 14. Main Loop

Startup:

1. acquire file lock
2. register SIGTERM handler (sets `shutdown_requested = True`)
3. connect IBKR client (needed before step 4 — state file creation may require `AccountSummary.net_liquidation`)
4. fetch `AccountSummary` and require `base_currency == "USD"`; if not, log CRITICAL and refuse to start
5. create/reuse `trade_daemon_state.json`
6. load all existing `trade/plan.json` with status `entering` or `open`, then run the same canonical state handlers defined in Sections 17 and 18 once before entering the loop
7. enter loop

Loop:

1. if `shutdown_requested`, break out of loop
2. if `not client.is_connected()`, call `await client.connect()`
3. monitor `entering` plans
4. monitor `open` plans
5. verify broker-state cleanliness once for the loop:
   - if any non-flat broker position or working order is unmatched by `con_id`, set `new_entries_blocked = true`
   - otherwise set `new_entries_blocked = false`
6. if `new_entries_blocked` is false, scan for new `prediction/result.json` (skip if `shutdown_requested`)
7. sleep `SCAN_INTERVAL_SEC`

Error handling: wrap each step (3, 4, 5, 6) in try/except. If one trade's monitoring throws (e.g., IBKR disconnected), log the error, skip that trade, continue to the next. Do not crash the loop.

Shutdown (after loop exits):

1. log "shutting down, N active trades"
2. disconnect IBKR client
3. release file lock
4. exit

## 15. New Prediction Processing

For each `prediction/result.json`:

This section runs only when the loop-level broker-state cleanliness check in Section 14 has already passed.

1. derive sibling `trade/` directory
2. if `trade/plan.json` exists, do nothing
3. if `trade/skipped.json` exists, do nothing
4. if `trade/result.json` exists, do nothing
5. read canonical TES signal fields directly from `prediction/result.json`
6. if `direction != "long"`, call `write_skipped_if_missing(...)` with reason `direction_short`
7. if `confidence < CONFIDENCE_THRESHOLD`, call `write_skipped_if_missing(...)` with reason `confidence_below_threshold`
8. if `edge_pct < MAGNITUDE_THRESHOLD`, call `write_skipped_if_missing(...)` with reason `magnitude_below_threshold`
9. qualify stock contract and capture `con_id`
   - if qualification fails, call `write_skipped_if_missing(...)` with reason `contract_unavailable`
10. fetch:
   - quote (record `spread_pct_at_entry` from bid/ask)
   - account summary
   - ATR_14
   - pre_earnings_close (from same daily OHLC data as ATR)
11. if quote invalid, call `write_skipped_if_missing(...)` with reason `quote_unavailable`
12. if ATR missing, call `write_skipped_if_missing(...)` with reason `atr_unavailable`
13. if daemon-managed open trade count `>= MAX_POSITIONS`, call `write_skipped_if_missing(...)` with reason `max_positions`
    (count = number of `trade/plan.json` files with status `entering` or `open`, but new entries are allowed only when broker state is clean)
14. compute shares and stop
15. if `shares < 1`, call `write_skipped_if_missing(...)` with reason `shares_too_small`
16. if `AccountSummary.buying_power < shares * entry_limit_price`, call `write_skipped_if_missing(...)` with reason `insufficient_capital`
17. capture `order_placement_time = datetime.now(tz=ZoneInfo("America/New_York"))` — this is the reference for entry deadline
18. write initial `trade/plan.json` with status `entering`
19. set:
   - `con_id = qualified_contract.conId`
   - `entry_order_id = null`
   - `stop_order_id = null`
   - `entry_deadline_at = order_placement_time + timedelta(seconds=ENTRY_FILL_TIMEOUT_SEC)` converted to UTC `Z` for JSON storage
   - `exit_deadline_at = null`
   - `order_placement_time = order_placement_time` converted to UTC `Z` for JSON storage
   - `pending_terminal_reason = null`
   - `submission_uncertain = false`
20. call `place_entry_with_stop(...)`
   - if `place_entry_with_stop(...)` raises an exception before returning `BracketPlacementResult`:
     - log CRITICAL with the exception
     - set `submission_uncertain = true`
     - keep `trade/plan.json` as `entering`
     - leave `entry_order_id` and `stop_order_id` as `null`
     - do not write `trade/result.json` or `trade/skipped.json`
     - do not call `place_entry_with_stop(...)` again for this plan
     - next monitoring/recovery cycle must reconcile broker state using `con_id`-matched positions/open orders until `entry_deadline_at`
21. update `trade/plan.json` with returned `entry_order_id` and `stop_order_id`
22. handle result:
   - `filled` and stop active -> capture `fill_observed_at = datetime.now(tz=ZoneInfo("America/New_York"))`, set `filled_shares = int(filled_quantity)`, set `entry_fill_price = result.entry.avg_fill_price if > 0 else null`, set `entry_filled_at = fill_observed_at` converted to UTC `Z`, set `exit_deadline_at = next_close(fill_observed_at)` converted to UTC `Z`, then update `trade/plan.json` to `open`
   - `partial_fill` and stop active success criteria:
     - parent-remainder cancel succeeds only if `cancel_order(entry_order_id)` returns non-null and no working entry order remains for the same `con_id` afterward
     - after canceling the parent remainder, refetch current positions and open orders, then define `repair_quantity = int(abs(position.quantity))` if a broker position exists for the same `con_id`, else `int(filled_quantity)`
     - stop-quantity repair succeeds only if `modify_stop_quantity(stop_order_id, repair_quantity)` returns non-null and `verify_stop_active(stop_order_id)` returns `True`
   - `partial_fill` and stop active -> first cancel the parent remainder using `cancel_order(entry_order_id)`, then refetch current positions and open orders and confirm no working entry order remains for the same `con_id`, then define `repair_quantity = int(abs(position.quantity))` if a broker position exists for the same `con_id`, else `int(filled_quantity)`, then adjust stop quantity via `modify_stop_quantity(stop_order_id, repair_quantity)`, then capture `fill_observed_at = datetime.now(tz=ZoneInfo("America/New_York"))`, set `filled_shares = repair_quantity`, set `entry_fill_price = result.entry.avg_fill_price if > 0 else null`, set `entry_filled_at = fill_observed_at` converted to UTC `Z`, set `exit_deadline_at = next_close(fill_observed_at)` converted to UTC `Z`, then update `trade/plan.json` to `open`
   - partial-fill safety rule: **only** mark the trade `open` after both steps above succeed. If either step fails, first capture `fill_observed_at = datetime.now(tz=ZoneInfo("America/New_York"))`, set `filled_shares = int(filled_quantity)`, set `entry_fill_price = result.entry.avg_fill_price if > 0 else null`, set `entry_filled_at = fill_observed_at` converted to UTC `Z`, set `pending_terminal_reason = stop_repair_failed`, then flatten immediately using `int(filled_quantity)`, then fetch open orders again, then cancel the stop order if it is still working, then call `write_result_if_missing(...)` with exit reason `stop_repair_failed`, then update `trade/plan.json` to `closed`
   - any filled quantity with inactive stop -> first capture `fill_observed_at = datetime.now(tz=ZoneInfo("America/New_York"))`, set `filled_shares = int(filled_quantity)`, set `entry_fill_price = result.entry.avg_fill_price if > 0 else null`, set `entry_filled_at = fill_observed_at` converted to UTC `Z`, set `pending_terminal_reason = stop_placement_failed`, then flatten immediately using `int(filled_quantity)`, then fetch open orders again, then cancel the stop order if it is still working, then call `write_result_if_missing(...)` with exit reason `stop_placement_failed`, then update `trade/plan.json` to `closed`
   - `timeout_no_fill` -> keep `trade/plan.json` as `entering`
   - `entry_rejected` with zero fills -> cancel any working entry/stop orders for the same `con_id`; if any cancellation fails, log CRITICAL and keep `trade/plan.json` as `entering` for retry next cycle; otherwise delete `trade/plan.json` and call `write_skipped_if_missing(...)` with reason `entry_rejected`

## 16. Position Matching Rule

Phase 1 qualifies the contract before entry and persists `plan.con_id`.

Match broker positions to trades by **contract ID**:

- broker position match = `Position.con_id == plan.con_id`
- stop-order match = `plan.stop_order_id == OrderResult.order_id`
- if `stop_order_id` is unknown, use `OrderResult.con_id == plan.con_id` plus `order_type == "STP"` to locate a lingering stop

`symbol` is used for logging only. `con_id` is the authoritative identity for matching and recovery.

Definition: **active stop exists** means:

- `plan.stop_order_id` is not `null`
- and `await client.verify_stop_active(plan.stop_order_id)` returns `True`

Use `get_open_orders()` only for locating/canceling orders. Use `verify_stop_active()` as the authoritative active-stop check.

Working-order matching rule (used when order IDs are missing or when cleaning up no-position branches):

- a **working entry order** = any current open order for the same `con_id` with `order_type != "STP"`
- a **lingering stop order** =:
  - the current open order whose `order_id == plan.stop_order_id`, if `plan.stop_order_id` is known
  - otherwise any current open order for the same `con_id` with `order_type == "STP"`

Unmatched broker state:

- any non-flat broker position or working order whose `con_id` does not match an existing `entering` or `open` plan is unmatched broker state
- unmatched broker state blocks all new entries until resolved

No-position finalization rule:

- before deleting `trade/plan.json` or calling `write_result_if_missing(...)` / `write_skipped_if_missing(...)` in any branch where no broker position remains, first cancel any lingering stop order if present
- if stop cancellation fails, log CRITICAL and retry next cycle/restart instead of finalizing the trade locally

## 17. Entering Plan Monitoring (status = entering)

This is the canonical `entering` state handler. Use the same handler during normal loop monitoring and during startup recovery.

For each `trade/plan.json` with status `entering`:

1. fetch current positions
2. fetch open orders
3. if `pending_terminal_reason` is not null and broker position exists:
   - flatten immediately using current broker position quantity
   - if flatten fails, log CRITICAL, skip and retry next cycle
   - fetch open orders again after flatten
   - if `stop_order_id` is still present in open orders, cancel it
   - if stop cancellation fails, log CRITICAL, skip and retry next cycle
   - call `write_result_if_missing(...)` using `pending_terminal_reason`
   - update `trade/plan.json` to `closed`
4. if `pending_terminal_reason` is not null and broker position does not exist:
   - cancel any lingering stop order first
   - call `write_result_if_missing(...)` using `pending_terminal_reason`
   - update `trade/plan.json` to `closed`
5. if broker position exists and active stop exists:
   - set `status = open`
   - set `filled_shares = int(abs(position.quantity))`
   - set `entry_fill_price` using this priority:
     1. existing `plan.entry_fill_price` if already set during initial result handling
     2. matching broker position `avg_cost` if > 0
     3. otherwise leave `entry_fill_price = null`
   - set `entry_filled_at` using this priority:
     1. existing `plan.entry_filled_at` if already set during initial result handling
     2. current recovery/monitoring timestamp converted to UTC `Z` if the exact broker fill time is not available
   - set `exit_deadline_at` from fill timestamp, stored in UTC with trailing `Z`
   - set `pending_terminal_reason = null`
6. if broker position exists and no active stop:
   - set `pending_terminal_reason = stop_repair_failed`
   - flatten immediately using current broker position quantity
   - fetch open orders again after flatten
   - if `stop_order_id` is still present in open orders, cancel it
   - if stop cancellation fails, log CRITICAL, skip and retry next cycle
   - call `write_result_if_missing(...)` with exit reason `stop_repair_failed`
   - update `trade/plan.json` to `closed`
7. if current time >= `entry_deadline_at` and broker position does not exist:
   - cancel any working entry/stop orders
   - if any cancellation fails, log CRITICAL, skip and retry next cycle
   - delete `trade/plan.json`
   - if `submission_uncertain` is true, call `write_skipped_if_missing(...)` with reason `entry_unresolved`
   - otherwise call `write_skipped_if_missing(...)` with reason `entry_timeout`

## 18. Open Plan Monitoring (status = open)

This is the canonical `open` state handler. Use the same handler during normal loop monitoring and during startup recovery.

For each `trade/plan.json` with status `open`:

1. fetch current positions
2. fetch current open orders
3. fetch current account summary
4. if `pending_terminal_reason` is not null and broker position exists:
   - flatten position using current broker position quantity
   - if flatten fails, log CRITICAL, skip and retry next cycle
   - fetch open orders again after flatten
   - if `stop_order_id` is still present in open orders, cancel it
   - if stop cancellation fails, log CRITICAL, skip and retry next cycle
   - call `write_result_if_missing(...)` using `pending_terminal_reason`
   - update `trade/plan.json` to `closed`
   - **skip remaining checks for this trade**
5. if no broker position exists for the plan's `con_id`:
   - cancel any lingering stop order first
   - if `pending_terminal_reason` is not null:
     - call `write_result_if_missing(...)` using `pending_terminal_reason`
   - otherwise call `write_result_if_missing(...)` with exit reason `stop_fired`
   - update `trade/plan.json` to `closed`
   - **skip remaining checks for this trade** (position is gone)
6. if `AccountSummary.net_liquidation < starting_equity * (1 - ACCOUNT_KILL_SWITCH_PCT / 100)`:
   - set `pending_terminal_reason = account_killswitch`
   - flatten position using current broker position quantity
   - if flatten fails and the broker-native stop is still active:
     - increment the in-memory protected-manual-exit retry counter for this trade
     - if retry count <= 3, log CRITICAL and retry next cycle
     - if retry count > 3, log `CRITICAL: MANUAL INTERVENTION REQUIRED` and stop automatic retries for this protected manual-exit path
   - if flatten fails and the broker-native stop is not active, treat as unprotected and continue retrying every cycle
   - fetch open orders again after flatten
   - if `stop_order_id` is still present in open orders, cancel it
   - if stop cancellation fails, log CRITICAL, skip and retry next cycle
   - call `write_result_if_missing(...)` with exit reason `account_killswitch`
   - update `trade/plan.json` to `closed`
7. if current time >= `exit_deadline_at`:
   - set `pending_terminal_reason = max_hold`
   - flatten position using current broker position quantity
   - if flatten fails and the broker-native stop is still active:
     - increment the in-memory protected-manual-exit retry counter for this trade
     - if retry count <= 3, log CRITICAL and retry next cycle
     - if retry count > 3, log `CRITICAL: MANUAL INTERVENTION REQUIRED` and stop automatic retries for this protected manual-exit path
   - if flatten fails and the broker-native stop is not active, treat as unprotected and continue retrying every cycle
   - fetch open orders again after flatten
   - if `stop_order_id` is still present in open orders, cancel it
   - if stop cancellation fails, log CRITICAL, skip and retry next cycle
   - call `write_result_if_missing(...)` with exit reason `max_hold`
   - update `trade/plan.json` to `closed`

## 19. Recovery

Recovery applies only to `trade/plan.json` files with status `entering` or `open`.

Implementation rule:

- do not implement a separate recovery decision tree
- on startup, after connecting and loading plans, call the same canonical state handlers from Section 17 for every `entering` plan and from Section 18 for every `open` plan
- recovery uses the same broker reads, branching rules, terminal-write rules, and retry behavior as normal loop monitoring
- if a handler raises during startup recovery, log CRITICAL, leave the plan unchanged, continue to the next plan, and let the next loop iteration retry it

## 20. Exact File Schemas

### 20.1 `trade/plan.json`

```json
{
  "signal_id": "AAPL_Q1_FY2026_2026-04-08T20:15:00Z",
  "source_type": "earnings",
  "symbol": "AAPL",
  "con_id": 265598,
  "event_id": "Q1_FY2026",
  "direction": "long",
  "confidence": 78,
  "expected_move_range": [4.0, 6.0],
  "status": "entering",
  "created_at": "2026-04-08T20:16:00Z",
  "updated_at": "2026-04-08T20:16:05Z",
  "entry_order_id": null,
  "stop_order_id": null,
  "intended_shares": 10,
  "filled_shares": 0,
  "entry_reference_price": 185.20,
  "entry_limit_price": 185.48,
  "entry_fill_price": null,
  "stop_price": 175.96,
  "stop_distance": 9.24,
  "atr_14": 4.62,
  "edge_pct": 4.0,
  "spread_pct_at_entry": 0.18,
  "pre_earnings_close": 178.10,
  "account_equity_at_entry": 100000.0,
  "issued_at": "2026-04-08T20:15:30Z",
  "event_time": "2026-04-08T20:15:00Z",
  "order_placement_time": "2026-04-09T00:16:00Z",
  "entry_deadline_at": "2026-04-09T00:21:00Z",
  "entry_filled_at": null,
  "exit_deadline_at": null,
  "pending_terminal_reason": null,
  "submission_uncertain": false,
  "account_mode": "paper",
  "data_mode": "delayed",
  "thesis_summary": null,
  "context_ref": null,
  "session_id": null
}
```

When the trade fills:

- set `status = open`
- set `entry_fill_price`
- set `entry_filled_at`
- set `filled_shares`
- set `exit_deadline_at`

When the trade closes:

- keep `plan.json`
- set `status = closed`
- keep the last `pending_terminal_reason` value if one was used to drive the terminal action
- update `updated_at`

Timestamp rules for `trade/plan.json`:

- `created_at` = UTC `Z` timestamp from the initial `plan.json` write; never changes afterward
- `updated_at` = UTC `Z` timestamp every time `plan.json` is rewritten

### 20.2 `trade/result.json`

```json
{
  "signal_id": "AAPL_Q1_FY2026_2026-04-08T20:15:00Z",
  "source_type": "earnings",
  "symbol": "AAPL",
  "con_id": 265598,
  "event_id": "Q1_FY2026",
  "direction": "long",
  "status": "closed",
  "opened_at": "2026-04-08T20:16:10Z",
  "closed_at": "2026-04-09T20:00:00Z",
  "shares": 10,
  "entry_fill_price": 185.31,
  "exit_fill_price": 189.00,
  "exit_reason": "max_hold",
  "pnl_dollars": 36.90,
  "pnl_pct": 1.99,
  "confidence": 78,
  "expected_move_range": [4.0, 6.0],
  "edge_pct": 4.0,
  "stop_price": 175.96,
  "stop_distance": 9.24,
  "atr_14": 4.62,
  "spread_pct_at_entry": 0.18,
  "pre_earnings_close": 178.10,
  "issued_at": "2026-04-08T20:15:30Z",
  "event_time": "2026-04-08T20:15:00Z",
  "account_mode": "paper",
  "data_mode": "delayed"
}
```

Note: `exit_fill_price` may be `null` if the stop fired while daemon was down and fill data is not recoverable from the broker.

Result assembly rules:

- `opened_at` = `plan.entry_filled_at`
  - for `stop_placement_failed` / `stop_repair_failed` during entry repair, this value is set from the `fill_observed_at` captured in result handling before flattening
- `closed_at` = timestamp when the daemon records the terminal trade outcome, stored in UTC with trailing `Z`
- `shares` = final realized position size:
  - `plan.filled_shares` for stop/max-hold/kill-switch
  - `BracketPlacementResult.filled_quantity` for `stop_placement_failed` / `stop_repair_failed` during entry repair
- `entry_fill_price` source priority:
  1. `plan.entry_fill_price` if present
  2. `BracketPlacementResult.entry.avg_fill_price` if > 0
  3. matching broker position `avg_cost` if > 0
  4. otherwise `null`
- `exit_fill_price`:
  - for `max_hold` / `account_killswitch`, use the fill price returned by `flatten_position()`
  - for `stop_fired`, use recovered broker stop fill if available, else `null`
  - for `stop_placement_failed` / `stop_repair_failed`, use the fill price returned by `flatten_position()`
- `pnl_dollars`:
  - if both `entry_fill_price` and `exit_fill_price` are known:
    - `(exit_fill_price - entry_fill_price) * shares`
  - otherwise `null`
- `pnl_pct`:
  - if `pnl_dollars` is known and `entry_fill_price` is known and `shares > 0`:
    - `pnl_dollars / (entry_fill_price * shares) * 100`
  - otherwise `null`
- `confidence`, `expected_move_range`, `edge_pct`, `stop_price`, `stop_distance`, `atr_14`, `spread_pct_at_entry`, `pre_earnings_close`, `issued_at`, `event_time`, `account_mode`, and `data_mode` are copied from `trade/plan.json`
- `direction`, `signal_id`, `source_type`, `symbol`, `con_id`, and `event_id` are copied from the canonical signal / `trade/plan.json`

Allowed `exit_reason`:

```text
stop_fired
max_hold
account_killswitch
stop_placement_failed
stop_repair_failed
```

### 20.3 `trade/skipped.json`

```json
{
  "signal_id": "AAPL_Q1_FY2026_2026-04-08T20:15:00Z",
  "source_type": "earnings",
  "symbol": "AAPL",
  "event_id": "Q1_FY2026",
  "status": "skipped",
  "skipped_at": "2026-04-08T20:15:30Z",
  "reason": "shares_too_small"
}
```

`skipped_at` = UTC `Z` timestamp when the daemon writes `trade/skipped.json`.

Allowed `reason`:

```text
direction_short
confidence_below_threshold
magnitude_below_threshold
quote_unavailable
atr_unavailable
contract_unavailable
insufficient_capital
max_positions
shares_too_small
entry_rejected
entry_timeout
entry_unresolved
```

## 21. Learning

Phase 1 **trade execution** reads no learner files. Phase 1 writes only:

- `trade/result.json`
- `trade/skipped.json`

These are the raw inputs for any future learner. `result.json` is self-contained (includes prediction fields, stop params, mode flags) so the learner does not need to also read `plan.json`.

Phase 1 **prediction** may still use prior learning.

Ownership split:

- attributor / learner writes past analyses or lesson files
- orchestrator loads the relevant prior lessons before prediction
- predictor receives those lessons as context in the prediction bundle
- TES / `trade_daemon.py` does not read learner files in phase 1

If no prior lessons exist, prediction still runs normally.

### Future learning interface (do not implement in Phase 1, design for):

- Learner writes per-trade lesson files, append-only: `learnings/trades/{signal_id}.json`
- Each lesson covers one trade: what went right, what went wrong, what would have been better
- Aggregation across trades is a separate concern (human or batch job), not the per-trade learner's job
- Predictor reads either raw per-trade lessons or compiled summaries, chosen by config
- Parameter recommendations are logged with empirical evidence, not auto-applied at launch
- Per-parameter learning policy (`auto` / `log` / `never`) is controlled by a config value per parameter, not hardcoded tiers
- Future components (reassessment, compactor, alternate signal sources) build on `result.json` + `skipped.json` without changing the Phase 1 trade loop

## 22. Future Extension Hooks

These interfaces are reserved now so later components plug in without rewriting phase 1.

### 22.1 Signal-source independence

All future signal sources must adapt into the canonical signal contract in Section 3.

TES remains blind to producer-specific fields beyond the canonical contract.

Orchestrator remains the place that assembles prediction context, including any lesson files used for prediction.

### 22.2 Generic reassessment event

Future reassessment must consume a generic event packet, not transcript/news-specific logic:

```json
{
  "signal_id": "AAPL_Q1_FY2026_2026-04-08T20:15:00Z",
  "source_type": "earnings",
  "symbol": "AAPL",
  "event_type": "transcript",
  "event_time": "2026-04-08T21:30:00Z",
  "event_ref": null,
  "summary": null
}
```

`event_type` may later be:

- transcript
- news
- price
- macro
- sector
- external_agent

Phase 1 does not implement reassessment.

### 22.3 Generic monitor decision

Future monitoring/reassessment engines must return a generic decision packet.
TES consumes the packet and acts deterministically. The monitor decides thesis;
TES decides broker actions.

```json
{
  "signal_id": "AAPL_Q1_FY2026_2026-04-08T20:15:00Z",
  "decision_time": "2026-04-08T21:35:00Z",
  "action": "hold",
  "reason": "thesis_intact",
  "confidence": 0.78,
  "summary": null
}
```

Allowed future `action` values:

- `hold`
- `exit`
- `escalate`

Examples of engines that may later produce this packet:

- pure Python trigger logic
- small watcher model that wakes a larger monitor
- external/full predictor flow
- hybrid monitoring stack

Phase 1 does not implement monitor decisions.

### 22.4 Config-driven future behavior

Future behavior must be switchable by config, not by rewriting TES:

- prediction learning input mode
- reassessment mode
- per-parameter learning policy

Default future-facing config values:

```text
PREDICTION_LEARNING_MODE = raw_lessons
REASSESSMENT_MODE = off
APPLY_LEARNED_PARAMETERS = false
PARAMETER_LEARNING_DEFAULT = log
```

Rules:

- prediction learning may affect the next prediction immediately, depending on `PREDICTION_LEARNING_MODE`
- TES parameter changes must never auto-apply unless explicitly enabled by config
- learned parameter recommendations default to `log`, not `auto`

Example future values:

```text
PREDICTION_LEARNING_MODE = off | raw_lessons | compiled_lessons
REASSESSMENT_MODE = off | python_triggers | external_engine
PARAMETER_LEARNING_POLICY[param] = auto | log | never
```

### 22.5 Ownership Rule

Architecture ownership must remain strict:

- TES owns execution state and all broker actions
- monitor/reassessment engines own thesis review only
- learner owns recommendations and evidence logging
- orchestrator decides what learning enters prediction context
- no component may bypass TES to place, cancel, or flatten broker orders

## 23. ToDo

After phase 1, add one component at a time:

1. walkforward using `DATA_MODE=delayed` + paper account
2. append-only learner outputs for:
   - paper trades
   - live trades
   - historical PIT predictions
3. config-driven prediction learning input:
   - orchestrator loads raw lessons first
   - compiled summaries later if needed
4. generic reassessment event ingestion
5. choose reassessment mode:
   - python-triggered minimal flow, or
   - external/full predictor flow
6. additional signal adapters beyond earnings
7. optional compactor / aggregated learning artifacts
8. parameter learning:
   - log with empirical evidence first
   - allow `auto` only per-parameter and only by config
9. deferred execution features from `trade-execution-system.md`:
   - Redis fast-trigger
   - extra monitoring rules
   - streaming quotes
   - realtime mode
   - broader risk/monitoring logic

## 24. Acceptance Test

Phase 1 is correct when all of the following work in paper + delayed mode:

1. detect one new `prediction/result.json`
2. read canonical TES signal fields directly
3. write one `trade/plan.json`
4. if no fill occurs before `ENTRY_FILL_TIMEOUT_SEC` after placement, call `write_skipped_if_missing(...)` with reason `entry_timeout`
5. if fill occurs, create exactly one `trade/result.json`
6. no duplicate trade on daemon restart
7. entry is never left unprotected
8. broker position disappearance is recorded as `stop_fired`
9. max-hold exit happens at correct NYSE close
10. kill-switch closes the position and writes `account_killswitch`
