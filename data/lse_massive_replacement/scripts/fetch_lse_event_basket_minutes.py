#!/usr/bin/env python3
"""Fetch minute rows for real event-window holdings-basket tests."""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

import requests

from benchmark_proxy_core import latest_snapshot
from event_basket_core import return_window
from fetch_lse_proxy_pilot import (
    _safe_error,
    fetch_rows,
    read_api_key,
    read_cache,
    safe_name,
    write_cache,
)
from run_proxy_pilot import prepare_historical_snapshots


def build_fetch_plan(
    cases: dict[str, list[dict[str, Any]]],
    historical_holdings: dict[str, Any],
    ticker_map: dict[str, Any],
    *,
    top_size: int,
) -> dict[str, Any]:
    groups: dict[str, Any] = {}
    requests: list[dict[str, str]] = []
    for group_name in sorted(cases):
        events = cases[group_name]
        if not events:
            continue
        endpoints = [
            datetime.fromisoformat(endpoint)
            for event in events
            for window in ("hourly", "session")
            for endpoint in return_window(event, window)
        ]
        start = (min(endpoints).date() - timedelta(days=4)).isoformat()
        end = max(endpoints).date().isoformat()
        event_date = datetime.fromisoformat(events[0]["created"]).date()
        fund_symbols = sorted(
            {
                str(events[0]["sector_etf"]),
                str(events[0]["industry_etf"]),
            }
        )
        funds: dict[str, Any] = {}
        symbols: set[str] = set()
        for fund_symbol in fund_symbols:
            fund = historical_holdings["funds"][fund_symbol]
            prepared = prepare_historical_snapshots(
                fund["snapshots"],
                ticker_map,
                size=top_size,
            )
            snapshot = latest_snapshot(
                prepared,
                event_date,
                date_key="report_date",
            )
            if snapshot is None:
                funds[fund_symbol] = {
                    "report_date": None,
                    "filing_date": None,
                    "accession": None,
                    "source_url": None,
                    "captured_fund_weight_percent": 0.0,
                    "mapped_weight_fraction": 0.0,
                    "weights": {},
                    "unmapped": [],
                    "unavailable_reason": (
                        "no SEC holdings snapshot on or before "
                        f"{event_date.isoformat()}"
                    ),
                }
                continue
            weights = {
                symbol: float(weight)
                for symbol, weight in snapshot["weights"].items()
            }
            symbols.update(
                symbol
                for symbol in weights
                if not symbol.startswith("__UNMAPPED__")
            )
            funds[fund_symbol] = {
                "report_date": snapshot["report_date"],
                "filing_date": snapshot["filing_date"],
                "accession": snapshot["accession"],
                "source_url": snapshot["source_url"],
                "captured_fund_weight_percent": snapshot[
                    "captured_fund_weight_percent"
                ],
                "mapped_weight_fraction": snapshot[
                    "mapped_weight_fraction"
                ],
                "weights": weights,
                "unmapped": snapshot["unmapped"],
            }
        group_symbols = sorted(symbols)
        groups[group_name] = {
            "start": start,
            "end": end,
            "event_date": event_date.isoformat(),
            "events": len(events),
            "funds": funds,
            "symbols": group_symbols,
        }
        requests.extend(
            {
                "group": group_name,
                "symbol": symbol,
                "start": start,
                "end": end,
            }
            for symbol in group_symbols
        )
    return {"groups": groups, "requests": requests}


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        type=Path,
        default=root / "results" / "event_return_candidates.json",
    )
    parser.add_argument(
        "--historical-holdings",
        type=Path,
        default=(
            root
            / "inventory"
            / "all60_mapped_sec_holdings_2022q4_2026q1.json"
        ),
    )
    parser.add_argument(
        "--historical-ticker-map",
        type=Path,
        default=(
            root
            / "inventory"
            / "all60_top20_ticker_map_v2_2026-07-19.json"
        ),
    )
    parser.add_argument("--top-size", type=int, default=20)
    parser.add_argument(
        "--groups",
        default="",
        help="Optional comma-separated event group names.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=root / "raw" / "event_basket_lse_minutes",
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--private-key-source", type=Path)
    parser.add_argument("--request-pause-seconds", type=float, default=0.35)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    case_report = json.loads(args.cases.read_text(encoding="utf-8"))
    cases = case_report["cases"]
    selected_groups = {
        value.strip() for value in args.groups.split(",") if value.strip()
    }
    if selected_groups:
        cases = {
            key: value
            for key, value in cases.items()
            if key in selected_groups
        }
    historical_holdings = json.loads(
        args.historical_holdings.read_text(encoding="utf-8")
    )
    ticker_map = json.loads(
        args.historical_ticker_map.read_text(encoding="utf-8")
    )
    plan = build_fetch_plan(
        cases,
        historical_holdings,
        ticker_map,
        top_size=args.top_size,
    )
    api_key = read_api_key(
        os.environ.get("LSE_API_KEY", ""),
        args.private_key_source,
    )

    chunks: list[dict[str, Any]] = []
    total = len(plan["requests"])
    with requests.Session() as session:
        for number, item in enumerate(plan["requests"], start=1):
            path = args.cache_dir / (
                f"{safe_name(item['group'])}__stocks__"
                f"{safe_name(item['symbol'])}__{item['start']}__"
                f"{item['end']}__1m.json.gz"
            )
            status = "cached"
            http_status = 200
            error = None
            if path.exists():
                rows = read_cache(path)
            else:
                try:
                    rows, http_status = fetch_rows(
                        session,
                        api_key,
                        {
                            "symbol": item["symbol"],
                            "dataset": "stocks",
                            "kind": "event_constituent",
                        },
                        item["start"],
                        item["end"],
                        timeframe="1m",
                        limit=5000,
                    )
                    if len(rows) >= 5000:
                        raise RuntimeError(
                            "response reached the 5,000-row limit"
                        )
                    write_cache(path, rows)
                    status = "downloaded"
                except RuntimeError as exc:
                    rows = []
                    http_status = 0
                    status = "error"
                    error = _safe_error(exc, api_key)
                if number < total:
                    time.sleep(max(args.request_pause_seconds, 0))
            chunk: dict[str, Any] = {
                **item,
                "dataset": "stocks",
                "timeframe": "1m",
                "status": status,
                "http_status": http_status,
                "rows": len(rows),
                "first_timestamp": rows[0].get("ts") if rows else None,
                "last_timestamp": rows[-1].get("ts") if rows else None,
                "cache_file": str(
                    path.relative_to(args.cache_dir.parent.parent)
                ),
            }
            if error:
                chunk["error"] = error
            chunks.append(chunk)
            print(
                f"{number}/{total} {item['group']} {item['symbol']}: "
                f"{len(rows)} rows"
            )

    report = {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "safety": (
            "Read-only LSE GET requests. The API key and headers were not "
            "printed or saved. Production code and databases were untouched."
        ),
        "method": (
            "Top-20 quarterly SEC holdings active on each real event date; "
            "minute candles include four prior calendar days for sparse-trade "
            "fallback."
        ),
        "top_size": args.top_size,
        **plan,
        "chunks": chunks,
        "summary": {
            "groups": len(plan["groups"]),
            "funds": len(
                {
                    fund
                    for group in plan["groups"].values()
                    for fund in group["funds"]
                }
            ),
            "symbols": len({item["symbol"] for item in chunks}),
            "requests": len(chunks),
            "rows": sum(item["rows"] for item in chunks),
            "errors": sum(item["status"] == "error" for item in chunks),
            "zero_row_requests": sum(item["rows"] == 0 for item in chunks),
        },
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.manifest.with_suffix(args.manifest.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.manifest)
    print(f"saved: {args.manifest}")
    return 0 if report["summary"]["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
