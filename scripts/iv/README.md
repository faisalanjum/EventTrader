# IV + Expected-Move Computation (`iv_moves.v2`)

Per-stock implied-volatility and IV-derived expected-move calculator for the
EventMarketDB tradeable universe. Reads IBKR's option chain via `ib_async`
and emits a JSON artifact a downstream predictor can consume.

This document is the operator + predictor quick reference. For the field-level
specification (rules, derivation order, edge cases) see [`SCHEMA_v2.md`](SCHEMA_v2.md).

## What this is — and what it is not

The artifact answers, per ticker, three questions:

| Question | Answer field |
|---|---|
| What is the market's ATM straddle price as a single-number expected move? | `expected_move_dollars`, `expected_move_pct` |
| What is the market's annualized vol, scaled to a 1-σ move for this DTE? | `iv_avg`, `em_from_iv_dollars`, `em_from_iv_pct` |
| What option choices existed for this ticker at run time? | `expiry_ladders[ticker]` |

It does NOT promise the numbers are tradeable. The straddle math is exact;
its truthfulness on any given row depends entirely on the underlying tick
quality, which the predictor must inspect via the quality fields documented
below.

## Quick start

```bash
# Sample of a few tickers, OPRA live quotes (default mdt=1)
python scripts/iv/compute_iv_moves.py --tickers AAPL,NVDA,JPM

# Full universe from Redis (default expiry = next monthly 3rd Friday)
python scripts/iv/compute_iv_moves.py --universe-redis

# Target a specific DTE
python scripts/iv/compute_iv_moves.py --universe-redis --target-dte 45

# No-OPRA fallback (delayed 15-min quotes via IBKR's free tier)
python scripts/iv/compute_iv_moves.py --universe-redis --market-data-type 3
```

Requires IB gateway reachable at `127.0.0.1:14003` (live) or `:14004` (paper):

```bash
kubectl port-forward -n mcp-services svc/ibkr-ib-gateway 14003:4003 &
```

The default `clientId=98` avoids collision with the MCP server (10) and
trader (1).

## Output envelope

The artifact has these top-level keys:

```jsonc
{
  "schema_version":             "iv_moves.v2",
  "run_id":                     "iv_moves.v2:2026-05-14T18:36:06+00:00:199",
  "run_as_of":                  "2026-05-14T18:36:06+00:00",
  "method":                     "atm_straddle",
  "target_dte":                 30,
  "market_data_type_requested": 1,
  "universe_size":              756,

  "market_conventions": {            // close times, AMC/BMO conventions, etc.
    "options_market_close_et":  "16:00",
    "amc_conventional_time_et": "16:30",
    "bmo_conventional_time_et": "07:30",
    "iv_annualization_days":    365
  },
  "config": {                         // surfaced thresholds & assumptions
    "tick_freshness_threshold_sec":   300,
    "iv_disagreement_warn_pp":        3.0,
    "atm_distance_warn_pct":          1.0,
    "delayed_tick_lag_min":           15,
    "earnings_just_after_window_days": 5,
    "expiry_ladder_max_entries":      7,
    ...
  },
  "data_sources": {
    "options_chain":     {"vendor": "IBKR", "via": "reqSecDefOptParams", "live_at_run": true},
    "quotes":            {"vendor": "IBKR", "via": "reqTickersAsync", "live_at_run": true,
                           "market_data_type_requested": 1},
    "earnings_calendar": {"vendor": "yahoo", "via": "yfinance.Ticker.earnings_dates",
                           "as_of":             "2026-05-09T08:00:00+00:00",
                           "newest_fetched_at": "2026-05-14T18:36:07+00:00",
                           "pit_safe": false,
                           "cache_file": "scripts/iv/output/_earnings_cache_2026-05-14.json"}
  },

  "summary":         { ...aggregate counts by status/data_tier/iv_quality/... },
  "results":         [ ...per-row IVRow records... ],
  "expiry_ladders":  { "TICKER": [ ...≤7 candidate expiries... ] }
}
```

