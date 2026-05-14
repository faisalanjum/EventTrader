# IV Moves Output Schema — `iv_moves.v2` (revision 3)

**Version**: `iv_moves.v2`
**Status**: PROPOSED — awaiting user sign-off before implementation
**Revision history**:
- r1 — STALE/data_tier contradiction; missing expiry_ladder; missing row_id; earnings date-window only
- r2 — fixed 12 issues from review
- r3 — fixed 9 more issues: envelope omission, Juneteenth dates, run_id wording, fallback double-count, Example 3 contradictions, "zeroed out" → "set to null", in_window phrasing, explicit pre/post selection rules, removed per-row pit_unsafe noise
- r4 — fixed 6 issues (AMC formula, BMO wording, freshness=unknown, dead enums, Example 5 date, Example 3 reasoning)
- r5 — CRITICAL: separates run time from quote-snapshot time
       Predictor runs at 16:35 after 8-K AMC release; option quotes are frozen from 16:00 pre-release.
       Bot MUST know the IV snapshot is pre-event even though the script run is post-event.
       Added per-row: quote_snapshot_as_of, quote_snapshot_source
       Added per earnings: event_ts (explicit), event_ts_source, quote_snapshot_relative_to_event
       Updated all derivation rules to use the right timestamp for each question

## Design principles

1. **Every row tells the trading bot what data it's looking at** — explicit `data_tier`, `quote_freshness`, `iv_quality`, `mid_source` (per leg), `tick_age_seconds` (per leg).
2. **Three orthogonal quality dimensions** — `data_tier` (entitlement: live/delayed/...), `quote_freshness` (tick age: fresh/stale), `iv_quality` (summary: HIGH/MEDIUM/LOW). **Delayed ≠ stale.**
3. **`OK` means "computed", NOT "safe to trade".** Trust derived from transparency fields.
4. **Quality flags vs context flags are separate.** Data-integrity defects vs semantic context don't share a list.
5. **`is_primary` separate from `earnings_role`.** A row can be both (primary AND post-earnings) without information loss.
6. **`expiry_ladder` exposes alternatives.** Bot sees the choices, not just the picked one.
7. **Stable identifiers** — `run_id` top-level, `row_id` per row. Citable by evidence catalog / learner.
8. **PIT honesty** — earnings calendar source + as_of + `pit_safe` flag explicit.
9. **Raw data preserved at all quality tiers.** Bot decides, schema doesn't hide.
10. **No promises the code won't fulfill** — `historical` data_tier reserved, not implemented in v2.

---

## Top-level envelope

```jsonc
{
  "schema_version": "iv_moves.v2",
  "run_id":         "iv_moves.v2:2026-05-14T13:30:00Z:33",  // {schema}:{run_as_of}:{clientId} — UNIQUE PER RUN. Stable within one run for citing rows; NOT stable across re-runs (timestamp varies).
  "run_as_of":      "2026-05-14T20:35:00Z",  // WHEN THE SCRIPT RAN (e.g., 16:35 ET = 20:35 UTC, post-market for predictor use)
                                              // Distinct from per-row `quote_snapshot_as_of` which is when the QUOTE represents.
                                              // Predictor running at 16:35 after 8-K release at 16:30 has run_as_of=16:35 but
                                              // quote_snapshot_as_of may be 16:00 (frozen pre-release).
  "method":         "atm_straddle",
  "target_dte":     30,
  "market_data_type_requested": 1,
  "universe_size":  783,

  "config": {
    // every threshold a quality rule references must be here, tunable + auditable
    "tick_freshness_threshold_sec":   300,    // tick_age >= this → leg quote_freshness=stale
    "spread_warn_bps":               1000,    // any leg spread > 10% of mid → quality_flag wide_spread (NEVER rejects mid; preserves raw data)
    "atm_distance_warn_pct":          1.0,    // strike > X% from spot → flag atm_distance_high
    "iv_disagreement_warn_pp":        3.0,    // |call_iv - put_iv| > X pp → flag iv_disagreement
    "iv_min_valid":                   0.01,   // IV < 1% → set to null + flag iv_sanitized
    "iv_max_valid":                   5.0,    // IV > 500% → set to null + flag iv_sanitized
    "earnings_just_after_window_days": 5,     // earnings within X days AFTER picked expiry → context_flag
    "live_to_delayed_fallback_enabled": true,
    "expiry_ladder_max_entries":       7      // cap per-ticker ladder size
  },

  "data_sources": {
    "options_chain":      { "vendor": "IBKR",  "via": "reqSecDefOptParams",      "live_at_run": true },
    "quotes":             { "vendor": "IBKR",  "via": "reqTickersAsync",         "live_at_run": true },
    "earnings_calendar":  { "vendor": "yahoo", "via": "mcp__yahoo-finance",      "as_of": "2026-05-14T08:00:00Z", "pit_safe": false, "cache_age_seconds": 19800 }
  },

  "summary": {
    "total_rows":         850,        // counts EACH emitted row (some tickers have 2: pre + post earnings)
    "by_status":          {"OK": 644, "PARTIAL": 112, "NO_CONID": 27, "...": 0},
    "by_data_tier":       {"live": 620, "delayed": 80, "fallback_delayed": 30, "frozen": 30, "delayed_frozen": 90},
    "by_quote_freshness": {"fresh": 720, "stale": 60, "unknown": 70},
    "by_iv_quality":      {"HIGH": 400, "MEDIUM": 250, "LOW": 100, "n/a": 100},
    "by_earnings_role":   {"non_earnings": 760, "pre_earnings": 45, "post_earnings": 45},
    "by_is_primary":      {"true": 783, "false": 67}
  },

  "expiry_ladder": [ /* one entry per ticker; see ladder shape below */ ],

  "results":       [ /* one or more rows per ticker; see row shape below */ ]
}
```

