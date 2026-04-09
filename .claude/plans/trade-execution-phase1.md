# Trade Execution System — Phase 1

This file is the implementation spec for the first build. If it conflicts with `trade-execution-system.md`, this file wins.

## 1. Scope

Implement only:

1. one daemon
2. filesystem detection
3. one canonical signal adapter
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

Implement:

```python
def adapt_prediction_result(path: Path) -> dict: ...
```

Phase 1 adapter from current earnings prediction file:

```text
prediction_id        -> signal_id
ticker               -> symbol
predicted_at         -> issued_at
filed_at             -> event_time
direction            -> direction
confidence           -> confidence
expected_move_range  -> expected_move_range
rationale_summary    -> thesis_summary
context_bundle path  -> context_ref
predictor_session_id -> session_id
quarter_label        -> event_id
source_type          -> "earnings"
```

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
  "prediction_id": "AAPL_Q1_FY2026_2026-04-08T20:15:00Z",
  "ticker": "AAPL",
  "quarter_label": "Q1_FY2026",
  "filed_at": "2026-04-08T20:15:00Z",
  "direction": "long",
  "confidence": 78,
  "expected_move_range": [4.0, 6.0]
}
```

Note: `quarter_label` and `filed_at` are earnings-specific fields. The adapter maps them to the generic `event_id` and `event_time` canonical fields. Future signal sources provide their own equivalents.

Optional:

```json
{
  "predicted_at": "2026-04-08T20:15:30Z",
  "rationale_summary": null,
  "predictor_session_id": null
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
MAX_HOLD_SESSIONS = 1

SCAN_INTERVAL_SEC = 30
MONITOR_INTERVAL_SEC = 30
ORDER_TIMEOUT_SEC = 60
TIMEZONE = America/New_York
NYSE_CALENDAR = XNYS
```

Phase 1 currency assumption: the IBKR paper account base currency is CAD, but all traded stocks are USD (SMART/USD). `AccountSummary.net_liquidation` and `buying_power` are returned in the account's base currency by IBKR. Phase 1 uses these values directly — no currency conversion. All stock prices, stop distances, and P&L are in USD. The sizing math uses `net_liquidation` as-is (CAD ≈ USD within ~25% — acceptable for paper trading plumbing validation). For live trading, ensure the account base currency is USD or add explicit conversion.

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
    ...
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

Spread formula (from the quote already fetched for entry_reference_price):

```text
spread_pct = (ask - bid) / ask * 100
```

Implement in `scripts/trade/trade_daemon.py` (or a helper module imported by it):

```python
def load_daily_bars(symbol: str, cutoff_date: date, limit: int = 15) -> list[dict]:
    """Query Neo4j for daily OHLC bars where bar.date <= cutoff_date.
    Returns list of {date, open, high, low, close}, newest first.
    Returns empty list if no data."""
    ...

def compute_atr14(bars: list[dict]) -> float | None:
    """Compute ATR-14 from bars. Returns None if fewer than 15 bars."""
    ...

def load_atr14(symbol: str, event_time: datetime) -> float | None:
    cutoff = trading_date_cutoff(event_time)
    bars = load_daily_bars(symbol, cutoff, limit=15)
    return compute_atr14(bars)

def load_pre_event_close(symbol: str, event_time: datetime) -> float | None:
    cutoff = trading_date_cutoff(event_time)
    bars = load_daily_bars(symbol, cutoff, limit=1)
    return bars[0]["close"] if bars else None
```

Both use the same daily OHLC data via `load_daily_bars`. `load_pre_event_close` returns the `close` of the most recent bar.

If fewer than 15 valid daily bars exist, `compute_atr14` returns `None`.

### 7.3 Entry reference price

```text
entry_reference_price = ask if ask is not null else last
```

If both are missing, skip.

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
one_tick = contract.minTick if available else price tick helper default
limit_buffer = max(one_tick, entry_reference_price * LIMIT_BUFFER_PCT / 100)
entry_limit_price = round_to_tick(entry_reference_price + limit_buffer)
```

## 8. IBKR

Read `scripts/trade/ibkr_client.py` for all return types, dataclass definitions, and error handling. Key classes:

- `BracketPlacementResult` — returned by `place_entry_with_stop()`. Fields: `status` ("filled", "partial_fill", "timeout_no_fill", "entry_rejected", "filled_stop_inactive"), `filled_quantity`, `intended_quantity`, `stop_active`, `entry` (OrderResult), `stop` (OrderResult), `message`. Properties: `needs_flatten` (filled but no stop), `needs_stop_qty_adjustment` (partial fill)
- `AccountSummary` — returned by `get_account_summary()`. Fields: `net_liquidation`, `available_funds`, `buying_power`
- `Position` — returned by `get_positions()`. Fields: `symbol`, `quantity`, `avg_cost`
- `QuoteSnapshot` — returned by `get_quote()`. Fields: `bid`, `ask`, `last`, `spread_pct`, `close`
- `OrderResult` — returned by `get_open_orders()`. Fields: `symbol`, `order_id`, `action`, `order_type`, `quantity`, `status`

Create client:

```python
config = IBKRConfig.from_account_mode("paper", data_mode="delayed")
client = TradeDaemonIBClient(config)
await client.connect()
```

Use:

- `await client.get_quote(symbol)`
- `await client.get_account_summary()`
- `await client.get_positions()`
- `await client.get_open_orders()`
- `await client.place_entry_with_stop(symbol, "BUY", shares, entry_limit_price, stop_price)`
- `await client.modify_stop_quantity(order_id, new_quantity)`
- `await client.cancel_order(order_id)`
- `await client.flatten_position(symbol, quantity, action="SELL")`
- `await client.verify_stop_active(order_id)`
- `await client.shutdown()`

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

## 11. Daemon State

`earnings-analysis/trade_daemon_state.json`

```json
{
  "schema_version": "daemon-state.v1",
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
    ...
```

### 12.2 Entry deadline

Orders are placed immediately with `outsideRth=True`.

If the market is not currently matching the order, queued entry is allowed.

Entry deadline rule:

- `entry_deadline_at` = `next_close(order_placement_time)`

If the bracket has zero fills at `entry_deadline_at`, cancel it and write `trade/skipped.json`.

`ORDER_TIMEOUT_SEC` means only:

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

## 14. Main Loop

Startup:

1. acquire file lock
2. register SIGTERM handler (sets `shutdown_requested = True`)
3. connect IBKR client (needed before step 4 — state file creation may require `AccountSummary.net_liquidation`)
4. create/reuse `trade_daemon_state.json`
5. recover all existing `trade/plan.json`
6. enter loop

Loop:

1. if `shutdown_requested`, break out of loop
2. monitor `entering` plans
3. monitor `open` plans
4. scan for new `prediction/result.json` (skip if `shutdown_requested`)
5. sleep `SCAN_INTERVAL_SEC`

Error handling: wrap each step (2, 3, 4) in try/except. If one trade's monitoring throws (e.g., IBKR disconnected), log the error, skip that trade, continue to the next. Do not crash the loop. Reconnect to IBKR on next cycle if needed.

Shutdown (after loop exits):

1. log "shutting down, N active trades"
2. disconnect IBKR client
3. release file lock
4. exit

## 15. New Prediction Processing

For each `prediction/result.json`:

1. derive sibling `trade/` directory
2. if `trade/plan.json` exists, do nothing
3. if `trade/skipped.json` exists, do nothing
4. if `trade/result.json` exists, do nothing
5. adapt prediction into canonical signal
6. if `direction != "long"`, write `trade/skipped.json` reason `direction_short`
7. if `confidence < CONFIDENCE_THRESHOLD`, write `trade/skipped.json` reason `confidence_below_threshold`
8. if `edge_pct < MAGNITUDE_THRESHOLD`, write `trade/skipped.json` reason `magnitude_below_threshold`
9. fetch:
   - quote (record `spread_pct_at_entry` from bid/ask)
   - account summary
   - positions
   - ATR_14
   - pre_earnings_close (from same daily OHLC data as ATR)
10. if quote invalid, write `trade/skipped.json` reason `quote_unavailable`
11. if ATR missing, write `trade/skipped.json` reason `atr_unavailable`
12. if daemon-managed open trade count `>= MAX_POSITIONS`, write `trade/skipped.json` reason `max_positions`
    (count = number of `trade/plan.json` files with status `entering` or `open`, NOT raw IBKR positions)
13. compute shares and stop
14. if `shares < 1`, write `trade/skipped.json` reason `shares_too_small`
15. if `AccountSummary.buying_power < shares * entry_limit_price`, write `trade/skipped.json` reason `insufficient_capital`
16. capture `order_placement_time = datetime.now(tz=ZoneInfo("America/New_York"))` — this is the reference for entry deadline
17. write initial `trade/plan.json` with status `entering`
18. set:
   - `entry_order_id = null`
   - `stop_order_id = null`
   - `entry_deadline_at = next_close(order_placement_time)`
   - `exit_deadline_at = null`
   - `order_placement_time = order_placement_time`
19. call `place_entry_with_stop(...)`
20. update `trade/plan.json` with returned `entry_order_id` and `stop_order_id`
21. handle result:
   - `filled` and stop active -> update `trade/plan.json` to `open`
   - `partial_fill` and stop active -> cancel parent remainder, adjust stop quantity via `modify_stop_quantity()`, update `trade/plan.json` to `open`. If cancel or stop-qty adjustment fails (returns None), treat as `needs_flatten` — flatten immediately, write `trade/result.json` exit reason `stop_repair_failed`
   - any filled quantity with inactive stop -> flatten immediately, write `trade/result.json` exit reason `stop_placement_failed`, update `trade/plan.json` to `closed`
   - `timeout_no_fill` -> keep `trade/plan.json` as `entering`
   - `entry_rejected` with zero fills -> delete `trade/plan.json`, write `trade/skipped.json` reason `entry_rejected`

## 16. Position Matching Rule

Phase 1 assumes a dedicated paper account (no external positions). Match broker positions to trades by **symbol only** (`Position.symbol == plan.symbol`). Match stop orders by `plan.stop_order_id == OrderResult.order_id`.

If a future phase shares the account with other systems, switch to contract ID matching (`conId`).

## 17. Entering Plan Monitoring (status = entering)

For each `trade/plan.json` with status `entering`:

1. fetch current positions
2. fetch open orders
3. if broker position exists and active stop exists:
   - set `status = open`
   - set `filled_shares`
   - set `entry_fill_price` if known
   - set `entry_filled_at`
   - set `exit_deadline_at` from fill timestamp
4. if broker position exists and no active stop:
   - flatten immediately
   - write `trade/result.json` exit reason `stop_repair_failed`
   - update `trade/plan.json` to `closed`
5. if current time >= `entry_deadline_at` and broker position does not exist:
   - cancel any working entry/stop orders
   - delete `trade/plan.json`
   - write `trade/skipped.json` reason `entry_expired_unfilled`

## 18. Open Plan Monitoring (status = open)

For each `trade/plan.json` with status `open`:

1. fetch current positions
2. fetch current account summary
3. if no broker position exists for the symbol:
   - write `trade/result.json` exit reason `stop_fired`
   - update `trade/plan.json` to `closed`
   - **skip remaining checks for this trade** (position is gone)
4. if `AccountSummary.net_liquidation < starting_equity * (1 - ACCOUNT_KILL_SWITCH_PCT / 100)`:
   - flatten position
   - if flatten fails, log CRITICAL, skip (broker stop protects, retry next cycle)
   - write `trade/result.json` exit reason `account_killswitch`
   - update `trade/plan.json` to `closed`
5. if current time >= `exit_deadline_at`:
   - flatten position
   - if flatten fails, log CRITICAL, skip (broker stop protects, retry next cycle)
   - write `trade/result.json` exit reason `max_hold`
   - update `trade/plan.json` to `closed`

## 19. Recovery

Recover only `trade/plan.json` files with status `entering` or `open`.

Recover `entering`:

1. inspect broker position and open orders
2. if broker position exists and active stop exists:
   - update to `open`
3. if broker position exists and no active stop:
   - flatten immediately
   - write `trade/result.json` exit reason `stop_repair_failed`
   - update `trade/plan.json` to `closed`
4. if broker position does not exist and no working entry order exists:
   - delete `trade/plan.json`
   - write `trade/skipped.json` reason `entry_recovery_cancelled`
5. if broker position does not exist and working entry order exists:
   - keep status `entering`

Recover `open`:

1. if broker position exists and active stop exists:
   - resume monitoring
2. if broker position exists and no active stop:
   - flatten immediately
   - write `trade/result.json` exit reason `stop_repair_failed`
   - update `trade/plan.json` to `closed`
3. if broker position does not exist:
   - write `trade/result.json` exit reason `stop_fired`
   - update `trade/plan.json` to `closed`

## 20. Exact File Schemas

### 19.1 `trade/plan.json`

```json
{
  "schema_version": "trade-plan.v1",
  "signal_id": "AAPL_Q1_FY2026_2026-04-08T20:15:00Z",
  "source_type": "earnings",
  "symbol": "AAPL",
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
  "entry_deadline_at": "2026-04-09T20:00:00Z",
  "entry_filled_at": null,
  "exit_deadline_at": null,
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
- update `updated_at`

### 19.2 `trade/result.json`

```json
{
  "schema_version": "trade-result.v1",
  "signal_id": "AAPL_Q1_FY2026_2026-04-08T20:15:00Z",
  "source_type": "earnings",
  "symbol": "AAPL",
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

Allowed `exit_reason`:

```text
stop_fired
max_hold
account_killswitch
stop_placement_failed
stop_repair_failed
```

### 19.3 `trade/skipped.json`

```json
{
  "schema_version": "trade-skipped.v1",
  "signal_id": "AAPL_Q1_FY2026_2026-04-08T20:15:00Z",
  "source_type": "earnings",
  "symbol": "AAPL",
  "event_id": "Q1_FY2026",
  "status": "skipped",
  "skipped_at": "2026-04-08T20:15:30Z",
  "reason": "shares_too_small"
}
```

Allowed `reason`:

```text
direction_short
confidence_below_threshold
magnitude_below_threshold
quote_unavailable
atr_unavailable
insufficient_capital
max_positions
shares_too_small
entry_rejected
entry_expired_unfilled
entry_recovery_cancelled
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

### 21.1 Signal-source independence

All future signal sources must adapt into the canonical signal contract in Section 3.

TES remains blind to producer-specific fields beyond the canonical contract.

Orchestrator remains the place that assembles prediction context, including any lesson files used for prediction.

### 21.2 Generic reassessment event

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

### 21.3 Config-driven future behavior

Future behavior must be switchable by config, not by rewriting TES:

- prediction learning input mode
- reassessment mode
- per-parameter learning policy

Example future values:

```text
PREDICTION_LEARNING_MODE = off | raw_lessons | compiled_lessons
REASSESSMENT_MODE = off | python_triggers | external_engine
PARAMETER_LEARNING_POLICY[param] = auto | log | never
```

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
2. adapt it into canonical signal fields
3. write one `trade/plan.json`
4. if no fill occurs before first NYSE close after placement, write `trade/skipped.json` reason `entry_expired_unfilled`
5. if fill occurs, create exactly one `trade/result.json`
6. no duplicate trade on daemon restart
7. entry is never left unprotected
8. broker position disappearance is recorded as `stop_fired`
9. max-hold exit happens at correct NYSE close
10. kill-switch closes the position and writes `account_killswitch`
