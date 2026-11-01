from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from run_proxy_pilot import (  # noqa: E402
    close_returns,
    evaluate_candidate,
    historical_coverage_thresholds,
    prepare_historical_snapshots,
    regular_close_returns,
)


def test_evaluate_candidate_supports_labeled_short_overlap_rule():
    dates = pd.date_range("2026-04-28", periods=45, freq="B").strftime(
        "%Y-%m-%d"
    )
    target = pd.Series(
        [float((index % 7) - 3) for index in range(45)],
        index=dates,
    )

    result = evaluate_candidate(
        target,
        target.copy(),
        minimum_observations=40,
        require_stability=False,
        periods={
            "recent_live_overlap": ("2026-04-28", "2026-07-17"),
        },
    )

    assert result["numerical_verdict"] == "strong"
    assert result["periods"]["recent_live_overlap"]["observations"] == 45
    assert result["verdict_rules"]["minimum_observations"] == 40
    assert result["verdict_rules"]["stability_required"] is False


def test_close_returns_uses_only_consecutive_required_sessions():
    rows = [
        {"ts": "2026-01-02 00:00:00", "close": 100},
        {"ts": "2026-01-03 00:00:00", "close": 999},
        {"ts": "2026-01-05 00:00:00", "close": 110},
        {"ts": "2026-01-07 00:00:00", "close": 121},
    ]
    sessions = ["2026-01-02", "2026-01-05", "2026-01-06", "2026-01-07"]

    result = close_returns(rows, sessions)

    assert result.to_dict() == {"2026-01-05": 10.0}


def test_close_returns_can_preserve_unrounded_component_moves():
    rows = [
        {"ts": "2026-01-02 00:00:00", "close": 3},
        {"ts": "2026-01-05 00:00:00", "close": 4},
    ]

    result = close_returns(
        rows,
        ["2026-01-02", "2026-01-05"],
        round_digits=None,
    )

    assert result.iloc[0] == pytest.approx(100 / 3)


def test_regular_close_returns_uses_hour_ending_at_market_close():
    rows = [
        {"ts": "2026-01-02 19:00:00", "close": 99},
        {"ts": "2026-01-02 20:00:00", "close": 100},
        {"ts": "2026-01-02 21:00:00", "close": 150},
        {"ts": "2026-01-05 20:00:00", "close": 110},
        {"ts": "2026-01-05 21:00:00", "close": 200},
    ]
    market_closes = {
        "2026-01-02": "2026-01-02T21:00:00+00:00",
        "2026-01-05": "2026-01-05T21:00:00+00:00",
    }

    result = regular_close_returns(
        rows,
        ["2026-01-02", "2026-01-05"],
        market_closes,
    )

    assert result.to_dict() == {"2026-01-05": 10.0}


def test_regular_close_returns_corrects_unadjusted_reverse_split():
    rows = [
        {"ts": "2026-06-23 19:00:00", "close": 100},
        {"ts": "2026-06-24 19:00:00", "close": 300},
    ]
    market_closes = {
        "2026-06-23": "2026-06-23T20:00:00+00:00",
        "2026-06-24": "2026-06-24T20:00:00+00:00",
    }

    result = regular_close_returns(
        rows,
        ["2026-06-23", "2026-06-24"],
        market_closes,
        split_rows=[
            {
                "effective_date": "2026-06-24",
                "split_from": 3,
                "split_to": 1,
            }
        ],
    )

    assert result.to_dict() == {"2026-06-24": 0.0}


def test_regular_close_returns_does_not_double_adjust_split_history():
    rows = [
        {"ts": "2024-06-07 19:00:00", "close": 100},
        {"ts": "2024-06-10 19:00:00", "close": 101},
    ]
    market_closes = {
        "2024-06-07": "2024-06-07T20:00:00+00:00",
        "2024-06-10": "2024-06-10T20:00:00+00:00",
    }

    result = regular_close_returns(
        rows,
        ["2024-06-07", "2024-06-10"],
        market_closes,
        split_rows=[
            {
                "effective_date": "2024-06-10",
                "split_from": 1,
                "split_to": 10,
            }
        ],
    )

    assert result.to_dict() == {"2024-06-10": 1.0}


def test_regular_close_returns_ignores_duplicate_split_rows():
    rows = [
        {"ts": "2026-06-23 19:00:00", "close": 100},
        {"ts": "2026-06-24 19:00:00", "close": 300},
    ]
    market_closes = {
        "2026-06-23": "2026-06-23T20:00:00+00:00",
        "2026-06-24": "2026-06-24T20:00:00+00:00",
    }
    split = {
        "effective_date": "2026-06-24",
        "split_from": 3,
        "split_to": 1,
    }

    result = regular_close_returns(
        rows,
        ["2026-06-23", "2026-06-24"],
        market_closes,
        split_rows=[split, dict(split)],
    )

    assert result.to_dict() == {"2026-06-24": 0.0}


def test_prepare_historical_snapshots_keeps_unmapped_weight_visible():
    snapshots = [
        {
            "report_date": "2025-12-31",
            "filing_date": "2026-02-27",
            "holdings": [
                {
                    "cusip": "111111111",
                    "name": "Mapped by CUSIP",
                    "weight_percent": 60,
                },
                {
                    "cusip": "N/A",
                    "name": "Mapped by Name",
                    "weight_percent": 30,
                },
                {
                    "cusip": "333333333",
                    "name": "Not Mapped",
                    "weight_percent": 10,
                },
            ],
        }
    ]
    ticker_map = {
        "cusip_to_symbol": {"111111111": "AAA"},
        "name_to_symbol": {"Mapped by Name": "BBB"},
    }

    result = prepare_historical_snapshots(
        snapshots,
        ticker_map,
        size=3,
    )

    prepared = result[0]
    assert prepared["weights"]["AAA"] == 60
    assert prepared["weights"]["BBB"] == 30
    unmapped_keys = [
        symbol
        for symbol in prepared["weights"]
        if symbol.startswith("__UNMAPPED__")
    ]
    assert len(unmapped_keys) == 1
    assert prepared["weights"][unmapped_keys[0]] == 10
    assert prepared["mapped_weight_fraction"] == pytest.approx(0.9)
    assert prepared["captured_fund_weight_percent"] == 100


def test_historical_coverage_sensitivity_only_expands_largest_basket():
    config = {
        "minimum_basket_weight_coverage": 0.9,
        "historical_minimum_weight_coverages": [0.75, 0.8, 0.85, 0.9],
        "historical_basket_sizes": [3, 5, 10, 20],
    }

    assert historical_coverage_thresholds(config, 10) == [0.9]
    assert historical_coverage_thresholds(config, 20) == [
        0.75,
        0.8,
        0.85,
        0.9,
    ]