---

## Per-ticker `expiry_ladder` (separate from `results` rows)

Each input ticker gets ONE entry in `expiry_ladder` listing the ≤N expiries we considered. Bot sees the choice space before reasoning over the computed row(s) in `results`.

```jsonc
{
  "ticker": "NVDA",
  "spot":   145.32,
  "as_of":  "2026-05-14T13:30:00Z",
  "candidate_expiries": [
    {
      "expiry":             "20260515",      // YYYYMMDD
      "dte":                1,
      "dte_fractional":     0.92,
      "type":               "weekly",         // weekly | monthly | quarterly | leap
      "distance_from_target_dte_days":  29,   // target was 30
      "covers_earnings_event": false,         // option's contract life includes the announcement?
      "is_amc_earnings_day":    true,
      "selected_for_compute":   true,
      "row_ids":  ["NVDA:20260515:pre_earnings"]
    },
    {
      "expiry":             "20260522",
      "dte":                8,
      "dte_fractional":     7.92,
      "type":               "weekly",
      "distance_from_target_dte_days":  22,
      "covers_earnings_event": true,
      "is_amc_earnings_day":   false,
      "selected_for_compute":  true,
      "row_ids":  ["NVDA:20260522:post_earnings"]
    },
    {
      "expiry":             "20260618",      // Holiday-aware: nominal 3rd-Friday 2026-06-19 is Juneteenth (market closed) → actual monthly expiry rolls to Thursday 2026-06-18
      "dte":                35,
      "dte_fractional":     34.7,
      "type":               "monthly",
      "distance_from_target_dte_days":  5,
      "covers_earnings_event": true,
      "is_amc_earnings_day":   false,
      "selected_for_compute":  false,         // not picked; shown for bot's alternative-paths reasoning
      "row_ids":  []
    },
    {
      "expiry":             "20260717",
      "dte":                64, "dte_fractional": 63.7, "type": "monthly",
      "distance_from_target_dte_days": 34,
      "covers_earnings_event": true, "is_amc_earnings_day": false,
      "selected_for_compute": false, "row_ids": []
    }
    /* ≤ config.expiry_ladder_max_entries entries */
  ]
}
```

---

## Per-row shape (in `results` array)

