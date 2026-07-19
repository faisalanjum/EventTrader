#!/usr/bin/env python3
"""Small, secret-safe probe of the LSE REST data contract.

The API key is read from LSE_API_KEY or a hidden terminal prompt. It is never
written or printed. Results contain only response status, headers relevant to
limits, field names, and a few market-data rows.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_URL = "https://api.londonstrategicedge.com/vault"


PROBES: list[dict[str, Any]] = [
    {"name": "usage", "path": "/usage", "params": {}},
    {"name": "meta", "path": "/meta", "params": {}},
    {
        "name": "aapl_daily_2023",
        "path": "/candles",
        "params": {
            "symbol": "AAPL",
            "dataset": "stocks",
            "timeframe": "1d",
            "start": "2023-01-03",
            "end": "2023-01-10",
            "order": "asc",
            "limit": 20,
        },
    },
    {
        "name": "spy_daily_2023",
        "path": "/candles",
        "params": {
            "symbol": "SPY",
            "dataset": "etf",
            "timeframe": "1d",
            "start": "2023-01-03",
            "end": "2023-01-10",
            "order": "asc",
            "limit": 20,
        },
    },
    {
        "name": "xle_daily_2023",
        "path": "/candles",
        "params": {
            "symbol": "XLE",
            "dataset": "etf",
            "timeframe": "1d",
            "start": "2023-01-03",
            "end": "2023-01-10",
            "order": "asc",
            "limit": 20,
        },
    },
    {
        "name": "catalog_absent_xlk_daily",
        "path": "/candles",
        "params": {
            "symbol": "XLK",
            "timeframe": "1d",
            "start": "2026-07-13",
            "end": "2026-07-17",
            "order": "asc",
            "limit": 20,
        },
    },
    {
        "name": "catalog_absent_holx_daily",
        "path": "/candles",
        "params": {
            "symbol": "HOLX",
            "timeframe": "1d",
            "start": "2026-07-13",
            "end": "2026-07-17",
            "order": "asc",
            "limit": 20,
        },
    },
    {
        "name": "aapl_one_second_close_window",
        "path": "/candles",
        "params": {
            "symbol": "AAPL",
            "dataset": "stocks",
            "timeframe": "1s",
            "start": "2026-07-17T19:59:50Z",
            "end": "2026-07-17T20:00:10Z",
            "order": "asc",
            "limit": 100,
        },
    },
    {
        "name": "aapl_one_minute_full_session",
        "path": "/candles",
        "params": {
            "symbol": "AAPL",
            "dataset": "stocks",
            "timeframe": "1m",
            "start": "2026-07-17T13:30:00Z",
            "end": "2026-07-17T20:00:00Z",
            "order": "asc",
            "limit": 500,
        },
    },
    {
        "name": "aapl_one_second_date_ascending_page",
        "path": "/candles",
        "params": {
            "symbol": "AAPL",
            "dataset": "stocks",
            "timeframe": "1s",
            "start": "2026-07-17",
            "end": "2026-07-17",
            "order": "asc",
            "limit": 5000,
        },
    },
    {
        "name": "aapl_one_second_date_descending_page",
        "path": "/candles",
        "params": {
            "symbol": "AAPL",
            "dataset": "stocks",
            "timeframe": "1s",
            "start": "2026-07-17",
            "end": "2026-07-17",
            "order": "desc",
            "limit": 5000,
        },
    },
    {
        "name": "aapl_one_minute_date",
        "path": "/candles",
        "params": {
            "symbol": "AAPL",
            "dataset": "stocks",
            "timeframe": "1m",
            "start": "2026-07-17",
            "end": "2026-07-17",
            "order": "asc",
            "limit": 1000,
        },
    },
    {
        "name": "aapl_one_second_latest_without_dates",
        "path": "/candles",
        "params": {
            "symbol": "AAPL",
            "dataset": "stocks",
            "timeframe": "1s",
            "order": "desc",
            "limit": 5,
        },
    },
    {
        "name": "aapl_one_minute_latest_without_dates",
        "path": "/candles",
        "params": {
            "symbol": "AAPL",
            "dataset": "stocks",
            "timeframe": "1m",
            "order": "desc",
            "limit": 5,
        },
    },
    {
        "name": "aapl_one_second_wide_date_range",
        "path": "/candles",
        "params": {
            "symbol": "AAPL",
            "dataset": "stocks",
            "timeframe": "1s",
            "start": "2026-07-16",
            "end": "2026-07-18",
            "order": "desc",
            "limit": 20,
        },
    },
    {
        "name": "aapl_one_minute_wide_date_range",
        "path": "/candles",
        "params": {
            "symbol": "AAPL",
            "dataset": "stocks",
            "timeframe": "1m",
            "start": "2026-07-16",
            "end": "2026-07-18",
            "order": "desc",
            "limit": 20,
        },
    },
    {
        "name": "spy_daily_first_available_period",
        "path": "/candles",
        "params": {
            "symbol": "SPY",
            "dataset": "etf",
            "timeframe": "1d",
            "start": "2026-04-27",
            "end": "2026-05-05",
            "order": "asc",
            "limit": 20,
        },
    },
    {
        "name": "xle_daily_first_available_period",
        "path": "/candles",
        "params": {
            "symbol": "XLE",
            "dataset": "etf",
            "timeframe": "1d",
            "start": "2026-04-27",
            "end": "2026-05-05",
            "order": "asc",
            "limit": 20,
        },
    },
    {
        "name": "aapl_dividends",
        "path": "/ref/dividends",
        "params": {"symbol": "AAPL", "order": "desc", "limit": 5},
    },
    {
        "name": "nvda_splits",
        "path": "/ref/stock_splits",
        "params": {"symbol": "NVDA", "order": "desc", "limit": 5},
    },
    {
        "name": "aapl_profile",
        "path": "/ref/company_profiles",
        "params": {"symbol": "AAPL", "limit": 5},
    },
]


def request(key: str, path: str, params: dict[str, Any]) -> dict[str, Any]:
    query = urllib.parse.urlencode(
        [(name, str(value)) for name, value in params.items() if value is not None]
    )
    url = BASE_URL + path + (f"?{query}" if query else "")
    req = urllib.request.Request(
        url,
        headers={
            "x-api-key": key,
            "Accept": "application/json",
            "User-Agent": "EventMarketDB-isolated-replacement-audit/1.0",
        },
    )

    response_headers: dict[str, str] = {}
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            status = response.status
            response_headers = {k.lower(): v for k, v in response.headers.items()}
            raw = response.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        response_headers = {k.lower(): v for k, v in exc.headers.items()}
        raw = exc.read()
    except OSError as exc:
        return {
            "status": 0,
            "error_type": type(exc).__name__,
            "error": str(exc)[:300],
        }

    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        body = raw.decode("utf-8", "replace")[:500]

    selected_headers = {
        name: response_headers[name]
        for name in (
            "x-data-bytes",
            "x-ratelimit-limit",
            "x-ratelimit-remaining",
            "x-ratelimit-reset",
            "retry-after",
        )
        if name in response_headers
    }
    result: dict[str, Any] = {
        "status": status,
        "headers": selected_headers,
        "body_type": type(body).__name__,
    }
    if isinstance(body, list):
        result.update(
            {
                "row_count": len(body),
                "field_names": sorted(
                    {key for row in body if isinstance(row, dict) for key in row}
                ),
                "first_rows": body[:3],
                "last_rows": body[-3:] if len(body) > 3 else [],
            }
        )
    elif isinstance(body, dict):
        result.update({"field_names": sorted(body), "body": body})
    else:
        result["body"] = body
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    key = os.environ.get("LSE_API_KEY") or getpass.getpass("LSE API key: ")
    if not key:
        raise SystemExit("No LSE API key supplied")

    output: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "safety": "The key was not printed or saved.",
        "probes": {},
    }
    for probe in PROBES:
        result = request(key, probe["path"], probe["params"])
        output["probes"][probe["name"]] = {
            "request": {"path": probe["path"], "params": probe["params"]},
            "response": result,
        }
        print(
            f"{probe['name']}: status={result.get('status')} "
            f"rows={result.get('row_count', '-')}",
            flush=True,
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(f"saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
