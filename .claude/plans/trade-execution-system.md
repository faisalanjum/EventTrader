# Trade Execution System — Design Plan

**Status:** ALL 6 BLOCKS LOCKED ✓ — PLAN COMPLETE

---

## Block 1: Goals, Non-Goals, and Key Definitions

### A. The Problem We're Solving

Our existing `earnings-prediction` pipeline reads 8-K filings and outputs a prediction (direction, confidence, magnitude). This prediction currently goes nowhere — no orders are placed, no money is made or lost. We need a system that automatically: detects the prediction → decides whether to trade → places orders → monitors the position → recalibrates when new text evidence arrives → exits → records the result for learning.

### B. What We're Optimizing For (priority order)

**B1. Maximize profit from earnings trades**
- Enter fast after the 8-K filing (every minute of delay reduces win rate — backtest: 72% at 5-min entry, 54% at 60-min)
- Capture the earnings reaction before signal decays (~88% of move done by next market open)
- Recalibrate when material new text evidence arrives (transcript, whitelisted Benzinga news) — the thesis may strengthen or invalidate
- System supports both long and short trades in code/schemas. At launch, the daemon only EXECUTES long trades (short signals are logged for attribution but not traded). Short execution is a future capability.

**B2. Cut losses fast, protect capital**
- Volatility-aware stops via clamped ATR: `stop_distance = clamp(k × ATR_14, min_stop_pct × entry, max_stop_pct × entry)`. Pure ATR can be too tight for post-earnings noise or too loose for quiet names. The clamp keeps stops in a sane range.
- Dollar-risk sizing: decide how much you're willing to LOSE per trade (a fixed dollar amount from config), then: `per_share_risk = stop_distance + execution_buffer`, `shares = floor(dollar_risk / per_share_risk)`. Wider stop = fewer shares = same dollar at risk. Risk is always ~$X regardless of stock volatility.
- Aggregate risk is implicitly bounded at launch: DOLLAR_RISK_PER_TRADE × MAX_POSITIONS = max aggregate exposure ($500 × 2 = $1,000 on a $50K account = 2%). An explicit total-capital-at-risk gate is deferred until MAX_POSITIONS increases beyond 2.
- Broker-protected stop placement: preferred implementation is a linked bracket order when supported. If a given entry path cannot link the stop atomically, the daemon must use fail-closed choreography: if entry fills and stop is not confirmed immediately, flatten the trade. There must never be an unprotected live position.
- Account-level emergency kill-switch: if total account equity drops below a threshold, close ALL positions immediately.

**B3. Don't cut winners too early**
- Backtest data: average winner is +12.1%. A 5% profit cap destroys 80% of returns.
- Monitoring should only catch genuine thesis breaks (stock reversed, sector collapsed, new evidence invalidated thesis), not minor noise.
- Default action is always HOLD. Wide thresholds by default.
- Never close a thesis-valid trade to fund a new one. If at max positions when a new prediction fires, skip the new trade. Portfolio optimization is explicitly deferred until confidence scores are calibrated from 100+ trades.

**B4. Recalibrate on new text evidence, not on price noise**
- The prediction is made from the 8-K press release. But within the trade's lifetime, two important new text sources can arrive:
  1. The earnings call transcript (typically 1-2 hours after filing) — management tone, guidance details, analyst Q&A
  2. Whitelisted Benzinga news categories (analyst downgrade/upgrade, guidance revision, SEC investigation, earnings revision) — via real-time Benzinga feed
- When these arrive, the Reassessment Engine resumes the original predictor session (which has full context) and asks: "does this new evidence confirm or invalidate the existing thesis?"
- Session resume is PREFERRED, not required. If resume fails (session expired, compacted), the daemon applies the safe fallback: no_change + no_escalation from persisted files. Trade safety never depends on session resumability.
- This is NOT continuous monitoring. It is NOT a full prediction rerun. It is a focused, text-triggered delta judgment.
- The daemon acts on the result deterministically. The LLM never touches trade state or places orders.
- **Fail-safe**: if the reassessment LLM call fails (API error, timeout, rate limit):
  - **no_change**: hold current position, do not exit
  - **no_escalation**: do not relax risk rules, extend hold, or take any optional action based on a failed reassessment
  - Hard stops and time exits remain active regardless
  - The system is correct even without reassessment. Reassessment is an enhancement, not a dependency.

**B5. Keep the system minimal**
- One primary LLM call at entry (the prediction, which already exists)
- Optional lightweight reassessment calls only on whitelisted text-event triggers — at most 2-3 times per trade lifetime
- One Python daemon for everything live (gate, size, execute, monitor, trigger reassessments, exit, reconcile)
- Files on disk as the source of truth
- The broker handles the hardest real-time job (native stop-loss enforcement)
- Three-layer ownership: LLM writes opinions → Python writes state → broker executes risk

**B6. Calibrate before risking real money**
- Paper trading first (IBKR paper account — simulated money, with data freshness determined by `DATA_MODE`)
- Two independent config flags:
  - `ACCOUNT_MODE = paper | live` — which IBKR account receives orders
  - `DATA_MODE = delayed | realtime` — price data freshness
- Launch configuration: `ACCOUNT_MODE=paper, DATA_MODE=delayed` (15-min delayed prices)
- Goal configuration: `ACCOUNT_MODE=live, DATA_MODE=realtime` (when IBKR Live provides real-time data)
- These are independent because: you might want paper+realtime (testing with live prices, fake money) or live should never run with delayed data (unsafe). Keeping them separate preserves this flexibility.
- The architecture is identical in all modes — only these two flags change behavior.
- Delayed-data paper trading validates plumbing, safety, restart behavior, and broad gate/monitor quality. P&L and timing metrics from delayed mode are provisional until validated with real-time data.

### C. What's Explicitly OUT for Launch

**C1. No continuous LLM monitoring during a trade**
The core monitoring (stop checks, benchmark stress, gap fade, momentum, time exit) is deterministic. No Claude calls for routine hold/exit decisions. The LLM never watches prices.

Reassessment IS allowed, but ONLY for two well-defined text-event triggers:
- **Transcript arrival**: when the earnings call transcript for THIS specific event is ingested into Neo4j, the Reassessment Engine runs a delta review against the original thesis.
- **Whitelisted Benzinga news**: categories `[analyst_downgrade, analyst_upgrade, guidance_revision, sec_investigation, earnings_revision]`. When a matching article appears for the held ticker, the sector ETF, or SPY, the Reassessment Engine runs.

Guardrails:
- Transcript: max 1 per trade (one earnings call per event)
- Benzinga: max 1 reassessment per 2-hour cooldown window, deduped by article ID
- Total: at most 2-3 reassessments per trade lifetime
- LLM failure: no_change + no_escalation (fail-safe)
- Generic "significant news" reruns are NOT allowed. The whitelist prevents false positives.

**C2. No custom per-trade numeric thresholds from the LLM**
The LLM's trading judgments are limited to: direction, confidence, expected_move_range, key_drivers, rationale_summary. All numeric thresholds (stop distances, benchmark stress levels, gate thresholds, hold durations) live in daemon config. Pipeline metadata such as `prediction_id`, `model_version`, and `prompt_version` may still be recorded in `prediction/result.json` for audit and attribution. Python owns all numeric policy.

**C3. No portfolio optimizer**
Max 2 concurrent positions. Dollar-risk sizing within a per-trade risk budget. First-come first-served. Never close an active trade to fund a new one at launch.

**C4. No re-entry after exit**
If we exit (stop hit, thesis invalidated, time expired), that trade is done. No "buy back if it bounces."

**C5. Long-only execution at launch, no options, no hedging**
System supports both long and short in code. Daemon only EXECUTES long at launch (short signals logged for attribution). No sector hedges, no options. Each is a future capability.

**C6. No trailing stop at launch**
IBKR supports native trailing stops. However: trailing stops can trigger during normal pullbacks, and our backtest says "let winners run." Trailing stops are a future optimization, additive via config flag.

**C7. No competing trade replacement at launch**
No cross-trade ranking, no replacing one active trade with another, and no portfolio optimization at launch.

**C8. No profiles (FAST/CONTESTED eliminated)**
Confidence decides WHETHER to trade, not HOW to size. All trades that pass the gate use the same sizing, the same monitoring template, the same reassessment flow. One template, not two. Simpler, more testable, less risk of classification error.

### D. Key Definitions

**D1. 8-K filing** — SEC form filed when a company reports earnings. Contains revenue, EPS, and forward guidance. Triggers the entire pipeline.

