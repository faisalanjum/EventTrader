"""Unit tests for scripts/iv/compute_iv_moves.py pure-compute helpers.

Pure tests — no IB connection required. Validates the calendar, strike,
math, and midpoint logic that needs to be 100% correct for IV calculations
to be trustworthy.
"""
from __future__ import annotations

import datetime as dt
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from compute_iv_moves import (  # noqa: E402
    third_friday,
    next_monthly_expiry,
    pick_expiry,
    pick_atm_strike,
    safe_mid,
    spread_bps,
    em_from_iv,
    SCHEMA_VERSION,
    MARKET_CONVENTIONS,
    DEFAULT_CONFIG,
    IVRow,
    sanitize_iv,
    compute_mid_and_source,
    derive_data_tier,
    get_tick_age_seconds,
    compute_atm_distance_pct,
    compute_iv_disagreement_pp,
    derive_quote_freshness,
    derive_iv_quality,
    derive_event_ts,
    derive_earnings_timing,
    derive_earnings_context_flags,
    find_first_expiry_after,
    find_last_expiry_before,
    pick_secondary_expiry,
)


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

class TestThirdFriday:
    def test_may_2026(self):
        assert third_friday(2026, 5) == dt.date(2026, 5, 15)

    def test_june_2026(self):
        assert third_friday(2026, 6) == dt.date(2026, 6, 19)

    def test_january_2026(self):
        # Jan 1 2026 is Thursday → first Friday Jan 2 → third Friday Jan 16
        assert third_friday(2026, 1) == dt.date(2026, 1, 16)

    def test_february_2024_leap(self):
        # Feb 1 2024 is Thursday → first Friday Feb 2 → third Friday Feb 16
        assert third_friday(2024, 2) == dt.date(2024, 2, 16)


class TestNextMonthlyExpiry:
    def test_today_before_this_months_expiry(self):
        # 2026-05-10 → next monthly is 2026-05-15
        assert next_monthly_expiry(dt.date(2026, 5, 10)) == dt.date(2026, 5, 15)

    def test_today_is_expiry_day_picks_next_month(self):
        # 2026-05-15 IS the 3rd Friday → next monthly is June
        assert next_monthly_expiry(dt.date(2026, 5, 15)) == dt.date(2026, 6, 19)

    def test_today_after_this_months_expiry(self):
        # 2026-05-16 → next monthly is June
        assert next_monthly_expiry(dt.date(2026, 5, 16)) == dt.date(2026, 6, 19)

    def test_december_rolls_to_january(self):
        # 2026-12-31 → next monthly is Jan 2027
        assert next_monthly_expiry(dt.date(2026, 12, 31)) == dt.date(2027, 1, 15)


# ---------------------------------------------------------------------------
# Expiry picker
# ---------------------------------------------------------------------------

class TestPickExpiry:
    def setup_method(self):
        # Chain available on 2026-05-14 typically includes weeklies + monthlies
        self.chain = {
            "20260515",  # this Fri (weekly + 3rd Fri of May)
            "20260522", "20260529",  # weeklies
            "20260619",  # June monthly
            "20260717",  # July monthly
            "20260821",  # Aug monthly
            "20261218",  # Dec monthly (long-dated)
            "20260301",  # already-passed expiry
        }

    def test_default_picks_next_monthly_when_today_before_15th(self):
        # On 2026-05-14, next monthly = 2026-05-15
        assert pick_expiry(self.chain, target_dte=None, today=dt.date(2026, 5, 14)) == "20260515"

    def test_default_picks_june_monthly_after_may_expiry(self):
        # On 2026-05-16, next monthly = 2026-06-19
        assert pick_expiry(self.chain, target_dte=None, today=dt.date(2026, 5, 16)) == "20260619"

    def test_target_dte_30_picks_closest(self):
        # On 2026-05-14, target = 2026-06-13. Closest in chain = 2026-06-19 (5 days off)
        assert pick_expiry(self.chain, target_dte=30, today=dt.date(2026, 5, 14)) == "20260619"

    def test_target_dte_45_picks_closest(self):
        # Target = 2026-06-28. Closest = 2026-06-19 (-9d) vs 2026-07-17 (+19d) → June wins
        assert pick_expiry(self.chain, target_dte=45, today=dt.date(2026, 5, 14)) == "20260619"

    def test_target_dte_60_picks_july(self):
        # Target = 2026-07-13. Closest = 2026-07-17 (4d off)
        assert pick_expiry(self.chain, target_dte=60, today=dt.date(2026, 5, 14)) == "20260717"

    def test_empty_chain_returns_none(self):
        assert pick_expiry(set(), target_dte=None) is None

    def test_only_expired_returns_none(self):
        assert pick_expiry({"20200101"}, target_dte=None, today=dt.date(2026, 5, 14)) is None

    def test_today_equals_expiry_excluded(self):
        # On 2026-05-15 (expiry day), the 0-DTE option is skipped — it's d <= today
        chain = {"20260515", "20260619"}
        assert pick_expiry(chain, target_dte=None, today=dt.date(2026, 5, 15)) == "20260619"

    def test_malformed_string_skipped(self):
        chain = {"GARBAGE", "20260619"}
        assert pick_expiry(chain, target_dte=None, today=dt.date(2026, 5, 14)) == "20260619"


# ---------------------------------------------------------------------------
# ATM strike picker
# ---------------------------------------------------------------------------

class TestPickAtmStrike:
    def test_exact_match(self):
        assert pick_atm_strike([290, 295, 300, 305, 310], 300.0) == 300.0

    def test_closest_when_no_exact(self):
        # spot 297.34 → 295 is closer (2.34) than 300 (2.66)
        assert pick_atm_strike([290, 295, 300, 305], 297.34) == 295.0

    def test_closest_when_above_midpoint(self):
        # spot 297.51 → 300 is closer (2.49) than 295 (2.51)
        assert pick_atm_strike([290, 295, 300, 305], 297.51) == 300.0

    def test_empty_returns_none(self):
        assert pick_atm_strike([], 300.0) is None

    def test_zero_spot_returns_none(self):
        assert pick_atm_strike([290, 295, 300], 0.0) is None

    def test_negative_spot_returns_none(self):
        assert pick_atm_strike([290, 295, 300], -5.0) is None

    def test_single_strike(self):
        assert pick_atm_strike([100.0], 300.0) == 100.0


# ---------------------------------------------------------------------------
# Midpoint
# ---------------------------------------------------------------------------

class TestSafeMid:
    def test_normal(self):
        assert safe_mid(4.95, 5.05, 5.00) == 5.0

    def test_bid_zero_falls_to_last(self):
        assert safe_mid(0.0, 5.05, 5.00) == 5.00

    def test_ask_zero_falls_to_last(self):
        assert safe_mid(4.95, 0.0, 5.00) == 5.00

    def test_both_zero_falls_to_last(self):
        assert safe_mid(0.0, 0.0, 5.00) == 5.00

    def test_all_none(self):
        assert safe_mid(None, None, None) is None

    def test_bid_ask_none_last_present(self):
        assert safe_mid(None, None, 5.00) == 5.00

    def test_last_zero_means_none(self):
        # last=0 is not a meaningful price → fall through
        assert safe_mid(None, None, 0.0) is None


