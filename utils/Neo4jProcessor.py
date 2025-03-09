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
from utils.EventTraderNodes import NewsNode, CompanyNode
from utils.date_utils import parse_news_dates  # Import our new date parsing utility

# Add XBRL module to path if needed
# sys.path.append(str(Path(__file__).parent.parent))
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
        """
        Initialize Neo4j database with company nodes.
        This method is kept for backward compatibility and
        simply calls populate_company_nodes().
        """
        # Skip if already initialized
        if self.is_initialized():
            logger.info("Neo4j database already initialized")
            return True
            
        # Simply call populate_company_nodes - avoid code duplication
        return self.populate_company_nodes()

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
            
            # Log available columns to help diagnose missing fields
            logger.info(f"CSV columns available: {list(df.columns)}")
            
            # Check for our critical fields - CORRECTED to match CSV column names
            critical_fields = ['mkt_cap', 'employees', 'shares_out']
            for field in critical_fields:
                if field not in df.columns:
                    logger.warning(f"Critical field '{field}' is missing in CSV")
                else:
                    # Check how many non-null values we have
                    non_null_count = df[field].notna().sum()
                    logger.info(f"Field '{field}' has {non_null_count} non-null values out of {len(df)} rows ({non_null_count/len(df)*100:.1f}%)")
            
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
        Create Company nodes in Neo4j with all required fields and relationships.
        Returns True if successful, False otherwise.
        """
        if not self.connect():
            logger.error("Cannot connect to Neo4j")
            return False
            
        try:
            # Get company data from tradable universe
            universe_data = self.get_tradable_universe()
            if not universe_data:
                logger.warning("No company data found")
                return False
                
            logger.info(f"Creating Company nodes for {len(universe_data)} companies")
            
            # Check if critical fields exist in the data
            first_company = next(iter(universe_data.values()))
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
            for symbol, data in universe_data.items():
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
            for symbol, data in universe_data.items():
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
                if self._create_company_relationships(universe_data, valid_nodes, ticker_to_cik):
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
        Create RELATED_TO relationships between related companies.
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
                        
                    target_node = node_by_cik[related_cik]
                    
                    relationships.append((
                        source_node,
                        target_node,
                        RELATED_TO,
                        {
                            "source_ticker": symbol,
                            "target_ticker": related_ticker,
                            "relationship_type": "news_co_occurrence"
                        }
                    ))
            
            if relationships:
                self.manager.merge_relationships(relationships)
                logger.info(f"Created {len(relationships)} RELATED_TO relationships between companies")
            else:
                logger.info("No company relationships to create")
                
        except Exception as e:
            logger.warning(f"Error creating company relationships: {e}")
            # Continue anyway - relationships aren't critical

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
            logger.warning("No Redis history client available for news processing")
            logger.info("Skipping news processing - Redis client required")
            return True  # Return success as this is not a fatal error
            
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
            updated_count = 0
            error_count = 0
            symbol_missing_count = 0
            cik_missing_count = 0
            
            news_nodes = []  # Collect NewsNode objects
            relationships = []  # Collect relationships
            
            for i in range(0, len(news_keys), batch_size):
                batch_keys = news_keys[i:i+batch_size]
                batch_processed = 0
                
                # Process each news item in the batch
                for key in batch_keys:
                    try:
                        # Extract ID from Redis key: "news:withreturns:44160162.2025-03-06T08.32.21+00.00" 
                        # -> "44160162.2025-03-06T08.32.21+00.00"
                        news_key_id = key.replace("news:withreturns:", "")
                        
                        # Get news data from Redis
                        news_data = self.hist_client.client.get(key)
                        if not news_data:
                            logger.warning(f"No data found for key {key}")
                            continue
                            
                        # Parse JSON data
                        news_item = json.loads(news_data)
                        
                        # Extract basic properties
                        news_id = news_key_id  # Use the full ID from Redis key
                        title = news_item.get('title', '')
                        body = news_item.get('body', '')
                        teaser = news_item.get('teaser', '')
                        
                        # Get creation and update timestamps using our new utility function
                        created_at, updated_at = parse_news_dates(news_item)
                        
                        # Get market session
                        market_session = ""
                        if 'metadata' in news_item and 'event' in news_item['metadata']:
                            market_session = news_item['metadata']['event'].get('market_session', '')
                        
                        # Extract list fields
                        authors = news_item.get('authors', [])
                        if isinstance(authors, str):
                            try:
                                authors = json.loads(authors)
                            except:
                                authors = [authors] if authors else []
                                
                        channels = news_item.get('channels', [])
                        if isinstance(channels, str):
                            try:
                                channels = json.loads(channels)
                            except:
                                channels = [channels] if channels else []
                                
                        tags = news_item.get('tags', [])
                        if isinstance(tags, str):
                            try:
                                tags = json.loads(tags)
                            except:
                                tags = [tags] if tags else []
                        
                        # Create NewsNode object with all properties
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
                            market_session=market_session
                        )
                        
                        news_nodes.append(news_node)
                        
                        # Get symbols mentioned in news
                        symbols = []
                        if 'symbols' in news_item and news_item['symbols']:
                            symbol_raw = news_item['symbols']
                            
                            # Handle list format: ["F", "TSLA"]
                            if isinstance(symbol_raw, list):
                                symbols = [s.upper() for s in symbol_raw if s]
                            
                            # Handle string format (multiple scenarios)
                            elif isinstance(symbol_raw, str):
                                try:
                                    # Try to parse as JSON
                                    if symbol_raw.startswith('[') and symbol_raw.endswith(']'):
                                        json_ready = symbol_raw.replace("'", '"')
                                        symbol_list = json.loads(json_ready)
                                        symbols = [s.upper() for s in symbol_list if s]
                                    else:
                                        # Single symbol string
                                        symbols = [symbol_raw.upper()]
                                except Exception as e:
                                    # Fallback parsing
                                    try:
                                        clean_str = symbol_raw.strip('[]').replace("'", "").replace('"', "")
                                        symbols = [s.strip().upper() for s in clean_str.split(',') if s.strip()]
                                    except Exception as e2:
                                        logger.warning(f"Could not parse symbols: {symbol_raw}")
                        
                        # If no symbols found, log and continue
                        if not symbols:
                            logger.debug(f"No symbols for news item {news_id}")
                            symbol_missing_count += 1
                            continue
                        
                        # Process many-to-many relationships between news and all mentioned companies
                        logger.debug(f"News {news_id} mentions {len(symbols)} symbols: {symbols}")
                        
                        # Create a list of company nodes for this news item
                        news_company_nodes = []
                        
                        for symbol_upper in symbols:
                            # Get CIK for this symbol if available
                            cik = ticker_to_cik.get(symbol_upper)
                            if not cik:
                                cik_missing_count += 1
                                logger.debug(f"No CIK for symbol {symbol_upper}")
                                continue
                            
                            # Get return metrics for this symbol/news item
                            return_metrics = {}
                            if 'returns' in news_item:
                                # Different possible structures for returns data
                                symbol_returns = None
                                
                                # Structure 1: {'returns': {'AAPL': {...}}}
                                if symbol_upper in news_item['returns']:
                                    symbol_returns = news_item['returns'][symbol_upper]
                                
                                # Structure 2: {'returns': {'symbols': {'AAPL': {...}}}}
                                elif 'symbols' in news_item['returns'] and symbol_upper in news_item['returns']['symbols']:
                                    symbol_returns = news_item['returns']['symbols'][symbol_upper]
                                    
                                if symbol_returns:
                                    # Get hourly returns
                                    if 'hourly_return' in symbol_returns:
                                        for metric, value in symbol_returns['hourly_return'].items():
                                            if value is not None and not (isinstance(value, str) and value.lower() == 'nan'):
                                                return_metrics[f'hourly_{metric}'] = value
                                    
                                    # Get session returns
                                    if 'session_return' in symbol_returns:
                                        for metric, value in symbol_returns['session_return'].items():
                                            if value is not None and not (isinstance(value, str) and value.lower() == 'nan'):
                                                return_metrics[f'session_{metric}'] = value
                                    
                                    # Get daily returns
                                    if 'daily_return' in symbol_returns:
                                        for metric, value in symbol_returns['daily_return'].items():
                                            if value is not None and not (isinstance(value, str) and value.lower() == 'nan'):
                                                return_metrics[f'daily_{metric}'] = value
                            
                            # Create the relationship with return metrics
                            # Use EventTraderNodes.CompanyNode instead of XBRLClasses.CompanyNode
                            
                            # Look up company data from universe if available
                            company_data = universe_data.get(symbol_upper, {})
                            company_name = company_data.get('company_name', company_data.get('name', 'Unknown Company'))
                            
                            # Try to find existing company node in Neo4j by CIK
                            company_node = None
                            company_query = """
                            MATCH (c:Company {id: $cik})
                            RETURN c
                            """
                            
                            # Use manager's driver directly instead of run_query
                            with self.manager.driver.session() as session:
                                company_result = session.run(company_query, {"cik": cik})
                                company_record = company_result.single()
                                
                                if company_record:
                                    # Use existing company node
                                    logger.debug(f"Found existing company node for {symbol_upper} (CIK: {cik})")
                                    company_props = dict(company_record['c'])
                                    company_node = CompanyNode.from_neo4j(company_props)
                                else:
                                    # Create a simple company node with basic info
                                    logger.debug(f"Creating new company node for {symbol_upper} (CIK: {cik})")
                                    company_node = CompanyNode(
                                        cik=cik,
                                        name=company_name,
                                        ticker=symbol_upper
                                    )
                                    
                                    # Add other fields if available
                                    if 'exchange' in company_data:
                                        company_node.exchange = company_data.get('exchange')
                                    if 'sector' in company_data:
                                        company_node.sector = company_data.get('sector')
                                    if 'industry' in company_data:
                                        company_node.industry = company_data.get('industry')
                                    
                                    # Create the company node in Neo4j
                                    self.manager.merge_nodes([company_node])
                                
                            # Add relationship properties - include symbol for clarity in graph
                            rel_props = {
                                'symbol': symbol_upper,
                                'created_at': datetime.now().isoformat(),
                                **return_metrics
                            }
                            
                            # Add to relationships list for this news-company pair
                            relationships.append((news_node, company_node, RelationType.MENTIONS, rel_props))
                        
                        batch_processed += 1
                        processed_count += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing news item {key}: {e}")
                        error_count += 1
                        
                # Log progress
                logger.info(f"Processed {batch_processed}/{len(batch_keys)} in current batch")
            
            # Export News nodes to Neo4j using Neo4jManager
            if news_nodes:
                logger.info(f"Exporting {len(news_nodes)} News nodes to Neo4j")
                # Use a direct Cypher query to create News nodes without NodeType restriction
                with self.manager.driver.session() as session:
                    for node in news_nodes:
                        properties = node.properties
                        news_id = node.id
                        query = """
                        MERGE (n:News {id: $id})
                        ON CREATE SET n += $properties
                        ON MATCH SET n += $properties
                        """
                        session.run(query, {"id": news_id, "properties": properties})
                logger.info(f"Created {len(news_nodes)} News nodes directly")
            
            # Create relationships similarly with direct Cypher query
            if relationships:
                logger.info(f"Creating {len(relationships)} News-Company relationships")
                with self.manager.driver.session() as session:
                    for rel in relationships:
                        source, target, rel_type, props = rel
                        # Handle properties
                        props_dict = props if props else {}
                        
                        # Execute the merge
                        query = f"""
                        MATCH (s:News {{id: $source_id}})
                        MATCH (t:Company {{id: $target_id}})
                        MERGE (s)-[r:{rel_type.value}]->(t)
                        SET r += $properties
                        """
                        session.run(query, {
                            "source_id": source.id, 
                            "target_id": target.id,
                            "properties": props_dict
                        })
                logger.info(f"Created {len(relationships)} relationships directly")
            
            # Get database stats
            self.manager.get_neo4j_db_counts()
            
            # Detailed summary
            logger.info(f"News processing complete:")
            logger.info(f"  - News nodes created: {len(news_nodes)}")
            logger.info(f"  - Relationships created: {len(relationships)}")
            logger.info(f"  - Errors: {error_count}")
            logger.info(f"  - News items without symbols: {symbol_missing_count}")
            logger.info(f"  - Symbols without CIK mapping: {cik_missing_count}")
            
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
def process_news_data(batch_size=100, max_items=1000, verbose=False):
    """Process news data from Redis into Neo4j
    
    Args:
        batch_size: Number of news items to process in each batch
        max_items: Maximum number of news items to process in total
        verbose: Whether to enable verbose logging
    """
    processor = None
    try:
        # Set up logging for this run
        if verbose:
            logging.basicConfig(level=logging.INFO, 
                               format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        processor = Neo4jProcessor()
        if not processor.connect():
            logger.error("Cannot connect to Neo4j")
            return False
            
        # Make sure Neo4j is initialized first
        if not processor.is_initialized():
            logger.warning("Neo4j not initialized. Initializing now...")
            if not processor.initialize():
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
        # Always ensure proper cleanup
        if processor:
            try:
                processor.close()
            except Exception as cleanup_error:
                logger.warning(f"Error during Neo4j connection cleanup: {cleanup_error}")
                
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