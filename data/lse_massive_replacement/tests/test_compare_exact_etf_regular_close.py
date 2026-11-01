from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from compare_exact_etf_regular_close import (  # noqa: E402
    massive_returns_from_rows,
)


def _milliseconds(value: str) -> int:
    return int(
        datetime.fromisoformat(value)
        .replace(tzinfo=timezone.utc)
        .timestamp()
        * 1000
    )


def test_massive_returns_require_consecutive_exchange_sessions():
    rows = [
        {
            "t": _milliseconds("2026-01-02T05:00:00"),
            "o": 100,
            "h": 100,
            "l": 100,
            "c": 100,
            "v": 1,
        },
        {
            "t": _milliseconds("2026-01-05T05:00:00"),
            "o": 110,
            "h": 110,
            "l": 110,
            "c": 110,
            "v": 1,
        },
        {
            "t": _milliseconds("2026-01-07T05:00:00"),
            "o": 121,
            "h": 121,
            "l": 121,
            "c": 121,
            "v": 1,
        },
    ]

    result = massive_returns_from_rows(
        "XLE",
        rows,
        ["2026-01-02", "2026-01-05", "2026-01-06", "2026-01-07"],
    )

    assert result.to_dict() == {"2026-01-05": 10.0}
