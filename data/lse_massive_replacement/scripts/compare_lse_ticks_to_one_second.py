#!/usr/bin/env python3
"""Prove whether LSE one-second candles are direct raw-tick rollups."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import duckdb


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticks", type=Path, required=True)
    parser.add_argument("--seconds", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    connection = duckdb.connect()
    connection.execute("SET TimeZone='UTC'")
    query = """
    WITH raw AS (
      SELECT date_trunc('second', ts) AS ts,
             first(symbol ORDER BY ts) AS symbol,
             first(price ORDER BY ts) AS open,
             max(price) AS high,
             min(price) AS low,
             last(price ORDER BY ts) AS close,
             sum(volume) AS volume,
             count(*) AS ticks
      FROM read_parquet(?)
      GROUP BY 1
    ),
    candle AS (
      SELECT ts, symbol, open, high, low, close, volume
      FROM read_parquet(?)
    ),
    joined AS (
      SELECT coalesce(raw.ts, candle.ts) AS ts,
             raw.ts IS NOT NULL AS has_raw,
             candle.ts IS NOT NULL AS has_candle,
             raw.ticks,
             raw.open AS raw_open,
             candle.open AS candle_open,
             raw.high AS raw_high,
             candle.high AS candle_high,
             raw.low AS raw_low,
             candle.low AS candle_low,
             raw.close AS raw_close,
             candle.close AS candle_close,
             raw.volume AS raw_volume,
             candle.volume AS candle_volume
      FROM raw
      FULL OUTER JOIN candle USING (ts)
    )
    SELECT count(*) AS union_seconds,
           count(*) FILTER (WHERE has_raw) AS raw_seconds,
           count(*) FILTER (WHERE has_candle) AS candle_seconds,
           count(*) FILTER (WHERE has_raw AND has_candle) AS overlap_seconds,
           count(*) FILTER (WHERE has_raw AND NOT has_candle) AS raw_only_seconds,
           count(*) FILTER (WHERE has_candle AND NOT has_raw) AS candle_only_seconds,
           count(*) FILTER (
             WHERE raw_open = candle_open
               AND raw_high = candle_high
               AND raw_low = candle_low
               AND raw_close = candle_close
               AND raw_volume = candle_volume
           ) AS exact_ohlcv_seconds,
           count(*) FILTER (WHERE raw_open != candle_open) AS open_mismatches,
           count(*) FILTER (WHERE raw_high != candle_high) AS high_mismatches,
           count(*) FILTER (WHERE raw_low != candle_low) AS low_mismatches,
           count(*) FILTER (WHERE raw_close != candle_close) AS close_mismatches,
           count(*) FILTER (WHERE raw_volume != candle_volume) AS volume_mismatches,
           max(abs(raw_open - candle_open)) AS max_open_difference,
           max(abs(raw_high - candle_high)) AS max_high_difference,
           max(abs(raw_low - candle_low)) AS max_low_difference,
           max(abs(raw_close - candle_close)) AS max_close_difference,
           max(abs(raw_volume - candle_volume)) AS max_volume_difference,
           sum(raw_volume) AS raw_total_volume,
           sum(candle_volume) AS candle_total_volume,
           sum(ticks) AS raw_ticks
    FROM joined
    """
    cursor = connection.execute(query, [str(args.ticks), str(args.seconds)])
    names = [column[0] for column in cursor.description]
    values = cursor.fetchone()
    comparison = dict(zip(names, values))

    tie_query = """
    WITH maximum_timestamp AS (
      SELECT date_trunc('second', ts) AS second,
             max(ts) AS maximum_ts
      FROM read_parquet(?)
      GROUP BY 1
    ),
    final_timestamp_prices AS (
      SELECT maximum_timestamp.second,
             maximum_timestamp.maximum_ts,
             count(*) AS trades_at_final_timestamp,
             list(tick.price) AS prices_at_final_timestamp
      FROM maximum_timestamp
      JOIN read_parquet(?) AS tick
        ON tick.ts = maximum_timestamp.maximum_ts
      GROUP BY 1, 2
    )
    SELECT count(*) AS seconds,
           count(*) FILTER (
             WHERE trades_at_final_timestamp > 1
           ) AS seconds_with_tied_final_timestamp,
           count(*) FILTER (
             WHERE list_contains(prices_at_final_timestamp, candle.close)
           ) AS candle_close_found_at_final_timestamp,
           count(*) FILTER (
             WHERE NOT list_contains(prices_at_final_timestamp, candle.close)
           ) AS candle_close_not_found_at_final_timestamp
    FROM final_timestamp_prices
    JOIN read_parquet(?) AS candle
      ON candle.ts = final_timestamp_prices.second
    """
    cursor = connection.execute(
        tie_query, [str(args.ticks), str(args.ticks), str(args.seconds)]
    )
    tie_names = [column[0] for column in cursor.description]
    tie_values = cursor.fetchone()
    close_tie_analysis = dict(zip(tie_names, tie_values))

    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "tick_input": str(args.ticks),
        "one_second_input": str(args.seconds),
        "method": (
            "Group raw ticks by UTC second; use first/max/min/last price and "
            "sum volume; full-join those rows to the supplied one-second file."
        ),
        "comparison": comparison,
        "close_tie_analysis": close_tie_analysis,
        "interpretation": (
            "Open, high, low, volume, and second presence can be checked "
            "directly. Raw close ordering is ambiguous when multiple exported "
            "trades have the same final microsecond timestamp because the raw "
            "schema has no sequence field. The tie analysis checks whether the "
            "candle close is one of the prices at that final timestamp."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(output, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.output)
    print(f"saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
