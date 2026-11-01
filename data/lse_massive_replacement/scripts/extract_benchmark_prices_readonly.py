#!/usr/bin/env python3
"""Export Massive-derived benchmark bars from Neo4j without any writes."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from neo4j import GraphDatabase, READ_ACCESS


QUERY = """
MATCH (d:Date)-[r:HAS_PRICE]->(e)
WITH d, r, e, coalesce(e.etf, e.ticker, e.id) AS symbol
WHERE symbol IN $symbols
  AND toString(d.date) >= $start
  AND toString(d.date) <= $end
RETURN symbol,
       labels(e) AS labels,
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
ORDER BY symbol, date
"""


def json_safe(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def fetch_rows(
    uri: str,
    username: str,
    password: str,
    symbols: list[str],
    start: str,
    end: str,
) -> list[dict[str, Any]]:
    def read(tx) -> list[dict[str, Any]]:
        return [
            json_safe(record.data())
            for record in tx.run(
                QUERY,
                symbols=symbols,
                start=start,
                end=end,
            )
        ]

    driver = GraphDatabase.driver(uri, auth=(username, password))
    try:
        driver.verify_connectivity()
        with driver.session(default_access_mode=READ_ACCESS) as session:
            return session.execute_read(read)
    finally:
        driver.close()


def build_report(
    rows: list[dict[str, Any]],
    symbols: list[str],
    start: str,
    end: str,
) -> dict[str, Any]:
    grouped = {
        symbol: [row for row in rows if row.get("symbol") == symbol]
        for symbol in symbols
    }
    return {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "safety": (
            "Neo4j was opened with READ_ACCESS and execute_read. "
            "The query contains no write clause."
        ),
        "source": "Massive-derived Neo4j HAS_PRICE relationships",
        "requested": {"symbols": symbols, "start": start, "end": end},
        "summary": {
            "rows": len(rows),
            "rows_by_symbol": {
                symbol: len(grouped[symbol]) for symbol in symbols
            },
            "first_date_by_symbol": {
                symbol: grouped[symbol][0]["date"] if grouped[symbol] else None
                for symbol in symbols
            },
            "last_date_by_symbol": {
                symbol: grouped[symbol][-1]["date"] if grouped[symbol] else None
                for symbol in symbols
            },
        },
        "rows": rows,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", default="XLK,IGV,XLE,SOXX")
    parser.add_argument("--start", default="2023-01-03")
    parser.add_argument("--end", default="2026-04-27")
    parser.add_argument("--output", type=Path, required=True)
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
    uri = os.environ.get("NEO4J_URI", "")
    username = os.environ.get("NEO4J_USERNAME", "")
    password = os.environ.get("NEO4J_PASSWORD", "")
    if not all((uri, username, password)):
        raise SystemExit(
            "NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD are required"
        )

    rows = fetch_rows(
        uri,
        username,
        password,
        symbols,
        args.start,
        args.end,
    )
    report = build_report(rows, symbols, args.start, args.end)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.output)
    print(f"exported {len(rows)} read-only rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
