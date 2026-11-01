from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from fetch_massive_benchmark_targets import (  # noqa: E402
    pause_between_symbols,
    target_rows,
)


def test_target_rows_calculates_consecutive_session_returns():
    rows = [
        {"t": 1767330000000, "c": 100, "o": 99, "h": 101, "l": 98, "v": 10},
        {"t": 1767589200000, "c": 110, "o": 100, "h": 111, "l": 99, "v": 20},
        {"t": 1767675600000, "c": 121, "o": 110, "h": 122, "l": 109, "v": 30},
    ]

    result = target_rows(
        "TEST",
        rows,
        ["2026-01-02", "2026-01-05", "2026-01-06"],
    )

    assert [row["date"] for row in result] == [
        "2026-01-02",
        "2026-01-05",
        "2026-01-06",
    ]
    assert result[0]["daily_return"] is None
    assert result[1]["daily_return"] == 10.0
    assert result[2]["daily_return"] == 10.0


def test_pause_between_symbols_waits_except_after_last(monkeypatch):
    waits = []
    monkeypatch.setattr(
        "fetch_massive_benchmark_targets.time.sleep",
        waits.append,
    )

    pause_between_symbols(0, 2, 6.5)
    pause_between_symbols(1, 2, 6.5)

    assert waits == [6.5]