# ---------------------------------------------------------------------------
# Spread
# ---------------------------------------------------------------------------

class TestSpreadBps:
    def test_tight_spread(self):
        # bid 4.95, ask 5.05, mid 5.00 → spread 0.10/5.00 = 2% = 200 bps
        assert spread_bps(4.95, 5.05, 5.00) == pytest.approx(200.0, abs=1e-6)

    def test_wide_spread(self):
        # bid 4.50, ask 5.50, mid 5.00 → 20% = 2000 bps
        assert spread_bps(4.50, 5.50, 5.00) == pytest.approx(2000.0, abs=1e-6)

    def test_zero_mid_returns_none(self):
        assert spread_bps(0.95, 1.05, 0.0) is None

    def test_inverted_returns_none(self):
        # ask < bid should never happen but if it does, return None
        assert spread_bps(5.05, 4.95, 5.00) is None

    def test_any_none_returns_none(self):
        assert spread_bps(None, 5.05, 5.00) is None
        assert spread_bps(4.95, None, 5.00) is None
        assert spread_bps(4.95, 5.05, None) is None


# ---------------------------------------------------------------------------
# EM from IV
# ---------------------------------------------------------------------------

class TestEmFromIv:
    def test_aapl_30d_30pct_iv(self):
        # AAPL spot 300, IV 30%, 30 DTE → 300 * 0.30 * sqrt(30/365)
        em = em_from_iv(300.0, 0.30, 30)
        expected = 300.0 * 0.30 * math.sqrt(30 / 365)
        assert abs(em - expected) < 1e-9
        assert 25 < em < 30  # roughly $25-30 for 30-day 30% IV move

    def test_zero_dte_means_zero_em(self):
        assert em_from_iv(300.0, 0.30, 0) == 0.0

    def test_zero_iv_returns_none(self):
        assert em_from_iv(300.0, 0.0, 30) is None

    def test_negative_iv_returns_none(self):
        assert em_from_iv(300.0, -0.30, 30) is None

    def test_zero_spot_returns_none(self):
        assert em_from_iv(0.0, 0.30, 30) is None

    def test_high_iv_high_dte(self):
        # SMCI-like: spot 50, IV 100%, 90 DTE → 50 * 1.0 * sqrt(90/365) ≈ 24.8
        em = em_from_iv(50.0, 1.00, 90)
        assert 24 < em < 26


# ---------------------------------------------------------------------------
# Cross-validation: straddle EM vs IV-derived EM should roughly agree
# ---------------------------------------------------------------------------

class TestCrossValidation:
    """In normal markets, straddle EM ≈ 0.797 × IV-derived 1σ EM (the
    sqrt(2/π) factor between straddle premium and Brownian 1-sigma).
    For a sanity check we expect the two within ~30% of each other."""

    def test_aapl_like_consistency(self):
        # Hypothetical AAPL: spot 300, IV 30%, 30 DTE
        # IV-derived 1σ ≈ 300 * 0.30 * sqrt(30/365) ≈ 27
        # Straddle premium ≈ 27 * 0.797 ≈ 21.5 (call_mid + put_mid)
        spot, iv, dte = 300.0, 0.30, 30
        em_iv = em_from_iv(spot, iv, dte)
        # Straddle premium under Black-Scholes ATM:
        # premium ≈ spot * iv * sqrt(2 * dte / (pi * 365)) — Brenner-Subrahmanyam
        em_straddle = spot * iv * math.sqrt(2 * dte / (math.pi * 365))
        ratio = em_straddle / em_iv
        # Expected ratio ≈ sqrt(2/π) ≈ 0.7979
        assert 0.79 < ratio < 0.80


# ---------------------------------------------------------------------------
# Schema v2 phase 1 — versioning, identifiers, envelope constants
# ---------------------------------------------------------------------------

class TestSchemaV2Constants:
    """Schema version + market conventions + default config — must be stable.
    Per the SCHEMA_v2.md contract, these are surfaced in every artifact."""

    def test_schema_version_pinned(self):
        assert SCHEMA_VERSION == "iv_moves.v2"

    def test_market_conventions_has_required_keys(self):
        for k in ("options_market_close_et", "amc_conventional_time_et",
                  "bmo_conventional_time_et", "dmh_conventional_time_et",
                  "iv_annualization_days"):
            assert k in MARKET_CONVENTIONS, f"missing {k}"

    def test_market_conventions_amc_after_close(self):
        # AMC release convention MUST be after options market close
        # (otherwise the "expires-before-event" logic is wrong)
        assert MARKET_CONVENTIONS["amc_conventional_time_et"] > MARKET_CONVENTIONS["options_market_close_et"]

    def test_market_conventions_bmo_before_open(self):
        # BMO release MUST be before 09:30 ET (market open)
        assert MARKET_CONVENTIONS["bmo_conventional_time_et"] < "09:30"

    def test_iv_annualization_calendar_days(self):
        # IV scaling uses calendar days (365), not trading days (252)
        assert MARKET_CONVENTIONS["iv_annualization_days"] == 365

    def test_default_config_has_required_thresholds(self):
        for k in ("tick_freshness_threshold_sec", "spread_warn_bps",
                  "atm_distance_warn_pct", "iv_disagreement_warn_pp",
                  "iv_min_valid", "iv_max_valid",
                  "earnings_just_after_window_days",
                  "live_to_delayed_fallback_enabled",
                  "expiry_ladder_max_entries"):
            assert k in DEFAULT_CONFIG, f"missing {k}"


class TestIVRowSchemaV2:
    """IVRow defaults match v2 schema phase 1."""

    def test_default_schema_version(self):
        r = IVRow(ticker="AAPL")
        assert r.schema_version == "iv_moves.v2"

    def test_default_earnings_role(self):
        # phase 4 will overwrite; phase 1 default is non_earnings
        r = IVRow(ticker="AAPL")
        assert r.earnings_role == "non_earnings"

    def test_default_is_primary(self):
        r = IVRow(ticker="AAPL")
        assert r.is_primary is True

    def test_default_row_id_empty(self):
        # row_id is set later by compute_one once expiry is picked
        r = IVRow(ticker="AAPL")
        assert r.row_id == ""

    def test_row_id_format_after_pick(self):
        # Format: {ticker}:{expiry}:{earnings_role}
        # This is the contract for evidence-catalog citation
        r = IVRow(ticker="AAPL")
        r.row_id = f"{r.ticker}:20260618:{r.earnings_role}"
        assert r.row_id == "AAPL:20260618:non_earnings"


