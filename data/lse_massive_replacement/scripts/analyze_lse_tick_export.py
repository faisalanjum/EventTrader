#!/usr/bin/env python3
"""Summarize an LSE raw-tick Parquet file without changing it."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb


def scalar_row(connection, sql: str, path: str) -> dict[str, Any]:
    result = connection.execute(sql, [path])
    names = [column[0] for column in result.description]
    row = result.fetchone()
    return dict(zip(names, row)) if row is not None else {}


def json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--session-open-utc", required=True)
    parser.add_argument("--session-close-utc", required=True)
    parser.add_argument("--reference-close", type=float)
    args = parser.parse_args()

    path = str(args.input)
    open_ts = args.session_open_utc
    close_ts = args.session_close_utc
    connection = duckdb.connect()
    # LSE timestamps are UTC wall-clock values. DuckDB otherwise inherits the
    # host timezone and can report a shifted epoch for Parquet TIMESTAMPTZ data.
    connection.execute("SET TimeZone='UTC'")

    schema_rows = connection.execute(
        "DESCRIBE SELECT * FROM read_parquet(?)", [path]
    ).fetchall()
    schema = [
        {"name": row[0], "type": row[1], "nullable": row[2]}
        for row in schema_rows
    ]
    full = scalar_row(
        connection,
        """
        SELECT count(*) AS ticks,
               min(ts) AS first_ts,
               max(ts) AS last_ts,
               sum(volume) AS volume,
               first(price ORDER BY ts) AS open,
               max(price) AS high,
               min(price) AS low,
               last(price ORDER BY ts) AS close
        FROM read_parquet(?)
        """,
        path,
    )
    regular = scalar_row(
        connection,
        f"""
        SELECT count(*) AS ticks,
               min(ts) AS first_ts,
               max(ts) AS last_ts,
               sum(volume) AS volume,
               first(price ORDER BY ts) AS open,
               max(price) AS high,
               min(price) AS low,
               last(price ORDER BY ts) AS close
        FROM read_parquet(?)
        WHERE ts >= TIMESTAMPTZ '{open_ts}'
          AND ts < TIMESTAMPTZ '{close_ts}'
        """,
        path,
    )
    second_summaries: dict[str, Any] = {}
    for second in (
        "2024-12-12 20:59:59+00",
        "2024-12-12 21:00:00+00",
        "2024-12-12 21:00:01+00",
    ):
        second_summaries[second] = scalar_row(
            connection,
            f"""
            SELECT count(*) AS ticks,
                   min(ts) AS first_ts,
                   max(ts) AS last_ts,
                   sum(volume) AS volume,
                   first(price ORDER BY ts) AS open,
                   max(price) AS high,
                   min(price) AS low,
                   last(price ORDER BY ts) AS close
            FROM read_parquet(?)
            WHERE ts >= TIMESTAMPTZ '{second}'
              AND ts < TIMESTAMPTZ '{second}' + INTERVAL 1 SECOND
            """,
            path,
        )

    boundary = scalar_row(
        connection,
        f"""
        SELECT
          last(ts ORDER BY ts) FILTER (
            WHERE ts <= TIMESTAMPTZ '{close_ts}'
          ) AS last_ts_at_or_before_boundary,
          last(price ORDER BY ts) FILTER (
            WHERE ts <= TIMESTAMPTZ '{close_ts}'
          ) AS last_price_at_or_before_boundary,
          first(ts ORDER BY ts) FILTER (
            WHERE ts > TIMESTAMPTZ '{close_ts}'
          ) AS first_ts_after_boundary,
          first(price ORDER BY ts) FILTER (
            WHERE ts > TIMESTAMPTZ '{close_ts}'
          ) AS first_price_after_boundary
        FROM read_parquet(?)
        """,
        path,
    )

    reference_occurrences: dict[str, Any] | None = None
    if args.reference_close is not None:
        reference_occurrences = scalar_row(
            connection,
            f"""
            SELECT count(*) AS ticks,
                   sum(volume) AS volume,
                   min(ts) AS first_ts,
                   max(ts) AS last_ts,
                   count(*) FILTER (
                     WHERE ts < TIMESTAMPTZ '{close_ts}'
                   ) AS ticks_before_boundary,
                   count(*) FILTER (
                     WHERE ts >= TIMESTAMPTZ '{close_ts}'
                   ) AS ticks_at_or_after_boundary
            FROM read_parquet(?)
            WHERE price = {args.reference_close}
            """,
            path,
        )

    output = json_safe(
        {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            ),
            "input": str(args.input),
            "schema": schema,
            "full_export": full,
            "regular_session_half_open": regular,
            "boundary": boundary,
            "one_second_raw_rollups": second_summaries,
            "reference_close_occurrences": reference_occurrences,
            "important_limit": (
                "Raw LSE rows contain only timestamp, symbol, price, and volume; "
                "they do not expose exchange, sale conditions, correction flags, "
                "participant timestamp, SIP timestamp, or sequence number."
            ),
        }
    )
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
