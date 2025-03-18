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
    IndustryNode, MarketIndexNode, ReportNode
)

# Internal Imports - Date Utilities
from utils.date_utils import parse_news_dates, parse_date  

# Internal Imports - Metadata Fields
from utils.metadata_fields import MetadataFields

# Internal Imports - XBRL Processing
from XBRL.Neo4jManager import Neo4jManager
from XBRL.XBRLClasses import NodeType, RelationType

# Internal Imports - Redis Constants
from utils.redis_constants import RedisKeys

# Internal Imports - Neo4j Initializer
from utils.Neo4jInitializer import Neo4jInitializer

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
        if not self.universe_data:
            self.universe_data = self._get_universe()
            if not self.universe_data:
                logger.warning("No company data found")
                return False
        
        # Use the dedicated initializer class
        initializer = Neo4jInitializer(
            uri=self.uri,
            username=self.username,
            password=self.password,
            universe_data=self.universe_data
        )
        
        # Run the initialization process
        success = initializer.initialize_all()
        if success:
            logger.info("Neo4j initialization complete")
        else:
            logger.error("Neo4j initialization failed")
        
        return success

    def _get_universe(self):
        """
        Private method to get tradable universe with caching.
        
        Returns:
            dict: Dictionary of stock universe data
        """
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
            universe_data = self._get_universe()
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




    def process_news_to_neo4j(self, batch_size=100, max_items=None, include_without_returns=True) -> bool:
        """
        Process news items from Redis to Neo4j
        
        Args:
            batch_size: Number of news items to process in each batch
            max_items: Maximum number of news items to process
            include_without_returns: Whether to include news items without returns
            
        Returns:
            bool: True if processing completed without errors
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
            universe_data = self._get_universe()
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

    def _process_deduplicated_report(self, report_id, report_data):
        """
        Process report data with deduplication, standardized fields, and efficient symbol relationships.
        Uses a hash-based MERGE pattern with conditional updates based on timestamps.
        Similar to _process_deduplicated_news but for SEC reports.
        
        Args:
            report_id: Unique identifier for the report (accessionNo)
            report_data: Dictionary containing report data
            
        Returns:
            bool: Success status
        """
        logger.debug(f"Processing deduplicated report {report_id}")
        
        try:
            # Get universe data for ticker-to-CIK mappings
            universe_data = self._get_universe()
            ticker_to_cik = {}
            for symbol, data in universe_data.items():
                cik = data.get('cik', '').strip()
                if cik and cik.lower() not in ['nan', 'none', '']:
                    ticker_to_cik[symbol.upper()] = str(cik).zfill(10)
            
            # Extract timestamps with proper parsing
            filed_at = parse_date(report_data.get('filedAt')) if report_data.get('filedAt') else None
            updated_at = parse_date(report_data.get('updated')) if report_data.get('updated') else None
            
            filed_str = filed_at.isoformat() if filed_at else datetime.now().isoformat()
            updated_str = updated_at.isoformat() if updated_at else filed_str
            
            # Extract basic properties
            form_type = report_data.get('formType', '')
            description = report_data.get('description', '')
            cik = report_data.get('cik', '')
            if cik:
                cik = str(cik).zfill(10)
            company_name = report_data.get('companyName', '')
            period_end = report_data.get('periodEnd', report_data.get('periodOfReport', ''))
            is_amendment = report_data.get('isAmendment', False)
            
            # Extract URL fields
            primary_document_url = report_data.get('primaryDocumentUrl', '')
            link_to_html = report_data.get('linkToHtml', '')
            link_to_txt = report_data.get('linkToTxt', '')
            link_to_filing_details = report_data.get('linkToFilingDetails', '')
            
            # Process complex fields
            exhibits = json.dumps(report_data.get('exhibits', {}))
            entities = json.dumps(report_data.get('entities', []))
            items = json.dumps(report_data.get('items', []))
            symbols_list = report_data.get('symbols', [])
            
            # Extract and prepare symbols list
            symbols = []
            if isinstance(symbols_list, list):
                symbols = [s.upper() for s in symbols_list if s]
            elif isinstance(symbols_list, str):
                try:
                    if symbols_list.startswith('[') and symbols_list.endswith(']'):
                        content = symbols_list.replace("'", '"')  # Make JSON-compatible
                        symbols = [s.upper() for s in json.loads(content) if s]
                    else:
                        symbols = [symbols_list.upper()]  # Single item
                except:
                    symbols = []
            
            # Extract symbols from metadata if available
            if 'metadata' in report_data and 'instruments' in report_data['metadata']:
                for instrument in report_data['metadata']['instruments']:
                    symbol = instrument.get('symbol', '')
                    if symbol and symbol.upper() not in symbols:
                        symbols.append(symbol.upper())
            
            symbols_json = json.dumps(symbols)
            
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
                metrics = self._extract_return_metrics(report_data, symbol_upper)
                
                # Get sector and industry information
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
                
                # Normalize sector ID
                sector_id = sector.replace(" ", "")
                
                # Protection against using ETF as ID - for sectors
                if sector_etf and sector_id == sector_etf:
                    logger.error(f"Sector ID {sector_id} matches ETF ticker {sector_etf} - using prefixed format to prevent this")
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
                
                # Normalize industry ID
                industry_id = industry.replace(" ", "")
                
                # Protection against using ETF as ID - for industries
                if industry_etf and industry_id == industry_etf:
                    logger.error(f"Industry ID {industry_id} matches ETF ticker {industry_etf} - using prefixed format to prevent this")
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
                # Create/update report node with conditional updates
                # This follows the same pattern as news deduplication
                result = session.run("""
                MERGE (r:Report {id: $id})
                ON CREATE SET 
                    r.id = $id,
                    r.formType = $formType,
                    r.description = $description,
                    r.cik = $cik,
                    r.companyName = $companyName,
                    r.periodEnd = $periodEnd,
                    r.filedAt = $filedAt,
                    r.updated = $updated,
                    r.isAmendment = $isAmendment,
                    r.primaryDocumentUrl = $primaryDocumentUrl,
                    r.linkToHtml = $linkToHtml,
                    r.linkToTxt = $linkToTxt,
                    r.linkToFilingDetails = $linkToFilingDetails,
                    r.exhibits = $exhibits,
                    r.entities = $entities, 
                    r.items = $items,
                    r.symbols = $symbols
                ON MATCH SET 
                    // Only update content-related fields if this is newer
                    r.description = CASE WHEN $updated > r.updated THEN $description ELSE r.description END,
                    r.formType = CASE WHEN $updated > r.updated THEN $formType ELSE r.formType END,
                    r.periodEnd = CASE WHEN $updated > r.updated THEN $periodEnd ELSE r.periodEnd END,
                    r.updated = CASE WHEN $updated > r.updated THEN $updated ELSE r.updated END,
                    // Always update these fields even if not newer (additive properties)
                    r.primaryDocumentUrl = $primaryDocumentUrl,
                    r.linkToHtml = $linkToHtml,
                    r.linkToTxt = $linkToTxt,
                    r.linkToFilingDetails = $linkToFilingDetails,
                    r.exhibits = $exhibits,
                    r.entities = $entities,
                    r.items = $items,
                    r.symbols = $symbols
                RETURN r
                """, {
                    "id": report_id,
                    "formType": form_type,
                    "description": description,
                    "cik": cik,
                    "companyName": company_name,
                    "periodEnd": period_end,
                    "filedAt": filed_str,
                    "updated": updated_str,
                    "isAmendment": is_amendment,
                    "primaryDocumentUrl": primary_document_url,
                    "linkToHtml": link_to_html,
                    "linkToTxt": link_to_txt,
                    "linkToFilingDetails": link_to_filing_details,
                    "exhibits": exhibits,
                    "entities": entities,
                    "items": items,
                    "symbols": symbols_json
                })
                
                # Process the result
                record = result.single()
                if not record:
                    logger.error(f"Failed to create or update report node {report_id}")
                    return False
                    
                # Skip processing if no symbols found
                if not valid_symbols:
                    logger.warning(f"No valid symbols found for report {report_id}")
                    return True
            
                # ----- Use UNWIND pattern for efficient batch processing of relationships -----
                
                # 1. Create Company INFLUENCES relationships using UNWIND pattern
                if company_params:
                    company_result = session.run("""
                    MATCH (r:Report {id: $report_id})
                    UNWIND $company_params AS param
                    MATCH (c:Company {cik: param.cik})
                    MERGE (r)-[rel:INFLUENCES]->(c)
                    SET rel += param.properties
                    RETURN count(rel) as relationship_count
                    """, {
                        "report_id": report_id,
                        "company_params": company_params
                    })
                    for record in company_result:
                        logger.info(f"Created {record['relationship_count']} INFLUENCES relationships to companies")
                
                # 2. Create Sector INFLUENCES relationships using UNWIND pattern
                if sector_params:
                    sector_result = session.run("""
                    MATCH (r:Report {id: $report_id})
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
                    MERGE (r)-[rel:INFLUENCES]->(s)
                    SET rel += param.properties
                    RETURN count(rel) as relationship_count
                    """, {
                        "report_id": report_id,
                        "sector_params": sector_params
                    })
                    for record in sector_result:
                        logger.info(f"Created {record['relationship_count']} INFLUENCES relationships to sectors")
                
                # 3. Create Industry INFLUENCES relationships using UNWIND pattern
                if industry_params:
                    industry_result = session.run("""
                    MATCH (r:Report {id: $report_id})
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
                    MERGE (r)-[rel:INFLUENCES]->(i)
                    SET rel += param.properties
                    RETURN count(rel) as relationship_count
                    """, {
                        "report_id": report_id,
                        "industry_params": industry_params
                    })
                    for record in industry_result:
                        logger.info(f"Created {record['relationship_count']} INFLUENCES relationships to industries")
                
                # 4. Create Market Index INFLUENCES relationships using UNWIND pattern
                if market_params:
                    market_result = session.run("""
                    MATCH (r:Report {id: $report_id})
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
                    WITH r, m
                    UNWIND $market_params AS param
                    MERGE (r)-[rel:INFLUENCES]->(m)
                    SET rel += param.properties
                    RETURN count(rel) as relationship_count
                    """, {
                        "report_id": report_id,
                        "market_params": market_params
                    })
                    for record in market_result:
                        logger.info(f"Created {record['relationship_count']} INFLUENCES relationships to market index")
                
                logger.info(f"Successfully processed report {report_id} with {len(valid_symbols)} symbols")
                return True
                
        except Exception as e:
            logger.error(f"Error processing report {report_id}: {e}")
            return False

    def process_reports_to_neo4j(self, batch_size=100, max_items=None, include_without_returns=True) -> bool:
        """
        Process SEC reports from Redis to Neo4j
        Similar to process_news_to_neo4j but for SEC reports
        
        Args:
            batch_size: Number of records to process at once
            max_items: Maximum number of items to process (None for all)
            include_without_returns: Whether to include reports without returns
            
        Returns:
            bool: True if processing is complete, False if it was interrupted
        """
        from utils.EventTraderNodes import ReportNode
        from utils.redis_constants import RedisKeys
        
        # Get Redis instance if available
        if not self.event_trader_redis:
            logger.error("No Redis instance available, cannot process reports")
            return False
            
        # Process reports with returns
        withreturns_keys = []
        try:
            # Get report keys with returns
            withreturns_namespace = RedisKeys.get_key(
                source_type=RedisKeys.SOURCE_REPORTS, 
                key_type=RedisKeys.SUFFIX_WITHRETURNS
            )
            withreturns_pattern = f"{withreturns_namespace}*"
            withreturns_keys = list(self.event_trader_redis.history_client.client.scan_iter(match=withreturns_pattern))
            
            if max_items is not None:
                withreturns_keys = withreturns_keys[:max_items]
                
            logger.info(f"Found {len(withreturns_keys)} reports with returns")
        except Exception as e:
            logger.error(f"Error getting withreturns keys: {e}")
            
        # Process reports without returns if requested
        withoutreturns_keys = []
        if include_without_returns:
            try:
                # Get report keys without returns
                withoutreturns_namespace = RedisKeys.get_key(
                    source_type=RedisKeys.SOURCE_REPORTS, 
                    key_type=RedisKeys.SUFFIX_WITHOUTRETURNS
                )
                withoutreturns_pattern = f"{withoutreturns_namespace}*"
                withoutreturns_keys = list(self.event_trader_redis.history_client.client.scan_iter(match=withoutreturns_pattern))
                
                if max_items is not None:
                    withoutreturns_keys = withoutreturns_keys[:max_items]
                    
                logger.info(f"Found {len(withoutreturns_keys)} reports without returns")
            except Exception as e:
                logger.error(f"Error getting withoutreturns keys: {e}")
                
        # Combine both key sets
        all_keys = withreturns_keys + withoutreturns_keys
        if not all_keys:
            logger.info("No report keys found to process")
            return True
            
        total_reports = len(all_keys)
        logger.info(f"Processing {total_reports} total reports")
        
        # Process in batches
        processed_count = 0
        error_count = 0
        
        for batch_start in range(0, len(all_keys), batch_size):
            batch_keys = all_keys[batch_start:batch_start + batch_size]
            batch_size_actual = len(batch_keys)
            
            logger.info(f"Processing batch {batch_start//batch_size + 1}, items {batch_start+1}-{batch_start+batch_size_actual} of {total_reports}")
            
            # Process each report in the batch
            for key in batch_keys:
                try:
                    # Extract key parts
                    parts = key.split(':')
                    report_id = parts[-1] if len(parts) > 0 else key
                    
                    # Get report data from Redis
                    raw_data = self.event_trader_redis.history_client.get(key)
                    if not raw_data:
                        logger.warning(f"No data found for key {key}")
                        continue
                        
                    # Parse JSON data
                    report_data = json.loads(raw_data)
                    
                    # Use accessionNo as report ID if available
                    if 'accessionNo' in report_data:
                        report_id = report_data['accessionNo']
                    
                    # Process report data with deduplication
                    success = self._process_deduplicated_report(report_id, report_data)
                    
                    if success:
                        processed_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing report key {key}: {e}")
                    error_count += 1
            
            logger.info(f"Processed batch {batch_start//batch_size + 1}/{(len(all_keys) + batch_size - 1)//batch_size}")
            
        # Summary and status
        logger.info(f"Finished processing reports to Neo4j. Processed: {processed_count}, Errors: {error_count}")
        
        return processed_count > 0 or error_count == 0

    def _process_pubsub_item(self, channel, item_id, content_type='news'):
        """
        Process an item update from PubSub (works for both news and reports)
        
        Args:
            channel: The Redis channel the message came from
            item_id: The ID of the item to process
            content_type: 'news' or 'report'
        """
        try:
            logger.info(f"Processing {content_type} update from {channel}: {item_id}")
            
            # Determine namespace from channel
            namespace = RedisKeys.SUFFIX_WITHRETURNS if RedisKeys.SUFFIX_WITHRETURNS in channel else RedisKeys.SUFFIX_WITHOUTRETURNS
            
            # Process based on content type
            if content_type == 'news':
                # Get the news data using standard key format
                key = RedisKeys.get_key(
                    source_type=self.event_trader_redis.source,
                    key_type=namespace,
                    identifier=item_id
                )
                
                # Get and process the news item
                raw_data = self.event_trader_redis.history_client.client.get(key)
                if raw_data:
                    news_data = json.loads(raw_data)
                    success = self._process_deduplicated_news(
                        news_id=f"bzNews_{item_id.split('.')[0]}", 
                        news_data=news_data
                    )
                    logger.info(f"Successfully processed news {item_id}")
                else:
                    logger.warning(f"No data found for news {item_id}")
            else:  # report
                # Get the report data using standard key format
                key = RedisKeys.get_key(
                    source_type=RedisKeys.SOURCE_REPORTS,
                    key_type=namespace,
                    identifier=item_id
                )
                
                # Get and process the report
                raw_data = self.event_trader_redis.history_client.client.get(key)
                if raw_data:
                    report_data = json.loads(raw_data)
                    
                    # Use accessionNo as report ID if available
                    report_id = report_data.get('accessionNo', item_id)
                    
                    # Process report with deduplication (same approach as news)
                    success = self._process_deduplicated_report(
                        report_id=report_id,
                        report_data=report_data
                    )
                    
                    logger.info(f"Successfully processed report {item_id}")
                else:
                    logger.warning(f"No data found for report {item_id}")
                
        except Exception as e:
            logger.error(f"Error processing {content_type} update for {item_id}: {e}")



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


    # ToDo: is designed to run indefinitely, so it will block the main thread. You need to handle this appropriately.
    def process_with_pubsub(self):
        """
        Process news and reports from Redis to Neo4j using PubSub for immediate notification.
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
        
        # Subscribe to news channels using consistent RedisKeys methods
        news_returns_keys = RedisKeys.get_returns_keys(self.event_trader_redis.source)
        withreturns_channel = news_returns_keys['withreturns']
        withoutreturns_channel = news_returns_keys['withoutreturns']
        pubsub.subscribe(withreturns_channel, withoutreturns_channel)
        logger.info(f"Subscribed to news channels: {withreturns_channel}, {withoutreturns_channel}")
        
        # Subscribe to report channels using the same RedisKeys methods
        report_returns_keys = RedisKeys.get_returns_keys(RedisKeys.SOURCE_REPORTS)
        report_withreturns_channel = report_returns_keys['withreturns']
        report_withoutreturns_channel = report_returns_keys['withoutreturns']
        pubsub.subscribe(report_withreturns_channel, report_withoutreturns_channel)
        logger.info(f"Subscribed to report channels: {report_withreturns_channel}, {report_withoutreturns_channel}")
        
        # Control flag
        self.pubsub_running = True
        
        # Process any existing items first (one-time batch processing)
        self.process_news_to_neo4j(batch_size=50, max_items=None, include_without_returns=True)
        self.process_reports_to_neo4j(batch_size=50, max_items=None, include_without_returns=True)
        
        # Event-driven processing loop
        while self.pubsub_running:
            try:
                # Non-blocking message check with 0.1s timeout
                message = pubsub.get_message(timeout=0.1)
                
                if message and message['type'] == 'message':
                    channel = message['channel']
                    item_id = message.get('data')
                    
                    if not item_id:
                        continue
                    
                    # Determine content type based on channel prefix
                    if channel.startswith(self.event_trader_redis.source):
                        # Process news
                        self._process_pubsub_item(channel, item_id, 'news')
                    elif channel.startswith(RedisKeys.SOURCE_REPORTS):
                        # Process report
                        self._process_pubsub_item(channel, item_id, 'report')
                
                # Periodically check for items that might have been missed (every 60 seconds)
                # This is a safety net, not the primary mechanism
                current_time = int(time.time())
                if current_time % 60 == 0:
                    self.process_news_to_neo4j(batch_size=10, max_items=10, include_without_returns=False)
                    self.process_reports_to_neo4j(batch_size=10, max_items=10, include_without_returns=False)
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
    
    def _process_report_companies(self, report_json: Dict[str, Any], company_nodes: Dict[str, 'CompanyNode']):
        """
        Extract and create company nodes from report data
        
        Args:
            report_json: The report JSON data
            company_nodes: Dictionary to store company nodes (cik -> node)
        """
        from utils.EventTraderNodes import CompanyNode
        
        # Get universe data for mapping
        universe_data = self._get_universe()
        ticker_to_cik = {}
        for symbol, data in universe_data.items():
            cik = data.get('cik', '').strip()
            if cik and cik.lower() not in ['nan', 'none', '']:
                ticker_to_cik[symbol.upper()] = str(cik).zfill(10)
        
        # Extract symbols from metadata - use the same approach as news processing
        symbols = []
        if 'metadata' in report_json and 'instruments' in report_json['metadata']:
            for instrument in report_json['metadata']['instruments']:
                symbol = instrument.get('symbol', '')
                if symbol:
                    symbols.append(symbol.upper())
        
        # If no symbols in metadata but we have a company symbol, try to use it
        if not symbols and 'symbols' in report_json and report_json['symbols']:
            symbols.extend([s.upper() for s in report_json['symbols']])
            
        # Create company nodes for all symbols
        for symbol in symbols:
            symbol_upper = symbol.upper()
            cik = ticker_to_cik.get(symbol_upper)
            if not cik:
                logger.warning(f"No CIK found for symbol {symbol_upper}")
                continue
                
            # Skip if we already processed this company
            if cik in company_nodes:
                continue
                
            # Get company data
            company_data = universe_data.get(symbol_upper, {})
            name = company_data.get('company_name', company_data.get('name', symbol_upper))
                
            # Create company node
            company = CompanyNode(
                cik=cik,
                name=name,
                ticker=symbol_upper
            )
                
            # Add additional fields if available
            for field in ['exchange', 'sector', 'industry', 'sic', 'sic_name']:
                if field in company_data:
                    setattr(company, field, company_data[field])
                
            company_nodes[cik] = company
        


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

