#!/usr/bin/env python3
"""Retest every long-history LSE market series at the official U.S. close."""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

import exchange_calendars as xcals
import pandas as pd
import requests

from fetch_lse_proxy_pilot import (
    _safe_error,
    fetch_rows,
    read_api_key,
    read_cache,
    safe_name,
    write_cache,
)
from run_proxy_pilot import (
    evaluate_candidate,
    regular_close_returns,
    target_series,
)


def long_history_candidates(
    fetches: list[dict[str, Any]],
    *,
    minimum_rows: int,
) -> list[tuple[str, str]]:
    return sorted(
        {
            (str(item["dataset"]), str(item["symbol"]))
            for item in fetches
            if int(item.get("daily_rows") or 0) >= minimum_rows
        }
    )


def day_chunks(
    start: str,
    end: str,
    *,
    days: int = 90,
) -> list[tuple[str, str]]:
    first = date.fromisoformat(start)
    last = date.fromisoformat(end)
    result: list[tuple[str, str]] = []
    current = first
    while current <= last:
        chunk_end = min(current + timedelta(days=days - 1), last)
        result.append((current.isoformat(), chunk_end.isoformat()))
        current = chunk_end + timedelta(days=1)
    return result


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--daily-screen",
        type=Path,
        default=(
            root
            / "results"
            / "all63_market_series_daily_screen_2026-07-19.json"
        ),
    )
    parser.add_argument(
        "--targets",
        type=Path,
        default=(
            root
            / "results"
            / "all63_benchmark_targets_2023-01-03_to_2026-04-27.json"
        ),
    )
    parser.add_argument("--start", default="2023-01-03")
    parser.add_argument("--end", default="2026-04-27")
    parser.add_argument("--minimum-daily-rows", type=int, default=500)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=root / "raw" / "long_market_series_hourly",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--private-key-source", type=Path)
    parser.add_argument("--request-pause-seconds", type=float, default=0.35)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    daily_screen = json.loads(args.daily_screen.read_text(encoding="utf-8"))
    targets = json.loads(args.targets.read_text(encoding="utf-8"))
    candidates = long_history_candidates(
        daily_screen["candidate_fetches"],
        minimum_rows=args.minimum_daily_rows,
    )
    metadata = {
        (str(item["dataset"]), str(item["symbol"])): item
        for item in daily_screen["candidate_fetches"]
    }
    api_key = read_api_key(
        os.environ.get("LSE_API_KEY", ""),
        args.private_key_source,
    )
    chunks = day_chunks(args.start, args.end)
    total_requests = len(candidates) * len(chunks)
    completed = 0
    evidence: list[dict[str, Any]] = []
    histories: dict[tuple[str, str], list[dict[str, Any]]] = {}
    with requests.Session() as session:
        for dataset, symbol in candidates:
            combined: list[dict[str, Any]] = []
            for chunk_start, chunk_end in chunks:
                completed += 1
                cache_path = args.cache_dir / (
                    f"{safe_name(dataset)}__{safe_name(symbol)}__"
                    f"{chunk_start}__{chunk_end}__1h.json.gz"
                )
                status = "cached"
                error = None
                if cache_path.exists():
                    rows = read_cache(cache_path)
                else:
                    try:
                        rows, _ = fetch_rows(
                            session,
                            api_key,
                            {
                                "dataset": dataset,
                                "symbol": symbol,
                                "kind": "regular_close_screen",
                            },
                            chunk_start,
                            chunk_end,
                            timeframe="1h",
                            limit=5000,
                        )
                        if len(rows) >= 5000:
                            raise RuntimeError(
                                "hourly response reached the 5,000-row limit"
                            )
                        write_cache(cache_path, rows)
                        status = "downloaded"
                    except RuntimeError as exc:
                        rows = []
                        status = "error"
                        error = _safe_error(exc, api_key)
                    if completed < total_requests:
                        time.sleep(max(args.request_pause_seconds, 0))
                combined.extend(rows)
                item = {
                    "dataset": dataset,
                    "symbol": symbol,
                    "start": chunk_start,
                    "end": chunk_end,
                    "status": status,
                    "hourly_rows": len(rows),
                    "first_timestamp": (
                        rows[0].get("ts") if rows else None
                    ),
                    "last_timestamp": (
                        rows[-1].get("ts") if rows else None
                    ),
                    "cache_file": str(
                        cache_path.resolve().relative_to(
                            args.daily_screen.resolve().parents[1]
                        )
                    ),
                }
                if error:
                    item["error"] = error
                evidence.append(item)
                if (
                    completed == 1
                    or completed % 20 == 0
                    or completed == total_requests
                ):
                    print(
                        f"hourly chunks: {completed}/{total_requests} "
                        f"(errors={sum(row['status'] == 'error' for row in evidence)})",
                        flush=True,
                    )
            histories[(dataset, symbol)] = combined

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
    returns = {
        key: regular_close_returns(
            rows,
            sessions,
            market_closes,
        )
        for key, rows in histories.items()
    }
    benchmark_symbols = sorted(
        {str(row["symbol"]) for row in targets["rows"]}
    )
    benchmarks: dict[str, Any] = {}
    for benchmark_symbol in benchmark_symbols:
        _, target = target_series(targets, benchmark_symbol)
        comparisons: list[dict[str, Any]] = []
        for dataset, symbol in candidates:
            result = evaluate_candidate(
                target,
                returns[(dataset, symbol)],
            )
            source = metadata[(dataset, symbol)]
            comparisons.append(
                {
                    "dataset": dataset,
                    "symbol": symbol,
                    "name": source.get("name"),
                    "catalog_last_tick": source.get("catalog_last_tick"),
                    "hourly_rows": len(histories[(dataset, symbol)]),
                    "coverage": result["coverage"],
                    "full_period": result["full_period"],
                    "holdout_2025_2026": result["periods"][
                        "holdout_2025_2026"
                    ],
                    "numerical_verdict": result["numerical_verdict"],
                }
            )
        verdict_rank = {"strong": 0, "context_only": 1, "reject": 2}
        ranked = sorted(
            comparisons,
            key=lambda item: (
                verdict_rank[item["numerical_verdict"]],
                -float(item["full_period"]["correlation"] or -1),
                float(
                    item["full_period"]["mean_absolute_error_pp"]
                    if item["full_period"]["mean_absolute_error_pp"] is not None
                    else 999
                ),
            ),
        )
        benchmarks[benchmark_symbol] = {
            "strong_candidates": [
                item
                for item in ranked
                if item["numerical_verdict"] == "strong"
            ],
            "context_candidates": [
                item
                for item in ranked
                if item["numerical_verdict"] == "context_only"
            ],
            "all_candidates": sorted(
                comparisons,
                key=lambda item: (item["dataset"], item["symbol"]),
            ),
        }
        print(
            f"{benchmark_symbol}: "
            f"strong={len(benchmarks[benchmark_symbol]['strong_candidates'])}, "
            f"context={len(benchmarks[benchmark_symbol]['context_candidates'])}"
        )

    report = {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "safety": (
            "Read-only LSE GET requests and a prior read-only Neo4j export. "
            "No credential, production file, or database was changed."
        ),
        "method": (
            "Every candidate with at least 500 daily rows in the broad screen "
            "was fetched hourly. Returns use the one-hour bar ending at each "
            "official XNYS close."
        ),
        "summary": {
            "benchmarks": len(benchmark_symbols),
            "candidates": len(candidates),
            "candidate_symbols": [
                {"dataset": dataset, "symbol": symbol}
                for dataset, symbol in candidates
            ],
            "hourly_chunks": len(evidence),
            "hourly_rows": sum(len(rows) for rows in histories.values()),
            "errors": sum(item["status"] == "error" for item in evidence),
            "benchmarks_with_strong_candidate": sum(
                bool(item["strong_candidates"]) for item in benchmarks.values()
            ),
            "benchmarks_with_context_candidate": sum(
                bool(item["context_candidates"]) for item in benchmarks.values()
            ),
        },
        "fetches": evidence,
        "benchmarks": benchmarks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.output)
    print(f"saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
