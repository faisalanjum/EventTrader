"""Source-neutral helpers for event-window holdings baskets."""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from typing import Any, Mapping, Sequence

import pandas as pd


MASSIVE_MAX_FALLBACK = timedelta(seconds=614_100)


def _utc_timestamp(value: object) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def latest_close(
    rows: Sequence[Mapping[str, Any]],
    at: object,
    *,
    maximum_age: timedelta = MASSIVE_MAX_FALLBACK,
) -> float | None:
    target = _utc_timestamp(at)
    best_timestamp: pd.Timestamp | None = None
    best_close: float | None = None
    for row in rows:
        raw_timestamp = row.get("ts", row.get("timestamp"))
        raw_close = row.get("close", row.get("c"))
        if raw_timestamp in (None, "") or raw_close is None:
            continue
        try:
            timestamp = _utc_timestamp(raw_timestamp)
            close = float(raw_close)
        except (TypeError, ValueError):
            continue
        if (
            timestamp <= target
            and math.isfinite(close)
            and (best_timestamp is None or timestamp > best_timestamp)
        ):
            best_timestamp = timestamp
            best_close = close
    if (
        best_timestamp is None
        or target - best_timestamp > pd.Timedelta(maximum_age)
    ):
        return None
    return best_close


def basket_return(
    rows_by_symbol: Mapping[str, Sequence[Mapping[str, Any]]],
    weights: Mapping[str, float],
    start: object,
    end: object,
    *,
    minimum_weight_coverage: float = 0.8,
) -> dict[str, float | int | None]:
    if not 0 < minimum_weight_coverage <= 1:
        raise ValueError("minimum_weight_coverage must be above 0 and at most 1")

    positive_weights = {
        str(symbol): float(weight)
        for symbol, weight in weights.items()
        if float(weight) > 0
    }
    total_weight = sum(positive_weights.values())
    if total_weight <= 0:
        raise ValueError("weights must contain at least one positive value")

    available_weight = 0.0
    weighted_return = 0.0
    constituents = 0
    for symbol, weight in positive_weights.items():
        rows = rows_by_symbol.get(symbol, ())
        start_close = latest_close(rows, start)
        end_close = latest_close(rows, end)
        if (
            start_close is None
            or end_close is None
            or start_close <= 0
        ):
            continue
        value = (end_close - start_close) / start_close * 100
        available_weight += weight
        weighted_return += value * weight
        constituents += 1

    coverage = available_weight / total_weight
    value = (
        weighted_return / available_weight
        if available_weight > 0 and coverage >= minimum_weight_coverage
        else None
    )
    return {
        "return": value,
        "weight_coverage": coverage,
        "available_weight": available_weight,
        "selected_weight": total_weight,
        "constituents": constituents,
    }


def _iso_seconds(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def return_window(
    case: Mapping[str, Any],
    window: str,
) -> tuple[str, str]:
    schedule_value = case["returns_schedule"]
    schedule = (
        json.loads(schedule_value)
        if isinstance(schedule_value, str)
        else schedule_value
    )
    end = datetime.fromisoformat(str(schedule[window]))

    if window == "hourly":
        start = end - timedelta(hours=1)
    elif window == "session":
        created = datetime.fromisoformat(str(case["created"]))
        if case.get("market_session") == "market_closed":
            start = created.replace(hour=20, minute=0, second=0, microsecond=0)
            if created.hour < 20:
                start -= timedelta(days=1)
        else:
            start = created
    else:
        raise ValueError(f"unsupported event window: {window}")
    return _iso_seconds(start), _iso_seconds(end)
