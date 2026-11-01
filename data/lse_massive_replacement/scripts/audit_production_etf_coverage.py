#!/usr/bin/env python3
"""Audit every production sector and industry ETF against the live LSE API.

This script is isolated from EventMarketDB runtime code. It reads the production
universe and an optional read-only Neo4j snapshot, but it never imports or
changes production modules and never writes to Neo4j or Redis.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


BASE_URL = "https://api.londonstrategicedge.com/vault"
AUDIT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = AUDIT_ROOT.parents[1]
DEFAULT_UNIVERSE = PROJECT_ROOT / "config" / "final_symbols.csv"
DEFAULT_ALLOWLIST = PROJECT_ROOT / "utils" / "ETF_mappings.py"
DEFAULT_GRAPH = AUDIT_ROOT / "results" / "neo4j_etf_inventory_2026-07-19.json"

MARKET_PROXY_DATASETS = {
    "commodity",
    "currency_index",
    "etf",
    "futures",
    "index",
    "interest_rates",
    "volatility",
}
_KEY_PATTERN = re.compile(r"lse_live_[A-Za-z0-9]+")
_ROLE_ORDER = {"sector": 0, "industry": 1}
_STOP_WORDS = {
    "and",
    "daily",
    "etf",
    "fund",
    "index",
    "invesco",
    "ishare",
    "eck",
    "van",
    "proshare",
    "select",
    "series",
    "share",
    "spdr",
    "state",
    "street",
    "the",
    "trust",
    "vanguard",
    "vaneck",
}


def _symbol(value: object) -> str:
    return str(value or "").strip().upper()


def _catalog_row(row: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "dataset",
        "symbol",
        "name",
        "ticks",
        "first_tick",
        "last_tick",
        "years",
        "last_value",
        "country",
        "country_name",
    )
    return {key: row.get(key) for key in keys if key in row}


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_requirement_rows(
    universe_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return one row per distinct ETF used by current company assignments."""

    inventory: dict[str, dict[str, Any]] = {}
    for row in universe_rows:
        company = _symbol(row.get("symbol"))
        for role, etf_key, group_key in (
            ("sector", "sector_etf", "sector"),
            ("industry", "industry_etf", "industry"),
        ):
            etf = _symbol(row.get(etf_key))
            if not etf:
                continue
            item = inventory.setdefault(
                etf,
                {
                    "symbol": etf,
                    "_companies": set(),
                    "_sector_companies": set(),
                    "_industry_companies": set(),
                    "_roles": set(),
                    "_groups": set(),
                    "_sector_groups": set(),
                    "_industry_groups": set(),
                },
            )
            item["_companies"].add(company)
            item[f"_{role}_companies"].add(company)
            item["_roles"].add(role)
            group = str(row.get(group_key) or "").strip()
            if group:
                item["_groups"].add(group)
                item[f"_{role}_groups"].add(group)

    result: list[dict[str, Any]] = []
    for etf in sorted(inventory):
        item = inventory[etf]
        result.append(
            {
                "symbol": etf,
                "roles": sorted(item["_roles"], key=_ROLE_ORDER.get),
                "csv_company_count": len(item["_companies"]),
                "sector_company_count": len(item["_sector_companies"]),
                "industry_company_count": len(item["_industry_companies"]),
                "groups": sorted(item["_groups"]),
                "sector_groups": sorted(item["_sector_groups"]),
                "industry_groups": sorted(item["_industry_groups"]),
            }
        )
    return result


def company_coverage(
    universe_rows: Iterable[dict[str, Any]], available_etfs: set[str]
) -> dict[str, int]:
    """Count company assignments with each exact benchmark leg available."""

    available = {_symbol(value) for value in available_etfs}
    companies = sector = industry = both = neither = 0
    for row in universe_rows:
        companies += 1
        has_sector = _symbol(row.get("sector_etf")) in available
        has_industry = _symbol(row.get("industry_etf")) in available
        sector += int(has_sector)
        industry += int(has_industry)
        both += int(has_sector and has_industry)
        neither += int(not has_sector and not has_industry)
    return {
        "companies": companies,
        "sector_covered": sector,
        "industry_covered": industry,
        "both_covered": both,
        "neither_covered": neither,
    }


