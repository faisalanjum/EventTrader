"""Synthetic minimal-input bundle builders for renderer Layer 3 coverage.

Each builder returns a complete bundle dict that triggers a specific
renderer placeholder/edge path. Used by:
  - tests/_capture_golden.py (commit 3 capture)
  - test_renderer_degraded.py (the test that asserts byte equality)

DO NOT add behavior changes here. If a builder needs to invoke a different
renderer code path, add it as a new entry in DEGRADED_BUILDERS.
"""
from __future__ import annotations
import math
from copy import deepcopy
from typing import Any, Callable

# All builder slot names that appear in `bundle["builder_errors"]` and the
# top-level bundle keys. Source: BUNDLE_ITEM_ORDER in earnings_orchestrator.py.
ALL_BUILDER_KEYS = [
    "8k_packet", "guidance_history", "inter_quarter_context",
    "peer_earnings_snapshot", "macro_snapshot", "consensus", "prior_financials",
]


def _minimal_bundle() -> dict:
    """Bare-minimum bundle that the renderer can process without crashing.

    All builder slots are None; renderer's [NO DATA] paths handle this.
    learning_context is an empty skeleton; renderer emits §10 outer
    "## Prior Lessons (from learner)" header + "No prior lessons available"
    message (post bundle.py empty-case fix in 5f4864f), with no inner
    `## Lessons To Label` section.
    """
    return {
        "schema_version": "prediction_bundle.v1",
        "ticker": "TEST",
        "quarter_info": {
            "accession_8k":      "0000000000-00-000000",
            "filed_8k":          "2026-01-01T16:00:00-05:00",
            "market_session":    "post_market",
            "period_of_report":  "2025-12-31",
            "prev_8k_ts":        "2025-10-01T16:00:00-04:00",
            "quarter_label":     "Q4_FY2025",
        },
        "pit_cutoff":     "2026-01-01T16:00:00-05:00",
        "assembled_at":   "2026-01-01T21:00:00+00:00",
        "builder_errors": None,
        "8k_packet":              None,
        "guidance_history":       None,
        "inter_quarter_context":  None,
        "peer_earnings_snapshot": None,
        "macro_snapshot":         None,
        "consensus":              None,
        "prior_financials":       None,
        "learning_context": {
            "ticker_lessons": [], "global_lessons": [],
            "ticker_ref": None, "global_ref": None,
        },
    }


# ── individual builders ──────────────────────────────────────────────

def _all_builder_errors() -> dict:
    b = _minimal_bundle()
    b["builder_errors"] = {k: f"synthetic error: {k} failed" for k in ALL_BUILDER_KEYS}
    return b


def _all_no_data() -> dict:
    # _minimal_bundle already has all slots None → triggers [NO DATA] paths
    return _minimal_bundle()


def _no_current_quarter() -> dict:
    # _render_results_and_expectations Consensus Bar emits "[No current-quarter row found]"
    b = _minimal_bundle()
    b["consensus"] = {
        "quarterly_rows": [
            {"fiscalDateEnding": "2025-09-30", "is_current_quarter": False,
             "estimatedEPS": 1.20, "reportedEPS": 1.25,
             "epsSurprisePct": 4.17, "revenueEstimate": 1e9,
             "revenueActual": 1.05e9, "revenueSurprisePct": 5.0},
        ],
        "summary": {"eps_beat_streak": 0, "quarterly_row_count": 1},
        "forward_estimates": [],
        "gaps": [],
    }
    return b


def _no_ex991() -> dict:
    # _render_results_and_expectations Reported Results emits "[No EX-99.1 found]"
    b = _minimal_bundle()
    b["8k_packet"] = {
        "accession_8k": "0000000000-00-000000",
        "form_type": "8-K",
        "items": ["Item 2.02"],
        "exhibits_99": [],   # empty — triggers the "no EX-99.1 found" branch
        "exhibits_other": [],
        "sections": [],
        "content_inventory": {"section_names": [], "exhibit_numbers": []},
        "filing_text": None,
        "sector": "Technology",
    }
    return b


def _no_lessons() -> dict:
    # §10 Prior Lessons renders the outer header + "No prior lessons available"
    # message (since 5f4864f). The inner ## Lessons To Label section is absent,
    # which is the cue the predictor uses to emit lesson_labels: [].
    return _minimal_bundle()   # already empty learning_context


