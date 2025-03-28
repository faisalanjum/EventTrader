# Standard Library Imports
import os
import random
import sys
import json
import threading
import time
import logging
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
import concurrent.futures

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
    IndustryNode, MarketIndexNode, ReportNode,
    ExtractedSectionContent, ExhibitContent, FinancialStatementContent, FilingTextContent
)

# Internal Imports - Date Utilities
from utils.date_utils import parse_news_dates, parse_date  

# Internal Imports - Metadata Fields
from utils.metadata_fields import MetadataFields

# Internal Imports - XBRL Processing
from XBRL.Neo4jManager import Neo4jManager
from XBRL.xbrl_core import NodeType, RelationType

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
    
    # Complete list of node types initialized in Neo4jInitializer
    REQUIRED_NODES = [
        "Company", 
        "MarketIndex", 
        "Sector", 
        "Industry", 
        "AdminReport", 
        # "AdminSection", 
        # "FinancialStatement"
    ]
    # Add more node types here as needed


# region: Initialization and Core Infrastructure - # Methods like connect, close, is_initialized, initialize, _get_universe, _collect_redis_key_counts



    def __init__(self, event_trader_redis=None, uri=NEO4J_URI, username=NEO4J_USERNAME, password=NEO4J_PASSWORD):

        # Override with environment variables if available - Save it in .env file
        self.uri = uri
        self.username = username
        self.password = password
        self.manager = None  # Will be initialized when needed
        self.universe_data = None
        
        # Flag to track if we've processed an XBRL report
        self.xbrl_processed = False
        
        
        # Add semaphore to limit concurrent XBRL operations
        self.xbrl_semaphore = threading.BoundedSemaphore(4)
        
        # Existing thread pool executor code remains unchanged
        self.xbrl_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=8,  
            thread_name_prefix="xbrl_worker"
        )
        
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
        """Connect to Neo4j using Neo4jManager singleton"""
        try:
            # Import here to avoid circular imports
            from XBRL.Neo4jConnection import get_manager
            
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
            
        # Shutdown the thread pool executor if it exists
        if hasattr(self, 'xbrl_executor'):
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
    

# endregion


# region: Primary Public Methods - # Methods like process_news_to_neo4j, process_reports_to_neo4j, process_pubsub_item, process_with_pubsub, stop_pubsub_processing

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
                raw_data = self.event_trader_redis.history_client.get(key)
                if raw_data:
                    news_data = json.loads(raw_data)
                    success = self._process_deduplicated_news(
                        news_id=f"bzNews_{item_id.split('.')[0]}", 
                        news_data=news_data
                    )
                    logger.info(f"Successfully processed news {item_id}")

                    # Delete key if it's from withreturns namespace
                    if success and namespace == RedisKeys.SUFFIX_WITHRETURNS:
                        try:
                            self.event_trader_redis.history_client.client.delete(key)
                            logger.info(f"Deleted processed withreturns key: {key}")
                        except Exception as e:
                            logger.warning(f"Error deleting key {key}: {e}")

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
                raw_data = self.event_trader_redis.history_client.get(key)
                if raw_data:
                    report_data = json.loads(raw_data)
                    
                    # Use accessionNo as report ID if available
                    report_id = report_data.get('accessionNo', item_id)
                    
                    # Process report with deduplication (same approach as news)
                    success = self._process_deduplicated_report(
                        report_id=report_id,
                        report_data=report_data
                    )
                    
                    # Note: No need to process extracted sections here as it's already handled in _execute_report_database_operations
                    
                    logger.info(f"Successfully processed report {item_id}")

                    # Delete key if it's from withreturns namespace
                    if success and namespace == RedisKeys.SUFFIX_WITHRETURNS:
                        try:
                            self.event_trader_redis.history_client.client.delete(key)
                            logger.info(f"Deleted processed withreturns key: {key}")
                        except Exception as e:
                            logger.warning(f"Error deleting key {key}: {e}")


                else:
                    logger.warning(f"No data found for report {item_id}")
                
        except Exception as e:
            logger.error(f"Error processing {content_type} update for {item_id}: {e}")




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


        # [NEW CODE]: Track reconciliation time
        last_reconciliation = 0
        reconciliation_interval = 3600  # Run once per hour

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
                # current_time = int(time.time())
                # if current_time % 60 == 0:
                #     self.process_news_to_neo4j(batch_size=10, max_items=10, include_without_returns=False)
                #     self.process_reports_to_neo4j(batch_size=10, max_items=10, include_without_returns=False)
                #     time.sleep(1)  # Prevent repeated execution in the same second

                # [NEW CODE]: Hourly reconciliation
                current_time = int(time.time())
                if current_time - last_reconciliation >= reconciliation_interval:
                    logger.info("Starting hourly reconciliation...")
                    self.reconcile_missing_items()
                    last_reconciliation = current_time


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
        """
        Stop the PubSub processing loop gracefully.
        Called by DataManagerCentral during shutdown.
        """
        logger.info("Stopping PubSub processing...")
        self.pubsub_running = False
        # Give time for the thread to exit gracefully
        time.sleep(0.5)
        logger.info("PubSub processing flag set to stop")
        return True


# endregion
    

