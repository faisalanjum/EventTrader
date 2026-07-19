#!/usr/bin/env python3
"""Find dense, stored Massive event-return cases for isolated LSE tests.

Every Neo4j query is submitted through a READ_ACCESS session and execute_read.
The output contains market data and event identifiers only; credentials are
read from the environment and are never written.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase, READ_ACCESS


def json_safe(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    return value


def rows(tx, query: str, **params: Any) -> list[dict[str, Any]]:
    return [json_safe(record.data()) for record in tx.run(query, **params)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument(
        "--case",
        action="append",
        default=[],
        help="Optional TICKER:YYYY-MM-DD case; may be repeated.",
    )
    args = parser.parse_args()

    uri = os.environ.get("NEO4J_URI")
    username = os.environ.get("NEO4J_USERNAME")
    password = os.environ.get("NEO4J_PASSWORD")
    if not all((uri, username, password)):
        raise SystemExit("Neo4j environment variables are required")

    shape_query = """
    MATCH (n:News)-[r:INFLUENCES]->(c:Company)
    WHERE r.hourly_stock IS NOT NULL
    RETURN keys(n) AS news_fields,
           keys(r) AS relationship_fields,
           keys(c) AS company_fields,
           n.id AS event_id,
           toString(n.created) AS news_created,
           toString(r.created_at) AS relationship_created,
           c.ticker AS ticker,
           c.sector_etf AS sector_etf,
           c.industry_etf AS industry_etf,
           r.hourly_stock AS hourly_stock,
           r.session_stock AS session_stock,
           r.daily_stock AS daily_stock
    LIMIT 5
    """

    dense_query = """
    MATCH (n:News)-[r:INFLUENCES]->(c:Company)
    WHERE r.hourly_stock IS NOT NULL
      AND n.created IS NOT NULL
    WITH c.ticker AS ticker,
         substring(toString(n.created), 0, 10) AS day,
         count(*) AS events,
         collect({
           event_id: n.id,
           created: toString(n.created),
           hourly_stock: r.hourly_stock,
           session_stock: r.session_stock,
           daily_stock: r.daily_stock,
           hourly_macro: r.hourly_macro,
           session_macro: r.session_macro,
           daily_macro: r.daily_macro,
           sector_etf: c.sector_etf,
           industry_etf: c.industry_etf
         })[0..20] AS samples
    WHERE day >= '2023-01-03' AND day <= '2026-04-27'
    RETURN ticker, day, events, samples
    ORDER BY events DESC, ticker, day
    LIMIT $limit
    """

    source_counts_query = """
    CALL {
      MATCH (n:News)-[r:INFLUENCES]->(c:Company)
      WHERE r.hourly_stock IS NOT NULL AND n.created IS NOT NULL
      RETURN 'News' AS source, n.created AS created, r, c
      UNION ALL
      MATCH (n:Report)-[r:PRIMARY_FILER|REFERENCED_IN]->(c:Company)
      WHERE r.hourly_stock IS NOT NULL AND n.created IS NOT NULL
      RETURN 'Report' AS source, n.created AS created, r, c
      UNION ALL
      MATCH (n:Transcript)-[r:INFLUENCES]->(c:Company)
      WHERE r.hourly_stock IS NOT NULL AND n.created IS NOT NULL
      RETURN 'Transcript' AS source, n.created AS created, r, c
    }
    RETURN source,
           count(*) AS rows,
           count(DISTINCT c.ticker) AS tickers,
           min(toString(created)) AS first_created,
           max(toString(created)) AS last_created
    ORDER BY source
    """

    case_query = """
    MATCH (n:News)-[r:INFLUENCES]->(c:Company {ticker: $ticker})
    WHERE substring(toString(n.created), 0, 10) = $day
      AND r.hourly_stock IS NOT NULL
    RETURN n.id AS event_id,
           toString(n.created) AS created,
           n.market_session AS market_session,
           n.returns_schedule AS returns_schedule,
           c.ticker AS ticker,
           c.sector_etf AS sector_etf,
           c.industry_etf AS industry_etf,
           r.hourly_stock AS hourly_stock,
           r.session_stock AS session_stock,
           r.daily_stock AS daily_stock,
           r.hourly_sector AS hourly_sector,
           r.session_sector AS session_sector,
           r.daily_sector AS daily_sector,
           r.hourly_industry AS hourly_industry,
           r.session_industry AS session_industry,
           r.daily_industry AS daily_industry,
           r.hourly_macro AS hourly_macro,
           r.session_macro AS session_macro,
           r.daily_macro AS daily_macro
    ORDER BY n.created, n.id
    """

    output: dict[str, Any] = {
        "safety": "All Neo4j queries used READ_ACCESS and execute_read.",
        "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    driver = GraphDatabase.driver(uri, auth=(username, password))
    try:
        driver.verify_connectivity()
        with driver.session(default_access_mode=READ_ACCESS) as session:
            output["sample_shape"] = session.execute_read(rows, shape_query)
            output["dense_news_symbol_days"] = session.execute_read(
                rows, dense_query, limit=args.limit
            )
            output["source_counts"] = session.execute_read(
                rows, source_counts_query
            )
            output["cases"] = {}
            for raw_case in args.case:
                ticker, separator, day = raw_case.partition(":")
                if not separator:
                    raise ValueError(f"Invalid case: {raw_case}")
                date.fromisoformat(day)
                ticker = ticker.strip().upper()
                output["cases"][f"{ticker}:{day}"] = session.execute_read(
                    rows, case_query, ticker=ticker, day=day
                )
    finally:
        driver.close()

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
