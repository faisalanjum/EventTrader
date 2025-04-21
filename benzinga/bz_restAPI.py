# https://docs.benzinga.com/benzinga-apis/newsfeed-v2/newsService-get

"""
Benzinga News REST API Client

Important API Parameter Notes:
1. Date Parameters (dateFrom, dateTo):
   - Only accept dates in YYYY-MM-DD format
   - Time components are not supported
   - Example: "2024-01-24"

2. Timestamp Parameters:
   - updatedSince: Unix timestamp in UTC 
   - Used to fetch news items updated after this timestamp
   - Example: 1706112000 (for 2024-01-24 12:00:00 UTC)

Implementation Details:
1. Maximum Page Size:
   - Set to 100 items per request (API maximum)
   - Implemented in self.ITEMS_PER_PAGE and _build_params()

2. Sort Order:
   - Uses "updated:desc" for most recent updates first
   - Implemented in _build_params()

3. Pagination:
   - Handles API limit of 0-100000 pages
   - Implemented in fetch_news() with MAX_PAGE_LIMIT
   - Includes progress tracking and automatic completion

4. Pagination Controls:
   - Stops on: fewer items than pageSize
   - Stops on: empty response
   - Stops on: API errors
   - Implemented in fetch_news() with detailed progress logging

5. Delta Updates:
   - Uses updatedSince with 5-second buffer
   - Critical for reliable data retrieval
   - Implemented in _build_params() and stream_news()

For more details: https://docs.benzinga.com/benzinga-apis/newsfeed-v2/newsService-get
"""


import time
import json
import requests
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union

from benzinga.bz_news_errors import NewsErrorHandler
from benzinga.bz_news_schemas import BzRestAPINews, UnifiedNews  # We'll need this for validation & unified format
from redisDB.redisClasses import RedisClient
from utils.log_config import get_logger, setup_logging

