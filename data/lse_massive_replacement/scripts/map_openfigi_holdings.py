#!/usr/bin/env python3
"""Resolve difficult SEC holdings through free OpenFIGI identifier mapping."""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Sequence

import requests

from build_holding_ticker_map import (
    INVALID_CUSIPS,
    normalize_company_name,
)


OPENFIGI_URL = "https://api.openfigi.com/v3/mapping"
EXCHANGE_SUFFIX = {
    "AU": ".AX",
    "AV": ".VI",
    "BB": ".BR",
    "CN": ".TO",
    "DC": ".CO",
    "FH": ".HE",
    "FP": ".PA",
    "GR": ".DE",
    "GY": ".DE",
    "HK": ".HK",
    "IM": ".MI",
    "JP": ".T",
    "KS": ".KS",
    "LN": ".L",
    "NA": ".AS",
    "NO": ".OL",
    "PL": ".WA",
    "SJ": ".JO",
    "SM": ".MC",
    "SP": ".SI",
    "SS": ".SS",
    "ST": ".ST",
    "SW": ".SW",
    "TI": ".IS",
}
CURRENCY_SUFFIXES = {
    "AUD",
    "CAD",
    "CHF",
    "CNY",
    "DKK",
    "EUR",
    "GBX",
    "HKD",
    "JPY",
    "KRW",
    "NOK",
    "PLN",
    "SEK",
    "TRY",
    "TWD",
    "USD",
    "ZAR",
}


def choose_lse_symbol(
    figi_rows: list[dict[str, Any]],
    catalog_rows: list[dict[str, Any]],
    holding_name: str,
) -> dict[str, Any] | None:
    catalog = [
        row
        for row in catalog_rows
        if row.get("dataset") == "stocks" and row.get("symbol")
    ]
    catalog_symbols = {str(row["symbol"]).upper() for row in catalog}
    normalized_holding = normalize_company_name(holding_name)

    exact_us = sorted(
        {
            str(row.get("ticker", "")).upper()
            for row in figi_rows
            if str(row.get("exchCode", "")).upper() == "US"
            and str(row.get("ticker", "")).upper() in catalog_symbols
        }
    )
    if len(exact_us) == 1:
        return {
            "symbol": exact_us[0],
            "selection": "exact OpenFIGI ticker in LSE catalog",
        }

    exchange_matches: set[str] = set()
    for row in figi_rows:
        ticker = str(row.get("ticker", "")).upper()
        suffix = EXCHANGE_SUFFIX.get(
            str(row.get("exchCode", "")).upper()
        )
        if ticker and suffix and f"{ticker}{suffix}" in catalog_symbols:
            exchange_matches.add(f"{ticker}{suffix}")
    if len(exchange_matches) == 1:
        return {
            "symbol": next(iter(exchange_matches)),
            "selection": "unique suffixed LSE symbol for FIGI ticker",
        }

    catalog_by_symbol = {
        str(row["symbol"]).upper(): row for row in catalog
    }
    currency_matches: set[str] = set()
    for row in figi_rows:
        ticker = str(row.get("ticker", "")).upper()
        for suffix in CURRENCY_SUFFIXES:
            if not ticker.endswith(suffix):
                continue
            base = ticker[: -len(suffix)]
            catalog_row = catalog_by_symbol.get(base)
            if not catalog_row:
                continue
            catalog_name = normalize_company_name(
                str(catalog_row.get("name", ""))
            )
            name_score = SequenceMatcher(
                None,
                normalized_holding,
                catalog_name,
            ).ratio()
            if name_score >= 0.88:
                currency_matches.add(base)
    if len(currency_matches) == 1:
        return {
            "symbol": next(iter(currency_matches)),
            "selection": (
                "currency-suffixed OpenFIGI ticker plus matching LSE "
                "company name"
            ),
        }

    figi_tickers = {
        str(row.get("ticker", "")).upper()
        for row in figi_rows
        if row.get("ticker")
    }
    exact = sorted(figi_tickers & catalog_symbols)
    if len(exact) == 1:
        return {
            "symbol": exact[0],
            "selection": "exact OpenFIGI ticker in LSE catalog",
        }

    suffixed = [
        row
        for row in catalog
        if str(row["symbol"]).upper().split(".", 1)[0] in figi_tickers
    ]
    suffixed_symbols = sorted(
        {str(row["symbol"]).upper() for row in suffixed}
    )
    if len(suffixed_symbols) == 1:
        return {
            "symbol": suffixed_symbols[0],
            "selection": "unique suffixed LSE symbol for FIGI ticker",
        }

    name_matched = sorted(
        {
            str(row["symbol"]).upper()
            for row in suffixed
            if normalize_company_name(str(row.get("name", "")))
            == normalized_holding
        }
    )
    if len(name_matched) == 1:
        return {
            "symbol": name_matched[0],
            "selection": (
                "OpenFIGI ticker plus exact normalized LSE company name"
            ),
        }
    return None


