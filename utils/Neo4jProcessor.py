import logging
import os
import sys
import json
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
import argparse
from eventtrader.keys import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
import time
from typing import Dict, List, Optional, Any, Set, Tuple
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, DatabaseUnavailable
from utils.redisClasses import EventTraderRedis
from utils.EventTraderNodes import NewsNode, CompanyNode, SectorNode, IndustryNode, MarketIndexNode
from utils.date_utils import parse_news_dates, parse_date  # Import our new date parsing utility


from XBRL.Neo4jManager import Neo4jManager
from XBRL.XBRLClasses import NodeType, RelationType

# Set up logger
logger = logging.getLogger(__name__)

class Neo4jProcessor:
    """
    A wrapper around Neo4jManager that provides integration with EventTrader workflow.
    This class delegates Neo4j operations to Neo4jManager while adding workflow-specific
    initialization and functionality.
    """
    
    def __init__(self, event_trader_redis=None, uri=NEO4J_URI, username=NEO4J_USERNAME, password=NEO4J_PASSWORD):
        """
        Initialize with Neo4j connection parameters and optional EventTrader Redis client
        
        Args:
            event_trader_redis: EventTraderRedis instance (optional)
            uri: Neo4j database URI
            username: Neo4j username
            password: Neo4j password
        """
        # Override with environment variables if available - Save it in .env file
        self.uri = uri
        self.username = username
        self.password = password
        self.manager = None  # Will be initialized when needed
        self.universe_data = None
        
        # Initialize ETF to name ID mappings
        self.etf_to_sector_id = {}
        self.etf_to_industry_id = {}
        
        # These will be populated from database when needed
        self._load_etf_mappings = False
        
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
        """
        Check if Neo4j database is initialized by verifying Company nodes exist.
        """
        if not self.connect():
            return False
            
        try:
            with self.manager.driver.session() as session:
                # Check for Company nodes - minimalistic approach
                result = session.run("MATCH (c:Company) RETURN count(c) as count")
                company_count = result.single()["count"]
                
                # Database is initialized if it has company nodes
                initialized = company_count > 0
                
                if initialized:
                    logger.info(f"Neo4j database already initialized with {company_count} companies")
                else:
                    logger.info("Neo4j database needs initialization (no companies found)")
                    
                return initialized
                
        except Exception as e:
            logger.error(f"Error checking Neo4j initialization: {e}")
            return False
    
    def initialize(self):
        """Initialize Neo4j with market hierarchy using the dedicated initializer."""
        # Skip if already initialized
        if self.is_initialized():
            logger.info("Neo4j database already initialized")
            return True
        
        # Load universe data if needed
        universe_data = self.get_tradable_universe()
        if not universe_data:
            logger.warning("No company data found")
            return False
        
        # Use the dedicated initializer class
        from utils.Neo4jInitializer import Neo4jInitializer
        initializer = Neo4jInitializer(
            uri=self.uri,
            username=self.username,
            password=self.password,
            universe_data=universe_data
        )
        
        # Run the initialization process
        success = initializer.initialize_all()
        if success:
            logger.info("Neo4j initialization complete")
        else:
            logger.error("Neo4j initialization failed")
        
        return success

    def get_tradable_universe(self):
        """
        Load tradable universe directly from CSV file to avoid Redis dependency.
        If data has already been loaded, returns the cached data instead of reloading.
        
        Returns:
            dict: Dictionary where each symbol is a key, with company data as values.
        """
        # Return cached data if available
        if self.universe_data is not None:
            return self.universe_data
            
        try:
            # Get the project root directory and file path
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            file_path = os.path.join(project_root, 'StocksUniverse', 'final_symbols.csv')
            
            if not os.path.exists(file_path):
                logger.error(f"Stock universe file not found: {file_path}")
                return {}
            
            # Read CSV file and perform basic validation
            try:
                df = pd.read_csv(file_path, on_bad_lines='warn')
                if 'symbol' not in df.columns or 'cik' not in df.columns:
                    logger.error("Required columns 'symbol' and 'cik' must be in CSV")
                    return {}
            except Exception as e:
                logger.error(f"Error reading CSV file: {e}")
                return {}
            
            # Clean up dataframe - remove empty symbols and duplicates
            df = df[df['symbol'].astype(str).str.strip().str.len() > 0]
            df = df.drop_duplicates(subset=['symbol'])
            
            logger.info(f"Loaded stock universe with {len(df)} companies")
            
            # Convert DataFrame to dictionary
            universe_data = {}
            for _, row in df.iterrows():
                symbol = str(row['symbol']).strip()
                company_data = {}
                
                # Process each column
                for col in df.columns:
                    if col != 'symbol' and pd.notnull(row.get(col, '')):
                        # Special handling for related field (string list conversion)
                        if col == 'related' and isinstance(row[col], str):
                            try:
                                if row[col].startswith('[') and row[col].endswith(']'):
                                    content = row[col].strip('[]').replace("'", "").replace('"', "")
                                    related_list = [item.strip() for item in content.split(',') if item.strip()]
                                    company_data[col] = related_list
                                else:
                                    company_data[col] = []
                            except Exception:
                                company_data[col] = []
                        else:
                            company_data[col] = str(row[col]).strip()
                
                universe_data[symbol] = company_data
            
            # Cache the data before returning
            self.universe_data = universe_data
            return universe_data
            
        except Exception as e:
            logger.error(f"Error loading tradable universe: {e}")
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
        Create Company nodes in Neo4j with all required fields and relationships.
        Returns True if successful, False otherwise.
        """
        if not self.connect():
            logger.error("Cannot connect to Neo4j")
            return False
            
        try:
            # Ensure we have universe data
            if self.universe_data is None:
                self.universe_data = self.get_tradable_universe()
                if not self.universe_data:
                    logger.warning("No company data found")
                    return False
                    
            logger.info(f"Creating Company nodes for {len(self.universe_data)} companies")
            
            # Check if critical fields exist in the data
            first_company = next(iter(self.universe_data.values()))
            # Update the critical field names to match what's in the CSV
            critical_fields = ['mkt_cap', 'employees', 'shares_out']
            missing_fields = [field for field in critical_fields if field not in first_company]
            if missing_fields:
                logger.warning(f"Warning: The following critical fields are missing in the company data: {missing_fields}")
                logger.info(f"Available fields: {list(first_company.keys())}")
            
            # Prepare company nodes with all fields
            valid_nodes = []
            
            # Build a ticker-to-CIK lookup dictionary for relationships
            ticker_to_cik = {}
            for symbol, data in self.universe_data.items():
                cik = data.get('cik', '').strip()
                if cik and cik.lower() not in ['nan', 'none', '']:
                    formatted_cik = str(cik).zfill(10)
                    ticker_to_cik[symbol.upper()] = formatted_cik
            
            # Statistics for reporting
            processed_count = 0
            had_mkt_cap = 0
            had_employees = 0
            had_shares_out = 0
            
            # Process and create company nodes with all fields
            for symbol, data in self.universe_data.items():
                cik = data.get('cik', '').strip()
                if not cik or cik.lower() in ['nan', 'none', '']:
                    continue
                    
                try:
                    cik = str(cik).zfill(10)
                    name = data.get('company_name', data.get('name', symbol)).strip()
                    
                    # Create CompanyNode with required fields
                    company_node = CompanyNode(
                        cik=cik,
                        name=name,
                        ticker=symbol
                    )
                    
                    # Specifically handle the three critical financial fields we need
                    # Process market_cap - CORRECTED field name to match CSV 
                    try:
                        if 'mkt_cap' in data and data['mkt_cap'] and str(data['mkt_cap']).lower() not in ['nan', 'none', '']:
                            mkt_cap_value = data['mkt_cap']
                            try:
                                # First try direct float conversion
                                mkt_cap_float = float(mkt_cap_value)
                                company_node.mkt_cap = mkt_cap_float
                                had_mkt_cap += 1
                            except (ValueError, TypeError) as e:
                                # Try to clean the string if it contains commas, etc.
                                try:
                                    clean_val = str(mkt_cap_value).replace(',', '').replace('$', '').strip()
                                    mkt_cap_float = float(clean_val)
                                    company_node.mkt_cap = mkt_cap_float
                                    had_mkt_cap += 1
                                except Exception as e2:
                                    logger.warning(f"Could not convert mkt_cap value '{mkt_cap_value}' to float for {symbol}: {e2}")
                    except Exception as e:
                        logger.error(f"Error processing mkt_cap for {symbol}: {e}")
                    
                    # Process employees
                    try:
                        if 'employees' in data and data['employees'] and str(data['employees']).lower() not in ['nan', 'none', '']:
                            employees_value = data['employees']
                            try:
                                # First try direct int conversion
                                # Convert through float first to handle decimal representations
                                employees_int = int(float(employees_value))
                                company_node.employees = employees_int
                                had_employees += 1
                            except (ValueError, TypeError) as e:
                                # Try to clean the string if it contains commas, etc.
                                try:
                                    clean_val = str(employees_value).replace(',', '').strip()
                                    employees_int = int(float(clean_val))
                                    company_node.employees = employees_int
                                    had_employees += 1
                                except Exception as e2:
                                    logger.warning(f"Could not convert employees value '{employees_value}' to int for {symbol}: {e2}")
                    except Exception as e:
                        logger.error(f"Error processing employees for {symbol}: {e}")
                    
                    # Process shares_outstanding - CORRECTED field name to match CSV
                    try:
                        if 'shares_out' in data and data['shares_out'] and str(data['shares_out']).lower() not in ['nan', 'none', '']:
                            shares_value = data['shares_out']
                            try:
                                # First try direct float conversion
                                shares_float = float(shares_value)
                                company_node.shares_out = shares_float
                                had_shares_out += 1
                            except (ValueError, TypeError) as e:
                                # Try to clean the string if it contains commas, etc.
                                try:
                                    clean_val = str(shares_value).replace(',', '').strip()
                                    shares_float = float(clean_val)
                                    company_node.shares_out = shares_float
                                    had_shares_out += 1
                                except Exception as e2:
                                    logger.warning(f"Could not convert shares_out value '{shares_value}' to float for {symbol}: {e2}")
                    except Exception as e:
                        logger.error(f"Error processing shares_out for {symbol}: {e}")
                    
                    # Process other fields using the normal flow
                    field_mappings = {
                        'exchange': 'exchange',
                        'sector': 'sector',
                        'industry': 'industry',
                        'fiscal_year_end': 'fiscal_year_end',
                        'cusip': 'cusip',
                        'figi': 'figi',
                        'class_figi': 'class_figi',
                        'sic': 'sic',
                        'sic_name': 'sic_name',
                        'sector_etf': 'sector_etf',
                        'industry_etf': 'industry_etf',
                        'ipo_date': 'ipo_date'
                    }
                    
                    # Set attributes if they exist in data
                    for source_field, target_field in field_mappings.items():
                        if source_field in data and data[source_field] and str(data[source_field]).lower() not in ['nan', 'none', '']:
                            setattr(company_node, target_field, data[source_field])
                    
                    valid_nodes.append(company_node)
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error creating CompanyNode for {symbol}: {e}")
            
            # Create all nodes in Neo4j
            if valid_nodes:
                self.manager.merge_nodes(valid_nodes)
                
                # Report statistics
                logger.info(f"Company node statistics:")
                logger.info(f"  - Processed: {processed_count} companies")
                logger.info(f"  - With market cap: {had_mkt_cap} ({had_mkt_cap/processed_count*100:.1f}%)")
                logger.info(f"  - With employees: {had_employees} ({had_employees/processed_count*100:.1f}%)")
                logger.info(f"  - With shares outstanding: {had_shares_out} ({had_shares_out/processed_count*100:.1f}%)")
                
                # Report on CIK coverage
                logger.info(f"  - CIK coverage: {len(ticker_to_cik)} companies")
                
                # Create relationships between companies
                if self._create_company_relationships(self.universe_data, valid_nodes, ticker_to_cik):
                    logger.info("Successfully created company relationships")
                    
                return True
            else:
                logger.warning("No valid company nodes were created")
                return False
                
        except Exception as e:
            logger.error(f"Error populating company nodes: {e}")
            return False

    def _create_company_relationships(self, universe_data, company_nodes, ticker_to_cik):
        """
        Create bidirectional RELATED_TO relationships between related companies.
        This creates a single relationship between each pair of companies.
        """
        try:
            from XBRL.XBRLClasses import RelationType
            
            # Define RELATED_TO relationship using the proper enum
            try:
                # Try using the actual enum if available
                RELATED_TO = RelationType.RELATED_TO
            except AttributeError:
                # Fallback to a mock with same interface if needed
                class CustomRelationType:
                    def __init__(self, value):
                        self.value = value
                
                RELATED_TO = CustomRelationType("RELATED_TO")
            
            # Create a lookup for CompanyNode by CIK
            node_by_cik = {node.cik: node for node in company_nodes}
            
            # Use a set to track unique company pairs (regardless of direction)
            relationship_pairs = set()
            relationships = []
            
            # Process each company's related tickers
            for symbol, data in universe_data.items():
                source_cik = ticker_to_cik.get(symbol.upper())
                if not source_cik or source_cik not in node_by_cik:
                    continue
                    
                source_node = node_by_cik[source_cik]
                
                # Parse the related field
                related_tickers = data.get('related', [])
                if related_tickers is None:
                    continue
                    
                if isinstance(related_tickers, str):
                    if related_tickers.startswith('[') and related_tickers.endswith(']'):
                        try:
                            content = related_tickers.strip('[]')
                            if content:
                                content = content.replace("'", "").replace('"', "")
                                related_tickers = [item.strip() for item in content.split(',') if item.strip()]
                            else:
                                related_tickers = []
                        except:
                            related_tickers = []
                    else:
                        related_tickers = []
                
                # Create relationships
                for related_ticker in related_tickers:
                    related_cik = ticker_to_cik.get(related_ticker.upper())
                    if not related_cik or related_cik not in node_by_cik:
                        continue
                    
                    # Only process each company pair once (regardless of direction)
                    # Sort CIKs to ensure same pair is recognized regardless of order
                    company_pair = tuple(sorted([source_cik, related_cik]))
                    if company_pair in relationship_pairs:
                        continue
                    
                    relationship_pairs.add(company_pair)
                    target_node = node_by_cik[related_cik]
                    
                    relationships.append((
                        source_node,
                        target_node,
                        RELATED_TO,
                        {
                            "source_ticker": symbol,
                            "target_ticker": related_ticker,
                            "relationship_type": "news_co_occurrence",
                            "bidirectional": True  # Flag to indicate bidirectional relationship
                        }
                    ))
            
            if relationships:
                # Use a Cypher query directly to create undirected relationships
                with self.manager.driver.session() as session:
                    batch_size = 100  # Process in batches for better performance
                    for i in range(0, len(relationships), batch_size):
                        batch = relationships[i:i+batch_size]
                        for source, target, rel_type, props in batch:
                            # Use undirected relationship syntax (no directional arrow)
                            session.run("""
                            MATCH (a:Company {id: $source_id})
                            MATCH (b:Company {id: $target_id})
                            MERGE (a)-[r:RELATED_TO]-(b)
                            SET r += $properties
                            """, {
                                "source_id": source.cik,
                                "target_id": target.cik,
                                "properties": props
                            })
                
                logger.info(f"Created {len(relationships)} bidirectional RELATED_TO relationships between companies")
            else:
                logger.info("No company relationships to create")
                
            return True
                
        except Exception as e:
            logger.warning(f"Error creating company relationships: {e}")
            # Continue anyway - relationships aren't critical
            return False

    def process_news_to_neo4j(self, batch_size=100, max_items=1000) -> bool:
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
            logger.warning("No Redis history client available for news processing")
            logger.info("Skipping news processing - Redis client required")
            return True  # Return success as this is not a fatal error
        
        # Load ETF to name mappings
        self._load_etf_to_name_mappings()
        
        try:
            logger.info("Processing news from Redis to Neo4j...")
            
            # Get ticker-to-CIK mapping
            universe_data = self.get_tradable_universe()
            ticker_to_cik = {}
            for symbol, data in universe_data.items():
                cik = data.get('cik', '').strip()
                if cik and cik.lower() not in ['nan', 'none', '']:
                    ticker_to_cik[symbol.upper()] = str(cik).zfill(10)
            
            logger.info(f"Created ticker-to-CIK mapping for {len(ticker_to_cik)} symbols")
            
            # Pattern for news keys in Redis
            pattern = "news:withreturns:*"
            news_keys = self.hist_client.client.keys(pattern)
            logger.info(f"Found {len(news_keys)} news keys in Redis")
            
            # Limit the number of items to process
            if max_items and len(news_keys) > max_items:
                news_keys = news_keys[:max_items]
            
            # Process in batches
            processed_count = 0
            error_count = 0
            symbol_missing_count = 0
            cik_missing_count = 0
            sector_ref_count = 0
            industry_ref_count = 0
            market_index_ref_count = 0
            
            # Main processing loop
            for i in range(0, len(news_keys), batch_size):
                batch_keys = news_keys[i:i+batch_size]
                batch_nodes = []
                batch_relationships = []
                
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(news_keys) + batch_size - 1)//batch_size}")
                
                # Process each news item in the batch
                for key in batch_keys:
                    try:
                        # Extract ID from Redis key
                        news_id = key.replace("news:withreturns:", "")
                        
                        # Get news data from Redis
                        news_data = self.hist_client.client.get(key)
                        if not news_data:
                            logger.warning(f"No data found for key {key}")
                            continue
                            
                        # Parse JSON data
                        news_item = json.loads(news_data)
                        
                        # Extract basic properties
                        title = news_item.get('title', '')
                        body = news_item.get('body', '')
                        teaser = news_item.get('teaser', '')
                        
                        # Get timestamps and clean them
                        created_at, updated_at = parse_news_dates(news_item)
                        
                        # Get market session
                        market_session = ""
                        if 'metadata' in news_item and 'event' in news_item['metadata']:
                            market_session = news_item['metadata']['event'].get('market_session', '')
                        
                        # Extract list fields
                        authors = self._parse_list_field(news_item.get('authors', []))
                        channels = self._parse_list_field(news_item.get('channels', []))
                        tags = self._parse_list_field(news_item.get('tags', []))
                        
                        # Extract returns_schedule
                        returns_schedule = {}
                        if 'metadata' in news_item and 'returns_schedule' in news_item['metadata']:
                            raw_schedule = news_item['metadata']['returns_schedule']
                            # Parse each date in the schedule
                            for key in ['hourly', 'session', 'daily']:
                                if key in raw_schedule and raw_schedule[key]:
                                    # Parse the date string to ensure it's valid, then convert back to string
                                    date_obj = parse_date(raw_schedule[key])
                                    if date_obj:
                                        returns_schedule[key] = date_obj.isoformat()
                        
                        # Create NewsNode
                        news_node = NewsNode(
                            news_id=news_id,
                            title=title,
                            body=body,
                            teaser=teaser,
                            created_at=created_at,
                            updated_at=updated_at,
                            url=news_item.get('url', ''),
                            authors=authors,
                            channels=channels,
                            tags=tags,
                            market_session=market_session,
                            returns_schedule=returns_schedule
                        )
                        
                        batch_nodes.append(news_node)
                        
                        # Get symbols mentioned in news
                        symbols = self._extract_symbols(news_item.get('symbols', []))
                        
                        if not symbols:
                            symbol_missing_count += 1
                            continue
                        
                        # Process each symbol for relationships
                        for symbol in symbols:
                            symbol_upper = symbol.upper()
                            cik = ticker_to_cik.get(symbol_upper)
                            if not cik:
                                cik_missing_count += 1
                                continue
                            
                            # Get return metrics for this symbol
                            return_metrics = self._extract_return_metrics(news_item, symbol_upper)
                            
                            # Create company node reference and relationship with ONLY stock metrics
                            company_rel_props = {
                                'symbol': symbol_upper,
                                'created_at': datetime.now().isoformat()
                            }
                            
                            # Add only stock-specific metrics
                            for timeframe in ['hourly', 'session', 'daily']:
                                metric_key = f"{timeframe}_stock"
                                if metric_key in return_metrics:
                                    company_rel_props[metric_key] = return_metrics[metric_key]
                            
                            company_node = CompanyNode(cik=cik)
                            batch_relationships.append((news_node, company_node, RelationType.INFLUENCES, company_rel_props))
                            
                            try:
                                # Look for benchmarks in the instruments array
                                sector_id = None
                                industry_id = None
                                has_macro_metrics = False
                                
                                if 'metadata' in news_item and 'instruments' in news_item['metadata']:
                                    for instrument in news_item['metadata']['instruments']:
                                        if instrument.get('symbol') == symbol_upper and 'benchmarks' in instrument:
                                            benchmarks = instrument['benchmarks']
                                            sector_etf = benchmarks.get('sector')
                                            industry_etf = benchmarks.get('industry')
                                            
                                            # Map ETFs to normalized name IDs
                                            # Try to get from our mappings first
                                            if sector_etf in self.etf_to_sector_id:
                                                sector_id = self.etf_to_sector_id.get(sector_etf)
                                            else:
                                                # Fallback: directly use the ETF as ID
                                                sector_id = sector_etf
                                                
                                            if industry_etf in self.etf_to_industry_id:
                                                industry_id = self.etf_to_industry_id.get(industry_etf)
                                            else:
                                                # Fallback: directly use the ETF as ID
                                                industry_id = industry_etf
                                                
                                            break
                                
                                # Create sector relationship if sector_id exists - with ONLY sector metrics
                                if sector_id:
                                    sector_rel_props = {
                                        'symbol': symbol_upper,
                                        'created_at': datetime.now().isoformat()
                                    }
                                    
                                    # Add only sector-specific metrics
                                    for timeframe in ['hourly', 'session', 'daily']:
                                        metric_key = f"{timeframe}_sector"
                                        if metric_key in return_metrics:
                                            sector_rel_props[metric_key] = return_metrics[metric_key]
                                    
                                    sector_node = SectorNode(node_id=sector_id)
                                    batch_relationships.append((news_node, sector_node, RelationType.INFLUENCES, sector_rel_props))
                                    sector_ref_count += 1
                                
                                # Create industry relationship if industry_id exists - with ONLY industry metrics
                                if industry_id:
                                    industry_rel_props = {
                                        'symbol': symbol_upper,
                                        'created_at': datetime.now().isoformat()
                                    }
                                    
                                    # Add only industry-specific metrics
                                    for timeframe in ['hourly', 'session', 'daily']:
                                        metric_key = f"{timeframe}_industry"
                                        if metric_key in return_metrics:
                                            industry_rel_props[metric_key] = return_metrics[metric_key]
                                    
                                    industry_node = IndustryNode(node_id=industry_id)
                                    batch_relationships.append((news_node, industry_node, RelationType.INFLUENCES, industry_rel_props))
                                    industry_ref_count += 1
                                
                                # Check if there are any macro metrics
                                has_macro_metrics = any(f"{timeframe}_macro" in return_metrics for timeframe in ['hourly', 'session', 'daily'])
                                
                                # Create relationship to SPY (macro index) if macro metrics exist - with ONLY macro metrics
                                if has_macro_metrics:
                                    macro_rel_props = {
                                        'symbol': symbol_upper,
                                        'created_at': datetime.now().isoformat()
                                    }
                                    
                                    # Add only macro-specific metrics
                                    for timeframe in ['hourly', 'session', 'daily']:
                                        metric_key = f"{timeframe}_macro"
                                        if metric_key in return_metrics:
                                            macro_rel_props[metric_key] = return_metrics[metric_key]
                                    
                                    market_index_node = MarketIndexNode(ticker="SPY")
                                    batch_relationships.append((news_node, market_index_node, RelationType.INFLUENCES, macro_rel_props))
                                    market_index_ref_count += 1
                            except Exception as e:
                                logger.warning(f"Error creating sector/industry relationships for {symbol_upper}: {e}")
                                # Continue processing - we at least created the company relationship
                        
                        processed_count += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing news item {key}: {e}")
                        error_count += 1
                
                # Create all news nodes in this batch using Neo4jManager
                if batch_nodes:
                    try:
                        self.manager.merge_nodes(batch_nodes)
                        logger.info(f"Created {len(batch_nodes)} news nodes")
                    except Exception as e:
                        logger.error(f"Error creating news nodes: {e}")
                
                # Create all relationships in this batch
                if batch_relationships:
                    try:
                        self.manager.merge_relationships(batch_relationships)
                        # Count relationship types
                        company_rels = sum(1 for r in batch_relationships if isinstance(r[1], CompanyNode))
                        sector_rels = sum(1 for r in batch_relationships if isinstance(r[1], SectorNode))
                        industry_rels = sum(1 for r in batch_relationships if isinstance(r[1], IndustryNode))
                        
                        logger.info(f"Created {len(batch_relationships)} total relationships:")
                        logger.info(f"  - News→Company: {company_rels}")
                        logger.info(f"  - News→Sector: {sector_rels}")
                        logger.info(f"  - News→Industry: {industry_rels}")
                    except Exception as e:
                        logger.error(f"Error creating relationships: {e}")
            
            # Get database stats to verify results
            try:
                self.manager.get_neo4j_db_counts()
            except:
                pass
            
            # Detailed summary
            logger.info(f"News processing complete:")
            logger.info(f"  - Processed: {processed_count} news items")
            logger.info(f"  - Errors: {error_count}")
            logger.info(f"  - Without symbols: {symbol_missing_count}")
            logger.info(f"  - Symbol-CIK mapping failures: {cik_missing_count}")
            logger.info(f"  - Sector references: {sector_ref_count}")
            logger.info(f"  - Industry references: {industry_ref_count}")
            logger.info(f"  - Market index references: {market_index_ref_count}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing news data: {e}")
            return False

    def get_node_by_id(self, node_id, node_type):
        """
        Get a node by its ID and type from Neo4j
        
        Args:
            node_id: The ID of the node
            node_type: The type of the node (NodeType enum)
            
        Returns:
            Node object if found, None otherwise
        """
        try:
            neo4j_manager = self._get_neo4j_manager()
            query = f"""
            MATCH (n:{node_type.value} {{id: $id}})
            RETURN n
            """
            params = {"id": node_id}
            
            # Use driver's session to execute query instead of run_query
            with neo4j_manager.driver.session() as session:
                result = session.run(query, params)
                record = result.single()
                
                if record:
                    # Get node properties
                    node_props = dict(record['n'])
                    
                    # Handle different node types
                    if node_type == NodeType.COMPANY:
                        # Use EventTraderNodes.CompanyNode instead of XBRLClasses.CompanyNode
                        return CompanyNode.from_neo4j(node_props)
                    elif node_type == NodeType.NEWS:
                        return NewsNode.from_neo4j(node_props)
                    
            return None
        except Exception as e:
            logger.error(f"Error getting node by ID: {e}")
            return None

    def _get_neo4j_manager(self):
        """Get or create a Neo4jManager instance"""
        if not hasattr(self, 'neo4j_manager'):
            self.neo4j_manager = Neo4jManager(uri=self.uri, username=self.username, password=self.password)
        return self.neo4j_manager

    def _parse_list_field(self, field_value) -> List:
        """Parse a field that could be a list or string representation of a list"""
        if isinstance(field_value, list):
            return field_value
        
        if isinstance(field_value, str):
            try:
                if field_value.startswith('[') and field_value.endswith(']'):
                    content = field_value.replace("'", '"')  # Make JSON-compatible
                    return json.loads(content)
                return [field_value]  # Single item
            except:
                pass
            
        return []

    def _extract_symbols(self, symbols_field) -> List[str]:
        """Extract symbol list from news data"""
        if isinstance(symbols_field, list):
            return [s.upper() for s in symbols_field if s]
        
        if isinstance(symbols_field, str):
            try:
                # Try JSON parsing
                if symbols_field.startswith('[') and symbols_field.endswith(']'):
                    content = symbols_field.replace("'", '"')
                    return [s.upper() for s in json.loads(content) if s]
                
                # Try comma-separated string
                if ',' in symbols_field:
                    return [s.strip().upper() for s in symbols_field.split(',') if s.strip()]
                
                # Single symbol
                return [symbols_field.upper()]
            except:
                # Last resort parsing
                clean = symbols_field.strip('[]').replace("'", "").replace('"', "")
                return [s.strip().upper() for s in clean.split(',') if s.strip()]
            
        return []

    def _extract_return_metrics(self, news_item, symbol) -> Dict:
        """Extract return metrics for a symbol from news data"""
        metrics = {}
        symbol_upper = symbol.upper()
        
        if 'returns' not in news_item:
            return metrics
        
        # Find symbol returns data
        symbol_returns = None
        
        # Structure 1: {'returns': {'AAPL': {...}}}
        if symbol_upper in news_item['returns']:
            symbol_returns = news_item['returns'][symbol_upper]
        
        # Structure 2: {'returns': {'symbols': {'AAPL': {...}}}}
        elif 'symbols' in news_item['returns'] and symbol_upper in news_item['returns']['symbols']:
            symbol_returns = news_item['returns']['symbols'][symbol_upper]
        
        if not symbol_returns:
            return metrics
        
        # Process different return timeframes
        for timeframe in ['hourly_return', 'session_return', 'daily_return']:
            if timeframe in symbol_returns:
                for metric, value in symbol_returns[timeframe].items():
                    if value is not None and not (isinstance(value, str) and value.lower() == 'nan'):
                        metrics[f"{timeframe.split('_')[0]}_{metric}"] = value
        
        return metrics

    def _load_etf_to_name_mappings(self):
        """Load ETF to normalized name mappings from the database"""
        if self._load_etf_mappings:
            return  # Already loaded
            
        try:
            if not self.connect():
                logger.error("Cannot connect to Neo4j")
                return
                
            with self.manager.driver.session() as session:
                # Get mappings from company nodes with ETF fields
                result = session.run("""
                MATCH (c:Company)
                WHERE c.sector_etf IS NOT NULL AND c.sector_etf <> ''
                AND c.sector IS NOT NULL AND c.sector <> ''
                RETURN DISTINCT c.sector_etf as etf, replace(c.sector, " ", "") as normalized_name
                """)
                
                for record in result:
                    etf = record["etf"]
                    normalized_name = record["normalized_name"]
                    self.etf_to_sector_id[etf] = normalized_name
                
                # Get industry mappings
                result = session.run("""
                MATCH (c:Company)
                WHERE c.industry_etf IS NOT NULL AND c.industry_etf <> ''
                AND c.industry IS NOT NULL AND c.industry <> ''
                RETURN DISTINCT c.industry_etf as etf, replace(c.industry, " ", "") as normalized_name
                """)
                
                for record in result:
                    etf = record["etf"]
                    normalized_name = record["normalized_name"]
                    self.etf_to_industry_id[etf] = normalized_name
                    
            self._load_etf_mappings = True
            logger.info(f"Loaded ETF to name mappings: {len(self.etf_to_sector_id)} sectors, {len(self.etf_to_industry_id)} industries")
            
        except Exception as e:
            logger.error(f"Error loading ETF to name mappings: {e}")
            return False

# Function to initialize Neo4j database
def init_neo4j():
    """Initialize Neo4j database with required structure and company data"""
    try:
        # Use the dedicated initializer class
        from utils.Neo4jInitializer import Neo4jInitializer
        from eventtrader.keys import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
        
        logger.info("Starting Neo4j database initialization...")
        
        initializer = Neo4jInitializer(
            uri=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD
        )
        
        success = initializer.initialize_all()
        
        if success:
            logger.info("Neo4j database initialization completed successfully")
        else:
            logger.error("Neo4j database initialization failed")
            
        return success
    except Exception as e:
        logger.error(f"Neo4j initialization error: {str(e)}")
        return False

# Function to process news data into Neo4j
def process_news_data(batch_size=100, max_items=1000, verbose=False):
    """Process news data from Redis into Neo4j"""
    processor = None
    try:
        # Set up logging for this run
        if verbose:
            logging.basicConfig(level=logging.INFO, 
                               format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Initialize Redis client for news data
        from utils.redisClasses import EventTraderRedis
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
        
        # Process news data
        logger.info(f"Processing news data to Neo4j with batch_size={batch_size}, max_items={max_items}...")
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
        if processor:
            processor.close()
        logger.info("News processing completed")



if __name__ == "__main__":
    import sys
    import argparse
    
    # Set up command line arguments
    parser = argparse.ArgumentParser(description="Neo4j processor for EventTrader")
    parser.add_argument("mode", choices=["init", "news", "all"], default="init", nargs="?",
                        help="Mode: 'init' (initialize Neo4j), 'news' (process news), 'all' (both)")
    parser.add_argument("--batch", type=int, default=10, 
                        help="Number of news items to process in each batch")
    parser.add_argument("--max", type=int, default=100, 
                        help="Maximum number of news items to process")
    parser.add_argument("--verbose", "-v", action="store_true", 
                        help="Enable verbose logging")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Force process even if errors occur")
    
    args = parser.parse_args()
    
    # Enable verbose logging for command line operation
    if args.verbose:
        logging.basicConfig(level=logging.INFO, 
                           format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    if args.mode == "init":
        # Run initialization 
        logger.info("Running Neo4j initialization...")
        init_neo4j()
    elif args.mode == "news":
        # Process news data
        logger.info(f"Processing news data with batch_size={args.batch}, max_items={args.max}")
        process_news_data(args.batch, args.max, args.verbose)
    elif args.mode == "all":
        # Run both initialization and news processing
        logger.info(f"Running complete Neo4j setup (batch_size={args.batch}, max_items={args.max})...")
        if init_neo4j():
            logger.info("Initialization successful, now processing news...")
            process_news_data(args.batch, args.max, args.verbose)
        else:
            logger.error("Initialization failed, skipping news processing")
    else:
        logger.error(f"Unknown mode: {args.mode}. Use 'init', 'news', or 'all'")
        print("Usage: python Neo4jProcessor.py [mode] [batch_size] [max_items]")
        print("  mode: 'init' (default), 'news', or 'all'")
        print("  batch_size: Number of news items to process in each batch (default: 10)")
        print("  max_items: Maximum number of news items to process (default: 100)") 