def load_static_allowlist(path: Path) -> set[str]:
    """Read the set literal without importing production code."""

    tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(
            isinstance(target, ast.Name)
            and target.id == "Sector_Industry_ETFs"
            for target in targets
        ):
            continue
        values = ast.literal_eval(node.value)
        return {_symbol(value) for value in values if _symbol(value)}
    raise ValueError(f"Sector_Industry_ETFs was not found in {path}")


def _normalized_symbol(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", _symbol(value))


def classify_catalog_symbol(
    symbol: str, catalog: Iterable[dict[str, Any]]
) -> dict[str, Any]:
    """Classify exact and punctuation-only symbol matches across all datasets."""

    wanted = _symbol(symbol)
    exact = [
        row for row in catalog if _symbol(row.get("symbol")) == wanted
    ]
    aliases = [
        row
        for row in catalog
        if _symbol(row.get("symbol")) != wanted
        and _normalized_symbol(row.get("symbol")) == _normalized_symbol(wanted)
    ]
    etf_rows = [
        row for row in exact if str(row.get("dataset", "")).lower() == "etf"
    ]
    non_etf = [
        row for row in exact if str(row.get("dataset", "")).lower() != "etf"
    ]
    datasets = sorted(
        {str(row.get("dataset", "")).lower() for row in exact if row.get("dataset")}
    )
    return {
        "exact_etf_available": bool(etf_rows),
        "exact_datasets": datasets,
        "exact_etf_rows": [_catalog_row(row) for row in etf_rows],
        "non_etf_exact_matches": [_catalog_row(row) for row in non_etf],
        "options_underlying_available": "options" in datasets,
        "normalized_symbol_aliases": [_catalog_row(row) for row in aliases],
    }


def _stem(token: str) -> str:
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("s") and not token.endswith("ss") and len(token) > 3:
        return token[:-1]
    return token


def _tokens(value: object) -> set[str]:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value or ""))
    words = re.findall(r"[A-Za-z0-9]+", text.lower())
    return {
        stemmed
        for word in words
        if len(stemmed := _stem(word)) > 2 and stemmed not in _STOP_WORDS
    }