```jsonc
{
  "schema_version": "iv_moves.v2",
  "row_id":         "NVDA:20260522:post_earnings",  // {ticker}:{expiry}:{earnings_role}; stable for evidence cite
  "run_id":         "iv_moves.v2:2026-05-14T13:30:00Z:33",

  // === identity ===
  "ticker":         "NVDA",
  "spot":           145.32,
  "spot_source":    "live",            // live | delayed | frozen | historical_close

  // === time provenance (NEW in r5 — separates run time from quote time) ===
  "quote_snapshot_as_of":  "2026-05-14T20:00:00Z",   // when the option quotes ACTUALLY represent
                                                      // (e.g., 16:00 ET frozen close even if run_as_of=16:35 ET)
  "quote_snapshot_source": "live_tick",                // live_tick | delayed_tick | frozen_close | delayed_frozen | unknown
                                                       // live_tick     : ticker.time within freshness window, mdt=1
                                                       // delayed_tick  : mdt=3, fresh tick within delayed stream
                                                       // frozen_close  : mdt=2, last live tick (often previous close)
                                                       // delayed_frozen: mdt=4, delayed-snapshot
                                                       // unknown       : ticker.time absent, can't infer

  // === expiry classification ===
  "expiry":         "20260522",
  "is_primary":     true,              // was this the user's target-DTE pick?
  "earnings_role":  "post_earnings",   // pre_earnings | post_earnings | non_earnings
  "dte":            8,
  "dte_fractional": 7.92,              // hours-to-close / 24

  // === strike ===
  "atm_strike":         145.0,
  "atm_distance_pct":   0.22,          // |strike - spot| / spot * 100
  "multiplier":         100,           // standard; flag if ≠100

  // === per-leg detail ===
  "call": {
    "conid": 234569,
    "bid": 5.30, "ask": 5.45, "last": 5.37,
    "mid": 5.375,
    "mid_source": "bid_ask_mid",       // bid_ask_mid | last_fresh | last_stale_rejected | none
    "iv": 0.6512,                       // sanitized: never NaN, never -1, within [iv_min_valid, iv_max_valid]
    "spread_bps": 28.0,
    "tick_age_seconds": 0.8,
    "tick_age_known": true              // false if IBKR didn't surface a tick timestamp
  },
  "put": { /* same shape */ },

  // === computed ===
  "expected_move_dollars": 10.45,
  "expected_move_pct":     0.0719,
  "iv_avg":                0.6500,
  "iv_disagreement_pp":    0.23,        // |call_iv - put_iv| in vol points
  "em_from_iv_dollars":    12.34,       // spot * iv_avg * sqrt(dte_fractional/365)
  "em_from_iv_pct":        0.0849,
  "em_method_ratio":       0.847,       // straddle / iv_derived; diagnostic only, do NOT interpret

  // === THREE orthogonal quality dimensions ===
  "data_tier":       "live",            // live | delayed | frozen | delayed_frozen | fallback_delayed
                                        // (RESERVED for v3: historical)
  "quote_freshness": "fresh",           // fresh | stale | unknown
                                        // fresh = both legs tick_age < config.tick_freshness_threshold_sec
                                        // stale = any leg tick_age ≥ threshold
                                        // unknown = tick_age_known=false on any leg
  "iv_quality":      "HIGH",            // HIGH | MEDIUM | LOW | n/a (see derivation rules)

  // === TWO separate flag lists ===
  "quality_flags": [                    // ONLY data/quote integrity issues
    /* "wide_spread" | "iv_disagreement" | "atm_distance_high" | "iv_sanitized"
       | "strike_retry_used" | "multiplier_nonstandard" | "stale_last_rejected" */
  ],
  "context_flags": [                    // semantic context (not defects)
    "includes_earnings_premium"
    /* | "expiry_before_known_earnings" | "amc_expiry_day"
       | "earnings_just_after_window" */
  ],

  "status":         "OK",               // OK | PARTIAL | NO_QUOTES | NO_CHAIN | NO_EXPIRY
                                        // | NO_ATM | OPT_NOT_FOUND | NO_CONID | SPOT_FAILED

  // === earnings context ===
  "earnings": {
    "next_date":            "2026-05-15",
    "next_time":            "AMC",                // AMC | BMO | DMH | unknown
    "next_time_source":     "yahoo",              // origin of the AMC/BMO classification
    "event_ts":             "2026-05-15T20:30:00Z",  // EXPLICIT timestamp; derived from next_date + conventional time
    "event_ts_source":      "yahoo_conventional",    // sec_filing | yahoo_conventional | user_supplied | unknown
                                                     // sec_filing  : timestamp from actual 8-K filing time (highest fidelity)
                                                     // yahoo_conventional : derived from date + AMC/BMO conventional time
                                                     // user_supplied: passed via CLI override
    "in_window":            true,                  // see derivation rules; date-level "earnings on calendar?"
    "earnings_in_contract_life": false,            // timing-level: contract spans event?
    "quote_snapshot_relative_to_event": "pre_event",  // pre_event | post_event | not_applicable
                                                      // pre_event  : quote_snapshot_as_of < event_ts → IV reflects forthcoming event
                                                      // post_event : quote_snapshot_as_of >= event_ts → IV is post-event vol
                                                      // not_applicable : no earnings in scope
    "calendar_source":      "yahoo",
    "calendar_as_of":       "2026-05-14T08:00:00Z",
    "calendar_pit_safe":    false                  // backtests MUST gate on top-level data_sources.earnings_calendar.pit_safe
  },

  "diagnostics": []                     // human-readable; empty when clean. NO interpretation of em_method_ratio.
}
```

### `data_tier` derivation rules

```
live              — mdt=1 AND (call.bid OR call.ask OR put.bid OR put.ask) populated
delayed           — mdt=3 (15-min streaming-delayed)
frozen            — mdt=2 (last known live state, no refresh)
delayed_frozen    — mdt=4 (delayed-frozen snapshot)
fallback_delayed  — initial request type=1, got nulls, retried with type=3 successfully
[reserved: historical] — not implemented in v2
```

### `quote_freshness` derivation rules

```
fresh   — both legs: tick_age_seconds < config.tick_freshness_threshold_sec
stale   — any leg:   tick_age_seconds ≥ config.tick_freshness_threshold_sec
unknown — any leg:   tick_age_known=false
```

