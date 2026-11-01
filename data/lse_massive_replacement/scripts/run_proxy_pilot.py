#!/usr/bin/env python3
"""Compare four pilot benchmark substitutes with real production history."""

from __future__ import annotations

import argparse
import gzip
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import exchange_calendars as xcals
import pandas as pd

from benchmark_proxy_core import (
    compare_returns,
    portfolio_returns,
    time_varying_portfolio_returns,
)


def close_returns(
    rows: list[dict[str, Any]],
    required_sessions: list[str],
    *,
    round_digits: int | None = 2,
) -> pd.Series:
    """Calculate close returns without bridging a missing required session."""

    closes: dict[str, float] = {}
    for row in rows:
        timestamp = str(row.get("ts", row.get("timestamp", "")))
        if len(timestamp) < 10:
            continue
        try:
            close = float(row["close"])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(close):
            closes[timestamp[:10]] = close

    result: dict[str, float] = {}
    for previous_day, current_day in zip(
        required_sessions,
        required_sessions[1:],
    ):
        if previous_day not in closes or current_day not in closes:
            continue
        previous = closes[previous_day]
        if previous == 0:
            continue
        value = (closes[current_day] - previous) / previous * 100
        result[current_day] = (
            round(value, round_digits) if round_digits is not None else value
        )
    return pd.Series(result, dtype=float)


def regular_close_returns(
    rows: list[dict[str, Any]],
    required_sessions: list[str],
    market_closes: dict[str, str],
    *,
    round_digits: int | None = 2,
    split_rows: list[dict[str, Any]] | None = None,
) -> pd.Series:
    """Use the hourly candle whose one-hour window ends at market close.

    Recent LSE hourly candles can retain a split price jump even when older
    history has already been adjusted. On a known split date, use the split
    factor only when it reduces that artificial discontinuity.
    """

    hourly_closes: dict[pd.Timestamp, float] = {}
    for row in rows:
        try:
            timestamp = pd.Timestamp(str(row["ts"]))
            if timestamp.tzinfo is None:
                timestamp = timestamp.tz_localize("UTC")
            else:
                timestamp = timestamp.tz_convert("UTC")
            value = float(row["close"])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(value):
            hourly_closes[timestamp] = value

    closes: dict[str, float] = {}
    for session in required_sessions:
        close_value = market_closes.get(session)
        if not close_value:
            continue
        expected_bar_start = pd.Timestamp(close_value).tz_convert("UTC") - pd.Timedelta(
            hours=1
        )
        if expected_bar_start in hourly_closes:
            closes[session] = hourly_closes[expected_bar_start]

    split_factors: dict[str, float] = {}
    seen_splits: set[tuple[str, float, float]] = set()
    for row in split_rows or []:
        effective_date = str(row.get("effective_date", ""))[:10]
        try:
            split_from = float(row["split_from"])
            split_to = float(row["split_to"])
        except (KeyError, TypeError, ValueError):
            continue
        if (
            not effective_date
            or not math.isfinite(split_from)
            or not math.isfinite(split_to)
            or split_from <= 0
            or split_to <= 0
        ):
            continue
        split_key = (effective_date, split_from, split_to)
        if split_key in seen_splits:
            continue
        seen_splits.add(split_key)
        split_factors[effective_date] = (
            split_factors.get(effective_date, 1.0)
            * split_to
            / split_from
        )

    result: dict[str, float] = {}
    for previous_day, current_day in zip(
        required_sessions,
        required_sessions[1:],
    ):
        if previous_day not in closes or current_day not in closes:
            continue
        previous = closes[previous_day]
        if previous == 0:
            continue
        current = closes[current_day]
        value = (current - previous) / previous * 100
        split_factor = split_factors.get(current_day)
        if split_factor is not None:
            split_adjusted = (
                (current * split_factor - previous) / previous * 100
            )
            if abs(split_adjusted) < abs(value):
                value = split_adjusted
        result[current_day] = (
            round(value, round_digits) if round_digits is not None else value
        )
    return pd.Series(result, dtype=float)


