from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from fetch_lse_event_basket_minutes import build_fetch_plan  # noqa: E402


def test_build_fetch_plan_uses_only_holdings_known_by_event_date():
    cases = {
        "AAPL:2023-06-05": [
            {
                "created": "2023-06-05T10:00:00-04:00",
                "market_session": "in_market",
                "returns_schedule": (
                    '{"hourly":"2023-06-05T11:00:00-04:00",'
                    '"session":"2023-06-05T16:00:00-04:00"}'
                ),
                "sector_etf": "XLK",
                "industry_etf": "IYW",
            }
        ]
    }
    holdings = {
        "funds": {
            "XLK": {
                "snapshots": [
                    {
                        "report_date": "2023-03-31",
                        "holdings": [
                            {
                                "cusip": "1",
                                "name": "Alpha",
                                "weight_percent": 60,
                            }
                        ],
                    },
                    {
                        "report_date": "2023-06-30",
                        "holdings": [
                            {
                                "cusip": "9",
                                "name": "Future",
                                "weight_percent": 100,
                            }
                        ],
                    },
                ]
            },
            "IYW": {
                "snapshots": [
                    {
                        "report_date": "2023-03-31",
                        "holdings": [
                            {
                                "cusip": "2",
                                "name": "Beta",
                                "weight_percent": 100,
                            }
                        ],
                    }
                ]
            },
        }
    }
    ticker_map = {
        "cusip_to_symbol": {"1": "A", "2": "B", "9": "FUTURE"},
        "name_to_symbol": {},
    }

    plan = build_fetch_plan(
        cases,
        holdings,
        ticker_map,
        top_size=20,
    )

    group = plan["groups"]["AAPL:2023-06-05"]
    assert group["start"] == "2023-06-01"
    assert group["end"] == "2023-06-05"
    assert set(group["funds"]) == {"XLK", "IYW"}
    assert group["funds"]["XLK"]["weights"] == {"A": 60.0}
    assert group["symbols"] == ["A", "B"]
    assert [item["symbol"] for item in plan["requests"]] == ["A", "B"]


def test_build_fetch_plan_records_fund_without_earlier_snapshot():
    cases = {
        "sample": [
            {
                "created": "2023-01-25T10:00:00-05:00",
                "market_session": "in_market",
                "returns_schedule": (
                    '{"hourly":"2023-01-25T11:00:00-05:00",'
                    '"session":"2023-01-25T16:00:00-05:00"}'
                ),
                "sector_etf": "XLY",
                "industry_etf": "CARZ",
            }
        ]
    }
    holdings = {
        "funds": {
            "XLY": {
                "snapshots": [
                    {"report_date": "2022-12-31", "holdings": []}
                ]
            },
            "CARZ": {
                "snapshots": [
                    {"report_date": "2023-03-31", "holdings": []}
                ]
            },
        }
    }

    plan = build_fetch_plan(
        cases,
        holdings,
        {"cusip_to_symbol": {}, "name_to_symbol": {}},
        top_size=20,
    )

    missing = plan["groups"]["sample"]["funds"]["CARZ"]
    assert missing["weights"] == {}
    assert missing["unavailable_reason"] == (
        "no SEC holdings snapshot on or before 2023-01-25"
    )