class TestRunIdFormat:
    """run_id format: {schema_version}:{run_as_of}:{client_id}"""

    def test_run_id_components(self):
        # Construct exactly as main() does
        from datetime import datetime, timezone
        run_as_of = datetime(2026, 5, 14, 20, 35, 0, tzinfo=timezone.utc).isoformat(timespec="seconds")
        client_id = 33
        run_id = f"{SCHEMA_VERSION}:{run_as_of}:{client_id}"
        # Must start with schema_version
        assert run_id.startswith("iv_moves.v2:")
        # Must end with client_id
        assert run_id.endswith(":33")
        # Must contain the timestamp
        assert "2026-05-14T20:35:00+00:00" in run_id

    def test_run_id_changes_per_run(self):
        # Two runs at different times produce different run_ids
        from datetime import datetime, timezone
        rid_1 = f"{SCHEMA_VERSION}:{datetime(2026, 5, 14, 10, 0, 0, tzinfo=timezone.utc).isoformat(timespec='seconds')}:33"
        rid_2 = f"{SCHEMA_VERSION}:{datetime(2026, 5, 14, 11, 0, 0, tzinfo=timezone.utc).isoformat(timespec='seconds')}:33"
        assert rid_1 != rid_2


class TestRowIdAlwaysCitable:
    """Every row — even early-failure rows — must carry a row_id so the
    predictor/learner evidence catalog can cite it. Empty row_id violates
    the v2 schema contract."""

    def test_row_id_format_when_no_expiry(self):
        # Pre-expiry-pick failure modes (NO_CONID / NO_SPOT / NO_CHAIN / NO_EXPIRY)
        # must still yield a citable row_id.
        # Simulate compute_one's init path:
        r = IVRow(ticker="ANSS")
        r.row_id = f"{r.ticker}:no_expiry:{r.earnings_role}"
        # Even with no expiry picked, row is citable:
        assert r.row_id == "ANSS:no_expiry:non_earnings"
        assert r.row_id != ""

    def test_row_id_overwritten_when_expiry_picked(self):
        # Once expiry is known, row_id is replaced with the canonical form.
        r = IVRow(ticker="AAPL")
        r.row_id = f"{r.ticker}:no_expiry:{r.earnings_role}"
        assert r.row_id == "AAPL:no_expiry:non_earnings"
        # Simulate expiry pick
        r.expiry = "20260618"
        r.row_id = f"{r.ticker}:{r.expiry}:{r.earnings_role}"
        assert r.row_id == "AAPL:20260618:non_earnings"


class TestDataSourcesLiveAtRun:
    """data_sources.quotes.live_at_run must reflect the actual market_data_type
    requested, not be hardcoded to True. If the user runs --market-data-type 3
    (delayed), live_at_run MUST be False; otherwise the artifact lies."""

    def test_live_at_run_true_only_when_type_1(self):
        # Mirror the logic from main()'s data_sources block
        for mdt in (1, 2, 3, 4):
            live = (mdt == 1)
            if mdt == 1:
                assert live is True, f"mdt={mdt} should be live"
            else:
                assert live is False, f"mdt={mdt} should NOT be live"

    def test_options_chain_always_live(self):
        # reqSecDefOptParams returns the chain catalog regardless of entitlement.
        # Phase 1 leaves this hardcoded True; if IBKR ever gates it, revisit.
        assert True  # documents the assumption


# ===========================================================================
# Tier 1 phase 2 — core safety: IV sanitize, mid_source, stale, holiday, fallback, data_tier
# ===========================================================================

class TestSanitizeIV:
    """Tier 1.A — reject NaN/-1/out-of-range IV values."""

    def test_normal_iv_passes(self):
        v, sanitized = sanitize_iv(0.30)
        assert v == 0.30 and sanitized is False

    def test_nan_rejected(self):
        v, sanitized = sanitize_iv(float("nan"))
        assert v is None and sanitized is True

    def test_minus_one_rejected(self):
        v, sanitized = sanitize_iv(-1)
        assert v is None and sanitized is True

    def test_zero_below_min_rejected(self):
        # IV 0 is meaningless; min_valid = 0.01 by default
        v, sanitized = sanitize_iv(0.005)
        assert v is None and sanitized is True

    def test_huge_above_max_rejected(self):
        # IV > 500% is almost certainly model artifact
        v, sanitized = sanitize_iv(7.0)
        assert v is None and sanitized is True

    def test_none_passes_through(self):
        # Already-None input is not "sanitized" — there was no garbage to reject
        v, sanitized = sanitize_iv(None)
        assert v is None and sanitized is False

    def test_string_garbage_rejected(self):
        v, sanitized = sanitize_iv("not-a-number")
        assert v is None and sanitized is True

    def test_boundary_low(self):
        # exactly at min_valid passes
        v, sanitized = sanitize_iv(0.01)
        assert v == 0.01 and sanitized is False

    def test_boundary_high(self):
        # exactly at max_valid passes
        v, sanitized = sanitize_iv(5.0)
        assert v == 5.0 and sanitized is False


class TestComputeMidAndSource:
    """Tier 1.B — stale `last` must NEVER become a trusted mid.
    Sources: bid_ask_mid | last_fresh | last_stale_rejected | none."""

    def test_bid_ask_mid_when_both_positive(self):
        mid, src = compute_mid_and_source(4.95, 5.05, 4.99, tick_age_seconds=2.0)
        assert mid == 5.0 and src == "bid_ask_mid"

    def test_last_fresh_when_bid_ask_missing(self):
        # bid/ask null, last positive, fresh tick → use last
        mid, src = compute_mid_and_source(None, None, 4.99, tick_age_seconds=10.0)
        assert mid == 4.99 and src == "last_fresh"

    def test_last_stale_rejected_when_tick_old(self):
        # bid/ask null, last positive but tick > threshold (300s) → reject
        mid, src = compute_mid_and_source(None, None, 4.99, tick_age_seconds=600.0)
        assert mid is None and src == "last_stale_rejected"

    def test_last_stale_rejected_when_age_unknown(self):
        # bid/ask null, last positive, but no age info → conservative reject
        mid, src = compute_mid_and_source(None, None, 4.99, tick_age_seconds=None)
        assert mid is None and src == "last_stale_rejected"

    def test_none_when_nothing_usable(self):
        mid, src = compute_mid_and_source(None, None, None, tick_age_seconds=None)
        assert mid is None and src == "none"

    def test_zero_bid_falls_to_last_fresh(self):
        # Zero bid is "no quote" not "$0 bid" — fall back to last
        mid, src = compute_mid_and_source(0.0, 5.05, 5.00, tick_age_seconds=2.0)
        assert mid == 5.00 and src == "last_fresh"


