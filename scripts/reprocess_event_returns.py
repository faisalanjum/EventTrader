#!/usr/bin/env python3
"""
Script to re-process events through the returns calculation pipeline.
This allows re-submitting events that already exist in the system for returns recalculation.

Usage:
    python scripts/reprocess_event_returns.py --event-id "EVENT_ID" [--source-type news|reports|transcripts]
    python scripts/reprocess_event_returns.py --all-withoutreturns [--source-type news|reports|transcripts] [--limit 10]
"""

import argparse
import json
import logging
from datetime import datetime, timezone
import pytz
from typing import Optional, List, Dict

from redisDB.redisClasses import EventTraderRedis
from redisDB.redis_constants import RedisKeys
from eventReturns.EventReturnsManager import EventReturnsManager
from utils.log_config import setup_logging

# Setup logging
logger = setup_logging(name="reprocess_returns")


class EventReprocessor:
    """Handles re-processing of events through the returns pipeline"""
    
    def __init__(self, source_type: str = "news"):
        self.source_type = source_type
        self.redis = EventTraderRedis()
        self.live_client = self.redis.live_client
        self.hist_client = self.redis.history_client
        
        # Get stock universe for returns manager
        self.stock_universe = self.redis.get_stock_universe()
        
        # Initialize EventReturnsManager with 15-minute delay for basic Polygon subscription
        self.polygon_subscription_delay = 900  # 15 minutes
        self.event_returns_manager = EventReturnsManager(
            self.stock_universe, 
            polygon_subscription_delay=self.polygon_subscription_delay
        )
        
        self.ny_tz = pytz.timezone("America/New_York")
        self.pending_zset = RedisKeys.get_returns_keys(self.source_type)['pending']
        
        logger.info(f"Initialized EventReprocessor for source: {source_type}")
        logger.info(f"Pending ZSET: {self.pending_zset}")
    
    def find_event(self, event_id: str) -> Optional[tuple[str, Dict, str]]:
        """Find an event in any namespace (processed, withreturns, withoutreturns)
        
        Returns:
            tuple: (namespace, event_data, redis_key) or None if not found
        """
        namespaces = [
            (RedisKeys.SUFFIX_PROCESSED, "processed"),
            (RedisKeys.SUFFIX_WITHRETURNS, "withreturns"),
            (RedisKeys.SUFFIX_WITHOUTRETURNS, "withoutreturns")
        ]
        
        # Check both live and hist prefixes
        for client, prefix in [(self.live_client, "live"), (self.hist_client, "hist")]:
            for suffix, namespace in namespaces:
                key = RedisKeys.get_key(
                    source_type=self.source_type,
                    key_type=suffix,
                    identifier=event_id,
                    prefix_type=f"PREFIX_{prefix.upper()}"
                )
                
                data = client.get(key)
                if data:
                    logger.info(f"Found event in {prefix}:{namespace} at key: {key}")
                    return namespace, json.loads(data), key
        
        logger.warning(f"Event {event_id} not found in any namespace")
        return None
    
    def move_to_processed(self, event_id: str, event_data: Dict, current_key: str) -> bool:
        """Move an event back to processed namespace for re-processing
        
        Args:
            event_id: The event identifier
            event_data: The event data dictionary
            current_key: The current Redis key where event is stored
            
        Returns:
            bool: True if successful
        """
        try:
            # Determine client based on current key
            client = self.live_client if ":live:" in current_key else self.hist_client
            
            # Create processed key
            processed_key = RedisKeys.get_key(
                source_type=self.source_type,
                key_type=RedisKeys.SUFFIX_PROCESSED,
                identifier=event_id,
                prefix_type="PREFIX_LIVE" if ":live:" in current_key else "PREFIX_HIST"
            )
            
            # Clear any existing returns data
            if 'returns' in event_data:
                del event_data['returns']
            
            # Atomic move using pipeline
            pipe = client.client.pipeline(transaction=True)
            pipe.set(processed_key, json.dumps(event_data))
            pipe.delete(current_key)
            
            # Update tracking metadata
            meta_key = f"tracking:meta:{self.source_type}:{event_id}"
            pipe = client.mark_lifecycle_timestamp(
                meta_key,
                "reprocessed_at",
                external_pipe=pipe
            ) or pipe
            
            success = all(pipe.execute())
            
            if success:
                logger.info(f"Successfully moved {event_id} to processed namespace")
                
                # Publish to trigger ReturnsProcessor
                channel = RedisKeys.get_pubsub_channel(self.source_type)
                client.client.publish(channel, event_id)
                logger.info(f"Published to channel: {channel}")
                
                # Remove any existing pending returns for this event
                self._clear_pending_returns(event_id)
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to move event to processed: {e}", exc_info=True)
            return False
    
    def _clear_pending_returns(self, event_id: str):
        """Clear any pending returns for an event from the ZSET"""
        try:
            # Remove all return types for this event
            for return_type in ['hourly', 'session', 'daily']:
                item_key = f"{event_id}:{return_type}"
                removed = self.live_client.client.zrem(self.pending_zset, item_key)
                if removed:
                    logger.info(f"Removed pending return: {item_key}")
        except Exception as e:
            logger.error(f"Failed to clear pending returns: {e}", exc_info=True)
    
    def reprocess_event(self, event_id: str) -> bool:
        """Re-process a single event through the returns pipeline
        
        Args:
            event_id: The event identifier (e.g., "12345.2024-01-15T10:30:00")
            
        Returns:
            bool: True if successful
        """
        logger.info(f"Attempting to reprocess event: {event_id}")
        
        # Find the event
        result = self.find_event(event_id)
        if not result:
            return False
        
        namespace, event_data, current_key = result
        
        # If already in processed, just republish
        if namespace == "processed":
            logger.info("Event already in processed namespace, republishing...")
            channel = RedisKeys.get_pubsub_channel(self.source_type)
            self.live_client.client.publish(channel, event_id)
            return True
        
        # Move to processed namespace
        return self.move_to_processed(event_id, event_data, current_key)
    
    def get_events_without_returns(self, limit: Optional[int] = None) -> List[str]:
        """Get all events currently in withoutreturns namespace
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of event IDs
        """
        events = []
        pattern_live = f"{self.source_type}:live:withoutreturns:*"
        pattern_hist = f"{self.source_type}:hist:withoutreturns:*"
        
        # Scan both live and hist
        for pattern in [pattern_live, pattern_hist]:
            for key in self.live_client.client.scan_iter(pattern):
                event_id = key.decode().split(':')[-1]
                events.append(event_id)
                
                if limit and len(events) >= limit:
                    return events
        
        return events
    
    def reprocess_all_without_returns(self, limit: Optional[int] = None) -> tuple[int, int]:
        """Re-process all events currently in withoutreturns namespace
        
        Args:
            limit: Maximum number of events to process
            
        Returns:
            tuple: (successful_count, failed_count)
        """
        events = self.get_events_without_returns(limit)
        logger.info(f"Found {len(events)} events in withoutreturns namespace")
        
        successful = 0
        failed = 0
        
        for i, event_id in enumerate(events, 1):
            logger.info(f"Processing {i}/{len(events)}: {event_id}")
            
            if self.reprocess_event(event_id):
                successful += 1
            else:
                failed += 1
        
        return successful, failed


