"""Small, source-neutral helpers for testing benchmark substitutes.

Returns are expressed in percentage points: ``1.0`` means a one percent move.
The module has no database or network access.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd


def _clean_series(values: pd.Series, name: str) -> pd.Series:
    cleaned = pd.to_numeric(values, errors="coerce").replace(
        [np.inf, -np.inf], np.nan
    )
    cleaned.name = name
    return cleaned


def _rounded(value: float, digits: int = 10) -> float | None:
    if not math.isfinite(value):
        return None
    rounded = round(float(value), digits)
    return 0.0 if rounded == -0.0 else rounded


def compare_returns(
    target: pd.Series,
    candidate: pd.Series,
) -> dict[str, float | int | str | None]:
    """Compare aligned target and candidate returns.

    Correlation alone can hide a leveraged or badly scaled substitute, so the
    strict screen also checks beta, absolute error, tracking error, and whether
    both series moved in the same direction.
    """

    paired = pd.concat(
        [_clean_series(target, "target"), _clean_series(candidate, "candidate")],
        axis=1,
        join="inner",
    ).dropna()

    observations = len(paired)
    if observations == 0:
        return {
            "observations": 0,
            "correlation": None,
            "beta": None,
            "mean_error_pp": None,
            "mean_absolute_error_pp": None,
            "root_mean_square_error_pp": None,
            "annualized_tracking_error_pp": None,
            "direction_agreement": None,
            "volatility_ratio": None,
            "daily_screen": "reject",
        }

    target_values = paired["target"]
    candidate_values = paired["candidate"]
    difference = candidate_values - target_values

    target_variance = (
        target_values.var(ddof=1) if observations > 1 else math.nan
    )
    target_volatility = (
        target_values.std(ddof=1) if observations > 1 else math.nan
    )
    candidate_volatility = (
        candidate_values.std(ddof=1) if observations > 1 else math.nan
    )
    correlation = (
        target_values.corr(candidate_values)
        if (
            observations > 1
            and target_volatility > 0
            and candidate_volatility > 0
        )
        else math.nan
    )
    beta = (
        candidate_values.cov(target_values) / target_variance
        if observations > 1 and target_variance > 0
        else math.nan
    )
    volatility_ratio = (
        candidate_volatility / target_volatility
        if observations > 1 and target_volatility > 0
        else math.nan
    )
    tracking_error = (
        difference.std(ddof=1) * math.sqrt(252) if observations > 1 else math.nan
    )
    direction_agreement = (
        np.sign(target_values.to_numpy()) == np.sign(candidate_values.to_numpy())
    ).mean()

    metrics: dict[str, float | int | str | None] = {
        "observations": observations,
        "correlation": _rounded(correlation),
        "beta": _rounded(beta),
        "mean_error_pp": _rounded(difference.mean()),
        "mean_absolute_error_pp": _rounded(difference.abs().mean()),
        "root_mean_square_error_pp": _rounded(
            math.sqrt(float((difference**2).mean()))
        ),
        "annualized_tracking_error_pp": _rounded(tracking_error),
        "direction_agreement": _rounded(direction_agreement),
        "volatility_ratio": _rounded(volatility_ratio),
    }

    correlation_value = metrics["correlation"]
    beta_value = metrics["beta"]
    mae_value = metrics["mean_absolute_error_pp"]
    tracking_value = metrics["annualized_tracking_error_pp"]
    direction_value = metrics["direction_agreement"]

    strong = (
        isinstance(correlation_value, float)
        and correlation_value >= 0.98
        and isinstance(beta_value, float)
        and 0.90 <= beta_value <= 1.10
        and isinstance(mae_value, float)
        and mae_value <= 0.25
        and isinstance(tracking_value, float)
        and tracking_value <= 5.0
        and isinstance(direction_value, float)
        and direction_value >= 0.85
    )
    context_only = (
        isinstance(correlation_value, float)
        and correlation_value >= 0.90
        and isinstance(beta_value, float)
        and 0.75 <= beta_value <= 1.25
        and isinstance(mae_value, float)
        and mae_value <= 0.60
        and isinstance(tracking_value, float)
        and tracking_value <= 12.0
        and isinstance(direction_value, float)
        and direction_value >= 0.75
    )
    metrics["daily_screen"] = (
        "strong" if strong else "context_only" if context_only else "reject"
    )
    return metrics


def portfolio_returns(
    constituent_returns: pd.DataFrame,
    weights: Mapping[str, float],
    *,
    minimum_weight_coverage: float = 0.90,
) -> pd.DataFrame:
    """Build daily weighted returns while exposing missing-weight risk."""

    if not 0 < minimum_weight_coverage <= 1:
        raise ValueError("minimum_weight_coverage must be above 0 and at most 1")

    selected_weights = pd.Series(
        {
            symbol: float(weight)
            for symbol, weight in weights.items()
            if symbol in constituent_returns.columns and float(weight) > 0
        },
        dtype=float,
    )
    if selected_weights.empty:
        raise ValueError("no positive weights match the return columns")
    selected_weights /= selected_weights.sum()

    selected_returns = constituent_returns[selected_weights.index].apply(
        pd.to_numeric, errors="coerce"
    )
    available = selected_returns.notna()
    weight_coverage = available.mul(selected_weights, axis=1).sum(axis=1)
    weighted_sum = selected_returns.fillna(0).mul(selected_weights, axis=1).sum(axis=1)
    result_return = (weighted_sum / weight_coverage).where(
        weight_coverage >= minimum_weight_coverage
    )

    return pd.DataFrame(
        {
            "return": result_return,
            "weight_coverage": weight_coverage,
            "constituents": available.sum(axis=1),
        },
        index=constituent_returns.index,
    )


def latest_snapshot(
    snapshots: Sequence[Mapping[str, Any]],
    session: Any,
    *,
    date_key: str,
) -> Mapping[str, Any] | None:
    """Return the newest snapshot dated on or before a trading session."""

    session_date = pd.Timestamp(session).date()
    eligible: list[tuple[Any, Mapping[str, Any]]] = []
    for snapshot in snapshots:
        value = snapshot.get(date_key)
        if value in (None, ""):
            continue
        snapshot_date = pd.Timestamp(value).date()
        if snapshot_date <= session_date:
            eligible.append((snapshot_date, snapshot))
    if not eligible:
        return None
    return max(eligible, key=lambda item: item[0])[1]


def time_varying_portfolio_returns(
    constituent_returns: pd.DataFrame,
    snapshots: Sequence[Mapping[str, Any]],
    *,
    date_key: str,
    minimum_weight_coverage: float = 0.90,
    drift_weights: bool = False,
    snapshot_effective_after_date: bool = False,
) -> pd.DataFrame:
    """Build returns with the holdings snapshot active on each session.

    A symbol named in a snapshot still counts toward required coverage when
    its return column or value is missing.
    """

    if not 0 < minimum_weight_coverage <= 1:
        raise ValueError("minimum_weight_coverage must be above 0 and at most 1")

    output: list[dict[str, Any]] = []
    active_snapshot_identity: tuple[str, Any] | None = None
    drifted_weights: dict[str, float] = {}
    for session, row in constituent_returns.iterrows():
        lookup_session = pd.Timestamp(session)
        if snapshot_effective_after_date:
            lookup_session -= pd.Timedelta(days=1)
        snapshot = latest_snapshot(
            snapshots,
            lookup_session,
            date_key=date_key,
        )
        if snapshot is None:
            output.append(
                {
                    "return": math.nan,
                    "weight_coverage": 0.0,
                    "constituents": 0,
                    "snapshot_date": None,
                }
            )
            continue

        snapshot_weights = {
            str(symbol): float(weight)
            for symbol, weight in snapshot.get("weights", {}).items()
            if float(weight) > 0
        }
        snapshot_identity = (
            str(snapshot.get(date_key, ""))[:10],
            snapshot.get("accession"),
        )
        if drift_weights:
            if snapshot_identity != active_snapshot_identity:
                drifted_weights = snapshot_weights.copy()
                active_snapshot_identity = snapshot_identity
            weights = drifted_weights
        else:
            weights = snapshot_weights
        total_weight = sum(weights.values())
        if total_weight <= 0:
            output.append(
                {
                    "return": math.nan,
                    "weight_coverage": 0.0,
                    "constituents": 0,
                    "snapshot_date": str(snapshot[date_key])[:10],
                }
            )
            continue

        available_weight = 0.0
        weighted_return = 0.0
        available_constituents = 0
        for symbol, weight in weights.items():
            if symbol not in constituent_returns.columns:
                continue
            value = pd.to_numeric(row[symbol], errors="coerce")
            if pd.isna(value) or not math.isfinite(float(value)):
                continue
            available_weight += weight
            weighted_return += float(value) * weight
            available_constituents += 1

        coverage = available_weight / total_weight
        result_return = (
            weighted_return / available_weight
            if (
                available_weight > 0
                and coverage >= minimum_weight_coverage
            )
            else math.nan
        )
        output.append(
            {
                "return": result_return,
                "weight_coverage": coverage,
                "constituents": available_constituents,
                "snapshot_date": str(snapshot[date_key])[:10],
            }
        )
        if drift_weights:
            next_weights: dict[str, float] = {}
            for symbol, weight in weights.items():
                value = (
                    pd.to_numeric(row[symbol], errors="coerce")
                    if symbol in constituent_returns.columns
                    else math.nan
                )
                if pd.isna(value) or not math.isfinite(float(value)):
                    next_weights[symbol] = weight
                    continue
                next_weights[symbol] = max(
                    0.0,
                    weight * (1.0 + float(value) / 100.0),
                )
            drifted_weights = next_weights

    return pd.DataFrame(output, index=constituent_returns.index)