**Delayed data CAN be fresh.** A type=3 ticker that received its 15-min-delayed tick 12 seconds ago is `data_tier=delayed, quote_freshness=fresh`. Independent dimensions.

### `iv_quality` derivation rules

```
Compute issue_count = number of TRUE conditions among the following INDEPENDENT checks:
  (1) data_tier ≠ live                                      (data tier is NOT live)
  (2) quote_freshness ≠ fresh                                 (stale OR unknown both count as issue)
  (3) any leg mid_source ≠ bid_ask_mid                        (fell back to last)
  (4) iv_disagreement_pp ≥ config.iv_disagreement_warn_pp
  (5) atm_distance_pct ≥ config.atm_distance_warn_pct
  (6) any quality_flag present that's NOT already implied by (1)-(5)
      [e.g. multiplier_nonstandard, strike_retry_used, iv_sanitized]

  NOTE: data_tier=fallback_delayed counts as ONE issue (data_tier≠live).
        The fallback action does NOT also get its own quality_flag; that would double-count.

HIGH    — issue_count == 0 AND data_tier == live (must be live AND clean)
MEDIUM  — issue_count == 1
LOW     — issue_count >= 2
          OR data_tier IN (frozen, delayed_frozen) — these are static/snapshot data; cap at LOW
n/a     — status NOT IN (OK, PARTIAL)
```

### Earnings field derivation rules (TIME PROVENANCE explicit in r5)

```
THREE TIMESTAMPS in play — distinguish them carefully:

  run_as_of              = when the SCRIPT RAN          (top-level)
  quote_snapshot_as_of   = when the QUOTE REPRESENTS    (per row; from ticker.time or freeze)
  event_ts               = when EARNINGS RELEASES       (per row; from sec_filing or yahoo conventional)

Common predictor scenario:
  run_as_of            = 2026-05-14T20:35:00Z  (16:35 ET, script kicked off after 8-K)
  quote_snapshot_as_of = 2026-05-14T20:00:00Z  (16:00 ET, options closed pre-release)
  event_ts             = 2026-05-14T20:30:00Z  (16:30 ET, 8-K announcement)
  → run is post-event; SNAPSHOT IS PRE-EVENT (IV reflects forthcoming earnings)


Let expiry_close_ts = expiry_date @ 16:00 ET.

────────────────────────────────────────────────────────────────────────
earnings.in_window  (DATE-LEVEL — "is earnings on this option's expiry calendar?")

  in_window = (earnings_date >= run_as_of.date()) AND (earnings_date <= expiry_date)

  → uses RUN time, not snapshot. Bot wants to know "is there an earnings event the
    option could care about, scheduled today or later through expiry?"

  → catches AMC on expiry day:
       run_as_of.date() = today, earnings_date = today, expiry_date = today
       → in_window = TRUE

────────────────────────────────────────────────────────────────────────
earnings.earnings_in_contract_life  (TIMESTAMP — "does the option's LIFE span the event?")

  earnings_in_contract_life = (event_ts <= expiry_close_ts)

  Specifically for expiry-day earnings:
    - AMC on expiry day:  event_ts (16:30) <= expiry_close_ts (16:00) → FALSE
                          (option dies before announcement)
    - BMO on expiry day:  event_ts (07:30) <= expiry_close_ts (16:00) → TRUE
                          (option alive overnight; captures BMO gap at next open)
    - DMH on expiry day:  event_ts (12:00) <= expiry_close_ts (16:00) → TRUE
    - earnings BEFORE expiry: always TRUE

────────────────────────────────────────────────────────────────────────
earnings.quote_snapshot_relative_to_event  (CRITICAL for post-market predictor use)

  pre_event   if quote_snapshot_as_of <  event_ts → IV reflects forthcoming event
  post_event  if quote_snapshot_as_of >= event_ts → IV is post-event vol
  not_applicable  if no earnings in scope

  → predictor at run_as_of=16:35 with quote_snapshot_as_of=16:00 and event_ts=16:30:
      16:00 < 16:30 → "pre_event"
      → bot reads IV correctly as forward-looking (includes earnings premium)

────────────────────────────────────────────────────────────────────────
SUMMARY OF AMC vs BMO ON EXPIRY DAY (run BEFORE the event):

                       in_window  in_contract_life  qs_rel_to_event  Bot interpretation
                       ─────────  ────────────────  ───────────────  ──────────────────
  AMC on expiry day    TRUE       FALSE             pre_event        Earnings is on the calendar
                                                                     but option dies before it →
                                                                     this row's IV does NOT include
                                                                     earnings move; pair with
                                                                     post_earnings row
  BMO on expiry day    TRUE       TRUE              pre_event        Option captures the BMO gap
                                                                     overnight → IV includes it

POST-RUN SCENARIO (run AFTER an AMC event, snapshot still pre-event from frozen close):
  run_as_of            = 16:35 ET   (after announcement)
  quote_snapshot_as_of = 16:00 ET   (frozen close, pre-announcement)
  event_ts             = 16:30 ET

  in_window: today >= today AND today <= expiry → TRUE
  in_contract_life: 16:30 <= 16:00 → FALSE
  qs_rel_to_event: 16:00 < 16:30 → "pre_event"
  → Bot reads: "Earnings is on calendar (in_window), but the option dies before announcement
                (in_contract_life=false), and my IV snapshot was taken pre-announcement
                (qs_rel_to_event=pre_event). So this row's IV reflects the pre-release uncertainty
                but won't include the actual announcement move. Pair with the post_earnings row
                for the post-event IV."
```