`run_id` format is `"iv_moves.v2:{run_as_of_iso}:{clientId}"`. It is the
canonical handle for citing a run.

`run_as_of` is the run's wall-clock start (UTC). All date-level logic
internally converts this to ET via the rules in
[`SCHEMA_v2.md`](SCHEMA_v2.md). The predictor should treat `run_as_of`
as truth for "what time was this snapshot."

## Per-row fields (`results[i]`)

Each row is one `(ticker, expiry, earnings_role)` triple. Most tickers
emit one row; the orchestrator emits **two** when an earnings event
creates a meaningful pre/post-event split (see [Earnings timing](#earnings-timing-semantics)).

### Identity

| Field | Type | Meaning |
|---|---|---|
| `row_id` | str | `{ticker}:{expiry}:{earnings_role}` — citable handle |
| `run_id` | str | Same `run_id` as the envelope; for joins |
| `ticker` | str | |
| `is_primary` | bool | True for the primary row per ticker; False for the secondary dual-row emission |

### Strike & expiry

| Field | Type | Meaning |
|---|---|---|
| `expiry` | str (YYYYMMDD) | The chain expiry this row computed |
| `dte` | int | Days-to-expiry from `run_as_of`'s **ET trading date** |
| `atm_strike` | float | Strike chosen for the ATM straddle |
| `atm_distance_pct` | float | `\|strike − spot\| / spot × 100` |
| `multiplier` | int \| null | Contract multiplier (100 = standard equity option); `null` = ambiguous; never silently defaulted |

### Market data — straddle leg quotes

| Field | Type | Meaning |
|---|---|---|
| `spot`, `spot_source` | float, str | Underlying price; `live` or `mdt=N` |
| `call_bid` / `call_ask` / `call_mid` | float | Call leg quotes. `call_mid` derived per `call_mid_source` rules |
| `call_mid_source` | str | `bid_ask_mid` \| `last_fresh` \| `last_stale_rejected` \| `none` |
| `put_bid` / `put_ask` / `put_mid` / `put_mid_source` | (same) | Put leg quotes |
| `call_iv`, `put_iv` | float | Per-leg model IV (annualized, decimal — e.g. 0.247 = 24.7%). May be sanitized; see flags |
| `call_tick_age_seconds`, `call_tick_age_known` | float, bool | Age of latest tick. `*_known=False` when IBKR didn't surface `ticker.time` |
| `put_tick_age_seconds`, `put_tick_age_known` | (same) | |
| `spread_call_bps`, `spread_put_bps` | float | Per-leg bid/ask spread in bps of mid |

### Computed outputs

| Field | Type | Meaning |
|---|---|---|
| `expected_move_dollars` | float | `call_mid + put_mid` |
| `expected_move_pct` | float | `expected_move_dollars / spot` |
| `iv_avg` | float | `(call_iv + put_iv) / 2`, annualized decimal |
| `em_from_iv_dollars` | float | `spot × iv_avg × sqrt(dte / 365)` — the raw 1-σ move (in $) implied by IV |
| `em_from_iv_pct` | float | `em_from_iv_dollars / spot` = `iv_avg × sqrt(dte / 365)` — the raw 1-σ move as a fraction of spot |
| `iv_disagreement_pp` | float | `\|call_iv − put_iv\|` in percentage points (e.g. 30% vs 27% = 3.0 pp) |

### Quality axes (the four orthogonal labels)

| Field | Type | Meaning |
|---|---|---|
| `status` | str | Did the computation **produce** numbers? Not "trustworthy." See [Quality model](#quality-model) |
| `data_tier` | str | Observed market data tier: `live` \| `delayed` \| `frozen` \| `delayed_frozen` \| `fallback_delayed` \| `unknown` |
| `quote_freshness` | str | `fresh` \| `stale` \| `unknown` — independent of `data_tier` |
| `iv_quality` | str | Aggregate label: `HIGH` \| `MEDIUM` \| `LOW` \| `n/a` — **mechanical data quality, NOT a trade signal** |

### Flag lists

| Field | Type | Meaning |
|---|---|---|
| `quality_flags` | list[str] | Operational data anomalies (mechanical) |
| `context_flags` | list[str] | Market/event context (semantic) |
| `diagnostics` | list[str] | Free-form trace messages from this row's compute path |

### Earnings timing

| Field | Type | Meaning |
|---|---|---|
| `earnings_role` | str | `pre_earnings` \| `post_earnings` \| `non_earnings` |
| `earnings_next_date` | str (YYYY-MM-DD) | Event's ET trading date |
| `earnings_next_time` | str | `AMC` \| `BMO` \| `DMH` \| `unknown` |
| `earnings_next_time_source` | str | Same as `earnings_calendar_source` |
| `earnings_event_ts` | str (ISO) | Event timestamp (UTC) |
| `earnings_event_ts_source` | str | `sec_filing` \| `user_supplied` \| `yahoo_conventional` \| `unknown` |
| `earnings_in_window` | bool | DATE-level: `event_date ≤ expiry_date AND ≥ today_et` |
| `earnings_in_contract_life` | bool | TS-level: `event_ts ≤ expiry_close_ts` |
| `earnings_calendar_source` | str | `yahoo` (current) |
| `earnings_calendar_as_of` | str | Per-row `fetched_at` from the cache entry (authoritative for THIS ticker) |
| `earnings_calendar_pit_safe` | bool | `false` — Yahoo's calendar is current-state |

### Quote snapshot provenance

| Field | Type | Meaning |
|---|---|---|
| `quote_snapshot_as_of` | str \| null | EFFECTIVE market time the quote represents. Delayed paths subtract `delayed_tick_lag_min` |
| `quote_snapshot_source` | str | `live_tick` \| `delayed_tick` \| `frozen_close` \| `delayed_frozen` \| `no_tick` \| `unknown` |
| `quote_snapshot_relative_to_event` | str | `pre_event` \| `post_event` \| `not_applicable` \| `unknown` |

## Quality model

The predictor MUST inspect four orthogonal axes — `status` alone is not
enough. They were split deliberately because they carry distinct truths:

```
          status          →  did compute_one produce numbers for this row?
          data_tier       →  what kind of market data did we observe?
          quote_freshness →  how old is the latest tick?
          iv_quality      →  aggregate of the above (convenience label)

quality_flags             →  operational anomalies (data quality)
context_flags             →  market context (earnings, expiry timing)
```

### `status` (what it does NOT mean)

`status = OK` means: **the math ran end to end and emitted finite
numbers.** It does NOT mean the numbers are tradeable, fresh, on-ATM,
or that bid/ask is sane.

A row can be `status=OK` AND `data_tier=delayed_frozen` AND
`quote_freshness=stale` AND `iv_quality=LOW`. That is correct behavior:
we computed it, but the predictor should not trade on it.

Status enum:

| Status | Meaning |
|---|---|
| `OK` | EM was computable from quotes |
| `PARTIAL` | Some legs populated but EM not computable (rare under OPRA) |
| `NO_QUOTES` | All legs returned null after delayed-fallback attempt |
| `NO_CHAIN` / `NO_EXPIRY` / `NO_ATM` / `OPT_NOT_FOUND` | Chain-side resolution failure |
| `NO_CONID` / `NO_SPOT` / `QUALIFY_FAILED` / `SPOT_FAILED` / `CHAIN_FAILED` / `QUOTE_FAILED` | Underlying-side or transient IBKR error |

### `data_tier` (observed, not requested)

`live` requires populated bid/ask/last. A run requested as
`market_data_type=1` (live) that returned only null ticks reports
`data_tier=unknown`, NOT `live`. Honesty over wishful labeling.

The `fallback_delayed` tier is distinct from native `delayed`: it means
the run requested live but the live stream was empty, so the code
auto-switched to delayed mid-run.

### `quote_freshness` (independent of `data_tier`)

`fresh` requires BOTH legs to have a known `ticker.time` AND age below
`config.tick_freshness_threshold_sec` (default 300s = 5 min). A
`delayed` row can still be `fresh` — the 15-min lag is reflected in
`quote_snapshot_as_of`, not in tick age.

### `iv_quality` (aggregate; mechanical only)

`iv_quality` is a convenience label aggregating the other three axes.
Its meaning is **data quality, not market opinion**:

| Label | Means |
|---|---|
| `HIGH` | Clean live data, no quality flags, tight quotes |
| `MEDIUM` | Live or near-live with one minor issue, OR clean delayed |
| `LOW` | Multiple issues OR frozen/delayed_frozen |
| `n/a` | Status not OK |

The predictor should NOT interpret `iv_quality=HIGH` as a buy signal or
`LOW` as a sell signal. It is a filter for "is this row's data worth
listening to."

### `quality_flags` enum (operational anomalies)

| Flag | Means |
|---|---|
| `iv_sanitized` | Per-leg IV was None / NaN / -1 / outside `[iv_min_valid, iv_max_valid]` and replaced with `null`. The leg's `*_iv` field is `null`; the value was NOT clamped to the range |
| `stale_last_rejected` | A leg fell back to `last` price but `last` was too old; mid set to None |
| `strike_retry_used` | Closest strike to spot didn't qualify; fell back to a farther strike |
| `multiplier_nonstandard` | Multiplier ≠ 100, or ambiguous across legs |
| `atm_distance_high` | `atm_distance_pct ≥ atm_distance_warn_pct` (1% default) |
| `iv_disagreement` | `iv_disagreement_pp ≥ iv_disagreement_warn_pp` (3 pp default) |
| `wide_spread` | Any leg's `spread_bps ≥ spread_warn_bps` (1000 bps = 10% default) |

### `context_flags` enum (market context)

| Flag | Means |
|---|---|
| `includes_earnings_premium` | `in_contract_life=True AND qs_rel=pre_event` — quote was taken before an event the option will see |
| `post_event_snapshot` | `qs_rel=post_event` — quote was taken after the event already happened |
| `expiry_before_known_earnings` | `in_window=True AND in_contract_life=False` — primary expiry dies before the event |
| `amc_expiry_day` | AMC event on expiry-day (sub-case of above) — option dies at 4:00 ET, event at 4:30 ET |
| `earnings_just_after_window` | `in_window=False` but event is ≤ `earnings_just_after_window_days` past expiry |

## Earnings timing semantics

Three distinct date/time questions, three distinct fields:

```
in_window           = event_date ≤ expiry_date     (DATE-level, ET)
in_contract_life    = event_ts   ≤ expiry_close_ts (TS-level, UTC compare)
qs_rel_to_event     = quote_snapshot_as_of vs event_ts
```

The AMC-on-expiry-day case forces the date↔timestamp split:

```
expiry = 2026-07-31 (Fri)         event = 2026-07-31 16:30 ET (AMC)
  date level:  event_date == expiry_date          → in_window = True
  ts level:    event_ts > expiry_close (16:00 ET) → in_contract_life = False
  role:        pre_earnings (option dies before event)
```

### `earnings_role` and the dual-row rule

When `earnings_in_window=True` the orchestrator may emit a SECOND row
for the same ticker so the predictor sees both sides of the event:

| Primary's role | Secondary expiry | Secondary's forced role |
|---|---|---|
| `pre_earnings` (primary expires before event) | First chain expiry strictly AFTER `event_ts` | `post_earnings` |
| `post_earnings` (primary's life spans event) | Last chain expiry strictly BEFORE `event_ts` (and after today_et) | `pre_earnings` |
| `non_earnings` | (none — no dual emission) | — |

The secondary's role is **forced by the orchestrator** to the complement
of the primary's, because the helper's `derive_earnings_timing` would
otherwise tag a secondary that's pre-event as `non_earnings` (its
`in_window=False` from the secondary's perspective). The dual-row note
appears in `diagnostics`.

`is_primary=False` distinguishes the secondary row. The two share
`run_id`, `ticker`, and `earnings_event_ts`.

### `event_ts` source precedence

The `earnings_event_ts_source` field tells the predictor where the
timestamp came from. Precedence:

```
sec_filing > user_supplied > yahoo_conventional > unknown
```

`yahoo_conventional` means Yahoo provided a date but no time, and the
code attached `MARKET_CONVENTIONS["amc_conventional_time_et"]` (or BMO/DMH).
This is a CONVENTION, not a fact — the actual release time may be off by
hours.

## Quote snapshot

`quote_snapshot_as_of` is the EFFECTIVE market time the quote represents,
NOT the wall-clock receive time:

| `quote_snapshot_source` | Effective time computation |
|---|---|
| `live_tick` | `ticker.time` as-is (UTC) |
| `delayed_tick` | `ticker.time − config.delayed_tick_lag_min` (default 15 min) |
| `frozen_close` | `ticker.time` as-is (last live tick before freeze) |
| `delayed_frozen` | `ticker.time − config.delayed_tick_lag_min` |
| `no_tick` | `quote_snapshot_as_of = null` — no tick flowed; do not infer a time |
| `unknown` | `mdt` outside 1..4 |

`no_tick` is the truthful label when both legs come back without
`ticker.time`. Previously this case returned `delayed_tick` with a null
timestamp, which misled consumers; the predictor should rely on the
explicit `no_tick` label.

`config.delayed_tick_lag_min` is surfaced in the artifact so the
predictor can verify the assumption or override it.

## Expiry ladders

`artifact["expiry_ladders"][TICKER]` is a list of ≤ `config.expiry_ladder_max_entries`
(default 7) candidate expiries the predictor can see, sorted ascending
by date:

```jsonc
{
  "expiry":                    "20260518",
  "dte":                       4,
  "class":                     "weekly",                // monthly | weekly | unknown
  "covers_earnings":           false,                   // date-level: event_date ≤ expiry_date
  "earnings_in_contract_life": false,                   // ts-level: event_ts ≤ expiry_close_ts
  "selected_for_compute":      true,                    // an emitted row uses this expiry
  "row_ids":                   ["NVDA:20260518:pre_earnings"]   // cross-ref to results[]
}
```

### Invariants

- **Sorted ascending** by date.
- **≤7 entries** per ticker by default.
- **Every emitted row's expiry appears** in its ticker's ladder, even if
  date-proximity ranking would have excluded it. (Force-included.) The
  predictor can rely on `row_id ∈ ladder.row_ids ⇒ ticker.expiry_ladder` contains it.
- `class` uses the third-Friday rule:
  - `monthly` — date is the third Friday of its month
  - `weekly` — Friday, not a third Friday
  - `unknown` — non-Friday (Mon/Tue/Wed expiries some chains carry)
- `covers_earnings` and `earnings_in_contract_life` answer the same
  questions as the per-row fields, but for any candidate expiry — useful
  for "what if we'd picked X instead?"

## Comparing IVs against a vendor

When cross-checking a row against a third-party IV (Bloomberg,
OptionMetrics, TradingView, Yahoo, etc.), the correct comparison is:

```
this artifact's   iv_avg        ≈   vendor's "30-day ATM IV"
```

Both are annualized vols in decimal form (e.g. 0.247 = 24.7%). Match
within a few percentage points in normal markets; wider deviations are
expected around earnings, dividends, hard-to-borrow names, illiquid
chains, or vendor differences in interpolation.

Do **NOT** compare:

- `expected_move_pct` to a vendor IV — they are different units (a
  scaled 1-σ move vs an annualized vol).
- A single leg's `call_iv` or `put_iv` to a vendor IV — put-call IV
  disparity is normal market structure (skew, dividend timing, hard-to-borrow).
  Vendors typically publish a single ATM IV that approximates the mean.

A useful sanity ratio is the **Brenner-Subrahmanyam** relation. The ATM
straddle price approximates `sqrt(2/π)` times a 1-σ move:

```
em_from_iv_pct        =  iv_avg × sqrt(dte/365)        # raw 1-σ move (fraction of spot)
expected_move_pct     ≈  sqrt(2/π) × em_from_iv_pct
                      ≈  0.7979   × em_from_iv_pct

⇒ expected_move_pct / em_from_iv_pct  ≈  0.7979
```

So the sanity check is the **ratio** of `expected_move_pct` to
`em_from_iv_pct` (not their equality). In normal markets at a tight ATM
strike, that ratio sits within roughly 0.6–1.0. Values outside that band
usually trace to `includes_earnings_premium`, `wide_spread`, or
`atm_distance_high` — check those flags before suspecting a bug.

## Known limitations

- **Yahoo earnings calendar is NOT PIT-safe.** `data_sources.earnings_calendar.pit_safe`
  is always `false`. Yahoo serves current-state data; if a company
  pre-announces or moves its date, the cache will reflect the new value
  on next refresh — not the historical truth. For PIT use, supply your
  own `event_ts` via `--user-earnings-ts <path/to/json>`.
- **`earnings_calendar.as_of` is the OLDEST** `fetched_at` across loaded
  cache entries (conservative top-level claim). `newest_fetched_at` is
  exposed alongside for the range. Per-row `earnings_calendar_as_of`
  remains the authoritative per-ticker value.
- **Delayed lag is an assumption.** `config.delayed_tick_lag_min` is the
  IBKR-documented 15 min. IBKR does not surface an explicit effective
  timestamp on delayed feeds; if they ever do, prefer that.
- **Multiplier is verified, not assumed.** If both legs report
  `multiplier=100` the field is set; mismatch or absence yields
  `multiplier=null + quality_flags=[multiplier_nonstandard]`. The
  predictor should treat null as "do not compute notional from this row."

## Run modes

| Mode | Command | Expected |
|---|---|---|
| OPRA live | `--market-data-type 1` (default) | Most rows `data_tier=live`, `quote_freshness=fresh`, `iv_quality=HIGH/MEDIUM` |
| Frozen (post-close) | `--market-data-type 2` | `data_tier=frozen`, `iv_quality≤MEDIUM` |
| Free delayed | `--market-data-type 3` | `data_tier=delayed`, `quote_snapshot_as_of` subtracts 15 min |
| Delayed frozen | `--market-data-type 4` | `data_tier=delayed_frozen` |

Live (mdt=1) auto-falls back to delayed if BOTH legs come back null —
the row is tagged `data_tier=fallback_delayed` and a diagnostic notes
the fallback.

## Testing

```bash
source venv/bin/activate
python -m pytest scripts/iv/test_compute_iv_moves.py -v
```

The suite covers calendar, expiry pickers, ATM strike retry, IV
sanitization, mid-source rules, data-tier derivation, quote freshness,
the dual-row orchestrator, all five timestamp/provenance honesty
patches, and the expiry-ladder invariants. See `test_compute_iv_moves.py`
for the breakdown.

## Pointers

- **Field-level spec**: [`SCHEMA_v2.md`](SCHEMA_v2.md) — derivation rules,
  edge cases, JSON envelope full schema.
- **Sample artifacts**: `output/sample_phase4_patch_v3.json`
  (single-/dual-row plus earnings provenance fields),
  `output/sample_phase5_expiry_ladder.json` (Phase 5 expiry ladder).
- **IBKR connection details**: see top of `compute_iv_moves.py`.