# region: News Processing Pipeline - # Methods like _prepare_news_data, _process_deduplicated_news, _execute_news_database_operations, _create_news_node_from_data

    def _prepare_news_data(self, news_id, news_data):
        """
        Prepare news data for processing, extracting all necessary information.
        
        Args:
            news_id: Unique identifier for the news
            news_data: Dictionary containing news data
            
        Returns:
            tuple: (news_node, valid_symbols, company_params, sector_params, industry_params, market_params, timestamps)
                where timestamps is a tuple of (created_at, updated_at, timestamp)
        """
        # Get ticker to CIK mappings from universe data
        universe_data = self._get_universe()
        ticker_to_cik = {}
        for symbol, data in universe_data.items():
            cik = data.get('cik', '').strip()
            if cik and cik.lower() not in ['nan', 'none', '']:
                ticker_to_cik[symbol.upper()] = str(cik).zfill(10)
        
        # Create NewsNode from news data
        news_node = self._create_news_node_from_data(news_id, news_data)
        
        # Extract symbols mentioned in news using the unified method
        symbols = self._extract_symbols_from_data(news_data)
        
        # Extract timestamps with proper parsing
        created_at, updated_at = parse_news_dates(news_data)
        timestamp = created_at.isoformat() if created_at else ""
        
        # Use the common method to prepare relationship parameters
        valid_symbols, company_params, sector_params, industry_params, market_params = self._prepare_entity_relationship_params(
            data_item=news_data,
            symbols=symbols,
            universe_data=universe_data,
            ticker_to_cik=ticker_to_cik,
            timestamp=timestamp
        )
        
        # Return all prepared data
        timestamps = (created_at, updated_at, timestamp)
        return (news_node, valid_symbols, company_params, sector_params, industry_params, market_params, timestamps)


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
            # Prepare all news data
            news_node, valid_symbols, company_params, sector_params, industry_params, market_params, timestamps = self._prepare_news_data(news_id, news_data)
            
            # Execute all database operations
            return self._execute_news_database_operations(
                news_id, news_node, valid_symbols, company_params, 
                sector_params, industry_params, market_params, timestamps
            )
                
        except Exception as e:
            logger.error(f"Error processing news {news_id}: {e}")
            return False
        


    def _execute_news_database_operations(self, news_id, news_node, valid_symbols, company_params, sector_params, industry_params, market_params, timestamps):
        """
        Execute all database operations for a news item.
        
        Args:
            news_id: Unique identifier for the news
            news_node: NewsNode object
            valid_symbols: List of valid symbols
            company_params: Parameters for company relationships
            sector_params: Parameters for sector relationships
            industry_params: Parameters for industry relationships
            market_params: Parameters for market index relationships
            timestamps: Tuple of (created_at, updated_at, timestamp)
            
        Returns:
            bool: Success status
        """
        created_at, updated_at, timestamp = timestamps
        
        # Execute deduplication and conditional update logic with direct Cypher
        # KEEP ALL DATABASE OPERATIONS INSIDE THIS SINGLE SESSION CONTEXT
        with self.manager.driver.session() as session:
            # Create/update news node with conditional updates
            # This follows the pattern from the deduplication notes
            news_merge_query = """
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
            """
            
            # Prepare parameters
            query_params = {
                "id": news_id,
                "title": news_node.title or "",
                "body": news_node.body or "",
                "teaser": news_node.teaser or "",
                "created": news_node.created.isoformat() if news_node.created else "",
                "updated": news_node.updated.isoformat() if news_node.updated else (news_node.created.isoformat() if news_node.created else ""),
                "url": news_node.url or "",
                "authors": json.dumps(news_node.authors or []),
                "tags": json.dumps(news_node.tags or []),
                "channels": json.dumps(news_node.channels or []),
                "market_session": news_node.market_session or "",
                "returns_schedule": json.dumps(news_node.returns_schedule or {})
            }
            
            # Execute the query using Neo4jManager
            record = self.manager.execute_cypher_query(news_merge_query, query_params)
            
            # Process the result
            if not record:
                logger.error(f"Failed to create or update news node {news_id}")
                return False
                
            # Skip processing if no symbols found
            if not valid_symbols:
                logger.warning(f"No valid symbols found for news {news_id}")
                return True
        
            # ----- Use UNWIND pattern for efficient batch processing of relationships -----

            # 1. Create Company, Sector, Industry, MarketIndex INFLUENCES relationships
            self._create_influences_relationships(session, news_id, "News", "Company", company_params)
            self._create_influences_relationships(session, news_id, "News", "Sector", sector_params)
            self._create_influences_relationships(session, news_id, "News", "Industry", industry_params)
            self._create_influences_relationships(session, news_id, "News", "MarketIndex", market_params)
            logger.info(f"Successfully processed news {news_id} with {len(valid_symbols)} symbols")
            return True



    def _create_news_node_from_data(self, news_id, news_data):
        """
        Create a NewsNode instance from raw news data.
        
        Args:
            news_id (str): Unique identifier for the news
            news_data (dict): Dictionary containing news data from Redis or API
        
        Returns:
            NewsNode: An instance of NewsNode with all available fields populated
        
        Note:
            This method handles data parsing, validation, and standardization
            to ensure the NewsNode has consistent field values.
        """
        from utils.EventTraderNodes import NewsNode
        
        # Extract timestamps with proper parsing
        created_at, updated_at = parse_news_dates(news_data)
        
        # Create news node with required fields
        news_node = NewsNode(
            news_id=news_id,
            title=news_data.get('title', ''),
            # body=news_data.get('body', news_data.get('content', '')),  # Fallback to content if body not available
            body=news_data.get('body', ''),
            teaser=news_data.get('teaser', ''),
            url=news_data.get('url', '')
        )
        
        # Set datetime fields
        if created_at:
            news_node.created = created_at
        # Removed fallback to current datetime
            
        if updated_at:
            news_node.updated = updated_at
        elif created_at:
            news_node.updated = created_at  # Use created_at as fallback for updated_at
        # Removed fallback to current datetime
        
        # Set list fields
        news_node.authors = self._parse_list_field(news_data.get('authors', []))
        news_node.tags = self._parse_list_field(news_data.get('tags', []))
        news_node.channels = self._parse_list_field(news_data.get('channels', []))
        
        # Extract market session and returns schedule using helper methods
        news_node.market_session = self._extract_market_session(news_data)
        news_node.returns_schedule = self._extract_returns_schedule(news_data)
        
        return news_node


# endregion


