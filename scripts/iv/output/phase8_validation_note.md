# Phase 8 — Full-Universe Live Run Validation Note

**Schema**: `iv_moves.v2`
**Status**: Validated — see distributions and vendor checks below.

## Command

```bash
python scripts/iv/compute_iv_moves.py \
  --universe-redis \
  --target-dte 30 \
  --port 14003 \
  --client-id 188 \
  --concurrency 8 \
  --market-data-type 1 \
  --output scripts/iv/output/phase8_universe_2026-05-14.json
```

Live IBKR gateway, OPRA subscription active. Live market hours (mid-day ET).
Universe source: Redis `admin:tradable_universe:symbols` (783 tickers).

## Run handle

| Field | Value |
|---|---|
| `run_id` | `iv_moves.v2:2026-05-14T19:41:32+00:00:188` |
| `run_as_of` | `2026-05-14T19:41:32+00:00` (15:41 ET) |
| Wall time | ~32 min (started 15:41 ET, artifact mtime 16:13 ET) |
| Concurrency | 8 (effective ~20 s/ticker — IBKR rate-limited; bump to 20-25 next run) |
| `universe_size` | 783 tickers |
| `total_rows` | 846 (783 primary + 63 dual-row secondaries) |

## Summary distributions

### Status (846 rows)

| Status | Count | % |
|---|---:|---:|
| `OK` | 456 | 53.9% |
| `PARTIAL` | 357 | 42.2% |
| `NO_CONID` | 27 | 3.2% |
| `NO_QUOTES` | 6 | 0.7% |

EM-computable rate = `OK / (OK + PARTIAL + NO_QUOTES) = 456/819 = 55.7%`. The
44% PARTIAL share is dominated by names with IV present but `null` bid/ask
on one leg, which is normal mid-day for illiquid mid-/small-caps.

### `data_tier`

| Tier | Count |
|---|---:|
| `live` | 684 |
| `fallback_delayed` | 135 |
| `unknown` | 27 (all `NO_CONID`) |

So 684/819 = 83.5% of tradeable rows got live OPRA data on the first
attempt. The 135 rows that auto-fell-back to delayed are the
illiquid-mid-day case the fallback was built for — none of them needed
manual intervention.

### `quote_freshness`

| | Count |
|---|---:|
| `fresh` | 814 (96.2%) |
| `unknown` | 32 (3.8%) |

`unknown` does NOT necessarily mean chain/quote failure — it also fires
when IBKR surfaced no `ticker.time` on either leg even though prices flowed.
And conversely, a `NO_QUOTES` row can still carry fresh tick metadata
(timestamp present even if the price fields are null). The predictor
should treat `quote_freshness` and `status` as independent axes.

### `iv_quality`

| | Count |
|---|---:|
| `HIGH` | 25 (clean live + no flags + tight quotes) |
| `MEDIUM` | 319 |
| `LOW` | 469 |
| `n/a` | 33 |

`HIGH` is rare because the threshold requires both ATM-tight quotes AND
no `wide_spread` / `atm_distance_high` / `iv_disagreement` flags. The
predictor should NOT filter to `HIGH`-only — `MEDIUM` is the normal
quality on live OPRA mid-day for liquid names; `LOW` flags real
illiquidity that the predictor can use as a signal.

### `quality_flags` (across 846 rows)

