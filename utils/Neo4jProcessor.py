# Standard Library Imports
import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple

# Third-Party Imports
import pandas as pd
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, DatabaseUnavailable

# Internal Imports - Configuration and Keys
from eventtrader.keys import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
from utils.log_config import get_logger, setup_logging

# Internal Imports - Redis Utilities
from utils.redisClasses import EventTraderRedis, RedisClient

# Internal Imports - EventTrader Node Classes
from utils.EventTraderNodes import (
    NewsNode, CompanyNode, SectorNode, 
    IndustryNode, MarketIndexNode
)

# Internal Imports - Date Utilities
from utils.date_utils import parse_news_dates, parse_date  

# Internal Imports - Metadata Fields
from utils.metadata_fields import MetadataFields

# Internal Imports - XBRL Processing
from XBRL.Neo4jManager import Neo4jManager
from XBRL.XBRLClasses import NodeType, RelationType



# Set up logger
logger = get_logger(__name__)

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
        self._loaded_etf_mappings = False
        
        # Initialize Redis clients if provided
        if event_trader_redis:
            self.event_trader_redis = event_trader_redis
            self.live_client = event_trader_redis.live_client
            self.hist_client = event_trader_redis.history_client
            self.source_type = event_trader_redis.source
            logger.info(f"Initialized Redis clients for source: {self.source_type}")
            
            # Test Redis access
            self._collect_redis_key_counts()
    
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


    def _process_deduplicated_news(self, news_id, news_data):
        """
        Process news data with deduplication, standardized fields, and efficient symbol relationships.
        Uses a hash-based MERGE pattern with conditional updates based on timestamps.
        
        Args:
            news_id: Unique identifier for the news
            news_data: Dictionary containing news data
            
        Returns:
            bool: Success status
        """
        logger.debug(f"Processing deduplicated news {news_id}")
        
        try:
            # Get ticker to CIK mappings from universe data
            universe_data = self.get_tradable_universe()
            ticker_to_cik = {}
            for symbol, data in universe_data.items():
                cik = data.get('cik', '').strip()
                if cik and cik.lower() not in ['nan', 'none', '']:
                    ticker_to_cik[symbol.upper()] = str(cik).zfill(10)
            
            # We don't need ETF mappings anymore
            # Completely removed ETF fallback logic
            
            # Extract timestamps with proper parsing
            created_at, updated_at = parse_news_dates(news_data)
            created_str = created_at.isoformat() if created_at else datetime.now().isoformat()
            updated_str = updated_at.isoformat() if updated_at else created_str
            
            # Extract basic properties - standardize field names
            title = news_data.get('title', '')
            body = news_data.get('body', news_data.get('content', ''))  # Fallback to content if body not available
            teaser = news_data.get('teaser', '')
            url = news_data.get('url', '')
            
            # Extract and prepare list fields - standardize JSON format
            authors = json.dumps(self._parse_list_field(news_data.get('authors', [])))
            tags = json.dumps(self._parse_list_field(news_data.get('tags', [])))
            channels = json.dumps(self._parse_list_field(news_data.get('channels', [])))
            
            # Extract market session - always include even if empty
            market_session = ""
            if 'metadata' in news_data and 'event' in news_data['metadata']:
                market_session = news_data['metadata']['event'].get('market_session', '')
                
            # Extract returns schedule - always include even if empty
            returns_schedule = {}
            if 'metadata' in news_data and 'returns_schedule' in news_data['metadata']:
                raw_schedule = news_data['metadata']['returns_schedule']
                # Parse each date in the schedule
                for key in ['hourly', 'session', 'daily']:
                    if key in raw_schedule and raw_schedule[key]:
                        # Parse the date string to ensure it's valid, then convert back to string
                        date_obj = parse_date(raw_schedule[key])
                        if date_obj:
                            returns_schedule[key] = date_obj.isoformat()
            returns_schedule_json = json.dumps(returns_schedule)
            
            # Extract symbols mentioned in news
            symbols = self._extract_symbols(news_data.get('symbols', []))
            
            # Create a mapping of symbol to benchmarks from the instruments array - only for ETF properties
            symbol_benchmarks = {}
            if 'metadata' in news_data and 'instruments' in news_data['metadata']:
                for instrument in news_data['metadata']['instruments']:
                    symbol = instrument.get('symbol', '')
                    if symbol and 'benchmarks' in instrument:
                        symbol_benchmarks[symbol.upper()] = {
                            'sector': instrument['benchmarks'].get('sector', ''),
                            'industry': instrument['benchmarks'].get('industry', '')
                        }
            
            # Prepare data structures for batch symbol processing
            valid_symbols = []
            symbol_data = {}
            
            # Preprocess symbols to collect metrics and filter valid ones
            for symbol in symbols:
                symbol_upper = symbol.upper()
                cik = ticker_to_cik.get(symbol_upper)
                if not cik:
                    logger.warning(f"No CIK found for symbol {symbol_upper}")
                    continue  # Skip symbols without CIK
                
                # Get return metrics for this symbol
                metrics = self._extract_return_metrics(news_data, symbol_upper)
                
                # Get sector and industry information - ONLY from company data
                company_data = universe_data.get(symbol_upper, {})
                sector = company_data.get('sector')
                industry = company_data.get('industry')
                
                # Skip symbol processing if missing sector or industry data
                if not sector or not industry:
                    logger.warning(f"Symbol {symbol_upper} is missing sector or industry data - skipping relationship creation")
                    continue
                    
                # Only add to valid symbols if it passed all checks
                valid_symbols.append(symbol_upper)
                
                # Store data for later batch processing
                symbol_data[symbol_upper] = {
                    'cik': cik,
                    'metrics': metrics,
                    'timestamp': datetime.now().isoformat(),
                    'sector': sector,
                    'industry': industry
                }
            
            # Prepare parameters for each relationship type
            company_params = []
            sector_params = []
            industry_params = []
            market_params = []

            # Prepare company relationship parameters
            for symbol in valid_symbols:
                symbol_data_item = symbol_data[symbol]
                # Prepare metrics as property
                props = {
                    'symbol': symbol,
                    'created_at': symbol_data_item['timestamp']
                }
                
                # Add stock metrics
                for timeframe in ['hourly', 'session', 'daily']:
                    metric_key = f"{timeframe}_stock"
                    if metric_key in symbol_data_item['metrics']:
                        props[metric_key] = symbol_data_item['metrics'][metric_key]
                
                company_params.append({
                    'cik': symbol_data_item['cik'],
                    'properties': props
                })
            
            # Prepare sector relationship parameters
            for symbol in valid_symbols:
                symbol_data_item = symbol_data[symbol]
                sector = symbol_data_item['sector']
                
                # Prepare metrics as property
                props = {
                    'symbol': symbol,
                    'created_at': symbol_data_item['timestamp']
                }
                
                # Add sector metrics
                for timeframe in ['hourly', 'session', 'daily']:
                    metric_key = f"{timeframe}_sector"
                    if metric_key in symbol_data_item['metrics']:
                        props[metric_key] = symbol_data_item['metrics'][metric_key]
                
                # Get sector_etf for property only - not for identification
                sector_etf = None
                company_data = universe_data.get(symbol, {})
                
                # Get ETF info from company data
                if 'sector_etf' in company_data and company_data['sector_etf']:
                    sector_etf = company_data['sector_etf']
                # Fallback to benchmark data for ETF property only if needed
                elif symbol in symbol_benchmarks and symbol_benchmarks[symbol]['sector']:
                    sector_etf = symbol_benchmarks[symbol]['sector']
                
                # Normalize sector ID and ensure it's not just the ETF ticker
                sector_id = sector.replace(" ", "")
                
                # Protection against using ETF as ID - for sectors
                if sector_etf and sector_id == sector_etf:
                    # Instead of warning, use concrete prevention
                    logger.error(f"Sector ID {sector_id} matches ETF ticker {sector_etf} - using prefixed format to prevent this")
                    # Use prefixed format to avoid this issue
                    sector_id = f"Sector_{sector.replace(' ', '_')}"
                
                sector_params.append({
                    'sector_id': sector_id,
                    'sector_name': sector,
                    'sector_etf': sector_etf,
                    'properties': props
                })
            
            # Prepare industry relationship parameters
            for symbol in valid_symbols:
                symbol_data_item = symbol_data[symbol]
                industry = symbol_data_item['industry']
                
                # Prepare metrics as property
                props = {
                    'symbol': symbol,
                    'created_at': symbol_data_item['timestamp']
                }
                
                # Add industry metrics
                for timeframe in ['hourly', 'session', 'daily']:
                    metric_key = f"{timeframe}_industry"
                    if metric_key in symbol_data_item['metrics']:
                        props[metric_key] = symbol_data_item['metrics'][metric_key]
                
                # Get industry_etf for property only - not for identification
                industry_etf = None
                company_data = universe_data.get(symbol, {})
                
                # Get ETF info from company data
                if 'industry_etf' in company_data and company_data['industry_etf']:
                    industry_etf = company_data['industry_etf']
                # Fallback to benchmark data for ETF property only if needed
                elif symbol in symbol_benchmarks and symbol_benchmarks[symbol]['industry']:
                    industry_etf = symbol_benchmarks[symbol]['industry']
                
                # Normalize industry ID and ensure it's not just the ETF ticker
                industry_id = industry.replace(" ", "")
                
                # Protection against using ETF as ID - for industries
                if industry_etf and industry_id == industry_etf:
                    # Instead of warning, use concrete prevention
                    logger.error(f"Industry ID {industry_id} matches ETF ticker {industry_etf} - using prefixed format to prevent this")
                    # Use prefixed format to avoid this issue
                    industry_id = f"Industry_{industry.replace(' ', '_')}"
                
                industry_params.append({
                    'industry_id': industry_id,
                    'industry_name': industry,
                    'industry_etf': industry_etf,
                    'properties': props
                })
            
            # Prepare market index relationship parameters
            for symbol in valid_symbols:
                symbol_data_item = symbol_data[symbol]
                has_macro_metrics = False
                
                # Prepare metrics as property
                props = {
                    'symbol': symbol,
                    'created_at': symbol_data_item['timestamp']
                }
                
                # Add macro metrics
                for timeframe in ['hourly', 'session', 'daily']:
                    metric_key = f"{timeframe}_macro"
                    if metric_key in symbol_data_item['metrics']:
                        props[metric_key] = symbol_data_item['metrics'][metric_key]
                        has_macro_metrics = True
                
                if has_macro_metrics:
                    market_params.append({
                        'properties': props
                    })
            
            # Execute deduplication and conditional update logic with direct Cypher
            # KEEP ALL DATABASE OPERATIONS INSIDE THIS SINGLE SESSION CONTEXT
            with self.manager.driver.session() as session:
                # Create/update news node with conditional updates
                # This follows the pattern from the deduplication notes
                result = session.run("""
                MERGE (n:News {id: $id})
                ON CREATE SET 
                    n.id = $id,
                    n.title = $title,
                    n.body = $body,
                    n.teaser = $teaser,
                    n.created = $created,
                    n.updated = $updated,
                    n.url = $url,
                    n.authors = $authors,
                    n.tags = $tags,
                    n.channels = $channels,
                    n.market_session = $market_session,
                    n.returns_schedule = $returns_schedule
                ON MATCH SET 
                    // Only update content-related fields if this is newer
                    n.title = CASE WHEN $updated > n.updated THEN $title ELSE n.title END,
                    n.body = CASE WHEN $updated > n.updated THEN $body ELSE n.body END,
                    n.teaser = CASE WHEN $updated > n.updated THEN $teaser ELSE n.teaser END,
                    n.updated = CASE WHEN $updated > n.updated THEN $updated ELSE n.updated END,
                    // Always update these fields even if not newer (additive properties)
                    n.url = $url,
                    n.authors = $authors,
                    n.tags = $tags,
                    n.channels = $channels,
                    n.market_session = $market_session,
                    n.returns_schedule = $returns_schedule
                RETURN n
                """, {
                    "id": news_id,
                    "title": title,
                    "body": body,
                    "teaser": teaser,
                    "created": created_str,
                    "updated": updated_str, 
                    "url": url,
                    "authors": authors,
                    "tags": tags,
                    "channels": channels,
                    "market_session": market_session,
                    "returns_schedule": returns_schedule_json
                })
                
                # Process the result
                record = result.single()
                if not record:
                    logger.error(f"Failed to create or update news node {news_id}")
                    return False
                    
                # Skip processing if no symbols found
                if not valid_symbols:
                    logger.warning(f"No valid symbols found for news {news_id}")
                    return True
            
                # ----- Use UNWIND pattern for efficient batch processing of relationships -----
                
                # 1. Create Company INFLUENCES relationships using UNWIND pattern
                if company_params:
                    company_result = session.run("""
                    MATCH (n:News {id: $news_id})
                    UNWIND $company_params AS param
                    MATCH (c:Company {cik: param.cik})
                    MERGE (n)-[r:INFLUENCES]->(c)
                    SET r += param.properties
                    RETURN count(r) as relationship_count
                    """, {
                        "news_id": news_id,
                        "company_params": company_params
                    })
                    for record in company_result:
                        logger.info(f"Created {record['relationship_count']} INFLUENCES relationships to companies")
                
                # 2. Create Sector INFLUENCES relationships using UNWIND pattern
                if sector_params:
                    sector_result = session.run("""
                    MATCH (n:News {id: $news_id})
                    UNWIND $sector_params AS param
                    MERGE (s:Sector {id: param.sector_id})
                    ON CREATE SET 
                        s.name = param.sector_name,
                        s.etf = param.sector_etf
                    SET
                        s.etf = CASE 
                            WHEN param.sector_etf IS NOT NULL AND (s.etf IS NULL OR s.etf = '') 
                            THEN param.sector_etf 
                            ELSE s.etf 
                        END
                    MERGE (n)-[r:INFLUENCES]->(s)
                    SET r += param.properties
                    RETURN count(r) as relationship_count
                    """, {
                        "news_id": news_id,
                        "sector_params": sector_params
                    })
                    for record in sector_result:
                        logger.info(f"Created {record['relationship_count']} INFLUENCES relationships to sectors")
                
                # 3. Create Industry INFLUENCES relationships using UNWIND pattern
                if industry_params:
                    industry_result = session.run("""
                    MATCH (n:News {id: $news_id})
                    UNWIND $industry_params AS param
                    MERGE (i:Industry {id: param.industry_id})
                    ON CREATE SET 
                        i.name = param.industry_name,
                        i.etf = param.industry_etf
                    SET
                        i.etf = CASE 
                            WHEN param.industry_etf IS NOT NULL AND (i.etf IS NULL OR i.etf = '') 
                            THEN param.industry_etf 
                            ELSE i.etf 
                        END
                    MERGE (n)-[r:INFLUENCES]->(i)
                    SET r += param.properties
                    RETURN count(r) as relationship_count
                    """, {
                        "news_id": news_id,
                        "industry_params": industry_params
                    })
                    for record in industry_result:
                        logger.info(f"Created {record['relationship_count']} INFLUENCES relationships to industries")
                
                # 4. Create Market Index INFLUENCES relationships using UNWIND pattern
                if market_params:
                    market_result = session.run("""
                    MATCH (n:News {id: $news_id})
                    MERGE (m:MarketIndex {id: 'SPY'})
                    ON CREATE SET
                        m.name = 'S&P 500 ETF',
                        m.ticker = 'SPY',
                        m.etf = 'SPY'
                    SET
                        m.ticker = 'SPY',
                        m.etf = 'SPY',
                        m.name = CASE
                            WHEN m.name IS NULL OR m.name = ''
                            THEN 'S&P 500 ETF'
                            ELSE m.name
                        END
                    WITH n, m
                    UNWIND $market_params AS param
                    MERGE (n)-[r:INFLUENCES]->(m)
                    SET r += param.properties
                    RETURN count(r) as relationship_count
                    """, {
                        "news_id": news_id,
                        "market_params": market_params
                    })
                    for record in market_result:
                        logger.info(f"Created {record['relationship_count']} INFLUENCES relationships to market index")
                
                logger.info(f"Successfully processed news {news_id} with {len(valid_symbols)} symbols")
                return True
                
        except Exception as e:
            logger.error(f"Error processing news {news_id}: {e}")
            return False

    def _load_etf_mappings(self):
        """
        Load ETF mappings for informational purposes only.
        These are not used for node identification, only for tracking ETF properties.
        """
        if self._loaded_etf_mappings:
            return True
        
        # Initialize mappings
        self.etf_to_sector_id = {}
        self.etf_to_industry_id = {}
        
        # Track many-to-one mappings for detailed reporting
        self.etf_to_sectors = {}  # {etf: [sector_names]}
        self.etf_to_industries = {}  # {etf: [industry_names]}

        try:
            with self.manager.driver.session() as session:
                # Get all ETF mappings from sectors
                result = session.run("""
                    MATCH (s:Sector) 
                    WHERE s.etf IS NOT NULL AND s.etf <> ""
                    RETURN s.etf as etf, s.id as id, s.name as name
                """)
                
                # Process sector mappings
                for record in result:
                    etf = record["etf"]
                    sector_id = record["id"]
                    sector_name = record["name"]
                    
                    # Track for many-to-one mapping detection
                    if etf not in self.etf_to_sectors:
                        self.etf_to_sectors[etf] = []
                    self.etf_to_sectors[etf].append(sector_name)
                    
                    # Store the last one encountered as the default (not ideal but consistent)
                    self.etf_to_sector_id[etf] = sector_id
                
                # Get all ETF mappings from industries
                result = session.run("""
                    MATCH (i:Industry) 
                    WHERE i.etf IS NOT NULL AND i.etf <> ""
                    RETURN i.etf as etf, i.id as id, i.name as name
                """)
                
                # Process industry mappings
                for record in result:
                    etf = record["etf"]
                    industry_id = record["id"]
                    industry_name = record["name"]
                    
                    # Track for many-to-one mapping detection
                    if etf not in self.etf_to_industries:
                        self.etf_to_industries[etf] = []
                    self.etf_to_industries[etf].append(industry_name)
                    
                    # Store the last one encountered as the default (not ideal but consistent)
                    self.etf_to_industry_id[etf] = industry_id
                
                # Log multi-mapping situations
                for etf, sectors in self.etf_to_sectors.items():
                    if len(sectors) > 1:
                        sector_list = ", ".join(sectors)
                        logger.warning(f"Multiple sectors map to the same ETF: {etf} -> {sector_list}")
                
                for etf, industries in self.etf_to_industries.items():
                    if len(industries) > 1:
                        industry_list = ", ".join(industries)
                        logger.warning(f"Multiple industries map to the same ETF: {etf} -> {industry_list}")
                
                self._loaded_etf_mappings = True
                logger.info(f"Loaded ETF mappings: {len(self.etf_to_sector_id)} sectors, {len(self.etf_to_industry_id)} industries")
                
                # Since we only use company data for identification, these mappings are just FYI
                logger.info("Note: ETF mappings are only used for properties, not for node identification")
                return True
        except Exception as e:
            logger.error(f"Error loading ETF mappings: {e}")
            return False

    def process_news_to_neo4j(self, batch_size=100, max_items=None, include_without_returns=True) -> bool:
        """
        Process news from Redis to Neo4j with deduplication.
        
        Args:
            batch_size: Number of items to process in each batch
            max_items: Maximum number of items to process (for debugging)
            include_without_returns: Whether to process news from the withoutreturns namespace
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.manager:
                if not self.connect():
                    logger.error("Cannot connect to Neo4j")
                    return False
            
            if not hasattr(self, 'hist_client') or not self.hist_client:
                logger.warning("No Redis history client available for news processing")
                return False
                
            # Get keys for withreturns first (these have return data)
            pattern = "news:withreturns:*"
            withreturns_keys = self.hist_client.client.keys(pattern)
            logger.info(f"Found {len(withreturns_keys)} news keys matching {pattern}")
            
            # Get keys for withoutreturns if requested
            withoutreturns_keys = []
            if include_without_returns:
                pattern = "news:withoutreturns:*"
                withoutreturns_keys = self.hist_client.client.keys(pattern)
                logger.info(f"Found {len(withoutreturns_keys)} news keys matching {pattern}")
            
            # Combine and sort keys by ID (process newer items first)
            news_keys = withreturns_keys + withoutreturns_keys
            # Sort by ID if needed (optional)
            
            # Limit the number of items to process
            if max_items is not None and len(news_keys) > max_items:
                news_keys = news_keys[:max_items]
                
            logger.info(f"Processing {len(news_keys)} news keys")
            
            # Load universe data for ticker-to-CIK mapping
            universe_data = self.get_tradable_universe()
            ticker_to_cik = {}
            ticker_to_name = {}
            
            for symbol, data in universe_data.items():
                cik = data.get('cik', '').strip()
                if cik and cik.lower() not in ['nan', 'none', '']:
                    ticker_to_cik[symbol.upper()] = str(cik).zfill(10)
                    ticker_to_name[symbol.upper()] = data.get('company_name', data.get('name', symbol)).strip()
            
            # Process in batches
            processed_count = 0
            error_count = 0
            
            for i in range(0, len(news_keys), batch_size):
                batch_keys = news_keys[i:i+batch_size]
                
                # Process each news item in the batch
                for key in batch_keys:
                    try:
                        # Extract ID and namespace from Redis key
                        parts = key.split(':')
                        namespace = parts[1] if len(parts) > 1 else "unknown"
                        concat_id = parts[2] if len(parts) > 2 else key
                        
                        # Extract just the base ID (part before the period)
                        base_id = concat_id.split('.')[0] if '.' in concat_id else concat_id
                        
                        # Add source prefix for future multi-source compatibility
                        news_id = f"bzNews_{base_id}"
                        
                        # Get news data from Redis
                        news_data = self.hist_client.client.get(key)
                        if not news_data:
                            logger.warning(f"No data found for key {key}")
                            continue
                            
                        # Parse JSON data
                        news_item = json.loads(news_data)
                        
                        # Process news data
                        success = self._process_deduplicated_news(news_id, news_item)
                        
                        if success:
                            processed_count += 1
                            
                            # Delete processed keys from withreturns namespace only
                            # We keep withoutreturns keys as they may get returns later


                            # if namespace == "withreturns":
                            #     try:
                            #         self.hist_client.client.delete(key)
                            #         logger.debug(f"Deleted processed key: {key}")
                            #     except Exception as e:
                            #         logger.warning(f"Error deleting key {key}: {e}")

                            
                        else:
                            error_count += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing news key {key}: {e}")
                        error_count += 1
                
                logger.info(f"Processed batch {i//batch_size + 1}/{(len(news_keys) + batch_size - 1)//batch_size}")
                
            # Summary and status
            logger.info(f"Finished processing news to Neo4j. Processed: {processed_count}, Errors: {error_count}")
            
            # Remove batch deletion approach in favor of immediate deletion
            return processed_count > 0 or error_count == 0
                
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
            if timeframe not in symbol_returns:
                continue
                
            if not isinstance(symbol_returns[timeframe], dict):
                logger.warning(f"Expected dictionary for {timeframe} but got {type(symbol_returns[timeframe])} for symbol {symbol}")
                continue
            
            short_timeframe = timeframe.split('_')[0]  # hourly, session, daily
            
            # Extract stock metrics
            if 'stock' in symbol_returns[timeframe]:
                metrics[f"{short_timeframe}_stock"] = symbol_returns[timeframe]['stock']
            
            # Extract sector metrics
            if 'sector' in symbol_returns[timeframe]:
                metrics[f"{short_timeframe}_sector"] = symbol_returns[timeframe]['sector']
            
            # Extract industry metrics
            if 'industry' in symbol_returns[timeframe]:
                metrics[f"{short_timeframe}_industry"] = symbol_returns[timeframe]['industry']
            
            # Extract macro metrics
            if 'macro' in symbol_returns[timeframe]:
                metrics[f"{short_timeframe}_macro"] = symbol_returns[timeframe]['macro']
        
        return metrics



    def process_with_pubsub(self):
        """
        Process news from Redis to Neo4j using PubSub for immediate notification.
        Non-blocking and highly efficient compared to polling.
        """
        logger.info("Starting event-driven Neo4j processing")
        
        if not hasattr(self, 'event_trader_redis') or not self.event_trader_redis:
            logger.error("No Redis client available for event-driven processing")
            return
        
        # Ensure Neo4j connection is established
        if not self.manager:
            if not self.connect():
                logger.error("Failed to connect to Neo4j, cannot proceed with processing")
                return
        
        # Create a dedicated PubSub client
        pubsub = self.event_trader_redis.live_client.create_pubsub_connection()
        
        # Subscribe to both withreturns and withoutreturns channels
        withreturns_channel = f"{self.event_trader_redis.source}:withreturns"
        withoutreturns_channel = f"{self.event_trader_redis.source}:withoutreturns"
        pubsub.subscribe(withreturns_channel, withoutreturns_channel)
        
        # Control flag
        self.pubsub_running = True
        
        # Process any existing items first (one-time batch processing)
        self.process_news_to_neo4j(batch_size=50, max_items=None, include_without_returns=True)
        
        # Event-driven processing loop
        while self.pubsub_running:
            try:
                # Non-blocking message check with 0.1s timeout
                message = pubsub.get_message(timeout=0.1)
                
                if message and message['type'] == 'message':
                    channel = message['channel']
                    news_id = message.get('data')
                    
                    if not news_id:
                        continue
                    
                    # Determine if this is from withreturns or withoutreturns
                    is_withreturns = 'withreturns' in channel
                    
                    # Get the news data
                    key_prefix = "withreturns" if is_withreturns else "withoutreturns"
                    key = f"{self.event_trader_redis.source}:{key_prefix}:{news_id}"
                    
                    try:
                        # Get and process the news item
                        raw_data = self.event_trader_redis.history_client.client.get(key)
                        if raw_data:
                            news_data = json.loads(raw_data)
                            success = self._process_deduplicated_news(
                                news_id=f"bzNews_{news_id.split('.')[0]}", 
                                news_data=news_data
                            )
                            
                            # Delete from withreturns after successful processing
                            # if success and is_withreturns:
                            #     self.event_trader_redis.history_client.client.delete(key)
                            #     logger.debug(f"Deleted processed item: {key}")


                    except Exception as e:
                        logger.error(f"Error processing {key}: {e}")
                
                # Periodically check for items that might have been missed (every 60 seconds)
                # This is a safety net, not the primary mechanism
                current_time = int(time.time())
                if current_time % 60 == 0:
                    self.process_news_to_neo4j(batch_size=10, max_items=10, include_without_returns=False)
                    time.sleep(1)  # Prevent repeated execution in the same second
                    
            except Exception as e:
                logger.error(f"Error in PubSub processing: {e}")
                # Try to reconnect to Neo4j if connection appears to be lost
                if not self.manager or "Neo4j" in str(e) or "Connection" in str(e):
                    logger.warning("Attempting to reconnect to Neo4j")
                    self.connect()
                time.sleep(1)
        
        # Clean up
        try:
            pubsub.unsubscribe()
            pubsub.close()
        except:
            pass
            
        logger.info("Stopped event-driven Neo4j processing")
        
    def stop_pubsub_processing(self):
        """Stop the PubSub processing loop"""
        self.pubsub_running = False



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








if __name__ == "__main__":
    import sys
    import argparse
    
    # Set up command line arguments
    parser = argparse.ArgumentParser(description="Neo4j processor for EventTrader")
    parser.add_argument("mode", choices=["init", "news", "all"], default="init", nargs="?",
                        help="Mode: 'init' (initialize Neo4j), 'news' (process news), 'all' (both)")
    parser.add_argument("--batch", type=int, default=10, 
                        help="Number of news items to process in each batch")
    parser.add_argument("--max", type=int, default=0, 
                        help="Maximum number of news items to process (0 for all items)")
    parser.add_argument("--verbose", "-v", action="store_true", 
                        help="Enable verbose logging")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Force process even if errors occur")
    parser.add_argument("--skip-without-returns", action="store_true",
                        help="Skip processing news from the withoutreturns namespace")
    
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
        include_without_returns = not args.skip_without_returns
        # Convert 0 to None to process all items
        max_items = None if args.max == 0 else args.max
        logger.info(f"Processing news data with batch_size={args.batch}, max_items={max_items}, include_without_returns={include_without_returns}")
        process_news_data(args.batch, max_items, args.verbose, include_without_returns)
    elif args.mode == "all":
        # Run both initialization and news processing
        include_without_returns = not args.skip_without_returns
        # Convert 0 to None to process all items
        max_items = None if args.max == 0 else args.max
        logger.info(f"Running complete Neo4j setup (batch_size={args.batch}, max_items={max_items}, include_without_returns={include_without_returns})...")
        if init_neo4j():
            logger.info("Initialization successful, now processing news...")
            process_news_data(args.batch, max_items, args.verbose, include_without_returns)
        else:
            logger.error("Initialization failed, skipping news processing")
    else:
        logger.error(f"Unknown mode: {args.mode}. Use 'init', 'news', or 'all'")
        print("Usage: python Neo4jProcessor.py [mode] [batch_size] [max_items]")
        print("  mode: 'init' (default), 'news', or 'all'")
        print("  batch_size: Number of news items to process in each batch (default: 10)")
        print("  max_items: Maximum number of news items to process (default: 0)") 