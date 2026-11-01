from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from compare_event_baskets import compare_cases, summarize_pairs  # noqa: E402


def _row(timestamp: str, close: float) -> dict[str, object]:
    return {"ts": timestamp, "close": close}


def test_compare_cases_checks_benchmark_and_relative_return():
    cases = {
        "sample": [
            {
                "event_id": "event-1",
                "created": "2026-07-17T10:00:00-04:00",
                "market_session": "in_market",
                "returns_schedule": (
                    '{"hourly":"2026-07-17T11:00:00-04:00",'
                    '"session":"2026-07-17T16:00:00-04:00"}'
                ),
                "sector_etf": "XLK",
                "industry_etf": "IYW",
                "hourly_sector": 1.0,
                "hourly_industry": 2.0,
                "hourly_stock": 3.0,
                "session_sector": 1.0,
                "session_industry": 2.0,
                "session_stock": 3.0,
            }
        ]
    }
    groups = {
        "sample": {
            "funds": {
                "XLK": {"weights": {"A": 100}},
                "IYW": {"weights": {"B": 100}},
            }
        }
    }
    rows = {
        ("sample", "A"): [
            _row("2026-07-17 14:00:00", 100),
            _row("2026-07-17 15:00:00", 101.1),
            _row("2026-07-17 20:00:00", 101.1),
        ],
        ("sample", "B"): [
            _row("2026-07-17 14:00:00", 100),
            _row("2026-07-17 15:00:00", 102),
            _row("2026-07-17 20:00:00", 102),
        ],
    }

    comparisons = compare_cases(cases, groups, rows)
    hourly_sector = next(
        row
        for row in comparisons
        if row["window"] == "hourly" and row["role"] == "sector"
    )

    assert hourly_sector["candidate_return"] == 1.1
    assert hourly_sector["error_pp"] == 0.1
    assert hourly_sector["stored_relative_return"] == 2.0
    assert hourly_sector["candidate_relative_return"] == 1.9
    assert hourly_sector["relative_error_pp"] == -0.1


def test_summarize_pairs_reports_availability_and_error():
    summary = summarize_pairs(
        [
            {"target_return": 1.0, "candidate_return": 1.1},
            {"target_return": -1.0, "candidate_return": -0.8},
            {"target_return": 2.0, "candidate_return": None},
        ]
    )

    assert summary["attempted"] == 3
    assert summary["observations"] == 2
    assert summary["availability"] == 2 / 3
    assert summary["mean_absolute_error_pp"] == 0.15
    assert summary["within_0_10_pp"] == 1


def test_compare_cases_keeps_unavailable_fund_as_missing_result():
    event = {
        "event_id": "event-1",
        "created": "2026-07-17T10:00:00-04:00",
        "market_session": "in_market",
        "returns_schedule": (
            '{"hourly":"2026-07-17T11:00:00-04:00",'
            '"session":"2026-07-17T16:00:00-04:00"}'
        ),
        "sector_etf": "XLY",
        "industry_etf": "CARZ",
        "hourly_sector": 1.0,
        "hourly_industry": 2.0,
        "hourly_stock": 3.0,
        "session_sector": 1.0,
        "session_industry": 2.0,
        "session_stock": 3.0,
    }
    groups = {
        "sample": {
            "funds": {
                "XLY": {"weights": {"A": 100}},
                "CARZ": {
                    "weights": {},
                    "unavailable_reason": "no earlier snapshot",
                },
            }
        }
    }
    rows = {
        ("sample", "A"): [
            _row("2026-07-17 14:00:00", 100),
            _row("2026-07-17 20:00:00", 101),
        ]
    }

    comparisons = compare_cases({"sample": [event]}, groups, rows)
    missing = next(
        row
        for row in comparisons
        if row["window"] == "hourly" and row["fund"] == "CARZ"
    )

    assert missing["candidate_return"] is None
    assert missing["weight_coverage"] == 0
    assert missing["unavailable_reason"] == "no earlier snapshot"