class BenzingaNewsRestAPI:
    """Simple class to fetch and print Benzinga news data"""
    
    def __init__(self, api_key: str, redis_client: RedisClient, ttl: int = 3600):
        self.redis_client = redis_client
        self.ttl = ttl 
        self.api_url = "https://api.benzinga.com/api/v2/news"
        self.api_key = api_key
        self.headers = {"accept": "application/json"}
        self.MAX_PAGE_LIMIT = 100000  # API supports up to 100,000 pages
        self.ITEMS_PER_PAGE = 99     # API requires pageSize < 100
        self.error_handler = NewsErrorHandler()  # Add error handler
        self.logger = get_logger("benzinga_rest_api")  # Add centralized logger

    def _build_params(self, 
                     page: int = 0,
                     updated_since: Optional[int] = None,
                     date_from: Optional[str] = None, 
                     date_to: Optional[str] = None,
                     tickers: Optional[List[str]] = None) -> Dict[str, Any]:
        """Build query parameters for the API request"""
        params = {
            "token": self.api_key,
            "page": page,
            "pageSize": self.ITEMS_PER_PAGE,
            "displayOutput": "full", # full, abstract, headline
            "sort": "updated:desc"
        }
        
        if updated_since is not None:
            # API expects Unix timestamp in UTC
            params["updatedSince"] = updated_since - 5  # Subtract 5 seconds per API guidelines
            
        if date_from:
            # Format: YYYY-MM-DD
            params["dateFrom"] = date_from
        if date_to:
            # Format: YYYY-MM-DD
            params["dateTo"] = date_to
            
        if tickers:
            params["tickers"] = ",".join(tickers)
            
        return params


    def _fetch_news(self, updated_since: Optional[int] = None,
                date_from: Optional[str] = None, 
                date_to: Optional[str] = None,
                tickers: Optional[List[str]] = None,
                raw: bool = False) -> List[Union[BzRestAPINews, UnifiedNews]]:
        """Internal method to fetch news from API"""
        self.error_handler.reset_stats()
        
        all_items = []
        current_page = 0
        total_items_received = 0
        current_batch = []  # For Redis batch storage
        BATCH_SIZE = 1000   # Explicit constant
        
        # Original logging
        self.logger.info("\nStarting API Request:")
        self.logger.info(f"- date_from: {date_from}")
        self.logger.info(f"- date_to: {date_to}")
        self.logger.info(f"- updated_since: {updated_since}")
        self.logger.info(f"- tickers: {tickers}")
        
        while current_page < self.MAX_PAGE_LIMIT:
            try:
                # Original pagination params
                params = self._build_params(
                    page=current_page,
                    updated_since=updated_since,
                    date_from=date_from,
                    date_to=date_to,
                    tickers=tickers
                )
                
                # Log progress but don't use end='\r' with logger
                self.logger.info(f"Fetching page {current_page}...")
                
                # Original API call and validation
                response = requests.get(self.api_url, headers=self.headers, params=params)
                response.raise_for_status()
                
                news_items = response.json()
                total_items_received += len(news_items)
                
                # Process items (maintaining original logic while adding Redis)
                current_page_items = []
                for raw_item in news_items:
                    item_id = raw_item.get('id', 'unknown')
                    self.error_handler.handle_news_item(item_id, "received", {})
                    
                    # Original processing for return value
                    processed_item = self.error_handler.process_news_item(raw_item, raw)
                    if processed_item:
                        current_page_items.append(processed_item)
                        # Additional Redis processing (always unified)
                        unified_item = self.error_handler.process_news_item(raw_item, raw=False)
                        current_batch.append(unified_item)
                        self.error_handler.handle_news_item(item_id, "processed", {})
                        
                        # Batch Redis storage
                        if len(current_batch) >= BATCH_SIZE:
                            self.redis_client.set_news_batch(current_batch, ex=self.ttl)
                            current_batch = []
                
                # Original item collection
                all_items.extend(current_page_items)
                
                # Original pagination check
                if len(news_items) < self.ITEMS_PER_PAGE:
                    self.logger.info(f"\nReached end of data at page {current_page}")
                    is_complete = True
                    break
                
                current_page += 1
                
                # Add a small delay to prevent API rate limiting
                time.sleep(0.2)
                
            except json.JSONDecodeError as je:
                self.error_handler.handle_json_error(je, response.text)
                break
            except requests.exceptions.RequestException as e:
                self.error_handler.handle_connection_error(e)
                break
        
        # Store final batch if any
        if current_batch:
            self.redis_client.set_news_batch(current_batch, ex=self.ttl)
        
        # Verify if there's more data only if we need to (exact page size edge case)
        is_complete = False
        if 'news_items' in locals():
            if len(news_items) < self.ITEMS_PER_PAGE:
                is_complete = True
            elif current_page < self.MAX_PAGE_LIMIT and len(news_items) == self.ITEMS_PER_PAGE:
                # Check one page ahead to confirm if there's more data (only for the edge case)
                try:
                    verify_response = requests.get(self.api_url, headers=self.headers, params=self._build_params(
                        page=current_page + 1, updated_since=updated_since, date_from=date_from, 
                        date_to=date_to, tickers=tickers))
                    is_complete = len(verify_response.json()) == 0 
                except Exception:
                    is_complete = False
        
        # Original summary logging
        self.logger.info("\nFetch Summary:")
        self.logger.info(f"Pages processed: {current_page + 1}" + (" (COMPLETE - all pages fetched)" if is_complete else " (INCOMPLETE - more pages available)"))
        self.logger.info(f"Total items received: {total_items_received}")
        self.logger.info(f"Items processed successfully: {len(all_items)}")
        if total_items_received > 0:
            self.logger.info(f"Success rate: {(len(all_items)/total_items_received)*100:.1f}%")
        else:
            self.logger.info("Success rate: N/A (no items received)")
        self.logger.info(self.error_handler.get_summary())
        
        return all_items

    def print_error_stats(self):
        """Print current error statistics"""
        print(self.error_handler.get_summary())

    @staticmethod
    def print_news_item(item: Union[BzRestAPINews, UnifiedNews]):
        """Print news item in appropriate format"""
        item.print()


    def get_historical_data(self,
                           date_from: str,
                           date_to: str,
                           tickers: Optional[List[str]] = None,
                           raw: bool = False) -> List[Union[BzRestAPINews, UnifiedNews]]:
        """Get historical news data between dates"""
        # Check feature flag with local import
        from config.feature_flags import ENABLE_HISTORICAL_DATA
        if not ENABLE_HISTORICAL_DATA:
            self.logger.info("Benzinga historical data ingestion disabled by feature flag")
            return []
            
        # Continue with original implementation
        # Store result before returning
        result = self._fetch_news(
            date_from=date_from,
            date_to=date_to,
            tickers=tickers,
            raw=raw
        )

        # --- Fetch Complete Signal --- Start
        try:
            batch_id = f"news:{date_from}-{date_to}"
            # Use the underlying redis-py client from RedisClient instance
            self.redis_client.client.set(f"batch:{batch_id}:fetch_complete", "1", ex=86400) 
            self.logger.info(f"Set fetch_complete flag for batch: {batch_id}")
        except Exception as e:
            self.logger.error(f"Failed to set fetch_complete flag for news batch {batch_id}: {e}")
        # --- Fetch Complete Signal --- End

        return result # Return stored result

    def get_news_since(self,
                       timestamp: int,
                       tickers: Optional[List[str]] = None,
                       raw: bool = False) -> List[Union[BzRestAPINews, UnifiedNews]]:
        """Get news since timestamp"""
        return self._fetch_news(
            updated_since=timestamp,
            tickers=tickers,
            raw=raw
        )

    # Using websocket instead of this
    def stream_news(self, interval: int = 5, tickers: Optional[List[str]] = None, raw: bool = False):
        """Stream news in real-time"""
        last_updated = int(datetime.now(timezone.utc).timestamp()) - 5
        print(f"Starting news stream from: {last_updated}")
        if tickers:
            print(f"Filtering for tickers: {tickers}")
        
        try:
            while True:
                news_items = self._fetch_news(
                    updated_since=last_updated,
                    tickers=tickers,
                    raw=raw
                )
                
                if news_items:
                    print(f"\nReceived {len(news_items)} news items")
                    for item in news_items:
                        self.print_news_item(item)
                    last_updated = int(datetime.now(timezone.utc).timestamp())
                
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nStopping news stream...") 