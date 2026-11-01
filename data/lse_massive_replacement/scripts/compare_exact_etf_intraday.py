#!/usr/bin/env python3
"""Compare LSE and Massive minute behavior for exact ETF symbols."""

from __future__ import annotations

import argparse
import json
import math
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import quote

import exchange_calendars as xcals
import pandas as pd
import requests

from benchmark_proxy_core import compare_returns
from compare_daily_apis import (
    MASSIVE_BASE,
    USER_AGENT,
    get_json_with_retries,
    read_json_gzip,
    write_json_gzip,
)
from fetch_lse_proxy_pilot import fetch_rows, read_api_key, safe_name


def fixed_window_returns(
    closes: pd.Series,
    *,
    minutes: int,
) -> pd.Series:
    """Return close-to-close moves only when the exact end minute exists."""

    numeric = pd.to_numeric(closes, errors="coerce").dropna()
    values = numeric.to_dict()
    result: dict[pd.Timestamp, float] = {}
    delta = pd.Timedelta(minutes=minutes)
    for timestamp, start_value in numeric.items():
        end_value = values.get(timestamp + delta)
        if end_value is None or float(start_value) == 0:
            continue
        result[timestamp] = (
            (float(end_value) - float(start_value))
            / float(start_value)
            * 100
        )
    return pd.Series(result, dtype=float)


def to_close_returns(
    closes: pd.Series,
    *,
    required_close_bar: pd.Timestamp | None = None,
) -> pd.Series:
    numeric = pd.to_numeric(closes, errors="coerce").dropna()
    if numeric.empty:
        return pd.Series(dtype=float)
    if (
        required_close_bar is not None
        and numeric.index[-1] != required_close_bar
    ):
        return pd.Series(dtype=float)
    final_value = float(numeric.iloc[-1])
    result = (
        (final_value - numeric.iloc[:-1])
        / numeric.iloc[:-1]
        * 100
    )
    return result.astype(float)


def minute_closes(
    rows: list[dict[str, Any]],
    *,
    source: str,
) -> pd.Series:
    values: dict[pd.Timestamp, float] = {}
    for row in rows:
        try:
            if source == "massive":
                timestamp = pd.Timestamp(int(row["t"]), unit="ms", tz="UTC")
                close = float(row["c"])
            else:
                timestamp = pd.Timestamp(str(row["ts"]))
                timestamp = (
                    timestamp.tz_localize("UTC")
                    if timestamp.tzinfo is None
                    else timestamp.tz_convert("UTC")
                )
                close = float(row["close"])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(close):
            values[timestamp] = close
    return pd.Series(values, dtype=float).sort_index()


def regular_session(
    closes: pd.Series,
    session_open: pd.Timestamp,
    session_close: pd.Timestamp,
) -> pd.Series:
    if closes.empty:
        return closes
    return closes.loc[
        (closes.index >= session_open)
        & (closes.index < session_close)
    ]


