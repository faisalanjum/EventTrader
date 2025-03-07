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
    
    def __init__(self, uri="bolt://localhost:7687", username="neo4j", password="Next2020#"):
        """Initialize with Neo4j connection parameters"""
        # Override with environment variables if available
        self.uri = os.environ.get("NEO4J_URI", uri)
        self.username = os.environ.get("NEO4J_USERNAME", username)
        self.password = os.environ.get("NEO4J_PASSWORD", password)
        self.manager = None  # Will hold Neo4jManager instance
        self.logger = logger
    
    def connect(self):
        """Connect to Neo4j using Neo4jManager"""
        try:
            # Initialize Neo4jManager (which automatically connects)
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
    
    def test_connection(self):
        """Test Neo4j connection using Neo4jManager"""
        if not self.manager:
            if not self.connect():
                return False
        
        return self.manager.test_connection()
    
    def close(self):
        """Close Neo4j connection"""
        if self.manager:
            self.manager.close()
    
    def is_initialized(self):
        """Check if Neo4j database is already initialized with EventTrader nodes"""
        if not self.manager:
            if not self.connect():
                return False
        
        try:
            with self.manager.driver.session() as session:
                # Check for initialization marker
                result = session.run(
                    "MATCH (i:Initialization {id: 'neo4j_init'}) RETURN count(i) as count"
                )
                is_init = result.single()["count"] > 0
                
                if is_init:
                    logger.info("Neo4j database is already initialized")
                else:
                    logger.info("Neo4j database needs initialization")
                    
                return is_init
                
        except Exception as e:
            logger.error(f"Error checking Neo4j initialization status: {e}")
            return False
    
    def initialize(self):
        """Create initialization marker node and minimal EventTrader data structure"""
        # First check if already initialized
        if self.is_initialized():
            return True
            
        if not self.manager:
            if not self.connect():
                return False
        
        try:
            with self.manager.driver.session() as session:
                # Create initialization marker node
                session.run(
                    """
                    MERGE (i:Initialization {id: 'neo4j_init'})
                    SET i.status = 'complete',
                        i.timestamp = $timestamp,
                        i.version = '1.0'
                    """,
                    timestamp=datetime.now().isoformat()
                )
                
                # Create test company node
                session.run(
                    """
                    MERGE (c:Company {id: '0000320193'})
                    SET c.cik = '0000320193', 
                        c.name = 'Apple Inc', 
                        c.ticker = 'AAPL',
                        c.displayLabel = 'Apple Inc (AAPL)'
                    """
                )
                
                # Create single test date node
                session.run(
                    """
                    MERGE (d:Date {id: '2023-01-01'})
                    SET d.year = 2023,
                        d.month = 1,
                        d.day = 1,
                        d.quarter = 'Q1',
                        d.displayLabel = '2023-01-01'
                    """
                )
                
                # Create single admin report node structure
                session.run(
                    """
                    MERGE (k:AdminReport {code: '10-K'})
                    SET k.label = '10-K Reports',
                        k.category = '10-K',
                        k.displayLabel = '10-K Reports'
                    
                    MERGE (q:AdminReport {code: '10-Q'})  
                    SET q.label = '10-Q Reports',
                        q.category = '10-Q',
                        q.displayLabel = '10-Q Reports'
                    """
                )
                
                logger.info("Neo4j database initialized with minimal test data")
                return True
                
        except Exception as e:
            logger.error(f"Error during Neo4j initialization: {e}")
            return False

    def clear_db(self):
        """Development only: Clear database using Neo4jManager"""
        if not self.manager:
            if not self.connect():
                return False
                
        try:
            self.manager.clear_db()
            logger.info("Database cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to clear database: {e}")
            return False

# Simple function to run initialization
def init_neo4j(force=False):
    """Initialize Neo4j with minimal required nodes"""
    processor = Neo4jProcessor()
    try:
        if processor.connect():
            if force:
                # Force reinitialization by clearing the database first
                processor.clear_db()
                
            result = processor.initialize()
            processor.close()
            return result
        return False
    except Exception as e:
        logger.error(f"Neo4j initialization failed: {e}")
        processor.close()
        return False

if __name__ == "__main__":
    # For direct testing from command line
    logging.basicConfig(level=logging.INFO)
    success = init_neo4j()
    print(f"Neo4j initialization {'succeeded' if success else 'failed'}") 