# Function to process report data into Neo4j
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
        from utils.redisClasses import EventTraderRedis
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


if __name__ == "__main__":
    import sys
    import argparse
    
    # Set up command line arguments
    parser = argparse.ArgumentParser(description="Neo4j processor for EventTrader")
    parser.add_argument("mode", choices=["init", "news", "reports", "all"], default="init", nargs="?",
                        help="Mode: 'init' (initialize Neo4j), 'news' (process news), 'reports' (process reports), 'all' (all of the above)")
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
        logger.info("Running Neo4j initialization...")
        init_neo4j()
    
    elif args.mode == "news":
        # Process news data
        logger.info(f"Processing news data with batch_size={batch_size}, max_items={max_items}, include_without_returns={include_without_returns}")
        process_news_data(batch_size, max_items, args.verbose, include_without_returns)
    
    elif args.mode == "reports":
        # Process report data
        logger.info(f"Processing report data with batch_size={batch_size}, max_items={max_items}, include_without_returns={include_without_returns}")
        process_report_data(batch_size, max_items, args.verbose, include_without_returns)
    
    elif args.mode == "all":
        # Run initialization and all processing modes
        logger.info(f"Running complete Neo4j setup (batch_size={batch_size}, max_items={max_items}, include_without_returns={include_without_returns})...")
        
        # Initialize Neo4j first
        if init_neo4j():
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
                
            logger.info("All processing completed.")
        else:
            logger.error("Initialization failed, skipping data processing")
    
    else:
        logger.error(f"Unknown mode: {args.mode}. Use 'init', 'news', 'reports', or 'all'")
        print("Usage: python Neo4jProcessor.py [mode] [options]")
        print("  mode: 'init' (default), 'news', 'reports', or 'all'")
        print("  --batch N: Number of items to process in each batch (default: 10)")
        print("  --max N: Maximum number of items to process (0 for all, default: 0)")
        print("  --verbose/-v: Enable verbose logging")
        print("  --skip-without-returns: Skip processing items without returns")
        print("  --skip-news: Skip processing news in 'all' mode")
        print("  --skip-reports: Skip processing reports in 'all' mode") 