def _empty_quarter_label() -> dict:
    # Forces _render_forward_guidance "Other Horizons" fallback
    b = _minimal_bundle()
    b["quarter_info"]["quarter_label"] = ""
    b["guidance_history"] = {
        "series": [
            {
                "metric": "Revenue",
                "basis_norm": "non_gaap",
                "segment": "Total",
                "segment_slug": "total",
                "period_scope": "quarter",
                "resolved_unit": "m_usd",
                "updates": [
                    {"low": 1000, "high": 1100, "given_day": "2026-01-15",
                     "fiscal_year": 2026, "fiscal_quarter": 1,
                     "period_start": None, "period_end": None,
                     "qualitative": None, "conditions": None},
                ],
            },
        ],
        "summary": {"total_series": 1, "total_updates_collapsed": 1,
                    "earliest_date": "2026-01-15", "latest_date": "2026-01-15"},
    }
    return b


def _unicode_in_text() -> dict:
    # Ensures pipe escaping + UTF-8 preserved
    b = _minimal_bundle()
    b["inter_quarter_context"] = {
        "ticker": "TEST", "sector": "Technology", "industry": "Software",
        "prev_8k_ts": "2025-10-01T16:00:00-04:00",
        "context_cutoff_ts": "2026-01-01T16:00:00-05:00",
        "context_cutoff_reason": "8K_filing",
        "prev_day": "2025-10-01", "cutoff_day": "2026-01-01",
        "pit_cutoff": "2026-01-01T16:00:00-05:00",
        "source_mode": "historical",
        "schema_version": "v1", "assembled_at": "2026-01-01T21:00:00+00:00",
        "summary": {"trading_days_ordinary": 1, "significant_move_days": 0,
                    "gap_days": 0, "total_news": 1, "total_filings": 0,
                    "total_dividends": 0, "total_splits": 0},
        "days": [
            {
                "date": "2025-12-15", "is_trading_day": True,
                "boundary_role": None, "price": {"close": 100.0, "daily_return": 1.5},
                "spy_return": 0.5, "sector_return": 0.8, "adj_return": 1.0,
                "is_significant": False, "is_gap_day": False,
                "events": [
                    {"type": "news", "market_session": "regular",
                     "title": "Acme | Beats EPS — strong growth",  # pipe + em-dash
                     "channels": ["Earnings"],
                     "forward_returns": None},
                ],
            },
        ],
    }
    return b


def _non_finite_numbers() -> dict:
    # _fmt_num / _fmt_money / _fmt_pct guards: None → "—", NaN → "—", ±Inf → "—"
    b = _minimal_bundle()
    b["consensus"] = {
        "quarterly_rows": [
            {"fiscalDateEnding": "2025-12-31", "is_current_quarter": True,
             "estimatedEPS": float("nan"), "reportedEPS": None,
             "epsSurprisePct": float("inf"),
             "revenueEstimate": float("-inf"), "revenueActual": None,
             "revenueSurprisePct": None},
        ],
        "summary": {}, "forward_estimates": [], "gaps": [],
    }
    return b


def _huge_and_tiny() -> dict:
    # Magnitude scaling boundaries
    b = _minimal_bundle()
    b["consensus"] = {
        "quarterly_rows": [
            {"fiscalDateEnding": "2025-12-31", "is_current_quarter": True,
             "estimatedEPS": 1e15, "reportedEPS": 1e-15,
             "epsSurprisePct": 0.0, "revenueEstimate": -0.0,
             "revenueActual": 1.0, "revenueSurprisePct": -1.0},
        ],
        "summary": {}, "forward_estimates": [], "gaps": [],
    }
    return b


def _guidance_qual_only() -> dict:
    # _fmt_guidance_value qualitative-only path
    b = _minimal_bundle()
    b["guidance_history"] = {
        "series": [
            {
                "metric": "Outlook", "basis_norm": "unknown",
                "segment": "Total", "segment_slug": "total",
                "period_scope": "quarter", "resolved_unit": "unknown",
                "updates": [
                    {"low": None, "high": None, "mid": None,
                     "given_day": "2026-01-15",
                     "fiscal_year": 2026, "fiscal_quarter": 2,
                     "period_start": None, "period_end": None,
                     "qualitative": "strong growth expected",
                     "conditions": None},
                ],
            },
        ],
        "summary": {"total_series": 1, "total_updates_collapsed": 1,
                    "earliest_date": "2026-01-15", "latest_date": "2026-01-15"},
    }
    return b


