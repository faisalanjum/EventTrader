import logging
import os
from datetime import datetime
import sys
from pathlib import Path

# Add XBRL module to path if needed
sys.path.append(str(Path(__file__).parent.parent))
from XBRL.Neo4jManager import Neo4jManager

# Set up logger
logger = logging.getLogger(__name__)

class Neo4jProcessor:
    """
    A wrapper around Neo4jManager that provides integration with EventTrader workflow.
    This class delegates Neo4j operations to Neo4jManager while adding workflow-specific
    initialization and functionality.
    """
    
    def __init__(self, event_trader_redis=None, uri="bolt://localhost:7687", username="neo4j", password="Next2020#"):
        """
        Initialize with Neo4j connection parameters and optional EventTrader Redis client
        
        Args:
            event_trader_redis: EventTraderRedis instance (optional)
            uri: Neo4j database URI
            username: Neo4j username
            password: Neo4j password
        """
        # Override with environment variables if available
        self.uri = os.environ.get("NEO4J_URI", uri)
        self.username = os.environ.get("NEO4J_USERNAME", username)
        self.password = os.environ.get("NEO4J_PASSWORD", password)
        self.manager = None  # Will hold Neo4jManager instance
        
        # Initialize Redis clients if provided
        if event_trader_redis:
            self.event_trader_redis = event_trader_redis
            self.live_client = event_trader_redis.live_client
            self.hist_client = event_trader_redis.history_client
            self.source_type = event_trader_redis.source
            logger.info(f"Initialized Redis clients for source: {self.source_type}")
            
            # Test Redis access
            self._test_redis_access()
    
    def connect(self):
        """Connect to Neo4j using Neo4jManager"""
        try:
            self.manager = Neo4jManager(
                uri=self.uri,
                username=self.username,
                password=self.password
            )
            logger.info("Connected to Neo4j database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False
    
    def close(self):
        """Close Neo4j connection"""
        if self.manager:
            self.manager.close()
    
    def is_initialized(self):
        """Check if Neo4j database is already initialized with EventTrader nodes"""
        if not self.manager and not self.connect():
            return False
        
        try:
            with self.manager.driver.session() as session:
                # Check for initialization marker
                result = session.run(
                    "MATCH (i:Initialization {id: 'neo4j_init'}) RETURN count(i) as count"
                )
                is_init = result.single()["count"] > 0
                
                logger.info("Neo4j database is " + ("already initialized" if is_init else "not initialized"))
                return is_init
                
        except Exception as e:
            logger.error(f"Error checking Neo4j initialization status: {e}")
            return False
    
    def initialize(self):
        """
        Initialize Neo4j database with required structure.
        Uses MERGE to ensure idempotent operation.
        """
        # First check if already initialized
        if self.is_initialized():
            return True
            
        if not self.manager and not self.connect():
            return False
        
        try:
            with self.manager.driver.session() as session:
                # Create initialization structure
                session.run(
                    """
                    // Initialization marker
                    MERGE (i:Initialization {id: 'neo4j_init'})
                    ON CREATE SET i.status = 'complete',
                        i.timestamp = $timestamp
                        
                    // Basic reference data
                    MERGE (k:AdminReport {code: '10-K'})
                    ON CREATE SET k.label = '10-K Reports',
                        k.displayLabel = '10-K Reports'
                    
                    MERGE (q:AdminReport {code: '10-Q'})  
                    ON CREATE SET q.label = '10-Q Reports',
                        q.displayLabel = '10-Q Reports'
                    """,
                    timestamp=datetime.now().isoformat()
                )
                
                # Get tradable universe symbols
                symbols = self.get_tradable_universe()
                if symbols:
                    logger.info(f"Found {len(symbols)} symbols in tradable universe")
                else:
                    logger.warning("No symbols found in tradable universe")
                
                logger.info("Neo4j database initialized with basic structure")
                return True
                
        except Exception as e:
            logger.error(f"Error during Neo4j initialization: {e}")
            return False

    def get_tradable_universe(self):
        """
        Simple method to fetch tradable universe symbols from Redis
        
        Returns:
            list: List of tradable symbols, or empty list if not available
        """
        if not hasattr(self, 'hist_client') or not self.hist_client:
            logger.warning("No Redis client available to fetch tradable universe")
            return []
            
        try:
            # Fetch tradable universe from Redis using exact key
            if hasattr(self.hist_client, 'client'):
                key = "admin:tradable_universe:stock_universe"
                result = self.hist_client.client.get(key)
                
                if result:
                    # Parse JSON result
                    import json
                    universe = json.loads(result)
                    logger.info(f"Retrieved {len(universe)} symbols from tradable universe")
                    # Return just the list of symbols
                    return list(universe.keys())
                else:
                    logger.warning(f"Tradable universe key '{key}' not found in Redis")
                    return []
            else:
                logger.warning("Redis client doesn't have expected 'client' attribute")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching tradable universe: {e}")
            return []
            
    def _test_redis_access(self):
        """A simple diagnostic test to verify Redis access for all available sources"""
        if not hasattr(self, 'hist_client') or not self.hist_client:
            logger.warning("No Redis client available for testing")
            return False
            
        try:
            from utils.redisClasses import RedisKeys
            
            # Get all available source types
            all_sources = []
            try:
                # Try to get all sources from RedisKeys constants
                for attr in dir(RedisKeys):
                    if attr.startswith('SOURCE_') and not attr.startswith('__'):
                        source = getattr(RedisKeys, attr)
                        if isinstance(source, str):
                            all_sources.append(source)
                
                # Add current source if it's not already in the list
                if hasattr(self, 'source_type') and self.source_type not in all_sources:
                    all_sources.append(self.source_type)
                    
                if not all_sources:
                    # Fallback to at least testing the current source
                    all_sources = [self.source_type]
            except:
                # Fallback to current source
                all_sources = [self.source_type]
                
            logger.info(f"Testing Redis access for sources: {all_sources}")
            
            # Test key patterns for each source
            success = False
            for source in all_sources:
                try:
                    # Get key patterns for current source
                    keys_dict = RedisKeys.get_returns_keys(source)
                    withreturns_key = keys_dict.get('withreturns', f"{source}:withreturns")
                    withoutreturns_key = keys_dict.get('withoutreturns', f"{source}:withoutreturns")
                    
                    # Test withreturns keys
                    pattern = f"{withreturns_key}:*"
                    keys = self.hist_client.client.keys(pattern)
                    logger.info(f"Redis test - found {len(keys)} keys matching {pattern}")
                    if len(keys) > 0:
                        success = True
                        
                    # Test withoutreturns keys
                    pattern = f"{withoutreturns_key}:*"
                    keys = self.hist_client.client.keys(pattern)
                    logger.info(f"Redis test - found {len(keys)} keys matching {pattern}")
                    if len(keys) > 0:
                        success = True
                except Exception as e:
                    logger.warning(f"Error testing Redis for source {source}: {e}")
            
            return success
                
        except Exception as e:
            logger.warning(f"Redis access test failed: {e}")
            return False

    def populate_company_nodes(self):
        """
        Simple placeholder for populating Neo4j with company data
        This will be implemented in more detail later
        """
        symbols = self.get_tradable_universe()
        if not symbols:
            logger.warning("No symbols found for company node creation")
            return False
            
        logger.info(f"Retrieved {len(symbols)} symbols for future company node creation")
        # Placeholder for actual implementation
        return True

# Simple function to run initialization
def init_neo4j():
    """Initialize Neo4j with required nodes"""
    processor = Neo4jProcessor()
    try:
        if processor.connect() and processor.initialize():
            logger.info("Neo4j initialization successful")
            return True
        logger.error("Neo4j initialization failed")
        return False
    except Exception as e:
        logger.error(f"Neo4j initialization error: {e}")
        return False
    finally:
        processor.close()

if __name__ == "__main__":
    # Run initialization directly if this script is executed
    init_neo4j() 