### Pre/post earnings expiry selection rules

When `earnings.in_window` is true for a ticker's primary expiry, the script may emit additional rows:

```
PRE-EARNINGS ROW (emitted when an earnings event is in_window for the primary expiry AND
                  the primary expiry already has earnings_in_contract_life=true,
                  meaning the primary captures the event but we ALSO want a clean
                  pre-event reference):

  pre_earnings_expiry = LAST chain expiry such that earnings_in_contract_life=false
                        AND expiry_close_ts <= event_ts

  (If no such expiry exists earlier than primary, pre_earnings row is omitted.
   If primary IS already pre-event, the primary itself gets role=pre_earnings
   and no separate row is needed.)

POST-EARNINGS ROW (emitted when primary expiry has earnings_in_contract_life=false,
                   so primary excludes the event and we need a post-event view):

  post_earnings_expiry = FIRST chain expiry such that earnings_in_contract_life=true
                         AND its expiry_close_ts > event_ts

ROLE TAGGING:
  - AMC on expiry day:  primary row gets role=pre_earnings, separate post_earnings row added
  - BMO on expiry day:  primary row gets role=post_earnings (it captures the BMO overnight gap)
  - earnings BEFORE primary expiry (any time): primary gets role=post_earnings, pre_earnings row added
  - earnings AFTER primary expiry but within +5 days: primary gets context_flag earnings_just_after_window
                                                       no extra rows
```

### `quality_flags` catalog (data-integrity defects only)

```
wide_spread                    — any leg spread_bps > config.spread_warn_bps. Mid is NEVER nulled for wide spread; raw preserved. Bot decides.
stale_last_rejected            — fell back to last but tick_age > freshness threshold; this leg's mid set to null
iv_disagreement                — |call_iv - put_iv| > config.iv_disagreement_warn_pp
atm_distance_high              — atm_distance_pct > config.atm_distance_warn_pct
strike_retry_used              — first-nearest strike didn't qualify; picked a back-up
iv_sanitized                   — call_iv or put_iv was NaN/-1/out-of-range; that leg's iv field SET TO null (not zero — explicit absence)
multiplier_nonstandard         — multiplier ≠ 100 (post-split adjusted contract)
```

### `context_flags` catalog (semantic context — NOT defects)

```
includes_earnings_premium      — earnings_in_contract_life=true; the row's EM contains the event
expiry_before_known_earnings   — earnings in_window=true BUT earnings_in_contract_life=false (AMC-on-expiry case)
amc_expiry_day                 — picked expiry IS the AMC earnings day
earnings_just_after_window     — earnings within config.earnings_just_after_window_days AFTER expiry
// (earnings_calendar_pit_unsafe REMOVED in r3: pit_safe flag lives in top-level data_sources block.
//  Backtest/historical mode reads `data_sources.earnings_calendar.pit_safe` and gates on it.
//  Per-row flagging when ALL Yahoo runs are pit_safe=false adds zero signal; spams every row.)
```

---

## Example 1 — clean live row (HIGH quality)

```jsonc
{
  "schema_version": "iv_moves.v2",
  "row_id":         "AAPL:20260618:non_earnings",
  "run_id":         "iv_moves.v2:2026-05-14T13:30:00Z:33",

  "ticker": "AAPL", "spot": 297.34, "spot_source": "live",
  "expiry": "20260618",                              // Juneteenth-adjusted: nominal 06-19 → actual 06-18 (Thursday)
  "is_primary": true, "earnings_role": "non_earnings",
  "dte": 35, "dte_fractional": 34.7,
  "atm_strike": 297.0, "atm_distance_pct": 0.114, "multiplier": 100,

  "call": { "conid": 838693204, "bid": 8.40, "ask": 8.55, "last": 8.47,
            "mid": 8.475, "mid_source": "bid_ask_mid", "iv": 0.2467,
            "spread_bps": 177.0, "tick_age_seconds": 1.2, "tick_age_known": true },
  "put":  { "conid": 838693205, "bid": 8.20, "ask": 8.35, "last": 8.27,
            "mid": 8.275, "mid_source": "bid_ask_mid", "iv": 0.2473,
            "spread_bps": 181.0, "tick_age_seconds": 0.8, "tick_age_known": true },

  "expected_move_dollars": 16.75, "expected_move_pct": 0.0563,
  "iv_avg": 0.2470, "iv_disagreement_pp": 0.06,
  "em_from_iv_dollars": 21.04, "em_from_iv_pct": 0.0708, "em_method_ratio": 0.7960,

  "data_tier": "live", "quote_freshness": "fresh", "iv_quality": "HIGH",
  "quality_flags": [], "context_flags": [], "status": "OK",

  "earnings": { "next_date": "2026-07-31", "next_time": "AMC", "next_time_source": "yahoo",
                "in_window": false, "earnings_in_contract_life": false,
                "calendar_source": "yahoo", "calendar_as_of": "2026-05-14T08:00:00Z",
                "calendar_pit_safe": false },

  "diagnostics": []
}
```

