import logging
import sys # Needed for command-line args processing
import argparse # Needed for command-line args processing

# Mixin Imports (Essential)
from .mixins.initialization import InitializationMixin
from .mixins.utility import UtilityMixin
from .mixins.news import NewsMixin
from .mixins.report import ReportMixin
from .mixins.transcript import TranscriptMixin
from .mixins.pubsub import PubSubMixin
from .mixins.embedding import EmbeddingMixin
from .mixins.xbrl import XbrlMixin
from .mixins.reconcile import ReconcileMixin

# Imports for Logger Setup and Standalone Functions
from utils.log_config import get_logger # For logger setup
from redisDB.redisClasses import EventTraderRedis # Needed by process_* functions
from .Neo4jInitializer import Neo4jInitializer # Needed by init_neo4j (using relative path)
from eventtrader.keys import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD # Needed by init_neo4j

# Setup logger (This line should be kept after imports)
logger = get_logger(__name__)


from .mixins.initialization import InitializationMixin
from .mixins.utility import UtilityMixin 
from .mixins.news import NewsMixin
from .mixins.report import ReportMixin
from .mixins.transcript import TranscriptMixin
from .mixins.pubsub import PubSubMixin
from .mixins.embedding import EmbeddingMixin
from .mixins.xbrl import XbrlMixin
from .mixins.reconcile import ReconcileMixin


class Neo4jProcessor(
    InitializationMixin, 
    UtilityMixin, 
    NewsMixin, 
    ReportMixin, 
    TranscriptMixin, 
    PubSubMixin, 
    EmbeddingMixin, 
    XbrlMixin, 
    ReconcileMixin):

    """
    A wrapper around Neo4jManager that provides integration with EventTrader workflow.
    This class delegates Neo4j operations to Neo4jManager while adding workflow-specific
    initialization and functionality.
    """
    
    pass

 # region: Initialization and Core Infrastructure - # Methods like connect, close, is_initialized, initialize, 
 # _get_universe, _collect_redis_key_counts, _initialize_chroma_db


# endregion


#### ISSUE IS None of Batch processing is working since data from redis queue comes in as single items- Not entirely True sometimes when you restart the system and there are items lined up, it uses batch processing.

# region: Primary Public Methods - # Methods like process_news_to_neo4j, process_reports_to_neo4j, process_pubsub_item, process_with_pubsub, stop_pubsub_processing

# endregion
    

# region: News Processing Pipeline - # Methods like _prepare_news_data, _process_deduplicated_news, _execute_news_database_operations, _create_news_node_from_data

# endregion


# region: Report Processing Pipeline - # Methods _prepare_report_data, _process_deduplicated_report, _execute_report_database_operations, _create_report_node_from_data, _process_report_companies

# endregion


# region: Common Utilities & Helpers : _extract_symbols_from_data, _extract_market_session, _extract_returns_schedule, 
#                                       _extract_return_metrics, _parse_list_field, _prepare_entity_relationship_params, 
#                                       _prepare_report_relationships, reconcile_missing_items

# endregion



# region: Database Operation Helpers : _create_influences_relationships, _reclassify_report_company_relationships, _process_xbrl

# endregion



########################### Transcripts Related Functions ##################################





####################################### END #################################################


# Function to initialize Neo4j database
def init_neo4j(check_only=False, start_date=None):
    """
    Initialize Neo4j database with required structure and company data
    
    Args:
        check_only: If True, only check if initialization is needed without actually performing it
        start_date: Optional start date for date nodes in format 'YYYY-MM-DD'
    """
    try:
        # First check if database is already initialized
        processor = Neo4jProcessor()
        if processor.is_initialized():
            logger.info("Neo4j database is already fully initialized. Skipping initialization.")
            return True
            
        # At this point, we know initialization is needed
        if check_only:
            logger.info("Neo4j database needs initialization, but check_only flag is set")
            return False
            
        # Database needs initialization, use the dedicated initializer class
        from neograph.Neo4jInitializer import Neo4jInitializer
        from eventtrader.keys import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
        
        logger.info("Starting Neo4j database initialization...")
        
        initializer = Neo4jInitializer(
            uri=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD
        )
        
        # Connect to Neo4j
        if not initializer.connect():
            logger.error("Failed to connect to Neo4j")
            return False
        
        try:
            # Initialize all nodes and relationships, including dates with the provided start date
            success = initializer.initialize_all(start_date=start_date)
            
            if success:
                logger.info("Neo4j database initialization completed successfully")
            else:
                logger.error("Neo4j database initialization failed")
                
            return success
        except Exception as e:
            logger.error(f"Neo4j initialization error: {str(e)}")
            return False
        finally:
            initializer.close()
            
    except Exception as e:
        logger.error(f"Neo4j initialization error: {str(e)}")
        return False

