"""Pure comparison helpers for the isolated market-data audit.

This module has no network, database, or repository write behavior.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from zoneinfo import ZoneInfo


EASTERN = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class Bar:
    symbol: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: float | None = None
    transactions: int | None = None
    timestamp: str | int | None = None

    def json(self) -> dict[str, Any]:
        return asdict(self)


def _finite_float(value: Any, field: str) -> float:
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{field} is not finite")
    return converted


def _optional_finite_float(value: Any) -> float | None:
    if value is None:
        return None
    converted = float(value)
    return converted if math.isfinite(converted) else None


def normalize_massive_bar(symbol: str, row: Mapping[str, Any]) -> Bar:
    """Normalize one Massive aggregate row.

    Massive timestamps are epoch milliseconds. Its daily bars are keyed by the
    exchange-local date, so conversion is made in America/New_York.
    """

    timestamp_ms = int(row["t"])
    eastern_date = (
        datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        .astimezone(EASTERN)
        .date()
        .isoformat()
    )
    transactions = row.get("n")
    return Bar(
        symbol=symbol,
        date=eastern_date,
        open=_finite_float(row["o"], "open"),
        high=_finite_float(row["h"], "high"),
        low=_finite_float(row["l"], "low"),
        close=_finite_float(row["c"], "close"),
        volume=_finite_float(row["v"], "volume"),
        vwap=_optional_finite_float(row.get("vw")),
        transactions=int(transactions) if transactions is not None else None,
        timestamp=timestamp_ms,
    )


def normalize_lse_bar(row: Mapping[str, Any]) -> Bar:
    """Normalize one raw LSE candle row.

    The live endpoint currently labels time as ``ts`` and returns a UTC-like
    SQL timestamp. Daily rows use the date at the beginning of that string.
    """

    timestamp = row.get("ts", row.get("timestamp"))
    if not isinstance(timestamp, str) or len(timestamp) < 10:
        raise ValueError("LSE bar has no usable ts/timestamp")
    return Bar(
        symbol=str(row["symbol"]),
        date=timestamp[:10],
        open=_finite_float(row["open"], "open"),
        high=_finite_float(row["high"], "high"),
        low=_finite_float(row["low"], "low"),
        close=_finite_float(row["close"], "close"),
        volume=_finite_float(row.get("volume", 0), "volume"),
        timestamp=timestamp,
    )


def normalize_neo4j_bar(row: Mapping[str, Any]) -> Bar:
    """Normalize one Massive-derived ``HAS_PRICE`` relationship."""

    transactions = row.get("transactions")
    return Bar(
        symbol=str(row["symbol"]),
        date=str(row["date"])[:10],
        open=_finite_float(row["open"], "open"),
        high=_finite_float(row["high"], "high"),
        low=_finite_float(row["low"], "low"),
        close=_finite_float(row["close"], "close"),
        volume=_finite_float(row["volume"], "volume"),
        vwap=_optional_finite_float(row.get("vwap")),
        transactions=int(transactions) if transactions is not None else None,
        timestamp=row.get("timestamp"),
    )


def bars_by_date(bars: list[Bar]) -> dict[str, Bar]:
    result: dict[str, Bar] = {}
    for bar in bars:
        if bar.date in result:
            raise ValueError(f"duplicate daily bar for {bar.symbol} on {bar.date}")
        result[bar.date] = bar
    return result


def daily_returns(
    bars: Mapping[str, Bar],
    session_dates: list[str] | None = None,
) -> dict[str, float]:
    """Use the production formula on consecutive exchange sessions.

    When ``session_dates`` is supplied, a missing session is not silently
    bridged. That matches the grouped-daily production path, which requires the
    current and immediately prior trading dates to both contain the symbol.
    """

    result: dict[str, float] = {}
    dates = session_dates if session_dates is not None else sorted(bars)
    for previous_date, current_date in zip(dates, dates[1:]):
        if previous_date not in bars or current_date not in bars:
            continue
        previous = bars[previous_date].close
        current = bars[current_date].close
        if (
            not math.isfinite(previous)
            or not math.isfinite(current)
            or previous == 0
        ):
            continue
        result[current_date] = round((current - previous) / previous * 100, 2)
    return result


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = math.ceil((len(ordered) - 1) * percentile)
    return ordered[index]


def _difference_stats(
    pairs: list[tuple[float, float]],
    *,
    price_field: bool,
) -> dict[str, Any]:
    absolute = [abs(candidate - reference) for reference, candidate in pairs]
    relative_bp = [
        abs(candidate - reference) / abs(reference) * 10_000
        for reference, candidate in pairs
        if reference != 0
    ]
    result: dict[str, Any] = {
        "compared": len(pairs),
        "exact": sum(candidate == reference for reference, candidate in pairs),
        "mean_absolute": statistics.fmean(absolute) if absolute else None,
        "median_absolute": statistics.median(absolute) if absolute else None,
        "p95_absolute": _percentile(absolute, 0.95),
        "max_absolute": max(absolute) if absolute else None,
        "mean_absolute_bp": statistics.fmean(relative_bp) if relative_bp else None,
        "p95_absolute_bp": _percentile(relative_bp, 0.95),
        "max_absolute_bp": max(relative_bp) if relative_bp else None,
        "within_1bp": sum(value <= 1 for value in relative_bp),
        "within_10bp": sum(value <= 10 for value in relative_bp),
        "within_50bp": sum(value <= 50 for value in relative_bp),
    }
    if price_field:
        result.update(
            {
                "within_1_cent": sum(value <= 0.0100000001 for value in absolute),
                "within_5_cents": sum(value <= 0.0500000001 for value in absolute),
                "within_10_cents": sum(value <= 0.1000000001 for value in absolute),
            }
        )
    return result


def compare_daily_series(
    massive: Mapping[str, Bar],
    lse: Mapping[str, Bar],
    session_dates: list[str] | None = None,
) -> dict[str, Any]:
    massive_dates = set(massive)
    lse_dates = set(lse)
    overlap = sorted(massive_dates & lse_dates)

    ohlc: dict[str, Any] = {}
    for field in ("open", "high", "low", "close"):
        pairs = [
            (getattr(massive[date], field), getattr(lse[date], field))
            for date in overlap
        ]
        ohlc[field] = _difference_stats(pairs, price_field=True)

    volume_pairs = [
        (massive[date].volume, lse[date].volume)
        for date in overlap
    ]

    massive_returns = daily_returns(massive, session_dates=session_dates)
    lse_returns = daily_returns(lse, session_dates=session_dates)
    return_dates = sorted(set(massive_returns) & set(lse_returns))
    return_differences = [
        abs(lse_returns[date] - massive_returns[date])
        for date in return_dates
    ]

    return {
        "massive_dates": len(massive_dates),
        "lse_dates": len(lse_dates),
        "overlap_dates": len(overlap),
        "massive_only_dates": len(massive_dates - lse_dates),
        "lse_only_dates": len(lse_dates - massive_dates),
        "first_overlap_date": overlap[0] if overlap else None,
        "last_overlap_date": overlap[-1] if overlap else None,
        "ohlc": ohlc,
        "volume": _difference_stats(volume_pairs, price_field=False),
        "daily_returns": {
            "massive_dates": len(massive_returns),
            "lse_dates": len(lse_returns),
            "overlap_dates": len(return_dates),
            "same_rounded_2dp": sum(
                massive_returns[date] == lse_returns[date]
                for date in return_dates
            ),
            "within_1bp": sum(value <= 0.01 for value in return_differences),
            "within_5bp": sum(value <= 0.05 for value in return_differences),
            "mean_absolute_percentage_points": (
                statistics.fmean(return_differences)
                if return_differences
                else None
            ),
            "p95_absolute_percentage_points": _percentile(
                return_differences, 0.95
            ),
            "max_absolute_percentage_points": (
                max(return_differences) if return_differences else None
            ),
        },
    }


def compare_daily_panels(
    reference: Mapping[str, Mapping[str, Bar]],
    candidate: Mapping[str, Mapping[str, Bar]],
    session_dates: list[str] | None = None,
) -> dict[str, Any]:
    """Compare multiple symbols without joining one symbol's returns to another."""

    symbols = sorted(set(reference) & set(candidate))
    field_pairs: dict[str, list[tuple[float, float]]] = {
        field: [] for field in ("open", "high", "low", "close")
    }
    volume_pairs: list[tuple[float, float]] = []
    return_differences: list[float] = []
    exact_returns = 0
    overlap_symbol_dates = 0
    reference_only_symbol_dates = 0
    candidate_only_symbol_dates = 0
    per_symbol: dict[str, Any] = {}

    for symbol in symbols:
        reference_rows = reference[symbol]
        candidate_rows = candidate[symbol]
        reference_dates = set(reference_rows)
        candidate_dates = set(candidate_rows)
        overlap = sorted(reference_dates & candidate_dates)
        overlap_symbol_dates += len(overlap)
        reference_only_symbol_dates += len(reference_dates - candidate_dates)
        candidate_only_symbol_dates += len(candidate_dates - reference_dates)

        for day in overlap:
            reference_bar = reference_rows[day]
            candidate_bar = candidate_rows[day]
            for field in field_pairs:
                field_pairs[field].append(
                    (
                        getattr(reference_bar, field),
                        getattr(candidate_bar, field),
                    )
                )
            volume_pairs.append(
                (reference_bar.volume, candidate_bar.volume)
            )

        reference_returns = daily_returns(
            reference_rows, session_dates=session_dates
        )
        candidate_returns = daily_returns(
            candidate_rows, session_dates=session_dates
        )
        return_dates = sorted(
            set(reference_returns) & set(candidate_returns)
        )
        for day in return_dates:
            reference_value = reference_returns[day]
            candidate_value = candidate_returns[day]
            exact_returns += reference_value == candidate_value
            return_differences.append(
                abs(candidate_value - reference_value)
            )

        per_symbol[symbol] = compare_daily_series(
            reference_rows,
            candidate_rows,
            session_dates=session_dates,
        )

    return {
        "coverage": {
            "reference_symbols": len(reference),
            "candidate_symbols": len(candidate),
            "symbols": len(symbols),
            "overlap_symbol_dates": overlap_symbol_dates,
            "reference_only_symbol_dates": reference_only_symbol_dates,
            "candidate_only_symbol_dates": candidate_only_symbol_dates,
        },
        "ohlc": {
            field: _difference_stats(pairs, price_field=True)
            for field, pairs in field_pairs.items()
        },
        "volume": _difference_stats(volume_pairs, price_field=False),
        "daily_returns": {
            "compared": len(return_differences),
            "same_rounded_2dp": exact_returns,
            "within_1bp": sum(
                value <= 0.01 for value in return_differences
            ),
            "within_5bp": sum(
                value <= 0.05 for value in return_differences
            ),
            "mean_absolute_percentage_points": (
                statistics.fmean(return_differences)
                if return_differences
                else None
            ),
            "p95_absolute_percentage_points": _percentile(
                return_differences, 0.95
            ),
            "max_absolute_percentage_points": (
                max(return_differences) if return_differences else None
            ),
        },
        "per_symbol": per_symbol,
    }
