#!/usr/bin/env python3
"""
Verify that our returns calculation matches existing returns in the database.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neograph.Neo4jConnection import get_manager
from eventReturns.polygonClass import Polygon
from datetime import datetime
from zoneinfo import ZoneInfo
import json

# Eastern timezone
EASTERN_TZ = ZoneInfo('America/New_York')

neo4j = get_manager()
api_key = os.environ.get('POLYGON_API_KEY')
polygon = Polygon(api_key=api_key, polygon_subscription_delay=900)

# Find a relationship that already has returns
query = """
MATCH (event)-[r:INFLUENCES]->(c:Company)
WHERE r.hourly_stock IS NOT NULL 
  AND r.session_stock IS NOT NULL 
  AND r.daily_stock IS NOT NULL
  AND event.created >= '2024-01-01'
  AND event.created < '2024-12-31'
RETURN 
    event.id as event_id,
    event.created as event_datetime,
    c.ticker as ticker,
    c.symbol as symbol,
    r.hourly_stock as existing_hourly,
    r.session_stock as existing_session,
    r.daily_stock as existing_daily,
    r.hourly_sector as existing_hourly_sector,
    r.hourly_industry as existing_hourly_industry,
    r.hourly_macro as existing_hourly_macro
ORDER BY event.created DESC
LIMIT 5
"""

print("Finding events with existing returns to verify calculation...")
with neo4j.driver.session() as session:
    result = session.run(query)
    
    for record in result:
        ticker = record['symbol'] or record['ticker']
        dt_str = record['event_datetime']
        
        print(f"\n{'='*60}")
        print(f"Event: {record['event_id']}")
        print(f"Ticker: {ticker}")
        print(f"DateTime: {dt_str}")
        print(f"\nExisting returns in database:")
        print(f"  Hourly:  stock={record['existing_hourly']:.2f}%, sector={record['existing_hourly_sector']:.2f}%, " +
              f"industry={record['existing_hourly_industry']:.2f}%, macro={record['existing_hourly_macro']:.2f}%")
        print(f"  Session: stock={record['existing_session']:.2f}%")
        print(f"  Daily:   stock={record['existing_daily']:.2f}%")
        
        # Parse datetime
        if 'T' in dt_str:
            if dt_str.endswith('Z'):
                dt_str = dt_str[:-1] + '+00:00'
            event_datetime = datetime.fromisoformat(dt_str)
        else:
            event_datetime = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        
        if event_datetime.tzinfo is None:
            event_datetime = event_datetime.replace(tzinfo=EASTERN_TZ)
        
        # Convert to UTC
        if event_datetime.tzinfo != ZoneInfo('UTC'):
            event_datetime = event_datetime.astimezone(ZoneInfo('UTC'))
        
        # Calculate returns
        print(f"\nRecalculating returns...")
        
        for return_type in ['hourly', 'session', 'daily']:
            try:
                return_data = polygon.get_event_returns(
                    ticker=ticker,
                    sector_etf='SPY',  # Default for now
                    industry_etf='SPY',
                    event_timestamp=event_datetime.isoformat(),
                    return_type=return_type
                )
                
                if return_data and 'stock' in return_data:
                    print(f"  {return_type}: stock={return_data['stock']:.2f}%")
                    
                    # Compare
                    existing = record[f'existing_{return_type}']
                    calculated = return_data['stock']
                    
                    if abs(existing - calculated) < 0.01:  # Within 0.01%
                        print(f"    ✓ MATCH! ({existing:.2f}% = {calculated:.2f}%)")
                    else:
                        print(f"    ✗ MISMATCH! Database: {existing:.2f}%, Calculated: {calculated:.2f}%")
                else:
                    print(f"  {return_type}: No data returned")
                    
            except Exception as e:
                print(f"  {return_type}: Error - {e}")
        
        break  # Just test one for now