# region: Report Processing Pipeline - # Methods _prepare_report_data, _process_deduplicated_report, _execute_report_database_operations, _create_report_node_from_data, _process_report_companies

    def _prepare_report_data(self, report_id, report_data):
        """
        Prepare report data for processing, extracting all necessary information.
        
        Args:
            report_id: Unique identifier for the report (accessionNo)
            report_data: Dictionary containing report data
            
        Returns:
            tuple: (report_node, node_properties, valid_symbols, company_params, sector_params, 
                   industry_params, market_params, report_timestamps)
                where report_timestamps is a tuple of (filed_at, updated_at, filed_str, updated_str)
        """
        # Get universe data for ticker-to-CIK mappings
        universe_data = self._get_universe()
        ticker_to_cik = {}
        for symbol, data in universe_data.items():
            cik = data.get('cik', '').strip()
            if cik and cik.lower() not in ['nan', 'none', '']:
                ticker_to_cik[symbol.upper()] = str(cik).zfill(10)
        
        # 1. Create ReportNode from report data
        report_node = self._create_report_node_from_data(report_id, report_data)
        
        # 2. Extract and process symbols using the unified method
        symbols = self._extract_symbols_from_data(report_data)
        symbols_json = json.dumps(symbols)
        
        # Get timestamps for parameters and conditional updates
        filed_at = parse_date(report_data.get('filedAt')) if report_data.get('filedAt') else None
        updated_at = parse_date(report_data.get('updated')) if report_data.get('updated') else None
        
        filed_str = filed_at.isoformat() if filed_at else ""
        updated_str = updated_at.isoformat() if updated_at else filed_str
        
        # 3. Use the common method to prepare relationship parameters
        valid_symbols, company_params, sector_params, industry_params, market_params = self._prepare_entity_relationship_params(
            data_item=report_data,
            symbols=symbols,
            universe_data=universe_data,
            ticker_to_cik=ticker_to_cik,
            timestamp=filed_str
        )
        
        # 4. Get node properties from ReportNode
        node_properties = report_node.properties
        
        # Return all prepared data
        report_timestamps = (filed_at, updated_at, filed_str, updated_str)
        return (report_node, node_properties, valid_symbols, company_params, 
                sector_params, industry_params, market_params, report_timestamps)




    def _process_deduplicated_report(self, report_id, report_data):
        """
        Process report data with deduplication, standardized fields, and efficient symbol relationships.
        Uses a hash-based MERGE pattern with conditional updates based on timestamps.
        
        Args:
            report_id: Unique identifier for the report (accessionNo)
            report_data: Dictionary containing report data
            
        Returns:
            bool: Success status
        """
        logger.debug(f"Processing deduplicated report {report_id}")
        
        try:
            # Prepare all report data
            report_node, node_properties, valid_symbols, company_params, sector_params, industry_params, market_params, report_timestamps = self._prepare_report_data(report_id, report_data)
            
            # Execute all database operations
            return self._execute_report_database_operations(
                report_id, report_node, node_properties, valid_symbols,
                company_params, sector_params, industry_params, market_params,
                report_timestamps
            )
                
        except Exception as e:
            logger.error(f"Error processing report {report_id}: {e}")
            return False




    def _execute_report_database_operations(self, report_id, report_node, node_properties, valid_symbols, 
                                           company_params, sector_params, industry_params, market_params, 
                                           report_timestamps):
        """
        Execute all database operations for a report.
        
        Args:
            report_id: Unique identifier for the report
            report_node: ReportNode object
            node_properties: Dictionary of node properties
            valid_symbols: List of valid symbols
            company_params: Parameters for company relationships
            sector_params: Parameters for sector relationships
            industry_params: Parameters for industry relationships
            market_params: Parameters for market index relationships
            report_timestamps: Tuple of (filed_at, updated_at, filed_str, updated_str)
            
        Returns:
            bool: Success status
        """
        filed_at, updated_at, filed_str, updated_str = report_timestamps
        
        # Build Cypher query for fields
        on_create_parts = []
        
        # Add all properties from node_properties
        for key, value in node_properties.items():
            on_create_parts.append(f"r.{key} = ${key}")
        
        # Build ON MATCH SET parts with conditional updates for content fields
        on_match_parts = [
            "r.description = CASE WHEN $updated > r.updated THEN $description ELSE r.description END",
            "r.formType = CASE WHEN $updated > r.updated THEN $formType ELSE r.formType END",
            "r.periodOfReport = CASE WHEN $updated > r.updated THEN $periodOfReport ELSE r.periodOfReport END",
            "r.effectivenessDate = CASE WHEN $updated > r.updated THEN $effectivenessDate ELSE r.effectivenessDate END",
            "r.updated = CASE WHEN $updated > r.updated THEN $updated ELSE r.updated END",
            "r.primaryDocumentUrl = $primaryDocumentUrl",
            "r.linkToHtml = $linkToHtml",
            "r.linkToTxt = $linkToTxt",
            "r.linkToFilingDetails = $linkToFilingDetails",
            "r.exhibits = $exhibits",
            "r.entities = $entities",
            "r.items = $items",
            "r.symbols = $symbols",
            "r.is_xml = $is_xml",
            "r.isAmendment = $isAmendment",
            "r.accessionNo = $id",
            "r.id = $id",
            "r.market_session = $market_session",
            "r.returns_schedule = $returns_schedule",
            "r.extracted_sections = CASE WHEN $updated > r.updated THEN $extracted_sections ELSE r.extracted_sections END",
            "r.financial_statements = CASE WHEN $updated > r.updated THEN $financial_statements ELSE r.financial_statements END",
            "r.exhibit_contents = CASE WHEN $updated > r.updated THEN $exhibit_contents ELSE r.exhibit_contents END",
            "r.filing_text_content = CASE WHEN $updated > r.updated THEN $filing_text_content ELSE r.filing_text_content END",
            "r.xbrl_status = CASE WHEN $updated > r.updated THEN $xbrl_status ELSE r.xbrl_status END",
            "r.created = $created"
        ]
        
        # Create parameter dictionary from node_properties
        query_params = {
            "updated": updated_str,  # For conditional updates
        }
        
        # Add all node properties to query params
        for key, value in node_properties.items():
            query_params[key] = value
        
        # Ensure all referenced parameters exist (even if they weren't in node_properties)
        required_params = ["effectivenessDate", "financial_statements", "exhibit_contents", 
                         "extracted_sections", "market_session", "returns_schedule", "filing_text_content", "items"]
        
        for param in required_params:
            if param not in query_params:
                if param in ["financial_statements", "exhibit_contents", "extracted_sections", "returns_schedule"]:
                    # These need to be JSON strings
                    query_params[param] = json.dumps({})
                elif param == "filing_text_content":
                    # This is a text field that can be null
                    query_params[param] = None
                elif param == "items":
                    # Default items to empty array as JSON string
                    query_params[param] = json.dumps([])
                else:
                    # Default to empty string for other fields
                    query_params[param] = ""
        
        # Construct the complete Cypher query
        report_merge_query = f"""
        MERGE (r:Report {{accessionNo: $id}})
        ON CREATE SET {', '.join(on_create_parts)}
        ON MATCH SET {', '.join(on_match_parts)}
        RETURN r
        """
        
        with self.manager.driver.session() as session:
            # Execute the query using Neo4jManager
            record = self.manager.execute_cypher_query(report_merge_query, query_params)
            
            # Process the result
            if not record:
                logger.error(f"Failed to create or update report node {report_id}")
                return False
            
            # Get the created/updated report
            report_props = dict(record["r"].items())
            
            # Process extracted sections if present
            if report_node.extracted_sections:
                section_data = {
                    'extracted_sections': report_node.extracted_sections,
                    'formType': report_node.formType,
                    'cik': report_node.cik,
                    'created': report_node.created
                }
                self._create_section_nodes_from_report(report_id, section_data)
            
            # Process exhibit contents if present
            if report_node.exhibit_contents:
                exhibit_data = {
                    'exhibit_contents': report_node.exhibit_contents,
                    'formType': report_node.formType,
                    'cik': report_node.cik,
                    'created': report_node.created
                }
                self._create_exhibit_nodes_from_report(report_id, exhibit_data)
            
            # Process financial statements if present
            if report_node.financial_statements:
                financial_data = {
                    'financial_statements': report_node.financial_statements,
                    'formType': report_node.formType,
                    'cik': report_node.cik,
                    'created': report_node.created
                }
                self._create_financial_statement_nodes_from_report(report_id, financial_data)
            
            # Process filing text content if present
            if report_node.filing_text_content:
                filing_text_data = {
                    'filing_text_content': report_node.filing_text_content,
                    'formType': report_node.formType,
                    'cik': report_node.cik,
                    'created': report_node.created
                }
                self._create_filing_text_content_nodes_from_report(report_id, filing_text_data)
            
            # Check if this report is eligible for XBRL processing and we haven't processed one yet
            if (not self.xbrl_processed and
                report_props.get('is_xml') == True and
                report_props.get('cik') and
                report_props.get('xbrl_status') != 'COMPLETED' and
                report_props.get('xbrl_status') != 'PROCESSING'):
                
                # Process XBRL data
                self._process_xbrl(
                    session=session,
                    report_id=report_props["id"],
                    cik=report_props["cik"],
                    accessionNo=report_props["accessionNo"]
                )
            
            # Skip processing if no symbols found
            if not valid_symbols:
                logger.warning(f"No valid symbols found for report {report_id}")
                return True
        
            # ----- Use helper method for efficient batch processing of relationships -----
            
            # Split company parameters into primary filer and referenced companies
            primary_filer_params = []
            referenced_in_params = []
            report_cik = report_props.get("cik")
            
            for param in company_params:
                if report_cik and param['cik'] == report_cik:
                    primary_filer_params.append(param)
                else:
                    referenced_in_params.append(param)
            
            # Deduplicate both lists by CIK to prevent any possibility of duplicate relationships
            primary_filer_params = list({param['cik']: param for param in primary_filer_params}.values())
            referenced_in_params = list({param['cik']: param for param in referenced_in_params}.values())
            
            # Create PRIMARY_FILER relationships directly using Neo4jManager
            if primary_filer_params:
                self.manager.create_relationships(
                    source_label="Report", 
                    source_id_field="id", 
                    source_id_value=report_id,
                    target_label="Company", 
                    target_match_clause="{cik: param.cik}", 
                    rel_type=RelationType.PRIMARY_FILER.value, 
                    params=primary_filer_params
                )
                logger.info(f"Created {len(primary_filer_params)} PRIMARY_FILER relationships to companies")
            
            # Create REFERENCED_IN relationships directly using Neo4jManager
            if referenced_in_params:
                self.manager.create_relationships(
                    source_label="Report", 
                    source_id_field="id", 
                    source_id_value=report_id,
                    target_label="Company", 
                    target_match_clause="{cik: param.cik}", 
                    rel_type=RelationType.REFERENCED_IN.value, 
                    params=referenced_in_params
                )
                logger.info(f"Created {len(referenced_in_params)} REFERENCED_IN relationships to companies")
            
            # Create other INFLUENCES relationships as before
            self._create_influences_relationships(session, report_id, "Report", "Sector", sector_params)
            self._create_influences_relationships(session, report_id, "Report", "Industry", industry_params)
            self._create_influences_relationships(session, report_id, "Report", "MarketIndex", market_params)
            
            # 5. Create Report Category relationships
            # Extract form type from report_node instead of report_data
            form_type = report_node.formType.split('/')[0] if report_node.formType else ""  # Extract base form type without amendments
            if form_type:
                # Here we are linking to ADMIN Nodes
                self.manager.create_report_category_relationship(report_id, form_type)
            
            return True


    def _create_report_node_from_data(self, report_id, report_data):
        """Create a ReportNode instance from report data"""
        from utils.EventTraderNodes import ReportNode
        
        # Process required fields
        cik = report_data.get('cik', '')
        if cik:
            cik = str(cik).zfill(10)
            
        primary_document_url = report_data.get('primaryDocumentUrl', '')
        
        # Create report node with required fields
        report_node = ReportNode(
            accessionNo=report_id,
            primaryDocumentUrl=primary_document_url,
            cik=cik
        )
        
        # Extract timestamps with proper parsing
        filed_at = parse_date(report_data.get('filedAt')) if report_data.get('filedAt') else None
        updated_at = parse_date(report_data.get('updated')) if report_data.get('updated') else None
        
        # Process basic fields
        form_type = report_data.get('formType', '')
        
        # Derive isAmendment from formType if not explicitly set
        is_amendment = report_data.get('isAmendment', False)
        if not is_amendment and form_type and '/A' in form_type:
            is_amendment = True
            
        # Set basic fields
        report_node.formType = form_type
        report_node.created = report_data.get('created', '')
        report_node.is_xml = bool(report_data.get('is_xml', False))
        report_node.isAmendment = is_amendment
        report_node.description = report_data.get('description', '')
        report_node.periodOfReport = report_data.get('periodOfReport', '')
        report_node.effectivenessDate = report_data.get('effectivenessDate', '')
        report_node.linkToHtml = report_data.get('linkToHtml', '')
        report_node.linkToTxt = report_data.get('linkToTxt', '')
        report_node.linkToFilingDetails = report_data.get('linkToFilingDetails', '')
        
        # Set complex fields - these will be serialized by ReportNode properties method
        report_node.exhibits = report_data.get('exhibits', {})
        report_node.entities = report_data.get('entities', [])
        report_node.items = report_data.get('items', [])
        report_node.symbols = report_data.get('symbols', [])
        report_node.extracted_sections = report_data.get('extracted_sections', {})
        report_node.financial_statements = report_data.get('financial_statements', {})
        report_node.exhibit_contents = report_data.get('exhibit_contents', {})
        report_node.filing_text_content = report_data.get('filing_text_content', None)
        
        # Set xbrl_status flag
        report_node.xbrl_status = report_data.get('xbrl_status', None)
        
        # Extract market session and returns schedule using helper methods
        report_node.market_session = self._extract_market_session(report_data)
        report_node.returns_schedule = self._extract_returns_schedule(report_data)
            
        return report_node


    def _create_section_nodes_from_report(self, report_id, report_data):
        """
        Create section nodes from report extracted_sections and link them to the report
        
        Args:
            report_id: Report accession number
            report_data: Report data with extracted_sections, formType, cik, and created
        
        Returns:
            List of created section nodes
        """
        from utils.EventTraderNodes import ExtractedSectionContent, ReportNode
        from XBRL.xbrl_core import RelationType
        
        # Skip if no extracted sections
        extracted_sections = report_data.get('extracted_sections')
        if not extracted_sections:
            return []
        
        try:
            # Get report information needed for section nodes
            form_type = report_data.get('formType', '')
            cik = report_data.get('cik', '')
            filed_at = report_data.get('created', '')
            
            # Create section nodes
            section_nodes = []
            
            for section_name, content in extracted_sections.items():
                # Skip sections with null content
                if content is None:
                    logger.warning(f"Skipping section {section_name} with null content for report {report_id}")
                    continue
                
                # Create unique ID from report ID and section name
                content_id = f"{report_id}_{section_name}"
                
                # Create section content node
                section_node = ExtractedSectionContent(
                    content_id=content_id,
                    filing_id=report_id,
                    form_type=form_type,
                    section_name=section_name,
                    content=content,
                    filer_cik=cik,
                    filed_at=filed_at
                )
                
                section_nodes.append(section_node)
            
            # Create the nodes
            if section_nodes:
                self.manager.merge_nodes(section_nodes)
                logger.info(f"Created {len(section_nodes)} section content nodes for report {report_id}")
                
                # Create relationships
                relationships = []
                for section_node in section_nodes:
                    relationships.append((
                        ReportNode(accessionNo=report_id, primaryDocumentUrl='', cik=''),
                        section_node,
                        RelationType.HAS_SECTION
                    ))
                
                if relationships:
                    self.manager.merge_relationships(relationships)
                    logger.info(f"Created {len(relationships)} HAS_SECTION relationships for report {report_id}")
            
            return section_nodes
        
        except Exception as e:
            logger.error(f"Error creating section nodes for report {report_id}: {e}")
            return []


    def _create_exhibit_nodes_from_report(self, report_id, report_data):
        """
        Create exhibit nodes from report exhibit_contents and link them to the report
        
        Args:
            report_id: Report accession number
            report_data: Report data with exhibit_contents, formType, cik, and created
        
        Returns:
            List of created exhibit nodes
        """
        from utils.EventTraderNodes import ExhibitContent, ReportNode
        from XBRL.xbrl_core import RelationType
        
        # Skip if no exhibit contents
        exhibit_contents = report_data.get('exhibit_contents')
        if not exhibit_contents:
            return []
        
        try:
            # Make sure exhibit_contents is a dictionary if it's a JSON string
            if isinstance(exhibit_contents, str):
                exhibit_contents = json.loads(exhibit_contents)
            
            # Get report information needed for exhibit nodes
            form_type = report_data.get('formType', '')
            cik = report_data.get('cik', '')
            filed_at = report_data.get('created', '')
            
            # Create exhibit nodes
            exhibit_nodes = []
            
            for exhibit_number, content in exhibit_contents.items():
                if not content:
                    continue
                
                # Create unique ID from report ID and exhibit number
                content_id = f"{report_id}_EX-{exhibit_number}"
                
                # Handle different content formats
                content_str = content
                if isinstance(content, dict) and 'text' in content:
                    content_str = content['text']
                elif not isinstance(content, str):
                    content_str = str(content)
                
                # Create exhibit content node
                exhibit_node = ExhibitContent(
                    content_id=content_id,
                    filing_id=report_id,
                    form_type=form_type,
                    exhibit_number=exhibit_number,
                    content=content_str,
                    filer_cik=cik,
                    filed_at=filed_at
                )
                
                exhibit_nodes.append(exhibit_node)
            
            # Create the nodes
            if exhibit_nodes:
                self.manager.merge_nodes(exhibit_nodes)
                logger.info(f"Created {len(exhibit_nodes)} exhibit content nodes for report {report_id}")
                
                # Create relationships
                relationships = []
                for exhibit_node in exhibit_nodes:
                    relationships.append((
                        ReportNode(accessionNo=report_id, primaryDocumentUrl='', cik=''),
                        exhibit_node,
                        RelationType.HAS_EXHIBIT
                    ))
                
                if relationships:
                    self.manager.merge_relationships(relationships)
                    logger.info(f"Created {len(relationships)} HAS_EXHIBIT relationships for report {report_id}")
            
            return exhibit_nodes
        
        except Exception as e:
            logger.error(f"Error creating exhibit nodes for report {report_id}: {e}")
            return []


    def _create_filing_text_content_nodes_from_report(self, report_id, report_data):
        """
        Create filing text content node from report filing_text_content and link it to the report
        
        Args:
            report_id: Report accession number
            report_data: Report data with filing_text_content, formType, cik, and created
        
        Returns:
            List containing the created filing text content node, or empty list if none created
        """
        from utils.EventTraderNodes import FilingTextContent, ReportNode
        from XBRL.xbrl_core import RelationType
        
        # Skip if no filing text content
        filing_text_content = report_data.get('filing_text_content')
        if not filing_text_content:
            return []
        
        try:
            # Get report information needed for the filing text content node
            form_type = report_data.get('formType', '')
            cik = report_data.get('cik', '')
            filed_at = report_data.get('created', '')
            
            # Create unique ID for this filing text content
            content_id = f"{report_id}_text"
            
            # Create filing text content node
            filing_text_node = FilingTextContent(
                content_id=content_id,
                filing_id=report_id,
                form_type=form_type,
                content=filing_text_content,
                filer_cik=cik,
                filed_at=filed_at
            )
            
            # Create the node using Neo4jManager's merge_nodes method
            self.manager.merge_nodes([filing_text_node])
            logger.info(f"Created filing text content node for report {report_id}")
            
            # Create relationship using Neo4jManager's merge_relationships method
            relationship = [(
                ReportNode(accessionNo=report_id, primaryDocumentUrl='', cik=''),
                filing_text_node,
                RelationType.HAS_FILING_TEXT
            )]
            
            self.manager.merge_relationships(relationship)
            logger.info(f"Created HAS_FILING_TEXT relationship for report {report_id}")
            
            return [filing_text_node]
        
        except Exception as e:
            logger.error(f"Error creating filing text content node for report {report_id}: {e}")
            return []


    def _create_financial_statement_nodes_from_report(self, report_id, report_data):
        """
        Create financial statement nodes from report financial_statements and link them to the report.
        Creates at most 4 nodes - one for each statement type (BalanceSheets, StatementsOfIncome, etc.)
        
        Args:
            report_id: Report accession number
            report_data: Report data with financial_statements, formType, cik, and created
    
        Returns:
            List of created financial statement nodes
        """
        from utils.EventTraderNodes import FinancialStatementContent, ReportNode
        from XBRL.xbrl_core import RelationType
        
        # Skip if no financial statements
        financial_statements = report_data.get('financial_statements')
        if not financial_statements:
            return []
        
        try:
            # Make sure financial_statements is a dictionary if it's a JSON string
            if isinstance(financial_statements, str):
                financial_statements = json.loads(financial_statements)
            
            # Get report information needed for financial statement nodes
            form_type = report_data.get('formType', '')
            cik = report_data.get('cik', '')
            filed_at = report_data.get('created', '')
            
            # Create financial statement nodes - one for each statement type
            financial_nodes = []
            
            # Process each statement type (BalanceSheets, StatementsOfIncome, etc.)
            for statement_type, metrics in financial_statements.items():
                if not metrics:
                    continue
                
                # Create unique ID for this statement type
                content_id = f"{report_id}_{statement_type}"
                
                # Store the entire content as JSON
                content_json = json.dumps(metrics)
                
                # Create financial statement content node
                financial_node = FinancialStatementContent(
                    content_id=content_id,
                    filing_id=report_id,
                    form_type=form_type,
                    statement_type=statement_type,
                    value=content_json,  # Store the entire content as JSON
                    filer_cik=cik,
                    filed_at=filed_at
                )
                
                financial_nodes.append(financial_node)
            
            # Create the nodes using Neo4jManager's merge_nodes method
            if financial_nodes:
                self.manager.merge_nodes(financial_nodes)
                logger.info(f"Created {len(financial_nodes)} financial statement content nodes for report {report_id}")
                
                # Create relationships using Neo4jManager's merge_relationships method
                relationships = []
                for financial_node in financial_nodes:
                    relationships.append((
                        ReportNode(accessionNo=report_id, primaryDocumentUrl='', cik=''),
                        financial_node,
                        RelationType.HAS_FINANCIAL_STATEMENT
                    ))
                
                if relationships:
                    self.manager.merge_relationships(relationships)
                    logger.info(f"Created {len(relationships)} HAS_FINANCIAL_STATEMENT relationships for report {report_id}")
            
            return financial_nodes
        
        except Exception as e:
            logger.error(f"Error creating financial statement nodes for report {report_id}: {e}")
            return []



    
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
        
        # Extract symbols using the unified method
        symbols = self._extract_symbols_from_data(report_json)
        
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


