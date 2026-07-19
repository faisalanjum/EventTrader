#!/usr/bin/env python3
"""Build reproducible LSE coverage files from read-only source inventories."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_current_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def load_catalog(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text())
    if not isinstance(value, list):
        raise ValueError("LSE catalog must be a JSON list")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe-csv", type=Path, required=True)
    parser.add_argument("--catalog-json", type=Path, required=True)
    parser.add_argument("--neo4j-inventory", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--supported-stock-list", type=Path, required=True)
    args = parser.parse_args()

    current_rows = load_current_rows(args.universe_csv)
    catalog = load_catalog(args.catalog_json)
    graph = json.loads(args.neo4j_inventory.read_text())

    by_dataset: dict[str, set[str]] = {}
    first_tick: dict[tuple[str, str], str | None] = {}
    for row in catalog:
        dataset = str(row.get("dataset", ""))
        symbol = str(row.get("symbol", ""))
        by_dataset.setdefault(dataset, set()).add(symbol)
        first_tick[(dataset, symbol)] = row.get("first_tick")

    stock_symbols = by_dataset.get("stocks", set())
    etf_symbols = by_dataset.get("etf", set())

    coverage_rows: list[dict[str, Any]] = []
    for row in current_rows:
        symbol = row["symbol"]
        sector = row["sector_etf"]
        industry = row["industry_etf"]
        coverage_rows.append(
            {
                "symbol": symbol,
                "sector_etf": sector,
                "industry_etf": industry,
                "stock_available": symbol in stock_symbols,
                "sector_available": sector in etf_symbols,
                "industry_available": industry in etf_symbols,
                "spy_available": "SPY" in etf_symbols,
                "complete_four_leg": (
                    symbol in stock_symbols
                    and sector in etf_symbols
                    and industry in etf_symbols
                    and "SPY" in etf_symbols
                ),
                "stock_first_tick": first_tick.get(("stocks", symbol)),
                "sector_first_tick": first_tick.get(("etf", sector)),
                "industry_first_tick": first_tick.get(("etf", industry)),
                "spy_first_tick": first_tick.get(("etf", "SPY")),
            }
        )

    graph_rows = graph["queries"]["has_price_symbols"]["rows"]
    graph_by_label: Counter[str] = Counter()
    graph_covered_by_label: Counter[str] = Counter()
    graph_missing: list[dict[str, Any]] = []
    for row in graph_rows:
        symbol = row["symbol"]
        label = row["labels"][0]
        graph_by_label[label] += 1
        available = symbol in (stock_symbols if label == "Company" else etf_symbols)
        if available:
            graph_covered_by_label[label] += 1
        else:
            graph_missing.append(
                {"symbol": symbol, "label": label, "dates": row["dates"]}
            )

    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "inputs": {
            "universe_csv": str(args.universe_csv),
            "catalog_json": str(args.catalog_json),
            "neo4j_inventory": str(args.neo4j_inventory),
        },
        "catalog_counts": {
            dataset: len(symbols)
            for dataset, symbols in sorted(by_dataset.items())
        },
        "current_universe": {
            "companies": len(coverage_rows),
            "stock_available": sum(row["stock_available"] for row in coverage_rows),
            "sector_available": sum(
                row["sector_available"] for row in coverage_rows
            ),
            "industry_available": sum(
                row["industry_available"] for row in coverage_rows
            ),
            "complete_four_leg": sum(
                row["complete_four_leg"] for row in coverage_rows
            ),
            "missing_companies": sorted(
                row["symbol"]
                for row in coverage_rows
                if not row["stock_available"]
            ),
            "covered_sector_etfs": sorted(
                {row["sector_etf"] for row in coverage_rows}
                & etf_symbols
            ),
            "covered_industry_etfs": sorted(
                {row["industry_etf"] for row in coverage_rows}
                & etf_symbols
            ),
        },
        "graph_price_universe": {
            "required_by_label": dict(sorted(graph_by_label.items())),
            "covered_by_label": dict(sorted(graph_covered_by_label.items())),
            "required_total": sum(graph_by_label.values()),
            "covered_total": sum(graph_covered_by_label.values()),
            "missing": sorted(
                graph_missing, key=lambda row: (row["label"], row["symbol"])
            ),
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(coverage_rows[0]))
        writer.writeheader()
        writer.writerows(coverage_rows)

    supported = sorted(
        row["symbol"] for row in coverage_rows if row["stock_available"]
    )
    args.supported_stock_list.write_text("\n".join(supported) + "\n")

    print(
        f"current stocks: {len(supported)}/{len(coverage_rows)}; "
        f"complete four-leg: {output['current_universe']['complete_four_leg']}"
    )
    print(f"saved: {args.output_json}")
    print(f"saved: {args.output_csv}")
    print(f"saved: {args.supported_stock_list}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
