#!/usr/bin/env python3
"""
Fix a specific relationship by ID - for testing returns calculation.
"""

import argparse
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neograph.Neo4jConnection import get_manager
from eventReturns.polygonClass import Polygon
from datetime import datetime
from zoneinfo import ZoneInfo
import logging
from utils.log_config import setup_logging
import pandas as pd

log_file = setup_logging(name="fix_specific_rel")
logger = logging.getLogger(__name__)

def process_specific_relationship(rel_id: int):
    """Process a specific relationship by ID."""
    
    neo4j = get_manager()
    api_key = os.environ.get('POLYGON_API_KEY')
    polygon = Polygon(api_key=api_key, polygon_subscription_delay=1020)
    
    # Load universe
    csv_path = '/home/faisal/EventMarketDB/config/final_symbols.csv'
    universe_df = pd.read_csv(csv_path)
    universe = {}
    for _, row in universe_df.iterrows():
        ticker = row['symbol']
        universe[ticker] = {
            'sector_etf': row.get('sector_etf', 'SPY'),
            'industry_etf': row.get('industry_etf', 'SPY')
        }
    
    # Get relationship details
    query = """
    MATCH (event)-[r]->(c:Company)
    WHERE id(r) = $rel_id
    RETURN 
        type(r) as rel_type,
        event.id as event_id,
        event.created as event_datetime,
        c.ticker as ticker,
        c.symbol as symbol,
        r.hourly_stock as existing_hourly,
        r.session_stock as existing_session,
        r.daily_stock as existing_daily
    """
    
    with neo4j.driver.session() as session:
        result = session.run(query, rel_id=rel_id)
        record = result.single()
        
        if not record:
            logger.error(f"Relationship {rel_id} not found")
            return
        
        ticker = record['symbol'] or record['ticker']
        event_datetime = record['event_datetime']
        
        logger.info(f"Processing relationship {rel_id}")
        logger.info(f"  Event: {record['event_id']}")
        logger.info(f"  Ticker: {ticker}")
        logger.info(f"  DateTime: {event_datetime}")
        logger.info(f"  Existing returns: H={record['existing_hourly']}, S={record['existing_session']}, D={record['existing_daily']}")
        
        # Get benchmarks
        ticker_data = universe.get(ticker, {})
        sector_etf = ticker_data.get('sector_etf', 'SPY')
        industry_etf = ticker_data.get('industry_etf', 'SPY')
        
        logger.info(f"  Benchmarks: sector={sector_etf}, industry={industry_etf}")
        
        # Calculate each return type
        all_props = {}
        for return_type in ['hourly', 'session', 'daily']:
            logger.info(f"\nCalculating {return_type} returns...")
            
            try:
                return_data = polygon.get_event_returns(
                    ticker=ticker,
                    sector_etf=sector_etf,
                    industry_etf=industry_etf,
                    event_timestamp=event_datetime,
                    return_type=return_type,
                    horizon_minutes=[60] if return_type == 'hourly' else None,
                    debug=True  # Enable debug logging
                )
                
                logger.info(f"  Raw result: {return_data}")
                
                if return_data:
                    # Add to properties
                    prefix = return_type.split('_')[0]
                    for metric_type in ['stock', 'sector', 'industry', 'macro']:
                        if metric_type in return_data:
                            value = return_data[metric_type]
                            # Skip NaN values and round to 2 decimal places
                            if value == value:  # NaN check
                                all_props[f'{prefix}_{metric_type}'] = round(value, 2)
                
            except Exception as e:
                logger.error(f"Error calculating {return_type} returns: {e}")
                import traceback
                traceback.print_exc()
        
        # Update relationship
        if all_props:
            logger.info(f"\nUpdating relationship with properties: {all_props}")
            
            update_query = """
            MATCH ()-[r]->()
            WHERE id(r) = $rel_id
            SET r += $properties
            RETURN r
            """
            
            with neo4j.driver.session() as session:
                result = session.run(update_query, rel_id=rel_id, properties=all_props)
                if result.single():
                    logger.info("✓ Successfully updated relationship")
                else:
                    logger.error("✗ Failed to update relationship")
        else:
            logger.warning("No valid returns calculated")


def main():
    parser = argparse.ArgumentParser(description='Fix a specific relationship by ID')
    parser.add_argument('rel_id', type=int, help='Relationship ID to process')
    
    args = parser.parse_args()
    
    process_specific_relationship(args.rel_id)


if __name__ == "__main__":
    main()