# endregion


# region: Common Utilities & Helpers : _extract_symbols_from_data, _extract_market_session, _extract_returns_schedule, 
#                                       _extract_return_metrics, _parse_list_field, _prepare_entity_relationship_params, 
#                                       _prepare_report_relationships, reconcile_missing_items



    def _extract_symbols_from_data(self, data_item, symbols_list=None):
        """
        Extract and normalize symbols from data item (news or report).
        Handles both direct symbols list and metadata.instruments sources.
        
        Args:
            data_item (dict): News or report data dictionary
            symbols_list (list or str, optional): Explicit symbols list to process
                                                 (if None, will use data_item.get('symbols'))
        
        Returns:
            list: List of uppercase symbol strings
        """
        symbols = []
        
        # If no explicit symbols_list provided, try to get from data_item
        if symbols_list is None:
            symbols_list = data_item.get('symbols', [])
        
        # Process symbols list
        if isinstance(symbols_list, list):
            symbols = [s.upper() for s in symbols_list if s]
        elif isinstance(symbols_list, str):
            try:
                # Try JSON parsing for array-like strings
                if symbols_list.startswith('[') and symbols_list.endswith(']'):
                    content = symbols_list.replace("'", '"')  # Make JSON-compatible
                    symbols = [s.upper() for s in json.loads(content) if s]
                # Try comma-separated string
                elif ',' in symbols_list:
                    symbols = [s.strip().upper() for s in symbols_list.split(',') if s.strip()]
                else:
                    # Single symbol
                    symbols = [symbols_list.upper()]
            except:
                # Last resort parsing for malformed strings
                clean = symbols_list.strip('[]').replace("'", "").replace('"', "")
                symbols = [s.strip().upper() for s in clean.split(',') if s.strip()]
        
        # Extract additional symbols from metadata if available
        if 'metadata' in data_item and 'instruments' in data_item['metadata']:
            for instrument in data_item['metadata']['instruments']:
                symbol = instrument.get('symbol', '')
                if symbol and symbol.upper() not in symbols:
                    symbols.append(symbol.upper())
                    
        return symbols



    def _extract_market_session(self, data_item):
        """
            str: Market session value (e.g., 'pre_market', 'in_market', 'post_market') or empty string
        """
        if 'metadata' in data_item and 'event' in data_item['metadata']:
            return data_item['metadata']['event'].get('market_session', '')
        return ''
    
    def _extract_returns_schedule(self, data_item):
        """
        Extract and parse returns schedule from data item.
        
        Args:
            data_item (dict): News or report data dictionary
            
        Returns:
            dict: Dictionary with parsed return schedule dates in ISO format
        """
        returns_schedule = {}
        
        if 'metadata' in data_item and 'returns_schedule' in data_item['metadata']:
            raw_schedule = data_item['metadata']['returns_schedule']
            
            # Parse each date in the schedule
            for key, time_str in raw_schedule.items():
                if time_str:
                    try:
                        date_obj = parse_date(time_str)
                        if date_obj:
                            returns_schedule[key] = date_obj.isoformat()
                    except Exception as e:
                        logger.warning(f"Error parsing returns schedule date '{time_str}': {e}")
        
        return returns_schedule


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



    def _prepare_entity_relationship_params(self, data_item, symbols, universe_data, ticker_to_cik, timestamp):
        """
        Prepare relationship parameters for different entity types based on symbols.
        Common method used by both news and reports processing.
        
        Args:
            data_item (dict): The news or report data
            symbols (list): List of symbols to process
            universe_data (dict): Universe data mapping
            ticker_to_cik (dict): Mapping of tickers to CIKs
            timestamp (str): ISO-formatted timestamp for created_at field
            
        Returns:
            tuple: (valid_symbols, company_params, sector_params, industry_params, market_params)
        """
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
            metrics = self._extract_return_metrics(data_item, symbol_upper)
            
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
                'timestamp': timestamp,
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
            # for timeframe in ['hourly', 'session', 'daily']:
            #     metric_key = f"{timeframe}_stock"
            #     if metric_key in symbol_data_item['metrics']:
            #         props[metric_key] = symbol_data_item['metrics'][metric_key]

            # Add ALL metrics: stock, sector, industry, macro
            for metric_key, metric_value in symbol_data_item['metrics'].items():
                props[metric_key] = metric_value
            
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
            
            # Check for benchmark data in data_item for ETF property (only for news items)
            if ('metadata' in data_item and 'instruments' in data_item['metadata']):
                for instrument in data_item['metadata']['instruments']:
                    if instrument.get('symbol', '').upper() == symbol and 'benchmarks' in instrument:
                        if not sector_etf and 'sector' in instrument['benchmarks']:
                            sector_etf = instrument['benchmarks']['sector']
            
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
            
            # Check for benchmark data in data_item for ETF property (only for news items)
            if ('metadata' in data_item and 'instruments' in data_item['metadata']):
                for instrument in data_item['metadata']['instruments']:
                    if instrument.get('symbol', '').upper() == symbol and 'benchmarks' in instrument:
                        if not industry_etf and 'industry' in instrument['benchmarks']:
                            industry_etf = instrument['benchmarks']['industry']
            
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
                
        return valid_symbols, company_params, sector_params, industry_params, market_params

    def _prepare_report_relationships(self, report_data, symbols, universe_data, ticker_to_cik):
        """Prepare relationship parameters for symbols"""
        # Extract timestamps with proper parsing
        filed_at = parse_date(report_data.get('filedAt')) if report_data.get('filedAt') else None
        filed_str = filed_at.isoformat() if filed_at else ""
        
        # Delegate to the common method
        return self._prepare_entity_relationship_params(
            data_item=report_data,
            symbols=symbols,
            universe_data=universe_data,
            ticker_to_cik=ticker_to_cik,
            timestamp=filed_str
        )




    def reconcile_missing_items(self, max_items_per_type=1000):
        """
        Identify and process items in Redis that are missing from Neo4j.
        Also checks for date node creation once after midnight.
        
        Returns:
            dict: results keyed by item type with counts
        """
        results = {"news": 0, "reports": 0, "dates": 0}
        
        try:
            # Extract midnight operations to separate method
            self._handle_midnight_operations(results)
            
            with self.manager.driver.session() as session:
                # 1. NEWS RECONCILIATION
                for namespace in ['withreturns', 'withoutreturns']:
                    pattern = RedisKeys.get_key(source_type=self.event_trader_redis.source, 
                                            key_type=namespace, identifier="*")
                    
                    # Get news IDs from Redis
                    redis_news_ids = set()
                    for key in self.event_trader_redis.history_client.client.scan_iter(pattern):
                        news_id = key.split(':')[-1].split('.')[0]  # Extract base ID
                        redis_news_ids.add(f"bzNews_{news_id}")
                    
                    if not redis_news_ids:
                        continue
                        
                    # Process in batches of 1000
                    for batch in [list(redis_news_ids)[i:i+1000] for i in range(0, len(redis_news_ids), 1000)]:
                        # Query Neo4j for these news IDs
                        cypher = "MATCH (n:News) WHERE n.id IN $ids RETURN n.id as id"
                        result = session.run(cypher, ids=batch)
                        neo4j_news_ids = {record["id"] for record in result}
                        
                        # Find missing news IDs
                        missing_ids = set(batch) - neo4j_news_ids
                        
                        # Process missing items
                        for news_id in list(missing_ids)[:max_items_per_type]:
                            original_id = news_id[7:]  # Remove "bzNews_" prefix
                            
                            # Try both namespaces
                            for ns in ['withreturns', 'withoutreturns']:
                                key = RedisKeys.get_key(source_type=self.event_trader_redis.source,
                                                    key_type=ns, identifier=original_id)
                                raw_data = self.event_trader_redis.history_client.get(key)
                                if raw_data:
                                    news_data = json.loads(raw_data)
                                    success = self._process_deduplicated_news(news_id, news_data)
                                    results["news"] += 1

                                    # Delete key if it's from withreturns namespace
                                    if success and ns == 'withreturns':
                                        try:
                                            self.event_trader_redis.history_client.client.delete(key)
                                            logger.debug(f"Deleted reconciled withreturns key: {key}")
                                        except Exception as e:
                                            logger.warning(f"Error deleting key {key}: {e}")


                                    break
                
                # 2. REPORTS RECONCILIATION
                for namespace in ['withreturns', 'withoutreturns']:
                    pattern = RedisKeys.get_key(source_type=RedisKeys.SOURCE_REPORTS, 
                                            key_type=namespace, identifier="*")
                    
                    # Get report IDs from Redis
                    redis_report_ids = set()
                    for key in self.event_trader_redis.history_client.client.scan_iter(pattern):
                        report_id = key.split(':')[-1]
                        redis_report_ids.add(report_id)
                    
                    if not redis_report_ids:
                        continue
                        
                    # Process in batches of 1000
                    for batch in [list(redis_report_ids)[i:i+1000] for i in range(0, len(redis_report_ids), 1000)]:
                        # Query Neo4j for these report IDs
                        cypher = "MATCH (r:Report) WHERE r.accessionNo IN $ids RETURN r.accessionNo as id"
                        result = session.run(cypher, ids=batch)
                        neo4j_report_ids = {record["id"] for record in result}
                        
                        # Find missing report IDs
                        missing_ids = set(batch) - neo4j_report_ids
                        
                        # Process missing items
                        for report_id in list(missing_ids)[:max_items_per_type]:
                            # Try both namespaces
                            for ns in ['withreturns', 'withoutreturns']:
                                key = RedisKeys.get_key(source_type=RedisKeys.SOURCE_REPORTS,
                                                    key_type=ns, identifier=report_id)
                                raw_data = self.event_trader_redis.history_client.get(key)
                                if raw_data:
                                    report_data = json.loads(raw_data)
                                    success = self._process_deduplicated_report(report_id, report_data)
                                    results["reports"] += 1

                                    # Delete key if it's from withreturns namespace
                                    if success and ns == 'withreturns':
                                        try:
                                            self.event_trader_redis.history_client.client.delete(key)
                                            logger.debug(f"Deleted reconciled withreturns key: {key}")
                                        except Exception as e:
                                            logger.warning(f"Error deleting key {key}: {e}")


                                    break
            
            logger.info(f"Reconciliation completed: {results}")
            return results
        
        except Exception as e:
            logger.error(f"Error reconciling missing items: {e}")
            return results

    def _handle_midnight_operations(self, results):
        """Check for and create yesterday's date node if missing, regardless of current time"""
        # Run date node reconciliation regardless of hour
        date_nodes_created = self.reconcile_date_nodes()
        results["dates"] = date_nodes_created
        if date_nodes_created > 0:
            logger.info(f"Created {date_nodes_created} date node(s) during reconciliation")
        return results