def process_news_data(batch_size=100, max_items=None, verbose=False, include_without_returns=True):
    """
    Process news data from Redis into Neo4j
    
    Args:
        batch_size: Number of news items to process in each batch
        max_items: Maximum number of news items to process. If None, process all items.
        verbose: Whether to enable verbose logging
        include_without_returns: Whether to process news from the withoutreturns namespace
    """
    processor = None
    try:
        # Set up logging for this run
        if verbose:
            logging.basicConfig(level=logging.INFO, 
                               format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Initialize Redis client for news data
        from redisDB.redisClasses import EventTraderRedis
        redis_client = EventTraderRedis(source='news')
        logger.info("Initialized Redis client for news data")
        
        # Initialize Neo4j processor with the Redis client
        processor = Neo4jProcessor(event_trader_redis=redis_client)
        if not processor.connect():
            logger.error("Cannot connect to Neo4j")
            return False
        
        # Make sure Neo4j is initialized first
        if not processor.is_initialized():
            logger.warning("Neo4j not initialized. Initializing now...")
            # Use the dedicated initializer to ensure market hierarchy is created
            if not init_neo4j():
                logger.error("Neo4j initialization failed, cannot process news")
                return False
        
        # Process news data with embedding generation handled internally
        logger.info(f"Processing news data to Neo4j with batch_size={batch_size}, max_items={max_items}, include_without_returns={include_without_returns}...")
        success = processor.process_news_to_neo4j(batch_size, max_items, include_without_returns)
        
        if success:
            logger.info("News data processing completed successfully")
        else:
            logger.error("News data processing failed")
            
        return success
    except Exception as e:
        logger.error(f"News data processing error: {str(e)}")
        return False
    finally:
        if processor:
            processor.close()
        logger.info("News processing completed")

def process_report_data(batch_size=100, max_items=None, verbose=False, include_without_returns=True):
    """
    Process SEC report data from Redis into Neo4j
    
    Args:
        batch_size: Number of report items to process in each batch
        max_items: Maximum number of report items to process. If None, process all items.
        verbose: Whether to enable verbose logging
        include_without_returns: Whether to process reports from the withoutreturns namespace
    """
    processor = None
    try:
        # Set up logging for this run
        if verbose:
            logging.basicConfig(level=logging.INFO, 
                               format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Initialize Redis client for news data (reports use the same Redis)
        from redisDB.redisClasses import EventTraderRedis
        redis_client = EventTraderRedis(source='news')
        logger.info("Initialized Redis client for report data")
        
        # Initialize Neo4j processor with the Redis client
        processor = Neo4jProcessor(event_trader_redis=redis_client)
        if not processor.connect():
            logger.error("Cannot connect to Neo4j")
            return False
            
        # Make sure Neo4j is initialized first
        if not processor.is_initialized():
            logger.warning("Neo4j not initialized. Initializing now...")
            # Use the dedicated initializer to ensure market hierarchy is created
            if not init_neo4j():
                logger.error("Neo4j initialization failed, cannot process reports")
                return False
        
        
        # Process report data
        logger.info(f"Processing report data to Neo4j with batch_size={batch_size}, max_items={max_items}, include_without_returns={include_without_returns}...")
        success = processor.process_reports_to_neo4j(batch_size, max_items, include_without_returns)
        
        if success:
            logger.info("Report data processing completed successfully")
        else:
            logger.error("Report data processing failed")
            
        return success
    except Exception as e:
        logger.error(f"Report data processing error: {str(e)}")
        return False
    finally:
        if processor:
            processor.close()
        logger.info("Report processing completed")


def process_transcript_data(batch_size=5, max_items=None, verbose=False, include_without_returns=True, process_embeddings=True):
    """
    Process transcript data from Redis into Neo4j
    
    Args:
        batch_size: Number of transcript items to process in each batch
        max_items: Maximum number of transcript items to process. If None, process all items.
        verbose: Whether to enable verbose logging
        include_without_returns: Whether to process transcripts from the withoutreturns namespace
    """
    processor = None
    try:
        # Set up logging for this run
        if verbose:
            logging.basicConfig(level=logging.INFO, 
                               format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Initialize Redis client for transcript data (uses the same Redis as news/reports)
        from redisDB.redisClasses import EventTraderRedis
        redis_client = EventTraderRedis(source='news')
        logger.info("Initialized Redis client for transcript data")
        
        # Initialize Neo4j processor with the Redis client
        processor = Neo4jProcessor(event_trader_redis=redis_client)
        if not processor.connect():
            logger.error("Cannot connect to Neo4j")
            return False
            
        # Make sure Neo4j is initialized first
        if not processor.is_initialized():
            logger.warning("Neo4j not initialized. Initializing now...")
            # Use the dedicated initializer to ensure market hierarchy is created
            if not init_neo4j():
                logger.error("Neo4j initialization failed, cannot process transcripts")
                return False
        
        # Process transcript data
        logger.info(f"Processing transcript data to Neo4j with batch_size={batch_size}, max_items={max_items}, include_without_returns={include_without_returns}...")
        success = processor.process_transcripts_to_neo4j(batch_size, max_items, include_without_returns)

        if success and processor and process_embeddings:
            processor.batch_process_qaexchange_embeddings(batch_size=batch_size, max_items=max_items)


        if success:
            logger.info("Transcript data processing completed successfully")
        else:
            logger.error("Transcript data processing failed")
            
        return success
        
    except Exception as e:
        logger.error(f"Transcript data processing error: {str(e)}")
        return False
    
    finally:
        if processor:
            processor.close()
        logger.info("Transcript processing completed")

        


if __name__ == "__main__":
    import sys
    import argparse
    
    # Set up command line arguments
    parser = argparse.ArgumentParser(description="Neo4j processor for EventTrader")
    parser.add_argument("mode", choices=["init", "news", "reports", "transcripts", "all"], default="init", nargs="?",
                        help="Mode: 'init' (initialize Neo4j), 'news' (process news), 'reports' (process reports), 'transcripts' (process transcripts), 'all' (all of the above)")
    parser.add_argument("--batch", type=int, default=10, 
                        help="Number of items to process in each batch")
    parser.add_argument("--max", type=int, default=0, 
                        help="Maximum number of items to process (0 for all items)")
    parser.add_argument("--verbose", "-v", action="store_true", 
                        help="Enable verbose logging")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Force process even if errors occur")
    parser.add_argument("--skip-without-returns", action="store_true",
                        help="Skip processing items from the withoutreturns namespace")
    parser.add_argument("--skip-news", action="store_true",
                        help="Skip processing news in 'all' mode")
    parser.add_argument("--skip-reports", action="store_true",
                        help="Skip processing reports in 'all' mode")
    parser.add_argument("--skip-transcripts", action="store_true",
                        help="Skip processing transcripts in 'all' mode")
    parser.add_argument("--start-date", type=str, default="2017-09-01",
                        help="Start date for date nodes in format 'YYYY-MM-DD'")
    
    args = parser.parse_args()
    
    # Enable verbose logging for command line operation
    if args.verbose:
        logging.basicConfig(level=logging.INFO, 
                           format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Convert batch size and max items
    batch_size = args.batch
    max_items = None if args.max == 0 else args.max
    include_without_returns = not args.skip_without_returns
    
    if args.mode == "init":
        # Run initialization 
        logger.info(f"Running Neo4j initialization with start date {args.start_date}...")
        init_neo4j(start_date=args.start_date)
    
    elif args.mode == "news":
        # Process news data
        logger.info(f"Processing news data with batch_size={batch_size}, max_items={max_items}, include_without_returns={include_without_returns}")
        process_news_data(batch_size, max_items, args.verbose, include_without_returns)
    
    elif args.mode == "reports":
        # Process report data
        logger.info(f"Processing report data with batch_size={batch_size}, max_items={max_items}, include_without_returns={include_without_returns}")
        process_report_data(batch_size, max_items, args.verbose, include_without_returns)
    
    elif args.mode == "transcripts":
        # Process transcript data
        logger.info(f"Processing transcript data with batch_size={batch_size}, max_items={max_items}, include_without_returns={include_without_returns}")
        process_transcript_data(batch_size, max_items, args.verbose, include_without_returns, process_embeddings=True)
    
    elif args.mode == "all":
        # Run initialization and all processing modes
        logger.info(f"Running complete Neo4j setup (batch_size={batch_size}, max_items={max_items}, include_without_returns={include_without_returns})...")
        
        # Initialize Neo4j first
        if init_neo4j(start_date=args.start_date):
            logger.info("Initialization successful, now processing data...")
            
            
            # Process news data if not skipped
            if not args.skip_news:
                logger.info("Processing news data...")
                process_news_data(batch_size, max_items, args.verbose, include_without_returns)
            else:
                logger.info("Skipping news processing (--skip-news flag used)")
            
            # Process report data if not skipped
            if not args.skip_reports:
                logger.info("Processing report data...")
                process_report_data(batch_size, max_items, args.verbose, include_without_returns)
            else:
                logger.info("Skipping report processing (--skip-reports flag used)")
                
            # Process transcript data if not skipped
            if not args.skip_transcripts:
                logger.info("Processing transcript data...")
                process_transcript_data(batch_size, max_items, args.verbose, include_without_returns, process_embeddings=True)
            else:
                logger.info("Skipping transcript processing (--skip-transcripts flag used)")
                
            logger.info("All processing completed.")
        else:
            logger.error("Initialization failed, skipping data processing")
    
    else:
        logger.error(f"Unknown mode: {args.mode}. Use 'init', 'news', 'reports', 'transcripts', or 'all'")
        print("Usage: python Neo4jProcessor.py [mode] [options]")
        print("  mode: 'init' (default), 'news', 'reports', 'transcripts', or 'all'")
        print("  --batch N: Number of items to process in each batch (default: 10)")
        print("  --max N: Maximum number of items to process (0 for all, default: 0)")
        print("  --verbose/-v: Enable verbose logging")
        print("  --skip-without-returns: Skip processing items without returns")
        print("  --skip-news: Skip processing news in 'all' mode")
        print("  --skip-reports: Skip processing reports in 'all' mode")
        print("  --skip-transcripts: Skip processing transcripts in 'all' mode")


    