def price_difference(reference: pd.Series, candidate: pd.Series) -> dict[str, Any]:
    paired = pd.concat(
        [reference.rename("reference"), candidate.rename("candidate")],
        axis=1,
        join="inner",
    ).dropna()
    absolute = (paired["candidate"] - paired["reference"]).abs()
    basis_points = absolute / paired["reference"].abs() * 10_000
    return {
        "observations": len(paired),
        "mean_absolute_price": (
            round(float(absolute.mean()), 10) if not absolute.empty else None
        ),
        "mean_absolute_basis_points": (
            round(float(basis_points.mean()), 10)
            if not basis_points.empty
            else None
        ),
        "within_001_price": int((absolute <= 0.0100000001).sum()),
        "within_005_price": int((absolute <= 0.0500000001).sum()),
        "maximum_absolute_price": (
            round(float(absolute.max()), 10) if not absolute.empty else None
        ),
    }


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--case",
        action="append",
        required=True,
        help="SYMBOL:YYYY-MM-DD; repeat for more cases",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=root / "raw" / "exact_etf_intraday",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--private-key-source", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    cases: list[tuple[str, str]] = []
    for raw in args.case:
        symbol, separator, day = raw.partition(":")
        if not separator:
            raise SystemExit("--case must be SYMBOL:YYYY-MM-DD")
        date.fromisoformat(day)
        cases.append((symbol.strip().upper(), day))

    lse_key = read_api_key(
        os.environ.get("LSE_API_KEY", ""),
        args.private_key_source,
    )
    massive_key = os.environ.get("POLYGON_API_KEY", "")
    if not massive_key:
        raise SystemExit("POLYGON_API_KEY is required")
    calendar = xcals.get_calendar("XNYS")

    report: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "safety": (
            "Read-only LSE and Massive GET requests. Credentials were not "
            "printed or saved. Production code and databases were untouched."
        ),
        "limit": (
            "This compares one-minute candles. Production event returns use "
            "Massive one-second candles, so this tests intraday feed agreement "
            "but cannot prove exact one-second equivalence."
        ),
        "cases": {},
        "pooled": {},
    }
    pooled_reference: dict[str, list[pd.Series]] = {
        "5_minute": [],
        "60_minute": [],
        "to_close": [],
    }
    pooled_candidate: dict[str, list[pd.Series]] = {
        "5_minute": [],
        "60_minute": [],
        "to_close": [],
    }

    with requests.Session() as session:
        for symbol, day in cases:
            day_ts = pd.Timestamp(day)
            if not calendar.is_session(day_ts):
                raise SystemExit(f"{day} is not an XNYS session")
            schedule = calendar.schedule.loc[day_ts]
            session_open = pd.Timestamp(schedule["open"]).tz_convert("UTC")
            session_close = pd.Timestamp(schedule["close"]).tz_convert("UTC")
            end_exclusive = (date.fromisoformat(day) + timedelta(days=1)).isoformat()

            lse_cache = args.cache_dir / "lse" / (
                f"etf__{safe_name(symbol)}__{day}__1m.json.gz"
            )
            if lse_cache.exists():
                lse_rows = read_json_gzip(lse_cache)
                lse_status = "cached"
            else:
                lse_rows, _ = fetch_rows(
                    session,
                    lse_key,
                    {
                        "symbol": symbol,
                        "dataset": "etf",
                        "kind": "exact_etf",
                    },
                    day,
                    day,
                    timeframe="1m",
                    limit=5000,
                )
                write_json_gzip(lse_cache, lse_rows)
                lse_status = "downloaded"

            massive_cache = args.cache_dir / "massive" / (
                f"{safe_name(symbol)}__{day}__1m.json.gz"
            )
            if massive_cache.exists():
                massive_rows = read_json_gzip(massive_cache)
                massive_status = "cached"
            else:
                value = get_json_with_retries(
                    session,
                    (
                        f"{MASSIVE_BASE}/v2/aggs/ticker/"
                        f"{quote(symbol, safe='')}/range/1/minute/{day}/{day}"
                    ),
                    params={
                        "adjusted": "true",
                        "sort": "asc",
                        "limit": 50000,
                    },
                    headers={
                        "Authorization": f"Bearer {massive_key}",
                        "Accept": "application/json",
                        "User-Agent": USER_AGENT,
                    },
                )
                if not isinstance(value, dict):
                    raise RuntimeError("Massive minute response was not an object")
                massive_rows = value.get("results") or []
                if not isinstance(massive_rows, list):
                    raise RuntimeError("Massive minute results were not a list")
                write_json_gzip(massive_cache, massive_rows)
                massive_status = "downloaded"

            lse_close = regular_session(
                minute_closes(lse_rows, source="lse"),
                session_open,
                session_close,
            )
            massive_close = regular_session(
                minute_closes(massive_rows, source="massive"),
                session_open,
                session_close,
            )
            horizons = {
                "5_minute": (
                    fixed_window_returns(massive_close, minutes=5),
                    fixed_window_returns(lse_close, minutes=5),
                ),
                "60_minute": (
                    fixed_window_returns(massive_close, minutes=60),
                    fixed_window_returns(lse_close, minutes=60),
                ),
                "to_close": (
                    to_close_returns(
                        massive_close,
                        required_close_bar=(
                            session_close - pd.Timedelta(minutes=1)
                        ),
                    ),
                    to_close_returns(
                        lse_close,
                        required_close_bar=(
                            session_close - pd.Timedelta(minutes=1)
                        ),
                    ),
                ),
            }
            case_key = f"{symbol}:{day}"
            report["cases"][case_key] = {
                "session_utc": {
                    "open": session_open.isoformat(),
                    "close": session_close.isoformat(),
                },
                "lse": {
                    "status": lse_status,
                    "all_rows": len(lse_rows),
                    "regular_minutes": len(lse_close),
                    "first_regular_timestamp": (
                        lse_close.index[0].isoformat()
                        if not lse_close.empty
                        else None
                    ),
                    "last_regular_timestamp": (
                        lse_close.index[-1].isoformat()
                        if not lse_close.empty
                        else None
                    ),
                },
                "massive": {
                    "status": massive_status,
                    "all_rows": len(massive_rows),
                    "regular_minutes": len(massive_close),
                },
                "minute_close_price": price_difference(
                    massive_close,
                    lse_close,
                ),
                "return_windows": {
                    name: compare_returns(reference, candidate)
                    for name, (reference, candidate) in horizons.items()
                },
            }
            for name, (reference, candidate) in horizons.items():
                prefix = f"{case_key}|"
                reference = reference.copy()
                candidate = candidate.copy()
                reference.index = [prefix + str(value) for value in reference.index]
                candidate.index = [prefix + str(value) for value in candidate.index]
                pooled_reference[name].append(reference)
                pooled_candidate[name].append(candidate)
            print(
                f"{case_key}: LSE regular minutes={len(lse_close)}, "
                f"Massive={len(massive_close)}"
            )

    for name in pooled_reference:
        reference = pd.concat(pooled_reference[name])
        candidate = pd.concat(pooled_candidate[name])
        report["pooled"][name] = compare_returns(reference, candidate)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.output)
    print(f"saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
