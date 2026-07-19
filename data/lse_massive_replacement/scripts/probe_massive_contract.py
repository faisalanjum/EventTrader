#!/usr/bin/env python3
"""Secret-safe, read-only probe of the Massive rules used by production."""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


BASE_URL = "https://api.polygon.io"
USER_AGENT = "EventMarketDB-isolated-replacement-audit/1.0"


def request(
    session: requests.Session,
    api_key: str,
    path: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    response = session.get(
        BASE_URL + path,
        params=params,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
        timeout=(15, 90),
    )
    try:
        body: Any = response.json()
    except ValueError:
        body = response.text[:500]
    return {
        "status": response.status_code,
        "body": body,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds-between", type=float, default=13.0)
    args = parser.parse_args()

    api_key = os.environ.get("POLYGON_API_KEY")
    if not api_key:
        raise SystemExit("POLYGON_API_KEY is required")

    probes = [
        (
            "stock_trade_conditions",
            "/v3/reference/conditions",
            {
                "asset_class": "stocks",
                "data_type": "trade",
                "limit": 1000,
                "sort": "id",
                "order": "asc",
            },
        ),
        (
            "avgo_open_close_2024_12_12",
            "/v1/open-close/AVGO/2024-12-12",
            {"adjusted": "true"},
        ),
        (
            "avgo_grouped_daily_2024_12_12",
            "/v2/aggs/grouped/locale/us/market/stocks/2024-12-12",
            {"adjusted": "true", "include_otc": "false"},
        ),
        (
            "avgo_minute_close_window_2024_12_12",
            (
                "/v2/aggs/ticker/AVGO/range/1/minute/"
                "1734037140000/1734037260000"
            ),
            {"adjusted": "true", "sort": "asc", "limit": 100},
        ),
    ]

    output: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "safety": "The Massive key was read from memory and was not saved.",
        "probes": {},
    }

    with requests.Session() as session:
        for index, (name, path, params) in enumerate(probes):
            if index:
                time.sleep(args.seconds_between)
            result = request(session, api_key, path, params)
            body = result["body"]

            if name == "avgo_grouped_daily_2024_12_12" and isinstance(body, dict):
                rows = body.get("results") or []
                selected = [
                    row
                    for row in rows
                    if isinstance(row, dict) and row.get("T") == "AVGO"
                ]
                body = {
                    key: value
                    for key, value in body.items()
                    if key != "results"
                }
                body["selected_results"] = selected
                body["unfiltered_result_count"] = len(rows)

            output["probes"][name] = {
                "request": {"path": path, "params": params},
                "response": {"status": result["status"], "body": body},
            }
            print(f"{name}: HTTP {result['status']}", flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.output)
    print(f"saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
