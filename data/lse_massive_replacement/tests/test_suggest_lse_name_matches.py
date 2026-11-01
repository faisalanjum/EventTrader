from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from suggest_lse_name_matches import rank_name_candidates  # noqa: E402


def test_rank_name_candidates_finds_truncated_company_name():
    catalog = [
        {
            "dataset": "stocks",
            "symbol": "CHKP",
            "name": "Check Point Software Technologies Ltd.",
        },
        {
            "dataset": "stocks",
            "symbol": "CP",
            "name": "Canadian Pacific Kansas City Limited",
        },
        {
            "dataset": "etf",
            "symbol": "HACK",
            "name": "Cybersecurity ETF",
        },
    ]

    result = rank_name_candidates(
        "Check Point Software Technolog",
        catalog,
        limit=2,
    )

    assert result[0]["symbol"] == "CHKP"
    assert result[0]["score"] > 0.9
    assert all(item["symbol"] != "HACK" for item in result)
