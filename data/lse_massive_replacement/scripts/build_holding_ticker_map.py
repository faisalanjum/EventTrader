#!/usr/bin/env python3
"""Build an auditable SEC-holding to LSE stock-symbol map."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


LEGAL_WORDS = {
    "the",
    "inc",
    "incorporated",
    "corp",
    "corporation",
    "co",
    "company",
    "plc",
    "ltd",
    "limited",
    "holdings",
    "holding",
    "group",
    "nv",
    "sa",
}
INVALID_CUSIPS = {"", "N/A", "NA", "NONE", "000000000"}


def normalize_company_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.replace("&", " and ").replace(".", "")
    words = re.findall(r"[a-z0-9]+", text.lower())
    return " ".join(word for word in words if word not in LEGAL_WORDS)


def _cusip_tokens(value: str) -> list[str]:
    return re.findall(r"[0-9A-Z]{9}", str(value).upper())


def _unique_production_cusips(
    rows: Iterable[dict[str, str]],
) -> dict[str, str]:
    candidates: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol:
            continue
        for cusip in _cusip_tokens(row.get("cusip", "")):
            candidates[cusip].add(symbol)
    return {
        cusip: next(iter(symbols))
        for cusip, symbols in candidates.items()
        if len(symbols) == 1
    }


def _selected_holding_keys(
    holdings: dict[str, Any],
    top_size: int,
    selected_funds: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for fund_symbol, fund in holdings["funds"].items():
        if selected_funds and fund_symbol.upper() not in selected_funds:
            continue
        for snapshot in fund["snapshots"]:
            for holding in snapshot.get("holdings", [])[:top_size]:
                cusip = str(holding.get("cusip", "")).strip().upper()
                name = str(holding.get("name", "")).strip()
                key = (
                    f"cusip::{cusip}"
                    if cusip not in INVALID_CUSIPS
                    else f"name::{name}"
                )
                item = selected.setdefault(
                    key,
                    {
                        "key": key,
                        "cusip": cusip,
                        "name": name,
                        "occurrences": 0,
                        "total_selected_weight_percent": 0.0,
                        "funds": set(),
                    },
                )
                item["occurrences"] += 1
                try:
                    item["total_selected_weight_percent"] += float(
                        holding["weight_percent"]
                    )
                except (KeyError, TypeError, ValueError):
                    pass
                item["funds"].add(fund_symbol)
    return selected


def build_holding_ticker_map(
    holdings: dict[str, Any],
    production_rows: Iterable[dict[str, str]],
    prior_maps: Iterable[dict[str, Any]],
    catalog_rows: Iterable[dict[str, Any]],
    manual: dict[str, Any],
    *,
    top_size: int,
    selected_funds: set[str] | None = None,
) -> dict[str, Any]:
    cusip_to_symbol = _unique_production_cusips(production_rows)
    cusip_sources = {
        cusip: "production final_symbols.csv"
        for cusip in cusip_to_symbol
    }
    name_to_symbol: dict[str, str] = {}
    name_sources: dict[str, str] = {}

    for index, prior in enumerate(prior_maps, start=1):
        for cusip, symbol in prior.get("cusip_to_symbol", {}).items():
            cusip_to_symbol[str(cusip).upper()] = str(symbol).upper()
            cusip_sources[str(cusip).upper()] = f"prior map {index}"
        for name, symbol in prior.get("name_to_symbol", {}).items():
            name_to_symbol[str(name)] = str(symbol).upper()
            name_sources[str(name)] = f"prior map {index}"

    for cusip, symbol in manual.get("cusip_to_symbol", {}).items():
        cusip_to_symbol[str(cusip).upper()] = str(symbol).upper()
        cusip_sources[str(cusip).upper()] = "manual reviewed override"
    for name, symbol in manual.get("name_to_symbol", {}).items():
        name_to_symbol[str(name)] = str(symbol).upper()
        name_sources[str(name)] = "manual reviewed override"

    catalog_index: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in catalog_rows:
        if row.get("dataset") != "stocks":
            continue
        symbol = str(row.get("symbol", "")).strip().upper()
        name = str(row.get("name", "")).strip()
        if symbol and name:
            catalog_index[normalize_company_name(name)].append(
                {"symbol": symbol, "name": name}
            )

    selected = _selected_holding_keys(
        holdings,
        int(top_size),
        selected_funds,
    )
    unresolved: list[dict[str, Any]] = []
    mapped_keys: set[str] = set()
    used_cusips: set[str] = set()
    used_names: set[str] = set()
    mapped_weight = 0.0
    total_weight = 0.0

    for key, item in selected.items():
        cusip = item["cusip"]
        name = item["name"]
        cusip_symbol = (
            cusip_to_symbol.get(cusip)
            if cusip not in INVALID_CUSIPS
            else None
        )
        symbol = cusip_symbol
        if not symbol:
            symbol = name_to_symbol.get(name)
        candidates = catalog_index.get(normalize_company_name(name), [])
        unique_symbols = sorted({row["symbol"] for row in candidates})
        if not symbol and len(unique_symbols) == 1:
            symbol = unique_symbols[0]
            if cusip not in INVALID_CUSIPS:
                cusip_to_symbol[cusip] = symbol
                cusip_sources[cusip] = (
                    "unique normalized LSE catalog name"
                )
                cusip_symbol = symbol
            else:
                name_to_symbol[name] = symbol
                name_sources[name] = "unique normalized LSE catalog name"
        elif symbol and not cusip_symbol and cusip not in INVALID_CUSIPS:
            cusip_to_symbol[cusip] = symbol
            cusip_sources[cusip] = (
                f"{name_sources.get(name, 'name map')} promoted to CUSIP"
            )
            cusip_symbol = symbol

        weight = float(item["total_selected_weight_percent"])
        total_weight += weight
        if symbol:
            mapped_keys.add(key)
            mapped_weight += weight
            if cusip_symbol:
                used_cusips.add(cusip)
            else:
                used_names.add(name)
            continue

        unresolved.append(
            {
                "key": key,
                "cusip": cusip,
                "name": name,
                "occurrences": item["occurrences"],
                "total_selected_weight_percent": round(weight, 8),
                "funds": sorted(item["funds"]),
                "exact_name_candidates": unique_symbols,
            }
        )

    unresolved.sort(
        key=lambda row: (
            -row["total_selected_weight_percent"],
            row["key"],
        )
    )
    selected_cusip_map = {
        cusip: cusip_to_symbol[cusip] for cusip in sorted(used_cusips)
    }
    selected_name_map = {
        name: name_to_symbol[name] for name in sorted(used_names)
    }
    return {
        "cusip_to_symbol": selected_cusip_map,
        "name_to_symbol": selected_name_map,
        "provenance": {
            "cusip_sources": {
                cusip: cusip_sources[cusip] for cusip in sorted(used_cusips)
            },
            "name_sources": {
                name: name_sources[name] for name in sorted(used_names)
            },
        },
        "unresolved": unresolved,
        "summary": {
            "selected_holding_keys": len(selected),
            "mapped_holding_keys": len(mapped_keys),
            "unresolved_holding_keys": len(unresolved),
            "mapped_selected_weight_fraction": round(
                mapped_weight / total_weight if total_weight else 0.0,
                6,
            ),
        },
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    project_root = root.parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--holdings",
        type=Path,
        default=root / "inventory" / "sector_sec_holdings_2022q4_2026q1.json",
    )
    parser.add_argument(
        "--production-csv",
        type=Path,
        default=project_root / "config" / "final_symbols.csv",
    )
    parser.add_argument(
        "--prior-map",
        action="append",
        type=Path,
        default=[],
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=root / "inventory" / "lse_market_catalog_2026-07-19.json",
    )
    parser.add_argument("--manual", type=Path, required=True)
    parser.add_argument("--top-size", type=int, default=20)
    parser.add_argument(
        "--symbols",
        default="",
        help="Optional comma-separated fund symbols.",
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    holdings = json.loads(args.holdings.read_text(encoding="utf-8"))
    production_rows = _read_csv(args.production_csv)
    prior_maps = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in args.prior_map
    ]
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    manual = json.loads(args.manual.read_text(encoding="utf-8"))
    selected_funds = {
        symbol.strip().upper()
        for symbol in args.symbols.split(",")
        if symbol.strip()
    }
    result = build_holding_ticker_map(
        holdings,
        production_rows,
        prior_maps,
        catalog["rows"],
        manual,
        top_size=args.top_size,
        selected_funds=selected_funds or None,
    )
    report = {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "inputs": {
            "holdings": str(args.holdings),
            "production_csv": str(args.production_csv),
            "prior_maps": [str(path) for path in args.prior_map],
            "catalog": str(args.catalog),
            "manual": str(args.manual),
            "top_size": args.top_size,
            "symbols": sorted(selected_funds),
        },
        "safety": (
            "Local isolated files only. No network, database, Redis, or "
            "production write."
        ),
        **result,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.output)
    print(json.dumps(result["summary"], sort_keys=True))
    print(f"saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
