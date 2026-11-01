#!/usr/bin/env python3
"""Fetch isolated Massive daily benchmark controls for a recent period."""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from compare_core import bars_by_date, daily_returns, normalize_massive_bar
from compare_daily_apis import fetch_massive_daily, session_dates


def pause_between_symbols(
    index: int,
    total: int,
    seconds: float,
) -> None:
    if index + 1 < total and seconds > 0:
        time.sleep(seconds)


def target_rows(
    symbol: str,
    rows: list[dict[str, Any]],
    sessions: list[str],
) -> list[dict[str, Any]]:
    bars = bars_by_date(
        [normalize_massive_bar(symbol, row) for row in rows]
    )
    returns = daily_returns(bars, session_dates=sessions)
    result = []
    for day in sessions:
        bar = bars.get(day)
        if bar is None:
            continue
        item = bar.json()
        item["daily_return"] = returns.get(day)
        result.append(item)
    return result


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=root / "raw" / "recent_massive_targets",
    )
    parser.add_argument("--request-pause-seconds", type=float, default=6.5)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    key = os.environ.get("POLYGON_API_KEY", "")
    if not key:
        raise SystemExit("POLYGON_API_KEY is required")
    symbols = sorted(
        {
            symbol.strip().upper()
            for symbol in args.symbols.split(",")
            if symbol.strip()
        }
    )
    sessions = session_dates(args.start, args.end)
    rows: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for index, symbol in enumerate(symbols):
        raw = fetch_massive_daily(
            symbol,
            args.start,
            args.end,
            key,
            args.cache_dir,
        )
        converted = target_rows(symbol, raw, sessions)
        rows.extend(converted)
        counts[symbol] = len(converted)
        print(f"{symbol}: {len(converted)} daily bars")
        pause_between_symbols(
            index,
            len(symbols),
            args.request_pause_seconds,
        )

    report = {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "source": "Massive adjusted daily aggregate REST endpoint",
        "safety": (
            "Read-only Massive GET requests. The credential was not printed "
            "or saved. Production code and databases were untouched."
        ),
        "requested": {
            "symbols": symbols,
            "start": args.start,
            "end": args.end,
        },
        "summary": {
            "rows": len(rows),
            "rows_by_symbol": counts,
        },
        "rows": rows,
    }
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