def main():
    parser = argparse.ArgumentParser(
        description="Re-process events through the returns calculation pipeline"
    )
    parser.add_argument(
        "--event-id",
        help="Specific event ID to reprocess (e.g., '12345.2024-01-15T10:30:00')"
    )
    parser.add_argument(
        "--all-withoutreturns",
        action="store_true",
        help="Reprocess all events currently in withoutreturns namespace"
    )
    parser.add_argument(
        "--source-type",
        choices=["news", "reports", "transcripts"],
        default="news",
        help="Source type (default: news)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of events to process (for --all-withoutreturns)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.event_id and not args.all_withoutreturns:
        parser.error("Either --event-id or --all-withoutreturns must be specified")
    
    # Initialize reprocessor
    reprocessor = EventReprocessor(source_type=args.source_type)
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
        
        if args.event_id:
            result = reprocessor.find_event(args.event_id)
            if result:
                namespace, event_data, key = result
                logger.info(f"Would reprocess event from {namespace} namespace")
                logger.info(f"Current key: {key}")
                logger.info(f"Has returns: {'returns' in event_data}")
        else:
            events = reprocessor.get_events_without_returns(args.limit)
            logger.info(f"Would reprocess {len(events)} events")
            for event_id in events[:10]:  # Show first 10
                logger.info(f"  - {event_id}")
            if len(events) > 10:
                logger.info(f"  ... and {len(events) - 10} more")
        
        return
    
    # Execute reprocessing
    if args.event_id:
        success = reprocessor.reprocess_event(args.event_id)
        if success:
            logger.info(f"Successfully queued {args.event_id} for returns recalculation")
            logger.info("The ReturnsProcessor will pick it up from the processed namespace")
        else:
            logger.error(f"Failed to reprocess {args.event_id}")
            exit(1)
    else:
        successful, failed = reprocessor.reprocess_all_without_returns(args.limit)
        logger.info(f"\nReprocessing complete:")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Failed: {failed}")
        
        if failed > 0:
            exit(1)


if __name__ == "__main__":
    main()