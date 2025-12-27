#!/usr/bin/env python3
"""Count relationships that can be fixed after excluding future dates and invalid tickers."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neograph.Neo4jConnection import get_manager
from eventReturns.polygonClass import Polygon
from datetime import datetime

neo4j = get_manager()
api_key = os.environ.get('POLYGON_API_KEY')
polygon = Polygon(api_key=api_key, polygon_subscription_delay=1020)

# Count total NULL returns excluding future dates
query_total = """
MATCH (event)-[r:INFLUENCES|PRIMARY_FILER]->(c:Company)
WHERE (r.hourly_stock IS NULL OR r.session_stock IS NULL OR r.daily_stock IS NULL)
  AND event.created < '2025-07-01'
RETURN 
    type(r) as rel_type,
    COUNT(r) as count
"""

print("Counting NULL returns (excluding future dates)...")
with neo4j.driver.session() as session:
    result = session.run(query_total)
    total_by_type = {}
    total = 0
    for record in result:
        rel_type = record['rel_type']
        count = record['count']
        total_by_type[rel_type] = count
        total += count

print(f"\nTotal NULL returns (excluding future): {total}")
for rel_type, count in total_by_type.items():
    print(f"  {rel_type}: {count}")

# Get unique tickers
query_tickers = """
MATCH (event)-[r:INFLUENCES|PRIMARY_FILER]->(c:Company)
WHERE (r.hourly_stock IS NULL OR r.session_stock IS NULL OR r.daily_stock IS NULL)
  AND event.created < '2025-07-01'
WITH DISTINCT c.ticker as ticker, c.symbol as symbol, COUNT(r) as null_count
RETURN ticker, symbol, null_count
ORDER BY null_count DESC
"""

print("\nChecking ticker validity...")
with neo4j.driver.session() as session:
    result = session.run(query_tickers)
    all_tickers = []
    for record in result:
        ticker = record['symbol'] or record['ticker']
        if ticker:
            all_tickers.append({
                'ticker': ticker,
                'null_count': record['null_count']
            })

# Validate tickers
valid_count = 0
invalid_count = 0
valid_relationships = 0
invalid_relationships = 0

for data in all_tickers:
    ticker = data['ticker']
    is_valid, _ = polygon.validate_ticker(ticker)
    
    if is_valid:
        valid_count += 1
        valid_relationships += data['null_count']
    else:
        invalid_count += 1
        invalid_relationships += data['null_count']

print(f"\nTicker validation results:")
print(f"  Valid tickers: {valid_count} ({valid_relationships} relationships)")
print(f"  Invalid tickers: {invalid_count} ({invalid_relationships} relationships)")
print(f"  Total tickers: {len(all_tickers)}")

print(f"\nFIXABLE RELATIONSHIPS: {valid_relationships}")
print(f"UNFIXABLE (invalid tickers): {invalid_relationships}")
print(f"Success rate potential: {valid_relationships / total * 100:.1f}%")