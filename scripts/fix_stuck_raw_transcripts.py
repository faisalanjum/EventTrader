#!/usr/bin/env python3
"""
Fix for transcripts stuck in raw state but not in processing queue.
This happens when the pipeline operation partially succeeds - storing the key but not pushing to queue.
"""

import logging
from redisDB.redisClasses import EventTraderRedis
from utils.log_config import setup_logging

# Setup logging
logger = setup_logging(name="fix_stuck_transcripts")
if isinstance(logger, str):
    # setup_logging returned a string (log path), create logger manually
    import logging as log_module
    logger = log_module.getLogger("fix_stuck_transcripts")


def fix_stuck_transcripts():
    """Find raw transcript keys and push them to the processing queue"""
    redis = EventTraderRedis()
    hist_client = redis.history_client
    
    # Find all raw transcript keys
    pattern = "transcripts:hist:raw:*"
    raw_keys = []
    
    # Use SCAN to avoid blocking Redis
    cursor = 0
    while True:
        cursor, keys = hist_client.client.scan(cursor, match=pattern, count=100)
        raw_keys.extend(keys)
        if cursor == 0:
            break
    
    logger.info(f"Found {len(raw_keys)} raw transcript keys")
    
    if not raw_keys:
        logger.info("No stuck transcripts found")
        return
    
    # Check the raw queue
    raw_queue = "transcripts:queues:raw"
    queue_length = hist_client.client.llen(raw_queue)
    logger.info(f"Current raw queue length: {queue_length}")
    
    # Push each raw key to the queue
    pipeline = hist_client.client.pipeline()
    for key in raw_keys:
        # The keys are already full keys like "transcripts:hist:raw:SYMBOL_DATETIME"
        logger.info(f"Pushing to queue: {key}")
        pipeline.lpush(raw_queue, key)
    
    # Execute the pipeline
    results = pipeline.execute()
    success_count = sum(1 for r in results if r)
    
    logger.info(f"Successfully pushed {success_count}/{len(raw_keys)} keys to the raw queue")
    
    # Verify the new queue length
    new_queue_length = hist_client.client.llen(raw_queue)
    logger.info(f"New raw queue length: {new_queue_length}")
    
    # Check if BaseProcessor is running
    logger.info("\nNOTE: Make sure TranscriptProcessor is running to process these items.")
    logger.info("The processor should pick up these items from the queue and move them through the pipeline.")


if __name__ == "__main__":
    fix_stuck_transcripts()