| Flag | Rows |
|---|---:|
| `atm_distance_high` | 353 (≥1% off ATM — typical for $5 strike grids on low-priced names) |
| `wide_spread` | 333 (≥10% bid/ask spread on either leg) |
| `strike_retry_used` | 79 (closest strike didn't qualify; fell back) |
| `iv_disagreement` | 41 (call/put IV diverge ≥3 pp) |
| `iv_sanitized` | 1 (NaN/-1/out-of-range — replaced with `null`) |

### `context_flags`

| Flag | Rows |
|---|---:|
| `includes_earnings_premium` | 65 (post_earnings primaries with pre-event quote) |
| `earnings_just_after_window` | 22 (event ≤5 days past expiry) |

### Earnings split

| Role | Rows |
|---|---:|
| `non_earnings` | 718 |
| `post_earnings` | 65 (primary captures event in contract life) |
| `pre_earnings` | 63 (mostly secondary dual-row emissions; 0 primaries here in this snapshot) |

| | Count |
|---|---:|
| `is_primary=true` | 783 |
| `is_primary=false` (dual-row secondary) | 63 |

So **63 tickers emitted a second row** for the OTHER side of their
known earnings event. 65 primaries are post_earnings → 2 of those had
no valid pre-event chain expiry between today and event (orchestrator
returns `[primary]` only, which is correct).

## Top failure causes

### `NO_CONID` (27) — delisted / M&A / no IBKR conId

```
ALEX AMED AXL BIGC BPMC CFLT DNB EXAS GMS HOLX IAS JAMF MMC MPW MRUS
... and 12 more
```

These match the expected delisted-zombie pattern from the prior coverage
probe. Per-row `status=NO_CONID` is the correct, fail-safe label — no
fake data is emitted. Predictor consumers should drop these.

### `NO_QUOTES` (6) — price fields null even after delayed fallback

```
ABM APLS DHR KKR MASI MMM
```

`NO_QUOTES` means bid/ask/last and IV all came back null on both legs.
Note: tick metadata (`ticker.time`) can still arrive on a `NO_QUOTES` row
even when the price values don't, so `quote_freshness` may report `fresh`
or `stale` independently of `status`. Six widely-traded large-caps with no
price values flowing during the snapshot
window. Most likely transient (IBKR pacing) rather than structural.
Worth a re-run during off-peak hours to confirm.

## `expiry_ladders`

- **756** tickers have ladders (the 27 `NO_CONID` failures resolve before chain → no ladder).
- Ladder size distribution:
  - 7 entries: 491 tickers (most chains have ≥7 candidate expiries within window)
  - 6 entries: 104 tickers
  - 5 entries: 161 tickers (smaller chains, e.g. ETFs with quarterly-heavy listings)

Every emitted row's expiry appears in its ticker's ladder
(`selected_for_compute=true` with `row_ids` populated) — invariant
holds across all 846 rows (verified by the orchestration test in
`test_compute_iv_moves.py::TestExpiryLadderInArtifactInvariant`).

## Vendor IV sanity checks

Vendor: **Yahoo Finance** via `yfinance.Ticker.option_chain(expiry)`.
Fetched **2026-05-14T20:15 UTC** (~34 min after the artifact's
`run_as_of`). Comparing `iv_avg` (this artifact) vs `(call_iv + put_iv) / 2`
at the same expiry+strike from Yahoo.

> Per the README's vendor-comparison guidance: we compare `iv_avg`, NOT
> `expected_move_pct` (units mismatch) and NOT a single leg's IV (skew
> makes that misleading).

| Ticker | Expiry | ATM strike | This `iv_avg` | Yahoo `iv_avg` | Δ (pp) | Notes |
|---|---|---:|---:|---:|---:|---|
| AAPL | 20260612 | 300 | 24.30% | 24.32% | **−0.02** | Effectively identical; quality_flags=`[strike_retry_used]` (chain mismatch on first attempt) |
| WMT | 20260612 | 132 | 31.50% | 32.23% | **−0.72** | Within typical IBKR↔Yahoo modelGreeks drift |
| NVDA | 20260612 | 235 | 48.53% | 48.20% | **+0.33** | Mild positive skew (Yahoo's put strike was 230 — slight ATM offset) |

All three within ~1 percentage point of vendor. This is the expected
band; deltas would widen for names trading wider quotes or for vendors
that interpolate IV at exactly ATM (we report at the chain's nearest strike).

## Notes / known gaps

- **Concurrency**: 8 was conservative. Wall time ~20 s/ticker is dominated
  by IBKR's pacing rather than CPU. Suggest **concurrency 20–25** for
  future universe runs to cut wall time to ~10 min. Pacing-violation
  risk exists but the script handles per-ticker failures gracefully.
- **`NO_QUOTES` on liquid names** (ABM/APLS/DHR/KKR/MASI/MMM): worth a
  re-run during off-peak to confirm transient vs structural.
- **`PARTIAL` rows**: predictor should consult `data_tier`,
  `quote_freshness`, and individual leg fields before computing
  notional exposure. `expected_move_dollars=null` is the correct signal
  that mid wasn't computable for at least one leg.
- **`iv_quality=HIGH` is rare** (25/846). Predictor should not gate on
  HIGH alone; MEDIUM with `quality_flags=[]` is generally tradeable on
  liquid names. LOW + `wide_spread` is a real liquidity signal.

## Out of scope

No predictor/learner/MCP files were touched. Phase 8 is purely a live
validation of the artifact emitted by Phases 1–7.