def find_name_candidates(
    requirement: dict[str, Any],
    catalog: Iterable[dict[str, Any]],
    *,
    minimum_score: float = 0.25,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Find text-similar market series; these are never called replacements."""

    query_tokens: set[str] = set()
    for group in requirement.get("groups", []):
        query_tokens.update(_tokens(group))
    if not query_tokens:
        return []

    candidates: list[dict[str, Any]] = []
    wanted = _symbol(requirement.get("symbol"))
    for row in catalog:
        dataset = str(row.get("dataset", "")).lower()
        candidate_symbol = _symbol(row.get("symbol"))
        if dataset not in MARKET_PROXY_DATASETS or candidate_symbol == wanted:
            continue
        name_tokens = _tokens(row.get("name"))
        overlap = sorted(query_tokens & name_tokens)
        if not overlap:
            continue
        score = len(overlap) / len(query_tokens | name_tokens)
        if score < minimum_score:
            continue
        candidates.append(
            {
                **_catalog_row(row),
                "name_score": round(score, 4),
                "matched_words": overlap,
                "is_exact_replacement": False,
                "warning": "Text similarity only; holdings and returns were not matched.",
            }
        )

    dataset_order = {"etf": 0, "index": 1, "futures": 2, "commodity": 3}
    candidates.sort(
        key=lambda row: (
            -float(row["name_score"]),
            dataset_order.get(str(row.get("dataset")), 9),
            str(row.get("symbol")),
        )
    )
    return candidates[:limit]


def _redact(value: Any, api_key: str) -> Any:
    if isinstance(value, dict):
        return {str(key): _redact(item, api_key) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item, api_key) for item in value]
    if isinstance(value, str):
        text = value.replace(api_key, "[REDACTED]") if api_key else value
        return _KEY_PATTERN.sub("[REDACTED]", text)
    return value


def api_get(
    api_key: str, path: str, params: dict[str, Any] | None = None
) -> dict[str, Any]:
    query = urllib.parse.urlencode(
        [
            (name, str(value))
            for name, value in (params or {}).items()
            if value is not None
        ]
    )
    url = BASE_URL + path + (f"?{query}" if query else "")
    request = urllib.request.Request(
        url,
        headers={
            "x-api-key": api_key,
            "Accept": "application/json",
            "User-Agent": "EventMarketDB-isolated-etf-audit/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            status = response.status
            raw = response.read().decode("utf-8", "replace")
            headers = {
                key.lower(): value
                for key, value in response.headers.items()
                if key.lower().startswith(("x-data-", "x-rate", "retry-after"))
            }
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read().decode("utf-8", "replace")
        headers = {
            key.lower(): value
            for key, value in exc.headers.items()
            if key.lower().startswith(("x-data-", "x-rate", "retry-after"))
        }
    except OSError as exc:
        return {
            "status": 0,
            "headers": {},
            "body": {"error": _redact(str(exc), api_key)},
        }

    try:
        body: Any = json.loads(raw)
    except json.JSONDecodeError:
        body = {"raw": raw[:500]}
    return {
        "status": status,
        "headers": headers,
        "body": _redact(body, api_key),
    }


def summarize_response(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body")
    summary: dict[str, Any] = {
        "status": response.get("status"),
        "headers": response.get("headers", {}),
        "body_type": type(body).__name__,
    }
    if isinstance(body, list):
        summary["row_count"] = len(body)
        summary["field_names"] = (
            sorted({key for row in body for key in row})
            if body and all(isinstance(row, dict) for row in body)
            else []
        )
        summary["first_rows"] = body[:1]
        summary["last_rows"] = body[-1:] if body else []
    else:
        summary["body"] = body
    return summary


def fetch_live_evidence(
    api_key: str, required_symbols: Sequence[str]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch the catalog and probe every exact ticker with and without ETF pinning."""

    catalog_response = api_get(api_key, "/catalog")
    catalog = catalog_response.get("body")
    if catalog_response.get("status") != 200 or not isinstance(catalog, list):
        raise RuntimeError(
            "LSE catalog request failed: "
            + json.dumps(summarize_response(catalog_response), sort_keys=True)
        )

    discovery = {
        "catalog": {
            "status": 200,
            "row_count": len(catalog),
            "headers": catalog_response.get("headers", {}),
        },
        "usage": api_get(api_key, "/usage"),
        "meta": api_get(api_key, "/meta"),
        "reference": api_get(api_key, "/reference"),
    }
    discovery["usage"] = summarize_response(discovery["usage"])
    discovery["meta"] = summarize_response(discovery["meta"])
    discovery["reference"] = summarize_response(discovery["reference"])

    probes: dict[str, dict[str, Any]] = {
        symbol: {} for symbol in required_symbols
    }

    def candle_probe(
        symbol: str, name: str, params: dict[str, Any]
    ) -> tuple[str, str, dict[str, Any]]:
        response = api_get(
            api_key,
            "/candles",
            {"symbol": symbol, **params},
        )
        return symbol, name, summarize_response(response)

    jobs: list[tuple[str, str, dict[str, Any]]] = []
    for symbol in required_symbols:
        common = {"timeframe": "1d", "order": "desc", "limit": 1}
        jobs.append((symbol, "latest_unpinned", common))
        jobs.append((symbol, "latest_etf_pinned", {**common, "dataset": "etf"}))

    exact_etfs = sorted(
        symbol
        for symbol in required_symbols
        if classify_catalog_symbol(symbol, catalog)["exact_etf_available"]
    )
    for symbol in exact_etfs:
        jobs.append(
            (
                symbol,
                "massive_overlap_daily",
                {
                    "dataset": "etf",
                    "timeframe": "1d",
                    "start": "2026-04-27",
                    "end": "2026-04-29",
                    "order": "asc",
                    "limit": 10,
                },
            )
        )
        jobs.append(
            (
                symbol,
                "latest_minute",
                {
                    "dataset": "etf",
                    "timeframe": "1m",
                    "order": "desc",
                    "limit": 1,
                },
            )
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(candle_probe, symbol, name, params): (symbol, name)
            for symbol, name, params in jobs
        }
        completed = 0
        for future in as_completed(futures):
            symbol, name, result = future.result()
            probes[symbol][name] = result
            completed += 1
            if completed % 20 == 0 or completed == len(futures):
                print(f"LSE candle probes: {completed}/{len(futures)}", flush=True)

    discovery["candle_probes"] = probes
    return catalog, discovery


def _load_graph_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return (
        payload.get("queries", {})
        .get("company_benchmark_assignments", {})
        .get("rows", [])
    )


def _attach_graph_counts(
    requirements: list[dict[str, Any]], graph_rows: list[dict[str, Any]]
) -> None:
    graph_requirements = {
        row["symbol"]: row for row in build_requirement_rows(graph_rows)
    }
    for row in requirements:
        graph = graph_requirements.get(row["symbol"], {})
        row["graph_company_count"] = graph.get("csv_company_count", 0)
        row["graph_sector_company_count"] = graph.get("sector_company_count", 0)
        row["graph_industry_company_count"] = graph.get(
            "industry_company_count", 0
        )


def build_report(
    universe_rows: list[dict[str, Any]],
    catalog: list[dict[str, Any]],
    *,
    graph_rows: list[dict[str, Any]] | None = None,
    allowlist: set[str] | None = None,
    live_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    requirements = build_requirement_rows(universe_rows)
    graph_rows = graph_rows or []
    _attach_graph_counts(requirements, graph_rows)

    probes = (live_evidence or {}).get("candle_probes", {})
    exact_etfs: set[str] = set()
    for row in requirements:
        classification = classify_catalog_symbol(row["symbol"], catalog)
        row["lse"] = classification
        row["name_similarity_candidates"] = find_name_candidates(row, catalog)
        row["api_probes"] = probes.get(row["symbol"], {})
        if classification["exact_etf_available"]:
            exact_etfs.add(row["symbol"])
            row["conclusion"] = "exact LSE ETF available"
        else:
            row["conclusion"] = "required ETF is not available from LSE"

    sector_required = {
        row["symbol"] for row in requirements if "sector" in row["roles"]
    }
    industry_required = {
        row["symbol"] for row in requirements if "industry" in row["roles"]
    }
    graph_symbols = {_symbol(row.get("symbol")) for row in graph_rows}
    csv_symbols = {_symbol(row.get("symbol")) for row in universe_rows}

    allowlist = allowlist or set()
    active_required = sector_required | industry_required
    allowlist_exact = allowlist & {
        _symbol(row.get("symbol"))
        for row in catalog
        if str(row.get("dataset", "")).lower() == "etf"
    }
    category_counts = Counter(
        str(row.get("dataset", "")) for row in catalog if row.get("dataset")
    )
    lse_etf_rows = sorted(
        (
            _catalog_row(row)
            for row in catalog
            if str(row.get("dataset", "")).lower() == "etf"
        ),
        key=lambda row: str(row.get("symbol")),
    )
    reference_names = (
        (live_evidence or {})
        .get("meta", {})
        .get("body", {})
        .get("reference", [])
    )
    has_etf_holdings = any(
        "holding" in str(name).lower() for name in reference_names
    )

    report: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "safety": {
            "production_code_changed": False,
            "database_access": "Neo4j evidence came from a separate read-only snapshot.",
            "credentials_written": False,
        },
        "production_sources": {
            "current_universe": "config/final_symbols.csv",
            "static_etf_allowlist": "utils/ETF_mappings.py",
            "runtime_mapping_path": [
                "Redis stock universe",
                "EventReturnsManager._get_etf",
                "Polygon.get_event_returns",
            ],
            "calculation_legs": [
                "stock",
                "sector ETF",
                "industry ETF",
                "SPY",
            ],
        },
        "summary": {
            "csv_companies": len(universe_rows),
            "graph_companies": len(graph_rows),
            "graph_only_companies": sorted(graph_symbols - csv_symbols),
            "required_distinct_etfs": len(active_required),
            "sector_etfs": {
                "required": len(sector_required),
                "exact_lse": len(sector_required & exact_etfs),
                "symbols": sorted(sector_required & exact_etfs),
            },
            "industry_etfs": {
                "required": len(industry_required),
                "exact_lse": len(industry_required & exact_etfs),
                "symbols": sorted(industry_required & exact_etfs),
            },
            "all_required_etfs": {
                "required": len(active_required),
                "exact_lse": len(exact_etfs),
                "missing": len(active_required - exact_etfs),
                "exact_symbols": sorted(exact_etfs),
                "missing_symbols": sorted(active_required - exact_etfs),
            },
            "csv_company_coverage": company_coverage(
                universe_rows, exact_etfs
            ),
            "graph_company_coverage": company_coverage(
                graph_rows, exact_etfs
            ),
            "bottom_line": (
                "LSE cannot replace the production sector/industry benchmark "
                "feed exactly because most required ETFs are absent."
            ),
        },
        "static_allowlist_check": {
            "symbols": sorted(allowlist),
            "count": len(allowlist),
            "active_required_missing_from_allowlist": sorted(
                active_required - allowlist
            ),
            "allowlist_not_active_in_current_universe": sorted(
                allowlist - active_required
            ),
            "exact_lse_count": len(allowlist_exact),
            "exact_lse_symbols": sorted(allowlist_exact),
        },
        "lse_catalog": {
            "source": f"{BASE_URL}/catalog",
            "total_rows": len(catalog),
            "category_counts": dict(sorted(category_counts.items())),
            "etf_count": len(lse_etf_rows),
            "etfs": lse_etf_rows,
            "reference_datasets": reference_names,
            "reference_data_has_etf_holdings": has_etf_holdings,
            "reference_data_note": (
                (
                    "An ETF holdings-like reference dataset is listed and "
                    "requires a separate exact reconstruction test."
                )
                if has_etf_holdings
                else (
                    "LSE metadata lists no ETF holdings or weights dataset, so "
                    "missing ETFs cannot be reconstructed exactly from provider "
                    "reference data."
                )
            ),
        },
        "requirements": requirements,
    }
    if live_evidence:
        report["live_api_evidence"] = live_evidence
    return report


def write_requirement_csv(path: Path, report: dict[str, Any]) -> None:
    fields = [
        "symbol",
        "roles",
        "groups",
        "csv_company_count",
        "graph_company_count",
        "sector_company_count",
        "industry_company_count",
        "exact_lse_etf",
        "exact_lse_datasets",
        "first_tick",
        "last_tick",
        "ticks",
        "unpinned_status",
        "unpinned_rows",
        "etf_pinned_status",
        "etf_pinned_rows",
        "conclusion",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for requirement in report["requirements"]:
            lse = requirement["lse"]
            etf_row = (lse.get("exact_etf_rows") or [{}])[0]
            probes = requirement.get("api_probes", {})
            unpinned = probes.get("latest_unpinned", {})
            pinned = probes.get("latest_etf_pinned", {})
            writer.writerow(
                {
                    "symbol": requirement["symbol"],
                    "roles": "|".join(requirement["roles"]),
                    "groups": "|".join(requirement["groups"]),
                    "csv_company_count": requirement["csv_company_count"],
                    "graph_company_count": requirement["graph_company_count"],
                    "sector_company_count": requirement[
                        "sector_company_count"
                    ],
                    "industry_company_count": requirement[
                        "industry_company_count"
                    ],
                    "exact_lse_etf": lse["exact_etf_available"],
                    "exact_lse_datasets": "|".join(lse["exact_datasets"]),
                    "first_tick": etf_row.get("first_tick", ""),
                    "last_tick": etf_row.get("last_tick", ""),
                    "ticks": etf_row.get("ticks", ""),
                    "unpinned_status": unpinned.get("status", ""),
                    "unpinned_rows": unpinned.get("row_count", ""),
                    "etf_pinned_status": pinned.get("status", ""),
                    "etf_pinned_rows": pinned.get("row_count", ""),
                    "conclusion": requirement["conclusion"],
                }
            )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", type=Path, default=DEFAULT_UNIVERSE)
    parser.add_argument("--allowlist", type=Path, default=DEFAULT_ALLOWLIST)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--catalog-json", type=Path)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    universe_rows = read_csv_rows(args.universe)
    graph_rows = _load_graph_rows(args.graph)
    allowlist = load_static_allowlist(args.allowlist)

    live_evidence = None
    if args.live:
        api_key = os.environ.get("LSE_API_KEY", "")
        if not api_key:
            raise SystemExit("LSE_API_KEY is required for --live")
        required = [
            row["symbol"] for row in build_requirement_rows(universe_rows)
        ]
        catalog, live_evidence = fetch_live_evidence(api_key, required)
    else:
        if not args.catalog_json:
            raise SystemExit("--catalog-json is required unless --live is used")
        catalog = json.loads(args.catalog_json.read_text(encoding="utf-8"))
        if not isinstance(catalog, list):
            raise SystemExit("catalog JSON must be a list")

    report = build_report(
        universe_rows,
        catalog,
        graph_rows=graph_rows,
        allowlist=allowlist,
        live_evidence=live_evidence,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_requirement_csv(args.output_csv, report)

    summary = report["summary"]
    print(
        "exact LSE ETF coverage: "
        f"{summary['all_required_etfs']['exact_lse']}/"
        f"{summary['all_required_etfs']['required']}"
    )
    print(f"saved: {args.output_json}")
    print(f"saved: {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
