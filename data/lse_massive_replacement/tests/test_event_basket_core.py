from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from event_basket_core import (  # noqa: E402
    basket_return,
    return_window,
)


def _row(timestamp: str, close: float) -> dict[str, object]:
    return {"ts": timestamp, "close": close}


def test_basket_return_uses_latest_minute_at_each_endpoint():
    rows = {
        "A": [
            _row("2026-07-17 14:29:00", 100),
            _row("2026-07-17 14:30:00", 101),
            _row("2026-07-17 15:29:00", 103),
            _row("2026-07-17 15:30:00", 999),
        ],
        "B": [
            _row("2026-07-17 14:29:00", 50),
            _row("2026-07-17 15:29:00", 49),
        ],
    }

    result = basket_return(
        rows,
        {"A": 60, "B": 40},
        "2026-07-17T14:29:30Z",
        "2026-07-17T15:29:30Z",
        minimum_weight_coverage=0.8,
    )

    assert result["weight_coverage"] == 1
    assert result["constituents"] == 2
    assert round(result["return"], 6) == 1.0


def test_basket_return_keeps_missing_weight_in_coverage_denominator():
    result = basket_return(
        {
            "A": [
                _row("2026-07-17 14:00:00", 100),
                _row("2026-07-17 15:00:00", 101),
            ]
        },
        {"A": 70, "__UNMAPPED__::B": 30},
        "2026-07-17T14:00:30Z",
        "2026-07-17T15:00:30Z",
        minimum_weight_coverage=0.8,
    )

    assert result["weight_coverage"] == 0.7
    assert result["return"] is None


def test_return_window_uses_saved_schedule_and_closed_market_boundary():
    hourly_case = {
        "created": "2023-06-05T23:30:06-04:00",
        "market_session": "market_closed",
        "returns_schedule": (
            '{"hourly":"2023-06-06T05:00:00-04:00",'
            '"session":"2023-06-06T09:35:00-04:00"}'
        ),
    }

    assert return_window(hourly_case, "hourly") == (
        "2023-06-06T04:00:00-04:00",
        "2023-06-06T05:00:00-04:00",
    )
    assert return_window(hourly_case, "session") == (
        "2023-06-05T20:00:00-04:00",
        "2023-06-06T09:35:00-04:00",
    )