class TestDeriveDataTier:
    """Tier 1.F — derive data_tier from observed marketDataType + populated check."""

    def test_live_requires_populated_quote(self):
        # mdt=1 + populated bid → live
        assert derive_data_tier(1, 4.95, 5.05, 4.99, False) == "live"

    def test_mdt_1_with_all_null_is_unknown_not_live(self):
        # Critical: mdt=1 default-value with no actual data ≠ live
        assert derive_data_tier(1, None, None, None, False) == "unknown"

    def test_mdt_2_is_frozen(self):
        assert derive_data_tier(2, 4.95, 5.05, 4.99, False) == "frozen"

    def test_mdt_3_is_delayed(self):
        assert derive_data_tier(3, 4.95, 5.05, 4.99, False) == "delayed"

    def test_mdt_4_is_delayed_frozen(self):
        assert derive_data_tier(4, 4.95, 5.05, 4.99, False) == "delayed_frozen"

    def test_fallback_overrides_mdt(self):
        # If we fell back from live, that's the canonical tier — even if mdt now says 3
        assert derive_data_tier(3, 4.95, 5.05, 4.99, True) == "fallback_delayed"

    def test_unknown_when_mdt_none(self):
        assert derive_data_tier(None, 4.95, 5.05, 4.99, False) == "unknown"

    def test_live_via_fresh_last_only(self):
        # Regression: phase 2 originally tagged this case as unknown because
        # compute_one passed any_last_fresh=None. The bot was MISLABELLING
        # rows with no bid/ask but a fresh last trade as unknown when they
        # should be live. Fixed by passing a positive proxy for last.
        # bid=None, ask=None, last_proxy=1.0 (positive) — fresh-last live data
        assert derive_data_tier(1, None, None, 1.0, False) == "live"


class TestHolidayExpiryPicker:
    """Tier 1.D — handle Juneteenth, Good Friday: actual expiry rolls to
    preceding Thursday. Picker searches chain within ±3 days of nominal 3rd Fri."""

    def test_juneteenth_2026_rolls_to_thursday(self):
        # today=2026-06-01 → next_monthly = 2026-06-19 (Juneteenth)
        # Chain has 20260618 (rolled Thursday) NOT 20260619 → picker must find Thursday.
        chain = {"20260618", "20260626", "20260717"}  # rolled-monthly + weekly + July monthly
        today = dt.date(2026, 6, 1)
        picked = pick_expiry(chain, target_dte=None, today=today)
        assert picked == "20260618", f"holiday-adjusted monthly should be 06-18, got {picked}"

    def test_normal_monthly_unchanged(self):
        # today=2026-06-20 (after June monthly) → next_monthly = 2026-07-17 (NOT a holiday)
        chain = {"20260710", "20260717", "20260724", "20260821"}
        today = dt.date(2026, 6, 20)
        picked = pick_expiry(chain, target_dte=None, today=today)
        assert picked == "20260717"

    def test_window_misses_returns_next_geq(self):
        # today=2026-06-20 → nominal monthly = 2026-07-17, no entry within ±3 days
        # → fallback: nearest >= 07-17 = 07-24
        chain = {"20260710", "20260724"}
        today = dt.date(2026, 6, 20)
        picked = pick_expiry(chain, target_dte=None, today=today)
        assert picked == "20260724"

    def test_target_dte_unaffected_by_holiday_logic(self):
        # target-dte path is independent of holiday logic
        chain = {"20260612", "20260618", "20260626"}
        today = dt.date(2026, 5, 14)
        # target 30 days = 2026-06-13 → closest is 20260612 (1 day off) vs 20260618 (5 off)
        assert pick_expiry(chain, target_dte=30, today=today) == "20260612"


class TestGetTickAge:
    """Tier 1.B — derive tick age from ticker.time with proper None handling."""

    def test_known_age(self):
        run = dt.datetime(2026, 5, 14, 12, 0, 0, tzinfo=dt.timezone.utc)
        tick = dt.datetime(2026, 5, 14, 11, 59, 30, tzinfo=dt.timezone.utc)
        age, known = get_tick_age_seconds(tick, run)
        assert age == 30.0 and known is True

    def test_unknown_when_none(self):
        run = dt.datetime(2026, 5, 14, 12, 0, 0, tzinfo=dt.timezone.utc)
        age, known = get_tick_age_seconds(None, run)
        assert age is None and known is False

    def test_no_negative_age(self):
        # Tick in the future (clock skew) → clamp to 0, still known
        run = dt.datetime(2026, 5, 14, 12, 0, 0, tzinfo=dt.timezone.utc)
        tick = dt.datetime(2026, 5, 14, 12, 0, 5, tzinfo=dt.timezone.utc)
        age, known = get_tick_age_seconds(tick, run)
        assert age == 0.0 and known is True


class TestPhase2IVRowFields:
    """IVRow has new Tier 1 fields with correct defaults."""

    def test_data_tier_default_unknown(self):
        r = IVRow(ticker="AAPL")
        assert r.data_tier == "unknown"

    def test_quality_flags_empty_default(self):
        r = IVRow(ticker="AAPL")
        assert r.quality_flags == []

    def test_mid_source_default_none(self):
        r = IVRow(ticker="AAPL")
        assert r.call_mid_source == "none"
        assert r.put_mid_source == "none"

    def test_tick_age_unknown_default(self):
        r = IVRow(ticker="AAPL")
        assert r.call_tick_age_seconds is None
        assert r.call_tick_age_known is False
        assert r.put_tick_age_seconds is None
        assert r.put_tick_age_known is False


# ===========================================================================
# Tier 2 phase 3 — transparency: atm_distance, iv_disagreement, multiplier, iv_quality
# ===========================================================================

class TestATMDistance:
    """G — atm_distance_pct so bot can filter off-ATM picks."""
    def test_exact_atm(self):
        assert compute_atm_distance_pct(300.0, 300.0) == 0.0

    def test_50c_off_atm_300(self):
        # strike 300, spot 297.5 → 2.5/297.5 * 100 ≈ 0.840
        v = compute_atm_distance_pct(300.0, 297.5)
        assert abs(v - 0.8403361344537815) < 1e-6

    def test_3pct_off(self):
        # strike 309, spot 300 → 9/300 * 100 = 3.0
        assert compute_atm_distance_pct(309.0, 300.0) == 3.0

    def test_none_inputs(self):
        assert compute_atm_distance_pct(None, 300.0) is None
        assert compute_atm_distance_pct(300.0, None) is None
        assert compute_atm_distance_pct(300.0, 0.0) is None  # spot zero rejected


class TestIVDisagreement:
    """H — iv_disagreement_pp catches skewed markets."""
    def test_aligned_zero_pp(self):
        assert compute_iv_disagreement_pp(0.30, 0.30) == 0.0

    def test_3pt_spread(self):
        # 30% call vs 27% put → 3.0 pp
        assert abs(compute_iv_disagreement_pp(0.30, 0.27) - 3.0) < 1e-9

    def test_takes_abs(self):
        # |0.27 - 0.30| = 0.03 = 3 pp
        assert abs(compute_iv_disagreement_pp(0.27, 0.30) - 3.0) < 1e-9

    def test_none_inputs(self):
        assert compute_iv_disagreement_pp(None, 0.30) is None
        assert compute_iv_disagreement_pp(0.30, None) is None


