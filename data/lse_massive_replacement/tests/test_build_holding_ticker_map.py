from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from build_holding_ticker_map import (  # noqa: E402
    build_holding_ticker_map,
    normalize_company_name,
)


def test_normalize_company_name_ignores_punctuation_and_legal_suffixes():
    assert normalize_company_name("The Example Holdings, Inc.") == "example"
    assert normalize_company_name("U.S. Bancorp") == "us bancorp"


def test_builder_uses_cusip_first_and_only_unique_exact_catalog_names():
    holdings = {
        "funds": {
            "ETF": {
                "snapshots": [
                    {
                        "holdings": [
                            {
                                "cusip": "111111111",
                                "name": "CSV Company Inc",
                                "weight_percent": 40,
                            },
                            {
                                "cusip": "222222222",
                                "name": "Unique Company, Inc.",
                                "weight_percent": 30,
                            },
                            {
                                "cusip": "333333333",
                                "name": "Two Classes Inc",
                                "weight_percent": 20,
                            },
                            {
                                "cusip": "000000000",
                                "name": "Manual PLC",
                                "weight_percent": 10,
                            },
                        ]
                    }
                ]
            },
            "OTHER": {
                "snapshots": [
                    {
                        "holdings": [
                            {
                                "cusip": "999999999",
                                "name": "Outside Company",
                                "weight_percent": 100,
                            }
                        ]
                    }
                ]
            }
        }
    }
    production_rows = [
        {"symbol": "CSV", "cusip": "111111111"},
        {"symbol": "OUT", "cusip": "999999999"},
    ]
    catalog_rows = [
        {"dataset": "stocks", "symbol": "UNIQ", "name": "Unique Company"},
        {"dataset": "stocks", "symbol": "TWO.A", "name": "Two Classes Inc."},
        {"dataset": "stocks", "symbol": "TWO.B", "name": "Two Classes Inc."},
    ]
    manual = {
        "cusip_to_symbol": {},
        "name_to_symbol": {"Manual PLC": "MAN"},
    }

    result = build_holding_ticker_map(
        holdings,
        production_rows,
        [],
        catalog_rows,
        manual,
        top_size=20,
        selected_funds={"ETF"},
    )

    assert result["cusip_to_symbol"] == {
        "111111111": "CSV",
        "222222222": "UNIQ",
    }
    assert result["name_to_symbol"] == {"Manual PLC": "MAN"}
    assert result["summary"] == {
        "selected_holding_keys": 4,
        "mapped_holding_keys": 3,
        "unresolved_holding_keys": 1,
        "mapped_selected_weight_fraction": 0.8,
    }
    assert result["unresolved"][0]["name"] == "Two Classes Inc"
