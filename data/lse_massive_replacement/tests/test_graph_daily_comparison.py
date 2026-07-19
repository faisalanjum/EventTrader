from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from compare_core import Bar
from compare_graph_daily_cached import compare_atr_panels


def test_compare_atr_panels_uses_each_symbols_own_rolling_window():
    start = date(2026, 1, 1)
    reference = {}
    for symbol, base in (("AAA", 100.0), ("BBB", 200.0)):
        rows = {}
        for offset in range(15):
            day = (start + timedelta(days=offset)).isoformat()
            close = base + offset
            rows[day] = Bar(
                symbol,
                day,
                close - 1,
                close + 1,
                close - 2,
                close,
                1000,
            )
        reference[symbol] = rows
    candidate = {
        symbol: dict(rows) for symbol, rows in reference.items()
    }

    result = compare_atr_panels(reference, candidate, days=14)

    assert result["summary"]["symbols"] == 2
    assert result["summary"]["rolling_windows"] == 2
    assert result["summary"]["same_rounded_2dp"] == 2
    assert result["summary"]["max_absolute_price_units"] == 0
