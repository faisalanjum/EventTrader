from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from fetch_lse_hourly_constituents import (  # noqa: E402
    selected_constituent_symbols,
    year_chunks,
)


def test_year_chunks_cover_period_without_overlap_or_gap():
    assert year_chunks("2023-01-03", "2026-04-27") == [
        ("2023-01-03", "2023-12-31"),
        ("2024-01-01", "2024-12-31"),
        ("2025-01-01", "2025-12-31"),
        ("2026-01-01", "2026-04-27"),
    ]


def test_selected_constituent_symbols_limits_holdings_to_requested_funds():
    holdings = {
        "funds": {
            "AAA": {"holdings": [{"symbol": "A"}, {"symbol": "B"}]},
            "BBB": {"holdings": [{"symbol": "C"}]},
        }
    }
    ticker_map = {
        "cusip_to_symbol": {"1": "D"},
        "name_to_symbol": {"Other": "E"},
    }

    assert selected_constituent_symbols(
        holdings,
        ticker_map,
        {"AAA"},
    ) == ["A", "B", "D", "E"]