def read_gzip_rows(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, list):
        raise ValueError(f"expected a row list in {path}")
    return value


def prepare_historical_snapshots(
    snapshots: list[dict[str, Any]],
    ticker_map: dict[str, Any],
    *,
    size: int,
) -> list[dict[str, Any]]:
    """Map the top holdings while retaining the weight of unmapped names."""

    cusip_map = {
        str(key).strip(): str(value).strip()
        for key, value in ticker_map.get("cusip_to_symbol", {}).items()
    }
    name_map = {
        str(key).strip(): str(value).strip()
        for key, value in ticker_map.get("name_to_symbol", {}).items()
    }
    prepared: list[dict[str, Any]] = []
    for snapshot in snapshots:
        weights: dict[str, float] = {}
        unmapped: list[dict[str, Any]] = []
        mapped_weight = 0.0
        selected = snapshot.get("holdings", [])[: int(size)]
        for position, holding in enumerate(selected, start=1):
            try:
                weight = float(holding["weight_percent"])
            except (KeyError, TypeError, ValueError):
                continue
            if not math.isfinite(weight) or weight <= 0:
                continue
            cusip = str(holding.get("cusip", "")).strip()
            name = str(holding.get("name", "")).strip()
            symbol = cusip_map.get(cusip) or name_map.get(name)
            if symbol:
                weights[symbol] = weights.get(symbol, 0.0) + weight
                mapped_weight += weight
            else:
                missing_key = f"__UNMAPPED__::{position}::{cusip or name}"
                weights[missing_key] = weight
                unmapped.append(
                    {
                        "position": position,
                        "cusip": cusip,
                        "name": name,
                        "weight_percent": weight,
                    }
                )

        total_weight = sum(weights.values())
        prepared.append(
            {
                "report_date": str(snapshot.get("report_date", ""))[:10],
                "filing_date": str(snapshot.get("filing_date", ""))[:10],
                "accession": snapshot.get("accession"),
                "source_url": snapshot.get("source_url"),
                "weights": weights,
                "selected_count": len(selected),
                "mapped_count": len(selected) - len(unmapped),
                "captured_fund_weight_percent": total_weight,
                "mapped_fund_weight_percent": mapped_weight,
                "mapped_weight_fraction": (
                    mapped_weight / total_weight if total_weight else 0.0
                ),
                "unmapped": unmapped,
            }
        )
    return prepared


def historical_coverage_thresholds(
    config: dict[str, Any],
    size: int,
) -> list[float]:
    """Run coverage sensitivity only for the largest historical basket."""

    default = float(config["minimum_basket_weight_coverage"])
    sizes = [
        int(value)
        for value in (
            config.get("historical_basket_sizes")
            or config["basket_sizes"]
        )
    ]
    if not sizes or int(size) != max(sizes):
        return [default]
    thresholds = sorted(
        {
            float(value)
            for value in config.get(
                "historical_minimum_weight_coverages",
                [default],
            )
            if 0 < float(value) <= 1
        }
    )
    return thresholds or [default]


def target_series(
    target_report: dict[str, Any],
    symbol: str,
) -> tuple[list[str], pd.Series]:
    rows = [
        row for row in target_report["rows"] if row.get("symbol") == symbol
    ]
    sessions = sorted(str(row["date"])[:10] for row in rows)
    values = {
        str(row["date"])[:10]: float(row["daily_return"])
        for row in rows
        if row.get("daily_return") is not None
    }
    return sessions, pd.Series(values, dtype=float)


