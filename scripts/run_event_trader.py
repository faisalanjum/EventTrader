#!/usr/bin/env python3
"""
Simple EventTrader Runner
Run with: python scripts/run_event_trader.py --from-date 2025-03-04 --to-date 2025-03-05
"""

import argparse
import sys
import time
import signal
import os
from datetime import datetime

# Add parent directory to path to import from utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.DataManagerCentral import DataManager
from utils.log_config import setup_logging, get_logger
from redisDB.redis_constants import RedisKeys
from config.feature_flags import (
    ENABLE_HISTORICAL_DATA, ENABLE_LIVE_DATA, 
    QAEXCHANGE_EMBEDDING_BATCH_SIZE, WITHRETURNS_MAX_RETRIES
)

# Make sure logs directory exists
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(logs_dir, exist_ok=True)

def parse_args():
    parser = argparse.ArgumentParser(description='Run EventTrader system')
    parser.add_argument('--from-date', type=str, required=True, 
                        help='Start date in YYYY-MM-DD format')
    parser.add_argument('--to-date', type=str, required=True, 
                        help='End date in YYYY-MM-DD format')
    # Simplified flags (default is both enabled)
    parser.add_argument('-historical', action='store_true',
                        help='Enable historical data only (disables live)')
    parser.add_argument('-live', action='store_true',
                        help='Enable live data only (disables historical)')
    parser.add_argument('--log-file', type=str, default=None,
                        help='Log file path (default: auto-generated in logs directory)')
    parser.add_argument('--check-interval', type=int, default=300,
                        help='Interval in seconds to check system status (default: 300)')
    parser.add_argument('--neo4j-init-only', action='store_true',
                        help='Initialize Neo4j database only without running the full system')
    parser.add_argument('--ensure-neo4j-initialized', action='store_true',
                        help='Ensure Neo4j is initialized but continue running the system')
    parser.add_argument('--gap-fill', action='store_true',
                        help='Gap-fill mode: fetch historical data and exit after initial processing (for filling missing days)')
    return parser.parse_args()

