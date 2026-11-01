from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from audit_lse_split_adjustments import (  # noqa: E402
    _parser,
    fetch_complete_reference_period,
    large_return_candidates,
    splits_in_period,
)


def test_large_return_candidates_uses_absolute_threshold():
    returns = pd.Series(
        {
            "2026-06-01": 34.9,
            "2026-06-02": -35.0,
            "2026-06-03": 195.1,
        }
    )

    assert large_return_candidates("DD", returns, 35) == [
        {
            "symbol": "DD",
            "date": "2026-06-02",
            "raw_return_pp": -35.0,
        },
        {
            "symbol": "DD",
            "date": "2026-06-03",
            "raw_return_pp": 195.1,
        },
    ]


def test_splits_in_period_filters_symbol_and_date():
    rows = [
        {
            "symbol": "NVDA",
            "effective_date": "2024-06-10",
            "split_from": 1,
            "split_to": 10,
        },
        {
            "symbol": "DD",
            "effective_date": "2026-06-24",
            "split_from": 3,
            "split_to": 1,
        },
    ]

    assert splits_in_period(rows, "2026-04-28", "2026-07-17") == [
        {
            "symbol": "DD",
            "effective_date": "2026-06-24",
            "split_from": 3,
            "split_to": 1,
        }
    ]


def test_complete_reference_period_splits_capped_date_range_automatically():
    calls = []

    def fetch_range(start, end):
        calls.append((start, end))
        if (start, end) == ("2026-01-01", "2026-01-04"):
            return [{}] * 5000
        return [
            {
                "symbol": f"ROW{len(calls)}",
                "effective_date": start,
            }
        ]

    rows, completed_ranges = fetch_complete_reference_period(
        fetch_range,
        "2026-01-01",
        "2026-01-04",
    )

    assert calls == [
        ("2026-01-01", "2026-01-04"),
        ("2026-01-01", "2026-01-02"),
        ("2026-01-03", "2026-01-04"),
    ]
    assert len(rows) == 2
    assert completed_ranges == [
        {
            "start": "2026-01-01",
            "end": "2026-01-02",
            "rows": 1,
        },
        {
            "start": "2026-01-03",
            "end": "2026-01-04",
            "rows": 1,
        },
    ]


def test_split_loader_defaults_to_all_symbols_through_today(tmp_path):
    args = _parser().parse_args(
        [
            "--start",
            "2023-01-03",
            "--output",
            str(tmp_path / "splits.json"),
        ]
    )

    assert args.manifest == []
    assert args.end == date.today().isoformat()