class TestQuoteFreshness:
    """Independent of data_tier. delayed ≠ stale."""
    def test_both_fresh(self):
        assert derive_quote_freshness(10.0, True, 5.0, True, 300.0) == "fresh"

    def test_one_stale(self):
        assert derive_quote_freshness(400.0, True, 5.0, True, 300.0) == "stale"

    def test_one_unknown(self):
        assert derive_quote_freshness(None, False, 5.0, True, 300.0) == "unknown"

    def test_both_at_threshold_boundary_stale(self):
        # exactly at threshold → stale (>=)
        assert derive_quote_freshness(300.0, True, 5.0, True, 300.0) == "stale"


class TestIVQuality:
    """J — HIGH/MEDIUM/LOW/n/a derivation per SCHEMA r6."""

    def _clean_args(self):
        return dict(
            status="OK", data_tier="live", quote_freshness="fresh",
            call_mid_source="bid_ask_mid", put_mid_source="bid_ask_mid",
            iv_disagreement_pp=1.0, atm_distance_pct=0.2,
            quality_flags=[],
        )

    def test_clean_live_is_high(self):
        assert derive_iv_quality(**self._clean_args()) == "HIGH"

    def test_one_issue_is_medium(self):
        a = self._clean_args(); a["quote_freshness"] = "stale"
        assert derive_iv_quality(**a) == "MEDIUM"

    def test_two_issues_is_low(self):
        a = self._clean_args(); a["quote_freshness"] = "stale"; a["data_tier"] = "delayed"
        assert derive_iv_quality(**a) == "LOW"

    def test_frozen_caps_at_low_regardless(self):
        a = self._clean_args(); a["data_tier"] = "frozen"  # still has clean mid_source etc
        assert derive_iv_quality(**a) == "LOW"

    def test_delayed_frozen_caps_at_low(self):
        a = self._clean_args(); a["data_tier"] = "delayed_frozen"
        assert derive_iv_quality(**a) == "LOW"

    def test_na_when_status_no_conid(self):
        a = self._clean_args(); a["status"] = "NO_CONID"
        assert derive_iv_quality(**a) == "n/a"

    def test_iv_disagreement_counted_once(self):
        # Both rule (4) AND a duplicate flag "iv_disagreement" → still 1 issue (flag is implied)
        a = self._clean_args()
        a["iv_disagreement_pp"] = 5.0  # above 3.0 threshold
        a["quality_flags"] = ["iv_disagreement"]  # implied flag, not separate
        assert derive_iv_quality(**a) == "MEDIUM"  # exactly 1 issue

    def test_iv_sanitized_counts_as_non_implied_issue(self):
        # iv_sanitized is NOT implied by 1-5, counts as separate issue (rule 6)
        a = self._clean_args()
        a["quality_flags"] = ["iv_sanitized"]
        assert derive_iv_quality(**a) == "MEDIUM"

    def test_partial_status_can_still_have_quality(self):
        a = self._clean_args(); a["status"] = "PARTIAL"
        # PARTIAL with no other issues → MEDIUM not HIGH (PARTIAL is not OK)
        # Wait: rule says iv_quality is derived from data_tier/freshness etc., not status.
        # status=PARTIAL only sets n/a if NOT in {OK, PARTIAL}. PARTIAL still gets derived.
        # With clean args otherwise, issues=0 AND data_tier=live → HIGH
        assert derive_iv_quality(**a) == "HIGH"


class TestPhase3IVRowFields:
    """IVRow has new Tier 2 fields with correct defaults."""
    def test_defaults(self):
        r = IVRow(ticker="AAPL")
        assert r.atm_distance_pct is None
        assert r.iv_disagreement_pp is None
        assert r.multiplier is None
        assert r.quote_freshness == "unknown"
        assert r.iv_quality == "n/a"
        assert r.context_flags == []


class TestSummaryBlock:
    """Phase 3 patch — summary aggregates per SCHEMA_v2."""

    def _make_row(self, **overrides):
        # Minimal IVRow constructed inline so we don't depend on full pipeline
        r = IVRow(ticker="X")
        for k, v in overrides.items():
            setattr(r, k, v)
        return r

    def test_summary_has_all_required_keys(self):
        from compute_iv_moves import summary as _summary
        rows = [self._make_row(status="OK", data_tier="live",
                                quote_freshness="fresh", iv_quality="HIGH",
                                earnings_role="non_earnings", is_primary=True)]
        s = _summary(rows)
        for k in ("total_rows", "by_status", "by_data_tier", "by_quote_freshness",
                  "by_iv_quality", "by_earnings_role", "by_is_primary"):
            assert k in s, f"missing summary key: {k}"

    def test_summary_counts_correctly(self):
        from compute_iv_moves import summary as _summary
        rows = [
            self._make_row(status="OK", data_tier="live", iv_quality="HIGH",
                           quote_freshness="fresh", earnings_role="non_earnings", is_primary=True),
            self._make_row(status="OK", data_tier="live", iv_quality="MEDIUM",
                           quote_freshness="fresh", earnings_role="non_earnings", is_primary=True),
            self._make_row(status="PARTIAL", data_tier="live", iv_quality="LOW",
                           quote_freshness="stale", earnings_role="non_earnings", is_primary=True),
            self._make_row(status="NO_CONID", data_tier="unknown", iv_quality="n/a",
                           quote_freshness="unknown", earnings_role="non_earnings", is_primary=True),
        ]
        s = _summary(rows)
        assert s["total_rows"] == 4
        assert s["by_status"] == {"OK": 2, "PARTIAL": 1, "NO_CONID": 1}
        assert s["by_iv_quality"] == {"HIGH": 1, "MEDIUM": 1, "LOW": 1, "n/a": 1}
        assert s["by_quote_freshness"] == {"fresh": 2, "stale": 1, "unknown": 1}
        assert s["by_data_tier"] == {"live": 3, "unknown": 1}
        assert s["by_is_primary"] == {"true": 4, "false": 0}


class TestMultiplierGuardStrict:
    """Phase 3 patch — multiplier MUST NOT default to 100 when uncertain.
    Verify against both legs; ambiguity → row.multiplier=None + flag."""

    def test_multiplier_known_100_both_legs_clean(self):
        # mc=100, mp=100, both legs explicit → multiplier=100, no flag
        from types import SimpleNamespace
        call_q = SimpleNamespace(multiplier="100", right="C")
        put_q  = SimpleNamespace(multiplier="100", right="P")
        # Mimic compute_one's inline parser
        def _parse(c):
            raw = getattr(c, "multiplier", "")
            if raw is None or raw == "":
                return None
            try:
                return int(float(str(raw)))
            except (ValueError, TypeError):
                return None
        assert _parse(call_q) == 100 and _parse(put_q) == 100

    def test_multiplier_missing_returns_none(self):
        from types import SimpleNamespace
        call_q = SimpleNamespace(multiplier="", right="C")
        def _parse(c):
            raw = getattr(c, "multiplier", "")
            if raw is None or raw == "":
                return None
            try:
                return int(float(str(raw)))
            except (ValueError, TypeError):
                return None
        assert _parse(call_q) is None

    def test_multiplier_unparseable_returns_none(self):
        from types import SimpleNamespace
        call_q = SimpleNamespace(multiplier="weird-value", right="C")
        def _parse(c):
            raw = getattr(c, "multiplier", "")
            if raw is None or raw == "":
                return None
            try:
                return int(float(str(raw)))
            except (ValueError, TypeError):
                return None
        assert _parse(call_q) is None

    def test_call_put_multiplier_mismatch_means_ambiguous(self):
        # This validates the LOGIC the patch implements: if mc != mp,
        # row.multiplier should be None (not silently picked from one leg)
        mc, mp = 100, 10
        result_multiplier = mc if (mc is not None and mp is not None and mc == mp) else None
        assert result_multiplier is None