Bot reads: `data_tier=live, quote_freshness=fresh, iv_quality=HIGH, quality_flags=[]` → trust.

---

## Example 2 — delayed fallback BUT fresh tick (delayed ≠ stale)

OPRA appears unentitled mid-day (transient or contract-specific). Phase 2's auto-fallback retries with type=3 (delayed). The delayed tick received 12 seconds ago.

```jsonc
{
  "schema_version": "iv_moves.v2",
  "row_id":         "MSFT:20260618:non_earnings",
  "run_id":         "iv_moves.v2:2026-05-14T13:30:00Z:33",

  "ticker": "MSFT", "spot": 422.10, "spot_source": "live",
  "expiry": "20260618",                              // Juneteenth-adjusted
  "is_primary": true, "earnings_role": "non_earnings",
  "dte": 35, "dte_fractional": 34.7,
  "atm_strike": 422.5, "atm_distance_pct": 0.095, "multiplier": 100,

  "call": { "conid": 444111, "bid": 9.80, "ask": 9.95, "last": 9.87,
            "mid": 9.875, "mid_source": "bid_ask_mid", "iv": 0.2103,
            "spread_bps": 151.9, "tick_age_seconds": 12.4, "tick_age_known": true },
  "put":  { "conid": 444112, "bid": 9.55, "ask": 9.70, "last": 9.62,
            "mid": 9.625, "mid_source": "bid_ask_mid", "iv": 0.2098,
            "spread_bps": 156.1, "tick_age_seconds": 9.7, "tick_age_known": true },

  "expected_move_dollars": 19.50, "expected_move_pct": 0.0462,
  "iv_avg": 0.2101, "iv_disagreement_pp": 0.05,
  "em_from_iv_dollars": 27.83, "em_from_iv_pct": 0.0659, "em_method_ratio": 0.7008,

  "data_tier":       "fallback_delayed",   // type=1 returned nulls; retried with type=3 successfully
  "quote_freshness": "fresh",               // BOTH legs tick within 300s threshold → fresh despite delayed
  "iv_quality":      "MEDIUM",              // exactly one issue: data_tier ≠ live (no double-count — see derivation rules)

  "quality_flags": [],                      // data_tier captures the fallback; no separate flag (would double-count)
  "context_flags": [],
  "status": "OK",

  "earnings": { "next_date": "2026-07-29", "next_time": "AMC", "next_time_source": "yahoo",
                "in_window": false, "earnings_in_contract_life": false,
                "calendar_source": "yahoo", "calendar_as_of": "2026-05-14T08:00:00Z",
                "calendar_pit_safe": false },

  "diagnostics": [
    "live (type=1) returned all-null during options RTH; auto-fell-back to type=3 delayed; data is 15-min lagged but tick is fresh in that lagged stream"
  ]
}
```

Bot reads: `data_tier=fallback_delayed, quote_freshness=fresh, iv_quality=MEDIUM` → use with awareness it's 15-min behind real-time.

---

## Example 3 — truly stale-last-rejected (separate concept from delayed)

Illiquid small-cap; bid/ask wide, last trade hours old. Distinct from "delayed".

