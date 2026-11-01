#!/usr/bin/env python3
"""Measure exact regular-close availability in an isolated LSE manifest."""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import exchange_calendars as xcals
import pandas as pd

from run_proxy_pilot import read_gzip_rows


def session_close_presence(
    rows: list[dict[str, Any]],
    sessions: list[str],
    market_closes: dict[str, str],
) -> set[str]:
    timestamps = set()
    for row in rows:
        try:
            timestamp = pd.Timestamp(str(row["ts"]))
        except (KeyError, TypeError, ValueError):
            continue
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize("UTC")
        else:
            timestamp = timestamp.tz_convert("UTC")
        timestamps.add(timestamp)

    present = set()
    for session in sessions:
        close = market_closes.get(session)
        if not close:
            continue
        expected = pd.Timestamp(close).tz_convert("UTC") - pd.Timedelta(
            hours=1
        )
        if expected in timestamps:
            present.add(session)
    return present


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=root / "config" / "recent_live_overlap.json",
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    config = json.loads(args.config.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))

    calendar = xcals.get_calendar("XNYS")
    calendar_sessions = calendar.sessions_in_range(
        pd.Timestamp(config["period"]["start"]),
        pd.Timestamp(config["period"]["end"]),
    )
    sessions = [session.date().isoformat() for session in calendar_sessions]
    market_closes = {
        session.date().isoformat(): calendar.session_close(session).isoformat()
        for session in calendar_sessions
    }

    chunks_by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for chunk in manifest["chunks"]:
        chunks_by_symbol[str(chunk["symbol"])].append(chunk)

    session_counts = {session: 0 for session in sessions}
    symbol_rows = []
    for symbol in manifest["symbols"]:
        rows = []
        for chunk in chunks_by_symbol.get(symbol, []):
            path = root / str(chunk["cache_file"])
            if path.exists():
                rows.extend(read_gzip_rows(path))
        present = session_close_presence(
            rows,
            sessions,
            market_closes,
        )
        for session in present:
            session_counts[session] += 1
        return_pairs = sum(
            previous in present and current in present
            for previous, current in zip(sessions, sessions[1:])
        )
        symbol_rows.append(
            {
                "symbol": symbol,
                "hourly_rows": len(rows),
                "close_sessions": len(present),
                "consecutive_return_dates": int(return_pairs),
                "missing_close_dates": sorted(set(sessions) - present),
            }
        )

    symbol_count = len(symbol_rows)
    session_rows = [
        {
            "date": session,
            "symbols_with_close": session_counts[session],
            "fraction": round(
                session_counts[session] / symbol_count
                if symbol_count
                else math.nan,
                6,
            ),
        }
        for session in sessions
    ]
    report = {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "safety": (
            "Local isolated LSE caches only. No network, database, Redis, "
            "or production write."
        ),
        "method": (
            "A close is present only when the exact one-hour candle begins "
            "one hour before the official XNYS close."
        ),
        "period": config["period"],
        "summary": {
            "symbols": symbol_count,
            "sessions": len(sessions),
            "symbols_with_zero_close_sessions": sum(
                item["close_sessions"] == 0 for item in symbol_rows
            ),
            "median_close_sessions": (
                statistics.median(
                    item["close_sessions"] for item in symbol_rows
                )
                if symbol_rows
                else None
            ),
            "median_consecutive_return_dates": (
                statistics.median(
                    item["consecutive_return_dates"]
                    for item in symbol_rows
                )
                if symbol_rows
                else None
            ),
            "feed_wide_outage_dates_below_10_percent": [
                item["date"]
                for item in session_rows
                if item["fraction"] < 0.1
            ],
        },
        "sessions": session_rows,
        "symbols": symbol_rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.output)
    print(json.dumps(report["summary"], sort_keys=True))
    print(f"saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