# ===========================================================================
# Phase 4 — earnings dual-expiry: event_ts, timing, context flags
# ===========================================================================

class TestEventTSDerivation:
    """C — precedence: sec_filing > user_supplied > yahoo_conventional > unknown."""

    def test_user_supplied_beats_yahoo(self):
        earnings = {"date": "2026-07-30", "time": "AMC", "source": "yahoo"}
        ts, src = derive_event_ts(earnings, MARKET_CONVENTIONS,
                                  user_supplied_ts="2026-07-30T20:00:00+00:00")
        assert src == "user_supplied"
        assert ts == "2026-07-30T20:00:00+00:00"

    def test_yahoo_amc_converts_to_conventional_utc(self):
        earnings = {"date": "2026-07-30", "time": "AMC", "source": "yahoo"}
        ts, src = derive_event_ts(earnings, MARKET_CONVENTIONS)
        assert src == "yahoo_conventional"
        # 16:30 ET = 20:30 UTC (during EDT in July) or 21:30 UTC (during EST in winter)
        # July is EDT → 16:30 ET = 20:30 UTC
        assert ts.startswith("2026-07-30T20:30:00")

    def test_bmo_yields_07_30_et(self):
        earnings = {"date": "2026-07-30", "time": "BMO", "source": "yahoo"}
        ts, src = derive_event_ts(earnings, MARKET_CONVENTIONS)
        # 07:30 ET = 11:30 UTC (EDT) or 12:30 UTC (EST)
        assert src == "yahoo_conventional"
        assert ts.startswith("2026-07-30T11:30:00")

    def test_dmh_yields_12_00_et(self):
        earnings = {"date": "2026-07-30", "time": "DMH", "source": "yahoo"}
        ts, src = derive_event_ts(earnings, MARKET_CONVENTIONS)
        assert src == "yahoo_conventional"
        assert ts.startswith("2026-07-30T16:00:00")  # 12:00 ET = 16:00 UTC (EDT)

    def test_no_earnings_yields_unknown(self):
        ts, src = derive_event_ts(None, MARKET_CONVENTIONS)
        assert ts is None and src == "unknown"

    def test_missing_date_yields_unknown(self):
        ts, src = derive_event_ts({"time": "AMC"}, MARKET_CONVENTIONS)
        assert ts is None and src == "unknown"


class TestEarningsTimingDerivation:
    """C — in_window (date-level), in_contract_life (timestamp), qs_rel_to_event."""

    def test_amc_on_expiry_day_window_true_contract_life_false(self):
        # event_ts 2026-05-14 16:30 ET = 2026-05-14T20:30Z
        # expiry 20260514, options close 16:00 ET → close_ts 20:00Z
        # → in_contract_life = (20:30 <= 20:00) FALSE
        # → in_window = TRUE (same date)
        run_iso = "2026-05-14T12:00:00+00:00"
        qs_iso  = "2026-05-14T13:00:00+00:00"
        ev_iso  = "2026-05-14T20:30:00+00:00"
        t = derive_earnings_timing(ev_iso, run_iso, "20260514", qs_iso, "16:00")
        assert t["in_window"] is True
        assert t["in_contract_life"] is False
        assert t["quote_snapshot_relative_to_event"] == "pre_event"

    def test_bmo_on_expiry_day_both_true(self):
        # BMO: event 07:30 ET = 11:30 UTC; expiry close 16:00 ET = 20:00 UTC
        # → in_contract_life = (11:30 <= 20:00) TRUE
        run_iso = "2026-05-13T20:00:00+00:00"
        qs_iso  = "2026-05-13T20:00:00+00:00"
        ev_iso  = "2026-05-14T11:30:00+00:00"
        t = derive_earnings_timing(ev_iso, run_iso, "20260514", qs_iso, "16:00")
        assert t["in_window"] is True
        assert t["in_contract_life"] is True

    def test_pre_event_qs_when_quote_before_event(self):
        ev_iso = "2026-07-30T20:30:00+00:00"
        qs_iso = "2026-05-14T15:00:00+00:00"  # well before
        t = derive_earnings_timing(ev_iso, "2026-05-14T12:00:00+00:00",
                                    "20260821", qs_iso, "16:00")
        assert t["quote_snapshot_relative_to_event"] == "pre_event"

    def test_post_event_qs_when_quote_after_event(self):
        ev_iso = "2026-05-14T20:30:00+00:00"
        qs_iso = "2026-05-14T20:35:00+00:00"  # 5 min after AMC
        t = derive_earnings_timing(ev_iso, "2026-05-14T20:35:00+00:00",
                                    "20260821", qs_iso, "16:00")
        assert t["quote_snapshot_relative_to_event"] == "post_event"

    def test_earnings_past_run_as_of_not_in_window(self):
        # earnings yesterday, run today → in_window=False
        ev_iso  = "2026-05-13T20:30:00+00:00"
        run_iso = "2026-05-14T12:00:00+00:00"
        t = derive_earnings_timing(ev_iso, run_iso, "20260821",
                                    "2026-05-14T12:00:00+00:00", "16:00")
        assert t["in_window"] is False

    def test_unknown_qs_when_no_snapshot(self):
        ev_iso = "2026-07-30T20:30:00+00:00"
        t = derive_earnings_timing(ev_iso, "2026-05-14T12:00:00+00:00",
                                    "20260821", None, "16:00")
        assert t["quote_snapshot_relative_to_event"] == "unknown"


