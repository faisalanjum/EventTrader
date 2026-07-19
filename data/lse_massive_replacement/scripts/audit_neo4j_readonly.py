#!/usr/bin/env python3
"""Read-only inventory of Massive-derived data stored in Neo4j.

This script never submits a write query. It opens a READ_ACCESS session and
uses execute_read for every query. Credentials are read from the environment
and are never included in the output.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase, READ_ACCESS


RETURN_KEYS = [
    "hourly_stock",
    "session_stock",
    "daily_stock",
    "hourly_sector",
    "session_sector",
    "daily_sector",
    "hourly_industry",
    "session_industry",
    "daily_industry",
    "hourly_macro",
    "session_macro",
    "daily_macro",
]


QUERIES: dict[str, tuple[str, dict[str, Any]]] = {
    "server": (
        """
        CALL dbms.components()
        YIELD name, versions, edition
        RETURN name, versions, edition
        """,
        {},
    ),
    "relevant_node_counts": (
        """
        CALL { MATCH (n:Company) RETURN count(n) AS companies }
        CALL { MATCH (n:Sector) RETURN count(n) AS sectors }
        CALL { MATCH (n:Industry) RETURN count(n) AS industries }
        CALL { MATCH (n:MarketIndex) RETURN count(n) AS market_indexes }
        CALL { MATCH (n:Date) RETURN count(n) AS dates }
        CALL { MATCH (n:Dividend) RETURN count(n) AS dividends }
        CALL { MATCH (n:Split) RETURN count(n) AS splits }
        CALL { MATCH (n:RiskCategory) RETURN count(n) AS risk_categories }
        CALL { MATCH (n:RiskClassification) RETURN count(n) AS risk_classifications }
        RETURN *
        """,
        {},
    ),
    "has_price_summary": (
        """
        MATCH (d:Date)-[r:HAS_PRICE]->(e)
        RETURN count(r) AS relationships,
               count(DISTINCT d) AS dates_with_prices,
               min(d.date) AS first_date,
               max(d.date) AS last_date,
               count(DISTINCT coalesce(e.ticker, e.etf, e.id)) AS distinct_symbols
        """,
        {},
    ),
    "has_price_by_target_label": (
        """
        MATCH (:Date)-[r:HAS_PRICE]->(e)
        UNWIND labels(e) AS target_label
        WITH target_label, r
        WHERE target_label IN ['Company', 'Sector', 'Industry', 'MarketIndex']
        RETURN target_label,
               count(r) AS relationships,
               count(r.open) AS open,
               count(r.high) AS high,
               count(r.low) AS low,
               count(r.close) AS close,
               count(r.volume) AS volume,
               count(r.vwap) AS vwap,
               count(r.transactions) AS transactions,
               count(r.timestamp) AS timestamp,
               count(r.daily_return) AS daily_return
        ORDER BY target_label
        """,
        {},
    ),
    "has_price_property_inventory": (
        """
        MATCH ()-[r:HAS_PRICE]->()
        UNWIND keys(r) AS property
        RETURN property, count(*) AS relationships
        ORDER BY property
        """,
        {},
    ),
    "has_price_symbols": (
        """
        MATCH (:Date)-[:HAS_PRICE]->(e)
        WITH labels(e) AS labels,
             coalesce(e.ticker, e.etf, e.id) AS symbol,
             count(*) AS dates
        RETURN labels, symbol, dates
        ORDER BY labels, symbol
        """,
        {},
    ),
    "event_return_locations": (
        """
        CALL {
          MATCH (source)-[r:INFLUENCES]->(target)
          RETURN source, r, target
          UNION ALL
          MATCH (source)-[r:PRIMARY_FILER]->(target)
          RETURN source, r, target
          UNION ALL
          MATCH (source)-[r:REFERENCED_IN]->(target)
          RETURN source, r, target
        }
        WITH source, r, target
        WHERE any(k IN $return_keys WHERE r[k] IS NOT NULL)
        RETURN labels(source) AS source_labels,
               type(r) AS relationship_type,
               labels(target) AS target_labels,
               count(r) AS relationships,
               count(r.hourly_stock) AS hourly_stock,
               count(r.session_stock) AS session_stock,
               count(r.daily_stock) AS daily_stock,
               count(r.hourly_sector) AS hourly_sector,
               count(r.session_sector) AS session_sector,
               count(r.daily_sector) AS daily_sector,
               count(r.hourly_industry) AS hourly_industry,
               count(r.session_industry) AS session_industry,
               count(r.daily_industry) AS daily_industry,
               count(r.hourly_macro) AS hourly_macro,
               count(r.session_macro) AS session_macro,
               count(r.daily_macro) AS daily_macro,
               min(toString(r.created_at)) AS first_relationship_created_at,
               max(toString(r.created_at)) AS last_relationship_created_at
        ORDER BY source_labels, relationship_type, target_labels
        """,
        {"return_keys": RETURN_KEYS},
    ),
    "event_return_property_inventory": (
        """
        CALL {
          MATCH ()-[r:INFLUENCES]->() RETURN r
          UNION ALL
          MATCH ()-[r:PRIMARY_FILER]->() RETURN r
          UNION ALL
          MATCH ()-[r:REFERENCED_IN]->() RETURN r
        }
        WITH r
        WHERE any(k IN $return_keys WHERE r[k] IS NOT NULL)
        UNWIND [k IN keys(r) WHERE k IN $return_keys] AS property
        RETURN type(r) AS relationship_type, property, count(*) AS relationships
        ORDER BY relationship_type, property
        """,
        {"return_keys": RETURN_KEYS},
    ),
    "event_return_source_span": (
        """
        CALL {
          MATCH (source)-[r:INFLUENCES]->(target:Company)
          RETURN source, r, target
          UNION ALL
          MATCH (source)-[r:PRIMARY_FILER]->(target:Company)
          RETURN source, r, target
          UNION ALL
          MATCH (source)-[r:REFERENCED_IN]->(target:Company)
          RETURN source, r, target
        }
        WITH source, r, target
        WHERE any(k IN $return_keys WHERE r[k] IS NOT NULL)
        RETURN labels(source) AS source_labels,
               type(r) AS relationship_type,
               count(r) AS relationships,
               min(toString(coalesce(source.created, source.published,
                                     source.updated, source.date))) AS first_source_time,
               max(toString(coalesce(source.created, source.published,
                                     source.updated, source.date))) AS last_source_time
        ORDER BY source_labels, relationship_type
        """,
        {"return_keys": RETURN_KEYS},
    ),
    "dividend_summary": (
        """
        MATCH (n:Dividend)
        RETURN count(n) AS nodes,
               count(DISTINCT n.ticker) AS tickers,
               min(n.declaration_date) AS first_declaration_date,
               max(n.declaration_date) AS last_declaration_date,
               count(n.cash_amount) AS cash_amount,
               count(n.ex_dividend_date) AS ex_dividend_date,
               count(n.dividend_type) AS dividend_type,
               count(n.currency) AS currency,
               count(n.frequency) AS frequency,
               count(n.pay_date) AS pay_date,
               count(n.record_date) AS record_date
        """,
        {},
    ),
    "dividend_relationships": (
        """
        MATCH ()-[r]->(n:Dividend)
        RETURN type(r) AS relationship_type,
               labels(startNode(r)) AS source_labels,
               count(r) AS relationships
        ORDER BY relationship_type, source_labels
        """,
        {},
    ),
    "split_summary": (
        """
        MATCH (n:Split)
        RETURN count(n) AS nodes,
               count(DISTINCT n.ticker) AS tickers,
               min(n.execution_date) AS first_execution_date,
               max(n.execution_date) AS last_execution_date,
               count(n.split_from) AS split_from,
               count(n.split_to) AS split_to
        """,
        {},
    ),
    "split_relationships": (
        """
        MATCH ()-[r]->(n:Split)
        RETURN type(r) AS relationship_type,
               labels(startNode(r)) AS source_labels,
               count(r) AS relationships
        ORDER BY relationship_type, source_labels
        """,
        {},
    ),
    "massive_risk_factor_summary": (
        """
        MATCH (n:RiskClassification)
        RETURN count(n) AS nodes,
               count(DISTINCT n.ticker) AS tickers,
               min(n.filing_date) AS first_filing_date,
               max(n.filing_date) AS last_filing_date,
               n.source AS source,
               count(n.supporting_text) AS supporting_text,
               count(n.embedding) AS embeddings
        ORDER BY source
        """,
        {},
    ),
    "massive_risk_factor_relationships": (
        """
        MATCH (a)-[r]->(b)
        WHERE a:RiskClassification OR b:RiskClassification
              OR a:RiskCategory OR b:RiskCategory
        RETURN labels(a) AS source_labels,
               type(r) AS relationship_type,
               labels(b) AS target_labels,
               count(r) AS relationships
        ORDER BY source_labels, relationship_type, target_labels
        """,
        {},
    ),
    "schema_relationship_properties": (
        """
        CALL db.schema.relTypeProperties()
        YIELD relType, propertyName, propertyTypes, mandatory
        WHERE propertyName IN $properties
        RETURN relType, propertyName, propertyTypes, mandatory
        ORDER BY relType, propertyName
        """,
        {
            "properties": RETURN_KEYS
            + [
                "open",
                "high",
                "low",
                "close",
                "volume",
                "vwap",
                "transactions",
                "timestamp",
                "daily_return",
            ]
        },
    ),
}


def json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    return value


def run_query(tx, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    return [json_safe(record.data()) for record in tx.run(query, params)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    uri = os.environ.get("NEO4J_URI")
    username = os.environ.get("NEO4J_USERNAME")
    password = os.environ.get("NEO4J_PASSWORD")
    if not all((uri, username, password)):
        raise SystemExit("NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD are required")

    audit: dict[str, Any] = {
        "safety": "All queries used Neo4j READ_ACCESS and execute_read.",
        "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "queries": {},
    }

    def save_checkpoint() -> None:
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(audit, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

    driver = GraphDatabase.driver(uri, auth=(username, password))
    try:
        driver.verify_connectivity()
        with driver.session(default_access_mode=READ_ACCESS) as session:
            for name, (query, params) in QUERIES.items():
                try:
                    rows = session.execute_read(run_query, query, params)
                    audit["queries"][name] = {"ok": True, "rows": rows}
                    print(f"{name}: {len(rows)} row(s)", flush=True)
                except Exception as exc:
                    audit["queries"][name] = {
                        "ok": False,
                        "error_type": type(exc).__name__,
                        "error": str(exc)[:500],
                    }
                    print(f"{name}: ERROR {type(exc).__name__}", flush=True)
                save_checkpoint()
    finally:
        driver.close()

    text = json.dumps(audit, indent=2, sort_keys=True)
    if args.output:
        save_checkpoint()
        print(f"saved: {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