def evaluate_candidate(
    target: pd.Series,
    candidate: pd.Series,
    *,
    minimum_observations: int = 500,
    minimum_target_coverage: float = 0.8,
    require_stability: bool = True,
    stability_period: str = "holdout_2025_2026",
    periods: dict[str, tuple[str, str]] | None = None,
) -> dict[str, Any]:
    paired = pd.concat(
        [target.rename("target"), candidate.rename("candidate")],
        axis=1,
        join="inner",
    ).dropna()
    target_count = int(target.notna().sum())
    observations = len(paired)
    full = compare_returns(target, candidate)

    period_ranges = periods or {
        "2023": ("2023-01-01", "2023-12-31"),
        "2024": ("2024-01-01", "2024-12-31"),
        "2025": ("2025-01-01", "2025-12-31"),
        "2026_to_cutoff": ("2026-01-01", "2026-04-27"),
        "training_2023_2024": ("2023-01-01", "2024-12-31"),
        "holdout_2025_2026": ("2025-01-01", "2026-04-27"),
    }
    period_metrics: dict[str, Any] = {}
    for name, (start, end) in period_ranges.items():
        selected = paired.loc[
            (paired.index.astype(str) >= start)
            & (paired.index.astype(str) <= end)
        ]
        period_metrics[name] = compare_returns(
            selected["target"],
            selected["candidate"],
        )

    coverage = observations / target_count if target_count else 0.0
    stability_screen = period_metrics.get(stability_period, {}).get(
        "daily_screen",
        "reject",
    )
    enough_history = (
        observations >= int(minimum_observations)
        and coverage >= float(minimum_target_coverage)
    )
    stable = (
        not require_stability
        or stability_screen in {"strong", "context_only"}
    )
    if enough_history and full["daily_screen"] == "strong" and stable:
        numerical_verdict = "strong"
    elif (
        enough_history
        and full["daily_screen"] == "context_only"
        and stable
    ):
        numerical_verdict = "context_only"
    else:
        numerical_verdict = "reject"

    return {
        "coverage": {
            "target_return_dates": target_count,
            "overlap_return_dates": observations,
            "fraction": round(coverage, 6),
            "first_overlap": str(paired.index[0]) if observations else None,
            "last_overlap": str(paired.index[-1]) if observations else None,
        },
        "full_period": full,
        "periods": period_metrics,
        "numerical_verdict": numerical_verdict,
        "verdict_rules": {
            "minimum_observations": int(minimum_observations),
            "minimum_target_coverage": float(minimum_target_coverage),
            "stability_required": bool(require_stability),
            "stability_period": (
                stability_period if require_stability else None
            ),
            "holdout_must_be_at_least": (
                "context_only" if require_stability else None
            ),
        },
    }


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=root / "config" / "proxy_pilot.json",
    )
    parser.add_argument(
        "--holdings",
        type=Path,
        default=(
            root / "inventory" / "proxy_pilot_holdings_2026-07-17.json"
        ),
    )
    parser.add_argument(
        "--historical-holdings",
        type=Path,
        default=(
            root
            / "inventory"
            / "proxy_pilot_sec_holdings_2022q4_2026q1.json"
        ),
    )
    parser.add_argument(
        "--historical-ticker-map",
        type=Path,
        default=(
            root / "inventory" / "proxy_pilot_sec_ticker_map.json"
        ),
    )
    parser.add_argument(
        "--targets",
        type=Path,
        default=(
            root
            / "results"
            / "proxy_pilot_targets_2023-01-03_to_2026-04-27.json"
        ),
    )
    parser.add_argument(
        "--component-targets",
        type=Path,
        default=(
            root
            / "results"
            / "proxy_pilot_component_targets_2023-01-03_to_2026-04-27.json"
        ),
    )
    parser.add_argument(
        "--lse-manifest",
        type=Path,
        default=(
            root
            / "results"
            / "proxy_pilot_lse_manifest_2026-07-19.json"
        ),
    )
    parser.add_argument(
        "--lse-hourly-manifest",
        type=Path,
        default=(
            root
            / "results"
            / "proxy_pilot_lse_hourly_manifest_2026-07-19.json"
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    config = json.loads(args.config.read_text(encoding="utf-8"))
    holdings = json.loads(args.holdings.read_text(encoding="utf-8"))
    historical_holdings = json.loads(
        args.historical_holdings.read_text(encoding="utf-8")
    )
    historical_ticker_map = json.loads(
        args.historical_ticker_map.read_text(encoding="utf-8")
    )
    targets = json.loads(args.targets.read_text(encoding="utf-8"))
    component_targets = json.loads(
        args.component_targets.read_text(encoding="utf-8")
    )
    manifest = json.loads(args.lse_manifest.read_text(encoding="utf-8"))
    hourly_manifest = json.loads(
        args.lse_hourly_manifest.read_text(encoding="utf-8")
    )

    cache: dict[tuple[str, str], list[dict[str, Any]]] = {}
    cache_evidence: dict[tuple[str, str], dict[str, Any]] = {}
    for item in manifest["requests"]:
        key = (str(item["dataset"]), str(item["symbol"]))
        path = root / item["cache_file"]
        cache[key] = read_gzip_rows(path)
        cache_evidence[key] = item

    hourly_cache: dict[str, list[dict[str, Any]]] = {}
    hourly_evidence: dict[str, list[dict[str, Any]]] = {}
    for item in hourly_manifest["chunks"]:
        symbol = str(item["symbol"])
        path = root / item["cache_file"]
        hourly_cache.setdefault(symbol, []).extend(read_gzip_rows(path))
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
    regular_return_cache: dict[tuple[str, tuple[str, ...]], pd.Series] = {}

    def cached_regular_close_returns(
        symbol: str,
        sessions: list[str],
    ) -> pd.Series:
        key = (symbol, tuple(sessions))
        if key not in regular_return_cache:
            regular_return_cache[key] = regular_close_returns(
                hourly_cache.get(symbol, []),
                sessions,
                market_closes,
                round_digits=None,
            )
        return regular_return_cache[key]

    report: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "safety": (
            "All inputs were isolated cached files and a prior read-only "
            "Neo4j export. No network, database, Redis, or production write "
            "occurred during this calculation."
        ),
        "method": {
            "target": (
                "Stored two-decimal daily returns on Massive-derived Neo4j "
                "HAS_PRICE rows."
            ),
            "direct": (
                "LSE close-to-close returns on consecutive target trading "
                "sessions. Missing sessions are never bridged."
            ),
            "basket": (
                "Weighted average of unrounded LSE constituent returns, then "
                "rounded to two decimals. Available weights are renormalized "
                "only when at least the configured weight coverage is present."
            ),
            "hourly_regular_close": (
                "For each stock and exchange session, use the LSE one-hour bar "
                "whose interval ends exactly at the official XNYS close. This "
                "excludes bars beginning at or after 4:00 p.m. Eastern."
            ),
            "historical_quarterly_basket": (
                "For each day, use the latest official SEC N-PORT quarter-end "
                "holdings dated on or before that day. Top holdings are "
                "renormalized only when at least 90% of their selected weight "
                "has a regular-close LSE return. This is a retrospective "
                "reconstruction: the SEC filing becomes public after its "
                "quarter-end report date."
            ),
            "important_limit": holdings["warning"],
        },
        "funds": {},
    }

    source_validation: dict[str, Any] = {"symbols": {}}
    validation_pairs: list[pd.DataFrame] = []
    component_symbols = sorted(
        {str(row["symbol"]) for row in component_targets["rows"]}
    )
    for symbol in component_symbols:
        sessions, target = target_series(component_targets, symbol)
        candidate = cached_regular_close_returns(symbol, sessions).round(2)
        comparison = evaluate_candidate(target, candidate)
        paired = pd.concat(
            [target.rename("massive"), candidate.rename("lse")],
            axis=1,
            join="inner",
        ).dropna()
        difference = (paired["lse"] - paired["massive"]).abs()
        source_validation["symbols"][symbol] = {
            "comparison": comparison,
            "same_rounded_2dp": int((difference == 0).sum()),
            "within_001_percentage_points": int(
                (difference <= 0.0100000001).sum()
            ),
            "within_005_percentage_points": int(
                (difference <= 0.0500000001).sum()
            ),
            "maximum_absolute_difference_pp": (
                round(float(difference.max()), 10)
                if not difference.empty
                else None
            ),
        }
        if not paired.empty:
            paired["symbol"] = symbol
            validation_pairs.append(paired)

    if validation_pairs:
        all_pairs = pd.concat(validation_pairs, ignore_index=True)
        all_difference = (all_pairs["lse"] - all_pairs["massive"]).abs()
        source_validation["summary"] = {
            "symbols": len(source_validation["symbols"]),
            "return_pairs": len(all_pairs),
            "correlation": round(
                float(all_pairs["massive"].corr(all_pairs["lse"])),
                10,
            ),
            "mean_absolute_difference_pp": round(
                float(all_difference.mean()),
                10,
            ),
            "same_rounded_2dp": int((all_difference == 0).sum()),
            "within_001_percentage_points": int(
                (all_difference <= 0.0100000001).sum()
            ),
            "within_005_percentage_points": int(
                (all_difference <= 0.0500000001).sum()
            ),
            "maximum_absolute_difference_pp": round(
                float(all_difference.max()),
                10,
            ),
            "conclusion": (
                "The hourly regular-close method removes the daily-candle "
                "after-hours date shift and closely reproduces Massive stock "
                "returns. Remaining basket error is mainly benchmark "
                "composition and weighting, not LSE stock-price timing."
            ),
        }
    else:
        source_validation["summary"] = {"symbols": 0, "return_pairs": 0}
    report["regular_close_source_validation"] = source_validation

    for target_symbol in sorted(config["direct_candidates"]):
        sessions, target = target_series(targets, target_symbol)
        fund_result: dict[str, Any] = {
            "target_dates": len(target),
            "direct_candidates": [],
            "official_holding_baskets": [],
            "regular_close_hourly_baskets": [],
            "historical_quarterly_baskets": [],
        }

        for candidate in config["direct_candidates"][target_symbol]:
            key = (candidate["dataset"], candidate["symbol"])
            rows = cache.get(key, [])
            returns = close_returns(rows, sessions)
            fund_result["direct_candidates"].append(
                {
                    **candidate,
                    "lse_history": {
                        "daily_rows": len(rows),
                        "first_timestamp": (
                            rows[0].get("ts") if rows else None
                        ),
                        "last_timestamp": (
                            rows[-1].get("ts") if rows else None
                        ),
                    },
                    "comparison": evaluate_candidate(target, returns),
                }
            )

        fund_holdings = holdings["funds"][target_symbol]
        for size in config["basket_sizes"]:
            selected = fund_holdings["holdings"][: int(size)]
            weights = {
                item["symbol"]: float(item["weight_percent"])
                for item in selected
            }
            constituent_panel = pd.DataFrame(index=sessions)
            hourly_constituent_panel = pd.DataFrame(index=sessions)
            constituent_evidence = []
            for symbol in weights:
                key = ("stocks", symbol)
                rows = cache.get(key, [])
                constituent_panel[symbol] = close_returns(
                    rows,
                    sessions,
                    round_digits=None,
                )
                hourly_rows = hourly_cache.get(symbol, [])
                hourly_constituent_panel[symbol] = (
                    cached_regular_close_returns(symbol, sessions)
                )
                source = cache_evidence.get(key, {})
                constituent_evidence.append(
                    {
                        "symbol": symbol,
                        "fund_weight_percent": weights[symbol],
                        "lse_daily_rows": len(rows),
                        "lse_first_timestamp": source.get("first_timestamp"),
                        "lse_last_timestamp": source.get("last_timestamp"),
                        "lse_hourly_rows": len(hourly_rows),
                        "lse_hourly_chunks": len(
                            hourly_evidence.get(symbol, [])
                        ),
                    }
                )

            basket = portfolio_returns(
                constituent_panel,
                weights,
                minimum_weight_coverage=float(
                    config["minimum_basket_weight_coverage"]
                ),
            )
            basket_returns = basket["return"].round(2)
            valid_coverage = basket.loc[basket["return"].notna(), "weight_coverage"]
            fund_result["official_holding_baskets"].append(
                {
                    "size": int(size),
                    "holdings_as_of": fund_holdings["as_of"],
                    "issuer": fund_holdings["issuer"],
                    "source": fund_holdings["source"],
                    "captured_fund_weight_percent": round(
                        sum(weights.values()), 6
                    ),
                    "constituents": constituent_evidence,
                    "daily_weight_coverage": {
                        "valid_days": int(valid_coverage.count()),
                        "minimum": (
                            round(float(valid_coverage.min()), 6)
                            if not valid_coverage.empty
                            else None
                        ),
                        "mean": (
                            round(float(valid_coverage.mean()), 6)
                            if not valid_coverage.empty
                            else None
                        ),
                    },
                    "comparison": evaluate_candidate(target, basket_returns),
                }
            )

            hourly_basket = portfolio_returns(
                hourly_constituent_panel,
                weights,
                minimum_weight_coverage=float(
                    config["minimum_basket_weight_coverage"]
                ),
            )
            hourly_basket_returns = hourly_basket["return"].round(2)
            hourly_valid_coverage = hourly_basket.loc[
                hourly_basket["return"].notna(), "weight_coverage"
            ]
            fund_result["regular_close_hourly_baskets"].append(
                {
                    "size": int(size),
                    "holdings_as_of": fund_holdings["as_of"],
                    "issuer": fund_holdings["issuer"],
                    "source": fund_holdings["source"],
                    "captured_fund_weight_percent": round(
                        sum(weights.values()), 6
                    ),
                    "constituents": constituent_evidence,
                    "daily_weight_coverage": {
                        "valid_days": int(hourly_valid_coverage.count()),
                        "minimum": (
                            round(float(hourly_valid_coverage.min()), 6)
                            if not hourly_valid_coverage.empty
                            else None
                        ),
                        "mean": (
                            round(float(hourly_valid_coverage.mean()), 6)
                            if not hourly_valid_coverage.empty
                            else None
                        ),
                    },
                    "comparison": evaluate_candidate(
                        target,
                        hourly_basket_returns,
                    ),
                }
            )

        fund_history = historical_holdings["funds"][target_symbol]
        for size in (
            config.get("historical_basket_sizes")
            or config["basket_sizes"]
        ):
            prepared_snapshots = prepare_historical_snapshots(
                fund_history["snapshots"],
                historical_ticker_map,
                size=int(size),
            )
            mapped_symbols = sorted(
                {
                    symbol
                    for snapshot in prepared_snapshots
                    for symbol in snapshot["weights"]
                    if not symbol.startswith("__UNMAPPED__")
                }
            )
            historical_panel = pd.DataFrame(index=sessions)
            for symbol in mapped_symbols:
                historical_panel[symbol] = cached_regular_close_returns(
                    symbol,
                    sessions,
                )

            base_methods = (
                {
                    "method": "fixed_quarter_end_weights",
                    "drift_weights": False,
                    "snapshot_effective_after_date": False,
                    "snapshot_date_rule": (
                        "latest SEC report_date on or before return date"
                    ),
                },
                {
                    "method": "daily_price_drift",
                    "drift_weights": True,
                    "snapshot_effective_after_date": True,
                    "snapshot_date_rule": (
                        "quarter-end weights take effect on the next session, "
                        "then drift with each constituent price"
                    ),
                },
            )
            methods = [
                {
                    **method,
                    "minimum_weight_coverage": minimum_weight_coverage,
                }
                for minimum_weight_coverage in historical_coverage_thresholds(
                    config,
                    int(size),
                )
                for method in base_methods
            ]
            for method in methods:
                historical_basket = time_varying_portfolio_returns(
                    historical_panel,
                    prepared_snapshots,
                    date_key="report_date",
                    minimum_weight_coverage=float(
                        method["minimum_weight_coverage"]
                    ),
                    drift_weights=bool(method["drift_weights"]),
                    snapshot_effective_after_date=bool(
                        method["snapshot_effective_after_date"]
                    ),
                )
                historical_returns = historical_basket["return"].round(2)
                active_coverage = historical_basket.loc[
                    historical_basket["snapshot_date"].notna(),
                    "weight_coverage",
                ]
                valid_coverage = historical_basket.loc[
                    historical_basket["return"].notna(),
                    "weight_coverage",
                ]
                fund_result["historical_quarterly_baskets"].append(
                    {
                        "size": int(size),
                        "method": method["method"],
                        "minimum_weight_coverage": method[
                            "minimum_weight_coverage"
                        ],
                        "snapshot_date_rule": method["snapshot_date_rule"],
                        "retrospective_only_warning": (
                            "N-PORT report_date holdings were filed later. "
                            "This tests reconstruction quality, not what was "
                            "publicly known on each historical date."
                        ),
                        "snapshots": [
                            {
                                key: snapshot[key]
                                for key in (
                                    "report_date",
                                    "filing_date",
                                    "accession",
                                    "source_url",
                                    "selected_count",
                                    "mapped_count",
                                    "captured_fund_weight_percent",
                                    "mapped_fund_weight_percent",
                                    "mapped_weight_fraction",
                                    "unmapped",
                                )
                            }
                            for snapshot in prepared_snapshots
                        ],
                        "symbols": [
                            {
                                "symbol": symbol,
                                "lse_hourly_rows": len(
                                    hourly_cache.get(symbol, [])
                                ),
                                "lse_hourly_chunks": len(
                                    hourly_evidence.get(symbol, [])
                                ),
                            }
                            for symbol in mapped_symbols
                        ],
                        "daily_weight_coverage": {
                            "days_with_snapshot": int(
                                active_coverage.count()
                            ),
                            "valid_days": int(valid_coverage.count()),
                            "invalid_days": int(
                                active_coverage.count()
                                - valid_coverage.count()
                            ),
                            "minimum_all_active_days": (
                                round(float(active_coverage.min()), 6)
                                if not active_coverage.empty
                                else None
                            ),
                            "mean_all_active_days": (
                                round(float(active_coverage.mean()), 6)
                                if not active_coverage.empty
                                else None
                            ),
                            "minimum_valid_days": (
                                round(float(valid_coverage.min()), 6)
                                if not valid_coverage.empty
                                else None
                            ),
                        },
                        "comparison": evaluate_candidate(
                            target,
                            historical_returns,
                        ),
                    }
                )

        report["funds"][target_symbol] = fund_result

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.output)
    print(f"saved: {args.output}")
    for symbol, fund in report["funds"].items():
        print(symbol)
        for item in fund["direct_candidates"]:
            result = item["comparison"]
            full = result["full_period"]
            print(
                f"  direct {item['symbol']}: "
                f"{result['numerical_verdict']}, n={full['observations']}, "
                f"corr={full['correlation']}, beta={full['beta']}, "
                f"mae={full['mean_absolute_error_pp']}"
            )
        for item in fund["official_holding_baskets"]:
            result = item["comparison"]
            full = result["full_period"]
            print(
                f"  basket {item['size']}: "
                f"{result['numerical_verdict']}, n={full['observations']}, "
                f"corr={full['correlation']}, beta={full['beta']}, "
                f"mae={full['mean_absolute_error_pp']}"
            )
        for item in fund["regular_close_hourly_baskets"]:
            result = item["comparison"]
            full = result["full_period"]
            print(
                f"  regular-close basket {item['size']}: "
                f"{result['numerical_verdict']}, n={full['observations']}, "
                f"corr={full['correlation']}, beta={full['beta']}, "
                f"mae={full['mean_absolute_error_pp']}"
            )
        for item in fund["historical_quarterly_baskets"]:
            result = item["comparison"]
            full = result["full_period"]
            print(
                f"  historical-quarterly {item['method']} "
                f"basket {item['size']} "
                f"coverage>={item['minimum_weight_coverage']}: "
                f"{result['numerical_verdict']}, n={full['observations']}, "
                f"corr={full['correlation']}, beta={full['beta']}, "
                f"mae={full['mean_absolute_error_pp']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