```jsonc
{
  "schema_version": "iv_moves.v2",
  "row_id":         "ACAD:20260618:non_earnings",
  "run_id":         "iv_moves.v2:2026-05-14T13:30:00Z:33",

  "ticker": "ACAD", "spot": 17.45, "spot_source": "live",
  "expiry": "20260618",                              // Juneteenth-adjusted
  "is_primary": true, "earnings_role": "non_earnings",
  "dte": 35, "dte_fractional": 34.7,
  "atm_strike": 17.50, "atm_distance_pct": 0.287, "multiplier": 100,

  "call": { "conid": 666111, "bid": null, "ask": null, "last": 1.20,
            "mid": null, "mid_source": "last_stale_rejected", "iv": 0.6521,
            "spread_bps": null, "tick_age_seconds": 3847, "tick_age_known": true },
  "put":  { "conid": 666112, "bid": 0.95, "ask": 2.50, "last": 1.40,
            "mid": 1.725, "mid_source": "bid_ask_mid", "iv": 0.6589,
            "spread_bps": 8985.5, "tick_age_seconds": 920, "tick_age_known": true },

  "expected_move_dollars": null,             // can't compute: call.mid null
  "expected_move_pct":     null,
  "iv_avg": 0.6555, "iv_disagreement_pp": 0.68,
  "em_from_iv_dollars": 3.59, "em_from_iv_pct": 0.2057, "em_method_ratio": null,

  "data_tier":       "live",                 // we DID get live entitlement, just bad quote conditions
  "quote_freshness": "stale",                // call leg tick_age > 300s threshold
  "iv_quality":      "LOW",                  // 3 issues per derivation rule:
                                              //   (2) quote_freshness=stale → 1
                                              //   (3) call leg mid_source ≠ bid_ask_mid (last_stale_rejected) → 1
                                              //   (6) wide_spread quality_flag (not implied by 1-5) → 1
                                              //   → issue_count=3 → LOW

  "quality_flags": ["stale_last_rejected", "wide_spread"],   // iv_disagreement_pp 0.68 < 3.0 threshold → NOT flagged
  "context_flags": [],
  "status": "PARTIAL",

  "earnings": { "next_date": "2026-08-12", "next_time": "BMO", "next_time_source": "yahoo",
                "in_window": false, "earnings_in_contract_life": false,
                "calendar_source": "yahoo", "calendar_as_of": "2026-05-14T08:00:00Z",
                "calendar_pit_safe": false },

  "diagnostics": [
    "call leg: last tick 64 minutes old; bid/ask absent; mid set null (rejected as stale)",
    "put leg: spread 8985 bps (90%) — wide but mid retained for caller's reference",
    "call_iv 65.2% vs put_iv 65.9% are close, but emitted IV is from option-model not live quote"
  ]
}
```

Bot reads: `quote_freshness=stale, iv_quality=LOW, status=PARTIAL` → IV is illustrative only, don't trade.

---

## Example 4 — AMC expiry-day (pre-earnings, EXPIRY HAPPENS BEFORE THE ANNOUNCEMENT)

```jsonc
{
  "schema_version": "iv_moves.v2",
  "row_id":         "NVDA:20260515:pre_earnings",
  "run_id":         "iv_moves.v2:2026-05-14T13:30:00Z:33",

  "ticker": "NVDA", "spot": 145.32, "spot_source": "live",
  "expiry": "20260515",
  "is_primary": false,                       // primary picked the next monthly; this row is generated because earnings in window
  "earnings_role": "pre_earnings",
  "dte": 1, "dte_fractional": 0.92,
  "atm_strike": 145.0, "atm_distance_pct": 0.22, "multiplier": 100,

  "call": { "conid": 234567, "bid": 1.20, "ask": 1.25, "last": 1.22,
            "mid": 1.225, "mid_source": "bid_ask_mid", "iv": 0.4321,
            "spread_bps": 408.2, "tick_age_seconds": 2.1, "tick_age_known": true },
  "put":  { "conid": 234568, "bid": 0.90, "ask": 0.95, "last": 0.92,
            "mid": 0.925, "mid_source": "bid_ask_mid", "iv": 0.4288,
            "spread_bps": 540.5, "tick_age_seconds": 1.5, "tick_age_known": true },

  "expected_move_dollars": 2.15, "expected_move_pct": 0.0148,
  "iv_avg": 0.4305, "iv_disagreement_pp": 0.33,
  "em_from_iv_dollars": 3.27, "em_from_iv_pct": 0.0225, "em_method_ratio": 0.657,

  "data_tier": "live", "quote_freshness": "fresh", "iv_quality": "MEDIUM",
  "quality_flags": [],                       // no data-integrity issues
  "context_flags": ["amc_expiry_day", "expiry_before_known_earnings"],
  "status": "OK",

  "earnings": {
    "next_date": "2026-05-15", "next_time": "AMC", "next_time_source": "yahoo",
    "in_window": true,
    "earnings_in_contract_life": false,      // option expires 16:00 ET; earnings ~16:30 ET → not in life
    "calendar_source": "yahoo", "calendar_as_of": "2026-05-14T08:00:00Z",
    "calendar_pit_safe": false
  },

  "diagnostics": [
    "Expiry 20260515 is the AMC earnings day; option expires at 16:00 ET; earnings released ~16:30 ET; option's life does NOT include the announcement",
    "Pair this with the post_earnings row (NVDA:20260522:post_earnings) for a clean event-implied move comparison"
  ]
}
```

