#!/usr/bin/env python3
"""Compare LSE corporate actions with Massive-derived Neo4j records.

Safety:
- Neo4j is queried only through READ_ACCESS and execute_read.
- LSE is accessed only with GET requests.
- The LSE key is read from a hidden prompt and is never saved or printed.
- API responses are cached only after headers and credentials are discarded.
"""

from __future__ import annotations

import argparse
import getpass
import gzip
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

from neo4j import GraphDatabase, READ_ACCESS


BASE_URL = "https://api.londonstrategicedge.com/vault"
USER_AGENT = "EventMarketDB-isolated-replacement-audit/1.0"

TYPE_MAP = {
    "CD": "Regular",
    "SC": "Special",
    "LT": "LongTermGain",
    "ST": "ShortTermGain",
}
FREQUENCY_MAP = {
    "0": "OneTime",
    "1": "Annual",
    "2": "BiAnnual",
    "4": "Quarterly",
    "12": "Monthly",
    "24": "BiMonthly",
    "52": "Weekly",
}


def json_safe(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    return value


def neo4j_rows(tx, query: str) -> list[dict[str, Any]]:
    return [json_safe(record.data()) for record in tx.run(query)]


def read_graph_actions() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    uri = os.environ.get("NEO4J_URI")
    username = os.environ.get("NEO4J_USERNAME")
    password = os.environ.get("NEO4J_PASSWORD")
    if not all((uri, username, password)):
        raise RuntimeError("Neo4j environment variables are required")

    dividend_query = """
    MATCH (d:Dividend)
    RETURN d.ticker AS ticker,
           toString(d.declaration_date) AS declaration_date,
           d.cash_amount AS cash_amount,
           d.currency AS currency,
           d.dividend_type AS dividend_type,
           toString(d.ex_dividend_date) AS ex_dividend_date,
           d.frequency AS frequency,
           toString(d.pay_date) AS pay_date,
           toString(d.record_date) AS record_date
    ORDER BY ticker, declaration_date, cash_amount
    """
    split_query = """
    MATCH (s:Split)
    RETURN s.ticker AS ticker,
           toString(s.execution_date) AS execution_date,
           s.split_from AS split_from,
           s.split_to AS split_to
    ORDER BY ticker, execution_date, split_from, split_to
    """

    driver = GraphDatabase.driver(uri, auth=(username, password))
    try:
        driver.verify_connectivity()
        with driver.session(default_access_mode=READ_ACCESS) as session:
            dividends = session.execute_read(neo4j_rows, dividend_query)
            splits = session.execute_read(neo4j_rows, split_query)
    finally:
        driver.close()
    return dividends, splits


def read_cache(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, list):
        raise RuntimeError(f"Invalid cache shape: {path}")
    return value


def write_cache(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wt", encoding="utf-8") as handle:
        json.dump(rows, handle, separators=(",", ":"))
    os.replace(temporary, path)


def fetch_reference_rows(
    key: str,
    dataset: str,
    symbol: str,
    cache_dir: Path,
    *,
    minimum_interval: float,
) -> list[dict[str, Any]]:
    cache = cache_dir / dataset / f"{symbol}.json.gz"
    if cache.exists():
        return read_cache(cache)

    params = urllib.parse.urlencode(
        {
            "symbol": symbol,
            "order": "asc",
            "limit": 5000,
        }
    )
    url = f"{BASE_URL}/ref/{dataset}?{params}"
    last_error = ""
    for attempt in range(1, 6):
        started = time.monotonic()
        request = urllib.request.Request(
            url,
            headers={
                "x-api-key": key,
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                raw = response.read()
            rows = json.loads(raw.decode("utf-8"))
            if not isinstance(rows, list):
                raise RuntimeError(
                    f"{dataset}/{symbol} returned {type(rows).__name__}"
                )
            write_cache(cache, rows)
            elapsed = time.monotonic() - started
            if elapsed < minimum_interval:
                time.sleep(minimum_interval - elapsed)
            return rows
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:300]
            last_error = f"HTTP {exc.code}: {body}"
            if exc.code == 404:
                write_cache(cache, [])
                return []
            if exc.code != 429 or attempt == 5:
                break
            retry_after = exc.headers.get("retry-after")
            time.sleep(float(retry_after) if retry_after else attempt * 2)
        except (OSError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt == 5:
                break
            time.sleep(attempt)
    raise RuntimeError(f"LSE {dataset}/{symbol} failed: {last_error}")


def decimal_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    try:
        converted = Decimal(text).normalize()
    except InvalidOperation:
        return text
    return format(converted, "f")


def normalized_type(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return TYPE_MAP.get(text, text)


def normalized_frequency(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return FREQUENCY_MAP.get(text, text)


def dividend_core(row: dict[str, Any], source: str) -> tuple[str, str, str]:
    return (
        str(row["ticker"] if source == "graph" else row["symbol"]),
        str(row["declaration_date"]),
        decimal_text(
            row["cash_amount"] if source == "graph" else row["dividend_amount"]
        )
        or "",
    )


def dividend_production_id(
    row: dict[str, Any],
    source: str,
) -> tuple[str, str, str]:
    ticker = str(row["ticker"] if source == "graph" else row["symbol"])
    declaration_date = str(row["declaration_date"])
    dividend_type = normalized_type(row.get("dividend_type")) or "UNKNOWN"
    return ticker, declaration_date, dividend_type


def normalized_dividend_payload(
    row: dict[str, Any],
    source: str,
) -> tuple[str | None, ...]:
    if source == "graph":
        cash = row.get("cash_amount")
        ex_date = row.get("ex_dividend_date")
        pay_date = row.get("pay_date")
    else:
        cash = row.get("dividend_amount")
        ex_date = row.get("effective_date")
        pay_date = row.get("payment_date")
    return (
        decimal_text(cash),
        str(row.get("currency") or "").upper() or None,
        str(ex_date) if ex_date is not None else None,
        normalized_frequency(row.get("frequency")),
        str(pay_date) if pay_date is not None else None,
        str(row.get("record_date"))
        if row.get("record_date") is not None
        else None,
    )


def split_core(row: dict[str, Any], source: str) -> tuple[str, str, str, str]:
    return (
        str(row["ticker"] if source == "graph" else row["symbol"]),
        str(
            row["execution_date"]
            if source == "graph"
            else row["effective_date"]
        ),
        decimal_text(row["split_from"]) or "",
        decimal_text(row["split_to"]) or "",
    )


def matched_field_counts(
    graph_rows: Iterable[dict[str, Any]],
    lse_rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    graph_by_core: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    lse_by_core: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in graph_rows:
        graph_by_core[dividend_core(row, "graph")].append(row)
    for row in lse_rows:
        if all(
            row.get(field) is not None
            for field in ("symbol", "declaration_date", "dividend_amount")
        ):
            lse_by_core[dividend_core(row, "lse")].append(row)

    comparisons: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for core in graph_by_core.keys() & lse_by_core.keys():
        graph_group = graph_by_core[core]
        lse_group = lse_by_core[core]
        for graph_row, lse_row in zip(graph_group, lse_group):
            comparisons.append((graph_row, lse_row))

    field_rules = {
        "currency": lambda g, l: (
            str(g.get("currency") or "").upper()
            == str(l.get("currency") or "").upper()
        ),
        "dividend_type": lambda g, l: (
            normalized_type(g.get("dividend_type"))
            == normalized_type(l.get("dividend_type"))
        ),
        "ex_dividend_date": lambda g, l: (
            str(g.get("ex_dividend_date"))
            == str(l.get("effective_date"))
        ),
        "frequency": lambda g, l: (
            normalized_frequency(g.get("frequency"))
            == normalized_frequency(l.get("frequency"))
        ),
        "pay_date": lambda g, l: (
            str(g.get("pay_date")) == str(l.get("payment_date"))
        ),
        "record_date": lambda g, l: (
            str(g.get("record_date")) == str(l.get("record_date"))
        ),
    }
    return {
        "paired_core_rows": len(comparisons),
        "field_exact_after_normalization": {
            field: sum(rule(graph, lse) for graph, lse in comparisons)
            for field, rule in field_rules.items()
        },
    }


def multiset_summary(
    graph_rows: list[dict[str, Any]],
    lse_rows: list[dict[str, Any]],
    core_function,
) -> dict[str, Any]:
    graph_counter = Counter(core_function(row, "graph") for row in graph_rows)
    lse_counter = Counter(core_function(row, "lse") for row in lse_rows)
    matched = graph_counter & lse_counter
    missing = graph_counter - lse_counter
    extra = lse_counter - graph_counter
    return {
        "graph_rows": sum(graph_counter.values()),
        "lse_rows": sum(lse_counter.values()),
        "graph_unique_keys": len(graph_counter),
        "lse_unique_keys": len(lse_counter),
        "matched_unique_keys": len(graph_counter.keys() & lse_counter.keys()),
        "graph_missing_unique_keys": len(
            graph_counter.keys() - lse_counter.keys()
        ),
        "lse_extra_unique_keys": len(lse_counter.keys() - graph_counter.keys()),
        "matched_rows": sum(matched.values()),
        "graph_missing_rows": sum(missing.values()),
        "lse_extra_rows": sum(extra.values()),
        "graph_match_rate_percent": round(
            sum(matched.values()) / sum(graph_counter.values()) * 100, 4
        )
        if graph_counter
        else None,
        "missing_examples": [
            {"key": list(core), "count": count}
            for core, count in missing.most_common(30)
        ],
        "extra_examples": [
            {"key": list(core), "count": count}
            for core, count in extra.most_common(30)
        ],
    }


def dividend_production_id_summary(
    graph_rows: list[dict[str, Any]],
    lse_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    graph_by_id: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    lse_by_id: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in graph_rows:
        graph_by_id[dividend_production_id(row, "graph")].append(row)
    for row in lse_rows:
        if row.get("symbol") and row.get("declaration_date"):
            lse_by_id[dividend_production_id(row, "lse")].append(row)

    overlap = graph_by_id.keys() & lse_by_id.keys()
    duplicate_groups = {
        identifier: rows
        for identifier, rows in lse_by_id.items()
        if len(rows) > 1
    }
    conflicting_duplicate_groups = {
        identifier: rows
        for identifier, rows in duplicate_groups.items()
        if len(
            {
                normalized_dividend_payload(row, "lse")
                for row in rows
            }
        )
        > 1
    }

    payload_any_match = 0
    cash_any_match = 0
    field_any_match = Counter()
    fields = (
        "cash_amount",
        "currency",
        "ex_dividend_date",
        "frequency",
        "pay_date",
        "record_date",
    )
    for identifier in overlap:
        graph_payloads = {
            normalized_dividend_payload(row, "graph")
            for row in graph_by_id[identifier]
        }
        lse_payloads = {
            normalized_dividend_payload(row, "lse")
            for row in lse_by_id[identifier]
        }
        if graph_payloads & lse_payloads:
            payload_any_match += 1
        if any(
            graph_payload[0] == lse_payload[0]
            for graph_payload in graph_payloads
            for lse_payload in lse_payloads
        ):
            cash_any_match += 1
        for index, field in enumerate(fields):
            if any(
                graph_payload[index] == lse_payload[index]
                for graph_payload in graph_payloads
                for lse_payload in lse_payloads
            ):
                field_any_match[field] += 1

    missing_ids = graph_by_id.keys() - lse_by_id.keys()
    extra_ids = lse_by_id.keys() - graph_by_id.keys()
    return {
        "rule": (
            "Production Dividend node ID is ticker + declaration_date + "
            "normalized dividend_type; cash amount is a property, not part "
            "of the ID."
        ),
        "graph_unique_ids": len(graph_by_id),
        "lse_unique_ids": len(lse_by_id),
        "overlap_ids": len(overlap),
        "graph_missing_ids": len(missing_ids),
        "lse_extra_ids": len(extra_ids),
        "ids_with_any_exact_full_payload": payload_any_match,
        "ids_with_any_exact_cash_amount": cash_any_match,
        "field_any_exact_after_normalization": {
            field: field_any_match[field] for field in fields
        },
        "lse_duplicate_rows_beyond_one_per_id": sum(
            len(rows) - 1 for rows in duplicate_groups.values()
        ),
        "lse_duplicate_ids": len(duplicate_groups),
        "lse_conflicting_duplicate_ids": len(conflicting_duplicate_groups),
        "missing_id_examples": [
            list(identifier) for identifier in sorted(missing_ids)[:30]
        ],
        "conflicting_duplicate_examples": [
            {
                "id": list(identifier),
                "payloads": [
                    list(payload)
                    for payload in sorted(
                        {
                            normalized_dividend_payload(row, "lse")
                            for row in rows
                        },
                        key=str,
                    )
                ],
            }
            for identifier, rows in list(
                sorted(conflicting_duplicate_groups.items())
            )[:20]
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minimum-interval", type=float, default=0.34)
    args = parser.parse_args()

    key = os.environ.get("LSE_API_KEY") or getpass.getpass("LSE API key: ")
    if not key:
        raise SystemExit("No LSE API key supplied")

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    lse_stocks = {
        str(row["symbol"])
        for row in catalog
        if row.get("dataset") == "stocks" and row.get("symbol")
    }
    graph_dividends, graph_splits = read_graph_actions()
    dividend_symbols = sorted(
        {str(row["ticker"]) for row in graph_dividends} & lse_stocks
    )
    split_symbols = sorted(
        {str(row["ticker"]) for row in graph_splits} & lse_stocks
    )

    lse_dividends: list[dict[str, Any]] = []
    lse_splits: list[dict[str, Any]] = []
    truncated: list[str] = []
    errors: dict[str, str] = {}

    total_calls = len(dividend_symbols) + len(split_symbols)
    completed = 0
    for dataset, symbols, destination in (
        ("dividends", dividend_symbols, lse_dividends),
        ("stock_splits", split_symbols, lse_splits),
    ):
        for symbol in symbols:
            try:
                rows = fetch_reference_rows(
                    key,
                    dataset,
                    symbol,
                    args.cache_dir,
                    minimum_interval=args.minimum_interval,
                )
                destination.extend(rows)
                if len(rows) == 5000:
                    truncated.append(f"{dataset}:{symbol}")
            except Exception as exc:
                errors[f"{dataset}:{symbol}"] = str(exc)[:500]
            completed += 1
            if completed % 25 == 0 or completed == total_calls:
                print(
                    f"corporate actions: {completed}/{total_calls} symbols",
                    flush=True,
                )

    graph_dividends_supported = [
        row for row in graph_dividends if row["ticker"] in lse_stocks
    ]
    graph_splits_supported = [
        row for row in graph_splits if row["ticker"] in lse_stocks
    ]

    declaration_dates = [
        row["declaration_date"] for row in graph_dividends_supported
        if row.get("declaration_date")
    ]
    if declaration_dates:
        first_declaration = min(declaration_dates)
        last_declaration = max(declaration_dates)
        lse_dividends_in_span = [
            row
            for row in lse_dividends
            if first_declaration
            <= str(row.get("declaration_date", ""))
            <= last_declaration
        ]
    else:
        first_declaration = last_declaration = None
        lse_dividends_in_span = []

    execution_dates = [
        row["execution_date"] for row in graph_splits_supported
        if row.get("execution_date")
    ]
    if execution_dates:
        first_execution = min(execution_dates)
        last_execution = max(execution_dates)
        lse_splits_in_span = [
            row
            for row in lse_splits
            if first_execution
            <= str(row.get("effective_date", ""))
            <= last_execution
        ]
    else:
        first_execution = last_execution = None
        lse_splits_in_span = []

    dividend_summary = multiset_summary(
        graph_dividends_supported,
        lse_dividends_in_span,
        dividend_core,
    )
    dividend_summary.update(
        matched_field_counts(
            graph_dividends_supported, lse_dividends_in_span
        )
    )
    dividend_summary["production_node_id_comparison"] = (
        dividend_production_id_summary(
            graph_dividends_supported, lse_dividends_in_span
        )
    )
    dividend_summary.update(
        {
            "graph_total_all_symbols": len(graph_dividends),
            "graph_rows_on_lse_symbols": len(graph_dividends_supported),
            "graph_rows_on_missing_lse_symbols": (
                len(graph_dividends) - len(graph_dividends_supported)
            ),
            "graph_span": [first_declaration, last_declaration],
            "symbols_requested": len(dividend_symbols),
        }
    )

    split_summary = multiset_summary(
        graph_splits_supported,
        lse_splits_in_span,
        split_core,
    )
    split_summary.update(
        {
            "graph_total_all_symbols": len(graph_splits),
            "graph_rows_on_lse_symbols": len(graph_splits_supported),
            "graph_rows_on_missing_lse_symbols": (
                len(graph_splits) - len(graph_splits_supported)
            ),
            "graph_span": [first_execution, last_execution],
            "symbols_requested": len(split_symbols),
        }
    )

    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "safety": (
            "Neo4j READ_ACCESS/execute_read and LSE GET requests only. "
            "No key was printed or saved; no production data was changed."
        ),
        "method": {
            "dividend_core": [
                "ticker/symbol",
                "declaration_date",
                "cash_amount/dividend_amount",
            ],
            "split_core": [
                "ticker/symbol",
                "execution_date/effective_date",
                "split_from",
                "split_to",
            ],
            "comparison_scope": (
                "Graph records whose ticker exists in the LSE stock catalog; "
                "LSE rows locally restricted to the graph date span."
            ),
        },
        "dividends": dividend_summary,
        "splits": split_summary,
        "truncated_symbol_endpoints": truncated,
        "errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.output)
    print(f"saved: {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