**D2. Prediction / Signal** — Output of the existing `earnings-prediction` skill. Written to `prediction/result.json`. Contains:
- `prediction_id`: deterministic identifier `{ticker}_{quarter_label}_{filed_8k_timestamp}`. Reruns produce the same ID. Used for idempotency (daemon won't trade the same prediction twice) and audit trail.
- `direction`: long or short (short logged but not executed at launch)
- `confidence`: 0-100
- `expected_move_range`: e.g., [5, 8] meaning +5% to +8%
- `key_drivers`: list of thesis reasons (for reassessment context and attribution)
- `rationale_summary`: one-paragraph thesis (for reassessment context)
- `model_version`, `prompt_version`: for attribution tracking

**D3. trade_daemon.py** — The ONE new Python script. Runs continuously on Kubernetes. Handles the entire trade lifecycle: detect prediction → gate → size → execute → monitor → trigger reassessments → act on results → exit → record result. Single owner of all trade state and execution.

**Market data fetch** — on detecting a new prediction, the daemon fetches all required market data BEFORE running the gate:
- Account equity, free cash, open positions (IBKR)
- ATR_14 for the stock (IBKR or Polygon historical)
- Current stock price and bid-ask spread (IBKR)
- Sector ETF + SPY mapping and prices (Neo4j + IBKR)
- Market session state (derived from current time)

All values are fetched fresh at detection time. Stop price and share count computed from these immediately before order placement. No pre-fetching during prediction — the daemon only starts work after prediction/result.json exists.

**Prediction detection** — two-layer trigger: Redis for speed, filesystem for truth.
- **Fast path (Redis)**: the **orchestrator** (sole owner: the component that writes and validates prediction/result.json) pushes a small event to `trades:pending` Redis queue: `{"prediction_id": "...", "ticker": "...", "quarter_label": "..."}`. The daemon does BRPOP → wakes immediately → evaluates the trade.
- **Safety net (filesystem)**: the daemon also scans the filesystem every 30 seconds for any `prediction/result.json` without a corresponding `trade/plan.json` or `trade/skipped.json`. This catches anything Redis missed (message lost, daemon restarted before consuming).
- **Startup recovery**: on restart, the daemon scans filesystem FIRST (not Redis) to rebuild state from authoritative files.
- **Idempotency**: `prediction_id` prevents double-trading. If plan.json or skipped.json already exists for a prediction_id, the daemon skips regardless of how many Redis events arrive.
- **Ownership split**:
  - `earnings_trigger_daemon.py` detects fresh 8-K → triggers the orchestrator
  - the **orchestrator** writes and validates `prediction/result.json` → then pushes the `trades:pending` Redis event
  - `trade_daemon.py` consumes Redis event (fast) OR detects via filesystem scan (fallback) → begins trade lifecycle
- Redis = fast trigger. Filesystem = authoritative truth.

**Monitoring adapts to data freshness:**
- `DATA_MODE=realtime`: daemon subscribes to IBKR streaming market data (via `ib_insync` / TWS Gateway API) for the held stock, sector ETF, and SPY. IBKR pushes quote updates; daemon checks registered thresholds on each update. Thresholds registered when trade opens:
  - stock below stop price (safety backup behind broker stop)
  - sector ETF dropped X% from reference snapshot (benchmark stress)
  - SPY dropped Y% from reference snapshot (macro stress)
  - stock gave back Z% of initial move (gap fade)
  When ANY threshold crosses → daemon acts immediately (no polling delay).
  Daemon unsubscribes when trade closes.
- `DATA_MODE=delayed`: streaming unavailable. Daemon polls IBKR for prices every 30 seconds and checks the same thresholds each cycle.
- In BOTH modes: a time-based loop runs for non-price checks — reassessment triggers (consumed via Redis events from ingestion pipeline, with Neo4j backstop scan as fallback), time exits (market close), and IBKR reconciliation (position/order verification).
- Broker-native stops remain the true real-time downside protection in all modes.

**D4. IBKR (Interactive Brokers)** — Our broker. Two accounts: live (real money) and paper (simulated money). Market-data freshness depends on `DATA_MODE`, not on whether the account is paper or live. The daemon talks to IBKR via API to check account balance, get prices, place orders, and verify positions.

**D5. Broker-native stop with ATR-based distance** — Every trade must be protected by an IBKR-native stop. Preferred implementation is a linked bracket order when supported. If linked placement is unavailable for a given order/session path, the daemon must use fail-closed choreography: if the entry fills and the stop is not confirmed immediately, flatten the position. There must never be a live unprotected trade.

Stop distance is volatility-aware:
```
stop_distance = clamp(k × ATR_14, min_stop_pct × entry_price, max_stop_pct × entry_price)
per_share_risk = stop_distance + EXECUTION_BUFFER_PER_SHARE
shares = floor(dollar_risk_per_trade / per_share_risk)
```
Example: stock at $185, ATR=$4.50, risk=$500, buffer=$0.30 → stop=$9, per_share_risk=$9.30 → 53 shares → max loss $493.

**D6. Benchmark policy** — One fixed rule, fully daemon-owned:
- Sector ETF: looked up from Neo4j (Company → sector → ETF mapping, e.g., AAPL → Technology → XLK). Accept ~10% misclassification at launch — hard stop still protects.
- SPY: ALWAYS checked for every trade (macro stress).
- Thresholds: from daemon config, not from the LLM.
- No extra benchmark intelligence at launch. No LLM-picked benchmarks, no benchmark_importance field.

**D7. Gate** — Checklist of conditions that must ALL pass before any trade. All thresholds live in a config file for easy tuning.

Checks:
- `direction == long` (short skipped at launch)
- `confidence >= CONFIDENCE_THRESHOLD` (e.g., 75)
- `edge >= MAGNITUDE_THRESHOLD` (e.g., 3%) — where edge = low_end(expected_move_range), consistent everywhere
- IBKR account has sufficient free capital
- Bid-ask spread: three-tier liquidity policy (see D8a below)
- Chase protection: stock hasn't already moved most of predicted range
- Under `MAX_POSITIONS` (e.g., 2). Justification for 2: captures the most common multi-filing overlap (peak earnings = 2-3 filings same evening), limits aggregate risk to $1,000 ($500 × 2) while uncalibrated, keeps operational complexity low. Configurable upward after paper trading validates. Aggregate risk is implicitly bounded: DOLLAR_RISK × MAX_POSITIONS = max exposure.

Gate checks are split into two classes:
- **Fixed** (from prediction, won't change): direction, confidence, magnitude. If any fail → skip permanently.
- **Dynamic** (market-dependent, can change): spread, chase protection, free capital, max positions.

Gate outcomes:
- All pass, spread in "trade now" tier → trade immediately
- Fixed check fails → skip permanently (logged with reason)
- Spread in "defer" tier (other checks pass) → DEFER briefly. Daemon retries ALL checks until retry window expires (next open + `SPREAD_DEFER_WINDOW_MIN`). On each retry, all dynamic checks re-run (spread, chase, capital, positions). If all pass → trade. If window expires → skip permanently.
- Spread in "skip" tier → skip permanently. Edge is gone.
- Any other dynamic check fails (chase, capital, max positions) → skip permanently. These are structural constraints, not temporary liquidity issues.
- Deferred state persistence and exact file format deferred to later blocks.

**D8. Chase protection** — Gate check. Compares stock's current move (from pre-earnings close) to the prediction's expected range. If most of the upside is already captured (e.g., predicted +5-8%, already up +6%), trade is skipped. Protects against entering with unfavorable risk/reward. The threshold for "too much already moved" is configurable.

**D8a. Three-tier spread policy** — Spread is judged relative to the prediction's expected edge, not as a fixed number. The same absolute spread means different things for different edge sizes.

```
edge_pct = low_end(expected_move_range)    e.g., prediction [5, 8] → edge = 5% (conservative)
soft_max = min(SPREAD_MAX_PCT, SPREAD_EDGE_RATIO × edge_pct)
hard_max = min(SPREAD_HARD_MAX_PCT, SPREAD_HARD_EDGE_RATIO × edge_pct)
```

Note: uses LOWER bound of expected range, not midpoint. Conservative — does not overestimate what we can spend on slippage. This is a strong launch heuristic, not a provably optimal rule. Tunable via paper trading data.

| Tier | Condition | Action |
|---|---|---|
| **Trade now** | spread ≤ soft_max | Enter immediately with marketable limit. Spread is affordable relative to edge. |
| **Defer briefly** | soft_max < spread ≤ hard_max | Defer to next open + SPREAD_DEFER_WINDOW_MIN. Re-run ALL dynamic checks on retry. Temporary illiquidity (extended hours) may resolve at open. |
| **Skip** | spread > hard_max | Skip permanently. The market friction exceeds the expected opportunity. Edge is gone. |

This naturally tightens for low-edge predictions: a +3% prediction can't afford the same slippage as a +8% prediction. Execution always uses marketable limit orders (not market orders) to cap worst-case fill regardless of tier.

**D9. Reassessment Engine** — Resumes the original predictor session (which has full context from the initial prediction) and asks: "does this new evidence confirm or invalidate the existing thesis?"

Session resume is PREFERRED but not required:
- `predictor_session_id` saved in `trade/plan.json` at entry
- When trigger fires → try to resume session with new evidence
- If resume fails (expired, compacted) → no_change + no_escalation. No second fallback LLM call at launch.
- Trade safety NEVER depends on session resumability

Also saved for fallback and audit:
- Reference to `prediction/result.json` (original thesis)
- Reference to `prediction/context_bundle.json` (original data bundle)
- `model_version`, `prompt_version`

Output:
```json
{
  "thesis_status": "confirmed | unchanged | invalidated",
  "confidence": 85,
  "delta_summary": "Transcript reinforced demand durability..."
}
```

Daemon action mapping:
- **confirmed** → HOLD
- **unchanged** → HOLD
- **invalidated** → EXIT
- **LLM failure** → no_change (hold) + no_escalation. Hard stops and time exits remain active.

**D10. Reassessment triggers** — Two classes:

1. **Transcript ingested**: matched to the trade's `prediction_id` (ticker + quarter + 8-K timestamp) — not just ticker + date. Max 1 per trade.

2. **Whitelisted Benzinga news**: article matching ALL of:
   - Ticker: held stock, OR sector ETF, OR SPY
   - Category: `[analyst_downgrade, analyst_upgrade, guidance_revision, sec_investigation, earnings_revision]`
   - Deduped by article ID
   - Max 1 news reassessment per 2-hour cooldown per trade

**D11. Three-layer ownership model** — The fundamental safety architecture:
- **LLM writes opinions**: prediction + reassessment output structured judgments. Never touches trade state or places orders.
- **Python writes state**: `trade_daemon.py` is the sole owner of `trade/plan.json`. It alone decides orders.
- **Broker executes risk**: IBKR native stops fire regardless of daemon state or LLM availability.

Fail-safe chain: LLM failure → no_change + no_escalation. Daemon failure → broker stop still protects. Each layer failing makes the system more conservative, never more aggressive.

**D12. Filesystem-authoritative** — Trade state lives in JSON files. Daemon reads these on restart to reconstruct state. The original prediction is NEVER modified — reassessments are always separate append-only files.

**D13. U1 feedback loop** — Existing attribution mechanism enriched with trade data (P&L, exit reason, monitor effectiveness, reassessment accuracy, slippage). Attribution runs during the next historical bootstrap when the ticker re-enters trade_ready in Redis — not immediately after trade close. No resources consumed until needed.

**D14. Prediction ID** — Deterministic: `{ticker}_{quarter_label}_{filed_8k_timestamp}`. NOT a random UUID. Reruns produce the same ID. The daemon checks if `trade/plan.json` exists for this ID before acting — prevents duplicate trades. Separate from `predictor_session_id` (which is for session resume, not idempotency).

**D15. Reference snapshot** — Market prices captured at trade entry: stock price, sector ETF price, SPY price, timestamp. All monitoring thresholds (benchmark stress, gap fade, etc.) measure changes relative to this snapshot.

**D16. Max hold = market closes, not clock hours** — Exit is always at a market close (4:00 PM ET), not an arbitrary time.
- Post-market filing (e.g., 4:15 PM): hold to NEXT market close (~24h)
- Pre-market filing (e.g., 7:30 AM): hold to SAME DAY market close (~8.5h)
- Config: `MAX_HOLD_SESSIONS = 1` (number of closes from entry). Could be 2 for extension.

**D17. ACCOUNT_MODE / DATA_MODE** — Two independent configuration flags:
- `ACCOUNT_MODE = paper | live` — which IBKR account receives orders
- `DATA_MODE = delayed | realtime` — price data freshness, affects monitoring cadence/behavior and result accuracy
- Launch: paper + delayed. Goal: live + realtime.
- Independent because: paper+realtime is useful for testing; live+delayed must be blocked (unsafe).
- Architecture identical in all modes.

### E. Success Criteria (Paper Trading Phase)

| # | Metric | Target | Type |
|---|---|---|---|
| E1 | **Expectancy** | `(avg_win × win_rate) - (avg_loss × loss_rate) > 0` | Primary — must be positive |
| E2 | Win rate | Track, no hard gate | Secondary — informational, not pass/fail |
| E3 | P&L asymmetry | avg winner $ > avg loser $ | Primary — validates stop + let-winners-run |
| E4 | Max drawdown | Track peak-to-trough account drop | Risk — catches dangerous losing streaks |
| E5 | Slippage | Track wanted-price vs fill-price per trade | Quality — measures extended-hours fill cost |
| E6 | Reassessment effectiveness | Track: did reassessment exits avoid losses? | Quality — validates reassessment engine value |
| E7 | Unprotected positions | Zero, ever | Safety — broker-native stop ALWAYS confirmed |
| E8 | Daemon restarts | Clean recovery, no missed exits | Safety — reads plan.json + reconciles IBKR |
| E9 | Result capture | 100% trades produce result.json | Completeness — every outcome feeds attribution |
| E10 | Skip logging | 100% skipped predictions produce skipped.json with reason | Completeness — validates gate is working |
| E11 | Autonomous operation | Zero manual intervention for trade logic | Operational — excludes broker auth/gateway/data infra issues |

If `DATA_MODE=delayed`, treat profitability and timing metrics as provisional until rerun in a real-time-data mode.

### F. File Locations

```
earnings-analysis/
├── trade_daemon_state.json      ← global daemon state (starting_equity, pod_id, startup time)
│
└── Companies/{TICKER}/events/{quarter_label}/
    ├── prediction/
    │   ├── result.json              ← original signal + thesis (NEVER modified)
    │   └── context_bundle.json      ← original data bundle (for fallback reassessment)
    ├── trade/
    │   ├── plan.json                ← live trade state (daemon-owned, updated during trade)
    │   │                               includes: predictor_session_id, reference_snapshot,
    │   │                               order IDs, fill prices, trigger_log
    │   ├── result.json              ← final P&L + exit reason (written on close)
    │   ├── skipped.json             ← if gate rejected (with specific reason)
    │   └── reassessments/           ← append-only delta reviews
    │       ├── 001_transcript.json
    │       └── 002_benzinga_12345.json
    └── attribution/
        └── result.json              ← enriched with trade + reassessment + slippage data
```

### G. Configuration (all tunable, one config file)

```
# Account & Data
ACCOUNT_MODE = paper              # paper | live
DATA_MODE = delayed               # delayed | realtime

# Gate thresholds
CONFIDENCE_THRESHOLD = 75
MAGNITUDE_THRESHOLD = 3.0
MAX_POSITIONS = 2
SPREAD_MAX_PCT = 1.0              # absolute soft cap
SPREAD_EDGE_RATIO = 0.25          # soft max = 25% of expected edge
SPREAD_HARD_MAX_PCT = 2.0         # absolute hard cap
SPREAD_HARD_EDGE_RATIO = 0.40     # hard max = 40% of expected edge
SPREAD_DEFER_WINDOW_MIN = 10      # minutes after next open to retry
CHASE_MAX_CONSUMED_PCT = 70       # skip if >70% of predicted range already moved

# Sizing & Risk
DOLLAR_RISK_PER_TRADE = 500
ATR_MULTIPLIER = 2.0
MIN_STOP_PCT = 3.0
MAX_STOP_PCT = 15.0
# MAX_TOTAL_RISK_PCT deferred — redundant while MAX_POSITIONS=2 (aggregate risk = $500×2 = $1,000)
ACCOUNT_KILL_SWITCH_PCT = 15.0    # close ALL if account drops this much

# Monitoring — fixed thresholds
MAX_HOLD_SESSIONS = 1             # exit at Nth close after entry
GAP_FADE_PCT = 50                 # % of initial move given back → exit (already adaptive)
DURING_HOURS_CUTOFF = 14:00       # during-hours filing before this → same-day close; after → next close

# Monitoring — computed-at-entry thresholds (volatility-aware)
BENCHMARK_ATR_MULT = 2.0          # multiplier on sector ETF ATR
BENCHMARK_MIN_PCT = 1.0           # floor: never trigger below this %
BENCHMARK_MAX_PCT = 4.0           # ceiling: never require more than this %
BENCHMARK_EDGE_SHARE = 0.50       # threshold can't exceed 50% of edge

MACRO_ATR_MULT = 2.0              # multiplier on SPY ATR
MACRO_MIN_PCT = 1.0
MACRO_MAX_PCT = 4.0
MACRO_EDGE_SHARE = 0.50

REVERSAL_ATR_MULT = 0.5           # half of stock's daily ATR
REVERSAL_MOVE_SHARE = 0.30        # 30% of initial move

# Reassessment
REASSESS_COOLDOWN_SEC = 7200      # 2 hours between Benzinga reassessments
REASSESS_MAX_PER_TRADE = 3        # max total reassessments per trade
BENZINGA_WHITELIST = analyst_downgrade,analyst_upgrade,guidance_revision,sec_investigation,earnings_revision
```

### H. Deferred To Later Blocks (explicitly NOT finalized in Block 1)

These items are intentionally deferred so Block 1 stays focused on goals, boundaries, and definitions. They must be designed explicitly before implementation:

1. **Trigger handoff from prediction to trading**
   - How `earnings_trigger_daemon.py` / orchestrator notifies `trade_daemon.py`
   - Redis wake-up vs filesystem polling fallback
   - `prediction_id`-based idempotency during handoff

2. **Architecture and ownership boundaries**
   - Exact responsibilities of `earnings_trigger_daemon.py`, orchestrator, predictor, reassessment engine, and `trade_daemon.py`
   - Which component writes which file and when

3. **Trade lifecycle state machine**
   - Exact statuses such as `pending_entry`, `open`, `closing`, `closed`, `skipped`
   - Allowed transitions and restart-safe behavior

4. **Order choreography**
   - Parent entry + attached stop flow
   - Partial fills
   - Cancel/replace behavior
   - Fail-closed handling if stop confirmation fails

5. **Realtime monitoring mechanism**
   - How quote subscriptions are registered in realtime mode
   - Which thresholds are monitored in-memory on quote updates
   - How delayed mode falls back to polling

6. **Reassessment contract**
   - Exact trigger packet
   - Exact reassessment result schema
   - Cooldown, dedupe, and session-resume fallback behavior
   - **Future TODO**: the reassessment packet architecture (trigger.type + market_snapshot) should remain flexible enough to support price-event triggers (e.g., "macro dropped 3%, reassess thesis") in addition to text-event triggers. No architectural change needed — just a new trigger type class.

7. **File schemas**
   - Exact JSON fields for `trade/plan.json`, `trade/result.json`, `trade/skipped.json`, and `trade/reassessments/*.json`

8. **Startup recovery and reconciliation**
   - How `trade_daemon.py` rebuilds in-memory state from files
   - How it reconciles with IBKR positions, orders, and fills after restart

10. **Attribution skill rebuild**
    - The existing `earnings-attribution` skill was designed for historical analysis. It needs to be redone/extended to handle live trade data (P&L, slippage, exit reason, reassessment accuracy, monitor effectiveness).
    - This is a separate effort — the trade daemon only writes trade output files; attribution consumes them later.

9. **Upstream earnings trigger integration**
   - Borrow from `.claude/plans/EarningsTrigger.md`:
     - live 8-K detection
     - watch key / cutoff / recovery logic
     - filesystem-authoritative completion
     - leases to avoid duplicate work
   - Keep ownership split:
     - `earnings_trigger_daemon.py` detects fresh 8-K and runs predictor
     - `trade_daemon.py` starts only after `prediction/result.json` exists and no trade exists yet for that `prediction_id`

---

## Block 2: Architecture and Ownership

### 2A. Component Inventory

The system has 4 active components and 3 infrastructure services:

**Active components** (things that make decisions or produce output):

| # | Component | Status | Owns |
|---|---|---|---|
| 1 | `earnings_trigger_daemon.py` | EXISTS (planned in EarningsTrigger.md) | Detects fresh 8-K, runs orchestrator, produces prediction |
| 2 | `earnings-prediction` skill | EXISTS | Makes the initial thesis: direction, confidence, magnitude |
| 3 | `trade_daemon.py` | **NEW** | Entire trade lifecycle from prediction detection through close. Includes reassessment as an internal capability (not a separate service). |
| 4 | `earnings-attribution` skill | EXISTS | Post-trade learning (enriched with trade data) |

Note: the Reassessment Engine is a call path INSIDE trade_daemon.py, not a separate component. The daemon invokes it when transcript or whitelisted news arrives. Implementation (same predictor MODE=reassess or separate skill) decided in Block 3.

**Infrastructure services** (things that store data or execute orders):

| # | Service | Role | Used when |
|---|---|---|---|
| 5 | IBKR (broker) | Executes orders, enforces stops 24/7, provides market data | Always (hard dependency) |
| 6 | Neo4j | Company/sector data, transcripts, whitelisted Benzinga news | Gate (sector lookup), monitoring (transcript/news detection) |
| 7 | Redis | Daemon singleton lock + `trades:pending` fast-trigger queue | Startup (lock) + prediction detection (fast trigger). NOT needed during active trade monitoring. |

### 2B. Ownership Boundaries — Who Does What

```
┌─────────────────────────────────────────────────────────────┐
│ EARNINGS TRIGGER DAEMON (existing)                          │
│                                                             │
│ Responsibility:                                             │
│ - Watch trade_ready:entries in Redis                        │
│ - Detect fresh 8-K (hourly_stock IS NULL)                  │
│ - Run orchestrator → orchestrator runs predictor            │
│ - Ensure prediction/result.json is written                  │
│ - Push prediction_id to trades:pending Redis queue          │
│                                                             │
│ Does NOT: place trades, monitor positions, talk to IBKR     │
│ Writes: prediction/result.json, context_bundle.json         │
│         (via orchestrator/predictor, not directly)          │
└──────────────────────┬──────────────────────────────────────┘
                       │
          prediction/result.json on disk
          + Redis trades:pending notification
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ TRADE DAEMON (new) — SINGLE OWNER OF ALL TRADE STATE       │
│                                                             │
│ Responsibilities (in lifecycle order):                      │
│                                                             │
│ 1. DETECT: consume Redis trades:pending (fast path)         │
│    OR scan filesystem for result.json where NEITHER         │
│    plan.json NOR skipped.json exists for that prediction_id │
│    (fallback, every 30s, and on startup)                    │
│                                                             │
│ 2. FETCH MARKET DATA: on detection, fetch fresh ATR,        │
│    prices, account state, sector ETF mapping from Neo4j.    │
│    (No pre-fetch — daemon starts after result.json exists.) │
│                                                             │
│ 3. GATE: run fixed checks (confidence, magnitude, direction)│
│    + dynamic checks (spread, chase, capital, max positions) │
│    Fixed fail → skip permanently.                           │
│    Spread/liquidity fail → defer + retry until window       │
│    expires (re-run ALL checks on each retry).               │
│    Any other dynamic fail → skip permanently.               │
│                                                             │
│ 4. SIZE: calculate stop distance (ATR-based, clamped),      │
│    calculate shares (dollar-risk / stop_distance).          │
│    Uses FRESH prices at execution time.                     │
│                                                             │
│ 5. EXECUTE: place bracket order on IBKR (entry + stop).    │
│    If bracket unavailable → fail-closed choreography.       │
│    Record fill prices, order IDs, reference snapshot.       │
│    Save predictor_session_id for reassessment resume.       │
│                                                             │
│ 6. MONITOR: check thresholds continuously                   │
│    Realtime mode: IBKR streaming → callback on each quote   │
│    Delayed mode: poll every POLL_INTERVAL_SEC               │
│    Checks: stop fired?, benchmark stress (sector ETF)?,     │
│    SPY stress?, gap fade?, max hold (market close)?         │
│                                                             │
│ 7. REASSESSMENT (internal capability, not separate service):│
│    Consume Redis event from transcript/news ingestion       │
│    pipeline (fast path) OR Neo4j backstop scan (fallback)   │
│    → load full artifact from Neo4j by ID                    │
│    → apply dedupe/cooldown                                  │
│    → resume predictor session (if fails: no_change+no_esc)  │
│    → act on confirmed/unchanged/invalidated deterministically│
│                                                             │
│ 8. EXIT: close position (any path: stop, threshold,         │
│    reassessment invalidation, time exit). Cancel remaining  │
│    orders.                                                  │
│                                                             │
│ 9. RECORD: write trade/result.json with P&L, exit reason,  │
│    slippage, trigger log, reassessment outcomes.            │
│                                                             │
│ 10. RECONCILE: on startup and periodically, verify IBKR     │
│     positions match plan.json state. Detect externally      │
│     closed positions (stop fired while daemon was down).    │
│                                                             │
│ Does NOT: run predictions, write prediction/result.json,    │
│           modify prediction files, invoke attribution       │
│           inline, talk to Benzinga API directly              │
│                                                             │
│ Writes: trade/plan.json (live state, sole owner)            │
│         trade/result.json (on close)                        │
│         trade/skipped.json (gate rejection)                 │
│         trade/reassessments/*.json (reassessment outputs)   │
│ Reads:  prediction/result.json (signal)                     │
│         prediction/context_bundle.json (fallback context)   │
│         Neo4j (sector mapping, transcript/news by ID)       │
│         Redis (transcript/news events from ingestion pipe)  │
│         IBKR direct API via ib_insync (prices, positions,   │
│              orders, account, streaming quotes)              │
└──────────────────────┬──────────────────────────────────────┘
                       │
              (after trade closes)
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ ATTRIBUTION (existing skill, NEEDS REDO for trade support)   │
│                                                             │
│ Responsibility:                                             │
│ - Post-trade analysis: was prediction correct?              │
│ - Enriched with: P&L, exit reason, slippage, reassessment  │
│   accuracy, monitor effectiveness                           │
│ - Runs on next trade_ready / historical bootstrap cycle     │
│ - NOT invoked inline by trade_daemon (avoids competing for  │
│   tokens/resources with live predictions)                   │
│ - Historical attribution handled upstream by earnings       │
│   trigger/orchestrator flow before next live prediction     │
│                                                             │
│ Reads: prediction/result.json, trade/result.json,           │
│        trade/reassessments/*.json                           │
│ Writes: attribution/result.json                             │
│ Feeds: U1 loop → improves next prediction                   │
└─────────────────────────────────────────────────────────────┘
```

### 2C. Communication Interfaces — How Components Talk

| From | To | What | Mechanism |
|---|---|---|---|
| Earnings trigger → Trade daemon | "prediction ready" | Redis `trades:pending` queue (fast) + filesystem scan (fallback) |
| Trade daemon → IBKR | orders, account, positions | IBKR API (`ib_insync` / TWS Gateway) |
| Transcript/news ingestion → Trade daemon | "reassessment candidate" | Redis event (fast) + Neo4j backstop scan (fallback). Requires upstream change: ingestion pipeline pushes Redis event on whitelisted ingest. |
| Trade daemon → IBKR | orders, account, positions, prices | Direct IBKR API (`ib_insync` / TWS Gateway). NOT via MCP — daemon needs streaming callbacks, order events, reconnection. MCP remains as operator/debug tool. |
| Trade daemon → Neo4j | sector lookup, load transcript/news artifact by ID | Neo4j Bolt driver |
| Trade daemon → Claude API | reassessment (internal capability) | Resume predictor session. If fails: no_change + no_escalation (no second LLM call at launch). Daemon writes result to reassessments/. |
| Trade daemon → Attribution | trade results | Filesystem only: trade/result.json + trade/reassessments/ |
| IBKR → Trade daemon (realtime) | quote updates | IBKR streaming subscription → threshold-check callback |
| IBKR → Trade daemon (delayed) | price snapshots | Daemon polls IBKR API every POLL_INTERVAL_SEC |

**Truth hierarchy** — each kind of data has exactly one authoritative source:

| Data | Authoritative source |
|---|---|
| Prediction/trade state | Filesystem (result.json, plan.json, skipped.json) |
| Transcript/news existence | Neo4j (ingested artifacts) |
| Broker execution state (positions, orders, fills) | IBKR |
| Fast wake-up signals | Redis (trigger only, never truth) |

Components may READ upstream filesystem artifacts (trade daemon reads prediction files, attribution reads trade files), but each file has exactly ONE writer.

### 2D. Trade Lifecycle State Machine

```
  prediction/result.json written
           │
           ▼
      ┌─────────┐
      │ DETECTED │ ← daemon found prediction without trade files
      └────┬─────┘
           │ run gate
           ▼
      ┌──────────────┐     fixed check fails
      │ GATE_CHECKING │ ──────────────────────┐
      └───────┬──────┘                        │
              │                               ▼
              │ SPREAD-ONLY failure      ┌─────────┐
              │ (other checks pass)      │ DEFERRED │ ← spread-only liquidity retry
              ├─────────────────────────▶└────┬─────┘   persists deferred_at + retry_deadline
              │                               │ retry loop (ALL checks re-run)
              │ other dynamic fail → SKIP     │ must NOT broaden to other gate failures
              │         ┌─────────────────────┤
              │         │ window expired       │ checks pass
              │         ▼                      │
              │    ┌─────────┐                 │
              │    │ SKIPPED  │ ← TERMINAL for this prediction_id
              │    └─────────┘   (writes skipped.json, never retried)
              │                                │
              │                                │
              │ all checks pass ◄──────────────┘
              ▼
      ┌──────────┐
      │ ENTERING │ ← placing bracket order on IBKR
      └────┬─────┘
           │ fill confirmed + stop confirmed
           ▼
      ┌──────┐
      │ OPEN │ ← position live, monitoring active
      └──┬───┘
         │
         │ ┌──────────────────────────────────────────┐
         │ │ MONITORING LOOP                           │
         │ │                                           │
         │ │ Continuous checks (streaming or polling):  │
         │ │ - stop fired?                             │
         │ │ - benchmark stress?                       │
         │ │ - SPY stress?                             │
         │ │ - gap fade?                               │
         │ │ - max hold (market close)?                │
         │ │                                           │
         │ │ Event checks (periodic scan):             │
         │ │ - transcript ingested?                    │
         │ │ - whitelisted Benzinga article?           │
         │ │   → invoke Reassessment Engine            │
         │ │   → act on confirmed/unchanged/invalidated│
         │ │                                           │
         │ │ Reconciliation (periodic):                │
         │ │ - IBKR positions match plan.json?         │
         │ └──────────────────────────────────────────┘
         │
         │ any exit condition met
         ▼
      ┌─────────┐
      │ EXITING │ ← closing position, cancelling remaining orders
      └────┬────┘
           │ fill confirmed
           ▼
      ┌────────┐
      │ CLOSED │ ← writes trade/result.json, updates plan.json
      └────────┘
           │
           ▼
      (attribution picks up later via trade_ready cycle)
```

**State ownership**: all state transitions are owned exclusively by `trade_daemon.py`. No other component changes trade state.

**Restart safety**: on daemon restart:
- Scan filesystem for `trade/plan.json` files (these only exist for trades that reached ENTERING or later)
- ENTERING → reconcile with IBKR (did the order fill? is the stop active?)
- OPEN → resume monitoring (verify position + stop still exist in IBKR)
- EXITING → reconcile with IBKR (did the exit fill?)
- CLOSED/SKIPPED → nothing to do
- Pre-entry states (DETECTED, GATE_CHECKING) have no persisted state — daemon re-discovers these via filesystem scan (predictions without plan.json or skipped.json).
- DEFERRED state MUST persist at least: `deferred_at` timestamp and `retry_deadline`, so that a daemon restart does not reset the retry window and keep stale signals alive. DEFERRED is spread-only — must not be broadened to other gate failures. Exact file format designed in Block 3/5.

**Upstream contract (PLANNED, not yet coded)**: the EarningsTrigger.md v12 plan describes a two-phase system where historical attribution/learner completes before live prediction fires. However, the current codebase (`scripts/earnings_trigger.py`) is a simple Redis listener — it does NOT yet enforce historical-first gating, live/historical modes, or deferred learner logic. The plans are ahead of the code.

**Trade daemon's stance**: operate on ANY valid prediction/result.json without assuming the upstream historical/U1 contract is enforced. The gate (confidence, magnitude) filters weak signals regardless of whether U1 feedback was available. When the upstream pipeline is fully implemented, prediction quality improves automatically — the trade daemon benefits without any changes on its side.

### 2E. File Ownership Matrix

| File | Written by | When | Modified by | Read by |
|---|---|---|---|---|
| `prediction/result.json` | Orchestrator/Predictor | After prediction completes | NEVER modified | Trade daemon, Attribution |
| `prediction/context_bundle.json` | Orchestrator | After bundle assembly | NEVER modified | Reassessment Engine (fallback) |
| `trade/plan.json` | Trade daemon | At entry (created), during trade (updated) | Trade daemon ONLY | Trade daemon (on restart), Attribution |
| `trade/result.json` | Trade daemon | On trade close | NEVER modified after write | Attribution |
| `trade/skipped.json` | Trade daemon | When gate permanently fails | NEVER modified after write | Attribution (for learning) |
| `trade/reassessments/*.json` | Trade daemon | After each reassessment | NEVER modified after write | Trade daemon (restart), Attribution |

**Rule**: every file has exactly ONE writer. No file is written by two components. This prevents race conditions and makes debugging trivial.

### 2F. Infrastructure Dependencies

| Dependency | Required for | When needed | What if down? |
|---|---|---|---|
| IBKR Gateway | Orders, market data, positions | Always (hard dependency) | Cannot trade. Daemon waits/retries. Existing positions protected by broker-native stops. |
| Neo4j | Sector lookup, transcript + news detection | Gate (sector mapping), monitoring (event triggers) | Cannot map sector → use SPY-only fallback. Cannot detect transcript/news → miss reassessment, fail-safe holds. |
| Redis | Singleton lock, fast trigger, transcript/news events | Startup + prediction detection + reassessment event delivery | Lock: daemon refuses to start (prevents duplicates). If Redis goes down during operation: active trade monitoring continues (no Redis dependency), but new trade acceptance stops (safer than degraded filesystem fallback). Transcript/news fast events degrade to Neo4j backstop scan. |
| Claude API | Reassessment (internal to daemon) | Only when transcript/news event fires | Reassessment fails. Fail-safe: no_change + no_escalation. |

**Principle**: every infrastructure failure degrades to a MORE conservative posture, never a more aggressive one. The only hard dependency is IBKR Gateway (can't trade without a broker). Redis going down during active monitoring has ZERO impact on price monitoring or trade safety; transcript/news reassessment events would be delayed until the Neo4j backstop scan catches them.

---

---

## Block 3: Trading Rules and Monitoring Template

This is where P&L behavior lives. One template for all trades (no FAST/CONTESTED profiles).

### 3A. Gate — Detailed Decision Flow

**One conservative edge input used everywhere**:
`edge = low_end(expected_move_range)` — e.g., prediction [5, 8] → edge = 5%. Used consistently in the gate magnitude check AND in the three-tier spread policy. Never midpoint, never high end.

```
prediction/result.json detected (via Redis or filesystem scan)
         │
         ▼
    FIXED CHECKS (from prediction, won't change):
    ├─ direction == long?                    NO → skip permanently
    ├─ confidence ≥ CONFIDENCE_THRESHOLD?    NO → skip permanently
    └─ edge ≥ MAGNITUDE_THRESHOLD?           NO → skip permanently
        (edge = low end of expected_move_range)
         │ all pass
         ▼
    FETCH MARKET DATA (two categories):

    Stable/slow-changing (can be cached briefly):
    ├─ ATR_14 (IBKR historical or Polygon — doesn't change minute to minute)
    ├─ sector ETF mapping (Neo4j — Company → sector → ETF)
    └─ pre-earnings close price (historical, fixed for this event)

    Live-sensitive (must be fresh at decision time):
    ├─ current stock price + bid-ask spread (IBKR)
    ├─ account equity + free cash + open positions (IBKR)
    └─ sector ETF + SPY prices (IBKR)
         │
         ▼
    DYNAMIC CHECKS (market-dependent):
    ├─ spread: three-tier policy (D8a, using same edge value)
    │   ├─ trade_now tier → continue
    │   ├─ defer tier → DEFERRED state (spread-only, temporary)
    │   │   persist deferred_at + retry_deadline
    │   │   retry until next open + SPREAD_DEFER_WINDOW_MIN
    │   │   on retry: re-run ALL dynamic checks
    │   └─ skip tier → skip permanently
    ├─ chase: stock moved > CHASE_MAX_CONSUMED_PCT of edge? → skip permanently
    ├─ capital: account has enough free cash? → skip permanently
    └─ positions: under MAX_POSITIONS? → skip permanently
         │
         │ ONLY spread triggers DEFER. All other dynamic failures = permanent SKIP.
         │ all pass
         ▼
    PROCEED TO SIZING
```

### 3B. Sizing — Dollar-Risk Formula

```
Step 1: Determine executable entry price
  Regular hours: current_ask (or last trade if ask unavailable)
  Extended hours: current_ask + LIMIT_BUFFER_PCT
  This is the price we expect to PAY, not the midpoint.

Step 2: Calculate stop distance
  stop_distance = clamp(ATR_MULTIPLIER × ATR_14,
                        MIN_STOP_PCT × entry_price,
                        MAX_STOP_PCT × entry_price)

Step 3: Calculate per-share risk (includes buffer for slippage + fees)
  per_share_risk = stop_distance + EXECUTION_BUFFER_PER_SHARE
  This keeps actual max loss closer to the intended budget.

Step 4: Calculate shares from risk budget
  shares = floor(DOLLAR_RISK_PER_TRADE / per_share_risk)

Step 5: Verify position value fits account
  position_value = shares × entry_price
  if position_value > account_free_cash → reduce shares

Step 6: Terminal small-size check
  if shares < MIN_SHARES (e.g., 1) → skip trade (position too small to matter)

Step 7: Calculate stop price
  stop_price = entry_price - stop_distance  (for long trades)
```

Example: stock ask at $185.20, ATR=$4.50, risk budget=$500, execution buffer=$0.30/share
- entry_price = $185.20 (expected fill)
- stop_distance = clamp(2.0 × $4.50, 3% × $185.20, 15% × $185.20) = clamp($9.00, $5.56, $27.78) = $9.00
- per_share_risk = $9.00 + $0.30 = $9.30
- shares = floor($500 / $9.30) = 53
- position = 53 × $185.20 = $9,815.60
- stop_price = $185.20 - $9.00 = $176.20
- max loss = 53 × $9.30 = $492.90 (within $500 budget including slippage buffer)

### 3C. Execution — Order Placement

```
Step 1: Create trade/plan.json with status="entering"
  Write immediately before placing any orders.
  Contains: prediction_id, ticker, direction, intended_shares, stop_price.
  This ensures a restart during order placement can detect the in-progress entry.

Step 2: Determine order type
  Default for ALL sessions: marketable limit
    (limit = current ask + LIMIT_BUFFER_PCT of price)
  This caps worst-case fill regardless of session or spread tier.
  No regular-hours market-order path — consistency with exit policy.

Step 3: Place orders on IBKR (bracket preferred, fail-closed fallback)

  PREFERRED: linked bracket order
    Parent: BUY {shares} {ticker} @ {order_type}
    Child:  SELL {shares} {ticker} @ STOP {stop_price}
    Both placed atomically. If entry fills, stop is automatically active.

  FALLBACK (if bracket unavailable for this order/session path):
    a. Place entry order → wait for fill confirmation
    b. Immediately place stop order for filled quantity
    c. If stop not confirmed → FLATTEN immediately (fail-closed)

Step 4: Handle partial fills
  If entry partially fills (got 30 of 55 shares):
  - Stop quantity must match FILLED shares (not intended shares)
  - Trade remains in status="entering" until filled quantity is protected
  - If remaining shares don't fill within a timeout → cancel unfilled portion
  - Proceed with the partially filled quantity

Step 5: Verify and record
  Entry fill confirmed? → record fill_price, fill_time, order_id, actual_shares
  Stop confirmed active for correct quantity? → record stop_order_id
  If stop NOT confirmed for filled shares → FLATTEN immediately (fail-closed)

Step 6: Transition to OPEN
  Only after BOTH entry fill AND stop active for correct quantity:
  - Update plan.json: status="open"
  - Record reference_snapshot: stock_price, sector_etf_price, spy_price, timestamp
  - Record predictor_session_id (for reassessment resume)
  - Initialize trigger_log: []
  - Begin monitoring
```

### 3D. Monitoring — One Template, All Trades

Once the trade is OPEN, the daemon monitors continuously. Thresholds are split into two groups:

**FIXED THRESHOLDS** (from config, same for every trade):
- Account kill-switch: `ACCOUNT_KILL_SWITCH_PCT`
- Max hold: `MAX_HOLD_SESSIONS`
- Gap fade: `GAP_FADE_PCT` (already normalized by initial move, so inherently adaptive)

**COMPUTED THRESHOLDS** (calculated once at entry, persisted in plan.json, never recalculated):

```
edge = low_end(expected_move_range)

Benchmark stress:
  sector_atr_pct = ATR_14(sector_etf) / sector_etf_price × 100
  benchmark_threshold = min(
    clamp(BENCHMARK_ATR_MULT × sector_atr_pct, BENCHMARK_MIN_PCT, BENCHMARK_MAX_PCT),
    BENCHMARK_EDGE_SHARE × edge
  )

Macro stress:
  spy_atr_pct = ATR_14(SPY) / spy_price × 100
  macro_threshold = min(
    clamp(MACRO_ATR_MULT × spy_atr_pct, MACRO_MIN_PCT, MACRO_MAX_PCT),
    MACRO_EDGE_SHARE × edge
  )

Session reversal:
  reversal_threshold = max(
    stock_atr_pct × REVERSAL_ATR_MULT,
    initial_move_pct × REVERSAL_MOVE_SHARE
  )
  (Exit at open+5 only if stock is against us by MORE than this threshold.
   Not just one tick red — a meaningful move relative to volatility.)
```

All computed thresholds stored in plan.json at entry. Monitoring loop compares current prices against these locked values. Adaptive to market conditions at entry time, deterministic afterward.

**MONITORING CHECKS:**

| Check | Condition | Action | When checked |
|---|---|---|---|
| **Stop fired** | IBKR position closed externally | Record exit, write result.json | Every cycle |
| **Account kill-switch** | account_equity < starting × (1 - ACCOUNT_KILL_SWITCH_PCT/100) | Close ALL positions immediately | Every cycle |
| **Benchmark stress** | sector_etf down > computed benchmark_threshold from reference | EXIT this trade | Every cycle (sector/SPY trade in extended hours too) |
| **Macro stress** | SPY down > computed macro_threshold from reference | EXIT this trade | Every cycle |
| **Gap fade** | stock gave back > GAP_FADE_PCT of initial_move | EXIT this trade | Post/pre-market filings: after next open + 30min. During-hours filings: entry + 30min. |
| **Session reversal** | stock against us by > computed reversal_threshold | EXIT this trade | Post/pre-market filings: next open + 5min. During-hours filings: NOT applicable (already in-session, no overnight gap to reverse). |
| **Max hold** | current time ≥ Nth market close (MAX_HOLD_SESSIONS) | EXIT this trade | Every cycle |

Notes:
- "reference" = reference_snapshot captured at entry
- "initial_move" = fill_price - pre_earnings_close
- Gap fade timing: post/pre-market filings → next open+30min. During-hours filings → entry+30min.
- Session reversal: post/pre-market filings → next open+5min. During-hours filings → N/A (no overnight gap).
- Benchmark and macro stress: checked continuously in ALL sessions including extended hours.

**EVENT CHECKS** (text-event triggers):

| Trigger | Detection | Action | Guardrails |
|---|---|---|---|
| **Transcript ingested** | Redis event from ingestion pipeline + Neo4j backstop scan | Invoke Reassessment Engine → act on result | Max 1 per trade, matched by prediction_id |
| **Whitelisted Benzinga news** | Redis event from ingestion pipeline + Neo4j backstop scan | Invoke Reassessment Engine → act on result | Whitelist categories only, 2h cooldown, deduped by article ID, max per trade |

**Every check is logged** in plan.json `trigger_log` array:
```json
{"timestamp": "2026-04-07T08:00:30", "check": "benchmark_stress",
 "value": -1.2, "threshold": -2.0, "result": "hold"}
```

### 3E. Reassessment — Internal Daemon Capability

When a text-event trigger fires:

```
Step 1: Load the evidence (compact)
  Transcript → query Neo4j for structured Q&A + prepared remarks (not raw transcript)
  Benzinga → query Neo4j for the article by ID (naturally compact)

Step 2: Build reassessment message
  Even on session resume, the daemon sends a bounded, auditable message containing:
  - the new evidence (compact, from step 1)
  - the original thesis summary (rationale_summary + key_drivers from prediction/result.json)
  - current trade state summary (entry_price, current_pnl_pct, time_in_trade, active exit rules)
  This ensures the reassessment is always reproducible and auditable.

Step 3: Try to resume predictor session
  If predictor_session_id exists in plan.json:
    → SendMessage(to: session_id, reassessment_message)
    → Parse structured response: thesis_status, confidence, delta_summary

  If predictor_session_id is MISSING or session resume FAILS (expired, compacted, API error):
    → no_change + no_escalation (safe default)
    → NO second fallback LLM call at launch
    → Log the failure in reassessments/

Step 4: Save reassessment result
  Write to trade/reassessments/{seq}_{trigger_type}.json:
  {
    "trigger_type": "transcript",
    "trigger_id": "AAPL_2026-04-06_transcript",
    "thesis_status": "confirmed",
    "confidence": 85,
    "delta_summary": "Transcript reinforced demand durability...",
    "timestamp": "2026-04-06T18:45:00"
  }

Step 5: Daemon acts deterministically
  confirmed   → HOLD (log only)
  unchanged   → HOLD (log only)
  invalidated → EXIT (close position)
  LLM failure → no_change + no_escalation (hold, don't add, don't extend)
```

### 3F. Exit — Closing the Position

Any exit path follows the same sequence:

```
Step 1: Determine exit reason
  stop_fired | benchmark_stress | macro_stress | gap_fade |
  session_reversal | max_hold | reassessment_invalidated | account_killswitch

Step 2: Update plan.json status → "exiting"
  Persisted BEFORE placing exit order. Restart-safe: if daemon crashes
  mid-exit, it resumes from "exiting" and reconciles with IBKR.

Step 3: Place exit order (if position still open)
  Default: marketable limit (caps worst-case fill in ALL sessions)
  Exception: account kill-switch → market order (urgency overrides fill quality)
  If stop already fired → no order needed, just record

Step 4: Cancel remaining orders
  Cancel the bracket stop if still active (position closed by our exit, not by stop)

Step 5: Record fill
  exit_price, exit_time, exit_order_id

Step 6: Write trade/result.json
  {
    "prediction_id": "...",
    "ticker": "AAPL",
    "direction": "long",
    "entry_price": 185.23,
    "exit_price": 192.45,
    "shares": 55,
    "pnl_dollars": 396.10,
    "pnl_pct": 3.90,
    "slippage_entry": 0.12,
    "slippage_exit": 0.08,
    "duration_hours": 23.6,
    "exit_reason": "max_hold",
    "monitors_triggered": ["benchmark_stress:hold", "session_reversal:hold"],
    "reassessments": ["001_transcript:confirmed"],
    "reference_snapshot": {...},
    "data_mode": "delayed",
    "account_mode": "paper"
  }

Step 7: Update plan.json status → "closed"
  Only after exit fill is confirmed AND result.json is written.
```

### 3G. Market Session Handling

53% of 8-K filings are post-market, 45% pre-market, 2% during hours.

| Filing time | Entry window | Monitoring schedule | Max hold exit |
|---|---|---|---|
| **Post-market** (after 4 PM) | Enter in after-hours (extended) | Benchmark/macro: continuous. Gap fade: at next open+30min. Session reversal: at open+5min. | Next market close (~24h) |
| **Pre-market** (before 9:30 AM) | Enter in pre-market (extended) | Benchmark/macro: continuous. Gap fade: at open+30min. Session reversal: at open+5min. | Same-day close (~8.5h) |
| **During hours** (9:30-4:00) | Enter immediately (marketable limit) | Benchmark/macro: immediately. Gap fade: entry+30min. Session reversal: N/A (no overnight gap). | If filed before DURING_HOURS_CUTOFF (e.g., 2:00 PM): same-day close. If filed after: next-day close. Deterministic cutoff, configurable. |

The daemon determines filing session from the 8-K timestamp. This affects:
- Order type (extended hours → marketable limit)
- Monitoring schedule (when gap fade / reversal checks activate)
- Max hold target (which close to exit at)

### 3H. Skip Logging

Every skipped prediction produces `trade/skipped.json`:

```json
{
  "prediction_id": "AAPL_Q1_FY2026_20260406T1603",
  "skipped_at": "2026-04-06T16:15:00",
  "reason": "spread_skip",
  "details": {
    "spread_pct": 2.3,
    "edge_pct": 5.0,
    "hard_max": 2.0,
    "message": "Spread exceeds hard max (2.3% > 2.0%). Edge too expensive to capture."
  },
  "gate_snapshot": {
    "confidence": 82,
    "magnitude": 6.5,
    "direction": "long",
    "account_free_cash": 45000,
    "positions_open": 1,
    "stock_price": 185.23,
    "spread_pct": 2.3
  }
}
```

This data feeds attribution — "would this have been profitable if we traded?" helps calibrate gate thresholds.

---

## Block 4: State and File Schemas

Every JSON schema below serves exactly one purpose. Fields are included only if needed for trade execution, restart recovery, attribution, or debugging. No speculative fields.

All timestamps: ISO 8601 with timezone. All prices: USD dollars (not cents). All percentages: numeric (2.5 means 2.5%, not 0.025).

### 4A. prediction/result.json — Fields Required by Trade Daemon

This file is OWNED by the prediction pipeline (orchestrator/predictor). The trade daemon only READS it. Shown here are the minimum fields the daemon requires — the prediction pipeline may include additional fields for its own purposes.

```json
{
  "prediction_id": "AAPL_Q1_FY2026_20260406T1603",
  "ticker": "AAPL",
  "quarter_label": "Q1_FY2026",
  "filed_8k": "2026-04-06T16:03:00-04:00",
  "direction": "long",
  "confidence": 82,
  "expected_move_range": [5, 8],
  "key_drivers": [
    {"driver": "EPS beat 15%", "direction": "long"},
    {"driver": "Guidance raised FY2026", "direction": "long"}
  ],
  "rationale_summary": "Strong beat with raised guidance in calm macro environment.",
  "model_version": "claude-opus-4-6",
  "prompt_version": "earnings-prediction-v3.2",
  "predicted_at": "2026-04-06T16:13:00-04:00",
  "predictor_session_id": "session_abc123"
}
```

| Field | Used by daemon for | Required? |
|---|---|---|
| prediction_id | Idempotency (don't trade same prediction twice) | Yes |
| ticker | IBKR order placement, Neo4j sector lookup | Yes |
| quarter_label | File path construction, attribution linking | Yes |
| direction | Gate (long-only filter) + order direction | Yes |
| confidence | Gate (threshold check) | Yes |
| expected_move_range | Gate (magnitude check), spread policy (edge calculation) | Yes |
| key_drivers | Reassessment input (original thesis context) | Yes |
| rationale_summary | Reassessment input (original thesis context) | Yes |
| model_version | Logged in trade files for attribution | Yes |
| prompt_version | Logged in trade files for attribution | Yes |
| filed_8k | Market session determination (post/pre/during) | Yes |
| predicted_at | Latency tracking (filed_8k → predicted_at → trade entry) | Yes |
| predictor_session_id | Reassessment resume (SendMessage to original session) | Optional — absent = safe fallback (no_change + no_escalation) |

### 4B. trade/plan.json — Live Trade State (Daemon-Owned)

Single most important file. Created when trade first needs persistent state (DEFERRED or ENTERING). Updated throughout lifecycle. Only `trade_daemon.py` writes to this file.

**Status = "deferred"** (spread too wide, retrying):
```json
{
  "schema_version": "trade_plan.v1",
  "prediction_id": "AAPL_Q1_FY2026_20260406T1603",
  "ticker": "AAPL",
  "direction": "long",
  "status": "deferred",
  "deferred_at": "2026-04-06T16:15:00-04:00",
  "retry_deadline": "2026-04-07T10:00:00-04:00",
  "defer_reason": "spread_too_wide",
  "defer_details": {
    "spread_pct": 1.3,
    "soft_max": 1.0,
    "hard_max": 1.8,
    "edge_pct": 5.0
  },
  "created_at": "2026-04-06T16:15:00-04:00",
  "updated_at": "2026-04-06T16:15:00-04:00"
}
```

**Status = "entering"** (placing bracket order):
```json
{
  "schema_version": "trade_plan.v1",
  "prediction_id": "AAPL_Q1_FY2026_20260406T1603",
  "ticker": "AAPL",
  "direction": "long",
  "status": "entering",
  "intended_shares": 53,
  "stop_price": 176.20,
  "entry_order_id": "IBKR_12345",
  "stop_order_id": "IBKR_12346",
  "created_at": "2026-04-06T16:15:00-04:00",
  "updated_at": "2026-04-06T16:15:30-04:00"
}
```

**Status = "open"** (position live, monitoring active — full state):
```json
{
  "schema_version": "trade_plan.v1",
  "prediction_id": "AAPL_Q1_FY2026_20260406T1603",
  "ticker": "AAPL",
  "direction": "long",
  "status": "open",

  "entry": {
    "fill_price": 185.20,
    "fill_time": "2026-04-06T16:15:45-04:00",
    "shares": 53,
    "order_id": "IBKR_12345",
    "order_type": "marketable_limit",
    "limit_price": 185.50
  },

  "stop": {
    "stop_price": 176.20,
    "order_id": "IBKR_12346",
    "status": "active"
  },

  "reference_snapshot": {
    "stock_price": 185.20,
    "pre_earnings_close": 178.50,
    "initial_move_pct": 3.75,
    "sector_etf": "XLK",
    "sector_etf_price": 215.30,
    "spy_price": 562.10,
    "timestamp": "2026-04-06T16:15:45-04:00"
  },

  "computed_thresholds": {
    "benchmark_threshold_pct": 2.5,
    "macro_threshold_pct": 2.0,
    "reversal_threshold_pct": 1.8
  },

  "monitoring_schedule": {
    "gap_fade_check_at": "2026-04-07T10:00:00-04:00",
    "session_reversal_check_at": "2026-04-07T09:35:00-04:00",
    "max_hold_exit_at": "2026-04-07T16:00:00-04:00",
    "filing_session": "post_market"
  },

  "predictor_session_id": "session_abc123",
  "reassessment_count": 0,
  "last_reconciled_at": "2026-04-06T16:16:00-04:00",

  "trigger_log": [
    {
      "timestamp": "2026-04-07T08:00:30-04:00",
      "check": "benchmark_stress",
      "current_value": -0.8,
      "threshold": -2.5,
      "result": "hold"
    }
  ],

  "edge_pct": 5.0,
  "per_share_risk": 9.30,
  "dollar_risk_budget": 500,
  "account_mode": "paper",
  "data_mode": "delayed",

  "created_at": "2026-04-06T16:15:00-04:00",
  "updated_at": "2026-04-07T08:00:30-04:00"
}
```

**Status = "exiting"** (closing position):
Adds to above:
```json
{
  "status": "exiting",
  "exit_reason": "max_hold",
  "exit_order_id": "IBKR_12350",
  "exit_initiated_at": "2026-04-07T15:59:00-04:00"
}
```

**Status = "closed"** (done):
Adds to above:
```json
{
  "status": "closed",
  "exit": {
    "fill_price": 192.45,
    "fill_time": "2026-04-07T16:00:15-04:00",
    "order_id": "IBKR_12350"
  },
  "closed_at": "2026-04-07T16:00:30-04:00"
}
```

**Key design decisions:**
- plan.json is created at DEFERRED or ENTERING (whichever comes first), not later
- On restart: status tells daemon exactly where to resume
- computed_thresholds calculated once at OPEN, never recalculated
- monitoring_schedule calculated once at OPEN based on filing_session
- trigger_log is append-only within plan.json (not a separate file)
- exit details added incrementally (exiting → closed), not replaced

### 4C. trade/result.json — Final Trade Record

Written ONCE when trade closes. Never modified. The authoritative P&L record for attribution.

```json
{
  "schema_version": "trade_result.v1",
  "prediction_id": "AAPL_Q1_FY2026_20260406T1603",
  "ticker": "AAPL",
  "direction": "long",

  "entry_price": 185.20,
  "exit_price": 192.45,
  "shares": 53,

  "pnl_dollars": 384.25,
  "pnl_pct": 3.91,
  "duration_hours": 23.75,

  "slippage_entry": 0.12,
  "slippage_exit": 0.08,
  "total_slippage": 0.20,

  "exit_reason": "max_hold",
  "exit_initiated_at": "2026-04-07T15:59:00-04:00",
  "exit_filled_at": "2026-04-07T16:00:15-04:00",

  "entry_filled_at": "2026-04-06T16:15:45-04:00",
  "filed_8k_at": "2026-04-06T16:03:00-04:00",
  "predicted_at": "2026-04-06T16:13:00-04:00",
  "entry_latency_sec": 765,

  "prediction_confidence": 82,
  "prediction_edge_pct": 5.0,
  "prediction_move_range": [5, 8],

  "reference_snapshot": {
    "stock_price": 185.20,
    "pre_earnings_close": 178.50,
    "initial_move_pct": 3.75,
    "sector_etf": "XLK",
    "sector_etf_price": 215.30,
    "spy_price": 562.10
  },

  "computed_thresholds": {
    "benchmark_threshold_pct": 2.5,
    "macro_threshold_pct": 2.0,
    "reversal_threshold_pct": 1.8
  },

  "monitors_triggered": [
    {"check": "benchmark_stress", "result": "hold", "count": 3},
    {"check": "gap_fade", "result": "hold", "count": 1},
    {"check": "max_hold", "result": "exit", "count": 1}
  ],

  "reassessments": [
    {"sequence": 1, "type": "transcript", "thesis_status": "confirmed", "confidence": 85}
  ],

  "filing_session": "post_market",
  "account_mode": "paper",
  "data_mode": "delayed",
  "model_version": "claude-opus-4-6",
  "prompt_version": "earnings-prediction-v3.2"
}
```

| Field group | Purpose |
|---|---|
| P&L (pnl_dollars, pnl_pct) | Primary metric for attribution |
| Slippage (entry, exit, total) | Measures execution quality |
| Latency (entry_latency_sec) | Time from 8-K filing to trade entry |
| Monitors triggered | Which checks fired, how many times, what results |
| Reassessments | Thesis status after each reassessment |
| Reference + thresholds | Reproduces the monitoring context for debugging |
| Mode flags | Distinguishes paper/delayed from live/realtime results |

### 4D. trade/skipped.json — Gate Rejection Record

Written when gate permanently fails. Never modified.

```json
{
  "schema_version": "trade_skipped.v1",
  "prediction_id": "AAPL_Q1_FY2026_20260406T1603",
  "ticker": "AAPL",
  "skipped_at": "2026-04-06T16:15:00-04:00",

  "reason": "spread_skip",
  "reason_detail": "Spread 2.3% exceeds hard max 2.0% (edge 5.0%). Friction exceeds opportunity.",

  "gate_snapshot": {
    "direction": "long",
    "confidence": 82,
    "edge_pct": 5.0,
    "spread_pct": 2.3,
    "spread_soft_max": 1.25,
    "spread_hard_max": 2.0,
    "stock_price": 185.23,
    "chase_consumed_pct": 45,
    "positions_open": 1,
    "account_free_cash": 45000
  },

  "was_deferred": false,
  "deferred_retries": 0,
  "account_mode": "paper",
  "data_mode": "delayed"
}
```

Possible `reason` values: `confidence_below_threshold`, `magnitude_below_threshold`, `direction_short`, `spread_skip`, `spread_defer_expired`, `chase_exceeded`, `max_positions`, `insufficient_capital`, `shares_too_small`, `entry_rejected`, `entry_timeout`, `entry_recovery_cancelled`. Exit-specific reasons (in result.json, not skipped.json): `stop_fired`, `benchmark_stress`, `macro_stress`, `gap_fade`, `session_reversal`, `max_hold`, `reassessment_invalidated`, `account_killswitch`, `stop_placement_failed`, `stop_repair_failed`.

### 4E. trade/reassessments/{seq}_{type}.json — Delta Review Records

Append-only. One file per reassessment event. Naming: `001_transcript.json`, `002_benzinga_12345.json`.

```json
{
  "schema_version": "reassessment.v1",
  "sequence": 1,
  "prediction_id": "AAPL_Q1_FY2026_20260406T1603",

  "trigger_type": "transcript",
  "trigger_id": "AAPL_2026-04-06_transcript",
  "triggered_at": "2026-04-06T18:45:00-04:00",

  "session_resumed": true,
  "predictor_session_id": "session_abc123",

  "input_sent": {
    "evidence_type": "transcript_qa_highlights",
    "evidence_size_chars": 3200,
    "thesis_summary_included": true,
    "trade_state_included": true,
    "trade_pnl_at_reassessment": 1.8,
    "time_in_trade_hours": 2.5
  },

  "output": {
    "thesis_status": "confirmed",
    "confidence": 85,
    "delta_summary": "Transcript reinforced demand durability. Management raised FY2027 preliminary outlook."
  },

  "daemon_action": "hold",
  "processing_time_sec": 12.5
}
```

If LLM call failed:
```json
{
  "schema_version": "reassessment.v1",
  "sequence": 1,
  "prediction_id": "AAPL_Q1_FY2026_20260406T1603",
  "trigger_type": "transcript",
  "trigger_id": "AAPL_2026-04-06_transcript",
  "triggered_at": "2026-04-06T18:45:00-04:00",

  "session_resumed": false,
  "failure_reason": "session_expired",

  "output": null,
  "daemon_action": "no_change_no_escalation",
  "processing_time_sec": 2.1
}
```

### 4F. Schema Versioning and Migration

Every file has a `schema_version` field (e.g., `trade_plan.v1`). If schemas change:
- New version gets a new schema_version value (e.g., `trade_plan.v2`)
- Daemon must handle reading both old and new versions during transition
- Old files are never rewritten — the daemon adapts to what it reads

### 4G. File Lifecycle Summary

```
prediction/result.json                    ← created by predictor, NEVER modified, read by daemon + attribution
trade/plan.json                           ← created at DEFERRED or ENTERING, updated through lifecycle, status tracks state
trade/result.json                         ← created ONCE at close, never modified, read by attribution
trade/skipped.json                        ← created ONCE at gate rejection, never modified, read by attribution
trade/reassessments/*.json                ← created ONCE per reassessment event, never modified, read by daemon (restart) + attribution
earnings-analysis/trade_daemon_state.json ← global daemon state, created on first startup, read on every startup, updated on equity capture
```

Idempotency rules:
- If plan.json exists for a prediction_id → don't create another (trade already in progress or done)
- If skipped.json exists for a prediction_id → don't retry (permanently rejected)
- If result.json exists for a prediction_id → trade is closed (nothing to do)
- On restart: read plan.json status to determine where to resume

DEFERRED → SKIPPED lifecycle:
- When retry deadline expires: write `trade/skipped.json` FIRST (reason=spread_defer_expired, includes deferral history), then DELETE `trade/plan.json`.
- Crash safety: if BOTH plan.json (status=deferred) AND skipped.json exist after restart → skipped.json takes precedence. Daemon deletes the orphan plan.json.
- This keeps skipped.json as the single terminal pre-entry truth. No ambiguity.

---

---

## Block 5: Operational Safety

How the system handles failures, restarts, and edge cases without losing money or leaving positions unprotected.

### 5A. Daemon Singleton — Only One Instance Runs

```
On startup:
  acquired = redis.set("trade_daemon:lock", pod_id, nx=True, ex=60)
  if not acquired:
    log.error("Another instance running — refusing to start")
    exit(1)

While running:
  Every 30 seconds: atomic compare-and-renew (Lua script or redis-py lock):
    if redis.get(key) == my_pod_id → renew TTL
    else → lock lost, stop accepting new trades

On shutdown:
  Atomic compare-and-delete (Lua script):
    if redis.get(key) == my_pod_id → delete
    else → do nothing (lock already owned by another pod)

  All lock operations are atomic to prevent race conditions between pods.
```

If Redis is down at startup → daemon refuses to start (safe: no duplicate risk).
If Redis goes down during operation:
- Active trade monitoring continues (uses IBKR + Neo4j, no Redis dependency)
- New trade acceptance stops (no fast trigger, filesystem scan is degraded fallback)
- Reassessment fast events degrade to Neo4j backstop scan
- log WARNING, but do NOT halt or enter safe mode

### 5B. Startup Recovery — Rebuilding State from Disk + IBKR

On every daemon startup (including after crashes):

```
Step 1: Acquire Redis singleton lock (5A)

Step 2: Scan filesystem for ALL trade/plan.json files
  For each plan.json:

  status = "deferred":
    → Check retry_deadline. If expired → write skipped.json, delete plan.json.
    → If not expired → resume retry loop.

  status = "entering":
    → Query IBKR: did the entry order fill?
      → If filled + stop active → update to "open", resume monitoring.
      → If filled + stop NOT active → FLATTEN immediately (fail-closed).
      → If not filled → cancel entry order, write skipped.json (reason=entry_recovery_cancelled), delete plan.json. Terminal — no re-entry for stale signals.

  status = "open":
    → Query IBKR: does the position still exist?
      → If yes + stop active → resume monitoring from trigger_log.
      → If yes + stop NOT active → place new stop immediately (repair). If repair fails → FLATTEN immediately (exit_reason=stop_repair_failed). Core invariant: never hold unprotected.
      → If position gone (stop fired while down) → record exit, write result.json, update to "closed".

  status = "exiting":
    → Query IBKR: did the exit fill?
      → If filled → write result.json, update to "closed".
      → If not filled → re-place exit order.
      → If position gone → record exit, write result.json, update to "closed".

  status = "closed":
    → Nothing to do.

Step 3: Crash safety for DEFERRED → SKIPPED
  If BOTH plan.json (status=deferred) AND skipped.json exist for same prediction_id:
    → skipped.json takes precedence → delete orphan plan.json.

Step 4: Scan for untraded predictions (filesystem fallback trigger)
  Look for prediction/result.json where NEITHER plan.json NOR skipped.json exists.
  → These are predictions that arrived while daemon was down → process normally (gate → size → execute).

Step 5: Resume normal operation
  Start the main loop: Redis BRPOP for new predictions + monitoring for active trades.
```

### 5C. IBKR Reconciliation — Periodic Verification

Not just at startup — the daemon periodically verifies that its filesystem state matches IBKR reality.

```
Every RECONCILIATION_INTERVAL_SEC (e.g., 300 = 5 minutes):

  For each active trade (plan.json status = "open" or "exiting"):
    1. Query IBKR for position in this ticker
       → Position exists? Size matches plan.json shares?
       → If missing → stop must have fired → record exit

    2. Query IBKR for stop order status
       → Stop still active?
       → If cancelled/expired → re-place stop immediately. If repair fails → FLATTEN (exit_reason=stop_repair_failed).
       Primary detection: ib_insync order-status callback fires immediately on stop cancellation/expiry → daemon re-places or flattens without waiting for reconciliation cycle.
       Reconciliation scan every 5 minutes is the backstop — catches anything the callback missed.

    3. Check for orphaned IBKR positions
       → If IBKR shows a position that NO plan.json claims → log CRITICAL (manual investigation required)
       → Do NOT auto-close orphan positions (could be from a different system)

    4. Update plan.json last_reconciled_at timestamp
```

### 5D. Order Failure Handling

| Failure | Detection | Action |
|---|---|---|
| Entry order rejected by IBKR | IBKR returns error/reject | Log reason, write skipped.json (reason=entry_rejected) |
| Entry order times out (no fill) | No fill within ORDER_TIMEOUT_SEC | Cancel order, write skipped.json (reason=entry_timeout), delete plan.json. Terminal — no re-entry. |
| Stop order fails after entry fills | Stop placement returns error | FLATTEN immediately — sell entire position at market. Record in result.json (exit_reason=stop_placement_failed) |
| Partial entry fill | IBKR reports partial fill | Place stop for FILLED shares only. Cancel unfilled remainder. Proceed with partial quantity. |
| Exit order rejected | IBKR returns error/reject | Retry with market order. If still fails → log CRITICAL alert, leave position for manual intervention. |
| IBKR Gateway disconnected | Connection lost | Existing positions protected by broker-native stops. Daemon retries connection. No new trades until reconnected. |

**Principle**: every failure path either resolves safely (flatten, retry) or escalates to manual intervention with a CRITICAL log. No failure silently leaves an unprotected position.

### 5E. Account Kill-Switch

Checked every monitoring cycle. Independent of individual trades.

```
if account_equity < starting_equity × (1 - ACCOUNT_KILL_SWITCH_PCT / 100):
    log.CRITICAL("ACCOUNT KILL-SWITCH TRIGGERED")
    for each active trade:
        place market order to close (urgency overrides fill quality)
        record result.json with exit_reason="account_killswitch"
    daemon enters HALTED mode:
        no new trades accepted
        only reconciliation runs
        requires manual restart/config change to resume trading
```

`starting_equity` is captured once at daemon startup and persisted to `earnings-analysis/trade_daemon_state.json` (global path, NOT under any per-event directory). It does NOT reset on restart (would defeat the purpose). Schema: `{"schema_version": "daemon_state.v1", "starting_equity": 50000, "captured_at": "2026-04-06T15:00:00-04:00", "pod_id": "trade-daemon-abc123"}`.

### 5F. Error Logging and Alerting

Three log levels matter for operations:

| Level | Meaning | Examples |
|---|---|---|
| INFO | Normal operation | "Trade opened AAPL 53 shares @ $185.20", "Reassessment: confirmed" |
| WARNING | Degraded but safe | "Redis down — monitoring continues, new trades stopped", "Session resume failed, applying no_change" |
| CRITICAL | Requires attention | "Stop placement failed — flattened position", "Account kill-switch triggered", "Orphan IBKR position detected" |

CRITICAL events should trigger an external alert (email, Slack, push notification). Mechanism is configurable — not locked in the plan.

### 5G. K8s Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: trade-daemon
  namespace: processing
spec:
  replicas: 1                    # singleton — Redis lock is the real guard
  strategy:
    type: Recreate               # not RollingUpdate — avoid brief double-running
  template:
    spec:
      containers:
      - name: trade-daemon
        env:
        - name: ACCOUNT_MODE
          value: "paper"
        - name: DATA_MODE
          value: "delayed"
        # ... all config from Section G
      terminationGracePeriodSeconds: 120   # allow in-flight exit orders to complete
      nodeSelector:
        kubernetes.io/hostname: minisforum  # pin to same node as IBKR Gateway
```

Key decisions:
- `replicas: 1` + `strategy: Recreate` — no overlap during updates (Redis lock is the backup guard)
- `terminationGracePeriodSeconds: 120` — on shutdown, daemon has 2 minutes to complete in-flight exit orders
- Node pinned to IBKR Gateway node for lowest latency
- On pod termination: daemon catches SIGTERM → completes any in-progress order → writes state → exits cleanly

### 5H. What Happens If Everything Goes Wrong

Worst-case scenario chain and how the system handles it:

```
8-K fires → prediction runs → daemon detects it
    │
    ├── Daemon crashes mid-gate → no plan.json → prediction re-discovered on restart
    ├── Daemon crashes mid-order → plan.json status=entering → reconcile with IBKR on restart
    ├── Entry fills, stop fails → FLATTEN immediately (fail-closed)
    ├── Entry fills, daemon crashes → plan.json status=entering → restart reconciles → repairs stop
    ├── Trade open, daemon crashes → plan.json status=open → restart resumes monitoring
    ├── Trade open, IBKR disconnects → broker stop still protects → daemon retries connection
    ├── Trade open, Neo4j down → miss transcript/news reassessment → fail-safe holds
    ├── Trade open, Redis down → monitoring unaffected → miss fast triggers → Neo4j backstop catches
    ├── Trade open, Claude API down → reassessment fails → no_change + no_escalation
    ├── Exit order fails → retry with market → if still fails → CRITICAL alert + manual intervention
    └── Account drops past kill-switch → close ALL → halt daemon → manual restart required
```

**Scenarios requiring human intervention**:
1. Exit order fails TWICE (rejected by IBKR on retry) → CRITICAL alert
2. Orphan IBKR position detected (position exists in IBKR with no matching plan.json) → manual investigation
3. Account kill-switch triggered → daemon halts, requires manual restart

Everything else is handled automatically with degradation toward safety.

---

---

## Block 6: Paper Trading, Tuning, and Rollout

How we validate the system before real money, what we measure, how we tune, and what triggers the decision to go live.

### 6A. Paper Trading Phase — What It Validates

Paper trading uses `ACCOUNT_MODE=paper, DATA_MODE=delayed`. Same code, same logic, degraded data quality.

| What paper trading validates | What it CANNOT validate |
|---|---|
| Gate logic works correctly (skips bad trades) | Exact fill prices (15-min delay) |
| Sizing math produces correct share counts | True slippage (paper fills are simulated) |
| Bracket orders place and confirm on IBKR Paper | Extended-hours liquidity reality |
| Monitoring checks fire at correct times | Real-time streaming threshold triggers |
| Reassessment triggers detect transcript/news | Exact entry latency (delayed data adds noise) |
| Startup recovery rebuilds state correctly | Production IBKR Gateway stability |
| Account kill-switch triggers at threshold | True market impact of our orders |
| All files written correctly (plan/result/skipped/reassessments) | — |
| Attribution receives and processes trade data | — |

**Paper trading is a plumbing test, not a P&L test.** Profitability metrics from delayed data are provisional. The real validation is: does the system work end-to-end without human intervention?

### 6B. Metrics to Track During Paper Phase

**Primary (must pass for go-live consideration):**

| Metric | Target | How measured |
|---|---|---|
| Expectancy | Positive (provisional — delayed data) | `(avg_win × win_rate) - (avg_loss × loss_rate)` from result.json files |
| P&L asymmetry | avg winner $ > avg loser $ | Aggregate from result.json |
| Unprotected positions | Zero, ever | Scan all result.json + plan.json for stop_repair_failed or stop_placement_failed events |
| Daemon uptime | > 99% | K8s pod restart count + trade_daemon_state.json captured_at history |
| Result capture | 100% closed trades have result.json | Count plan.json (status=closed) vs result.json |
| Skip logging | 100% rejected predictions have skipped.json | Count predictions without any trade file |
| Autonomous operation | Zero manual intervention for trade logic | Operator log review |

**Secondary (track, inform tuning, no hard gate):**

| Metric | What it tells us |
|---|---|
| Win rate | Directional accuracy (provisional with delayed data) |
| Max drawdown (peak-to-trough) | Worst losing streak — informs kill-switch threshold |
| Slippage (wanted vs filled) | Entry/exit quality — mostly simulated in paper, but tracks order mechanics |
| Entry latency (8-K filed → trade entered) | System speed — includes prediction time + gate + execution |
| Reassessment count + effectiveness | How often reassessments fire and whether they improve outcomes |
| Skip reason distribution | Which gate checks reject most — informs threshold tuning |
| Deferred count + outcomes | How often spread deferral fires, what % eventually trades vs expires |
| Benchmark/macro stress false positive rate | Did we exit trades that would have been winners? |

### 6C. Tuning — What Can Change and How

All tunable parameters live in the config file (Section G). Changes require config update + daemon restart. No code changes.

**What to tune during paper phase:**

| Parameter | Tune if... | Direction |
|---|---|---|
| CONFIDENCE_THRESHOLD | Too many skips (too high) or too many losers (too low) | Start 75, adjust by 5 |
| MAGNITUDE_THRESHOLD | Skipping profitable small-move trades (too high) or taking unprofitable ones (too low) | Start 3%, adjust by 0.5% |
| DOLLAR_RISK_PER_TRADE | Max drawdown too high (reduce) or P&L too small to matter (increase) | Start $500 |
| ATR_MULTIPLIER | Stops firing too often on normal noise (increase) or not protecting enough (decrease) | Start 2.0 |
| BENCHMARK_ATR_MULT | Exiting on normal sector fluctuation (increase) or missing real sector stress (decrease) | Start 2.0 |
| GAP_FADE_PCT | Exiting on minor pullbacks (increase) or missing real fades (decrease) | Start 50% |
| CHASE_MAX_CONSUMED_PCT | Skipping too many trades (increase) or chasing too much (decrease) | Start 70% |
| SPREAD_EDGE_RATIO | Deferring too often (increase) or accepting bad fills (decrease) | Start 0.25 |

**Tuning protocol:**
- Never tune on fewer than 20 trades for that parameter
- Change one parameter at a time
- Wait for 10+ new trades after each change before evaluating
- Log every config change with date and reason

### 6D. Go-Live Decision — When to Switch to Real Money

**Prerequisites (ALL must be met):**

1. **Paper phase complete**: minimum 50 trades completed, across at least 2 earnings seasons (to cover both peak and off-peak)
2. **Expectancy positive**: even with delayed-data noise, `(avg_win × win_rate) - (avg_loss × loss_rate) > 0`
3. **P&L asymmetry confirmed**: average winner $ > average loser $
4. **Zero safety failures**: no unprotected positions, no missed exits, no orphan positions
5. **Daemon stable**: zero unexpected crashes over the final 2 weeks of paper trading
6. **Config stabilized**: no parameter changes in the final 2 weeks
7. **IBKR Live data available**: `DATA_MODE=realtime` confirmed working (streaming quotes, real-time fills)
8. **Starting capital decided**: real dollar amount deposited in IBKR Live account

**Rollout path (three stages, not two):**

```
STAGE 1: Paper + Delayed (plumbing test)
  ACCOUNT_MODE=paper, DATA_MODE=delayed
  Validates: logic, safety, file writing, recovery, end-to-end flow.
  Does NOT validate: fill quality, timing accuracy, streaming thresholds.
  Target: 50+ trades across 2 earnings seasons.

STAGE 2: Paper + Realtime (behavior test)
  ACCOUNT_MODE=paper, DATA_MODE=realtime (requires IBKR Live data subscription)
  Validates: streaming threshold triggers, entry latency, real spreads,
  realtime monitoring behavior, slippage measurement accuracy.
  This is the TRUE P&L baseline for live comparison.
  Target: 20+ trades. Compare to delayed-paper to understand data-quality impact.

STAGE 3: Live + Realtime (real money)
  Steps below.
```

**Go-live steps (sequential, from Stage 2 → Stage 3):**

```
Step 1: Final paper+realtime review
  Aggregate all paper+realtime results. Review every losing trade.
  Confirm expectancy is positive. Review max drawdown.

Step 2: Freeze config
  Lock all parameters. No changes during initial live period.

Step 3: Switch to live + realtime
  ACCOUNT_MODE=live, DATA_MODE=realtime
  Deploy with the SAME config validated in paper+realtime.

Step 4: Start with reduced risk
  DOLLAR_RISK_PER_TRADE = 50% of paper-validated value
  MAX_POSITIONS = 1 (not 2)
  Run for 10 trades at reduced risk.

Step 5: If 10 live trades confirm paper results
  Increase to full DOLLAR_RISK_PER_TRADE.
  Increase MAX_POSITIONS to 2.

Step 6: Ongoing
  Monitor weekly: expectancy, max drawdown, slippage (now real).
  Compare live results to paper+realtime results (NOT delayed paper — delayed paper was a plumbing test, not a P&L baseline).
  If live is materially worse than paper+realtime → pause and investigate.
```

### 6E. What Justifies Adding More Complexity Later

The launch system is deliberately minimal. Complexity should be added ONLY when paper/live data demonstrates a clear gap:

| Observation from data | Justified addition |
|---|---|
| Many profitable trades skipped because spread was temporarily wide | Tune SPREAD_EDGE_RATIO or add more aggressive deferral |
| Short signals consistently profitable in attribution | Enable short execution (remove direction==long gate filter) |
| Specific stocks need different monitoring (e.g., low-float names) | Add per-ticker or per-sector monitoring parameter overrides |
| Benchmark stress exits are frequently false positives | Tune BENCHMARK_ATR_MULT upward or add benchmark_importance classification |
| Reassessment consistently helps/hurts | Enable/disable or add price-event triggers (the future TODO) |
| Multiple good signals fire simultaneously | Raise MAX_POSITIONS, add portfolio-aware ranking |
| Winners pull back significantly before continuing | Add trailing stop option |
| Live P&L significantly worse than paper | Investigate slippage, fill quality → consider execution improvements |

**Rule: never add complexity to solve a hypothetical problem. Only add when data shows the gap.**

### 6F. Implementation Order

What to build first, in dependency order:

```
Phase 1: Entry-capable skeleton
├── trade_daemon.py main loop (detect, gate, size)
├── IBKR integration (ib_insync: orders, positions, account, delayed prices)
├── Bracket order placement + fail-closed logic
├── plan.json / skipped.json file writing
├── Gate logic (all checks from 3A)
├── Sizing logic (ATR stop + dollar-risk from 3B)
├── Config file loading
├── Redis singleton lock
├── Prediction detection (Redis BRPOP + filesystem scan)
└── K8s deployment (paper mode)
    NOTE: Phase 1 can ENTER trades but cannot monitor or exit them.
    Must proceed to Phase 2 before any real paper trading begins.

Phase 2: Minimum end-to-end paper trading system
├── Monitoring loop (price threshold checks)
├── Computed-at-entry thresholds (benchmark, macro, reversal)
├── Monitoring schedule (filing session → check times)
├── trigger_log recording in plan.json
├── Exit logic (all paths from 3F) + result.json writing
├── Startup recovery (5B)
├── IBKR reconciliation (5C)
├── Order-status callbacks (stop cancellation detection)
└── Account kill-switch (5E)
    NOTE: Phase 1 + Phase 2 together = minimum viable paper trading system.

Phase 3: Reassessment (trades can be recalibrated)
├── Transcript detection (Redis event + Neo4j backstop)
├── Benzinga news detection (Redis event + Neo4j backstop)
├── Reassessment message building
├── Predictor session resume (SendMessage)
├── Reassessment result handling
├── reassessments/*.json writing
└── Upstream pipeline change: push Redis events on ingest

Phase 4: Realtime mode (when IBKR Live data available)
├── IBKR streaming quote subscriptions
├── Threshold-based callbacks (replace polling)
├── Order-status callbacks (stop cancellation detection)
└── DATA_MODE=realtime path testing

Phase 5: Go-live
├── ACCOUNT_MODE=live validation
├── Reduced-risk initial trades
├── Monitoring comparison (live vs paper+realtime)
└── Full-risk ramp-up
```

Each phase is independently deployable, but Phase 1 + Phase 2 together are the minimum viable paper trading system.

---

**END OF PLAN — All 6 blocks complete.**