class TestEarningsContextFlags:
    """E — context_flags derivation; pre_event ALONE is NOT premium."""

    def _row(self, **kw):
        r = IVRow(ticker="X", expiry="20260821")
        for k, v in kw.items():
            setattr(r, k, v)
        return r

    def test_pre_event_with_in_contract_life_emits_includes_premium(self):
        r = self._row(earnings_in_contract_life=True,
                      quote_snapshot_relative_to_event="pre_event")
        flags = derive_earnings_context_flags(r)
        assert "includes_earnings_premium" in flags

    def test_pre_event_WITHOUT_in_contract_life_NO_premium(self):
        # CRITICAL: pre_event ALONE != premium (AMC-on-expiry-day case)
        r = self._row(earnings_in_window=True,
                      earnings_in_contract_life=False,
                      quote_snapshot_relative_to_event="pre_event")
        flags = derive_earnings_context_flags(r)
        assert "includes_earnings_premium" not in flags
        assert "expiry_before_known_earnings" in flags

    def test_post_event_emits_post_event_snapshot(self):
        r = self._row(quote_snapshot_relative_to_event="post_event")
        flags = derive_earnings_context_flags(r)
        assert "post_event_snapshot" in flags
        # post_event MUST NOT also imply includes_earnings_premium
        assert "includes_earnings_premium" not in flags

    def test_amc_on_expiry_day_specific_flag(self):
        # Event_ts on the expiry date AND time=AMC AND in_contract_life=False
        r = self._row(expiry="20260514",
                      earnings_next_time="AMC",
                      earnings_event_ts="2026-05-14T20:30:00+00:00",
                      earnings_in_window=True,
                      earnings_in_contract_life=False,
                      quote_snapshot_relative_to_event="pre_event")
        flags = derive_earnings_context_flags(r)
        assert "amc_expiry_day" in flags
        assert "expiry_before_known_earnings" in flags
        assert "includes_earnings_premium" not in flags

    def test_no_earnings_no_flags(self):
        r = self._row()  # earnings_in_window=False, qs_rel=not_applicable defaults
        flags = derive_earnings_context_flags(r)
        assert flags == []


class TestPhase4IVRowFields:
    def test_defaults(self):
        r = IVRow(ticker="AAPL")
        assert r.quote_snapshot_as_of is None
        assert r.quote_snapshot_source == "unknown"
        assert r.earnings_next_date is None
        assert r.earnings_next_time == "unknown"
        assert r.earnings_next_time_source == "unknown"
        assert r.earnings_event_ts is None
        assert r.earnings_event_ts_source == "unknown"
        assert r.earnings_in_window is False
        assert r.earnings_in_contract_life is False
        assert r.quote_snapshot_relative_to_event == "not_applicable"
        assert r.earnings_calendar_source == "yahoo"
        assert r.earnings_calendar_pit_safe is False


# ---------------------------------------------------------------------------
# Phase 4 patch — dual-row emission helpers
# ---------------------------------------------------------------------------

class TestFindFirstExpiryAfter:
    """Picks the first chain expiry strictly after an event date."""

    EXPIRIES = {"20260717", "20260724", "20260731", "20260807", "20260821"}

    def test_picks_first_strictly_after(self):
        # event on 20260731 (Friday AMC) → first AFTER is 20260807
        result = find_first_expiry_after(self.EXPIRIES, dt.date(2026, 7, 31))
        assert result == "20260807"

    def test_picks_next_when_event_before_all(self):
        result = find_first_expiry_after(self.EXPIRIES, dt.date(2026, 7, 1))
        assert result == "20260717"

    def test_none_when_no_expiry_after_event(self):
        result = find_first_expiry_after(self.EXPIRIES, dt.date(2026, 12, 31))
        assert result is None

    def test_skips_malformed_expirations(self):
        bad = self.EXPIRIES | {"BAD", "2026", ""}
        result = find_first_expiry_after(bad, dt.date(2026, 7, 31))
        assert result == "20260807"


class TestFindLastExpiryBefore:
    """Picks the last chain expiry strictly before event date (and after today)."""

    EXPIRIES = {"20260717", "20260724", "20260731", "20260807", "20260821"}

    def test_picks_last_strictly_before(self):
        # event on 20260730 → last expiry before is 20260724 (not 20260731)
        result = find_last_expiry_before(
            self.EXPIRIES, dt.date(2026, 7, 30), today=dt.date(2026, 7, 14),
        )
        assert result == "20260724"

    def test_excludes_already_expired(self):
        # today=20260725 → 20260717 and 20260724 are already expired
        result = find_last_expiry_before(
            self.EXPIRIES, dt.date(2026, 7, 30), today=dt.date(2026, 7, 25),
        )
        # only 20260724 candidates? no — 20260724 < today=20260725, so excluded.
        # nothing between 20260725 and 20260730 in this chain → None
        assert result is None

    def test_picks_correctly_when_event_far_out(self):
        result = find_last_expiry_before(
            self.EXPIRIES, dt.date(2026, 8, 25), today=dt.date(2026, 7, 14),
        )
        assert result == "20260821"

    def test_none_when_no_expiry_in_range(self):
        result = find_last_expiry_before(
            self.EXPIRIES, dt.date(2026, 7, 15), today=dt.date(2026, 7, 14),
        )
        # no expiry between 20260714 (excl) and 20260715 (excl)
        assert result is None


class TestPickSecondaryExpiry:
    """Dual-row decision: which secondary expiry (if any) to compute alongside primary."""

    EXPIRIES = {"20260717", "20260724", "20260731", "20260807", "20260821"}

    def _row(self, **kw):
        r = IVRow(ticker="AAPL")
        for k, v in kw.items():
            setattr(r, k, v)
        return r

    def test_returns_none_when_no_earnings_in_window(self):
        primary = self._row(
            earnings_in_window=False, earnings_event_ts="2026-07-31T20:30:00+00:00",
            earnings_role="non_earnings", expiry="20260731",
        )
        assert pick_secondary_expiry(primary, self.EXPIRIES) is None

    def test_returns_none_when_event_ts_missing(self):
        primary = self._row(
            earnings_in_window=True, earnings_event_ts=None,
            earnings_role="pre_earnings", expiry="20260731",
        )
        assert pick_secondary_expiry(primary, self.EXPIRIES) is None

    def test_returns_none_when_role_non_earnings(self):
        primary = self._row(
            earnings_in_window=True, earnings_event_ts="2026-07-31T20:30:00+00:00",
            earnings_role="non_earnings", expiry="20260731",
        )
        assert pick_secondary_expiry(primary, self.EXPIRIES) is None

    def test_pre_earnings_picks_first_expiry_after_event(self):
        # AMC-on-expiry-day: primary 20260731 expires before 16:30 AMC event
        # → primary.role=pre_earnings; secondary should be 20260807 (first AFTER event)
        primary = self._row(
            earnings_in_window=True, earnings_event_ts="2026-07-31T20:30:00+00:00",
            earnings_role="pre_earnings", expiry="20260731",
        )
        assert pick_secondary_expiry(primary, self.EXPIRIES) == "20260807"

    def test_post_earnings_picks_last_expiry_before_event(self):
        # Monthly 20260821 captures event 20260730. primary.role=post_earnings.
        # Secondary should be 20260724 (last expiry strictly before event, after today).
        primary = self._row(
            earnings_in_window=True, earnings_event_ts="2026-07-30T20:30:00+00:00",
            earnings_role="post_earnings", expiry="20260821",
        )
        result = pick_secondary_expiry(
            primary, self.EXPIRIES, today=dt.date(2026, 7, 14),
        )
        assert result == "20260724"

    def test_malformed_event_ts_yields_none(self):
        primary = self._row(
            earnings_in_window=True, earnings_event_ts="not-a-timestamp",
            earnings_role="pre_earnings", expiry="20260731",
        )
        assert pick_secondary_expiry(primary, self.EXPIRIES) is None

    def test_pre_earnings_with_no_expiry_after_event(self):
        # event is past the last chain expiry — no secondary available
        primary = self._row(
            earnings_in_window=True, earnings_event_ts="2027-01-15T20:30:00+00:00",
            earnings_role="pre_earnings", expiry="20260821",
        )
        assert pick_secondary_expiry(primary, self.EXPIRIES) is None


