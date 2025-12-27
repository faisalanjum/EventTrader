#!/usr/bin/env python3
"""
Fix missing hourly_sector and session_sector returns for transcripts that have daily_sector.

This script specifically addresses 3 transcripts where:
- daily_sector is populated
- hourly_sector and/or session_sector are NULL
"""

import argparse
import logging
import sys
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neograph.Neo4jConnection import get_manager
from neograph.Neo4jManager import Neo4jManager
from eventtrader.keys import POLYGON_API_KEY
from eventReturns.polygonClass import Polygon
from utils.log_config import setup_logging
from utils.market_session import MarketSessionClassifier
import pandas as pd

log_file = setup_logging(name="fix_sector_returns")
logger = logging.getLogger(__name__)

class SectorReturnsFixProcessor:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        # Use direct connection for script running outside cluster
        uri = "bolt://localhost:30687"
        username = "neo4j"
        password = "Next2020#"
        self.neo4j_manager = Neo4jManager(uri=uri, username=username, password=password)
        self.polygon = Polygon(api_key=POLYGON_API_KEY, polygon_subscription_delay=0)
        self.market_session = MarketSessionClassifier()
        
    def find_affected_relationships(self) -> List[Dict]:
        """Find Sector relationships with missing returns."""
        
        query = """
        MATCH (t:Transcript)-[r:INFLUENCES]->(s:Sector)
        WHERE (r.hourly_sector IS NULL OR r.session_sector IS NULL)
        AND r.daily_sector IS NOT NULL
        RETURN 
            t.id as transcript_id,
            t.event_datetime as event_datetime,
            s.name as sector_name,
            s.etf as sector_etf,
            id(r) as rel_id,
            r.daily_sector as daily_sector,
            r.hourly_sector as hourly_sector,
            r.session_sector as session_sector
        ORDER BY t.event_datetime
        """
        
        logger.info("Finding Sector relationships with missing returns...")
        
        with self.neo4j_manager.driver.session() as session:
            result = session.run(query)
            relationships = []
            for record in result:
                relationships.append(dict(record))
        
        logger.info(f"Found {len(relationships)} Sector relationships with missing returns")
        return relationships
    
    def parse_transcript_datetime(self, transcript_id: str) -> datetime:
        """Extract datetime from transcript ID and convert to datetime object."""
        # Format: TICKER_YYYY-MM-DDTHH.MM.SS-TZ
        parts = transcript_id.split('_')
        if len(parts) >= 2:
            datetime_str = parts[1]
            # Replace dots with colons in time part
            datetime_str = datetime_str.replace('.', ':')
            # Parse the datetime string
            return datetime.fromisoformat(datetime_str)
        raise ValueError(f"Cannot parse datetime from transcript ID: {transcript_id}")
    
    def ensure_etf_price_data(self, etf_symbol: str, date: str) -> bool:
        """Ensure we have ETF price data for the given date."""
        
        # Check if price data exists
        check_query = """
        MATCH (p:Price {symbol: $symbol, date: date($date)})
        RETURN p
        """
        
        with self.neo4j_manager.driver.session() as session:
            result = session.run(check_query, symbol=etf_symbol, date=date)
            if result.single():
                logger.info(f"Price data already exists for {etf_symbol} on {date}")
                return True
        
        # Fetch price data from Polygon
        logger.info(f"Fetching price data for {etf_symbol} on {date}")
        try:
            prices = self.polygon.get_daily_prices(etf_symbol, date, date)
            if not prices or prices.empty:
                logger.error(f"No price data returned for {etf_symbol} on {date}")
                return False
            
            # Store price data in Neo4j
            for _, row in prices.iterrows():
                create_query = """
                CREATE (p:Price {
                    symbol: $symbol,
                    date: date($date),
                    open: $open,
                    close: $close,
                    high: $high,
                    low: $low,
                    volume: $volume,
                    vwap: $vwap,
                    market_open: $market_open,
                    market_close: $market_close
                })
                """
                
                with self.neo4j_manager.driver.session() as session:
                    session.run(create_query,
                        symbol=etf_symbol,
                        date=date,
                        open=float(row['open']),
                        close=float(row['close']),
                        high=float(row['high']),
                        low=float(row['low']),
                        volume=int(row['volume']),
                        vwap=float(row.get('vwap', 0)),
                        market_open=float(row['open']),  # Using open as market_open
                        market_close=float(row['close'])  # Using close as market_close
                    )
            
            logger.info(f"Successfully stored price data for {etf_symbol} on {date}")
            return True
            
        except Exception as e:
            logger.error(f"Error fetching/storing price data for {etf_symbol}: {e}")
            return False
    
    def calculate_etf_return(self, etf_symbol: str, event_datetime: datetime, 
                           return_type: str) -> Optional[float]:
        """Calculate ETF return for the given period."""
        
        # Get the appropriate time windows
        if return_type == 'hourly':
            start_time = self.market_session.get_interval_start_time(event_datetime)
            end_time = self.market_session.get_interval_end_time(event_datetime, 60, respect_session_boundary=False)
        elif return_type == 'session':
            start_time = self.market_session.get_interval_start_time(event_datetime)
            end_time = self.market_session.get_end_time(event_datetime)
        else:
            raise ValueError(f"Invalid return type: {return_type}")
        
        # Get price at start time
        start_price = self.polygon.get_price_at_time(etf_symbol, start_time)
        if start_price is None:
            logger.error(f"Could not get start price for {etf_symbol} at {start_time}")
            return None
        
        # Get price at end time
        end_price = self.polygon.get_price_at_time(etf_symbol, end_time)
        if end_price is None:
            logger.error(f"Could not get end price for {etf_symbol} at {end_time}")
            return None
        
        # Calculate return
        etf_return = ((end_price - start_price) / start_price) * 100
        return round(etf_return, 2)
    
    def calculate_missing_returns(self, relationship: Dict) -> Dict[str, Optional[float]]:
        """Calculate missing sector returns for a relationship."""
        
        transcript_id = relationship['transcript_id']
        sector_etf = relationship['sector_etf']
        
        if not sector_etf:
            logger.error(f"No ETF mapping for sector {relationship['sector_name']}")
            return {}
        
        # Parse event datetime
        event_datetime = self.parse_transcript_datetime(transcript_id)
        event_date = event_datetime.date().isoformat()
        
        logger.info(f"Calculating returns for {sector_etf} at {event_datetime}")
        
        # Ensure we have price data
        if not self.ensure_etf_price_data(sector_etf, event_date):
            logger.error(f"Could not ensure price data for {sector_etf} on {event_date}")
            return {}
        
        returns = {}
        
        try:
            # Calculate hourly sector if missing
            if relationship['hourly_sector'] is None:
                hourly_return = self.calculate_etf_return(sector_etf, event_datetime, 'hourly')
                if hourly_return is not None:
                    returns['hourly_sector'] = hourly_return
                    logger.info(f"  Calculated hourly_sector: {returns['hourly_sector']}")
            
            # Calculate session sector if missing
            if relationship['session_sector'] is None:
                session_return = self.calculate_etf_return(sector_etf, event_datetime, 'session')
                if session_return is not None:
                    returns['session_sector'] = session_return
                    logger.info(f"  Calculated session_sector: {returns['session_sector']}")
                    
        except Exception as e:
            logger.error(f"Error calculating returns for {sector_etf}: {e}")
            
        return returns
    
    def update_relationship(self, rel_id: int, properties: Dict) -> bool:
        """Update relationship with calculated returns."""
        
        if not properties:
            logger.warning(f"No properties to update for relationship {rel_id}")
            return False
        
        query = """
        MATCH ()-[r]->()
        WHERE id(r) = $rel_id
        SET r += $properties
        RETURN r
        """
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would update relationship {rel_id} with: {properties}")
            return True
        
        try:
            with self.neo4j_manager.driver.session() as session:
                result = session.run(query, rel_id=rel_id, properties=properties)
                if result.single():
                    logger.info(f"Updated relationship {rel_id} with {properties}")
                    return True
                else:
                    logger.error(f"Failed to update relationship {rel_id}")
                    return False
        except Exception as e:
            logger.error(f"Error updating relationship {rel_id}: {e}")
            return False
    
    def process_relationship(self, relationship: Dict) -> bool:
        """Process a single relationship to fix its sector returns."""
        
        transcript_id = relationship['transcript_id']
        sector_name = relationship['sector_name']
        
        logger.info(f"\nProcessing relationship for {transcript_id} -> {sector_name}")
        logger.info(f"  Current: hourly_sector={relationship['hourly_sector']}, "
                   f"session_sector={relationship['session_sector']}, "
                   f"daily_sector={relationship['daily_sector']}")
        
        # Calculate missing returns
        returns = self.calculate_missing_returns(relationship)
        
        if not returns:
            logger.warning(f"No returns calculated for {transcript_id} -> {sector_name}")
            return False
        
        # Update relationship
        return self.update_relationship(relationship['rel_id'], returns)
    
    def run(self):
        """Main execution method."""
        
        # Find affected relationships
        relationships = self.find_affected_relationships()
        
        if not relationships:
            logger.info("No Sector relationships found with missing returns")
            return
        
        # Summary
        logger.info(f"\nFound {len(relationships)} relationships to process:")
        for r in relationships:
            missing = []
            if r['hourly_sector'] is None:
                missing.append('hourly')
            if r['session_sector'] is None:
                missing.append('session')
            logger.info(f"  {r['transcript_id']} -> {r['sector_name']} ({r['sector_etf']}) - missing: {', '.join(missing)}")
        
        if self.dry_run:
            logger.info("\n[DRY RUN MODE] - No changes will be made")
        
        # Process each relationship
        success_count = 0
        failed_count = 0
        
        for relationship in relationships:
            try:
                if self.process_relationship(relationship):
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Error processing {relationship['transcript_id']}: {e}", exc_info=True)
                failed_count += 1
            
            # Small delay to avoid overwhelming the API
            import time
            time.sleep(0.5)
        
        # Final summary
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing complete:")
        logger.info(f"  Successful: {success_count}")
        logger.info(f"  Failed: {failed_count}")
        logger.info(f"  Total: {len(relationships)}")

def main():
    parser = argparse.ArgumentParser(description='Fix missing sector returns for transcripts')
    parser.add_argument('--dry-run', action='store_true', help='Run without making changes')
    
    args = parser.parse_args()
    
    processor = SectorReturnsFixProcessor(dry_run=args.dry_run)
    processor.run()

if __name__ == '__main__':
    main()