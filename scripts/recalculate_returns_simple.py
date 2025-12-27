#!/usr/bin/env python3
"""
Simple script to directly recalculate returns for existing events.
This bypasses the normal pipeline and directly calculates returns.

Usage:
    python scripts/recalculate_returns_simple.py --event-id "EVENT_ID" [--source news]
"""

import argparse
import json
import logging
from datetime import datetime
import pytz

from redisDB.redisClasses import EventTraderRedis
from redisDB.redis_constants import RedisKeys
from eventReturns.EventReturnsManager import EventReturnsManager
from utils.log_config import setup_logging

# Setup logging
logger = setup_logging(name="recalc_returns")


def recalculate_returns(event_id: str, source_type: str = "news"):
    """Directly recalculate returns for an event"""
    
    # Initialize components
    redis = EventTraderRedis()
    stock_universe = redis.get_stock_universe()
    event_returns_manager = EventReturnsManager(
        stock_universe, 
        polygon_subscription_delay=900  # 15 minutes for basic subscription
    )
    
    # Find the event
    event_data = None
    current_key = None
    
    # Check all possible locations
    for client, prefix in [(redis.live_client, "live"), (redis.history_client, "hist")]:
        for suffix in ["processed", "withreturns", "withoutreturns"]:
            key = f"{source_type}:{prefix}:{suffix}:{event_id}"
            data = client.get(key)
            if data:
                event_data = json.loads(data)
                current_key = key
                logger.info(f"Found event at: {key}")
                break
        if event_data:
            break
    
    if not event_data:
        logger.error(f"Event {event_id} not found")
        return False
    
    # Prepare event for returns calculation
    event = {
        'event_id': event_id,
        'created': event_data.get('created'),
        'symbols': event_data.get('symbols', []),
        'metadata': event_data.get('metadata', {})
    }
    
    logger.info(f"Calculating returns for event: {event_id}")
    logger.info(f"Created: {event['created']}")
    logger.info(f"Symbols: {event['symbols']}")
    
    # Calculate returns
    try:
        event_returns = event_returns_manager.process_events([event])
        
        if event_returns and event_returns[0].returns:
            returns = event_returns[0].returns
            logger.info("Returns calculated successfully:")
            logger.info(json.dumps(returns, indent=2))
            
            # Update the event data
            event_data['returns'] = returns
            
            # Check if all returns are complete
            all_complete = True
            for symbol_returns in returns['symbols'].values():
                if any(ret is None for ret in symbol_returns.values()):
                    all_complete = False
                    break
            
            # Determine destination
            client = redis.live_client if ":live:" in current_key else redis.history_client
            
            if all_complete:
                new_key = RedisKeys.get_key(
                    source_type=source_type,
                    key_type=RedisKeys.SUFFIX_WITHRETURNS,
                    identifier=event_id,
                    prefix_type="PREFIX_LIVE" if ":live:" in current_key else "PREFIX_HIST"
                )
                logger.info(f"All returns complete, moving to: {new_key}")
            else:
                new_key = RedisKeys.get_key(
                    source_type=source_type,
                    key_type=RedisKeys.SUFFIX_WITHOUTRETURNS,
                    identifier=event_id,
                    prefix_type="PREFIX_LIVE" if ":live:" in current_key else "PREFIX_HIST"
                )
                logger.info(f"Some returns pending, moving to: {new_key}")
            
            # Save updated data
            pipe = client.client.pipeline(transaction=True)
            pipe.set(new_key, json.dumps(event_data))
            if new_key != current_key:
                pipe.delete(current_key)
            pipe.execute()
            
            logger.info("Event updated successfully")
            return True
            
        else:
            logger.warning("No returns calculated")
            return False
            
    except Exception as e:
        logger.error(f"Failed to calculate returns: {e}", exc_info=True)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Directly recalculate returns for existing events"
    )
    parser.add_argument(
        "--event-id",
        required=True,
        help="Event ID to recalculate (e.g., '12345.2024-01-15T10:30:00')"
    )
    parser.add_argument(
        "--source",
        choices=["news", "reports", "transcripts"],
        default="news",
        help="Source type (default: news)"
    )
    
    args = parser.parse_args()
    
    success = recalculate_returns(args.event_id, args.source)
    
    if not success:
        exit(1)


if __name__ == "__main__":
    main()