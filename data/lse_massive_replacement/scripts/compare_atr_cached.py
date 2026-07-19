#!/usr/bin/env python3
"""Compare the production ATR formula on cached Massive and LSE daily bars."""

from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import exchange_calendars as xcals
import pandas as pd


def read_rows(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, list):
        raise ValueError(f"Expected list in {path}")
    return value


def massive_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "date": datetime.fromtimestamp(
                int(row["t"]) / 1000, tz=timezone.utc
            ).date().isoformat(),
            "open": float(row["o"]),
            "high": float(row["h"]),
            "low": float(row["l"]),
            "close": float(row["c"]),
        }
        for row in rows
    ]


def lse_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    calendar = xcals.get_calendar("XNYS")
    result = []
    for row in rows:
        day = str(row["ts"])[:10]
        if not calendar.is_session(pd.Timestamp(day)):
            continue
        result.append(
            {
                "date": day,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
            }
        )
    return result


def atr_from_rows(rows: list[dict[str, Any]], days: int) -> float:
    """Exact formula used by production scripts/atr_compare_sources.py."""

    if len(rows) < days + 1:
        raise ValueError(f"Need at least {days + 1} bars")
    true_ranges = []
    previous_close = float(rows[0]["close"])
    for row in rows[1:]:
        high = float(row["high"])
        low = float(row["low"])
        close = float(row["close"])
        true_ranges.append(
            max(
                high - low,
                abs(high - previous_close),
                abs(low - previous_close),
            )
        )
        previous_close = close
    window = true_ranges[-days:]
    return sum(window) / len(window)


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = math.ceil((len(ordered) - 1) * fraction)
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--massive-dir", type=Path, required=True)
    parser.add_argument("--lse-dir", type=Path, required=True)
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    massive_files = {
        path.name: path for path in args.massive_dir.glob("*.json.gz")
    }
    lse_files = {path.name: path for path in args.lse_dir.glob("*.json.gz")}
    common_files = sorted(massive_files.keys() & lse_files.keys())

    comparisons: list[dict[str, Any]] = []
    symbols: dict[str, Any] = {}
    for name in common_files:
        symbol = name.split("_", 1)[0]
        massive = massive_rows(read_rows(massive_files[name]))
        lse = lse_rows(read_rows(lse_files[name]))
        massive_by_date = {row["date"]: row for row in massive}
        lse_by_date = {row["date"]: row for row in lse}
        dates = sorted(massive_by_date.keys() & lse_by_date.keys())
        symbol_comparisons = []
        for end_index in range(args.days, len(dates)):
            window_dates = dates[
                end_index - args.days : end_index + 1
            ]
            massive_window = [massive_by_date[day] for day in window_dates]
            lse_window = [lse_by_date[day] for day in window_dates]
            massive_atr = atr_from_rows(massive_window, args.days)
            lse_atr = atr_from_rows(lse_window, args.days)
            absolute = abs(lse_atr - massive_atr)
            record = {
                "symbol": symbol,
                "end_date": window_dates[-1],
                "massive_atr": massive_atr,
                "lse_atr": lse_atr,
                "absolute_difference": absolute,
                "relative_difference_bp": (
                    absolute / massive_atr * 10_000
                    if massive_atr
                    else None
                ),
                "same_rounded_2dp": (
                    round(massive_atr, 2) == round(lse_atr, 2)
                ),
            }
            comparisons.append(record)
            symbol_comparisons.append(record)
        symbols[symbol] = {
            "common_dates": len(dates),
            "first_common_date": dates[0] if dates else None,
            "last_common_date": dates[-1] if dates else None,
            "rolling_windows": len(symbol_comparisons),
            "final_window": (
                symbol_comparisons[-1] if symbol_comparisons else None
            ),
        }

    absolute = [row["absolute_difference"] for row in comparisons]
    relative = [
        row["relative_difference_bp"]
        for row in comparisons
        if row["relative_difference_bp"] is not None
    ]
    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "atr_days": args.days,
        "method": (
            "For every rolling common-date window, calculate true range as "
            "max(high-low, |high-prior close|, |low-prior close|), then take "
            "the arithmetic mean of the final N true ranges."
        ),
        "summary": {
            "symbols": len(symbols),
            "rolling_windows": len(comparisons),
            "same_rounded_2dp": sum(
                row["same_rounded_2dp"] for row in comparisons
            ),
            "mean_absolute_price_units": (
                statistics.fmean(absolute) if absolute else None
            ),
            "p95_absolute_price_units": percentile(absolute, 0.95),
            "max_absolute_price_units": max(absolute) if absolute else None,
            "mean_relative_bp": (
                statistics.fmean(relative) if relative else None
            ),
            "p95_relative_bp": percentile(relative, 0.95),
            "max_relative_bp": max(relative) if relative else None,
        },
        "symbols": symbols,
        "safety": "Cached files only; no network, database, or production writes.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.output)
    print(f"saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
