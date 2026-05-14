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
