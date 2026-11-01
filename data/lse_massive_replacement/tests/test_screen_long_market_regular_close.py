from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from screen_long_market_regular_close import (  # noqa: E402
    long_history_candidates,
)


def test_long_history_candidates_uses_actual_daily_row_count():
    fetches = [
        {"dataset": "index", "symbol": "A", "daily_rows": 600},
        {"dataset": "futures", "symbol": "B", "daily_rows": 499},
        {"dataset": "index", "symbol": "A", "daily_rows": 600},
    ]

    assert long_history_candidates(fetches, minimum_rows=500) == [
        ("index", "A")
    ]
