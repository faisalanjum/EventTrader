#!/usr/bin/env python3
"""Fetch isolated LSE daily rows needed by the benchmark-proxy pilot.

The script makes read-only HTTPS GET requests. It never imports production
code, and it saves response rows only--never API keys or request headers.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

import requests


BASE_URL = "https://api.londonstrategicedge.com/vault/candles"
KEY_PATTERN = re.compile(r"lse_live_[A-Za-z0-9]+")
USER_AGENT = "EventMarketDB-isolated-proxy-pilot/1.0"


def read_api_key(environment_value: str, source: Path | None) -> str:
    if environment_value:
        return environment_value.strip()
    if source is None:
        raise ValueError("LSE_API_KEY or --private-key-source is required")
    matches = set(KEY_PATTERN.findall(source.read_text(encoding="utf-8")))
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one LSE key in the private source; found {len(matches)}"
        )
    return matches.pop()


def build_requests(
    config: dict[str, Any],
    holdings: dict[str, Any],
) -> list[dict[str, str]]:
    direct = {
        (str(item["symbol"]), str(item["dataset"]))
        for candidates in config["direct_candidates"].values()
        for item in candidates
    }
    constituents = {
        str(item["symbol"])
        for fund in holdings["funds"].values()
        for item in fund["holdings"]
    }
    result = [
        {"symbol": symbol, "dataset": dataset, "kind": "direct"}
        for symbol, dataset in sorted(direct)
    ]
    result.extend(
        {
            "symbol": symbol,
            "dataset": "stocks",
            "kind": "constituent",
        }
        for symbol in sorted(constituents)
        if (symbol, "stocks") not in direct
    )
    return result


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value)


def cache_path(
    cache_dir: Path,
    request: dict[str, str],
    start: str,
    end: str,
) -> Path:
    return cache_dir / (
        f"{safe_name(request['dataset'])}__{safe_name(request['symbol'])}"
        f"__{start}__{end}__1d.json.gz"
    )


def read_cache(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, list):
        raise ValueError(f"cached response is not a row list: {path}")
    return value


def write_cache(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wt", encoding="utf-8") as handle:
        json.dump(rows, handle, separators=(",", ":"), sort_keys=True)
    os.replace(temporary, path)


def _safe_error(value: object, api_key: str) -> str:
    text = str(value).replace(api_key, "[REDACTED]")
    return KEY_PATTERN.sub("[REDACTED]", text)[:300]


def fetch_rows(
    session: requests.Session,
    api_key: str,
    request: dict[str, str],
    start: str,
    end: str,
    *,
    timeframe: str = "1d",
    limit: int = 5000,
) -> tuple[list[dict[str, Any]], int]:
    end_exclusive = (date.fromisoformat(end) + timedelta(days=1)).isoformat()
    last_error = ""
    for attempt in range(4):
        try:
            response = session.get(
                BASE_URL,
                params={
                    "symbol": request["symbol"],
                    "dataset": request["dataset"],
                    "timeframe": timeframe,
                    "start": start,
                    "end": end_exclusive,
                    "order": "asc",
                    "limit": limit,
                },
                headers={
                    "x-api-key": api_key,
                    "Accept": "application/json",
                    "User-Agent": USER_AGENT,
                },
                timeout=90,
            )
            status = response.status_code
            if status == 200:
                value = response.json()
                if not isinstance(value, list):
                    raise ValueError(
                        f"expected a row list, received {type(value).__name__}"
                    )
                return value, status
            last_error = f"HTTP {status}: {response.text[:200]}"
            if status != 429 and status < 500:
                break
        except (OSError, ValueError, requests.RequestException) as exc:
            status = 0
            last_error = _safe_error(exc, api_key)
        if attempt < 3:
            time.sleep(min(2**attempt, 10))
    raise RuntimeError(_safe_error(last_error or "request failed", api_key))


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
        "--cache-dir",
        type=Path,
        default=root / "raw" / "proxy_pilot_lse",
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--private-key-source",
        type=Path,
        help="Private local file containing one key; never copied to output.",
    )
    parser.add_argument(
        "--request-pause-seconds",
        type=float,
        default=0.35,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    holdings = json.loads(args.holdings.read_text(encoding="utf-8"))
    api_key = read_api_key(
        os.environ.get("LSE_API_KEY", ""),
        args.private_key_source,
    )
    requests_to_make = build_requests(config, holdings)
    start = config["period"]["start"]
    end = config["period"]["end"]

    evidence: list[dict[str, Any]] = []
    with requests.Session() as session:
        for index, request in enumerate(requests_to_make):
            path = cache_path(args.cache_dir, request, start, end)
            if path.exists():
                rows = read_cache(path)
                status = "cached"
                http_status = 200
            else:
                try:
                    rows, http_status = fetch_rows(
                        session,
                        api_key,
                        request,
                        start,
                        end,
                    )
                    write_cache(path, rows)
                    status = "downloaded"
                except RuntimeError as exc:
                    rows = []
                    http_status = 0
                    status = "error"
                    error = _safe_error(exc, api_key)
                if index + 1 < len(requests_to_make):
                    time.sleep(max(args.request_pause_seconds, 0))

            item: dict[str, Any] = {
                **request,
                "status": status,
                "http_status": http_status,
                "rows": len(rows),
                "first_timestamp": rows[0].get("ts") if rows else None,
                "last_timestamp": rows[-1].get("ts") if rows else None,
                "cache_file": str(path.relative_to(args.cache_dir.parent.parent)),
            }
            if status == "error":
                item["error"] = error
            evidence.append(item)
            print(
                f"{request['dataset']} {request['symbol']}: "
                f"{status}, {len(rows)} rows"
            )

    report = {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "safety": (
            "Read-only LSE GET requests. The API key and headers were not "
            "printed or saved. Production code and databases were untouched."
        ),
        "period": {"start": start, "end": end},
        "requests": evidence,
        "summary": {
            "requests": len(evidence),
            "with_rows": sum(item["rows"] > 0 for item in evidence),
            "empty": sum(
                item["rows"] == 0 and item["status"] != "error"
                for item in evidence
            ),
            "errors": sum(item["status"] == "error" for item in evidence),
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