def _holding_lookup(
    holdings: dict[str, Any],
    top_size: int,
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for fund in holdings["funds"].values():
        for snapshot in fund["snapshots"]:
            for holding in snapshot.get("holdings", [])[:top_size]:
                cusip = str(holding.get("cusip", "")).strip().upper()
                name = str(holding.get("name", "")).strip()
                key = (
                    f"cusip::{cusip}"
                    if cusip not in INVALID_CUSIPS
                    else f"name::{name}"
                )
                result.setdefault(
                    key,
                    {
                        "key": key,
                        "cusip": cusip,
                        "name": name,
                        "isin": str(holding.get("isin", "")).strip(),
                    },
                )
    return result


def _mapping_job(holding: dict[str, str]) -> dict[str, str] | None:
    if holding["isin"]:
        return {"idType": "ID_ISIN", "idValue": holding["isin"]}
    cusip = holding["cusip"]
    if cusip in INVALID_CUSIPS:
        return None
    id_type = "ID_CUSIP" if cusip[0].isdigit() else "ID_CINS"
    return {"idType": id_type, "idValue": cusip}


def _fetch_batches(
    jobs: list[dict[str, Any]],
    pause_seconds: float,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    with requests.Session() as session:
        for start in range(0, len(jobs), 5):
            batch = jobs[start : start + 5]
            payload = [item["job"] for item in batch]
            last_error = ""
            for attempt in range(5):
                response = session.post(
                    OPENFIGI_URL,
                    json=payload,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "User-Agent": (
                            "EventMarketDB isolated replacement audit"
                        ),
                    },
                    timeout=90,
                )
                if response.status_code == 200:
                    values = response.json()
                    if not isinstance(values, list) or len(values) != len(batch):
                        raise RuntimeError(
                            "OpenFIGI response did not align with request"
                        )
                    results.extend(
                        {
                            **item,
                            "response": value,
                        }
                        for item, value in zip(batch, values)
                    )
                    break
                last_error = (
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )
                if response.status_code != 429 and response.status_code < 500:
                    raise RuntimeError(last_error)
                if attempt < 4:
                    retry = response.headers.get(
                        "ratelimit-reset",
                        response.headers.get("Retry-After", "3"),
                    )
                    try:
                        wait = max(float(retry), 1)
                    except ValueError:
                        wait = 3
                    time.sleep(min(wait, 60))
            else:
                raise RuntimeError(last_error or "OpenFIGI request failed")
            if start + 5 < len(jobs):
                time.sleep(max(pause_seconds, 0))
    return results


def split_cached_jobs(
    jobs: list[dict[str, Any]],
    cached_results: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cached_by_key = {
        str(item.get("holding", {}).get("key")): item
        for item in cached_results
        if item.get("holding", {}).get("key")
    }
    reused = []
    pending = []
    for job in jobs:
        key = str(job["holding"]["key"])
        if key in cached_by_key:
            reused.append(cached_by_key[key])
        else:
            pending.append(job)
    return reused, pending


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--holdings", type=Path, required=True)
    parser.add_argument("--draft-map", type=Path, required=True)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=root / "inventory" / "lse_market_catalog_2026-07-19.json",
    )
    parser.add_argument("--top-size", type=int, default=20)
    parser.add_argument("--raw-cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--request-pause-seconds", type=float, default=2.5)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    holdings = json.loads(args.holdings.read_text(encoding="utf-8"))
    draft = json.loads(args.draft_map.read_text(encoding="utf-8"))
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))["rows"]
    lookup = _holding_lookup(holdings, args.top_size)

    jobs = []
    no_identifier = []
    for unresolved in draft["unresolved"]:
        holding = lookup.get(unresolved["key"])
        if not holding:
            no_identifier.append({**unresolved, "reason": "holding not found"})
            continue
        job = _mapping_job(holding)
        if not job:
            no_identifier.append(
                {**unresolved, "reason": "no ISIN, CUSIP, or CINS"}
            )
            continue
        jobs.append({"holding": holding, "job": job})

    cached_results: list[dict[str, Any]] = []
    if args.raw_cache.exists():
        cached_results = json.loads(
            args.raw_cache.read_text(encoding="utf-8")
        )["results"]
    reused_results, pending_jobs = split_cached_jobs(
        jobs,
        cached_results,
    )
    fetched_results = (
        _fetch_batches(
            pending_jobs,
            args.request_pause_seconds,
        )
        if pending_jobs
        else []
    )
    raw_results = reused_results + fetched_results
    if fetched_results or not args.raw_cache.exists():
        cache_by_key = {
            str(item["holding"]["key"]): item
            for item in cached_results + fetched_results
        }
        raw_report = {
            "generated_at_utc": datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
            "source": OPENFIGI_URL,
            "results": [
                cache_by_key[key] for key in sorted(cache_by_key)
            ],
        }
        args.raw_cache.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.raw_cache.with_suffix(
            args.raw_cache.suffix + ".tmp"
        )
        temporary.write_text(
            json.dumps(raw_report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, args.raw_cache)

    cusip_to_symbol: dict[str, str] = {}
    name_to_symbol: dict[str, str] = {}
    mapped = []
    unresolved = list(no_identifier)
    for item in raw_results:
        holding = item["holding"]
        response = item["response"]
        figi_rows = response.get("data") or []
        choice = choose_lse_symbol(figi_rows, catalog, holding["name"])
        if not choice:
            unresolved.append(
                {
                    **holding,
                    "reason": response.get("warning")
                    or response.get("error")
                    or "no unique LSE catalog match",
                    "openfigi_candidates": [
                        {
                            key: row.get(key)
                            for key in (
                                "ticker",
                                "name",
                                "exchCode",
                                "securityType2",
                            )
                        }
                        for row in figi_rows
                    ],
                }
            )
            continue
        symbol = choice["symbol"]
        if holding["cusip"] not in INVALID_CUSIPS:
            cusip_to_symbol[holding["cusip"]] = symbol
        else:
            name_to_symbol[holding["name"]] = symbol
        mapped.append({**holding, **choice})

    report = {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "source": (
            "OpenFIGI v3 identifier mapping, accepted only when its ticker "
            "maps uniquely into the authenticated LSE stock catalog."
        ),
        "safety": (
            "Public read-only identifier requests. No credential, database, "
            "Redis, or production write."
        ),
        "cusip_to_symbol": dict(sorted(cusip_to_symbol.items())),
        "name_to_symbol": dict(sorted(name_to_symbol.items())),
        "mapped": sorted(mapped, key=lambda row: row["key"]),
        "unresolved": sorted(
            unresolved,
            key=lambda row: (row.get("key", ""), row.get("name", "")),
        ),
        "summary": {
            "input_unresolved": len(draft["unresolved"]),
            "jobs": len(jobs),
            "cached_jobs": len(reused_results),
            "fetched_jobs": len(fetched_results),
            "mapped": len(mapped),
            "unresolved": len(unresolved),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.output)
    print(json.dumps(report["summary"], sort_keys=True))
    print(f"saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
