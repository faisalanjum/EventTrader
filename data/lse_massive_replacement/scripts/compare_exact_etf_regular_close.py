#!/usr/bin/env python3
"""Compare LSE exact-ETF 4 p.m. closes with Massive daily returns."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import exchange_calendars as xcals
import pandas as pd
import requests

from benchmark_proxy_core import compare_returns
from compare_core import bars_by_date, daily_returns, normalize_massive_bar
from compare_daily_apis import fetch_massive_daily
from fetch_lse_proxy_pilot import (
    fetch_rows,
    read_api_key,
    read_cache,
    safe_name,
    write_cache,
)
from run_proxy_pilot import regular_close_returns


def massive_returns_from_rows(
    symbol: str,
    rows: list[dict[str, Any]],
    sessions: list[str],
) -> pd.Series:
    bars = bars_by_date(
        [normalize_massive_bar(symbol, row) for row in rows]
    )
    return pd.Series(
        daily_returns(bars, session_dates=sessions),
        dtype=float,
    )


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", default="XLE,SOXX")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=root / "raw" / "exact_etf_regular_close",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--private-key-source", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    symbols = sorted(
        {
            value.strip().upper()
            for value in args.symbols.split(",")
            if value.strip()
        }
    )
    lse_key = read_api_key(
        os.environ.get("LSE_API_KEY", ""),
        args.private_key_source,
    )
    massive_key = os.environ.get("POLYGON_API_KEY", "")
    if not massive_key:
        raise SystemExit("POLYGON_API_KEY is required")

    calendar = xcals.get_calendar("XNYS")
    exchange_sessions = calendar.sessions_in_range(
        pd.Timestamp(args.start),
        pd.Timestamp(args.end),
    )
    sessions = [value.date().isoformat() for value in exchange_sessions]
    market_closes = {
        value.date().isoformat(): calendar.session_close(value).isoformat()
        for value in exchange_sessions
    }

    report: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "safety": (
            "Read-only LSE and Massive GET requests. Credentials were not "
            "printed or saved. Production code and databases were untouched."
        ),
        "period": {
            "start": args.start,
            "end_inclusive": args.end,
            "exchange_sessions": len(sessions),
        },
        "method": (
            "LSE one-hour ETF bar ending at the official XNYS close versus "
            "Massive adjusted daily close-to-close return. Missing exchange "
            "sessions are never bridged."
        ),
        "symbols": {},
    }

    with requests.Session() as session:
        for symbol in symbols:
            lse_cache = args.cache_dir / (
                f"etf__{safe_name(symbol)}__{args.start}__"
                f"{args.end}__1h.json.gz"
            )
            if lse_cache.exists():
                lse_rows = read_cache(lse_cache)
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
                    args.start,
                    args.end,
                    timeframe="1h",
                    limit=5000,
                )
                write_cache(lse_cache, lse_rows)
                lse_status = "downloaded"

            massive_rows = fetch_massive_daily(
                symbol,
                args.start,
                args.end,
                massive_key,
                args.cache_dir,
            )
            lse_returns = regular_close_returns(
                lse_rows,
                sessions,
                market_closes,
            )
            massive_returns = massive_returns_from_rows(
                symbol,
                massive_rows,
                sessions,
            )
            paired = pd.concat(
                [
                    massive_returns.rename("massive"),
                    lse_returns.rename("lse"),
                ],
                axis=1,
                join="inner",
            ).dropna()
            difference = (paired["lse"] - paired["massive"]).abs()
            report["symbols"][symbol] = {
                "lse": {
                    "status": lse_status,
                    "hourly_rows": len(lse_rows),
                    "first_timestamp": (
                        lse_rows[0].get("ts") if lse_rows else None
                    ),
                    "last_timestamp": (
                        lse_rows[-1].get("ts") if lse_rows else None
                    ),
                },
                "massive_daily_rows": len(massive_rows),
                "comparison": compare_returns(
                    massive_returns,
                    lse_returns,
                ),
                "difference_counts": {
                    "same_rounded_2dp": int((difference == 0).sum()),
                    "within_001_percentage_points": int(
                        (difference <= 0.0100000001).sum()
                    ),
                    "within_005_percentage_points": int(
                        (difference <= 0.0500000001).sum()
                    ),
                    "maximum_absolute_difference_pp": (
                        round(float(difference.max()), 10)
                        if not difference.empty
                        else None
                    ),
                },
                "first_overlap": (
                    str(paired.index[0]) if not paired.empty else None
                ),
                "last_overlap": (
                    str(paired.index[-1]) if not paired.empty else None
                ),
            }
            metrics = report["symbols"][symbol]["comparison"]
            print(
                f"{symbol}: n={metrics['observations']}, "
                f"corr={metrics['correlation']}, "
                f"mae={metrics['mean_absolute_error_pp']}"
            )

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
