#!/usr/bin/env python3
"""
Fix NULL stock returns on relationships by re-processing events through the returns pipeline.

This script:
1. Finds all relationships with NULL stock returns
2. Extracts the source event information
3. Re-submits events through the existing returns pipeline
4. The pipeline will recalculate returns and update relationships
"""

import argparse
import logging
from datetime import datetime
from typing import List, Dict, Tuple
import sys
import os
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neograph.Neo4jConnection import get_manager
from eventReturns.ReturnsProcessor import ReturnsProcessor
from eventReturns.EventReturnsManager import EventReturnsManager
from redisDB.redisClasses import RedisClient
from utils.log_config import setup_logging
import time
import logging

log_file = setup_logging(name="fix_null_returns")
logger = logging.getLogger(__name__)

class NullReturnsReprocessor:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.neo4j_manager = get_manager()
        self.redis_client = RedisClient()
        
    def verify_prerequisites(self) -> bool:
        """Verify system is ready for reprocessing."""
        
        logger.info("Verifying prerequisites...")
        
        # 1. Check if Company nodes have symbol field populated
        query = """
        MATCH (c:Company)
        WHERE c.ticker IS NOT NULL AND c.symbol IS NULL
        RETURN COUNT(c) as null_symbol_count
        """
        
        with self.neo4j_manager.driver.session() as session:
            result = session.run(query)
            null_count = result.single()['null_symbol_count']
            
        if null_count > 0:
            logger.error(f"ERROR: {null_count} Company nodes still have NULL symbol field!")
            logger.error("Run this query first: MATCH (c:Company) WHERE c.ticker IS NOT NULL AND c.symbol IS NULL SET c.symbol = c.ticker")
            return False
        
        logger.info("✓ All Company nodes have symbol field populated")
        
        # 2. Check if ReturnsProcessor is monitoring the channels
        test_channels = ['news:live:processed', 'news:hist:processed', 
                         'transcripts:live:processed', 'transcripts:hist:processed',
                         'reports:live:processed', 'reports:hist:processed']
        
        active_channels = []
        for channel in test_channels:
            # Check if anyone is subscribed to this channel
            pubsub_info = self.redis_client.client.pubsub_numsub(channel)
            if pubsub_info and len(pubsub_info) > 0 and pubsub_info[0][1] > 0:
                active_channels.append(channel)
        
        if not active_channels:
            logger.warning("WARNING: No ReturnsProcessor appears to be listening to channels!")
            logger.warning("The ReturnsProcessor may not be running. Events will queue but not process.")
            logger.warning("Start the ReturnsProcessor or event-trader pod to process returns.")
            response = input("Continue anyway? (yes/no): ")
            if response.lower() != 'yes':
                return False
        else:
            logger.info(f"✓ ReturnsProcessor is monitoring {len(active_channels)} channels")
        
        # 3. Verify we can connect to Polygon API (by checking if any recent returns exist)
        query = """
        MATCH ()-[r:INFLUENCES|PRIMARY_FILER]->()
        WHERE r.daily_stock IS NOT NULL
        RETURN r.daily_stock as return_value
        ORDER BY r.created_at DESC
        LIMIT 1
        """
        
        with self.neo4j_manager.driver.session() as session:
            result = session.run(query)
            record = result.single()
            
        if not record:
            logger.warning("WARNING: No existing returns found in the database.")
            logger.warning("This might indicate Polygon API connectivity issues.")
        else:
            logger.info(f"✓ Recent returns found in database (sample: {record['return_value']:.2f}%)")
        
        return True
        
    def find_affected_events(self, limit: int = None) -> List[Dict]:
        """Find all events with NULL stock returns on their relationships."""
        
        query = """
        MATCH (event)-[r:INFLUENCES|PRIMARY_FILER]->(c:Company)
        WHERE r.hourly_stock IS NULL 
           OR r.session_stock IS NULL 
           OR r.daily_stock IS NULL
        WITH DISTINCT event, c, type(r) as rel_type
        RETURN 
            event.id as event_id,
            labels(event)[0] as event_type,
            event.created as event_datetime,
            CASE 
                WHEN event:News THEN event.title
                WHEN event:Transcript THEN event.company_name + ' Q' + event.fiscal_quarter + ' ' + event.fiscal_year + ' Earnings Call'
                WHEN event:Report THEN event.formType + ': ' + coalesce(event.description, '')
            END as event_description,
            c.ticker as company_ticker,
            c.symbol as company_symbol,
            rel_type as relationship_type
        ORDER BY event.created DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
            
        logger.info(f"Finding events with NULL stock returns{f' (limit: {limit})' if limit else ''}...")
        
        with self.neo4j_manager.driver.session() as session:
            result = session.run(query)
            events = []
            for record in result:
                events.append({
                    'event_id': record['event_id'],
                    'event_type': record['event_type'],
                    'event_datetime': record['event_datetime'],
                    'description': record['event_description'],
                    'company_ticker': record['company_ticker'],
                    'company_symbol': record['company_symbol'],
                    'relationship_type': record['relationship_type']
                })
        
        logger.info(f"Found {len(events)} events with NULL stock returns")
        return events
    
    def get_event_from_redis(self, event_id: str, source_type: str) -> Tuple[str, Dict]:
        """Find event in Redis across all namespaces."""
        
        # Map event type to source
        source_map = {
            'News': 'news',
            'Transcript': 'transcripts', 
            'Report': 'reports'
        }
        source = source_map.get(source_type, source_type.lower())
        
        # Check all possible namespaces
        namespaces = [
            f'{source}:live:withreturns',
            f'{source}:live:withoutreturns', 
            f'{source}:live:processed',
            f'{source}:hist:withreturns',
            f'{source}:hist:withoutreturns',
            f'{source}:hist:processed'
        ]
        
        for namespace in namespaces:
            key = f"{namespace}:{event_id}"
            event_json = self.redis_client.client.get(key)
            if event_json:
                logger.debug(f"Found event {event_id} in namespace {namespace}")
                try:
                    event_data = json.loads(event_json)
                    return namespace, event_data
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse event JSON for {event_id}")
                    continue
        
        return None, None
    
    def reprocess_event(self, event: Dict) -> bool:
        """Re-submit an event through the returns pipeline."""
        
        event_id = event['event_id']
        event_type = event['event_type']
        
        # Find event in Redis
        namespace, event_data = self.get_event_from_redis(event_id, event_type)
        
        if not event_data:
            logger.warning(f"Event {event_id} not found in Redis")
            return False
        
        # Determine source type and prefix
        parts = namespace.split(':')
        source = parts[0]
        prefix = parts[1]  # 'live' or 'hist'
        
        logger.info(f"Re-processing {event_type} event {event_id} from {namespace}")
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would reprocess event {event_id}")
            return True
        
        # Move event back to processed state
        processed_key = f"{source}:{prefix}:processed:{event_id}"
        
        # Copy event to processed namespace
        pipeline = self.redis_client.client.pipeline()
        
        # Delete from current namespace
        pipeline.delete(f"{namespace}:{event_id}")
        
        # Set in processed namespace as JSON string
        pipeline.set(processed_key, json.dumps(event_data))
        
        # Clear any pending returns
        pipeline.zrem(f"{source}:pending_returns", event_id)
        
        # Execute pipeline
        pipeline.execute()
        
        # Publish to trigger ReturnsProcessor
        channel = f"{source}:{prefix}:processed"
        self.redis_client.client.publish(channel, event_id)
        
        logger.info(f"Published {event_id} to channel {channel} for reprocessing")
        
        return True
    
    def run(self, limit: int = None, batch_size: int = 10):
        """Main execution method."""
        
        # Verify prerequisites first
        if not self.verify_prerequisites():
            logger.error("Prerequisites check failed. Exiting.")
            return
        
        # Find affected events
        events = self.find_affected_events(limit=limit)
        
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
            logger.info("\n[DRY RUN] Would reprocess the above events")
            # Show sample events
            for event in events[:5]:
                logger.info(f"  {event['event_type']} {event['event_id']}: {event['description'][:50]}...")
            if len(events) > 5:
                logger.info(f"  ... and {len(events) - 5} more")
            return
        
        # Process in batches
        success_count = 0
        failed_count = 0
        
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            logger.info(f"\nProcessing batch {i//batch_size + 1} ({len(batch)} events)...")
            
            for event in batch:
                try:
                    if self.reprocess_event(event):
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    logger.error(f"Error processing event {event['event_id']}: {e}")
                    failed_count += 1
            
            # Small delay between batches
            if i + batch_size < len(events):
                time.sleep(1)
        
        logger.info(f"\nReprocessing complete:")
        logger.info(f"  Successfully queued: {success_count}")
        logger.info(f"  Failed: {failed_count}")
        
        if success_count > 0:
            logger.info("\nNote: Events have been queued for reprocessing.")
            logger.info("The ReturnsProcessor will calculate returns based on market hours and data availability.")
            logger.info("Monitor the returns processing logs to track progress.")


def main():
    parser = argparse.ArgumentParser(description='Fix NULL stock returns by reprocessing events')
    parser.add_argument('--limit', type=int, help='Limit number of events to process')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for processing (default: 10)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    
    args = parser.parse_args()
    
    reprocessor = NullReturnsReprocessor(dry_run=args.dry_run)
    reprocessor.run(limit=args.limit, batch_size=args.batch_size)


if __name__ == "__main__":
    main()