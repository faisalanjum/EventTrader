#!/usr/bin/env python3
"""Fetch yearly LSE hourly chunks for the small official-holdings pilot."""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import requests

from fetch_lse_proxy_pilot import (
    _safe_error,
    fetch_rows,
    read_api_key,
    read_cache,
    safe_name,
    write_cache,
)


def year_chunks(start: str, end: str) -> list[tuple[str, str]]:
    first = date.fromisoformat(start)
    last = date.fromisoformat(end)
    chunks: list[tuple[str, str]] = []
    year = first.year
    while year <= last.year:
        chunk_start = max(first, date(year, 1, 1))
        chunk_end = min(last, date(year, 12, 31))
        chunks.append((chunk_start.isoformat(), chunk_end.isoformat()))
        year += 1
    return chunks


def selected_constituent_symbols(
    holdings: dict[str, Any],
    historical_ticker_map: dict[str, Any],
    selected_funds: set[str] | None = None,
) -> list[str]:
    funds = holdings["funds"]
    selected_holdings = (
        {
            symbol: fund
            for symbol, fund in funds.items()
            if symbol.upper() in selected_funds
        }
        if selected_funds
        else funds
    )
    return sorted(
        {
            str(item["symbol"])
            for fund in selected_holdings.values()
            for item in fund.get("holdings", [])
            if item.get("symbol")
        }
        | {
            str(symbol)
            for symbol in historical_ticker_map[
                "cusip_to_symbol"
            ].values()
        }
        | {
            str(symbol)
            for symbol in historical_ticker_map[
                "name_to_symbol"
            ].values()
        }
    )


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
        "--historical-ticker-map",
        type=Path,
        default=(
            root / "inventory" / "proxy_pilot_sec_ticker_map.json"
        ),
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=root / "raw" / "proxy_pilot_lse_hourly",
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--private-key-source", type=Path)
    parser.add_argument("--request-pause-seconds", type=float, default=0.5)
    parser.add_argument(
        "--symbols",
        default="",
        help="Optional comma-separated fund symbols.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    holdings = json.loads(args.holdings.read_text(encoding="utf-8"))
    historical_ticker_map = json.loads(
        args.historical_ticker_map.read_text(encoding="utf-8")
    )
    api_key = read_api_key(
        os.environ.get("LSE_API_KEY", ""),
        args.private_key_source,
    )
    start = config["period"]["start"]
    end = config["period"]["end"]
    chunks = year_chunks(start, end)
    selected_funds = {
        symbol.strip().upper()
        for symbol in args.symbols.split(",")
        if symbol.strip()
    }
    symbols = selected_constituent_symbols(
        holdings,
        historical_ticker_map,
        selected_funds or None,
    )

    evidence: list[dict[str, Any]] = []
    request_number = 0
    total_requests = len(symbols) * len(chunks)
    with requests.Session() as session:
        for symbol in symbols:
            symbol_rows = 0
            for chunk_start, chunk_end in chunks:
                request_number += 1
                path = args.cache_dir / (
                    f"stocks__{safe_name(symbol)}__{chunk_start}__"
                    f"{chunk_end}__1h.json.gz"
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
                                "symbol": symbol,
                                "dataset": "stocks",
                                "kind": "constituent",
                            },
                            chunk_start,
                            chunk_end,
                            timeframe="1h",
                            limit=5000,
                        )
                        if len(rows) >= 5000:
                            raise RuntimeError(
                                "response reached the 5,000-row limit; "
                                "use smaller chunks"
                            )
                        write_cache(path, rows)
                        status = "downloaded"
                    except RuntimeError as exc:
                        rows = []
                        http_status = 0
                        status = "error"
                        error = _safe_error(exc, api_key)
                    if request_number < total_requests:
                        time.sleep(max(args.request_pause_seconds, 0))

                symbol_rows += len(rows)
                item: dict[str, Any] = {
                    "symbol": symbol,
                    "dataset": "stocks",
                    "timeframe": "1h",
                    "start": chunk_start,
                    "end": chunk_end,
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
                    item["error"] = error
                evidence.append(item)
            print(f"{symbol}: {symbol_rows} hourly rows")

    report = {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "safety": (
            "Read-only LSE GET requests. The API key and headers were not "
            "printed or saved. Production code and databases were untouched."
        ),
        "period": {"start": start, "end": end},
        "symbols": symbols,
        "chunks": evidence,
        "summary": {
            "symbols": len(symbols),
            "requests": len(evidence),
            "rows": sum(item["rows"] for item in evidence),
            "errors": sum(item["status"] == "error" for item in evidence),
            "limit_hits": sum(item["rows"] >= 5000 for item in evidence),
        },
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.manifest.with_suffix(args.manifest.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.manifest)
    print(f"saved manifest: {args.manifest}")
    return 0 if report["summary"]["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
