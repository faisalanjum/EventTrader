from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from fetch_lse_market_catalog import select_relevant_catalog  # noqa: E402


def test_select_relevant_catalog_keeps_stocks_and_market_series_only():
    rows = [
        {"dataset": "economics", "symbol": "GDP", "name": "GDP"},
        {"dataset": "stocks", "symbol": "AAPL", "name": "Apple"},
        {"dataset": "index", "symbol": "SPX500/USD", "name": "S&P 500"},
        {"dataset": "etf", "symbol": "XLE", "name": "Energy ETF"},
    ]

    result = select_relevant_catalog(rows)

    assert [(row["dataset"], row["symbol"]) for row in result] == [
        ("etf", "XLE"),
        ("index", "SPX500/USD"),
        ("stocks", "AAPL"),
    ]
