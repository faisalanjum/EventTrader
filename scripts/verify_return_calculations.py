#!/usr/bin/env python3
"""Verify that our return calculations match exactly with existing returns in the database."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fix_null_returns_exact import ExactReturnsFixProcessor
from neograph.Neo4jConnection import get_manager
import logging
from utils.log_config import setup_logging
import numpy as np

log_file = setup_logging(name="verify_calculations")
logger = logging.getLogger(__name__)

def main():
    neo4j = get_manager()
    processor = ExactReturnsFixProcessor(dry_run=True)
    
    # Find relationships that already have returns calculated
    query = """
    MATCH (event)-[r:INFLUENCES|PRIMARY_FILER]->(c:Company)
    WHERE r.hourly_stock IS NOT NULL 
      AND r.session_stock IS NOT NULL 
      AND r.daily_stock IS NOT NULL
      AND event.created STARTS WITH '2023-12'
      AND c.ticker IN ['AAPL', 'MSFT', 'TSLA', 'NVDA', 'META']
    RETURN 
        id(r) as rel_id,
        type(r) as rel_type,
        event.id as event_id,
        event.created as event_datetime,
        c.ticker as ticker,
        c.symbol as symbol,
        c.cik as cik,
        r.hourly_stock as existing_hourly,
        r.session_stock as existing_session,
        r.daily_stock as existing_daily,
        r.hourly_sector as existing_hourly_sector,
        r.session_sector as existing_session_sector,
        r.daily_sector as existing_daily_sector
    ORDER BY event.created DESC
    LIMIT 10
    """
    
    logger.info("Fetching relationships with existing returns for verification...")
    
    with neo4j.driver.session() as session:
        result = session.run(query)
        relationships = []
        for record in result:
            relationships.append(dict(record))
    
    logger.info(f"Found {len(relationships)} relationships to verify")
    
    # Verify each relationship
    matches = 0
    mismatches = 0
    
    for rel in relationships:
        ticker = rel['symbol'] or rel['ticker']
        event_timestamp = rel['event_datetime']
        
        logger.info(f"\nVerifying {ticker} - Event: {event_timestamp}")
        logger.info(f"  Existing returns:")
        logger.info(f"    Hourly: {rel['existing_hourly']}")
        logger.info(f"    Session: {rel['existing_session']}")
        logger.info(f"    Daily: {rel['existing_daily']}")
        
        # Calculate returns using our script
        returns_data = processor._calculate_returns_for_symbol(ticker, event_timestamp, rel)
        
        if returns_data:
            # Extract metrics
            calculated = processor._extract_return_metrics(returns_data, ticker)
            
            logger.info(f"  Calculated returns:")
            
            # Compare hourly
            if 'hourly_stock' in calculated:
                calc_hourly = calculated['hourly_stock']
                # Handle list format for hourly returns
                if isinstance(calc_hourly, list) and len(calc_hourly) > 0:
                    calc_hourly = calc_hourly[0]
                logger.info(f"    Hourly: {calc_hourly}")
                
                # Compare values
                existing_hourly = rel['existing_hourly']
                if isinstance(existing_hourly, list) and len(existing_hourly) > 0:
                    existing_hourly = existing_hourly[0]
                
                if not np.isnan(calc_hourly) and not np.isnan(existing_hourly):
                    diff = abs(calc_hourly - existing_hourly)
                    if diff < 0.0001:  # Allow small floating point differences
                        logger.info(f"    ✓ Hourly matches (diff: {diff:.6f})")
                    else:
                        logger.warning(f"    ✗ Hourly mismatch! Diff: {diff}")
                        mismatches += 1
            
            # Compare session
            if 'session_stock' in calculated:
                calc_session = calculated['session_stock']
                logger.info(f"    Session: {calc_session}")
                
                if not np.isnan(calc_session) and rel['existing_session'] is not None:
                    diff = abs(calc_session - rel['existing_session'])
                    if diff < 0.0001:
                        logger.info(f"    ✓ Session matches (diff: {diff:.6f})")
                    else:
                        logger.warning(f"    ✗ Session mismatch! Diff: {diff}")
                        mismatches += 1
            
            # Compare daily
            if 'daily_stock' in calculated:
                calc_daily = calculated['daily_stock']
                logger.info(f"    Daily: {calc_daily}")
                
                if not np.isnan(calc_daily) and rel['existing_daily'] is not None:
                    diff = abs(calc_daily - rel['existing_daily'])
                    if diff < 0.0001:
                        logger.info(f"    ✓ Daily matches (diff: {diff:.6f})")
                        matches += 1
                    else:
                        logger.warning(f"    ✗ Daily mismatch! Diff: {diff}")
                        mismatches += 1
        else:
            logger.warning("  No returns calculated!")
    
    logger.info(f"\n\nVERIFICATION SUMMARY:")
    logger.info(f"  Total comparisons: {matches + mismatches}")
    logger.info(f"  Matches: {matches}")
    logger.info(f"  Mismatches: {mismatches}")
    
    if mismatches == 0:
        logger.info("\n✓ ALL CALCULATIONS MATCH! The fix script produces identical results.")
    else:
        logger.error(f"\n✗ Found {mismatches} mismatches! Do not proceed with bulk processing.")

if __name__ == "__main__":
    main()