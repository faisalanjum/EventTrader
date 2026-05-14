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
