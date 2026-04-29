"""Targeted tests for U1 — `is_current_quarter` flagging via fiscal-math.

Covers:
  - `_provider_fde_for_period` helper: archetype matrix, /A normalization, missing inputs.
  - `_build_quarterly_rows` `target_fde` routing: 13-week fiscal cases, calendar regressions, fallback.
  - `_build_forward_estimates` `cutoff_fde` regression: just-reported quarter excluded.

Run:
    venv/bin/python -m pytest scripts/earnings/test_builders_consensus_current_quarter.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

from scripts.earnings.builders import consensus as bc

pytestmark = pytest.mark.builders


def _quarterly(rows: list[dict]) -> dict:
    """Wrap mock AV EARNINGS response."""
    return {"quarterlyEarnings": rows}


def _row(fde: str, reported_date: str, *, eps_est=1.0, eps_act=1.05,
         eps_surp=0.05, eps_surp_pct=5.0, report_time="post-market") -> dict:
    return {
        "fiscalDateEnding": fde,
        "reportedDate": reported_date,
        "reportTime": report_time,
        "reportedEPS": str(eps_act),
        "estimatedEPS": str(eps_est),
        "surprise": str(eps_surp),
        "surprisePercentage": str(eps_surp_pct),
    }


# ── _provider_fde_for_period ────────────────────────────────────────────────

class TestProviderFdeHelper:
    def test_avgo_q4_fy2023_13week_sun_close(self):
        # period_of_report=2023-10-29 (last Sunday Oct), fye_month=10, 10-K → provider_fde=2023-10-31
        out = bc._provider_fde_for_period("2023-10-29", 10, "10-K")
        assert out == "2023-10-31"

    def test_aapl_q4_fy2024_last_sat_sep(self):
        # AAPL Q4 FY2024 fiscal close = 2024-09-28 (last Sat). fye_month=9.
        out = bc._provider_fde_for_period("2024-09-28", 9, "10-K")
        assert out == "2024-09-30"

    def test_calendar_dec31_passes_through(self):
        # CHRW Q4 FY2025: period=2025-12-31, fye_month=12. Provider FDE matches.
        out = bc._provider_fde_for_period("2025-12-31", 12, "10-K")
        assert out == "2025-12-31"

    def test_calendar_jan31_passes_through(self):
        # CXM-style Jan 31 calendar. fye_month=1, 10-K → provider_fde=2026-01-31.
        out = bc._provider_fde_for_period("2026-01-31", 1, "10-K")
        assert out == "2026-01-31"

    def test_amendment_form_normalized(self):
        # 10-K/A must be normalized to 10-K before fiscal_math; otherwise
        # period_to_fiscal misclassifies as 10-Q.
        out_amend = bc._provider_fde_for_period("2023-10-29", 10, "10-K/A")
        out_plain = bc._provider_fde_for_period("2023-10-29", 10, "10-K")
        assert out_amend == out_plain == "2023-10-31"

    def test_missing_period_returns_none(self):
        assert bc._provider_fde_for_period(None, 10, "10-K") is None
        assert bc._provider_fde_for_period("", 10, "10-K") is None

    def test_missing_fye_month_returns_none(self):
        assert bc._provider_fde_for_period("2023-10-29", None, "10-K") is None
        assert bc._provider_fde_for_period("2023-10-29", 0, "10-K") is None  # falsy

    def test_missing_form_type_returns_none(self):
        assert bc._provider_fde_for_period("2023-10-29", 10, None) is None
        assert bc._provider_fde_for_period("2023-10-29", 10, "") is None

    def test_string_fye_month_coerced(self):
        # Defensive: if upstream stores fye_month as string (Neo4j edge), still works.
        out = bc._provider_fde_for_period("2023-10-29", "10", "10-K")
        assert out == "2023-10-31"

    def test_garbage_period_returns_none(self):
        assert bc._provider_fde_for_period("not-a-date", 10, "10-K") is None


# ── _build_quarterly_rows target_fde routing ────────────────────────────────

class TestBuildQuarterlyRowsTargetFde:
    def test_avgo_target_fde_routes_correctly(self):
        # Live mode (as_of_ts=None): no PIT filter, all rows flow through.
        # AVGO-style: period=2023-10-29 SEC, AV row at fde=2023-10-31. Strict equality
        # would miss; target_fde=2023-10-31 must flag this row True.
        rows = bc._build_quarterly_rows(
            earnings_data=_quarterly([
                _row("2023-10-31", "2023-12-07"),
                _row("2023-07-30", "2023-08-31"),
            ]),
            income_data=None, estimates_data=None,
            period_of_report="2023-10-29",
            filed_8k_ts=None, as_of_ts=None,
            gaps=[],
            target_fde="2023-10-31",
        )
        flags = {r["fiscalDateEnding"]: r["is_current_quarter"] for r in rows}
        assert flags == {"2023-10-31": True, "2023-07-30": False}

    def test_calendar_regression_safety(self):
        # CHRW-style: period=2025-12-31, target_fde=2025-12-31 (calendar). Same row True.
        rows = bc._build_quarterly_rows(
            earnings_data=_quarterly([
                _row("2025-12-31", "2026-01-28"),
                _row("2025-09-30", "2025-10-29"),
            ]),
            income_data=None, estimates_data=None,
            period_of_report="2025-12-31",
            filed_8k_ts=None, as_of_ts=None,
            gaps=[],
            target_fde="2025-12-31",
        )
        flags = {r["fiscalDateEnding"]: r["is_current_quarter"] for r in rows}
        assert flags == {"2025-12-31": True, "2025-09-30": False}

    def test_target_fde_none_falls_back_to_period_of_report(self):
        # If caller passes target_fde=None, behavior is existing strict-equality
        # against period_of_report. This is the ACI/missing-inputs fallback.
        rows = bc._build_quarterly_rows(
            earnings_data=_quarterly([
                _row("2023-10-31", "2023-12-07"),
                _row("2023-10-29", "2023-12-07"),  # synthetic — would match
            ]),
            income_data=None, estimates_data=None,
            period_of_report="2023-10-29",
            filed_8k_ts=None, as_of_ts=None,
            gaps=[],
            target_fde=None,
        )
        flags = {r["fiscalDateEnding"]: r["is_current_quarter"] for r in rows}
        # Strict equality on period_of_report=2023-10-29: only the synthetic row matches.
        assert flags == {"2023-10-31": False, "2023-10-29": True}

    def test_no_match_emits_fiscal_match_fallback_gap_when_rows_present(self):
        # ACI-class case: rows exist but none match target_fde or period_of_report.
        # Gap should be emitted exactly once.
        gaps: list = []
        bc._build_quarterly_rows(
            earnings_data=_quarterly([
                _row("2026-08-31", "2026-10-15"),  # ACI-style shifted FDE
            ]),
            income_data=None, estimates_data=None,
            period_of_report="2026-09-09",       # SEC exact, no match
            filed_8k_ts=None, as_of_ts=None,
            gaps=gaps,
            target_fde="2026-09-30",             # computed, no match
        )
        fallback_gaps = [g for g in gaps if g.get("type") == "fiscal_match_fallback"]
        assert len(fallback_gaps) == 1
        assert fallback_gaps[0]["period_of_report"] == "2026-09-09"
        assert fallback_gaps[0]["target_fde"] == "2026-09-30"

    def test_no_rows_does_not_emit_fiscal_match_fallback(self):
        # AV upstream failure → empty rows → existing empty_data gap fires; we
        # MUST NOT add a redundant fiscal_match_fallback on top.
        gaps: list = []
        bc._build_quarterly_rows(
            earnings_data=_quarterly([]),   # empty
            income_data=None, estimates_data=None,
            period_of_report="2023-10-29",
            filed_8k_ts=None, as_of_ts=None,
            gaps=gaps,
            target_fde="2023-10-31",
        )
        assert not any(g.get("type") == "fiscal_match_fallback" for g in gaps)


# ── _build_forward_estimates cutoff regression ──────────────────────────────

class TestForwardEstimatesCutoff:
    def test_just_reported_excluded_when_cutoff_fde_provided(self):
        # AVGO-style: AV EARNINGS_ESTIMATES still has a row at fde=2023-10-31 for
        # the just-reported quarter (transient). Without cutoff_fde fix, the string
        # compare "2023-10-31" <= "2023-10-29" returns False and the row LEAKS into
        # forward_estimates. With cutoff_fde=2023-10-31, it must be excluded.
        estimates = {"data": [
            {"date": "2023-10-31", "horizon": "fiscal quarter",
             "eps_estimate_average": 1.10, "revenue_estimate_average": 9.3e9},
            {"date": "2024-01-31", "horizon": "fiscal quarter",
             "eps_estimate_average": 1.20, "revenue_estimate_average": 9.5e9},
        ]}
        out = bc._build_forward_estimates(
            estimates_data=estimates,
            period_of_report="2023-10-29",
            gaps=[],
            cutoff_fde="2023-10-31",
        )
        fdes = [r["fiscalDateEnding"] for r in out]
        assert "2023-10-31" not in fdes
        assert "2024-01-31" in fdes

    def test_cutoff_fde_none_falls_back_to_period_of_report(self):
        # Backwards-compat: if cutoff_fde is omitted/None, behaves as today
        # (uses period_of_report). 13-week leak is preserved (existing bug),
        # confirming the function is purely additive when caller doesn't opt in.
        estimates = {"data": [
            {"date": "2023-10-31", "horizon": "fiscal quarter",
             "eps_estimate_average": 1.10, "revenue_estimate_average": 9.3e9},
        ]}
        out = bc._build_forward_estimates(
            estimates_data=estimates,
            period_of_report="2023-10-29",
            gaps=[],
            cutoff_fde=None,
        )
        # Existing bug preserved: "2023-10-31" > "2023-10-29" lex, so leaks in.
        assert any(r["fiscalDateEnding"] == "2023-10-31" for r in out)
