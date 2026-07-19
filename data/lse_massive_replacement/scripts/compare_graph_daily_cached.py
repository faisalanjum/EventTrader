#!/usr/bin/env python3
"""Compare real Neo4j Massive daily rows with cached LSE daily candles.

Neo4j is opened in READ_ACCESS. LSE data is read only from prior cache files.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import re
import statistics
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import exchange_calendars as xcals
import pandas as pd
from neo4j import GraphDatabase, READ_ACCESS

from compare_core import (
    Bar,
    bars_by_date,
    compare_daily_panels,
    daily_returns,
    normalize_lse_bar,
    normalize_massive_bar,
    normalize_neo4j_bar,
)


QUERY = """
MATCH (d:Date)-[r:HAS_PRICE]->(e)
WITH d, r, coalesce(e.ticker, e.etf, e.id) AS symbol
WHERE symbol IN $symbols
  AND toString(d.date) >= $start
  AND toString(d.date) <= $end
RETURN symbol,
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


def safe_name(symbol: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", symbol)


def read_gzip_json(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, list):
        raise ValueError(f"Expected a row list in {path}")
    return value


def fetch_graph_rows(
    uri: str,
    username: str,
    password: str,
    symbols: list[str],
    start: str,
    end: str,
) -> list[dict[str, Any]]:
    def read(tx) -> list[dict[str, Any]]:
        return [
            record.data()
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


def panel_from_graph(
    rows: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Bar]], dict[str, dict[str, float]]]:
    bars: dict[str, list[Bar]] = {}
    stored_returns: dict[str, dict[str, float]] = {}
    for row in rows:
        symbol = str(row["symbol"])
        bars.setdefault(symbol, []).append(normalize_neo4j_bar(row))
        if row.get("daily_return") is not None:
            stored_returns.setdefault(symbol, {})[str(row["date"])[:10]] = (
                float(row["daily_return"])
            )
    return (
        {symbol: bars_by_date(values) for symbol, values in bars.items()},
        stored_returns,
    )


def panel_from_lse(
    cache_dir: Path,
    symbols: list[str],
    start: str,
    end: str,
    session_set: set[str],
) -> tuple[dict[str, dict[str, Bar]], dict[str, int]]:
    panel: dict[str, dict[str, Bar]] = {}
    excluded: dict[str, int] = {}
    for symbol in symbols:
        path = cache_dir / f"{safe_name(symbol)}_{start}_{end}_1d.json.gz"
        rows = [normalize_lse_bar(row) for row in read_gzip_json(path)]
        filtered = [row for row in rows if row.date in session_set]
        panel[symbol] = bars_by_date(filtered)
        excluded[symbol] = len(rows) - len(filtered)
    return panel, excluded


def panel_from_massive_cache(
    cache_dir: Path,
    symbols: list[str],
    start: str,
    end: str,
) -> dict[str, dict[str, Bar]]:
    panel: dict[str, dict[str, Bar]] = {}
    for symbol in symbols:
        path = cache_dir / f"{safe_name(symbol)}_{start}_{end}_1d.json.gz"
        rows = [
            normalize_massive_bar(symbol, row)
            for row in read_gzip_json(path)
        ]
        panel[symbol] = bars_by_date(rows)
    return panel


def validate_stored_returns(
    graph: dict[str, dict[str, Bar]],
    stored: dict[str, dict[str, float]],
    sessions: list[str],
) -> dict[str, Any]:
    compared = 0
    exact = 0
    examples: list[dict[str, Any]] = []
    for symbol in sorted(graph):
        calculated = daily_returns(graph[symbol], session_dates=sessions)
        for day in sorted(set(calculated) & set(stored.get(symbol, {}))):
            compared += 1
            actual = stored[symbol][day]
            expected = calculated[day]
            exact += actual == expected
            if actual != expected and len(examples) < 20:
                examples.append(
                    {
                        "symbol": symbol,
                        "date": day,
                        "stored": actual,
                        "recalculated": expected,
                    }
                )
    return {
        "compared": compared,
        "exact": exact,
        "mismatches": compared - exact,
        "mismatch_examples": examples,
    }


def atr_from_bars(rows: list[Bar], days: int) -> float:
    if len(rows) < days + 1:
        raise ValueError(f"Need at least {days + 1} bars")
    true_ranges = []
    previous_close = rows[0].close
    for row in rows[1:]:
        true_ranges.append(
            max(
                row.high - row.low,
                abs(row.high - previous_close),
                abs(row.low - previous_close),
            )
        )
        previous_close = row.close
    window = true_ranges[-days:]
    return sum(window) / len(window)


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil((len(ordered) - 1) * fraction)]


