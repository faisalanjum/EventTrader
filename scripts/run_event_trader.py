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
# Import Neo4jProcessor - used in all workflows now
from utils.Neo4jProcessor import Neo4jProcessor

# Make sure logs directory exists
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(logs_dir, exist_ok=True)

def parse_args():
    parser = argparse.ArgumentParser(description='Run EventTrader system')
    parser.add_argument('--from-date', type=str, required=True, 
                        help='Start date in YYYY-MM-DD format')
    parser.add_argument('--to-date', type=str, required=True, 
                        help='End date in YYYY-MM-DD format')
    parser.add_argument('--log-file', type=str, default=None,
                        help='Log file path (default: auto-generated in logs directory)')
    parser.add_argument('--check-interval', type=int, default=300,
                        help='Interval in seconds to check system status (default: 300)')
    # Keep Neo4j init flag for testing purposes
    parser.add_argument('--neo4j-init-only', action='store_true',
                        help='Only initialize Neo4j database and exit')
    # Add flag to skip Neo4j initialization if needed
    parser.add_argument('--skip-neo4j', action='store_true',
                        help='Skip Neo4j initialization check')
    return parser.parse_args()

def initialize_neo4j(logger, manager=None):
    """Initialize Neo4j database
    
    Args:
        logger: Logger instance
        manager: Optional DataManager instance
        
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    logger.info("Initializing Neo4j database...")
    
    # If DataManager is provided, use its initialize_neo4j method
    if manager:
        logger.info("Using DataManager to initialize Neo4j")
        return manager.initialize_neo4j()
        
    # Fallback for direct initialization when manager not available
    from utils.Neo4jProcessor import Neo4jProcessor
    neo4j = Neo4jProcessor()
    
    try:
        if not neo4j.connect():
            logger.error("Failed to connect to Neo4j database")
            return False
            
        # Initialize the database (idempotent)
        success = neo4j.initialize()
        return success
    except Exception as e:
        logger.error(f"Neo4j initialization failed: {e}")
        return False
    finally:
        # Ensure connection is closed even if an error occurs
        neo4j.close()

def main():
    try:
        # Parse command line args
        args = parse_args()
        
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
        logger.info(f"Logs will be written to: {log_path}")
        
        # Handle Neo4j initialization only mode
        if args.neo4j_init_only:
            # Just initialize Neo4j and exit (for testing)
            success = initialize_neo4j(logger)
            print(f"Neo4j initialization {'successful' if success else 'failed'}")
            sys.exit(0 if success else 1)
        
        # Create DataManager before Neo4j initialization
        manager = DataManager(date_from=args.from_date, date_to=args.to_date)
        
        # Initialize Neo4j as part of regular workflow (unless skipped)
        if not args.skip_neo4j:
            logger.info("Initializing Neo4j using DataManager...")
            neo4j_success = initialize_neo4j(logger, manager)
            if neo4j_success:
                logger.info("Neo4j initialization completed successfully")
            else:
                logger.error("Neo4j initialization failed. EventTrader requires Neo4j to function properly.")
                logger.error("Use --skip-neo4j flag if you want to proceed without Neo4j (some features may not work).")
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
        
        # Start manager (exactly like in the notebook)
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