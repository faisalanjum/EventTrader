from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from macro_comparison_core import lse_minutes_for_et_day


def _row(ts: str) -> dict:
    return {
        "symbol": "SPY",
        "ts": ts,
        "open": 1,
        "high": 1,
        "low": 1,
        "close": 1,
        "volume": 1,
    }


def test_lse_minutes_for_et_day_removes_prior_et_evening_from_utc_day():
    rows = [
        _row("2026-07-17 00:00:00.000000"),  # 8 PM ET on July 16
        _row("2026-07-17 07:59:00.000000"),  # 3:59 AM ET
        _row("2026-07-17 08:00:00.000000"),  # 4:00 AM ET
        _row("2026-07-17 19:59:00.000000"),  # 3:59 PM ET
        _row("2026-07-17 23:59:00.000000"),  # 7:59 PM ET
    ]

    selected = lse_minutes_for_et_day(rows, "2026-07-17")

    assert [row["ts"] for row in selected] == [
        "2026-07-17 08:00:00.000000",
        "2026-07-17 19:59:00.000000",
        "2026-07-17 23:59:00.000000",
    ]
