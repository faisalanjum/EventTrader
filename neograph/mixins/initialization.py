import logging
import chromadb
import concurrent.futures
import threading
import os
import time


from eventtrader.keys import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
from chromadb.config import Settings
from ..Neo4jInitializer import Neo4jInitializer

logger = logging.getLogger(__name__)

class InitializationMixin:
    """
    Handles initialization, connection, and core setup for Neo4jProcessor.
    Owns the primary state attributes like database connections and configuration.
    """
    # Complete list of node types initialized in Neo4jInitializer
    REQUIRED_NODES = [
        "Company", 
        "MarketIndex", 
        "Sector", 
        "Industry", 
        "AdminReport",
        "Dividend"
    ]
    # Add more node types here as needed

    def __init__(self, event_trader_redis=None, uri=NEO4J_URI, username=NEO4J_USERNAME, password=NEO4J_PASSWORD):

        # Override with environment variables if available - Save it in .env file
        self.uri = uri
        self.username = username
        self.password = password
        self.manager = None  # Will be initialized when needed
        self.universe_data = None
        
        # Flag to track if we've processed an XBRL report
        self.xbrl_processed = False
        
        # Import feature flag
        from config.feature_flags import ENABLE_XBRL_PROCESSING, XBRL_WORKER_THREADS
        self.enable_xbrl = ENABLE_XBRL_PROCESSING
        
        # Only initialize XBRL resources if feature flag is enabled
        if self.enable_xbrl:
            # Add semaphore to limit concurrent XBRL operations
            self.xbrl_semaphore = threading.BoundedSemaphore(4)
            
            # Thread pool executor for XBRL processing
            self.xbrl_executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=XBRL_WORKER_THREADS,  
                thread_name_prefix="xbrl_worker"
            )
            logger.info(f"XBRL processing is enabled with {XBRL_WORKER_THREADS} worker threads")
        else:
            logger.info("XBRL processing is disabled via feature flag")
        
        # Initialize Redis clients if provided
        if event_trader_redis:
            self.event_trader_redis = event_trader_redis
            self.live_client = event_trader_redis.live_client
            self.hist_client = event_trader_redis.history_client
            self.source_type = event_trader_redis.source
            logger.info(f"Initialized Redis clients for source: {self.source_type}")
            
            # Test Redis access
            self._collect_redis_key_counts()
            self._initialize_chroma_db()


    def connect(self) -> bool:
        """Connect to Neo4j using Neo4jManager singleton"""
        try:
            # Import here to avoid circular imports
            from ..Neo4jConnection import get_manager
            
            # Use the singleton manager
            self.manager = get_manager()
            logger.info("Connected to Neo4j database using singleton manager")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False
        
    
    def close(self):
        """Close Neo4j connection"""
        if self.manager:
            self.manager.close()
            
        # Shutdown the thread pool executor if XBRL is enabled and executor exists
        if self.enable_xbrl and hasattr(self, 'xbrl_executor'):
            self.xbrl_executor.shutdown(wait=False)
            logger.info("Shut down XBRL thread pool executor")
    
    def is_initialized(self):
        """
        Check if Neo4j database is initialized with all required node types.
        
        Args:
            test_mode: If True, simulate that a node type is missing (for testing)
        """
        if not self.connect():
            return False
            
        try:
            # Use a simple query approach - faster and more reliable
            missing = []
            node_status = {}
            
            # Check each required node type with a separate query
            with self.manager.driver.session() as session:
                for node_type in self.REQUIRED_NODES:
                    result = session.run(f"MATCH (n:{node_type}) RETURN COUNT(n) > 0 AS exists").single()
                    exists = result["exists"]
                    
                    node_status[node_type] = exists
                    
                    if not exists:
                        missing.append(node_type)
                    
            # Database is initialized if no required nodes are missing
            initialized = len(missing) == 0
            
            if initialized:
                logger.info("Neo4j database fully initialized")
                logger.info(f"Node status: {node_status}")
            else:
                logger.info(f"Neo4j database needs initialization (missing: {', '.join(missing)})")
                logger.info(f"Node status: {node_status}")
                
            return initialized
                
        except Exception as e:
            logger.error(f"Error checking Neo4j initialization: {e}")
            return False
    
    def initialize(self, start_date=None):
        """
        Minimalistic initialization of Neo4j database.
        
        Args:
            start_date: Optional start date for date nodes in format 'YYYY-MM-DD'
        """
        # Skip if already initialized
        if self.is_initialized():
            logger.info("Neo4j database already initialized")
            return True
        
        # Load universe data if needed
        if not self.universe_data:
            self.universe_data = self._get_universe()
            if not self.universe_data:
                logger.warning("No company data found")
                return False
        
        # Initialize using Neo4jInitializer
        initializer = Neo4jInitializer(
            uri=self.uri,
            username=self.username,
            password=self.password,
            universe_data=self.universe_data
        )
        
        # One-time connection and initialization
        if not initializer.connect():
            logger.error("Failed to connect to Neo4j")
            return False
        
        try:
            # Initialize all nodes and relationships, including dates with the provided start date
            success = initializer.initialize_all(start_date=start_date)
            logger.info("Initialization " + ("succeeded" if success else "failed"))
            return success
        except Exception as e:
            logger.error(f"Error during initialization: {e}")
            return False
        finally:
            initializer.close()

    def _get_universe(self):

        # Return cached data if available
        if self.universe_data is not None:
            return self.universe_data
            
        # Use Neo4jInitializer's static method to load the data
        self.universe_data = Neo4jInitializer.get_tradable_universe()
        return self.universe_data

    def _collect_redis_key_counts(self):
        """Test access to Redis to ensure the sources are accessible"""


        # If no Redis client is available, just return early
        if not hasattr(self, 'hist_client') or not self.hist_client:
            logger.warning("No Redis client available for testing")
            return False
        
        patterns = {
            "news": ["news:withreturns:*", "news:withoutreturns:*"],
            "reports": ["reports:withreturns:*", "reports:withoutreturns:*"],
            "transcripts": ["transcripts:withreturns:*", "transcripts:withoutreturns:*"],
        }
        
        logger.info(f"Getting keys count across Redis namespaces for all sources: {list(patterns.keys())}")
        results = {}
        
        for source, source_patterns in patterns.items():
                
            for pattern in source_patterns:
                keys = self.hist_client.client.keys(pattern)
                results[pattern] = len(keys)
                logger.info(f"Redis db: found {len(keys)} keys matching {pattern}")
                
        return results



    def _initialize_chroma_db(self):
        """Initialize ChromaDB for embedding storage/caching if enabled"""
        try:
            from config.feature_flags import ENABLE_NEWS_EMBEDDINGS, CHROMADB_PERSIST_DIRECTORY, USE_CHROMADB_CACHING
            
            logger.info(f"Initializing ChromaDB: ENABLE_NEWS_EMBEDDINGS={ENABLE_NEWS_EMBEDDINGS}, USE_CHROMADB_CACHING={USE_CHROMADB_CACHING}")
            
            if not ENABLE_NEWS_EMBEDDINGS or not USE_CHROMADB_CACHING:
                logger.info("ChromaDB initialization skipped because embeddings or caching are disabled")
                self.chroma_client = None
                self.chroma_collection = None
                return
                
            # Ensure persistence directory exists
            logger.info(f"Using ChromaDB persist directory: {CHROMADB_PERSIST_DIRECTORY}")
            os.makedirs(CHROMADB_PERSIST_DIRECTORY, exist_ok=True)
            
            # Initialize client with persistent storage
            self.chroma_client = chromadb.Client(Settings(
                is_persistent=True,
                persist_directory=CHROMADB_PERSIST_DIRECTORY
            ))
            
            # Create or get collection with retry
            for retry in range(3):
                try:
                    self.chroma_collection = self.chroma_client.get_or_create_collection(
                        name="news",
                        metadata={"hnsw:space": "cosine"}
                    )
                    count = self.chroma_collection.count()
                    logger.info(f"✅ ChromaDB initialized successfully with {count} embeddings")
                    return
                except Exception as e:
                    logger.warning(f"ChromaDB initialization retry {retry+1}/3 failed: {e}")
                    if retry < 2:
                        time.sleep(1)
                    else:
                        raise
        except Exception as e:
            logger.warning(f"❌ ChromaDB initialization error: {e}")
            self.chroma_client = None
            self.chroma_collection = None

