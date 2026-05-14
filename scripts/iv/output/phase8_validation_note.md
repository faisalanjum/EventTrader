# Phase 8 — Full-Universe Validation Note (v4 regen)

**Schema**: `iv_moves.v2`
**Status**: Arithmetic self-consistency validated. Vendor differences within
methodology noise. v4 semantic fixes (`qs_rel_to_event=not_applicable`,
timestamp-based secondary picker, `last_only_no_iv` flag, in-contract-life
lower bound) verified on regenerated universe.

> ⚠️ This run was executed **after the 4pm ET close** (run_as_of 16:57 ET).
> The data-tier and iv_quality distributions reflect a fallback-delayed
> snapshot, NOT live-RTH OPRA. Use the v4 artifact for **semantic** field
> validation only. The earlier pre-v4 in-session artifact remains in the
> repo for live-RTH distribution comparison.

## Commands & run handles

### v4 regen (this artifact — CANONICAL)

```bash
python scripts/iv/compute_iv_moves.py \
  --universe-redis \
  --target-dte 30 \
  --port 14003 \
  --client-id 220 \
  --concurrency 20 \
  --market-data-type 1 \
  --output scripts/iv/output/phase8_universe_2026-05-14_v4.json
```

| Field | Value |
|---|---|
| `run_id` | `iv_moves.v2:2026-05-14T20:57:22+00:00:220` |
| `run_as_of` | `2026-05-14T20:57:22+00:00` (**16:57 ET — 57 min past close**) |
| Wall time | ~13 min (concurrency 20) |
| Code commit at run time | `bc595f6` (Phase 4 patch v4) |
| `universe_size` | 783 tickers |
| `total_rows` | 848 (783 primary + **65 dual-row secondaries**) |

### Pre-v4 in-session reference (still on disk for comparison)

```
run_id:    iv_moves.v2:2026-05-14T19:41:32+00:00:188
run_as_of: 15:41 ET (mid-session)
file:      scripts/iv/output/phase8_universe_2026-05-14.json
```

## v4 semantic check results

### Check 1 — `quote_snapshot_relative_to_event` not_applicable

**Rule**: when a row's earnings event is outside BOTH the window AND the contract
life, `qs_rel_to_event` MUST be `not_applicable`, never `pre_event`/`post_event`.

| Snapshot | Stale rows (in_window=False AND in_contract_life=False but qs_rel=pre/post_event) |
|---|---:|
| **v4 regen** | **0** ✓ |
| Pre-v4 in-session (for reference) | 468 (55% of rows had misleading labels) |

v4 distribution: `not_applicable=781`, `pre_event=63`, `post_event=4`.

### Check 2 — `last_only_no_iv` rows demoted to LOW

52 rows triggered the flag. **All 52** carry `iv_quality=LOW`. Zero are
MEDIUM/HIGH. The `derive_iv_quality` non-implied-flag rule correctly
demotes them so the predictor cannot mistake them for clean rows.

Examples:
```
A:20260515:pre_earnings      flags=['atm_distance_high', 'last_only_no_iv']  iv_q=LOW
ALKS:20260618:non_earnings   flags=['last_only_no_iv']                       iv_q=LOW
AMC:20260618:non_earnings    flags=['atm_distance_high', 'last_only_no_iv']  iv_q=LOW
```

### Check 3 — Summary count refresh

| Field | v4 regen | Pre-v4 in-session |
|---|---:|---:|
| total_rows | 848 | 846 |
| OK | 270 (31.8%) | 456 (53.9%) |
| PARTIAL | 544 (64.2%) | 357 (42.2%) |
| NO_QUOTES | 7 | 6 |
| NO_CONID | 27 | 27 |
| data_tier `live` | 520 (61.3%) | 684 (80.8%) |
| data_tier `fallback_delayed` | 301 (35.5%) | 135 (15.9%) |
| iv_quality HIGH | 0 | 25 |
| iv_quality MEDIUM | 237 | 319 |
| iv_quality LOW | 577 | 469 |
| earnings_role `pre_earnings` | **65** | 63 |
| dual-row secondaries (`is_primary=false`) | **65** | 63 |

**Why the deltas vs in-session**:
- **More PARTIAL / fewer OK**: 57 min past close, OPRA stream is empty; most
  rows fall back to delayed which often delivers IV but not bid/ask.
- **Zero HIGH**: `iv_quality=HIGH` requires `data_tier=live`. After-hours
  rows default to `live` only when last-trade ticks from the 4pm close are
  still cached at IBKR, but most need to fall back to delayed.
- **+2 secondaries / +2 pre_earnings**: v4's timestamp-aware secondary
  picker catches 2 additional same-day cases that the date-only logic
  silently missed.

### Check 4 — Self-consistency math (Phase A repeat on regenerated artifact)

| Identity | Failures |
|---|---:|
| `iv_avg = (call_iv + put_iv) / 2` | 0 |
| `em_from_iv_dollars = spot × iv_avg × √(dte/365)` | 0 |
| `em_from_iv_pct = em_from_iv_dollars / spot` | 0 |
| `expected_move_dollars = call_mid + put_mid` | 0 |

Arithmetic identities continue to hold across the regenerated 848 rows.

## Top failure causes (unchanged across runs)

### `NO_CONID` (27) — delisted / M&A names

Same list as the in-session run: `ALEX AMED AXL BIGC BPMC CFLT DNB EXAS GMS HOLX ...`
Correct fail-safe — these names have no IBKR conId; predictor consumers should drop them.

### `NO_QUOTES` (7) — null prices even after delayed fallback

Names that returned null on all legs even after the fallback path:
`ABM APLS DHR KKR MASI MMM` + 1 more in the v4 snapshot. Mostly transient
post-close IBKR pacing.

## What this run does NOT validate

- **Live-RTH OPRA distribution** — for that, use the pre-v4 in-session
  artifact (`phase8_universe_2026-05-14.json`) which has ~80% `data_tier=live`.
- **Vendor IV bulk comparison** — already done in the earlier validation
  pass (50 names, Yahoo, mean bias −1.05pp). Re-doing post-close would
  add noise (Yahoo also reflects after-hours staleness).

## What this run DOES validate (canonical)

- v4 patch is live in production code (`bc595f6`).
- Zero stale `qs_rel_to_event` cases on a fresh artifact.
- All `last_only_no_iv` rows correctly demoted to LOW.
- Timestamp-aware secondary picker emits the same dual-row invariants
  (every emitted row resolves into `expiry_ladders[ticker]`).
- 224/224 unit tests still pass.

## Files

| Path | Role |
|---|---|
| `scripts/iv/output/phase8_universe_2026-05-14_v4.json` | **CANONICAL v4 artifact** |
| `scripts/iv/output/phase8_universe_2026-05-14.json` | Pre-v4 in-session reference (kept for live-RTH distribution) |
| `scripts/iv/output/phase8_validation_note.md` | This document |

## Out of scope

Predictor / learner / MCP files untouched. Phase 8 is purely a live
validation of the artifact emitted by Phases 1–7 + v4 patches.
