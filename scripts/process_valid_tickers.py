#!/usr/bin/env python3
"""Process all valid tickers with NULL returns."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fix_null_returns_exact import ExactReturnsFixProcessor
from eventReturns.polygonClass import Polygon
from neograph.Neo4jConnection import get_manager
import logging
from utils.log_config import setup_logging

log_file = setup_logging(name="process_valid_tickers")
logger = logging.getLogger(__name__)

def find_valid_tickers_with_nulls():
    """Find all valid tickers that have NULL returns."""
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
    
    logger.info("Fetching all tickers with NULL returns...")
    with neo4j.driver.session() as session:
        result = session.run(query)
        all_tickers = []
        for record in result:
            ticker = record['symbol'] or record['ticker']
            if ticker:
                all_tickers.append({
                    'ticker': ticker,
                    'null_count': record['null_count']
                })
    
    logger.info(f"Found {len(all_tickers)} unique tickers with NULL returns")
    
    # Validate each ticker
    valid_tickers = []
    invalid_count = 0
    
    logger.info("Validating tickers with Polygon API...")
    for i, data in enumerate(all_tickers):
        ticker = data['ticker']
        is_valid, error = polygon.validate_ticker(ticker)
        
        if is_valid:
            valid_tickers.append(ticker)
            logger.info(f"✓ {ticker} - {data['null_count']} NULL returns")
        else:
            invalid_count += 1
            if i < 20:  # Log first 20 invalid ones
                logger.debug(f"✗ {ticker} - {error}")
        
        # Progress indicator
        if (i + 1) % 50 == 0:
            logger.info(f"Processed {i + 1}/{len(all_tickers)} tickers...")
    
    logger.info(f"\nValidation complete:")
    logger.info(f"  Valid tickers: {len(valid_tickers)}")
    logger.info(f"  Invalid tickers: {invalid_count}")
    
    return valid_tickers

def main():
    # Find valid tickers
    valid_tickers = find_valid_tickers_with_nulls()
    
    if not valid_tickers:
        logger.info("No valid tickers found with NULL returns")
        return
    
    logger.info(f"\nProcessing {len(valid_tickers)} valid tickers...")
    
    # Initialize processor
    processor = ExactReturnsFixProcessor(dry_run=False)
    
    # Process each valid ticker
    total_success = 0
    total_failed = 0
    
    for i, ticker in enumerate(valid_tickers):
        logger.info(f"\n[{i+1}/{len(valid_tickers)}] Processing {ticker}...")
        
        # Find relationships for this ticker
        relationships = processor.find_affected_relationships(company=ticker)
        
        if not relationships:
            logger.info(f"  No NULL relationships found for {ticker}")
            continue
        
        logger.info(f"  Found {len(relationships)} relationships to process")
        
        # Process in batches
        batch_success = 0
        batch_failed = 0
        
        for j in range(0, len(relationships), 5):
            batch = relationships[j:j + 5]
            
            for rel in batch:
                try:
                    if processor.process_relationship(rel):
                        batch_success += 1
                    else:
                        batch_failed += 1
                except Exception as e:
                    logger.error(f"  Error processing relationship {rel['rel_id']}: {e}")
                    batch_failed += 1
        
        logger.info(f"  {ticker} complete: {batch_success} success, {batch_failed} failed")
        total_success += batch_success
        total_failed += batch_failed
    
    logger.info(f"\n\nFINAL SUMMARY:")
    logger.info(f"  Total relationships processed: {total_success + total_failed}")
    logger.info(f"  Successfully updated: {total_success}")
    logger.info(f"  Failed: {total_failed}")
    logger.info(f"  Success rate: {total_success / (total_success + total_failed) * 100:.1f}%")

if __name__ == "__main__":
    main()