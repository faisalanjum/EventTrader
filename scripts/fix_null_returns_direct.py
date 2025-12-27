#!/usr/bin/env python3
"""
Fix NULL stock returns by directly calculating from Neo4j data.

This script:
1. Finds events with NULL returns from Neo4j
2. Uses EventReturnsManager to calculate returns
3. Updates Neo4j relationships directly
"""

import argparse
import logging
from datetime import datetime
from typing import List, Dict, Optional
import sys
import os
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neograph.Neo4jConnection import get_manager
from eventReturns.EventReturnsManager import EventReturnsManager
from eventReturns.polygonClass import EventReturnsCalculator
from utils.log_config import setup_logging
import time

log_file = setup_logging(name="fix_returns_direct")
logger = logging.getLogger(__name__)

class DirectReturnsFixProcessor:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.neo4j_manager = get_manager()
        self.returns_manager = EventReturnsManager()
        self.returns_calculator = EventReturnsCalculator()
        
    def find_affected_events(self, limit: int = None, company: str = None) -> List[Dict]:
        """Find events with NULL stock returns from Neo4j."""
        
        where_clause = "WHERE (r.hourly_stock IS NULL OR r.session_stock IS NULL OR r.daily_stock IS NULL)"
        if company:
            where_clause += f" AND c.ticker = '{company}'"
            
        query = f"""
        MATCH (event)-[r:INFLUENCES|PRIMARY_FILER]->(c:Company)
        {where_clause}
        WITH event, c, r, type(r) as rel_type
        RETURN 
            id(event) as event_neo4j_id,
            event.id as event_id,
            labels(event)[0] as event_type,
            event.created as event_datetime,
            event.title as title,
            event.market_session as market_session,
            c.ticker as ticker,
            c.symbol as symbol,
            c.cik as cik,
            rel_type as relationship_type,
            id(r) as rel_id
        ORDER BY event.created DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
            
        logger.info(f"Finding events with NULL stock returns...")
        
        with self.neo4j_manager.driver.session() as session:
            result = session.run(query)
            events = []
            for record in result:
                events.append(dict(record))
        
        logger.info(f"Found {len(events)} events with NULL stock returns")
        return events
    
    def create_event_data(self, event: Dict) -> Dict:
        """Create event data structure for returns calculation."""
        
        # Convert Neo4j datetime string to Python datetime
        dt_str = event['event_datetime']
        if 'T' in dt_str:
            # Parse ISO format with timezone
            if dt_str.endswith('Z'):
                dt_str = dt_str[:-1] + '+00:00'
            dt = datetime.fromisoformat(dt_str)
        else:
            dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        
        # Create event data structure similar to Redis format
        event_data = {
            'id': event['event_id'],
            'created': dt.isoformat(),
            'type': event['event_type'].lower(),
            'ticker': event['ticker'],
            'symbol': event['symbol'],
            'cik': event['cik'],
            'market_session': event.get('market_session', 'unknown')
        }
        
        if event['title']:
            event_data['title'] = event['title']
            
        return event_data
    
    def calculate_returns(self, event_data: Dict) -> Optional[Dict]:
        """Calculate returns for an event."""
        
        try:
            # Generate metadata (determines when to calculate returns)
            metadata = self.returns_manager.process_event_metadata(event_data)
            
            if not metadata or 'return_schedules' not in metadata:
                logger.warning(f"No return schedules generated for event {event_data['id']}")
                return None
            
            # Calculate all returns
            event_with_metadata = {**event_data, **metadata}
            returns_data = self.returns_manager.process_events([event_with_metadata])
            
            if returns_data and len(returns_data) > 0:
                return returns_data[0]  # Get first (and only) event
            else:
                logger.warning(f"No returns calculated for event {event_data['id']}")
                return None
                
        except Exception as e:
            logger.error(f"Error calculating returns for event {event_data['id']}: {e}")
            return None
    
    def update_relationship(self, rel_id: int, returns: Dict) -> bool:
        """Update relationship with calculated returns."""
        
        # Extract return values
        properties = {}
        
        # Map the returns to relationship properties
        if 'metrics' in returns:
            metrics = returns['metrics']
            
            # Stock returns
            properties['hourly_stock'] = metrics.get('hourly_stock')
            properties['session_stock'] = metrics.get('session_stock')
            properties['daily_stock'] = metrics.get('daily_stock')
            
            # Sector returns
            properties['hourly_sector'] = metrics.get('hourly_sector')
            properties['session_sector'] = metrics.get('session_sector')
            properties['daily_sector'] = metrics.get('daily_sector')
            
            # Industry returns
            properties['hourly_industry'] = metrics.get('hourly_industry')
            properties['session_industry'] = metrics.get('session_industry')
            properties['daily_industry'] = metrics.get('daily_industry')
            
            # Macro returns
            properties['hourly_macro'] = metrics.get('hourly_macro')
            properties['session_macro'] = metrics.get('session_macro')
            properties['daily_macro'] = metrics.get('daily_macro')
        
        # Remove None values
        properties = {k: v for k, v in properties.items() if v is not None}
        
        if not properties:
            logger.warning(f"No valid returns to update for relationship {rel_id}")
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
    
    def process_event(self, event: Dict) -> bool:
        """Process a single event to fix its returns."""
        
        event_id = event['event_id']
        logger.info(f"Processing {event['event_type']} event {event_id} for {event['ticker']}")
        
        # Create event data
        event_data = self.create_event_data(event)
        
        # Calculate returns
        returns_data = self.calculate_returns(event_data)
        
        if not returns_data:
            logger.warning(f"No returns calculated for event {event_id}")
            return False
        
        # Update relationship
        success = self.update_relationship(event['rel_id'], returns_data)
        
        return success
    
    def run(self, limit: int = None, company: str = None, batch_size: int = 10):
        """Main execution method."""
        
        # Find affected events
        events = self.find_affected_events(limit=limit, company=company)
        
        if not events:
            logger.info("No events found with NULL stock returns")
            return
        
        # Group by event type for summary
        event_counts = {}
        for event in events:
            event_type = event['event_type']
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        logger.info(f"\nSummary by event type:")
        for event_type, count in event_counts.items():
            logger.info(f"  {event_type}: {count}")
        
        if self.dry_run:
            logger.info("\n[DRY RUN] Would process the above events")
            # Show sample events
            for event in events[:3]:
                logger.info(f"  {event['event_type']} {event['event_id']} ({event['ticker']})")
            if len(events) > 3:
                logger.info(f"  ... and {len(events) - 3} more")
            return
        
        # Process in batches
        success_count = 0
        failed_count = 0
        
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            logger.info(f"\nProcessing batch {i//batch_size + 1} ({len(batch)} events)...")
            
            for event in batch:
                try:
                    if self.process_event(event):
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    logger.error(f"Error processing event {event['event_id']}: {e}")
                    failed_count += 1
            
            # Small delay between batches to avoid overwhelming Polygon API
            if i + batch_size < len(events):
                time.sleep(2)
        
        logger.info(f"\nProcessing complete:")
        logger.info(f"  Successfully updated: {success_count}")
        logger.info(f"  Failed: {failed_count}")


def main():
    parser = argparse.ArgumentParser(description='Fix NULL stock returns by direct calculation')
    parser.add_argument('--limit', type=int, help='Limit number of events to process')
    parser.add_argument('--company', help='Process only specific company ticker (e.g., ACCD)')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for processing (default: 10)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    
    args = parser.parse_args()
    
    processor = DirectReturnsFixProcessor(dry_run=args.dry_run)
    processor.run(limit=args.limit, company=args.company, batch_size=args.batch_size)


if __name__ == "__main__":
    main()