import logging
import os
import sys
import json
import pandas as pd
from datetime import datetime
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
        # Override with environment variables if available - Save it in .env file
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
        """Check if Neo4j database is initialized"""
        if not self.connect():
            return False
            
        try:
            with self.manager.driver.session() as session:
                result = session.run("""
                    MATCH (i:Initialization {id: 'neo4j_init'})
                    RETURN i.status as status
                """)
                
                record = result.single()
                initialized = record and record.get('status') == 'complete'
                
                # Log initialization status
                if initialized:
                    logger.info("Neo4j database is already initialized")
                else:
                    logger.info("Neo4j database needs initialization")
                    
                return initialized
                
        except Exception as e:
            logger.error(f"Error checking Neo4j initialization: {e}")
            return False
    
    def initialize(self):
        """
        Initialize Neo4j database with required structure and company nodes.
        Uses MERGE to ensure idempotent operation.
        """
        # Skip if already initialized
        if self.is_initialized():
            logger.info("Neo4j database already initialized")
            return True
            
        if not self.connect():
            logger.error("Cannot connect to Neo4j")
            return False
        
        try:
            # Verify company data is available
            universe_data = self.get_tradable_universe()
            if not universe_data:
                logger.error("Company data required for initialization unavailable")
                return False
                
            logger.info(f"Initializing Neo4j with {len(universe_data)} available companies")
            
            # Create initialization structure and mark as in_progress
            with self.manager.driver.session() as session:
                session.run("""
                    // Initialization marker (in_progress)
                    MERGE (i:Initialization {id: 'neo4j_init'})
                    ON CREATE SET i.status = 'in_progress',
                                  i.timestamp = $timestamp
                    ON MATCH SET i.status = 'in_progress',
                                i.restart_timestamp = $timestamp
                    
                    // Basic reference data
                    MERGE (k:AdminReport {code: '10-K'})
                    ON CREATE SET k.label = '10-K Reports',
                                  k.displayLabel = '10-K Reports'
                    
                    MERGE (q:AdminReport {code: '10-Q'})  
                    ON CREATE SET q.label = '10-Q Reports',
                                  q.displayLabel = '10-Q Reports'
                """, timestamp=datetime.now().isoformat())
            
            # Populate company nodes (blocking operation)
            logger.info("Creating company nodes (blocking operation)...")
            if not self.populate_company_nodes():
                logger.error("Failed to create company nodes, initialization aborted")
                return False
            
            # Mark initialization as complete only after successful node creation
            with self.manager.driver.session() as session:
                session.run("""
                    MATCH (i:Initialization {id: 'neo4j_init'})
                    SET i.status = 'complete',
                        i.completed_at = $timestamp
                """, timestamp=datetime.now().isoformat())
            
            logger.info("Neo4j database initialization completed successfully")
            return True
                
        except Exception as e:
            # Ensure initialization is properly marked as failed
            try:
                with self.manager.driver.session() as session:
                    session.run("""
                        MATCH (i:Initialization {id: 'neo4j_init'})
                        SET i.status = 'failed',
                            i.error = $error,
                            i.failed_at = $timestamp
                    """, error=str(e), timestamp=datetime.now().isoformat())
            except:
                pass
                
            logger.error(f"Neo4j initialization failed: {e}")
            return False


    def get_tradable_universe(self):
        """
        Load tradable universe directly from CSV file to avoid Redis dependency.
        
        Returns:
            dict: Dictionary where each symbol is a key, with company data as values.
        """
        try:
            # Get the project root directory
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            file_path = os.path.join(project_root, 'StocksUniverse', 'final_symbols.csv')
            
            # Check if file exists
            if not os.path.exists(file_path):
                logger.error(f"Stock universe file not found: {file_path}")
                return {}
            
            logger.info(f"Loading stock universe from: {file_path}")
            
            # Read CSV file with error handling
            try:
                df = pd.read_csv(file_path, on_bad_lines='warn')
            except Exception as e:
                logger.error(f"Error reading CSV file: {e}")
                return {}
            
            # Ensure required columns exist
            if 'symbol' not in df.columns or 'cik' not in df.columns:
                logger.error("Required columns 'symbol' and 'cik' must be in CSV")
                return {}
            
            # Clean up dataframe
            df = df[df['symbol'].astype(str).str.strip().str.len() > 0]
            df = df.drop_duplicates(subset=['symbol'])
            
            logger.info(f"Successfully processed CSV with {len(df)} valid companies")
            
            # Convert DataFrame to dictionary
            universe_data = {}
            for _, row in df.iterrows():
                symbol = str(row['symbol']).strip()
                company_data = {}
                
                # Add all available columns (excluding empty values)
                for col in df.columns:
                    if col != 'symbol' and pd.notnull(row.get(col, '')):
                        if col == 'related':
                            # Special handling for the 'related' field to convert string to list
                            try:
                                related_val = row[col]
                                # If it's a string like "['AAPL', 'MSFT']", parse it
                                if isinstance(related_val, str) and related_val.startswith('[') and related_val.endswith(']'):
                                    # Safer alternative to eval() - extract content and split
                                    content = related_val.strip('[]')
                                    if content:
                                        # Handle quoted values like "'AAPL'" or unquoted like "AAPL"
                                        content = content.replace("'", "").replace('"', "")
                                        related_list = [item.strip() for item in content.split(',') if item.strip()]
                                        company_data[col] = related_list
                                    else:
                                        company_data[col] = []
                                else:
                                    company_data[col] = related_val  # Keep as is if already a list or another format
                            except Exception:
                                # If parsing fails, use empty list as fallback
                                company_data[col] = []
                        else:
                            company_data[col] = str(row[col]).strip()
                
                universe_data[symbol] = company_data
            
            return universe_data
            
        except Exception as e:
            logger.error(f"Error loading tradable universe from CSV: {e}")
            return {}

    def _test_redis_access(self):
        """Diagnostic test to verify Redis access"""
        if not hasattr(self, 'hist_client') or not self.hist_client:
            logger.warning("No Redis client available for testing")
            return False
            
        try:
            from utils.redisClasses import RedisKeys
            
            # Determine sources to test
            sources = []
            if hasattr(self, 'source_type'):
                sources.append(self.source_type)
                
            # Add common sources if available
            try:
                common_sources = ['news', 'reports', 'transcripts']
                for src in common_sources:
                    if src not in sources:
                        sources.append(src)
            except:
                pass
                
            if not sources:
                logger.warning("No sources available for Redis testing")
                return False
                
            logger.info(f"Testing Redis access for sources: {sources}")
            
            # Test each source for keys
            success = False
            for source in sources:
                try:
                    # Test withreturns and withoutreturns patterns
                    for pattern_type in ['withreturns', 'withoutreturns']:
                        pattern = f"{source}:{pattern_type}:*"
                        try:
                            keys = self.hist_client.client.keys(pattern)
                            logger.info(f"Redis test: found {len(keys)} keys matching {pattern}")
                            if keys:
                                success = True
                        except Exception:
                            continue
                except Exception as e:
                    logger.debug(f"Redis test error for {source}: {e}")
            
            return success
                
        except Exception as e:
            logger.warning(f"Redis access test failed: {e}")
            return False

    def populate_company_nodes(self):
        """
        Create Company nodes in Neo4j with all fields from CSV.
        This is a blocking function that ensures nodes are created before returning.
        """
        if not self.connect():
            logger.error("Cannot connect to Neo4j")
            return False
            
        try:
            # Get company data directly from CSV
            universe_data = self.get_tradable_universe()
            if not universe_data:
                logger.warning("No company data found for node creation")
                return False
                
            logger.info(f"Creating Company nodes for {len(universe_data)} companies")
            
            from XBRL.XBRLClasses import CompanyNode, RelationType
            valid_nodes = []
            
            # Build a ticker-to-CIK lookup dictionary
            ticker_to_cik = {}
            for symbol, data in universe_data.items():
                cik = data.get('cik', '').strip()
                if cik and cik.lower() not in ['nan', 'none', '']:
                    formatted_cik = str(cik).zfill(10)
                    ticker_to_cik[symbol] = formatted_cik
            
            # Process and validate company data
            for symbol, data in universe_data.items():
                # Get and validate CIK
                cik = data.get('cik', '').strip()
                if not cik or cik.lower() in ['nan', 'none', '']:
                    continue
                
                # Format CIK properly (10 digits with leading zeros)
                try:
                    cik = str(cik).zfill(10)
                    
                    # Get company name from various possible fields
                    name = data.get('company_name', data.get('name', symbol)).strip()
                    
                    # Convert numeric fields properly
                    mkt_cap = None
                    if 'mkt_cap' in data and data['mkt_cap']:
                        try:
                            mkt_cap = float(data['mkt_cap'])
                        except (ValueError, TypeError):
                            pass
                        
                    employees = None
                    if 'employees' in data and data['employees']:
                        try:
                            employees = int(data['employees'])
                        except (ValueError, TypeError):
                            pass
                        
                    shares_out = None
                    if 'shares_out' in data and data['shares_out']:
                        try:
                            shares_out = float(data['shares_out'])
                        except (ValueError, TypeError):
                            pass
                    
                    # Create CompanyNode with all fields from CSV
                    valid_nodes.append(CompanyNode(
                        cik=cik,
                        name=name,
                        ticker=symbol,
                        cusip=data.get('cusip'),
                        figi=data.get('figi'),
                        class_figi=data.get('class_figi'),
                        exchange=data.get('exchange'),
                        sector=data.get('sector'),
                        industry=data.get('industry'),
                        sic=data.get('sic'),
                        sic_name=data.get('sic_name'),
                        sector_etf=data.get('sector_etf'),
                        industry_etf=data.get('industry_etf'),
                        mkt_cap=mkt_cap,
                        employees=employees,
                        shares_out=shares_out,
                        ipo_date=data.get('ipo_date')
                    ))
                except Exception as e:
                    logger.debug(f"Skipping {symbol}: {e}")
            
            if not valid_nodes:
                logger.warning("No valid company nodes to create")
                return False
            
            # Use Neo4jManager's _export_nodes method to create company nodes
            try:
                self.manager._export_nodes([valid_nodes])
                logger.info(f"Created {len(valid_nodes)} company nodes in Neo4j")
                
                # Now create relationships between companies
                self._create_company_relationships(universe_data, valid_nodes, ticker_to_cik)
                
                return True
            except Exception as e:
                logger.error(f"Error exporting nodes to Neo4j: {e}")
                return False
            
        except Exception as e:
            logger.error(f"Error creating company nodes: {e}")
            return False
            
    def _create_company_relationships(self, universe_data, company_nodes, ticker_to_cik):
        """
        Create relationships between related companies based on the 'related' field.
        Companies that appear together in news according to Polygon methodology.
        
        Args:
            universe_data: Dictionary of company data from CSV
            company_nodes: List of CompanyNode objects
            ticker_to_cik: Dictionary mapping tickers to CIK values
        """
        from XBRL.XBRLClasses import RelationType
        
        # Define custom relationship type for co-mentioned companies
        # Since we can't modify the enum at runtime, we'll create a mock with same interface
        class CustomRelationType:
            def __init__(self, value):
                self.value = value
                
        # Create CO_MENTIONED relation type
        CO_MENTIONED = CustomRelationType("CO_MENTIONED")
        
        # Create a lookup for CompanyNode by CIK
        node_by_cik = {node.cik: node for node in company_nodes}
        relationships = []
        
        # Process each company's related tickers
        for symbol, data in universe_data.items():
            source_cik = ticker_to_cik.get(symbol)
            if not source_cik or source_cik not in node_by_cik:
                continue
                
            source_node = node_by_cik[source_cik]
            
            # Parse the related field (could be string representation of list or actual list)
            related_tickers = data.get('related', [])
            if related_tickers is None:
                related_tickers = []
            elif isinstance(related_tickers, str):
                # Parse string representation of list like "['AAPL', 'MSFT']"
                if related_tickers.startswith('[') and related_tickers.endswith(']'):
                    try:
                        # Handle both quoted and unquoted formats
                        content = related_tickers.strip('[]')
                        if content:
                            # Handle quoted values like "'AAPL'" or unquoted like "AAPL"
                            content = content.replace("'", "").replace('"', "")
                            related_tickers = [item.strip() for item in content.split(',') if item.strip()]
                        else:
                            related_tickers = []
                    except:
                        related_tickers = []
                else:
                    related_tickers = []
            
            # Create relationships for each related ticker
            for related_ticker in related_tickers:
                related_cik = ticker_to_cik.get(related_ticker)
                if not related_cik or related_cik not in node_by_cik:
                    continue
                    
                target_node = node_by_cik[related_cik]
                
                # Add relationship with properties
                relationships.append((
                    source_node,
                    target_node,
                    CO_MENTIONED,
                    {
                        "source_ticker": symbol,
                        "target_ticker": related_ticker,
                        "relationship_type": "news_co_occurrence"
                    }
                ))
        
        # Create relationships in Neo4j if any exist
        if relationships:
            try:
                self.manager.merge_relationships(relationships)
                logger.info(f"Created {len(relationships)} CO_MENTIONED relationships between companies")
            except Exception as e:
                logger.warning(f"Error creating company relationships: {e}")
        else:
            logger.info("No company relationships to create")

    def process_news_to_neo4j(self, batch_size=100, max_items=1000):
        """
        Process news data from Redis withreturns namespace and upload to Neo4j.
        Connect news nodes to company nodes based on symbols.
        
        Args:
            batch_size: Number of news items to process in each batch
            max_items: Maximum number of news items to process in total
            
        Returns:
            bool: Success status
        """
        if not self.connect():
            logger.error("Cannot connect to Neo4j")
            return False
            
        if not hasattr(self, 'hist_client') or not self.hist_client:
            logger.error("No Redis history client available")
            return False
            
        try:
            logger.info("Processing news from Redis to Neo4j...")
            
            # Get ticker-to-CIK mapping
            universe_data = self.get_tradable_universe()
            ticker_to_cik = {}
            for symbol, data in universe_data.items():
                cik = data.get('cik', '').strip()
                if cik and cik.lower() not in ['nan', 'none', '']:
                    ticker_to_cik[symbol.upper()] = str(cik).zfill(10)
            
            # Pattern for news keys in Redis
            pattern = "news:withreturns:*"
            news_keys = self.hist_client.client.keys(pattern)
            logger.info(f"Found {len(news_keys)} news keys in Redis")
            
            # Limit the number of items to process
            if max_items and len(news_keys) > max_items:
                news_keys = news_keys[:max_items]
                
            # Process in batches
            processed_count = 0
            updated_count = 0
            error_count = 0
            
            for i in range(0, len(news_keys), batch_size):
                batch_keys = news_keys[i:i+batch_size]
                
                # Process each news item in the batch
                for key in batch_keys:
                    try:
                        # Get news data from Redis
                        news_data = self.hist_client.client.get(key)
                        if not news_data:
                            continue
                            
                        # Parse JSON data
                        news_item = json.loads(news_data)
                        
                        # Extract news ID and create hash
                        news_id = news_item.get('id')
                        if not news_id:
                            continue
                            
                        # Extract relevant properties
                        news_hash = f"news-{news_id}"
                        created_time = news_item.get('created_at', '')
                        updated_time = news_item.get('updated_at', created_time)
                        
                        # Extract content fields
                        title = news_item.get('title', '')
                        body = news_item.get('body', '')
                        teaser = news_item.get('teaser', '')
                        content = f"{title}\n\n{teaser}\n\n{body}"
                        
                        # Get symbols mentioned in news
                        symbols = []
                        if 'symbols' in news_item and news_item['symbols']:
                            symbols = [s.upper() for s in news_item['symbols'] if s]
                        
                        # Prepare properties
                        news_props = {
                            'id': news_id,
                            'hash': news_hash,
                            'title': title,
                            'body': body,
                            'teaser': teaser,
                            'content': content,
                            'created': created_time,
                            'updated': updated_time,
                            'source': news_item.get('source', ''),
                            'author': news_item.get('author', ''),
                            'url': news_item.get('url', '')
                        }
                        
                        # Upload to Neo4j using the pattern from bz_notes.md
                        with self.manager.driver.session() as session:
                            result = session.run("""
                            MERGE (n:News {hash: $hash})
                            ON CREATE SET 
                                n = $props,
                                n.created_at = datetime($created),
                                n.updated_at = datetime($updated)
                            ON MATCH SET 
                                n.updated_at = CASE 
                                    WHEN datetime($updated) > n.updated_at 
                                    THEN datetime($updated) 
                                    ELSE n.updated_at END,
                                n.title = CASE 
                                    WHEN datetime($updated) > n.updated_at 
                                    THEN $title 
                                    ELSE n.title END,
                                n.body = CASE 
                                    WHEN datetime($updated) > n.updated_at 
                                    THEN $body 
                                    ELSE n.body END,
                                n.teaser = CASE 
                                    WHEN datetime($updated) > n.updated_at 
                                    THEN $teaser 
                                    ELSE n.teaser END,
                                n.content = CASE 
                                    WHEN datetime($updated) > n.updated_at 
                                    THEN $content 
                                    ELSE n.content END
                            WITH n
                            RETURN n.hash as hash, 
                                   CASE WHEN n.updated_at = datetime($updated) THEN true ELSE false END as was_updated
                            """, {
                                'hash': news_hash,
                                'props': news_props,
                                'created': created_time,
                                'updated': updated_time,
                                'title': title,
                                'body': body,
                                'teaser': teaser,
                                'content': content
                            })
                            
                            result_record = result.single()
                            was_updated = result_record and result_record.get('was_updated', False)
                            
                            # Create relationships to company nodes for each symbol
                            if symbols:
                                # Create relationships for each symbol
                                for symbol in symbols:
                                    cik = ticker_to_cik.get(symbol)
                                    if not cik:
                                        continue
                                        
                                    # Connect news to company
                                    session.run("""
                                    MATCH (n:News {hash: $hash})
                                    MATCH (c:Company {cik: $cik})
                                    MERGE (n)-[r:MENTIONS]->(c)
                                    ON CREATE SET r.created_at = datetime()
                                    RETURN n, c
                                    """, {
                                        'hash': news_hash,
                                        'cik': cik
                                    })
                            
                            if was_updated:
                                updated_count += 1
                            else:
                                processed_count += 1
                                
                    except Exception as e:
                        logger.error(f"Error processing news item {key}: {e}")
                        error_count += 1
                        
                # Log progress
                logger.info(f"Processed {i+len(batch_keys)} of {len(news_keys)} news items")
                
            logger.info(f"News processing complete. Created: {processed_count}, Updated: {updated_count}, Errors: {error_count}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing news data: {e}")
            return False


