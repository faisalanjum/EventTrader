#!/usr/bin/env python3
"""Find NULL returns for tickers that are valid in Polygon."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neograph.Neo4jConnection import get_manager
from eventReturns.polygonClass import Polygon

# Get some major tickers that should be valid
neo4j = get_manager()
api_key = os.environ.get('POLYGON_API_KEY')
polygon = Polygon(api_key=api_key, polygon_subscription_delay=1020)

# Test some tickers
test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA']
valid_tickers = []

print("Testing ticker validity in Polygon:")
for ticker in test_tickers:
    is_valid, error = polygon.validate_ticker(ticker)
    print(f"  {ticker}: {'Valid' if is_valid else f'Invalid - {error}'}")
    if is_valid:
        valid_tickers.append(ticker)

print(f"\nValid tickers: {valid_tickers}")

# Find NULL returns for valid tickers
if valid_tickers:
    ticker_list = "', '".join(valid_tickers)
    query = f"""
    MATCH (event)-[r:INFLUENCES|PRIMARY_FILER]->(c:Company)
    WHERE (r.hourly_stock IS NULL OR r.session_stock IS NULL OR r.daily_stock IS NULL) 
      AND event.created STARTS WITH '2023-12'
      AND c.ticker IN ['{ticker_list}']
    RETURN 
        id(r) as rel_id,
        event.id as event_id,
        event.created as event_datetime,
        c.ticker as ticker,
        type(r) as rel_type
    ORDER BY event.created DESC
    LIMIT 10
    """
    
    print("\nFinding NULL returns for valid tickers in December 2023:")
    with neo4j.driver.session() as session:
        result = session.run(query)
        count = 0
        for record in result:
            count += 1
            print(f"  {record['rel_type']} - {record['ticker']} - {record['event_datetime']} - RelID: {record['rel_id']}")
        
        if count == 0:
            print("  No NULL returns found for valid tickers in December 2023")