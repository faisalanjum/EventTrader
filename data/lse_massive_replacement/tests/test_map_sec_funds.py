from __future__ import annotations

import json
import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from map_sec_funds import map_target_funds, parse_sec_fund_rows  # noqa: E402


def test_parse_sec_fund_rows_uses_declared_field_order():
    payload = json.dumps(
        {
            "fields": ["classId", "symbol", "cik", "seriesId"],
            "data": [
                ["C0001", "xlk", 1064641, "S0001"],
                ["C0002", "SOXX", 1100663, "S0002"],
            ],
        }
    ).encode()

    assert parse_sec_fund_rows(payload) == [
        {
            "cik": "1064641",
            "series_id": "S0001",
            "class_id": "C0001",
            "symbol": "XLK",
        },
        {
            "cik": "1100663",
            "series_id": "S0002",
            "class_id": "C0002",
            "symbol": "SOXX",
        },
    ]


def test_map_target_funds_reports_unique_missing_and_ambiguous_symbols():
    rows = [
        {
            "cik": "1",
            "series_id": "S1",
            "class_id": "C1",
            "symbol": "XLK",
        },
        {
            "cik": "2",
            "series_id": "S2",
            "class_id": "C2",
            "symbol": "SOXX",
        },
        {
            "cik": "3",
            "series_id": "S3",
            "class_id": "C3",
            "symbol": "SOXX",
        },
    ]

    result = map_target_funds(rows, ["soxx", "XLK", "HACK"])

    assert result["matched"] == {
        "XLK": {
            "cik": "1",
            "series_id": "S1",
            "class_id": "C1",
            "symbol": "XLK",
        }
    }
    assert result["missing"] == ["HACK"]
    assert result["ambiguous"] == {
        "SOXX": [
            {
                "cik": "2",
                "series_id": "S2",
                "class_id": "C2",
                "symbol": "SOXX",
            },
            {
                "cik": "3",
                "series_id": "S3",
                "class_id": "C3",
                "symbol": "SOXX",
            },
        ]
    }
