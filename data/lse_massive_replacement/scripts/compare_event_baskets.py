#!/usr/bin/env python3
"""Compare holdings baskets with real stored event benchmark returns."""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from event_basket_core import basket_return, return_window
from run_proxy_pilot import read_gzip_rows


def _rounded(value: float | None, digits: int = 10) -> float | None:
    if value is None or not math.isfinite(float(value)):
        return None
    result = round(float(value), digits)
    return 0.0 if result == -0.0 else result


def compare_cases(
    cases: Mapping[str, list[dict[str, Any]]],
    groups: Mapping[str, dict[str, Any]],
    rows_by_group_symbol: Mapping[
        tuple[str, str], list[dict[str, Any]]
    ],
    *,
    minimum_weight_coverage: float = 0.8,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for group_name in sorted(cases):
        group = groups[group_name]
        group_rows = {
            symbol: rows
            for (row_group, symbol), rows in rows_by_group_symbol.items()
            if row_group == group_name
        }
        for event in cases[group_name]:
            for window in ("hourly", "session"):
                start, end = return_window(event, window)
                stock_return = event.get(f"{window}_stock")
                for role in ("sector", "industry"):
                    fund_symbol = str(event[f"{role}_etf"])
                    target = event.get(f"{window}_{role}")
                    fund_plan = group["funds"][fund_symbol]
                    if fund_plan["weights"]:
                        candidate = basket_return(
                            group_rows,
                            fund_plan["weights"],
                            start,
                            end,
                            minimum_weight_coverage=(
                                minimum_weight_coverage
                            ),
                        )
                    else:
                        candidate = {
                            "return": None,
                            "weight_coverage": 0.0,
                            "constituents": 0,
                        }
                    raw_candidate = candidate["return"]
                    rounded_candidate = (
                        round(float(raw_candidate), 2)
                        if raw_candidate is not None
                        else None
                    )
                    target_value = (
                        float(target) if target is not None else None
                    )
                    stock_value = (
                        float(stock_return)
                        if stock_return is not None
                        else None
                    )
                    error = (
                        rounded_candidate - target_value
                        if (
                            rounded_candidate is not None
                            and target_value is not None
                        )
                        else None
                    )
                    stored_relative = (
                        stock_value - target_value
                        if (
                            stock_value is not None
                            and target_value is not None
                        )
                        else None
                    )
                    candidate_relative = (
                        stock_value - rounded_candidate
                        if (
                            stock_value is not None
                            and rounded_candidate is not None
                        )
                        else None
                    )
                    output.append(
                        {
                            "group": group_name,
                            "event_id": event.get("event_id"),
                            "created": event["created"],
                            "market_session": event["market_session"],
                            "window": window,
                            "role": role,
                            "fund": fund_symbol,
                            "start": start,
                            "end": end,
                            "target_return": target_value,
                            "candidate_return_raw": _rounded(
                                raw_candidate
                            ),
                            "candidate_return": rounded_candidate,
                            "error_pp": _rounded(error),
                            "absolute_error_pp": _rounded(
                                abs(error) if error is not None else None
                            ),
                            "stock_return": stock_value,
                            "stored_relative_return": _rounded(
                                stored_relative
                            ),
                            "candidate_relative_return": _rounded(
                                candidate_relative
                            ),
                            "relative_error_pp": _rounded(
                                (
                                    candidate_relative - stored_relative
                                    if (
                                        candidate_relative is not None
                                        and stored_relative is not None
                                    )
                                    else None
                                )
                            ),
                            "weight_coverage": _rounded(
                                candidate["weight_coverage"]
                            ),
                            "constituents": candidate[
                                "constituents"
                            ],
                            "holdings_report_date": group["funds"][
                                fund_symbol
                            ].get("report_date"),
                            "unavailable_reason": fund_plan.get(
                                "unavailable_reason"
                            ),
                        }
                    )
    return output


def summarize_pairs(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    paired = [
        (
            float(row["target_return"]),
            float(row["candidate_return"]),
        )
        for row in rows
        if row.get("target_return") is not None
        and row.get("candidate_return") is not None
    ]
    attempted = len(rows)
    observations = len(paired)
    if not paired:
        return {
            "attempted": attempted,
            "observations": 0,
            "availability": 0.0 if attempted else None,
            "correlation": None,
            "beta": None,
            "mean_error_pp": None,
            "mean_absolute_error_pp": None,
            "median_absolute_error_pp": None,
            "p95_absolute_error_pp": None,
            "maximum_absolute_error_pp": None,
            "within_0_05_pp": 0,
            "within_0_10_pp": 0,
            "within_0_25_pp": 0,
        }

    targets = pd.Series([item[0] for item in paired], dtype=float)
    candidates = pd.Series([item[1] for item in paired], dtype=float)
    differences = [
        round(candidate - target, 10)
        for target, candidate in paired
    ]
    absolute = sorted(abs(value) for value in differences)
    p95_index = max(0, math.ceil(len(absolute) * 0.95) - 1)
    variance = targets.var(ddof=1) if observations > 1 else math.nan
    beta = (
        candidates.cov(targets) / variance
        if observations > 1 and variance > 0
        else math.nan
    )
    correlation = (
        candidates.corr(targets) if observations > 1 else math.nan
    )
    return {
        "attempted": attempted,
        "observations": observations,
        "availability": observations / attempted if attempted else None,
        "correlation": _rounded(correlation),
        "beta": _rounded(beta),
        "mean_error_pp": _rounded(statistics.fmean(differences)),
        "mean_absolute_error_pp": _rounded(
            statistics.fmean(absolute)
        ),
        "median_absolute_error_pp": _rounded(
            statistics.median(absolute)
        ),
        "p95_absolute_error_pp": _rounded(absolute[p95_index]),
        "maximum_absolute_error_pp": _rounded(max(absolute)),
        "within_0_05_pp": sum(value <= 0.05 for value in absolute),
        "within_0_10_pp": sum(value <= 0.10 for value in absolute),
        "within_0_25_pp": sum(value <= 0.25 for value in absolute),
    }


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        type=Path,
        default=root / "results" / "event_return_candidates.json",
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--minimum-weight-coverage",
        type=float,
        default=0.8,
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    case_report = json.loads(args.cases.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    selected_groups = set(manifest["groups"])
    cases = {
        key: value
        for key, value in case_report["cases"].items()
        if key in selected_groups
    }
    rows_by_group_symbol: dict[
        tuple[str, str], list[dict[str, Any]]
    ] = {}
    for chunk in manifest["chunks"]:
        path = root / chunk["cache_file"]
        rows_by_group_symbol[
            (chunk["group"], chunk["symbol"])
        ] = read_gzip_rows(path) if path.exists() else []

    comparisons = compare_cases(
        cases,
        manifest["groups"],
        rows_by_group_symbol,
        minimum_weight_coverage=args.minimum_weight_coverage,
    )
    by_fund_window: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_session_window: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in comparisons:
        by_fund_window[f"{row['fund']}:{row['window']}"].append(row)
        by_session_window[
            f"{row['market_session']}:{row['window']}"
        ].append(row)

    report = {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "safety": (
            "Local isolated LSE caches and a prior read-only Neo4j export "
            "only. No network, database, Redis, or production write."
        ),
        "method": {
            "target": (
                "Stored two-decimal Massive-derived sector and industry "
                "returns on real event relationships."
            ),
            "candidate": (
                "Top-20 historical SEC holdings using LSE one-minute closes "
                "at the exact production start and end timestamps."
            ),
            "minute_limit": (
                "A minute close can include trades later in the same minute; "
                "this is an approximation of production one-second candles."
            ),
            "minimum_selected_weight_coverage": (
                args.minimum_weight_coverage
            ),
        },
        "summary": summarize_pairs(comparisons),
        "by_fund_window": {
            key: summarize_pairs(value)
            for key, value in sorted(by_fund_window.items())
        },
        "by_market_session_window": {
            key: summarize_pairs(value)
            for key, value in sorted(by_session_window.items())
        },
        "comparisons": comparisons,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.output)
    print(json.dumps(report["summary"], sort_keys=True))
    print(f"saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
