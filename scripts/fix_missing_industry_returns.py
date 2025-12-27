#!/usr/bin/env python3
"""
Fix missing hourly_industry and session_industry returns for transcripts that have daily_industry.

This script specifically addresses 16 transcripts where:
- daily_industry is populated
- hourly_industry and/or session_industry are NULL
- Stock returns are already calculated
"""

import argparse
import logging
import sys
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neograph.Neo4jConnection import get_manager
from eventReturns.polygonClass import Polygon
from eventReturns.ReturnsProcessor import ReturnsProcessor
from utils.log_config import setup_logging
import pandas as pd

log_file = setup_logging(name="fix_industry_returns")
logger = logging.getLogger(__name__)

class IndustryReturnsFixProcessor:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.neo4j_manager = get_manager()
        self.polygon = EventReturnsCalculator()
        self.returns_processor = ReturnsProcessor()
        
    def find_affected_transcripts(self) -> List[Dict]:
        """Find transcripts with missing industry returns."""
        
        query = """
        MATCH (t:Transcript)-[r:INFLUENCES]->(c:Company)
        WHERE (r.hourly_industry IS NULL OR r.session_industry IS NULL)
        AND r.daily_industry IS NOT NULL
        RETURN 
            t.id as transcript_id,
            t.datetime as event_datetime,
            c.ticker as ticker,
            c.symbol as symbol,
            c.cik as cik,
            id(r) as rel_id,
            r.daily_industry as daily_industry,
            r.hourly_industry as hourly_industry,
            r.session_industry as session_industry,
            r.hourly_stock as hourly_stock,
            r.session_stock as session_stock,
            r.daily_stock as daily_stock
        ORDER BY t.datetime
        """
        
        logger.info("Finding transcripts with missing industry returns...")
        
        with self.neo4j_manager.driver.session() as session:
            result = session.run(query)
            transcripts = []
            for record in result:
                transcripts.append(dict(record))
        
        logger.info(f"Found {len(transcripts)} transcripts with missing industry returns")
        return transcripts
    
    def get_industry_etf(self, ticker: str) -> str:
        """Get industry ETF for a ticker."""
        
        # Try to get from ReturnsProcessor method
        industry_etf = self.returns_processor.get_etf(ticker, 'industry_etf')
        
        if industry_etf and industry_etf != 'SPY':
            return industry_etf
        
        # If not found, use sector ETF as fallback
        sector_etf = self.returns_processor.get_etf(ticker, 'sector_etf')
        if sector_etf and sector_etf != 'SPY':
            logger.warning(f"No industry ETF found for {ticker}, using sector ETF {sector_etf}")
            return sector_etf
        
        # Default to SPY
        logger.warning(f"No ETF found for {ticker}, defaulting to SPY")
        return 'SPY'
    
    def parse_transcript_datetime(self, transcript_id: str) -> str:
        """Extract datetime from transcript ID."""
        # Format: TICKER_YYYY-MM-DDTHH.MM.SS-TZ
        parts = transcript_id.split('_')
        if len(parts) >= 2:
            return parts[1]
        raise ValueError(f"Cannot parse datetime from transcript ID: {transcript_id}")
    
    def calculate_missing_returns(self, transcript: Dict) -> Dict[str, Optional[float]]:
        """Calculate missing industry returns for a transcript."""
        
        ticker = transcript['ticker']
        transcript_id = transcript['transcript_id']
        
        # Get industry ETF
        industry_etf = self.get_industry_etf(ticker)
        sector_etf = self.returns_processor.get_etf(ticker, 'sector_etf')
        
        # Parse event timestamp from transcript ID
        event_timestamp = self.parse_transcript_datetime(transcript_id)
        
        logger.info(f"Calculating returns for {ticker} at {event_timestamp}")
        logger.info(f"  Industry ETF: {industry_etf}, Sector ETF: {sector_etf}")
        
        returns = {}
        
        try:
            # Calculate hourly industry if missing
            if transcript['hourly_industry'] is None:
                hourly_returns = self.polygon.get_event_returns(
                    ticker=ticker,
                    sector_etf=sector_etf,
                    industry_etf=industry_etf,
                    event_timestamp=event_timestamp,
                    return_type='hourly',
                    horizon_minutes=[60]
                )
                
                if hourly_returns and 'industry' in hourly_returns:
                    # For hourly returns, the value is a list, take first element
                    industry_value = hourly_returns['industry'][0] if isinstance(hourly_returns['industry'], list) else hourly_returns['industry']
                    if not pd.isna(industry_value):
                        returns['hourly_industry'] = round(industry_value, 2)
                        logger.info(f"  Calculated hourly_industry: {returns['hourly_industry']}")
            
            # Calculate session industry if missing
            if transcript['session_industry'] is None:
                session_returns = self.polygon.get_event_returns(
                    ticker=ticker,
                    sector_etf=sector_etf,
                    industry_etf=industry_etf,
                    event_timestamp=event_timestamp,
                    return_type='session',
                    horizon_minutes=None
                )
                
                if session_returns and 'industry' in session_returns:
                    industry_value = session_returns['industry']
                    if not pd.isna(industry_value):
                        returns['session_industry'] = round(industry_value, 2)
                        logger.info(f"  Calculated session_industry: {returns['session_industry']}")
                        
        except Exception as e:
            logger.error(f"Error calculating returns for {ticker}: {e}")
            
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
    
    def process_transcript(self, transcript: Dict) -> bool:
        """Process a single transcript to fix its industry returns."""
        
        ticker = transcript['ticker']
        transcript_id = transcript['transcript_id']
        
        logger.info(f"\nProcessing transcript {transcript_id} for {ticker}")
        logger.info(f"  Current: hourly_industry={transcript['hourly_industry']}, "
                   f"session_industry={transcript['session_industry']}, "
                   f"daily_industry={transcript['daily_industry']}")
        
        # Calculate missing returns
        returns = self.calculate_missing_returns(transcript)
        
        if not returns:
            logger.warning(f"No returns calculated for {transcript_id}")
            return False
        
        # Update relationship
        return self.update_relationship(transcript['rel_id'], returns)
    
    def run(self):
        """Main execution method."""
        
        # Find affected transcripts
        transcripts = self.find_affected_transcripts()
        
        if not transcripts:
            logger.info("No transcripts found with missing industry returns")
            return
        
        # Summary
        logger.info(f"\nFound {len(transcripts)} transcripts to process:")
        for t in transcripts:
            missing = []
            if t['hourly_industry'] is None:
                missing.append('hourly')
            if t['session_industry'] is None:
                missing.append('session')
            logger.info(f"  {t['transcript_id']} ({t['ticker']}) - missing: {', '.join(missing)}")
        
        if self.dry_run:
            logger.info("\n[DRY RUN MODE] - No changes will be made")
        
        # Process each transcript
        success_count = 0
        failed_count = 0
        
        for transcript in transcripts:
            try:
                if self.process_transcript(transcript):
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Error processing {transcript['transcript_id']}: {e}", exc_info=True)
                failed_count += 1
            
            # Small delay to avoid overwhelming the API
            import time
            time.sleep(0.5)
        
        # Final summary
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing complete:")
        logger.info(f"  Successful: {success_count}")
        logger.info(f"  Failed: {failed_count}")
        logger.info(f"  Total: {len(transcripts)}")

def main():
    parser = argparse.ArgumentParser(description='Fix missing industry returns for transcripts')
    parser.add_argument('--dry-run', action='store_true', help='Run without making changes')
    
    args = parser.parse_args()
    
    processor = IndustryReturnsFixProcessor(dry_run=args.dry_run)
    processor.run()

if __name__ == '__main__':
    main()