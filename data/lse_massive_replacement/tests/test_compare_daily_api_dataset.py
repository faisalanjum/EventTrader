from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from compare_daily_apis import lse_daily_cache_path  # noqa: E402


def test_lse_daily_cache_path_separates_stocks_from_etfs(tmp_path):
    stock = lse_daily_cache_path(
        tmp_path,
        "ABC",
        "stocks",
        "2026-01-01",
        "2026-01-31",
    )
    etf = lse_daily_cache_path(
        tmp_path,
        "ABC",
        "etf",
        "2026-01-01",
        "2026-01-31",
    )

    assert stock != etf
    assert "stocks" in stock.name
    assert "etf" in etf.name
