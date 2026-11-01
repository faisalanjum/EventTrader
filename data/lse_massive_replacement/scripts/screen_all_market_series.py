#!/usr/bin/env python3
"""Numerically screen every LSE market series against all 63 benchmarks."""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import exchange_calendars as xcals
import pandas as pd
import requests

from audit_production_etf_coverage import MARKET_PROXY_DATASETS
from fetch_lse_proxy_pilot import (
    _safe_error,
    fetch_rows,
    read_api_key,
    read_cache,
    safe_name,
    write_cache,
)
from run_proxy_pilot import close_returns, evaluate_candidate, target_series


def catalog_candidates(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return one row per LSE series that could represent a market price."""

    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        dataset = str(row.get("dataset", "")).lower()
        symbol = str(row.get("symbol", "")).strip()
        if dataset not in MARKET_PROXY_DATASETS or not symbol:
            continue
        by_key.setdefault((dataset, symbol), row)
    return [
        by_key[key]
        for key in sorted(by_key)
    ]


def _candidate_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    verdict_rank = {"strong": 0, "context_only": 1, "reject": 2}
    full = item["full_period"]
    correlation = full.get("correlation")
    mae = full.get("mean_absolute_error_pp")
    return (
        verdict_rank.get(item["numerical_verdict"], 9),
        -float(correlation) if correlation is not None else math.inf,
        float(mae) if mae is not None else math.inf,
        -int(full.get("observations") or 0),
        item["dataset"],
        item["symbol"],
    )


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--catalog",
        type=Path,
        default=root / "inventory" / "lse_market_catalog_2026-07-19.json",
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
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=root / "raw" / "all_market_series_daily",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--private-key-source", type=Path)
    parser.add_argument("--request-pause-seconds", type=float, default=0.35)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    catalog_report = json.loads(args.catalog.read_text(encoding="utf-8"))
    catalog_rows = catalog_report.get("rows", catalog_report)
    if not isinstance(catalog_rows, list):
        raise SystemExit("catalog must contain a row list")
    candidates = catalog_candidates(catalog_rows)
    targets = json.loads(args.targets.read_text(encoding="utf-8"))
    benchmark_symbols = sorted(
        {str(row["symbol"]) for row in targets["rows"]}
    )
    api_key = read_api_key(
        os.environ.get("LSE_API_KEY", ""),
        args.private_key_source,
    )

    calendar = xcals.get_calendar("XNYS")
    exchange_sessions = calendar.sessions_in_range(
        pd.Timestamp(args.start),
        pd.Timestamp(args.end),
    )
    sessions = [value.date().isoformat() for value in exchange_sessions]

    histories: dict[tuple[str, str], list[dict[str, Any]]] = {}
    fetch_evidence: list[dict[str, Any]] = []
    with requests.Session() as session:
        for index, candidate in enumerate(candidates, start=1):
            dataset = str(candidate["dataset"])
            symbol = str(candidate["symbol"])
            cache_path = args.cache_dir / (
                f"{safe_name(dataset)}__{safe_name(symbol)}__"
                f"{args.start}__{args.end}__1d.json.gz"
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
                            "kind": "market_screen",
                        },
                        args.start,
                        args.end,
                        timeframe="1d",
                        limit=5000,
                    )
                    write_cache(cache_path, rows)
                    status = "downloaded"
                except RuntimeError as exc:
                    rows = []
                    status = "error"
                    error = _safe_error(exc, api_key)
                if index < len(candidates):
                    time.sleep(max(args.request_pause_seconds, 0))

            histories[(dataset, symbol)] = rows
            item = {
                "dataset": dataset,
                "symbol": symbol,
                "name": candidate.get("name"),
                "catalog_first_tick": candidate.get("first_tick"),
                "catalog_last_tick": candidate.get("last_tick"),
                "status": status,
                "daily_rows": len(rows),
                "first_timestamp": rows[0].get("ts") if rows else None,
                "last_timestamp": rows[-1].get("ts") if rows else None,
                "cache_file": str(
                    cache_path.resolve().relative_to(
                        args.catalog.resolve().parents[1]
                    )
                ),
            }
            if error:
                item["error"] = error
            fetch_evidence.append(item)
            if index == 1 or index % 20 == 0 or index == len(candidates):
                print(
                    f"market histories: {index}/{len(candidates)} "
                    f"(errors={sum(row['status'] == 'error' for row in fetch_evidence)})",
                    flush=True,
                )

    candidate_returns = {
        key: close_returns(rows, sessions)
        for key, rows in histories.items()
    }
    benchmark_results: dict[str, Any] = {}
    for benchmark_symbol in benchmark_symbols:
        _, target = target_series(targets, benchmark_symbol)
        comparisons: list[dict[str, Any]] = []
        for candidate in candidates:
            dataset = str(candidate["dataset"])
            symbol = str(candidate["symbol"])
            comparison = evaluate_candidate(
                target,
                candidate_returns[(dataset, symbol)],
            )
            comparisons.append(
                {
                    "dataset": dataset,
                    "symbol": symbol,
                    "name": candidate.get("name"),
                    "catalog_country": candidate.get("country"),
                    "catalog_first_tick": candidate.get("first_tick"),
                    "catalog_last_tick": candidate.get("last_tick"),
                    "coverage": comparison["coverage"],
                    "full_period": comparison["full_period"],
                    "holdout_2025_2026": comparison["periods"][
                        "holdout_2025_2026"
                    ],
                    "numerical_verdict": comparison["numerical_verdict"],
                }
            )
        ranked = sorted(comparisons, key=_candidate_sort_key)
        benchmark_results[benchmark_symbol] = {
            "target_return_dates": int(target.notna().sum()),
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
            "top_ten_numerical": ranked[:10],
            "all_candidates": sorted(
                comparisons,
                key=lambda item: (item["dataset"], item["symbol"]),
            ),
        }
        print(
            f"{benchmark_symbol}: "
            f"strong={len(benchmark_results[benchmark_symbol]['strong_candidates'])}, "
            f"context={len(benchmark_results[benchmark_symbol]['context_candidates'])}"
        )

    report = {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "safety": (
            "Read-only LSE GET requests and a prior read-only Neo4j export. "
            "The API key was not printed or saved. Production code and "
            "databases were untouched."
        ),
        "method": {
            "candidate_scope": (
                "Every LSE commodity, currency index, ETF, future, index, "
                "interest-rate price, and volatility series in the fresh "
                "authenticated catalog."
            ),
            "return_rule": (
                "Raw LSE daily close-to-close return on consecutive XNYS "
                "sessions. This is a broad first screen; promising candidates "
                "must be retested at the official 4 p.m. close."
            ),
            "warning": (
                "A numerical match is not automatically a valid economic "
                "substitute. Region, exposure, leverage, freshness, and "
                "meaning require manual review."
            ),
        },
        "period": {
            "start": args.start,
            "end": args.end,
            "exchange_sessions": len(sessions),
        },
        "summary": {
            "benchmarks": len(benchmark_symbols),
            "candidates": len(candidates),
            "pairwise_tests": len(benchmark_symbols) * len(candidates),
            "candidate_histories_with_rows": sum(
                bool(rows) for rows in histories.values()
            ),
            "candidate_history_errors": sum(
                item["status"] == "error" for item in fetch_evidence
            ),
            "benchmarks_with_strong_candidate": sum(
                bool(value["strong_candidates"])
                for value in benchmark_results.values()
            ),
            "benchmarks_with_context_candidate": sum(
                bool(value["context_candidates"])
                for value in benchmark_results.values()
            ),
        },
        "candidate_fetches": fetch_evidence,
        "benchmarks": benchmark_results,
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