def _guidance_all_units() -> dict:
    # Every supported unit in _fmt_guidance_value
    b = _minimal_bundle()
    units = ["m_usd", "k_usd", "usd", "percent", "percent_yoy",
             "percent_points", "basis_points", "x", "count", "unknown"]
    series = []
    for i, u in enumerate(units, start=1):
        series.append({
            "metric": f"Metric_{u}", "basis_norm": "non_gaap",
            "segment": "Total", "segment_slug": "total",
            "period_scope": "quarter", "resolved_unit": u,
            "updates": [
                {"low": 10, "high": 20, "mid": None,
                 "given_day": "2026-01-15",
                 "fiscal_year": 2026, "fiscal_quarter": i % 4 + 1,
                 "period_start": None, "period_end": None,
                 "qualitative": None, "conditions": None},
            ],
        })
    b["guidance_history"] = {
        "series": series,
        "summary": {"total_series": len(units),
                    "total_updates_collapsed": len(units),
                    "earliest_date": "2026-01-15",
                    "latest_date": "2026-01-15"},
    }
    return b


def _iq_no_events() -> dict:
    # Inter-quarter day with empty events list (omits all 4 event sub-tables)
    b = _minimal_bundle()
    b["inter_quarter_context"] = {
        "ticker": "TEST", "sector": "Technology", "industry": "Software",
        "prev_8k_ts": "2025-10-01T16:00:00-04:00",
        "context_cutoff_ts": "2026-01-01T16:00:00-05:00",
        "context_cutoff_reason": "8K_filing",
        "prev_day": "2025-10-01", "cutoff_day": "2026-01-01",
        "pit_cutoff": None, "source_mode": "live",
        "schema_version": "v1", "assembled_at": "2026-01-01T21:00:00+00:00",
        "summary": {"trading_days_ordinary": 1, "significant_move_days": 0,
                    "gap_days": 0, "total_news": 0, "total_filings": 0,
                    "total_dividends": 0, "total_splits": 0},
        "days": [
            {"date": "2025-12-15", "is_trading_day": True,
             "boundary_role": None, "price": {"close": 100.0, "daily_return": 0.5},
             "spy_return": 0.2, "sector_return": 0.3, "adj_return": 0.2,
             "is_significant": False, "is_gap_day": False,
             "events": []},
        ],
    }
    return b


def _iq_pipe_in_title() -> dict:
    # _iq_cell pipe escaping in news title
    b = _minimal_bundle()
    b["inter_quarter_context"] = {
        "ticker": "TEST", "sector": "Technology", "industry": "Software",
        "prev_8k_ts": "2025-10-01T16:00:00-04:00",
        "context_cutoff_ts": "2026-01-01T16:00:00-05:00",
        "context_cutoff_reason": "8K_filing",
        "prev_day": "2025-10-01", "cutoff_day": "2026-01-01",
        "pit_cutoff": None, "source_mode": "live",
        "schema_version": "v1", "assembled_at": "2026-01-01T21:00:00+00:00",
        "summary": {"trading_days_ordinary": 1, "significant_move_days": 0,
                    "gap_days": 0, "total_news": 1, "total_filings": 0,
                    "total_dividends": 0, "total_splits": 0},
        "days": [
            {"date": "2025-12-15", "is_trading_day": True,
             "boundary_role": None, "price": {"close": 100.0, "daily_return": 0.5},
             "spy_return": 0.2, "sector_return": 0.3, "adj_return": 0.2,
             "is_significant": False, "is_gap_day": False,
             "events": [
                 {"type": "news", "market_session": "regular",
                  "title": "Headline a|b|c with pipes",
                  "channels": ["Earnings"], "forward_returns": None},
             ]},
        ],
    }
    return b


# ── registry ─────────────────────────────────────────────────────────

DEGRADED_BUILDERS: list[tuple[str, Callable[[], dict]]] = [
    ("all_builder_errors",   _all_builder_errors),
    ("all_no_data",          _all_no_data),
    ("no_current_quarter",   _no_current_quarter),
    ("no_ex991",             _no_ex991),
    ("no_lessons",           _no_lessons),
    ("empty_quarter_label",  _empty_quarter_label),
    ("unicode_in_text",      _unicode_in_text),
    ("non_finite_numbers",   _non_finite_numbers),
    ("huge_and_tiny",        _huge_and_tiny),
    ("guidance_qual_only",   _guidance_qual_only),
    ("guidance_all_units",   _guidance_all_units),
    ("iq_no_events",         _iq_no_events),
    ("iq_pipe_in_title",     _iq_pipe_in_title),
]
