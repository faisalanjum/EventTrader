"""Compute implied-volatility + IV-based expected moves for a US-equity universe.

PRIMARY METHOD — ATM straddle at a target expiry:
    expected_move_dollars = call_atm.mid + put_atm.mid
    expected_move_pct     = expected_move_dollars / spot

SANITY-CHECK METHOD — IV from modelGreeks scaled to expiry:
    expected_move_from_iv = spot * iv_avg * sqrt(dte / 365)
    (1-sigma move under the lognormal-vol assumption)

The two methods should agree within ~10% in normal markets. Divergence signals
either earnings premium, dividend, or illiquid quotes.

DESIGN DECISIONS LOCKED IN 2026-05-14:
  expiry      : --target-dte=N (configurable); default = next monthly (3rd Friday)
  earnings    : if earnings between today and expiry → emit BOTH expiries (pre + post)
  liquidity   : NO spread filter; compute spread_bps; caller decides
  output      : JSON file + stdout table

PRE-OPRA   : status will mostly be NO_QUOTES (call/put bid/ask all null).
             Pipeline still validated end-to-end: chain, strike picker, math.
POST-OPRA  : ~100% OK expected (verified: 756/756 of tradeable universe has listed options).

Run:
    python scripts/iv/compute_iv_moves.py \
        [--tickers AAPL,JPM,XLK | --tickers-file path | --universe-redis] \
        [--target-dte 30] \
        [--earnings-check] \
        [--output scripts/iv/output/iv_$(date +%Y-%m-%d).json]
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import math
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path

from ib_async import IB
from ib_async.contract import Stock, Option


# ---------------------------------------------------------------------------
# SCHEMA v2 — versioning, constants, and runtime config
# ---------------------------------------------------------------------------
# Schema reference: scripts/iv/SCHEMA_v2.md (revision 8)
# Phase 1 scope: schema-versioning shim only (envelope + run_id/row_id).
# Tier 1/2/earnings fields land in subsequent phases.

SCHEMA_VERSION = "iv_moves.v2"

# US market structural constants (real-world facts, surfaced in artifact for audit).
# These are NOT fixtures — they are exchange conventions; CME/CBOE/OPRA close at 16:00 ET.
MARKET_CONVENTIONS = {
    "options_market_close_et":  "16:00",   # standard US options market close
    "amc_conventional_time_et": "16:30",   # after-market-close release convention
    "bmo_conventional_time_et": "07:30",   # before-market-open release convention
    "dmh_conventional_time_et": "12:00",   # during-market-hours (rare)
    "iv_annualization_days":    365,       # calendar-day basis for IV → expected move
}

# Quality / threshold defaults (tunable via future CLI flags).
DEFAULT_CONFIG = {
    "tick_freshness_threshold_sec":    300,
    "spread_warn_bps":                1000,
    "atm_distance_warn_pct":           1.0,
    "iv_disagreement_warn_pp":         3.0,
    "iv_min_valid":                    0.01,
    "iv_max_valid":                    5.0,
    "earnings_just_after_window_days":   5,
    "live_to_delayed_fallback_enabled": True,
    "expiry_ladder_max_entries":         7,
}


# ---------------------------------------------------------------------------
# Calendar helpers
# ---------------------------------------------------------------------------

def third_friday(year: int, month: int) -> dt.date:
    """The 3rd Friday of (year, month) — the standard US monthly expiry."""
    first = dt.date(year, month, 1)
    # Friday = weekday 4
    days_to_first_friday = (4 - first.weekday()) % 7
    first_friday = first + dt.timedelta(days=days_to_first_friday)
    return first_friday + dt.timedelta(days=14)


def next_monthly_expiry(today: dt.date | None = None) -> dt.date:
    """The next standard monthly expiry on or after today."""
    today = today or dt.date.today()
    candidate = third_friday(today.year, today.month)
    if candidate <= today:
        ny = today.year + (1 if today.month == 12 else 0)
        nm = 1 if today.month == 12 else today.month + 1
        candidate = third_friday(ny, nm)
    return candidate


def pick_expiry(available_yyyymmdd: set[str], target_dte: int | None,
                today: dt.date | None = None) -> str | None:
    """Pick the best expiry from the chain.
    target_dte=None → next monthly (≥ today). Else → expiry closest to today + target_dte.
    Returns YYYYMMDD or None if no expiry qualifies.
    """
    today = today or dt.date.today()
    if not available_yyyymmdd:
        return None

    def to_date(s: str) -> dt.date | None:
        try:
            return dt.datetime.strptime(s, "%Y%m%d").date()
        except ValueError:
            return None

    candidates: list[tuple[str, dt.date]] = []
    for s in available_yyyymmdd:
        d = to_date(s)
        if d is None or d <= today:
            continue
        candidates.append((s, d))
    if not candidates:
        return None

    if target_dte is None:
        monthly = next_monthly_expiry(today)
        # Holiday-aware (Tier 1.D): if the nominal 3rd Friday is a market holiday
        # (e.g., 2026-06-19 Juneteenth, or Good Friday), the actual options expiry
        # rolls — typically to the preceding Thursday. We search the chain for the
        # ACTUAL monthly within a small window around the computed 3rd Friday.
        # Order of preference inside the window: exact match → prior Thursday →
        # next available Friday (e.g., 4th-Friday roll if exchange chose that).
        HOLIDAY_SEARCH_DAYS = 3
        window_lo = monthly - dt.timedelta(days=HOLIDAY_SEARCH_DAYS)
        window_hi = monthly + dt.timedelta(days=HOLIDAY_SEARCH_DAYS)
        in_window = [(s, d) for s, d in candidates if window_lo <= d <= window_hi]
        if in_window:
            # Prefer exact match, then closest to nominal
            for s, d in sorted(in_window, key=lambda x: (abs((x[1] - monthly).days), x[1])):
                return s
        # No expiry within the ±3 day window — fall through to "next available
        # expiry >= nominal" (original behavior preserved)
        candidates_geq = [(s, d) for s, d in candidates if d >= monthly]
        if candidates_geq:
            return min(candidates_geq, key=lambda x: x[1])[0]
        return min(candidates, key=lambda x: x[1])[0]
    # target_dte specified — pick closest
    target = today + dt.timedelta(days=target_dte)
    return min(candidates, key=lambda x: abs((x[1] - target).days))[0]


def pick_atm_strike(strikes: list[float], spot: float) -> float | None:
    """Return the strike closest to spot, or None if strikes is empty."""
    if not strikes or spot is None or spot <= 0:
        return None
    return min(strikes, key=lambda s: abs(s - spot))


# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------

def safe_mid(bid: float | None, ask: float | None, last: float | None) -> float | None:
    """Midpoint of (bid, ask) if both positive; else last if positive; else None."""
    if bid is not None and ask is not None and bid > 0 and ask > 0:
        return (bid + ask) / 2.0
    if last is not None and last > 0:
        return last
    return None


def spread_bps(bid: float | None, ask: float | None, mid: float | None) -> float | None:
    """((ask-bid)/mid)*1e4. None if any input invalid."""
    if bid is None or ask is None or mid is None or mid <= 0 or ask < bid:
        return None
    return (ask - bid) / mid * 10000.0


def em_from_iv(spot: float, iv: float, dte: int) -> float | None:
    """1-sigma expected move from IV: spot * iv * sqrt(dte/365)."""
    if spot is None or spot <= 0 or iv is None or iv <= 0 or dte is None or dte < 0:
        return None
    return spot * iv * math.sqrt(max(dte, 0) / 365.0)


# ---------------------------------------------------------------------------
# Tier 1 phase 2 helpers (IV sanitize, mid+source, tick_age, data_tier)
# ---------------------------------------------------------------------------

def sanitize_iv(raw_iv, min_valid: float = 0.01, max_valid: float = 5.0) -> tuple[float | None, bool]:
    """Sanitize an IV value. Returns (clean_iv, was_sanitized).

    Tier 1.A fix: ib_async modelGreeks.impliedVol can be NaN, -1, or
    out-of-range. Bare `if iv:` lets NaN through (NaN is truthy as a
    non-zero float). This guard rejects garbage and signals via flag.
    """
    if raw_iv is None:
        return None, False
    try:
        v = float(raw_iv)
    except (TypeError, ValueError):
        return None, True
    if math.isnan(v) or v < min_valid or v > max_valid or v == -1:
        return None, True
    return v, False


def compute_mid_and_source(
    bid: float | None, ask: float | None, last: float | None,
    tick_age_seconds: float | None, freshness_threshold_sec: float = 300.0,
) -> tuple[float | None, str]:
    """Return (mid, mid_source).

    Tier 1.B: never trust stale `last` as a mid. Sources, ordered preference:
      bid_ask_mid          — both bid and ask positive: (bid+ask)/2
      last_fresh           — bid/ask absent but last is positive AND tick within threshold
      last_stale_rejected  — last is positive but tick is stale OR unknown: mid=None
      none                 — no usable data at all
    """
    if bid is not None and ask is not None and bid > 0 and ask > 0:
        return (bid + ask) / 2.0, "bid_ask_mid"
    if last is not None and last > 0:
        if tick_age_seconds is not None and tick_age_seconds < freshness_threshold_sec:
            return last, "last_fresh"
        # last is stale or unknown — DO NOT trust it as mid
        return None, "last_stale_rejected"
    return None, "none"


def derive_data_tier(
    market_data_type: int | None,
    bid: float | None, ask: float | None, last: float | None,
    fell_back_from_live: bool,
) -> str:
    """Per SCHEMA_v2.md derivation rules.

    Note: `live` REQUIRES populated bid/ask/last (mdt=1 alone is not proof of
    live data — ib_async defaults to 1 with no actual ticks). Fallback path is
    a distinct tier from native delayed.
    """
    if fell_back_from_live:
        return "fallback_delayed"
    if market_data_type == 1:
        # live ONLY when at least one populated quote exists
        if (bid and bid > 0) or (ask and ask > 0) or (last and last > 0):
            return "live"
        # mdt=1 + nulls = default-value, not real live data
        return "unknown"
    if market_data_type == 2:
        return "frozen"
    if market_data_type == 3:
        return "delayed"
    if market_data_type == 4:
        return "delayed_frozen"
    return "unknown"


def get_tick_age_seconds(ticker_time, run_time) -> tuple[float | None, bool]:
    """Return (tick_age_seconds, tick_age_known).
    ticker.time is None when IBKR didn't surface a timestamp.
    """
    if ticker_time is None:
        return None, False
    try:
        if isinstance(ticker_time, dt.datetime):
            tt = ticker_time
        else:
            tt = dt.datetime.fromisoformat(str(ticker_time))
        if tt.tzinfo is None:
            tt = tt.replace(tzinfo=dt.timezone.utc)
        age = (run_time - tt).total_seconds()
        return max(0.0, age), True
    except Exception:
        return None, False


# ---------------------------------------------------------------------------
# Tier 2 phase 3 helpers (transparency)
# ---------------------------------------------------------------------------

def compute_atm_distance_pct(strike: float | None, spot: float | None) -> float | None:
    """|strike - spot| / spot * 100. Bot can filter on this directly."""
    if strike is None or spot is None or spot <= 0:
        return None
    return abs(strike - spot) / spot * 100.0


def compute_iv_disagreement_pp(call_iv: float | None, put_iv: float | None) -> float | None:
    """|call_iv - put_iv| in percentage points (0.30 vs 0.27 = 3.0 pp)."""
    if call_iv is None or put_iv is None:
        return None
    return abs(call_iv - put_iv) * 100.0


def derive_quote_freshness(
    call_age: float | None, call_known: bool,
    put_age: float | None, put_known: bool,
    threshold: float,
) -> str:
    """fresh | stale | unknown — independent of data_tier (delayed ≠ stale).

    fresh   = BOTH legs have known age AND tick_age < threshold
    stale   = either leg has known age >= threshold
    unknown = any leg's age is not known
    """
    if not call_known or not put_known:
        return "unknown"
    if (call_age is not None and call_age >= threshold) or (put_age is not None and put_age >= threshold):
        return "stale"
    return "fresh"


def derive_iv_quality(
    status: str,
    data_tier: str,
    quote_freshness: str,
    call_mid_source: str,
    put_mid_source: str,
    iv_disagreement_pp: float | None,
    atm_distance_pct: float | None,
    quality_flags: list[str],
    config: dict | None = None,
) -> str:
    """HIGH | MEDIUM | LOW | n/a per SCHEMA_v2 r6 derivation rules.

    issue_count = count of TRUE conditions among:
      (1) data_tier != live
      (2) quote_freshness != fresh
      (3) any leg mid_source != bid_ask_mid
      (4) iv_disagreement_pp >= threshold
      (5) atm_distance_pct >= threshold
      (6) any quality_flag not implied by 1-5 (e.g., multiplier_nonstandard,
          strike_retry_used, iv_sanitized, wide_spread)

    HIGH    issue_count == 0 AND data_tier == live (must be clean AND live)
    MEDIUM  issue_count == 1
    LOW     issue_count >= 2  OR  data_tier in (frozen, delayed_frozen)
    n/a     status not in (OK, PARTIAL)
    """
    if status not in ("OK", "PARTIAL"):
        return "n/a"
    cfg = config or DEFAULT_CONFIG
    issues = 0
    # (1) data_tier
    if data_tier != "live":
        issues += 1
    # (2) freshness
    if quote_freshness != "fresh":
        issues += 1
    # (3) mid source not bid_ask_mid
    if call_mid_source != "bid_ask_mid" or put_mid_source != "bid_ask_mid":
        issues += 1
    # (4) iv disagreement
    if iv_disagreement_pp is not None and iv_disagreement_pp >= cfg["iv_disagreement_warn_pp"]:
        issues += 1
    # (5) atm distance
    if atm_distance_pct is not None and atm_distance_pct >= cfg["atm_distance_warn_pct"]:
        issues += 1
    # (6) any quality flag NOT implied by 1-5
    implied = {"iv_disagreement", "atm_distance_high", "stale_last_rejected"}
    non_implied = [f for f in quality_flags if f not in implied]
    if non_implied:
        issues += 1

    # Static-snapshot tiers (frozen, delayed_frozen) cap at LOW regardless
    if data_tier in ("frozen", "delayed_frozen"):
        return "LOW"
    if issues == 0 and data_tier == "live":
        return "HIGH"
    if issues == 1:
        return "MEDIUM"
    return "LOW"


# ---------------------------------------------------------------------------
# Result schema
# ---------------------------------------------------------------------------

@dataclass
class IVRow:
    # === schema identifiers (v2 phase 1) ===
    schema_version: str = SCHEMA_VERSION
    row_id: str = ""               # populated post-expiry-pick: "{ticker}:{expiry}:{earnings_role}"
    run_id: str = ""               # populated by main() — same value across all rows in a run
    earnings_role: str = "non_earnings"  # phase 4 may overwrite to pre_earnings | post_earnings
    is_primary: bool = True              # phase 4 may set False for added pre/post rows
    # === identity ===
    ticker: str = ""
    spot: float | None = None
    spot_source: str = ""
    expiry: str = ""
    dte: int | None = None
    atm_strike: float | None = None
    call_bid: float | None = None
    call_ask: float | None = None
    call_mid: float | None = None
    call_iv: float | None = None
    # Tier 1.B per-leg quote-quality metadata
    call_mid_source: str = "none"               # bid_ask_mid | last_fresh | last_stale_rejected | none
    call_tick_age_seconds: float | None = None
    call_tick_age_known: bool = False
    put_bid: float | None = None
    put_ask: float | None = None
    put_mid: float | None = None
    put_iv: float | None = None
    put_mid_source: str = "none"
    put_tick_age_seconds: float | None = None
    put_tick_age_known: bool = False
    expected_move_dollars: float | None = None
    expected_move_pct: float | None = None
    iv_avg: float | None = None
    em_from_iv_dollars: float | None = None
    em_from_iv_pct: float | None = None
    spread_call_bps: float | None = None
    spread_put_bps: float | None = None
    # Tier 1.F + flag aggregator
    data_tier: str = "unknown"                       # live | delayed | frozen | delayed_frozen | fallback_delayed | unknown
    quality_flags: list[str] = field(default_factory=list)
    # Tier 2 phase 3 transparency fields
    atm_distance_pct: float | None = None            # |strike-spot| / spot * 100
    iv_disagreement_pp: float | None = None          # |call_iv - put_iv| in pp
    multiplier: int | None = None                    # standard 100; flag if not
    quote_freshness: str = "unknown"                 # fresh | stale | unknown (independent of data_tier)
    iv_quality: str = "n/a"                          # HIGH | MEDIUM | LOW | n/a
    context_flags: list[str] = field(default_factory=list)  # semantic flags (populated in phase 4)
    status: str = "PENDING"
    diagnostics: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Per-ticker workflow
# ---------------------------------------------------------------------------

async def compute_one(
    ib: IB, sem: asyncio.Semaphore, ticker: str, target_dte: int | None,
    market_data_type: int = 1, run_id: str = "",
) -> IVRow:
    row = IVRow(ticker=ticker, run_id=run_id)
    # Initialize row_id immediately so EVERY row is citable by evidence catalog,
    # even early-failure rows (NO_CONID / NO_SPOT / NO_CHAIN / NO_EXPIRY).
    # Overwritten below once an expiry is picked.
    row.row_id = f"{ticker}:no_expiry:{row.earnings_role}"
    async with sem:
        # 1. Qualify underlying
        try:
            qualified = await asyncio.wait_for(
                ib.qualifyContractsAsync(Stock(ticker, "SMART", "USD")), timeout=8,
            )
        except Exception as e:
            row.status = "QUALIFY_FAILED"
            row.diagnostics.append(f"{type(e).__name__}: {e}")
            return row
        underlying = qualified[0] if qualified else None
        if underlying is None or getattr(underlying, "conId", 0) == 0:
            row.status = "NO_CONID"
            return row

        # 2. Spot price
        try:
            ib.reqMarketDataType(market_data_type)
            [stk_ticker] = await asyncio.wait_for(
                ib.reqTickersAsync(underlying), timeout=20,
            )
        except Exception as e:
            row.status = "SPOT_FAILED"
            row.diagnostics.append(f"{type(e).__name__}: {e}")
            return row
        spot = None
        for v in (stk_ticker.last, stk_ticker.marketPrice(), stk_ticker.close):
            if v is not None and not math.isnan(v) and v > 0:
                spot = float(v)
                break
        if spot is None:
            row.status = "NO_SPOT"
            return row
        row.spot = spot
        row.spot_source = (
            "live" if stk_ticker.marketDataType == 1 and stk_ticker.last and not math.isnan(stk_ticker.last)
            else f"mdt={stk_ticker.marketDataType}"
        )

        # 3. Chain
        try:
            chain_params = await asyncio.wait_for(
                ib.reqSecDefOptParamsAsync(underlying.symbol, "", underlying.secType, underlying.conId),
                timeout=10,
            )
        except Exception as e:
            row.status = "CHAIN_FAILED"
            row.diagnostics.append(f"{type(e).__name__}: {e}")
            return row
        if not chain_params:
            row.status = "NO_CHAIN"
            return row
        # Filter to the STANDARD chain — tradingClass matches ticker, prefer SMART.
        # IBKR returns one chain entry per (exchange, tradingClass); weekly variants
        # (e.g., SPYW for SPY) have their own restricted strike grids that would
        # cause "closest strike" mis-picks like ATM=639 for spot=745.
        std_chains = [p for p in chain_params if p.tradingClass == ticker]
        if not std_chains:
            std_chains = chain_params  # fallback if no exact tradingClass match
        smart = next((p for p in std_chains if p.exchange == "SMART"), None)
        params = smart or std_chains[0]
        all_expirations = set(params.expirations or [])
        all_strikes = sorted(set(params.strikes or []))

        # 4. Pick expiry
        expiry_yyyymmdd = pick_expiry(all_expirations, target_dte)
        if expiry_yyyymmdd is None:
            row.status = "NO_EXPIRY"
            row.diagnostics.append(f"chain_expirations={len(all_expirations)}")
            return row
        row.expiry = expiry_yyyymmdd
        # row_id format: {ticker}:{expiry}:{earnings_role}. earnings_role defaults to
        # "non_earnings" in phase 1; phase 4 may emit dual rows with role=pre_earnings/post_earnings
        # in which case row_id is regenerated at row-emission time.
        row.row_id = f"{ticker}:{expiry_yyyymmdd}:{row.earnings_role}"
        expiry_date = dt.datetime.strptime(expiry_yyyymmdd, "%Y%m%d").date()
        row.dte = (expiry_date - dt.date.today()).days

        # 5. ATM strike — try closest, fall back to next-nearest if not valid
        # for the chosen expiry (chain.strikes is UNION across expirations).
        if not all_strikes or spot is None:
            row.status = "NO_ATM"
            return row
        ranked_strikes = sorted(all_strikes, key=lambda s: abs(s - spot))
        call_q = put_q = None
        for candidate in ranked_strikes[:5]:  # try up to 5 nearest strikes
            call = Option(ticker, expiry_yyyymmdd, candidate, "C", "SMART",
                          currency="USD", tradingClass=params.tradingClass or ticker)
            put = Option(ticker, expiry_yyyymmdd, candidate, "P", "SMART",
                         currency="USD", tradingClass=params.tradingClass or ticker)
            try:
                qualified_opts = await asyncio.wait_for(
                    ib.qualifyContractsAsync(call, put), timeout=8,
                )
            except Exception as e:
                row.diagnostics.append(f"qualify@{candidate}: {type(e).__name__}")
                continue
            qualified_opts = [c for c in qualified_opts if c and getattr(c, "conId", 0)]
            if len(qualified_opts) >= 2:
                row.atm_strike = candidate
                # Tier 2.G — surface atm_distance_pct so bot sees how far off-ATM we picked
                row.atm_distance_pct = compute_atm_distance_pct(candidate, spot)
                if (row.atm_distance_pct is not None
                        and row.atm_distance_pct >= DEFAULT_CONFIG["atm_distance_warn_pct"]):
                    if "atm_distance_high" not in row.quality_flags:
                        row.quality_flags.append("atm_distance_high")
                call_q = next((c for c in qualified_opts if c.right == "C"), None)
                put_q = next((c for c in qualified_opts if c.right == "P"), None)
                if call_q and put_q:
                    if candidate != ranked_strikes[0]:
                        # Tier 2 transparency — flag when we fell back
                        if "strike_retry_used" not in row.quality_flags:
                            row.quality_flags.append("strike_retry_used")
                        row.diagnostics.append(
                            f"fell-back from {ranked_strikes[0]} → {candidate} "
                            f"(closest strike not valid for {expiry_yyyymmdd})",
                        )
                    # Tier 2.I — multiplier guard. Standard equity options = 100.
                    # Adjusted contracts (post-split/spinoff) may differ.
                    try:
                        mult_raw = getattr(call_q, "multiplier", "") or "100"
                        row.multiplier = int(float(mult_raw))
                    except (ValueError, TypeError):
                        row.multiplier = None
                    if row.multiplier is not None and row.multiplier != 100:
                        if "multiplier_nonstandard" not in row.quality_flags:
                            row.quality_flags.append("multiplier_nonstandard")
                    break
                call_q = put_q = None  # both rights required
        if call_q is None or put_q is None:
            row.status = "OPT_NOT_FOUND"
            row.diagnostics.append(f"tried_strikes={ranked_strikes[:5]}")
            return row

        # 7. Get tickers
        ib.reqMarketDataType(market_data_type)
        try:
            tickers = await asyncio.wait_for(
                ib.reqTickersAsync(call_q, put_q), timeout=20,
            )
        except Exception as e:
            row.status = "QUOTE_FAILED"
            row.diagnostics.append(f"{type(e).__name__}: {e}")
            return row
        call_t = next((t for t in tickers if t.contract.right == "C"), None)
        put_t = next((t for t in tickers if t.contract.right == "P"), None)

        # 7b. Tier 1.E — auto-fallback to type=3 (delayed) when type=1 returns all-null
        # during options RTH. This handles the "OPRA entitlement lapsed" case so the bot
        # gets the best available data tier without manual intervention.
        fell_back_from_live = False
        def _legs_all_null(c_t, p_t) -> bool:
            def _ok(v):
                if v is None: return False
                try: return not math.isnan(float(v)) and float(v) > 0
                except Exception: return False
            for t in (c_t, p_t):
                if t is None:
                    continue
                if _ok(t.bid) or _ok(t.ask) or _ok(t.last):
                    return False
            return True
        if (market_data_type == 1 and DEFAULT_CONFIG["live_to_delayed_fallback_enabled"]
                and _legs_all_null(call_t, put_t)):
            ib.reqMarketDataType(3)
            try:
                tickers = await asyncio.wait_for(
                    ib.reqTickersAsync(call_q, put_q), timeout=20,
                )
                call_t = next((t for t in tickers if t.contract.right == "C"), None)
                put_t = next((t for t in tickers if t.contract.right == "P"), None)
                fell_back_from_live = True
                row.diagnostics.append("type=1 returned all-null; auto-fell-back to type=3 delayed")
            except Exception as e:
                row.diagnostics.append(f"fallback-quote-fetch failed: {type(e).__name__}: {e}")

    # Outside the semaphore — pure compute
    run_time = dt.datetime.now(dt.timezone.utc)
    def _f(x):
        return None if (x is None or (isinstance(x, float) and math.isnan(x)) or x == -1) else float(x)

    # Capture per-leg ticker.time → tick_age (Tier 1.B)
    if call_t is not None:
        row.call_bid = _f(call_t.bid)
        row.call_ask = _f(call_t.ask)
        c_last = _f(call_t.last)
        ca, ca_known = get_tick_age_seconds(getattr(call_t, "time", None), run_time)
        row.call_tick_age_seconds = ca
        row.call_tick_age_known = ca_known
        row.call_mid, row.call_mid_source = compute_mid_and_source(
            row.call_bid, row.call_ask, c_last, ca,
            DEFAULT_CONFIG["tick_freshness_threshold_sec"],
        )
        # Tier 1.A — sanitize IV
        raw_call_iv = call_t.modelGreeks.impliedVol if call_t.modelGreeks else None
        row.call_iv, call_iv_sanitized = sanitize_iv(
            raw_call_iv, DEFAULT_CONFIG["iv_min_valid"], DEFAULT_CONFIG["iv_max_valid"],
        )
        if call_iv_sanitized:
            if "iv_sanitized" not in row.quality_flags:
                row.quality_flags.append("iv_sanitized")
        row.spread_call_bps = spread_bps(row.call_bid, row.call_ask, row.call_mid)
    if put_t is not None:
        row.put_bid = _f(put_t.bid)
        row.put_ask = _f(put_t.ask)
        p_last = _f(put_t.last)
        pa, pa_known = get_tick_age_seconds(getattr(put_t, "time", None), run_time)
        row.put_tick_age_seconds = pa
        row.put_tick_age_known = pa_known
        row.put_mid, row.put_mid_source = compute_mid_and_source(
            row.put_bid, row.put_ask, p_last, pa,
            DEFAULT_CONFIG["tick_freshness_threshold_sec"],
        )
        raw_put_iv = put_t.modelGreeks.impliedVol if put_t.modelGreeks else None
        row.put_iv, put_iv_sanitized = sanitize_iv(
            raw_put_iv, DEFAULT_CONFIG["iv_min_valid"], DEFAULT_CONFIG["iv_max_valid"],
        )
        if put_iv_sanitized:
            if "iv_sanitized" not in row.quality_flags:
                row.quality_flags.append("iv_sanitized")
        row.spread_put_bps = spread_bps(row.put_bid, row.put_ask, row.put_mid)

    # Tier 1.B — emit stale_last_rejected flag if any leg fell back to a stale last (mid=None despite last>0)
    if (row.call_mid_source == "last_stale_rejected" or row.put_mid_source == "last_stale_rejected"):
        if "stale_last_rejected" not in row.quality_flags:
            row.quality_flags.append("stale_last_rejected")

    # Tier 1.F — derive data_tier per row using observed marketDataType + populated check.
    # Use call_t's marketDataType (both legs were requested in same call, same tier).
    observed_mdt = getattr(call_t, "marketDataType", None) if call_t is not None else (
        getattr(put_t, "marketDataType", None) if put_t is not None else None
    )
    # representative populated check — pass a positive proxy for last if EITHER leg's
    # mid was derived from a fresh last (mid_source == "last_fresh"). Without this proxy,
    # rows with no bid/ask but a fresh last would be tagged data_tier=unknown despite
    # having real live data — bug caught in phase 2 review.
    any_bid = row.call_bid or row.put_bid
    any_ask = row.call_ask or row.put_ask
    any_last_fresh = 1.0 if (row.call_mid_source == "last_fresh"
                             or row.put_mid_source == "last_fresh") else None
    row.data_tier = derive_data_tier(observed_mdt, any_bid, any_ask, any_last_fresh, fell_back_from_live)

    # Compute EM
    if row.call_mid is not None and row.put_mid is not None and row.spot is not None:
        row.expected_move_dollars = row.call_mid + row.put_mid
        row.expected_move_pct = row.expected_move_dollars / row.spot
    ivs = [x for x in (row.call_iv, row.put_iv) if x is not None]
    if ivs:
        row.iv_avg = sum(ivs) / len(ivs)
        row.em_from_iv_dollars = em_from_iv(row.spot, row.iv_avg, row.dte or 0)
        if row.em_from_iv_dollars is not None and row.spot:
            row.em_from_iv_pct = row.em_from_iv_dollars / row.spot

    # Tier 1.C — status logic. OK only if EM computable AND we have actual data.
    # mdt=1 + everything null = NOT OK (default-value, not real live).
    if row.expected_move_dollars is not None:
        row.status = "OK"
    elif (row.call_bid is None and row.put_bid is None
          and row.call_iv is None and row.put_iv is None
          and row.call_mid is None and row.put_mid is None):
        row.status = "NO_QUOTES"
        row.diagnostics.append("no usable quotes flowed (all legs null after fallback)")
    else:
        row.status = "PARTIAL"

    # Tier 2.H — iv_disagreement_pp + threshold flag
    row.iv_disagreement_pp = compute_iv_disagreement_pp(row.call_iv, row.put_iv)
    if (row.iv_disagreement_pp is not None
            and row.iv_disagreement_pp >= DEFAULT_CONFIG["iv_disagreement_warn_pp"]):
        if "iv_disagreement" not in row.quality_flags:
            row.quality_flags.append("iv_disagreement")

    # Tier 2 — wide_spread threshold (any leg spread > warn_bps)
    for leg_spread in (row.spread_call_bps, row.spread_put_bps):
        if leg_spread is not None and leg_spread > DEFAULT_CONFIG["spread_warn_bps"]:
            if "wide_spread" not in row.quality_flags:
                row.quality_flags.append("wide_spread")
            break

    # Tier 2 — quote_freshness derivation (independent of data_tier)
    row.quote_freshness = derive_quote_freshness(
        row.call_tick_age_seconds, row.call_tick_age_known,
        row.put_tick_age_seconds, row.put_tick_age_known,
        DEFAULT_CONFIG["tick_freshness_threshold_sec"],
    )

    # Tier 2.J — iv_quality summary label per SCHEMA_v2 r6
    row.iv_quality = derive_iv_quality(
        status=row.status,
        data_tier=row.data_tier,
        quote_freshness=row.quote_freshness,
        call_mid_source=row.call_mid_source,
        put_mid_source=row.put_mid_source,
        iv_disagreement_pp=row.iv_disagreement_pp,
        atm_distance_pct=row.atm_distance_pct,
        quality_flags=row.quality_flags,
    )
    return row


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def stdout_table(rows: list[IVRow]) -> None:
    hdr = f"{'TICKER':<7} {'SPOT':>9} {'EXP':>10} {'DTE':>4} {'ATM':>8}  {'EM$':>8} {'EM%':>7} {'IV':>7}  STATUS"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        em_d = f"{r.expected_move_dollars:.2f}" if r.expected_move_dollars else "-"
        em_p = f"{r.expected_move_pct*100:.2f}%" if r.expected_move_pct else "-"
        iv = f"{r.iv_avg*100:.1f}%" if r.iv_avg else "-"
        spot = f"{r.spot:.2f}" if r.spot else "-"
        atm = f"{r.atm_strike:.1f}" if r.atm_strike else "-"
        exp = r.expiry or "-"
        dte = str(r.dte) if r.dte is not None else "-"
        print(f"{r.ticker:<7} {spot:>9} {exp:>10} {dte:>4} {atm:>8}  {em_d:>8} {em_p:>7} {iv:>7}  {r.status}")


def summary(rows: list[IVRow]) -> dict:
    s = {"total": len(rows)}
    for r in rows:
        s[r.status.lower()] = s.get(r.status.lower(), 0) + 1
    return s


def load_tickers(args) -> list[str]:
    if args.tickers:
        return [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    if args.tickers_file:
        return [t.strip().upper() for t in Path(args.tickers_file).read_text().split() if t.strip()]
    if args.universe_redis:
        import subprocess
        out = subprocess.check_output([
            "kubectl", "exec", "-n", "infrastructure",
            "redis-79d9c8d68f-z256d", "--", "redis-cli", "GET",
            "admin:tradable_universe:symbols",
        ], text=True).strip()
        return [t for t in out.split(",") if t]
    raise SystemExit("provide --tickers, --tickers-file, or --universe-redis")


async def amain():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", help="comma-separated tickers")
    ap.add_argument("--tickers-file", help="newline or whitespace-separated tickers file")
    ap.add_argument("--universe-redis", action="store_true",
                    help="load from Redis admin:tradable_universe:symbols")
    ap.add_argument("--target-dte", type=int, default=None,
                    help="target days-to-expiry. Default: next monthly (3rd Friday)")
    ap.add_argument("--market-data-type", type=int, default=1, choices=[1, 2, 3, 4],
                    help="1=Live(needs OPRA for options) 2=Frozen 3=Delayed-15min 4=Delayed-Frozen. "
                         "Pre-OPRA use 3 to validate pipeline with free delayed quotes; "
                         "post-OPRA use 1 (default) for real-time.")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=14003)
    ap.add_argument("--client-id", type=int, default=98)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--output", default=None,
                    help="JSON output path. Default: scripts/iv/output/iv_YYYY-MM-DD.json")
    args = ap.parse_args()

    tickers = load_tickers(args)

    # Schema v2 phase 1: runtime-derived identifiers (never hardcoded)
    run_as_of = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    run_id = f"{SCHEMA_VERSION}:{run_as_of}:{args.client_id}"
    print(f"Computing IV for {len(tickers)} tickers  (run_id={run_id})", file=sys.stderr)

    ib = IB()
    await ib.connectAsync(host=args.host, port=args.port, clientId=args.client_id, timeout=20)
    sem = asyncio.Semaphore(args.concurrency)
    t0 = time.time()
    tasks = [compute_one(ib, sem, t, args.target_dte, args.market_data_type, run_id) for t in tickers]
    rows: list[IVRow] = []
    for i, fut in enumerate(asyncio.as_completed(tasks), 1):
        r = await fut
        rows.append(r)
        if i % 50 == 0:
            elapsed = time.time() - t0
            ok = sum(1 for x in rows if x.status == "OK")
            print(f"  [{i:4d}/{len(tickers)}]  ok={ok}  elapsed={elapsed:.0f}s",
                  file=sys.stderr)
    ib.disconnect()
    rows.sort(key=lambda r: r.ticker)

    out_path = Path(args.output) if args.output else (
        Path(__file__).parent / "output" / f"iv_{dt.date.today().isoformat()}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        # === schema identifiers (v2 phase 1) ===
        "schema_version":             SCHEMA_VERSION,
        "run_id":                     run_id,
        "run_as_of":                  run_as_of,
        # === run params ===
        "method":                     "atm_straddle",
        "target_dte":                 args.target_dte,
        "market_data_type_requested": args.market_data_type,
        "universe_size":              len(tickers),
        # === constants + thresholds (surfaced for audit per user guardrail; NOT runtime data) ===
        "market_conventions":         MARKET_CONVENTIONS,
        "config":                     DEFAULT_CONFIG,
        # === provenance ===
        "data_sources": {
            # options_chain catalog (reqSecDefOptParams) always returns live catalog — no entitlement gate.
            "options_chain": {"vendor": "IBKR", "via": "reqSecDefOptParams", "live_at_run": True},
            # quotes path actual tier depends on what the user requested.
            # Phase 2 will refine using observed per-row data_tier; for phase 1 we reflect intent.
            "quotes": {
                "vendor":      "IBKR",
                "via":         "reqTickersAsync",
                "live_at_run": args.market_data_type == 1,
                "market_data_type_requested": args.market_data_type,  # 1|2|3|4 — see CLI help
            },
            # earnings_calendar block appended in phase 4
        },
        # === aggregates ===
        "summary":  summary(rows),
        # === per-ticker rows ===
        "results":  [asdict(r) for r in rows],
    }
    out_path.write_text(json.dumps(payload, indent=2, default=str))
    print(f"\nWrote {out_path}", file=sys.stderr)
    print()
    stdout_table(rows)
    print()
    print("Summary:", json.dumps(payload["summary"]))


if __name__ == "__main__":
    asyncio.run(amain())
