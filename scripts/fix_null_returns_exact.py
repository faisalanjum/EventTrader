#!/usr/bin/env python3
"""
Fix NULL stock returns by replicating the exact returns calculation flow.

This script:
1. Finds relationships with NULL returns from Neo4j
2. Calculates returns using the EXACT same logic as ReturnsProcessor
3. Updates Neo4j relationships directly with calculated returns
"""

import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import sys
import os
from zoneinfo import ZoneInfo
import numpy as np

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neograph.Neo4jConnection import get_manager
from eventReturns.polygonClass import Polygon
from utils.log_config import setup_logging
from redisDB.redisClasses import RedisClient
import time

log_file = setup_logging(name="fix_returns_exact")
logger = logging.getLogger(__name__)

# Eastern timezone for market hours
EASTERN_TZ = ZoneInfo('America/New_York')

class ExactReturnsFixProcessor:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.neo4j_manager = get_manager()
        
        # Initialize Polygon with API key from environment
        api_key = os.environ.get('POLYGON_API_KEY')
        if not api_key:
            raise ValueError("POLYGON_API_KEY environment variable not set")
        
        # Use 17 minute delay for lower tier subscription (1020 seconds)
        self.polygon = Polygon(api_key=api_key, polygon_subscription_delay=1020)
        
        # Get universe data for sector/industry lookups
        self.redis_client = RedisClient(prefix='admin:')
        self.universe = self._load_universe()
        
    def _load_universe(self) -> Dict[str, Dict]:
        """Load stock universe data from Redis."""
        universe = {}
        
        # Load from CSV file like the production system does
        import pandas as pd
        try:
            # This is the path used in EventTraderRedis
            csv_path = '/home/faisal/EventMarketDB/config/final_symbols.csv'
            df = pd.read_csv(csv_path)
            
            # Convert to dict format
            for _, row in df.iterrows():
                ticker = row['symbol']
                universe[ticker] = {
                    'symbol': ticker,
                    'sector_etf': row.get('sector_etf', 'SPY'),
                    'industry_etf': row.get('industry_etf', 'SPY'),
                    'cik': row.get('cik', '')
                }
                
            logger.info(f"Loaded universe data for {len(universe)} tickers from CSV")
        except Exception as e:
            logger.error(f"Error loading universe from CSV: {e}")
            # Fall back to Redis
            admin_client = RedisClient(prefix='admin:')
            keys = admin_client.client.keys('universe:*')
            
            for key in keys:
                ticker = key.split(':')[-1]
                data = admin_client.client.hgetall(key)
                if data:
                    universe[ticker] = data
                    
            logger.info(f"Loaded universe data for {len(universe)} tickers from Redis")
        
        return universe
    
    def find_affected_relationships(self, limit: int = None, company: str = None, exclude_future: bool = True) -> List[Dict]:
        """Find relationships with NULL stock returns from Neo4j."""
        
        where_clause = "WHERE (r.hourly_stock IS NULL OR r.session_stock IS NULL OR r.daily_stock IS NULL)"
        if company:
            where_clause += f" AND c.ticker = '{company}'"
        if exclude_future:
            # Exclude events from July 2025 onwards (as requested)
            where_clause += " AND event.created < '2025-07-01'"
            
        query = f"""
        MATCH (event)-[r:INFLUENCES|PRIMARY_FILER]->(c:Company)
        {where_clause}
        RETURN 
            id(r) as rel_id,
            type(r) as rel_type,
            event.id as event_id,
            labels(event)[0] as event_type,
            event.created as event_datetime,
            event.market_session as market_session,
            c.ticker as ticker,
            c.symbol as symbol,
            c.cik as cik
        ORDER BY event.created DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
            
        logger.info(f"Finding relationships with NULL stock returns...")
        
        with self.neo4j_manager.driver.session() as session:
            result = session.run(query)
            relationships = []
            for record in result:
                relationships.append(dict(record))
        
        logger.info(f"Found {len(relationships)} relationships with NULL stock returns")
        return relationships
    
    def _calculate_returns_for_symbol(self, symbol: str, event_timestamp: str, rel: Dict) -> Dict:
        """Calculate returns for a symbol using the EXACT logic from ReturnsProcessor."""
        
        # Get universe data for benchmarks
        ticker_data = self.universe.get(symbol, {})
        sector_etf = ticker_data.get('sector_etf', 'SPY')  # Default to SPY if not found
        industry_etf = ticker_data.get('industry_etf', 'SPY')
        
        logger.debug(f"Calculating returns for {symbol} (sector: {sector_etf}, industry: {industry_etf})")
        
        returns = {}
        
        # Calculate each return type
        for return_type in ['hourly', 'session', 'daily']:
            try:
                # This matches ReturnsProcessor._calculate_available_returns() logic
                # IMPORTANT: event_timestamp should be the original Eastern time string, not UTC
                return_data = self.polygon.get_event_returns(
                    ticker=symbol,
                    sector_etf=sector_etf,
                    industry_etf=industry_etf,
                    event_timestamp=event_timestamp,  # Use original Eastern time string
                    return_type=return_type,
                    horizon_minutes=[60] if return_type == 'hourly' else None
                )
                
                if return_data:
                    # The API returns data directly as {stock, sector, industry, macro}
                    # We need to wrap it with the return type
                    returns[f'{return_type}_return'] = return_data
                    logger.info(f"Got {return_type} returns for {symbol}: {return_data}")
                else:
                    logger.warning(f"No {return_type} returns calculated for {symbol}")
                    
            except Exception as e:
                logger.error(f"Error calculating {return_type} returns for {symbol}: {e}")
                continue
        
        return returns
    
    def _extract_return_metrics(self, returns_data: Dict, symbol: str) -> Dict:
        """Extract return metrics using the EXACT logic from neograph/mixins/utility.py."""
        
        props = {}
        
        # This matches _extract_return_metrics() in utility.py
        for timeframe in ['hourly_return', 'session_return', 'daily_return']:
            if timeframe in returns_data:
                timeframe_data = returns_data[timeframe]
                prefix = timeframe.split('_')[0]  # 'hourly', 'session', 'daily'
                
                # Extract each metric type and round to 2 decimal places (matching production)
                for metric_type in ['stock', 'sector', 'industry', 'macro']:
                    if metric_type in timeframe_data:
                        value = timeframe_data[metric_type]
                        
                        # Handle list format for hourly returns
                        if isinstance(value, list):
                            # For hourly returns, take the first value in the list
                            if len(value) > 0 and not np.isnan(value[0]):
                                props[f'{prefix}_{metric_type}'] = round(value[0], 2)
                            else:
                                props[f'{prefix}_{metric_type}'] = None
                        else:
                            # For session/daily returns
                            if not np.isnan(value):
                                props[f'{prefix}_{metric_type}'] = round(value, 2)
                            else:
                                props[f'{prefix}_{metric_type}'] = None
        
        return props
    
    def process_relationship(self, rel: Dict) -> bool:
        """Process a single relationship to fix its returns."""
        
        rel_id = rel['rel_id']
        symbol = rel['symbol'] or rel['ticker']  # Use symbol, fallback to ticker
        
        if not symbol:
            logger.error(f"No symbol found for relationship {rel_id}")
            return False
        
        logger.info(f"Processing {rel['rel_type']} relationship {rel_id} for {symbol} - Event: {rel['event_datetime']}")
        
        # Use the original timestamp string directly - Polygon expects Eastern time strings
        event_timestamp = rel['event_datetime']
        
        # Calculate returns
        returns_data = self._calculate_returns_for_symbol(symbol, event_timestamp, rel)
        
        if not returns_data:
            logger.warning(f"No returns calculated for {symbol}")
            return False
        
        # Extract metrics in the exact format
        properties = self._extract_return_metrics(returns_data, symbol)
        
        if not properties:
            logger.warning(f"No valid return properties extracted for relationship {rel_id}")
            return False
        
        # Update the relationship
        query = """
        MATCH ()-[r]->()
        WHERE id(r) = $rel_id
        SET r += $properties
        RETURN r
        """
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would update relationship {rel_id} with properties: {properties}")
            return True
        
        try:
            with self.neo4j_manager.driver.session() as session:
                result = session.run(query, rel_id=rel_id, properties=properties)
                if result.single():
                    logger.info(f"Updated relationship {rel_id} with {len(properties)} return values")
                    return True
                else:
                    logger.error(f"Failed to update relationship {rel_id}")
                    return False
        except Exception as e:
            logger.error(f"Error updating relationship {rel_id}: {e}")
            return False
    
    def run(self, limit: int = None, company: str = None, batch_size: int = 5, exclude_future: bool = True):
        """Main execution method."""
        
        # Find affected relationships
        relationships = self.find_affected_relationships(limit=limit, company=company, exclude_future=exclude_future)
        
        if not relationships:
            logger.info("No relationships found with NULL stock returns")
            return
        
        # Group by type for summary
        rel_counts = {}
        for rel in relationships:
            rel_type = rel['rel_type']
            rel_counts[rel_type] = rel_counts.get(rel_type, 0) + 1
        
        logger.info(f"\nSummary by relationship type:")
        for rel_type, count in rel_counts.items():
            logger.info(f"  {rel_type}: {count}")
        
        if self.dry_run:
            logger.info("\n[DRY RUN] Would process the above relationships")
            # Show sample relationships
            for rel in relationships[:3]:
                logger.info(f"  {rel['rel_type']} for {rel['ticker']} (event: {rel['event_id']})")
            if len(relationships) > 3:
                logger.info(f"  ... and {len(relationships) - 3} more")
            return
        
        # Process in batches
        success_count = 0
        failed_count = 0
        
        for i in range(0, len(relationships), batch_size):
            batch = relationships[i:i + batch_size]
            logger.info(f"\nProcessing batch {i//batch_size + 1} ({len(batch)} relationships)...")
            
            for rel in batch:
                try:
                    if self.process_relationship(rel):
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    logger.error(f"Error processing relationship {rel['rel_id']}: {e}")
                    failed_count += 1
            
            # Delay between batches to respect Polygon API limits
            if i + batch_size < len(relationships):
                logger.info("Waiting 2 seconds before next batch (Polygon API rate limit)...")
                time.sleep(2)
        
        logger.info(f"\nProcessing complete:")
        logger.info(f"  Successfully updated: {success_count}")
        logger.info(f"  Failed: {failed_count}")


def main():
    parser = argparse.ArgumentParser(description='Fix NULL stock returns using exact calculation logic')
    parser.add_argument('--limit', type=int, help='Limit number of relationships to process')
    parser.add_argument('--company', help='Process only specific company ticker (e.g., ACCD)')
    parser.add_argument('--batch-size', type=int, default=5, help='Batch size for processing (default: 5)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    
    args = parser.parse_args()
    
    processor = ExactReturnsFixProcessor(dry_run=args.dry_run)
    processor.run(limit=args.limit, company=args.company, batch_size=args.batch_size)


if __name__ == "__main__":
    main()