# endregion


# region: Database Operation Helpers : _create_influences_relationships, _reclassify_report_company_relationships, _process_xbrl


    def _create_influences_relationships(self, session, source_id, source_label, entity_type, params, create_node_cypher=None):
        """
        Generic method to create INFLUENCES relationships between a source node (News or Report) and various entity types.
        Uses Neo4jManager.create_relationships for the actual implementation.
        
        Args:
            session: Neo4j session (not used directly but kept for interface compatibility)
            source_id: ID of the source node (report or news)
            source_label: Label of the source node ("News" or "Report")
            entity_type: Type of entity to connect (Company, Sector, Industry, MarketIndex)
            params: List of parameter dictionaries for the UNWIND operation
            create_node_cypher: Optional custom Cypher for node creation/update (not used)
            
        Returns:
            Number of relationships created
        """
        if not params:
            return 0
            
        # Import here to avoid circular imports
        from XBRL.Neo4jConnection import get_manager
        
        # Get the singleton Neo4j manager
        neo4j_manager = self.manager if hasattr(self, 'manager') else get_manager()
        
        try:
            count = 0
            if entity_type == "Company":
                count = neo4j_manager.create_relationships(
                    source_label=source_label, 
                    source_id_field="id", 
                    source_id_value=source_id,
                    target_label="Company", 
                    target_match_clause="{cik: param.cik}", 
                    rel_type="INFLUENCES", 
                    params=params
                )
            elif entity_type == "Sector":
                count = neo4j_manager.create_relationships(
                    source_label=source_label, 
                    source_id_field="id", 
                    source_id_value=source_id,
                    target_label="Sector", 
                    target_match_clause="{id: param.sector_id}", 
                    rel_type="INFLUENCES", 
                    params=params,
                    target_create_properties="target.name = param.sector_name, target.etf = param.sector_etf",
                    target_set_properties="""
                        target.etf = CASE 
                            WHEN param.sector_etf IS NOT NULL AND (target.etf IS NULL OR target.etf = '') 
                            THEN param.sector_etf ELSE target.etf 
                        END
                    """
                )
            elif entity_type == "Industry":
                count = neo4j_manager.create_relationships(
                    source_label=source_label, 
                    source_id_field="id", 
                    source_id_value=source_id,
                    target_label="Industry", 
                    target_match_clause="{id: param.industry_id}", 
                    rel_type="INFLUENCES", 
                    params=params,
                    target_create_properties="target.name = param.industry_name, target.etf = param.industry_etf",
                    target_set_properties="""
                        target.etf = CASE 
                            WHEN param.industry_etf IS NOT NULL AND (target.etf IS NULL OR target.etf = '') 
                            THEN param.industry_etf ELSE target.etf 
                        END
                    """
                )
            elif entity_type == "MarketIndex":
                count = neo4j_manager.create_relationships(
                    source_label=source_label, 
                    source_id_field="id", 
                    source_id_value=source_id,
                    target_label="MarketIndex", 
                    target_match_clause="{id: 'SPY'}", 
                    rel_type="INFLUENCES", 
                    params=params,
                    target_create_properties="target.name = 'S&P 500 ETF', target.ticker = 'SPY', target.etf = 'SPY'",
                    target_set_properties="""
                        target.ticker = 'SPY', target.etf = 'SPY',
                        target.name = CASE 
                            WHEN target.name IS NULL OR target.name = '' 
                            THEN 'S&P 500 ETF' ELSE target.name 
                        END
                    """
                )
            
            if count > 0:
                logger.info(f"Created {count} INFLUENCES relationships to {entity_type.lower()}s")
                
            return count
        finally:
            # Don't close the singleton manager
            pass









    def _process_xbrl(self, session, report_id, cik, accessionNo):
        """
        Queue an XBRL report for background processing.
        
        Args:
            session: Neo4j session
            report_id: Report ID
            cik: Company CIK
            accessionNo: Report accession number
            
        Returns:
            bool: Success status for queueing (not processing)
        """
        try:
            # Update status to QUEUED - using transaction function for automatic retry
            def update_queued_status(tx):
                tx.run(
                    "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status",
                    id=report_id, status="QUEUED"
                )
            session.execute_write(update_queued_status)
            
            # Add a small delay before submitting to reduce contention
            time.sleep(0.1)  # 100ms delay to stagger job submissions
            
            # Submit task to thread pool and return immediately
            self.xbrl_executor.submit(
                self._xbrl_worker_task, 
                report_id, 
                cik, 
                accessionNo
            )
            
            logger.info(f"Queued report {report_id} for background XBRL processing")
            return True
            
        except Exception as e:
            error_msg = str(e)[:255]  # Limit error message length
            logger.error(f"Error queueing XBRL for report {report_id}: {error_msg}")
            
            # Update status to FAILED - using transaction function for automatic retry
            def update_failed_status(tx):
                tx.run(
                    "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status, r.xbrl_error = $error",
                    id=report_id, status="FAILED", error=str(e)
                )
            session.execute_write(update_failed_status)
            return False

            

    def _xbrl_worker_task(self, report_id, cik, accessionNo):
        """Process a single XBRL report in background"""
        # Add semaphore acquisition flag
        acquired = False
        
        try:
            # Try to acquire semaphore before processing
            acquired = self.xbrl_semaphore.acquire(timeout=5)
            if not acquired:
                # Cannot acquire - update status and exit
                with self.manager.driver.session() as session:
                    # Use transaction function for automatic retry on deadlocks
                    def update_pending_status(tx):
                        tx.run(
                            "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status, r.xbrl_error = $error",
                            id=report_id, status="PENDING", error="System resource limit reached"
                        )
                    session.execute_write(update_pending_status)
                logger.info(f"Resource limit reached for report {report_id}, will retry later")
                return
                
            # Create a new session for this thread
            with self.manager.driver.session() as session:
                start_time = time.time()  # Start timing
                try:
                    # Mark as processing - using transaction function for automatic retry
                    def update_processing_status(tx):
                        tx.run(
                            "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status",
                            id=report_id, status="PROCESSING"
                        )
                    session.execute_write(update_processing_status)
                    
                    # Import needed components
                    from XBRL.xbrl_processor import process_report, get_company_by_cik, get_report_by_accessionNo
                    from XBRL.Neo4jConnection import get_manager
                    
                    # Use the singleton Neo4j manager
                    neo4j_manager = get_manager()
                    
                    # Track the XBRL processor instance for proper cleanup
                    xbrl_processor = None
                    
                    try:
                        # Use the existing helper functions to get Report and Company nodes
                        report_node = get_report_by_accessionNo(neo4j_manager, accessionNo)
                        if not report_node:
                            logger.error(f"Report with accessionNo {accessionNo} not found in Neo4j")
                            def update_failed_status(tx):
                                tx.run(
                                    "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status, r.xbrl_error = $error",
                                    id=report_id, status="FAILED", error="Report not found in Neo4j"
                                )
                            session.execute_write(update_failed_status)
                            return
                            
                        company_node = get_company_by_cik(neo4j_manager, report_node.cik)
                        if not company_node:
                            logger.error(f"Company with CIK {report_node.cik} not found in Neo4j")
                            def update_failed_status(tx):
                                tx.run(
                                    "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status, r.xbrl_error = $error",
                                    id=report_id, status="FAILED", error="Company not found in Neo4j"
                                )
                            session.execute_write(update_failed_status)
                            return
                        
                        # Use the properly formatted values from the Neo4j nodes
                        processed_cik = company_node.cik
                        processed_accessionNo = report_node.accessionNo
                        
                        logger.info(f"Processing XBRL for report {report_id} (CIK: {processed_cik}, AccessionNo: {processed_accessionNo})")
                        
                        # Process the report and store the processor instance
                        xbrl_processor = process_report(
                            neo4j=neo4j_manager,
                            cik=processed_cik,
                            accessionNo=processed_accessionNo,
                            testing=False
                        )
                        
                        # Mark as completed - using transaction function for automatic retry
                        def update_completed_status(tx):
                            tx.run(
                                "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status",
                                id=report_id, status="COMPLETED"
                            )
                        session.execute_write(update_completed_status)
                        
                        # Log completion time
                        elapsed = time.time() - start_time
                        mins, secs = divmod(int(elapsed), 60)
                        logger.info(f"Completed XBRL processing for report {report_id} in {mins}m {secs}s")
                        
                        # Add delay after each successful processing to allow for resource cleanup
                        time.sleep(3)  # 3 second delay to allow for resource cleanup
                        
                    finally:
                        # Explicitly clean up XBRL resources
                        if xbrl_processor:
                            try:
                                xbrl_processor.close_resources()
                                logger.info(f"Cleaned up XBRL resources for report {report_id}")
                            except Exception as e:
                                logger.warning(f"Failed to clean up XBRL resources for report {report_id}: {e}")
                        
                        # Don't close the singleton manager
                        pass
                        
                except Exception as e:
                    # Log error with timing
                    elapsed = time.time() - start_time
                    mins, secs = divmod(int(elapsed), 60)
                    logger.error(f"Error in XBRL processing for report {report_id} after {mins}m {secs}s: {e}")
                    
                    # Update status to FAILED - using transaction function for automatic retry
                    def update_failed_status(tx):
                        tx.run(
                            "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status, r.xbrl_error = $error",
                            id=report_id, status="FAILED", error=str(e)
                        )
                    session.execute_write(update_failed_status)
        finally:
            # Release semaphore if acquired
            if acquired:
                self.xbrl_semaphore.release()



    def reconcile_date_nodes(self):
        """Check for yesterday's date node and create it with price relationships if needed"""
        try:
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            day_before = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
            
            # Check both nodes and price relationships in a single query
            query = """
            MATCH (yesterday:Date {date: $yesterday}) 
            OPTIONAL MATCH (yesterday)-[r:HAS_PRICE]->()
            OPTIONAL MATCH (previous:Date {date: $day_before})
            RETURN count(yesterday) as yesterday_exists, 
                   count(r) as has_prices, 
                   count(previous) as previous_exists
            """
            result = self.manager.execute_cypher_query(query, 
                                                      {"yesterday": yesterday, 
                                                       "day_before": day_before})
            
            # Skip if everything is in place
            if (result and result["yesterday_exists"] > 0 and 
                result["has_prices"] > 0):
                return 0
                
            # Initialize needed components
            if not self.universe_data:
                self.universe_data = self._get_universe()
                if not self.universe_data:
                    return 0
            
            # Create initializer and connect
            from utils.Neo4jInitializer import Neo4jInitializer
            initializer = Neo4jInitializer(
                uri=self.uri, 
                username=self.username,
                password=self.password,
                universe_data=self.universe_data
            )
            
            if initializer.connect():
                try:
                    initializer.prepare_universe_data()
                    
                    # Create previous date first if needed
                    if not result or result["previous_exists"] == 0:
                        initializer.create_single_date(day_before)
                    
                    # Create yesterday with price relationships
                    return 1 if initializer.create_single_date(yesterday) else 0
                finally:
                    initializer.close()
            
            return 0
        except Exception as e:
            logger.error(f"Error reconciling date nodes: {e}")
            return 0



    # def _xbrl_worker_task(self, report_id, cik, accessionNo):
    #     """Process a single XBRL report in background"""
    #     # Create a new session for this thread
    #     with self.manager.driver.session() as session:
    #         start_time = time.time()  # Start timing
    #         try:
    #             # Mark as processing
    #             session.run(
    #                 "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status",
    #                 id=report_id, status="PROCESSING"
    #             )
                
    #             # Import needed components
    #             from XBRL.xbrl_processor import process_report, get_company_by_cik, get_report_by_accessionNo
    #             from XBRL.Neo4jManager import Neo4jManager
                
    #             # Create a dedicated Neo4j connection for this task
    #             neo4j_manager = Neo4jManager(
    #                 uri=self.uri,
    #                 username=self.username,
    #                 password=self.password
    #             )
                
    #             # Track the XBRL processor instance for proper cleanup
    #             xbrl_processor = None
                
    #             try:
    #                 # Use the existing helper functions to get Report and Company nodes
    #                 report_node = get_report_by_accessionNo(neo4j_manager, accessionNo)
    #                 if not report_node:
    #                     logger.error(f"Report with accessionNo {accessionNo} not found in Neo4j")
    #                     session.run(
    #                         "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status, r.xbrl_error = $error",
    #                         id=report_id, status="FAILED", error="Report not found in Neo4j"
    #                     )
    #                     return
                        
    #                 company_node = get_company_by_cik(neo4j_manager, report_node.cik)
    #                 if not company_node:
    #                     logger.error(f"Company with CIK {report_node.cik} not found in Neo4j")
    #                     session.run(
    #                         "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status, r.xbrl_error = $error",
    #                         id=report_id, status="FAILED", error="Company not found in Neo4j"
    #                     )
    #                     return
                    
    #                 # Use the properly formatted values from the Neo4j nodes
    #                 processed_cik = company_node.cik
    #                 processed_accessionNo = report_node.accessionNo
                    
    #                 logger.info(f"Processing XBRL for report {report_id} (CIK: {processed_cik}, AccessionNo: {processed_accessionNo})")
                    
    #                 # Process the report and store the processor instance
    #                 xbrl_processor = process_report(
    #                     neo4j=neo4j_manager,
    #                     cik=processed_cik,
    #                     accessionNo=processed_accessionNo,
    #                     testing=False
    #                 )
                    
    #                 # Mark as completed
    #                 session.run(
    #                     "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status",
    #                     id=report_id, status="COMPLETED"
    #                 )
    #                 # Log completion time
    #                 elapsed = time.time() - start_time
    #                 mins, secs = divmod(int(elapsed), 60)
    #                 logger.info(f"Completed XBRL processing for report {report_id} in {mins}m {secs}s")
                    
    #                 # Add delay after each successful processing to allow for resource cleanup
    #                 time.sleep(3)  # 3 second delay to allow for resource cleanup
                    
    #             finally:
    #                 # Explicitly clean up XBRL resources
    #                 if xbrl_processor:
    #                     try:
    #                         xbrl_processor.close_resources()
    #                         logger.info(f"Cleaned up XBRL resources for report {report_id}")
    #                     except Exception as e:
    #                         logger.warning(f"Failed to clean up XBRL resources for report {report_id}: {e}")
                    
    #                 # Always close the manager
    #                 neo4j_manager.close()
                    
    #         except Exception as e:
    #             # Log error with timing
    #             elapsed = time.time() - start_time
    #             mins, secs = divmod(int(elapsed), 60)
    #             logger.error(f"Error in XBRL processing for report {report_id} after {mins}m {secs}s: {e}")
    #             session.run(
    #                 "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status, r.xbrl_error = $error",
    #                 id=report_id, status="FAILED", error=str(e)
    #             )

# endregion







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
        from utils.Neo4jInitializer import Neo4jInitializer
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

# Testing function for initialization with custom required nodes
def test_initialization_with_custom_nodes(required_nodes=None, run_init=False):
    """
    Test function to simulate initialization with custom required nodes
    
    Args:
        required_nodes: Custom list of required node types
        run_init: Whether to actually run the initialization
        
    Returns:
        True if the database is considered initialized with the given requirements
    """
    original_nodes = Neo4jProcessor.REQUIRED_NODES
    
    try:
        if required_nodes:
            Neo4jProcessor.REQUIRED_NODES = required_nodes
            
        # Check initialization status
        processor = Neo4jProcessor()
        is_init = processor.is_initialized()
        
        # Run initialization if requested
        if not is_init and run_init:
            logger.info("Database not initialized with custom nodes, running initialization...")
            init_result = init_neo4j()
            logger.info(f"Initialization result: {init_result}")
            
            # Check again after initialization
            is_init = processor.is_initialized()
            
        return is_init
        
    finally:
        # Restore original required nodes
        Neo4jProcessor.REQUIRED_NODES = original_nodes