Bot reads: `context_flags includes amc_expiry_day` → KNOWS this row excludes earnings. Pairs with `NVDA:20260522:post_earnings` for the event-aware view.

---

## Example 5 — `expiry_ladder` (per-ticker, separate from `results`)

```jsonc
{
  "ticker": "NVDA",
  "spot":   145.32,
  "as_of":  "2026-05-14T13:30:00Z",
  "candidate_expiries": [
    { "expiry": "20260515", "dte": 1, "dte_fractional": 0.92, "type": "weekly",
      "distance_from_target_dte_days": 29,
      "covers_earnings_event": false, "is_amc_earnings_day": true,
      "selected_for_compute": true,
      "row_ids": ["NVDA:20260515:pre_earnings"] },

    { "expiry": "20260522", "dte": 8, "dte_fractional": 7.92, "type": "weekly",
      "distance_from_target_dte_days": 22,
      "covers_earnings_event": true, "is_amc_earnings_day": false,
      "selected_for_compute": true,
      "row_ids": ["NVDA:20260522:post_earnings"] },

    { "expiry": "20260618",                                       // Juneteenth-adjusted: nominal 06-19 holiday → actual 06-18
      "dte": 35, "dte_fractional": 34.7, "type": "monthly",
      "distance_from_target_dte_days": 5,
      "covers_earnings_event": true, "is_amc_earnings_day": false,
      "selected_for_compute": false,
      "row_ids": [] },

    { "expiry": "20260717", "dte": 64, "dte_fractional": 63.7, "type": "monthly",
      "distance_from_target_dte_days": 34,
      "covers_earnings_event": true, "is_amc_earnings_day": false,
      "selected_for_compute": false,
      "row_ids": [] },

    { "expiry": "20270116", "dte": 247, "dte_fractional": 246.7, "type": "leap",
      "distance_from_target_dte_days": 217,
      "covers_earnings_event": true, "is_amc_earnings_day": false,
      "selected_for_compute": false,
      "row_ids": [] }
  ]
}
```

Bot reads: knows the option alternatives, can reason about "what if 7DTE vs 30DTE vs 60DTE." Doesn't need to re-query.

---

## What's REMOVED vs revision 1

```
✗ Single `expiry_role` field          → split into is_primary + earnings_role
✗ STALE as an iv_quality value         → replaced by quote_freshness=stale + iv_quality=LOW
✗ "historical" in data_tier enum       → marked RESERVED, not implemented in v2
✗ `quality_flags` containing context   → split off into context_flags
✗ Earnings-move math in diagnostics    → removed; bot reasons over both rows
✗ em_method_ratio interpretation       → diagnostic only; no interpretation strings
✗ Example 2 internal inconsistency     → replaced with proper fallback_delayed/fresh example
```

## What's ADDED vs revision 1

```
✓ run_id top-level + row_id per row    (stable IDs for evidence catalog)
✓ expiry_ladder per ticker             (≤7 entries, exposes choice space)
✓ Three orthogonal quality dims        (data_tier, quote_freshness, iv_quality)
✓ Two separate flag lists              (quality_flags + context_flags)
✓ data_sources block top-level         (provenance per source: vendor + as_of + pit_safe)
✓ earnings_in_contract_life            (timing-aware: AMC-on-expiry → false even if in_window=true)
✓ tick_age_known per leg               (handles IBKR not surfacing timestamps)
✓ All config thresholds listed         (auditable + tunable)
✓ 5 example rows                       (one per ChatGPT spec)
✓ Reserved enum values marked          (no schema promises code won't fulfill)
```

## What `is_primary` means for `expiry_ladder.selected_for_compute`

```
The script:
  1. Picks the "primary" expiry per the user's --target-dte (or default monthly)
  2. Sets is_primary=true for that expiry's row
  3. If earnings is in_window AND earnings_in_contract_life:
       → also emit a pre_earnings row (for the earnings day expiry if it exists)
  4. If earnings is in_window AND NOT earnings_in_contract_life:
       → also emit a post_earnings row (first expiry AFTER the announcement)
  5. Each selected expiry's row_ids populated; non-selected entries have row_ids=[]
```

## Implementation order (unchanged from r1, reaffirmed)

```
1. Schema-versioning shim + run_id/row_id + envelope/config block
2. Tier 1 — core safety (NaN/-1, stale last, mdt=1+nulls, holiday picker, fallback)
3. Tier 2 — transparency (atm_distance, iv_disagreement, multiplier, iv_quality, three-dim split)
4. Earnings dual-expiry (Yahoo MCP + cache + contract-life-aware roles)
5. expiry_ladder per ticker
6. Tests (9 new + existing 43)
7. README rewrite (drop "no doubt" framing)
8. Full universe re-run + verification + signed-off sample artifact for predictor consumption

No mutation of prediction_result.v1, learner_result.v1, learner memory.
```