def compare_atr_panels(
    reference: dict[str, dict[str, Bar]],
    candidate: dict[str, dict[str, Bar]],
    *,
    days: int,
) -> dict[str, Any]:
    comparisons: list[dict[str, Any]] = []
    symbols: dict[str, Any] = {}
    for symbol in sorted(set(reference) & set(candidate)):
        dates = sorted(set(reference[symbol]) & set(candidate[symbol]))
        symbol_rows = []
        for end_index in range(days, len(dates)):
            window_dates = dates[end_index - days : end_index + 1]
            reference_atr = atr_from_bars(
                [reference[symbol][day] for day in window_dates], days
            )
            candidate_atr = atr_from_bars(
                [candidate[symbol][day] for day in window_dates], days
            )
            absolute = abs(candidate_atr - reference_atr)
            row = {
                "symbol": symbol,
                "end_date": window_dates[-1],
                "reference_atr": reference_atr,
                "candidate_atr": candidate_atr,
                "absolute_difference": absolute,
                "relative_difference_bp": (
                    absolute / reference_atr * 10_000
                    if reference_atr
                    else None
                ),
                "same_rounded_2dp": (
                    round(reference_atr, 2) == round(candidate_atr, 2)
                ),
            }
            comparisons.append(row)
            symbol_rows.append(row)
        symbols[symbol] = {
            "common_dates": len(dates),
            "rolling_windows": len(symbol_rows),
            "final_window": symbol_rows[-1] if symbol_rows else None,
        }

    absolute = [row["absolute_difference"] for row in comparisons]
    relative = [
        row["relative_difference_bp"]
        for row in comparisons
        if row["relative_difference_bp"] is not None
    ]
    return {
        "days": days,
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
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--lse-cache-dir", type=Path, required=True)
    parser.add_argument("--massive-cache-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    symbols = sorted(
        {
            value.strip().upper()
            for value in args.symbols.split(",")
            if value.strip()
        }
    )
    uri = os.environ.get("NEO4J_URI")
    username = os.environ.get("NEO4J_USERNAME")
    password = os.environ.get("NEO4J_PASSWORD")
    if not all((uri, username, password)):
        raise SystemExit(
            "NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD are required"
        )

    calendar = xcals.get_calendar("XNYS")
    session_index = calendar.sessions_in_range(
        pd.Timestamp(args.start), pd.Timestamp(args.end)
    )
    sessions = [value.date().isoformat() for value in session_index]
    session_set = set(sessions)

    graph_rows = fetch_graph_rows(
        uri,
        username,
        password,
        symbols,
        args.start,
        args.end,
    )
    graph, stored_returns = panel_from_graph(graph_rows)
    lse, excluded = panel_from_lse(
        args.lse_cache_dir,
        symbols,
        args.start,
        args.end,
        session_set,
    )
    comparison = compare_daily_panels(
        graph,
        lse,
        session_dates=sessions,
    )

    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "safety": (
            "Neo4j used READ_ACCESS/execute_read only. LSE rows came from "
            "existing gzip caches. No API or production write was made."
        ),
        "method": {
            "reference": (
                "Real Neo4j HAS_PRICE rows originally loaded from Massive "
                "grouped adjusted daily summaries."
            ),
            "candidate": (
                "Cached LSE 1d stock candles, filtered to XNYS sessions."
            ),
            "start": args.start,
            "end": args.end,
            "symbols": symbols,
            "return_formula": (
                "round((current_close-prior_close)/prior_close*100, 2) "
                "on consecutive XNYS sessions"
            ),
        },
        "graph_rows": len(graph_rows),
        "lse_non_session_rows_excluded": excluded,
        "stored_daily_return_validation": validate_stored_returns(
            graph, stored_returns, sessions
        ),
        "comparison": comparison,
        "atr14": compare_atr_panels(graph, lse, days=14),
    }
    if args.massive_cache_dir:
        refetched_massive = panel_from_massive_cache(
            args.massive_cache_dir,
            symbols,
            args.start,
            args.end,
        )
        output["stored_graph_vs_refetched_massive"] = compare_daily_panels(
            graph,
            refetched_massive,
            session_dates=sessions,
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.output)
    print(f"graph rows: {len(graph_rows)}")
    print(
        "overlap symbol-dates: "
        f"{comparison['coverage']['overlap_symbol_dates']}"
    )
    print(f"saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
