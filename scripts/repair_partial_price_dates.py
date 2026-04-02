#!/usr/bin/env python3
"""
One-time repair for 14 legacy batch-boundary dates with exactly 500 HAS_PRICE.

Root cause: the old write loop committed 500 rows per transaction. Process
interruption after batch 1 left dates with exactly 500 prices, permanently
locked by the skip guard (existing_count > 0).

This script calls Polygon for each date and MERGEs all rows. MERGE is additive:
existing edges are updated (no-op), missing edges are created. No deletions.

Usage:
    source venv/bin/activate
    python scripts/repair_partial_price_dates.py --dry-run
    python scripts/repair_partial_price_dates.py
"""
import os
import sys
import logging
import argparse
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neograph.Neo4jInitializer import Neo4jInitializer
from eventReturns.polygonClass import Polygon

logger = logging.getLogger("repair_partial_prices")

BAD_DATES = [
    "2024-02-06", "2025-03-14", "2025-07-16", "2025-07-21", "2025-07-23",
    "2025-07-24", "2025-08-06", "2025-08-07", "2025-08-22", "2025-08-28",
    "2025-08-29", "2025-09-02", "2026-03-31", "2026-04-01",
]

ENTITY_QUERY = """
MATCH (e:Company) WHERE e.ticker IN $symbols
RETURN e.id AS id, e.ticker AS ticker
UNION
MATCH (e:Sector) WHERE e.etf IN $symbols
RETURN e.id AS id, e.etf AS ticker
UNION
MATCH (e:Industry) WHERE e.etf IN $symbols
RETURN e.id AS id, e.etf AS ticker
UNION
MATCH (e:MarketIndex) WHERE e.id IN $symbols
RETURN e.id AS id, e.id AS ticker
"""


def main():
    parser = argparse.ArgumentParser(description="Repair partial-price dates")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    polygon_api_key = os.environ.get("POLYGON_API_KEY")
    if not polygon_api_key:
        logger.error("Missing POLYGON_API_KEY")
        return

    # Neo4jInitializer requires uri/username/password but connect() uses singleton
    initializer = Neo4jInitializer("", "", "")
    initializer.universe_data = initializer.get_tradable_universe()

    if not initializer.connect():
        logger.error("Failed to connect to Neo4j")
        return

    try:
        initializer.prepare_universe_data()
        polygon = Polygon(api_key=polygon_api_key, polygon_subscription_delay=0)

        with initializer.manager.driver.session() as session:
            entity_results = session.run(
                ENTITY_QUERY, {"symbols": initializer.all_symbols}
            ).data()

        ticker_to_id = {}
        for row in entity_results:
            if row["ticker"]:
                ticker_to_id[row["ticker"]] = row["id"]

        logger.info(f"Universe: {len(ticker_to_id)} unique priceable symbols")

        for date_str in BAD_DATES:
            # Read date metadata from Neo4j
            with initializer.manager.driver.session() as session:
                meta = session.run(
                    """
                    MATCH (d:Date {date: $date})
                    OPTIONAL MATCH (d)-[r:HAS_PRICE]->()
                    RETURN d.id AS date_id,
                           d.previous_trading_date AS prev,
                           count(r) AS existing_count
                    """,
                    {"date": date_str},
                ).single()

            if not meta or not meta["date_id"] or not meta["prev"]:
                logger.warning(f"{date_str}: missing Date metadata, skipping")
                continue

            # Hard gate: only repair dates with exactly 500 (batch boundary artifact)
            if meta["existing_count"] != 500:
                logger.info(
                    f"{date_str}: existing_count={meta['existing_count']}, "
                    f"not 500, skipping"
                )
                continue

            # Fetch from Polygon
            price_data = polygon.get_daily_market_summary(
                date_str, meta["prev"], initializer.all_symbols
            )
            if price_data is None or price_data.empty:
                logger.warning(f"{date_str}: Polygon returned no data")
                continue

            # Build params (same logic as add_price_relationships_to_dates)
            batch_params = []
            for ticker, row in price_data.iterrows():
                entity_id = ticker_to_id.get(ticker)
                if not entity_id:
                    continue
                props = row.to_dict()
                if "timestamp" in props and pd.notnull(props["timestamp"]):
                    props["timestamp"] = props["timestamp"].strftime(
                        "%Y-%m-%d %H:%M:%S%z"
                    )
                batch_params.append({
                    "date_id": meta["date_id"],
                    "entity_id": entity_id,
                    "properties": props,
                })

            if not batch_params:
                logger.warning(
                    f"{date_str}: no writable params built from Polygon data, skipping"
                )
                continue

            if args.dry_run:
                logger.info(
                    f"{date_str}: DRY RUN — existing={meta['existing_count']} "
                    f"planned_upserts={len(batch_params)}"
                )
                continue

            # Atomic MERGE — adds missing edges, updates existing (no deletions)
            committed = initializer.manager.create_price_relationships_batch(
                batch_params
            )

            # Post-repair verification
            with initializer.manager.driver.session() as session:
                after = session.run(
                    "MATCH (:Date {id: $id})-[r:HAS_PRICE]->() "
                    "RETURN count(r) AS cnt",
                    {"id": meta["date_id"]},
                ).single()["cnt"]

            if after <= meta["existing_count"]:
                logger.warning(
                    f"{date_str}: no improvement after repair "
                    f"(before={meta['existing_count']}, after={after}, "
                    f"planned={len(batch_params)})"
                )
            elif committed != len(batch_params):
                logger.warning(
                    f"{date_str}: committed {committed} of {len(batch_params)} "
                    f"planned upserts (after={after})"
                )
            else:
                logger.info(
                    f"{date_str}: committed={committed} "
                    f"planned={len(batch_params)} "
                    f"after={after} (was {meta['existing_count']})"
                )

    finally:
        initializer.close()


if __name__ == "__main__":
    main()
