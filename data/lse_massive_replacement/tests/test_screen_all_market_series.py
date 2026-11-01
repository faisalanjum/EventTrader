from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from screen_all_market_series import catalog_candidates  # noqa: E402


def test_catalog_candidates_keeps_only_price_proxy_datasets_and_deduplicates():
    rows = [
        {"dataset": "stocks", "symbol": "AAPL", "name": "Apple"},
        {"dataset": "economics", "symbol": "GDP", "name": "GDP"},
        {"dataset": "index", "symbol": "SOX/USD", "name": "PHLX"},
        {"dataset": "index", "symbol": "SOX/USD", "name": "duplicate"},
        {"dataset": "futures", "symbol": "ES.F", "name": "S&P futures"},
        {"dataset": "etf", "symbol": "XLE", "name": "Energy"},
    ]

    result = catalog_candidates(rows)

    assert [(item["dataset"], item["symbol"]) for item in result] == [
        ("etf", "XLE"),
        ("futures", "ES.F"),
        ("index", "SOX/USD"),
    ]
