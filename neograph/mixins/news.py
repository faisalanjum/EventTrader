# neograph/mixins/news.py

import logging
from typing import Dict, List, Optional, Any, Set, Tuple
import json
from utils.date_utils import parse_news_dates
from utils.id_utils import canonicalise_news_full_id
from ..EventTraderNodes import NewsNode
from config.feature_flags import ENABLE_NEWS_EMBEDDINGS
from redisDB.redis_constants import RedisKeys  # NEW: needed for withreturns cleanup

logger = logging.getLogger(__name__)

class NewsMixin:
    """
    Handles processing and storage of news data into Neo4j.
    """

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

                        # --- NEW: clean up withreturns key after successful batch insert ---
                        if success and namespace == RedisKeys.SUFFIX_WITHRETURNS:
                            try:
                                self.hist_client.client.delete(key)
                                logger.debug(f"Deleted withreturns key after batch processing: {key}")
                            except Exception as e_del:
                                logger.warning(f"Error deleting withreturns key {key}: {e_del}")
                        # -------------------------------------------------------------------

                        if success:
                            processed_count += 1
                        else:
                            error_count += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing news key {key}: {e}", exc_info=True)
                        error_count += 1
                
                logger.info(f"Processed batch {i//batch_size + 1}/{(len(news_keys) + batch_size - 1)//batch_size}")
                
            # Summary and status
            logger.info(f"Finished processing news to Neo4j. Processed: {processed_count}, Errors: {error_count}")
            
            # Check if we should generate embeddings based on feature flag
            if processed_count > 0:
                
                if ENABLE_NEWS_EMBEDDINGS:
                    try:
                        logger.info("Auto-generating embeddings based on feature flag...")
                        embedding_results = self.batch_process_news_embeddings(batch_size=batch_size)
                        logger.info(f"Auto embedding generation results: {embedding_results}")
                    except Exception as e:
                        logger.warning(f"Could not auto-generate embeddings: {e}")
            
            # Remove batch deletion approach in favor of immediate deletion
            return processed_count > 0 or error_count == 0
                
        except Exception as e:
            logger.error(f"Error processing news data: {e}", exc_info=True)
            return False




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
            success = self._execute_news_database_operations(
                news_id, news_node, valid_symbols, company_params, 
                sector_params, industry_params, market_params, timestamps
            )

            if success and hasattr(self, 'event_trader_redis') and self.event_trader_redis:
                # Remove internal "bzNews_" prefix to match lifecycle key
                base_id = news_id.replace("bzNews_", "", 1)
                id_only = base_id
                
                # Try to get timestamp from updated or created fields
                updated_ts_iso = news_data.get('updated', '')
                created_ts_iso = news_data.get('created', '')
                
                # Prefer updated, fall back to created
                timestamp_iso = updated_ts_iso if updated_ts_iso else created_ts_iso
                updated_key_suffix = timestamp_iso.replace(':', '.') if timestamp_iso else ''

                if not updated_key_suffix:
                    logger.warning(f"Missing both 'updated' and 'created' timestamps in news_data for {id_only}, meta key will lack suffix.")
                    full_news_id_for_meta = id_only # Fallback to id_only if no timestamp available
                else:
                    raw_full_id = f"{id_only}.{updated_key_suffix}"
                    # Always canonicalize to UTC for the meta key
                    full_news_id_for_meta = canonicalise_news_full_id(raw_full_id)
                
                meta_key = f"tracking:meta:{self.event_trader_redis.source}:{full_news_id_for_meta}"
                try:
                    # Use TTL defined in Redis client configuration (if any)
                    self.event_trader_redis.history_client.mark_lifecycle_timestamp(meta_key, "inserted_into_neo4j_at")
                except Exception as e:
                    logger.warning(f"Failed to mark lifecycle timestamp for {meta_key}: {e}")
                    pass

            return success
                
        except Exception as e:
            logger.error(f"Error processing news {news_id}: {e}", exc_info=True)
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

