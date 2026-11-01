#!/usr/bin/env python3
"""Test historical official-holdings baskets for many benchmarks."""

from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import exchange_calendars as xcals
import pandas as pd

from benchmark_proxy_core import time_varying_portfolio_returns
from run_proxy_pilot import (
    evaluate_candidate,
    historical_coverage_thresholds,
    prepare_historical_snapshots,
    read_gzip_rows,
    regular_close_returns,
    target_series,
)


VERDICT_RANK = {"reject": 0, "context_only": 1, "strong": 2}


def best_candidate(
    candidates: list[dict[str, Any]],
    *,
    decision_minimum_coverage: float | None = None,
) -> dict[str, Any] | None:
    eligible = candidates
    if decision_minimum_coverage is not None:
        eligible = [
            item
            for item in candidates
            if float(item.get("minimum_weight_coverage", 0))
            >= decision_minimum_coverage
        ]
    if not eligible:
        return None

    def rank(item: dict[str, Any]) -> tuple[int, float, float]:
        comparison = item["comparison"]
        full = comparison["full_period"]
        verdict_rank = VERDICT_RANK.get(
            comparison.get("numerical_verdict"),
            -1,
        )
        observations = int(full.get("observations") or 0)
        mae = full.get("mean_absolute_error_pp")
        error_rank = (
            -float(mae)
            if mae is not None and math.isfinite(float(mae))
            else -math.inf
        )
        if verdict_rank == VERDICT_RANK["reject"]:
            return verdict_rank, float(observations), error_rank
        return (
            verdict_rank,
            error_rank,
            float(observations),
        )

    return max(eligible, key=rank)


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=root / "config" / "proxy_pilot.json",
    )
    parser.add_argument("--historical-holdings", type=Path, required=True)
    parser.add_argument("--historical-ticker-map", type=Path, required=True)
    parser.add_argument(
        "--targets",
        type=Path,
        default=(
            root
            / "results"
            / "all63_benchmark_targets_2023-01-03_to_2026-04-27.json"
        ),
    )
    parser.add_argument("--lse-hourly-manifest", type=Path, required=True)
    parser.add_argument(
        "--splits",
        type=Path,
        help=(
            "Optional JSON report containing LSE stock-split rows under "
            "the 'rows' key."
        ),
    )
    parser.add_argument(
        "--symbols",
        default="",
        help="Optional comma-separated benchmark symbols.",
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    config = json.loads(args.config.read_text(encoding="utf-8"))
    historical_holdings = json.loads(
        args.historical_holdings.read_text(encoding="utf-8")
    )
    ticker_map = json.loads(
        args.historical_ticker_map.read_text(encoding="utf-8")
    )
    targets = json.loads(args.targets.read_text(encoding="utf-8"))
    hourly_manifest = json.loads(
        args.lse_hourly_manifest.read_text(encoding="utf-8")
    )
    split_rows: list[dict[str, Any]] = []
    if args.splits:
        split_report = json.loads(args.splits.read_text(encoding="utf-8"))
        if isinstance(split_report, list):
            split_rows = split_report
        elif isinstance(split_report, dict):
            split_rows = split_report.get("rows", [])
        if not isinstance(split_rows, list):
            raise ValueError("split report 'rows' must be a list")
    splits_by_symbol: dict[str, list[dict[str, Any]]] = {}
    for row in split_rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        if symbol:
            splits_by_symbol.setdefault(symbol, []).append(row)
    selected = {
        symbol.strip().upper()
        for symbol in args.symbols.split(",")
        if symbol.strip()
    }
    evaluation = config.get("evaluation", {})
    evaluation_periods = config.get("evaluation_periods")
    if evaluation_periods:
        evaluation_periods = {
            str(name): (str(bounds[0]), str(bounds[1]))
            for name, bounds in evaluation_periods.items()
        }

    hourly_cache: dict[str, list[dict[str, Any]]] = {}
    hourly_evidence: dict[str, list[dict[str, Any]]] = {}
    for item in hourly_manifest["chunks"]:
        symbol = str(item["symbol"])
        path = root / item["cache_file"]
        rows = read_gzip_rows(path) if path.exists() else []
        hourly_cache.setdefault(symbol, []).extend(rows)
        hourly_evidence.setdefault(symbol, []).append(item)

    calendar = xcals.get_calendar("XNYS")
    calendar_sessions = calendar.sessions_in_range(
        pd.Timestamp(config["period"]["start"]),
        pd.Timestamp(config["period"]["end"]),
    )
    market_closes = {
        session.date().isoformat(): calendar.session_close(session).isoformat()
        for session in calendar_sessions
    }
    return_cache: dict[tuple[str, tuple[str, ...]], pd.Series] = {}

    def constituent_returns(symbol: str, sessions: list[str]) -> pd.Series:
        key = (symbol, tuple(sessions))
        if key not in return_cache:
            return_cache[key] = regular_close_returns(
                hourly_cache.get(symbol, []),
                sessions,
                market_closes,
                round_digits=None,
                split_rows=splits_by_symbol.get(symbol, []),
            )
        return return_cache[key]

    report: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "safety": (
            "Local isolated caches and a prior read-only Neo4j export only. "
            "No network, database, Redis, or production write."
        ),
        "method": {
            "target": (
                "Stored two-decimal daily returns from the production "
                "Massive-derived Neo4j price graph."
            ),
            "candidate": (
                "Official quarterly SEC N-PORT top holdings, weighted by "
                "their filed weights, using each LSE hourly candle ending "
                "at the official 4:00 p.m. New York close."
            ),
            "missing_data": (
                "A day is accepted only when the configured fraction of the "
                "selected basket weight has consecutive-session prices."
            ),
            "look_ahead_warning": (
                "Quarter-end N-PORT holdings are filed later. This is a "
                "retrospective reconstruction test, not a claim that those "
                "weights were public on the report date."
            ),
            "split_adjustment": {
                "source": str(args.splits) if args.splits else None,
                "rows": len(split_rows),
                "symbols": len(splits_by_symbol),
                "rule": (
                    "On a known split date, apply split_to/split_from only "
                    "when it reduces the raw close discontinuity. This "
                    "avoids double-adjusting older LSE candles."
                ),
            },
            "decision_minimum_selected_weight_coverage": float(
                config.get("decision_minimum_weight_coverage", 0.8)
            ),
        },
        "funds": {},
    }

    basket_sizes = (
        config.get("historical_basket_sizes") or config["basket_sizes"]
    )
    for fund_symbol in sorted(historical_holdings["funds"]):
        if selected and fund_symbol not in selected:
            continue
        sessions, target = target_series(targets, fund_symbol)
        fund_history = historical_holdings["funds"][fund_symbol]
        candidates: list[dict[str, Any]] = []

        for size in basket_sizes:
            prepared = prepare_historical_snapshots(
                fund_history["snapshots"],
                ticker_map,
                size=int(size),
            )
            symbols = sorted(
                {
                    symbol
                    for snapshot in prepared
                    for symbol in snapshot["weights"]
                    if not symbol.startswith("__UNMAPPED__")
                }
            )
            panel = pd.DataFrame(index=sessions)
            for symbol in symbols:
                panel[symbol] = constituent_returns(symbol, sessions)

            methods = (
                {
                    "method": "fixed_quarter_end_weights",
                    "drift_weights": False,
                    "snapshot_effective_after_date": False,
                    "snapshot_date_rule": (
                        "latest SEC report date on or before return date"
                    ),
                },
                {
                    "method": "daily_price_drift",
                    "drift_weights": True,
                    "snapshot_effective_after_date": True,
                    "snapshot_date_rule": (
                        "quarter-end weights begin next session and then "
                        "drift with constituent prices"
                    ),
                },
            )
            for minimum_coverage in historical_coverage_thresholds(
                config,
                int(size),
            ):
                for method in methods:
                    basket = time_varying_portfolio_returns(
                        panel,
                        prepared,
                        date_key="report_date",
                        minimum_weight_coverage=float(minimum_coverage),
                        drift_weights=method["drift_weights"],
                        snapshot_effective_after_date=method[
                            "snapshot_effective_after_date"
                        ],
                    )
                    returns = basket["return"].round(2)
                    active = basket.loc[
                        basket["snapshot_date"].notna(),
                        "weight_coverage",
                    ]
                    valid = basket.loc[
                        basket["return"].notna(),
                        "weight_coverage",
                    ]
                    candidates.append(
                        {
                            "size": int(size),
                            "method": method["method"],
                            "minimum_weight_coverage": float(
                                minimum_coverage
                            ),
                            "snapshot_date_rule": method[
                                "snapshot_date_rule"
                            ],
                            "selected_fund_weight_percent": {
                                "minimum": round(
                                    min(
                                        snapshot[
                                            "captured_fund_weight_percent"
                                        ]
                                        for snapshot in prepared
                                    ),
                                    6,
                                ),
                                "maximum": round(
                                    max(
                                        snapshot[
                                            "captured_fund_weight_percent"
                                        ]
                                        for snapshot in prepared
                                    ),
                                    6,
                                ),
                            },
                            "mapping": {
                                "minimum_snapshot_fraction": round(
                                    min(
                                        snapshot["mapped_weight_fraction"]
                                        for snapshot in prepared
                                    ),
                                    6,
                                ),
                                "unmapped": [
                                    {
                                        "report_date": snapshot["report_date"],
                                        "holdings": snapshot["unmapped"],
                                    }
                                    for snapshot in prepared
                                    if snapshot["unmapped"]
                                ],
                            },
                            "constituents": [
                                {
                                    "symbol": symbol,
                                    "hourly_rows": len(
                                        hourly_cache.get(symbol, [])
                                    ),
                                    "chunks": len(
                                        hourly_evidence.get(symbol, [])
                                    ),
                                }
                                for symbol in symbols
                            ],
                            "daily_weight_coverage": {
                                "days_with_snapshot": int(active.count()),
                                "valid_days": int(valid.count()),
                                "invalid_days": int(
                                    active.count() - valid.count()
                                ),
                                "minimum_all_active_days": (
                                    round(float(active.min()), 6)
                                    if not active.empty
                                    else None
                                ),
                                "mean_all_active_days": (
                                    round(float(active.mean()), 6)
                                    if not active.empty
                                    else None
                                ),
                            },
                            "comparison": evaluate_candidate(
                                target,
                                returns,
                                minimum_observations=int(
                                    evaluation.get(
                                        "minimum_observations",
                                        500,
                                    )
                                ),
                                minimum_target_coverage=float(
                                    evaluation.get(
                                        "minimum_target_coverage",
                                        0.8,
                                    )
                                ),
                                require_stability=bool(
                                    evaluation.get(
                                        "require_stability",
                                        True,
                                    )
                                ),
                                stability_period=str(
                                    evaluation.get(
                                        "stability_period",
                                        "holdout_2025_2026",
                                    )
                                ),
                                periods=evaluation_periods,
                            ),
                        }
                    )

        best = best_candidate(
            candidates,
            decision_minimum_coverage=float(
                config.get("decision_minimum_weight_coverage", 0.8)
            ),
        )
        report["funds"][fund_symbol] = {
            "target_dates": int(target.notna().sum()),
            "snapshots": len(fund_history["snapshots"]),
            "candidates": candidates,
            "best_candidate": best,
        }
        if best:
            full = best["comparison"]["full_period"]
            print(
                f"{fund_symbol}: "
                f"{best['comparison']['numerical_verdict']}, "
                f"top {best['size']}, {best['method']}, "
                f"coverage>={best['minimum_weight_coverage']}, "
                f"n={full['observations']}, "
                f"corr={full['correlation']}, "
                f"beta={full['beta']}, "
                f"mae={full['mean_absolute_error_pp']}"
            )

    verdicts = {"strong": 0, "context_only": 0, "reject": 0}
    for fund in report["funds"].values():
        best = fund["best_candidate"]
        verdict = (
            best["comparison"]["numerical_verdict"] if best else "reject"
        )
        verdicts[verdict] = verdicts.get(verdict, 0) + 1
    report["summary"] = {
        "funds": len(report["funds"]),
        "best_verdicts": verdicts,
        "hourly_symbols": len(hourly_cache),
        "hourly_rows": sum(len(rows) for rows in hourly_cache.values()),
        "manifest_errors": hourly_manifest["summary"]["errors"],
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
