from __future__ import annotations

import math
import sys
import warnings
from pathlib import Path

import pandas as pd
import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from benchmark_proxy_core import (  # noqa: E402
    compare_returns,
    latest_snapshot,
    portfolio_returns,
    time_varying_portfolio_returns,
)


def test_identical_returns_pass_the_strict_daily_screen():
    target = pd.Series(
        [1.0, -0.5, 0.25, 1.5, -1.0],
        index=pd.date_range("2026-01-02", periods=5, freq="B"),
    )

    result = compare_returns(target, target.copy())

    assert result["observations"] == 5
    assert result["correlation"] == 1.0
    assert result["beta"] == 1.0
    assert result["mean_absolute_error_pp"] == 0.0
    assert result["direction_agreement"] == 1.0
    assert result["daily_screen"] == "strong"


def test_perfectly_correlated_leveraged_series_is_not_a_drop_in_substitute():
    target = pd.Series(
        [1.0, -0.5, 0.25, 1.5, -1.0],
        index=pd.date_range("2026-01-02", periods=5, freq="B"),
    )

    result = compare_returns(target, target * 2)

    assert result["correlation"] == 1.0
    assert result["beta"] == 2.0
    assert result["daily_screen"] == "reject"


def test_one_observation_rejects_without_numpy_runtime_warnings():
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        result = compare_returns(
            pd.Series([1.0]),
            pd.Series([1.0]),
        )

    assert result["observations"] == 1
    assert result["correlation"] is None
    assert result["daily_screen"] == "reject"


def test_portfolio_renormalizes_available_weight_but_enforces_coverage():
    dates = pd.date_range("2026-01-02", periods=3, freq="B")
    returns = pd.DataFrame(
        {
            "A": [1.0, 2.0, 3.0],
            "B": [1.0, math.nan, 5.0],
            "C": [1.0, math.nan, 7.0],
        },
        index=dates,
    )

    result = portfolio_returns(
        returns,
        {"A": 0.5, "B": 0.3, "C": 0.2},
        minimum_weight_coverage=0.75,
    )

    assert result.loc[dates[0], "return"] == 1.0
    assert math.isnan(result.loc[dates[1], "return"])
    assert result.loc[dates[1], "weight_coverage"] == 0.5
    assert result.loc[dates[2], "return"] == 4.4


def test_latest_snapshot_uses_most_recent_report_not_after_session():
    snapshots = [
        {"report_date": "2022-12-31", "weights": {"A": 1.0}},
        {"report_date": "2023-03-31", "weights": {"B": 1.0}},
        {"report_date": "2023-06-30", "weights": {"C": 1.0}},
    ]

    selected = latest_snapshot(
        snapshots,
        "2023-04-03",
        date_key="report_date",
    )

    assert selected == snapshots[1]


def test_time_varying_portfolio_changes_weights_at_quarter_boundary():
    returns = pd.DataFrame(
        {
            "A": [1.0, 1.0],
            "B": [3.0, 3.0],
        },
        index=["2023-03-30", "2023-04-03"],
    )
    snapshots = [
        {"report_date": "2022-12-31", "weights": {"A": 1.0}},
        {"report_date": "2023-03-31", "weights": {"B": 1.0}},
    ]

    result = time_varying_portfolio_returns(
        returns,
        snapshots,
        date_key="report_date",
    )

    assert result["return"].to_dict() == {
        "2023-03-30": 1.0,
        "2023-04-03": 3.0,
    }
    assert result["snapshot_date"].to_dict() == {
        "2023-03-30": "2022-12-31",
        "2023-04-03": "2023-03-31",
    }


def test_time_varying_portfolio_counts_missing_symbol_weight():
    returns = pd.DataFrame(
        {"A": [2.0]},
        index=["2023-01-03"],
    )
    snapshots = [
        {
            "report_date": "2022-12-31",
            "weights": {"A": 0.85, "MISSING": 0.15},
        }
    ]

    result = time_varying_portfolio_returns(
        returns,
        snapshots,
        date_key="report_date",
        minimum_weight_coverage=0.90,
    )

    assert math.isnan(result.loc["2023-01-03", "return"])
    assert result.loc["2023-01-03", "weight_coverage"] == 0.85


def test_time_varying_portfolio_can_drift_weights_with_prices():
    returns = pd.DataFrame(
        {
            "A": [10.0, 10.0],
            "B": [0.0, 0.0],
        },
        index=["2023-01-03", "2023-01-04"],
    )
    snapshots = [
        {
            "report_date": "2022-12-31",
            "weights": {"A": 0.5, "B": 0.5},
        }
    ]

    result = time_varying_portfolio_returns(
        returns,
        snapshots,
        date_key="report_date",
        drift_weights=True,
    )

    assert result.loc["2023-01-03", "return"] == 5.0
    assert result.loc["2023-01-04", "return"] == pytest.approx(110 / 21)


def test_snapshot_can_take_effect_after_its_report_date_return():
    returns = pd.DataFrame(
        {
            "A": [1.0, 1.0],
            "B": [3.0, 3.0],
        },
        index=["2023-03-31", "2023-04-03"],
    )
    snapshots = [
        {"report_date": "2022-12-31", "weights": {"A": 1.0}},
        {"report_date": "2023-03-31", "weights": {"B": 1.0}},
    ]

    result = time_varying_portfolio_returns(
        returns,
        snapshots,
        date_key="report_date",
        snapshot_effective_after_date=True,
    )

    assert result["return"].to_dict() == {
        "2023-03-31": 1.0,
        "2023-04-03": 3.0,
    }
