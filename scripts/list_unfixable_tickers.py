#!/usr/bin/env python3
"""List all unfixable tickers with NULL returns (invalid in Polygon)."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neograph.Neo4jConnection import get_manager
from eventReturns.polygonClass import Polygon
from collections import defaultdict
import pandas as pd

def main():
    neo4j = get_manager()
    api_key = os.environ.get('POLYGON_API_KEY')
    polygon = Polygon(api_key=api_key, polygon_subscription_delay=1020)
    
    # Get all tickers with NULL returns (excluding future dates)
    query = """
    MATCH (event)-[r:INFLUENCES|PRIMARY_FILER]->(c:Company)
    WHERE (r.hourly_stock IS NULL OR r.session_stock IS NULL OR r.daily_stock IS NULL)
      AND event.created < '2025-07-01'
    WITH c.ticker as ticker, c.symbol as symbol, c.name as company_name,
         COUNT(DISTINCT CASE WHEN type(r) = 'INFLUENCES' THEN r END) as influences_null,
         COUNT(DISTINCT CASE WHEN type(r) = 'PRIMARY_FILER' THEN r END) as primary_filer_null,
         MIN(event.created) as earliest_event,
         MAX(event.created) as latest_event
    RETURN ticker, symbol, company_name, 
           influences_null, primary_filer_null,
           influences_null + primary_filer_null as total_null,
           earliest_event, latest_event
    ORDER BY total_null DESC
    """
    
    print("Fetching all tickers with NULL returns...")
    with neo4j.driver.session() as session:
        result = session.run(query)
        all_data = []
        for record in result:
            ticker = record['symbol'] or record['ticker']
            if ticker:
                all_data.append({
                    'ticker': ticker,
                    'company_name': record['company_name'],
                    'influences_null': record['influences_null'],
                    'primary_filer_null': record['primary_filer_null'],
                    'total_null': record['total_null'],
                    'earliest_event': record['earliest_event'],
                    'latest_event': record['latest_event']
                })
    
    print(f"Found {len(all_data)} unique tickers with NULL returns")
    print("\nValidating each ticker with Polygon API...")
    
    # Separate valid and invalid
    invalid_tickers = []
    valid_tickers = []
    
    for i, data in enumerate(all_data):
        ticker = data['ticker']
        is_valid, error_msg = polygon.validate_ticker(ticker)
        
        if not is_valid:
            data['error_reason'] = error_msg
            invalid_tickers.append(data)
        else:
            valid_tickers.append(data)
        
        # Progress indicator
        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(all_data)} tickers...")
    
    # Create DataFrame for invalid tickers
    df_invalid = pd.DataFrame(invalid_tickers)
    
    print("\n" + "="*80)
    print("UNFIXABLE TICKERS (Invalid in Polygon)")
    print("="*80)
    
    # Group by error reason
    error_counts = defaultdict(list)
    for ticker_data in invalid_tickers:
        reason = ticker_data['error_reason']
        error_counts[reason].append(ticker_data)
    
    # Show summary by error type
    print("\nSummary by Error Type:")
    for reason, tickers in sorted(error_counts.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"\n{reason}: {len(tickers)} tickers")
        print("-" * 60)
        
        # Show top 10 by NULL count
        sorted_tickers = sorted(tickers, key=lambda x: x['total_null'], reverse=True)[:10]
        for t in sorted_tickers:
            print(f"  {t['ticker']:6} - {t['total_null']:4} NULLs - {t['company_name'][:40]}")
            print(f"         Events from {t['earliest_event'][:10]} to {t['latest_event'][:10]}")
    
    # Show total counts
    total_null_relationships = sum(t['total_null'] for t in invalid_tickers)
    print(f"\n{'='*80}")
    print(f"TOTAL UNFIXABLE:")
    print(f"  Tickers: {len(invalid_tickers)}")
    print(f"  Relationships: {total_null_relationships}")
    print(f"    - INFLUENCES: {sum(t['influences_null'] for t in invalid_tickers)}")
    print(f"    - PRIMARY_FILER: {sum(t['primary_filer_null'] for t in invalid_tickers)}")
    
    # Save full list to CSV
    if df_invalid.empty:
        print("\nNo invalid tickers found!")
    else:
        output_file = '/home/faisal/EventMarketDB/unfixable_tickers.csv'
        df_invalid.to_csv(output_file, index=False)
        print(f"\nFull list saved to: {output_file}")
        
        # Show some interesting cases
        print(f"\n{'='*80}")
        print("NOTABLE CASES:")
        print("="*80)
        
        # High volume tickers
        print("\nHighest NULL counts:")
        for _, row in df_invalid.nlargest(5, 'total_null').iterrows():
            print(f"  {row['ticker']:6} - {row['total_null']:4} relationships - {row['company_name']}")
        
        # Recent delistings (events in 2024/2025)
        recent = df_invalid[df_invalid['latest_event'] >= '2024-01-01'].sort_values('latest_event', ascending=False)
        if not recent.empty:
            print(f"\nRecent delistings (events in 2024-2025):")
            for _, row in recent.head(10).iterrows():
                print(f"  {row['ticker']:6} - Last event: {row['latest_event'][:10]} - {row['company_name']}")

if __name__ == "__main__":
    main()