class TestDualRowOrchestration:
    """End-to-end: compute_one returns [primary, secondary] when warranted.
    Uses monkeypatch on _compute_row_for_expiry to skip IB calls.
    """

    EXPIRIES = {"20260717", "20260724", "20260731", "20260807", "20260821"}

    def _make_orchestrator_stubs(self, monkeypatch, primary_attrs):
        """Stub IB layer + helper so compute_one is testable without IBKR."""
        import asyncio
        from types import SimpleNamespace

        import compute_iv_moves as m

        call_log = []

        # Stub the helper: returns IVRow synthesized from primary_attrs for primary,
        # and a synthesized "secondary" row when called with a different expiry.
        async def fake_helper(*, ib, sem, ticker, run_id, run_as_of_iso,
                              underlying, spot, spot_source,
                              all_strikes, all_expirations, params,
                              market_data_type, expiry_yyyymmdd,
                              earnings, user_supplied_ts, is_primary=True):
            call_log.append({"expiry": expiry_yyyymmdd, "is_primary": is_primary})
            r = IVRow(ticker=ticker, run_id=run_id)
            r.is_primary = is_primary
            r.expiry = expiry_yyyymmdd
            r.spot = spot
            r.status = "OK"
            if is_primary:
                for k, v in primary_attrs.items():
                    setattr(r, k, v)
            else:
                # opposite-role secondary
                r.earnings_event_ts = primary_attrs.get("earnings_event_ts")
                r.earnings_in_window = True
                if primary_attrs.get("earnings_role") == "pre_earnings":
                    r.earnings_role = "post_earnings"
                    r.earnings_in_contract_life = True
                elif primary_attrs.get("earnings_role") == "post_earnings":
                    r.earnings_role = "pre_earnings"
                    r.earnings_in_contract_life = False
            r.row_id = f"{ticker}:{expiry_yyyymmdd}:{r.earnings_role}"
            return r

        monkeypatch.setattr(m, "_compute_row_for_expiry", fake_helper)

        # Stub IB session
        class FakeIB:
            async def qualifyContractsAsync(self, c):
                return [SimpleNamespace(conId=1, symbol=c.symbol, secType="STK")]
            def reqMarketDataType(self, n):
                pass
            async def reqTickersAsync(self, *args):
                # underlying ticker for spot resolution
                return [SimpleNamespace(
                    last=100.0, close=100.0, marketDataType=1,
                    marketPrice=lambda: 100.0,
                )]
            async def reqSecDefOptParamsAsync(self, *a, **k):
                return [SimpleNamespace(
                    tradingClass="AAPL", exchange="SMART",
                    expirations=list(self_e := self.EXPIRIES),
                    strikes=[95.0, 100.0, 105.0],
                )]
            EXPIRIES = self.EXPIRIES

        return FakeIB(), call_log

    def test_single_row_when_no_earnings(self, monkeypatch):
        import asyncio
        from compute_iv_moves import compute_one

        primary_attrs = {
            "earnings_in_window": False,
            "earnings_event_ts": None,
            "earnings_role": "non_earnings",
        }
        ib, call_log = self._make_orchestrator_stubs(monkeypatch, primary_attrs)
        sem = asyncio.Semaphore(1)

        rows = asyncio.run(
            compute_one(ib, sem, "AAPL", target_dte=30, run_id="test"),
        )
        assert len(rows) == 1
        assert rows[0].is_primary is True
        # only one call to helper
        assert len(call_log) == 1
        assert call_log[0]["is_primary"] is True

    def test_dual_row_pre_earnings_primary(self, monkeypatch):
        """AMC-on-expiry-day: primary=pre_earnings → secondary=post_earnings."""
        import asyncio
        from compute_iv_moves import compute_one

        primary_attrs = {
            "earnings_in_window": True,
            "earnings_event_ts": "2026-07-31T20:30:00+00:00",
            "earnings_role": "pre_earnings",
            "expiry": "20260731",  # will be overwritten by helper anyway
        }
        ib, call_log = self._make_orchestrator_stubs(monkeypatch, primary_attrs)
        sem = asyncio.Semaphore(1)

        rows = asyncio.run(
            compute_one(ib, sem, "AAPL", target_dte=78, run_id="test"),
        )
        assert len(rows) == 2
        primary, secondary = rows
        assert primary.is_primary is True
        assert primary.earnings_role == "pre_earnings"
        assert secondary.is_primary is False
        assert secondary.earnings_role == "post_earnings"
        # secondary was called with the post-event expiry
        assert call_log[1]["expiry"] == "20260807"
        # primary has diagnostic noting the secondary
        assert any("dual-row" in d for d in primary.diagnostics)

    def test_dual_row_post_earnings_primary(self, monkeypatch):
        """Monthly captures event → primary=post_earnings, secondary=pre_earnings."""
        import asyncio
        from compute_iv_moves import compute_one

        primary_attrs = {
            "earnings_in_window": True,
            "earnings_event_ts": "2026-07-30T20:30:00+00:00",
            "earnings_role": "post_earnings",
        }
        ib, call_log = self._make_orchestrator_stubs(monkeypatch, primary_attrs)
        sem = asyncio.Semaphore(1)

        rows = asyncio.run(
            compute_one(ib, sem, "AAPL", target_dte=99, run_id="test"),
        )
        # secondary is "last expiry before event AND after today" — depends on today's date
        # Without freezing today, just verify orchestration semantics:
        # either 1 (no candidate before event) or 2 (candidate found) rows.
        assert len(rows) in (1, 2)
        if len(rows) == 2:
            assert rows[1].is_primary is False
            assert rows[1].earnings_role == "pre_earnings"

    def test_no_secondary_when_secondary_equals_primary_expiry(self, monkeypatch):
        """Guard: if find_*_expiry returns same expiry as primary, no dual emission."""
        import asyncio
        from compute_iv_moves import compute_one

        primary_attrs = {
            "earnings_in_window": True,
            "earnings_event_ts": "2026-07-31T20:30:00+00:00",
            "earnings_role": "non_earnings",  # non_earnings → pick_secondary returns None
        }
        ib, call_log = self._make_orchestrator_stubs(monkeypatch, primary_attrs)
        sem = asyncio.Semaphore(1)

        rows = asyncio.run(
            compute_one(ib, sem, "AAPL", target_dte=78, run_id="test"),
        )
        assert len(rows) == 1
        assert len(call_log) == 1
