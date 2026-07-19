from __future__ import annotations

from datetime import datetime, timezone

from session_reconstruction import aggregate_rows, rows_in_window


def _row(ts: str, open_: float, high: float, low: float, close: float, volume: float):
    return {
        "symbol": "TEST",
        "ts": ts,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }


def test_regular_session_window_includes_open_and_excludes_close_boundary():
    rows = [
        _row("2024-12-12 20:00:00.000000", 50, 51, 49, 50, 5),
        _row("2024-12-12 19:59:00.000000", 40, 44, 39, 43, 4),
        _row("2024-12-12 13:29:00.000000", 10, 11, 9, 10, 1),
        _row("2024-12-12 13:30:00.000000", 20, 22, 19, 21, 2),
    ]
    start = datetime(2024, 12, 12, 13, 30, tzinfo=timezone.utc)
    end = datetime(2024, 12, 12, 20, 0, tzinfo=timezone.utc)

    selected = rows_in_window(rows, start, end)

    assert [row["ts"] for row in selected] == [
        "2024-12-12 13:30:00.000000",
        "2024-12-12 19:59:00.000000",
    ]


def test_aggregate_rows_uses_time_order_and_standard_ohlcv_rules():
    rows = [
        _row("2024-12-12 19:59:00.000000", 40, 44, 39, 43, 4),
        _row("2024-12-12 13:30:00.000000", 20, 22, 19, 21, 2),
        _row("2024-12-12 15:00:00.000000", 30, 45, 18, 35, 3),
    ]

    result = aggregate_rows(rows)

    assert result == {
        "row_count": 3,
        "first_ts": "2024-12-12 13:30:00.000000",
        "last_ts": "2024-12-12 19:59:00.000000",
        "open": 20.0,
        "high": 45.0,
        "low": 18.0,
        "close": 43.0,
        "volume": 9.0,
    }


def test_aggregate_rows_returns_none_for_empty_input():
    assert aggregate_rows([]) is None