def main():
    try:
        # Parse command line args
        args = parse_args()
        
        # Set feature flags based on arguments
        import config.feature_flags as feature_flags
        
        # If neither flag is set, enable both (default behavior)
        if not args.historical and not args.live:
            feature_flags.ENABLE_HISTORICAL_DATA = True
            feature_flags.ENABLE_LIVE_DATA = True
        else:
            # Enable only what was specifically requested
            feature_flags.ENABLE_HISTORICAL_DATA = args.historical
            feature_flags.ENABLE_LIVE_DATA = args.live
        
        # Setup logging using the existing log_config.py
        if args.log_file:
            # If a specific log file was provided, we still use it with setup_logging
            # We'll set the log_dir manually to ensure it uses the right path
            log_dir_bak = os.getcwd()
            os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            log_path = setup_logging(name="event_trader")
            os.chdir(log_dir_bak)
        else:
            # Use the default setup_logging, which will create a timestamped file
            log_path = setup_logging(name="event_trader")
        
        # Get a logger for this script
        logger = get_logger("event_trader_runner")
        
        # Log startup information
        logger.info(f"Starting EventTrader for dates: {args.from_date} to {args.to_date}")
        logger.info(f"Data sources: Historical={feature_flags.ENABLE_HISTORICAL_DATA}, Live={feature_flags.ENABLE_LIVE_DATA}")
        logger.info(f"Logs will be written to: {log_path}")
        
        # Create and initialize DataManager
        logger.info("Creating DataManager...")
        manager = DataManager(date_from=args.from_date, date_to=args.to_date)
        
        # Check if Neo4j was initialized properly
        if not manager.has_neo4j():
            logger.error("Neo4j initialization failed. EventTrader requires Neo4j to function properly.")
            print("Neo4j initialization failed. See logs for details. Exiting.")
            sys.exit(1)
        
        # If neo4j-init-only flag is set, exit after initialization
        if args.neo4j_init_only:
            logger.info("Neo4j initialization completed successfully. Exiting as requested.")
            print("Neo4j initialization completed successfully.")
            manager.stop()  # Clean up any open connections
            sys.exit(0)
            
        # If ensure-neo4j-initialized flag is set, check and log but don't exit
        if args.ensure_neo4j_initialized:
            logger.info("Neo4j initialization check completed successfully. Continuing with system startup.")
            print("Neo4j initialization check completed successfully.")
            # Do NOT call manager.stop() here - continue with the regular process
        
        # Set up signal handlers for clean shutdown
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, initiating shutdown")
            print("\nShutting down EventTrader...")
            manager.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler) # kill command
        
        # Start manager
        logger.info("Starting DataManager processes...")
        start_success = manager.start()
        # Check if start was successful for all sources maybe?
        # For now, assume it proceeds unless there was a major error during init.
        logger.info("DataManager processes started.")

        # Define helper function to check if only withreturns items exist
        def only_withreturns_remain(redis_client, sources, date_range_id):
            """
            Check if only withreturns items remain with no other pipeline issues.
            
            Returns True only when:
            1. All normal processing is complete for all sources
            2. At least one source has items in withreturns namespace
            
            Args:
                redis_client: Redis client instance
                sources: List of sources to check
                date_range_id: Date range identifier for fetch complete keys
                
            Returns:
                bool: True if only withreturns remain, False otherwise
            """
            # First check: ANY source still has active processing = don't trigger reconciliation
            for source in sources:
                # 1. Check fetch complete flag
                fetch_key = f"batch:{source}:{date_range_id}:fetch_complete"
                if redis_client.get(fetch_key) != "1":
                    return False
                
                # 2. Check raw queue
                if redis_client.llen(f"{source}:{RedisKeys.RAW_QUEUE}") > 0:
                    return False
                
                # 3. Check pending returns
                if redis_client.zcard(RedisKeys.get_returns_keys(source)['pending']) > 0:
                    return False
                
                # 4. Check withoutreturns namespace
                withoutreturns_pattern = f"{source}:{RedisKeys.SUFFIX_WITHOUTRETURNS}:*"
                if any(True for _ in redis_client.scan_iter(withoutreturns_pattern, count=1)):
                    return False
            
            # At this point, ALL sources have passed the first 4 conditions
            # Now check if AT LEAST ONE source has withreturns items
            has_any_withreturns = False
            for source in sources:
                # Check if this source has any withreturns items
                withreturns_pattern = f"{source}:{RedisKeys.SUFFIX_WITHRETURNS}:*"
                if any(True for _ in redis_client.scan_iter(withreturns_pattern, count=1)):
                    has_any_withreturns = True
                    break
            
            return has_any_withreturns
        
        # Define helper function for gap-fill monitoring
        def monitor_gap_fill(manager_instance, date_from, date_to):
            """Monitor only data fetching and initial processing for gap-fill mode."""
            logger.info("Gap-fill mode: Will wait for data fetching and initial processing")
            interval = 30  # Check interval in seconds
            
            # Get Redis connection
            try:
                if 'news' not in manager_instance.sources or not manager_instance.sources['news'].redis:
                    raise ConnectionError("Can't access Redis client")
                redis = manager_instance.sources['news'].redis.live_client.client
                redis.ping()  # Verify connection
            except Exception as e:
                logger.error(f"Redis connection error: {e}")
                return False
                
            # Monitoring loop
            date_range_key = f"{date_from}-{date_to}"
            sources = [RedisKeys.SOURCE_NEWS, RedisKeys.SOURCE_REPORTS, RedisKeys.SOURCE_TRANSCRIPTS]
            
            while True:
                all_complete = True
                status = {}
                
                for source in sources:
                    # Use helper function to check initial processing conditions
                    if not check_initial_processing(redis, source, date_range_key, status):
                        all_complete = False
                        continue
                        
                    status[source] = "Complete"
                
                if all_complete:
                    logger.info("Gap-fill complete: All data fetched and initial processing done")
                    return True
                    
                logger.info(f"Gap-fill in progress: {status}. Waiting {interval}s...")
                time.sleep(interval)
        
        # Helper function to check initial processing conditions
        def check_initial_processing(redis_client, source, date_range_key, status_dict):
            """
            Check the first three conditions for processing completion:
            1. Fetch complete flag
            2. Raw queue empty
            3. Historical namespaces empty
            
            Args:
                redis_client: Redis client instance
                source: Source type (news, reports, transcripts)
                date_range_key: Date range identifier 
                status_dict: Dictionary to update with status messages
                
            Returns:
                bool: True if all conditions pass, False otherwise
            """
            # 1. Check fetch complete flag
            fetch_key = f"batch:{source}:{date_range_key}:fetch_complete"
            fetch_status = redis_client.get(fetch_key)
            if fetch_status != "1":
                status_dict[source] = f"Fetch Incomplete (Flag: {fetch_status})"
                return False
            
            # 2. Check raw queue
            raw_queue = f"{source}:{RedisKeys.RAW_QUEUE}"
            raw_len = redis_client.llen(raw_queue)
            if raw_len > 0:
                status_dict[source] = f"Raw Queue Not Empty (Len: {raw_len})"
                return False
            

            # If we are doing Check 2 above we need not check hist:raw below.
            # 3. Check hist namespace is empty (both raw and processed)
            hist_prefix = RedisKeys.get_prefixes(source)['hist']
            for suffix in [RedisKeys.SUFFIX_RAW, RedisKeys.SUFFIX_PROCESSED]:
                pattern = f"{hist_prefix}{suffix}:*"
                if any(True for _ in redis_client.scan_iter(pattern, count=100)):
                    status_dict[source] = f"Historical {suffix.capitalize()} Items Not Empty"
                    return False
            
            return True
        
        # --- MODIFIED Main Loop (Minimalistic Version) --- 
        if feature_flags.ENABLE_LIVE_DATA:
            # Keep process alive indefinitely for live data or live+historical
            logger.info("Live data enabled, keeping process alive indefinitely...")
            while True:
                time.sleep(60) # Check less frequently when just keeping alive
        elif feature_flags.ENABLE_HISTORICAL_DATA:
            # Historical only mode: Wait for processing related to this chunk to finish
            if args.gap_fill:
                # Use dedicated gap-fill monitoring - exits when fetching & initial processing complete
                if monitor_gap_fill(manager, args.from_date, args.to_date):
                    logger.info("Gap-fill completed. Skipping QA embeddings. Shutting down.")
                    manager.stop()
                    sys.exit(0)
                else:
                    logger.error("Gap-fill monitoring failed. Attempting clean shutdown.")
                    manager.stop()
                    sys.exit(1)
            else:
                logger.info("Historical-only mode: Monitoring Redis for chunk completion...")
                chunk_monitor_interval = 30 # Seconds between checks
            
            # --- Get Redis connection from existing manager --- 
            try:
                # Use the live client associated with the news source (any valid client works)
                if 'news' in manager.sources and manager.sources['news'].redis and manager.sources['news'].redis.live_client:
                    redis_conn = manager.sources['news'].redis.live_client.client
                    redis_conn.ping() # Verify connection
                    logger.info("Using existing Redis connection for monitoring.")
                else:
                    raise ConnectionError("Could not access Redis client via DataManager for monitoring")
            except Exception as redis_err:
                logger.error(f"Failed to get/verify Redis connection for monitoring: {redis_err}")
                print(f"ERROR: Failed to get/verify Redis connection for monitoring: {redis_err}", file=sys.stderr)
                # Cannot monitor, safest to exit to prevent shell script hanging
                manager.stop() # Attempt cleanup
                sys.exit(1)
            # -------------------------------------------------
            
            # Construct the expected fetch complete key format for this chunk
            date_range_key = f"{args.from_date}-{args.to_date}"
            sources_to_check = [RedisKeys.SOURCE_NEWS, RedisKeys.SOURCE_REPORTS, RedisKeys.SOURCE_TRANSCRIPTS]
            
            reconcile_triggered = False
            retries_waited = 0
            max_retries = WITHRETURNS_MAX_RETRIES
            
            while True:
                all_complete = True
                completion_status = {}

                for source in sources_to_check:
                    try:
                        # Use helper function to check initial processing conditions
                        if not check_initial_processing(redis_conn, source, date_range_key, completion_status):
                            all_complete = False
                            continue
                            
                        # 4. Check Pending Returns Set (indicates ReturnsProcessor work)
                        pending_key_base = RedisKeys.get_returns_keys(source)['pending']
                        pending_zset = pending_key_base # Key already includes source
                        pending_count = redis_conn.zcard(pending_zset)
                        if pending_count > 0:
                            all_complete = False
                            completion_status[source] = f"Pending Returns Not Empty (Count: {pending_count})"
                            continue
                            
                        # --- ADDED CHECKS for returns namespaces ---
                        # 5. Check withreturns Namespace (should be empty if Neo4j is consuming)
                        withreturns_pattern = f"{source}:{RedisKeys.SUFFIX_WITHRETURNS}:*"
                        withreturns_keys_exist = False
                        for _ in redis_conn.scan_iter(withreturns_pattern, count=100): # count helps efficiency
                            withreturns_keys_exist = True
                            break # Found at least one key, no need to scan further
                        if withreturns_keys_exist:
                            all_complete = False
                            completion_status[source] = f"WithReturns Namespace Not Empty"
                            continue 
                            
                        # 6. Check withoutreturns Namespace (should be empty if ReturnsProcessor finished)
                        withoutreturns_pattern = f"{source}:{RedisKeys.SUFFIX_WITHOUTRETURNS}:*"
                        withoutreturns_keys_exist = False
                        for _ in redis_conn.scan_iter(withoutreturns_pattern, count=100):
                            withoutreturns_keys_exist = True
                            break # Found at least one key
                        if withoutreturns_keys_exist:
                            all_complete = False
                            completion_status[source] = f"WithoutReturns Namespace Not Empty"
                            continue 
                        # --- END ADDED CHECKS ---
                            
                        # If all checks pass for this source
                        completion_status[source] = "Complete"

                    except Exception as e:
                        logger.warning(f"Redis check failed for source {source}: {e}. Assuming incomplete.")
                        all_complete = False
                        completion_status[source] = f"Redis Check Error: {e}"
                        break 

                if all_complete:
                    logger.info("All Redis checks indicate historical chunk processing is complete.")
                    break # Exit the monitoring loop
                else:
                    retries_waited += 1
                    
                    if retries_waited >= max_retries and not reconcile_triggered:
                        # Use helper function to check if only withreturns items remain
                        if only_withreturns_remain(redis_conn, sources_to_check, date_range_key):
                            logger.warning(f"Processing stuck with only withreturns items after {retries_waited} checks, forcing reconciliation...")
                            if hasattr(manager, 'neo4j_processor') and manager.neo4j_processor:
                                manager.neo4j_processor.reconcile_missing_items(max_items_per_type=None)
                                reconcile_triggered = True
                    
                    logger.info(f"Chunk processing not yet complete. Status: {completion_status}. Waiting {chunk_monitor_interval}s...")
                    time.sleep(chunk_monitor_interval)
            
            # <<<====== ADD EMBEDDING TRIGGER HERE ======>>>
            logger.info("Historical chunk processing appears complete. Attempting to generate QA embeddings...")
            try:
                if manager.has_neo4j() and hasattr(manager, 'neo4j_processor') and manager.neo4j_processor:
                    # Ensure we have the processor instance
                    neo4j_processor = manager.neo4j_processor
                    # Use the batch size from feature flags
                    embedding_batch_size = QAEXCHANGE_EMBEDDING_BATCH_SIZE
                    embedding_max_items = None # Process all found
                    logger.info(f"Calling batch_process_qaexchange_embeddings (batch={embedding_batch_size}, max={embedding_max_items})")
                    embedding_results = neo4j_processor.batch_process_qaexchange_embeddings(
                        batch_size=embedding_batch_size,
                        max_items=embedding_max_items
                    )
                    logger.info(f"QA Embedding generation finished with result: {embedding_results}")
                else:
                    logger.warning("Cannot generate QA embeddings: Neo4j processor not available or not initialized properly.")
            except Exception as embed_err:
                logger.error(f"Error during explicit QA embedding generation call: {embed_err}", exc_info=True)
            # <<<=======================================>>>

            logger.info("Historical chunk processing finished. Initiating shutdown for this process.")
            manager.stop() 
            logger.info("Shutdown complete. Exiting Python process.")
            sys.exit(0) 

        else:
            logger.info("No data sources enabled. Exiting.")
            manager.stop()
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        print("\nKeyboard interrupt received")
        if 'manager' in locals():
            manager.stop()
    except Exception as e:
        error_msg = f"FATAL ERROR: {e}"
        if 'logger' in locals():
            logger.error(error_msg, exc_info=True)
        else:
            # Fallback if logger isn't established yet
            print(error_msg, file=sys.stderr)
        
        if 'manager' in locals():
            try:
                manager.stop()
            except Exception as cleanup_error:
                if 'logger' in locals():
                    logger.error(f"Failed to clean up: {cleanup_error}")
                print(f"Failed to clean up: {cleanup_error}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 