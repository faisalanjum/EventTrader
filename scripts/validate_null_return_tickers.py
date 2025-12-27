#!/usr/bin/env python3
"""Validate which tickers with NULL returns are still valid in Polygon."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neograph.Neo4jConnection import get_manager
from eventReturns.polygonClass import Polygon
from collections import defaultdict

neo4j = get_manager()
api_key = os.environ.get('POLYGON_API_KEY')
polygon = Polygon(api_key=api_key, polygon_subscription_delay=1020)

# Get all unique tickers with NULL returns
query = """
MATCH (event)-[r:INFLUENCES|PRIMARY_FILER]->(c:Company)
WHERE (r.hourly_stock IS NULL OR r.session_stock IS NULL OR r.daily_stock IS NULL)
WITH DISTINCT c.ticker as ticker, c.symbol as symbol, COUNT(r) as null_count
RETURN ticker, symbol, null_count
ORDER BY null_count DESC
"""

print("Fetching tickers with NULL returns...")
with neo4j.driver.session() as session:
    result = session.run(query)
    tickers_data = []
    for record in result:
        tickers_data.append({
            'ticker': record['ticker'],
            'symbol': record['symbol'],
            'null_count': record['null_count']
        })

print(f"Found {len(tickers_data)} unique tickers with NULL returns")

# Validate each ticker
valid_tickers = []
invalid_tickers = defaultdict(list)

print("\nValidating tickers with Polygon API...")
for i, data in enumerate(tickers_data[:20]):  # Check first 20
    ticker = data['symbol'] or data['ticker']
    if ticker:
        is_valid, error = polygon.validate_ticker(ticker)
        if is_valid:
            valid_tickers.append((ticker, data['null_count']))
            print(f"✓ {ticker} (Valid) - {data['null_count']} NULL returns")
        else:
            invalid_tickers[error].append((ticker, data['null_count']))
            print(f"✗ {ticker} - {error} - {data['null_count']} NULL returns")

print(f"\n\nSummary:")
print(f"Valid tickers: {len(valid_tickers)}")
print(f"Invalid tickers: {sum(len(v) for v in invalid_tickers.values())}")

if valid_tickers:
    print(f"\nValid tickers with NULL returns:")
    for ticker, count in valid_tickers[:10]:
        print(f"  {ticker}: {count} relationships")

print(f"\nInvalid ticker reasons:")
for reason, tickers in invalid_tickers.items():
    print(f"  {reason}: {len(tickers)} tickers")
    for ticker, count in tickers[:3]:
        print(f"    - {ticker} ({count} relationships)")
    if len(tickers) > 3:
        print(f"    ... and {len(tickers) - 3} more")