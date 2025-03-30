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

from utils.DataManagerCentral import DataManager
from utils.log_config import setup_logging, get_logger

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
    return parser.parse_args()

def main():
    try:
        # Parse command line args
        args = parse_args()
        
        # Set feature flags based on arguments
        import utils.feature_flags as feature_flags
        
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
        
        # Set up signal handlers for clean shutdown
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, initiating shutdown")
            print("\nShutting down EventTrader...")
            manager.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler) # kill command
        
        # Start manager
        logger.info("EventTrader is now running")
        manager.start()
        
        # If manager.start() returns, keep alive
        while True:
            time.sleep(10)
            
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