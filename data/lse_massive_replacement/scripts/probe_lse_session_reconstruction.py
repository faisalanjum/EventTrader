#!/usr/bin/env python3
"""Compare LSE daily/minute candles with stored Massive-derived daily rows.

The script is isolated and read-only:
- LSE credentials come from memory or a hidden prompt.
- Neo4j uses READ_ACCESS and execute_read.
- Cached market rows never contain request headers or API keys.
"""

from __future__ import annotations

import argparse
import getpass
import gzip
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import exchange_calendars as xcals
import pandas as pd
import requests
from neo4j import GraphDatabase, READ_ACCESS

from session_reconstruction import aggregate_rows, rows_in_window


BASE_URL = "https://api.londonstrategicedge.com/vault"
USER_AGENT = "EventMarketDB-isolated-replacement-audit/1.0"


def read_gzip_json(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def write_gzip_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wt", encoding="utf-8") as handle:
        json.dump(value, handle, separators=(",", ":"))
    os.replace(temporary, path)


def fetch_lse_rows(
    key: str,
    symbol: str,
    timeframe: str,
    day: str,
    cache_dir: Path,
) -> list[dict[str, Any]]:
    cache = cache_dir / f"{symbol}_{day}_{timeframe}.json.gz"
    if cache.exists():
        rows = read_gzip_json(cache)
        if not isinstance(rows, list):
            raise RuntimeError(f"Invalid cache shape in {cache}")
        return rows

    end_exclusive = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
    response = requests.get(
        f"{BASE_URL}/candles",
        params={
            "symbol": symbol,
            "dataset": "stocks",
            "timeframe": timeframe,
            "start": day,
            "end": end_exclusive,
            "order": "asc",
            "limit": 5000,
        },
        headers={
            "x-api-key": key,
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
        timeout=(15, 90),
    )
    if response.status_code != 200:
        body = response.text[:300].replace("\n", " ")
        raise RuntimeError(f"LSE HTTP {response.status_code}: {body}")
    rows = response.json()
    if not isinstance(rows, list):
        raise RuntimeError(f"LSE returned {type(rows).__name__}, expected list")
    write_gzip_json(cache, rows)
    return rows


def graph_price(tx, symbol: str, day: str) -> dict[str, Any] | None:
    query = """
    MATCH (d:Date)-[r:HAS_PRICE]->(c:Company {ticker: $symbol})
    WHERE toString(d.date) = $day
    RETURN c.ticker AS symbol,
           toString(d.date) AS date,
           r.open AS open,
           r.high AS high,
           r.low AS low,
           r.close AS close,
           r.volume AS volume,
           r.vwap AS vwap,
           r.transactions AS transactions,
           toString(r.timestamp) AS timestamp,
           r.daily_return AS daily_return
    LIMIT 1
    """
    record = tx.run(query, symbol=symbol, day=day).single()
    return record.data() if record else None


def get_graph_prices(cases: list[tuple[str, str]]) -> dict[str, Any]:
    uri = os.environ.get("NEO4J_URI")
    username = os.environ.get("NEO4J_USERNAME")
    password = os.environ.get("NEO4J_PASSWORD")
    if not all((uri, username, password)):
        raise RuntimeError("Neo4j environment variables are required")

    result: dict[str, Any] = {}
    driver = GraphDatabase.driver(uri, auth=(username, password))
    try:
        with driver.session(default_access_mode=READ_ACCESS) as session:
            for symbol, day in cases:
                key = f"{symbol}:{day}"
                result[key] = session.execute_read(graph_price, symbol, day)
    finally:
        driver.close()
    return result


def daily_row(rows: list[dict[str, Any]], day: str) -> dict[str, Any] | None:
    matches = [row for row in rows if str(row.get("ts", ""))[:10] == day]
    if len(matches) > 1:
        raise RuntimeError(f"More than one LSE daily row for {day}")
    return matches[0] if matches else None


def field_differences(
    reference: dict[str, Any] | None,
    candidate: dict[str, Any] | None,
) -> dict[str, float | None]:
    fields = ("open", "high", "low", "close", "volume")
    result: dict[str, float | None] = {}
    for field in fields:
        if reference is None or candidate is None:
            result[field] = None
            continue
        left = reference.get(field)
        right = candidate.get(field)
        result[field] = (
            float(right) - float(left)
            if left is not None and right is not None
            else None
        )
    return result


def parse_case(raw: str) -> tuple[str, str]:
    symbol, separator, day = raw.partition(":")
    if not separator:
        raise argparse.ArgumentTypeError("case must be SYMBOL:YYYY-MM-DD")
    symbol = symbol.strip().upper()
    try:
        date.fromisoformat(day)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("case date must be YYYY-MM-DD") from exc
    return symbol, day


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--case",
        action="append",
        type=parse_case,
        dest="cases",
        help="SYMBOL:YYYY-MM-DD; may be repeated",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    args = parser.parse_args()
    cases = args.cases or [("AVGO", "2024-12-12")]

    key = os.environ.get("LSE_API_KEY") or getpass.getpass("LSE API key: ")
    if not key:
        raise SystemExit("No LSE API key supplied")

    graph_rows = get_graph_prices(cases)
    calendar = xcals.get_calendar("XNYS")
    report: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "safety": "LSE key was not printed or saved; Neo4j was read-only.",
        "cases": {},
    }

    for symbol, day in cases:
        case_key = f"{symbol}:{day}"
        day_ts = pd.Timestamp(day)
        if not calendar.is_session(day_ts):
            raise RuntimeError(f"{day} is not an XNYS session")
        schedule = calendar.schedule.loc[day_ts]
        session_open = schedule["open"].to_pydatetime()
        session_close = schedule["close"].to_pydatetime()

        minute_rows = fetch_lse_rows(
            key, symbol, "1m", day, args.cache_dir
        )
        lse_daily_rows = fetch_lse_rows(
            key, symbol, "1d", day, args.cache_dir
        )
        regular_rows = rows_in_window(
            minute_rows, session_open, session_close
        )
        reconstructed = aggregate_rows(regular_rows)
        lse_daily = daily_row(lse_daily_rows, day)
        graph = graph_rows.get(case_key)

        report["cases"][case_key] = {
            "exchange_session_utc": {
                "open": session_open.astimezone(timezone.utc).isoformat(),
                "close": session_close.astimezone(timezone.utc).isoformat(),
            },
            "lse_minute_rows": {
                "all_day_count": len(minute_rows),
                "regular_session_count": len(regular_rows),
                "zero_volume_all_day": sum(
                    float(row.get("volume", 0)) == 0 for row in minute_rows
                ),
                "first_all_day_ts": (
                    str(minute_rows[0].get("ts")) if minute_rows else None
                ),
                "last_all_day_ts": (
                    str(minute_rows[-1].get("ts")) if minute_rows else None
                ),
            },
            "massive_derived_graph_daily": graph,
            "lse_raw_daily": lse_daily,
            "lse_regular_session_from_minutes": reconstructed,
            "raw_daily_minus_graph": field_differences(graph, lse_daily),
            "reconstructed_minus_graph": field_differences(
                graph, reconstructed
            ),
        }
        print(
            f"{case_key}: all_minute={len(minute_rows)} "
            f"regular_minute={len(regular_rows)}"
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