# Function to initialize Neo4j database
def init_neo4j():
    """Initialize Neo4j database with required structure and company data"""
    processor = None
    try:
        processor = Neo4jProcessor()
        
        # Attempt initialization
        logger.info("Starting Neo4j database initialization...")
        success = processor.connect() and processor.initialize()
        
        if success:
            logger.info("Neo4j database initialization completed successfully")
        else:
            logger.error("Neo4j database initialization failed")
            
        return success
    except Exception as e:
        logger.error(f"Neo4j initialization error: {str(e)}")
        return False
    finally:
        # Always ensure proper cleanup
        if processor:
            try:
                processor.close()
            except Exception as cleanup_error:
                logger.warning(f"Error during Neo4j connection cleanup: {cleanup_error}")
                
        logger.info("Neo4j initialization process completed")
        
# Function to process news data into Neo4j
def process_news_data(batch_size=100, max_items=1000):
    """Process news data from Redis into Neo4j"""
    processor = None
    try:
        processor = Neo4jProcessor()
        if not processor.connect():
            logger.error("Cannot connect to Neo4j")
            return False
            
        # Process news data
        logger.info("Processing news data to Neo4j...")
        success = processor.process_news_to_neo4j(batch_size, max_items)
        
        if success:
            logger.info("News data processing completed successfully")
        else:
            logger.error("News data processing failed")
            
        return success
    except Exception as e:
        logger.error(f"News data processing error: {str(e)}")
        return False
    finally:
        # Always ensure proper cleanup
        if processor:
            try:
                processor.close()
            except Exception as cleanup_error:
                logger.warning(f"Error during Neo4j connection cleanup: {cleanup_error}")
                
        logger.info("News processing completed")

if __name__ == "__main__":
    # Run initialization directly if this script is executed
    init_neo4j() 