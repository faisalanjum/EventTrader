
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

class BenzingaNewsRestAPI:
    """Simple class to fetch and print Benzinga news data"""
    
    def __init__(self, api_key: str):
        self.api_url = "https://api.benzinga.com/api/v2/news"
        self.api_key = api_key
        self.headers = {"accept": "application/json"}
        self.MAX_PAGE_LIMIT = 100     # API limit is 100 pages
        self.ITEMS_PER_PAGE = 100     # API's maximum items per page
        self.error_handler = NewsErrorHandler()  # Add error handler

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
            "displayOutput": "full",
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

        # Reset error stats at start of each fetch
        self.error_handler.reset_stats()
        
        all_items = []
        current_page = 0
        total_items_received = 0
        
        # Print initial params once
        print("\nStarting API Request:")
        print(f"- date_from: {date_from}")
        print(f"- date_to: {date_to}")
        print(f"- updated_since: {updated_since}")
        print(f"- tickers: {tickers}")
        
        while current_page < self.MAX_PAGE_LIMIT:
            try:
                params = self._build_params(
                    page=current_page,
                    updated_since=updated_since,
                    date_from=date_from,
                    date_to=date_to,
                    tickers=tickers
                )
                
                # Just print page progress
                print(f"Fetching page {current_page}...", end='\r')
                
                response = requests.get(self.api_url, headers=self.headers, params=params)
                try:
                    response.raise_for_status()
                except requests.exceptions.HTTPError as e:
                    self.error_handler.handle_http_error(e)
                    break
                
                news_items = response.json()
                total_items_received += len(news_items)
                
                # Process items
                current_page_items = []
                for raw_item in news_items:
                    item_id = raw_item.get('id', 'unknown')
                    self.error_handler.handle_news_item(item_id, "received", {})
                    
                    # Use centralized processing
                    processed_item = self.error_handler.process_news_item(raw_item, raw)
                    if processed_item:
                        current_page_items.append(processed_item)
                        self.error_handler.handle_news_item(item_id, "processed", {})
                
                all_items.extend(current_page_items)
                
                # Check pagination using raw response size
                if len(news_items) < self.ITEMS_PER_PAGE:
                    print(f"\nReached end of data at page {current_page}")
                    break
                
                current_page += 1
                
            except json.JSONDecodeError as je:
                self.error_handler.handle_json_error(je, response.text)
                break
            except requests.exceptions.RequestException as e:
                self.error_handler.handle_connection_error(e)
                break
        
        # Clear progress line
        print("\n")
        
        # Print final summary with error stats in both cases
        print("\nFetch Summary:")
        print(f"Pages processed: {current_page + 1}")
        print(f"Total items received: {total_items_received}")
        print(f"Items processed successfully: {len(all_items)}")
        if total_items_received > 0:
            print(f"Success rate: {(len(all_items)/total_items_received)*100:.1f}%")
        else:
            print("Success rate: N/A (no items received)")
        print(self.error_handler.get_summary())
        
        return all_items

    def print_error_stats(self):
        """Print current error statistics"""
        print(self.error_handler.get_summary())

    @staticmethod
    def print_news_item(item: Union[BzRestAPINews, UnifiedNews]):
        """Print news item in appropriate format based on type"""
        if isinstance(item, BzRestAPINews):
            BenzingaNewsRestAPI._print_raw_news(item)
        elif isinstance(item, UnifiedNews):
            BenzingaNewsRestAPI._print_unified_news(item)
        # Remove unreachable else clause


    @staticmethod
    def _print_unified_news(news: UnifiedNews):
        """Print unified news format"""
        news.print()


    @staticmethod
    def _print_raw_news(news: BzRestAPINews):
        """Print raw REST API format"""
        print("\n" + "="*80)
        print(f"ID: {news.id}")
        print(f"Title: {news.title}")
        print(f"Author: {news.author}")
        print(f"Created: {news.created}")
        print(f"Updated: {news.updated}")
        print(f"URL: {news.url}")
        
        # Print all stocks
        stocks = [stock.name for stock in news.stocks] if news.stocks else []
        print(f"\nStocks: {', '.join(stocks)}")
        
        # Print all channels
        channels = [channel.name for channel in news.channels] if news.channels else []
        print(f"Channels: {', '.join(channels)}")
        
        # Print all tags
        tags = [tag.name for tag in news.tags] if news.tags else []
        print(f"Tags: {', '.join(tags)}")
        
        print(f"\nTeaser: {news.teaser}")
        print(f"\nBody: {news.body}")
        
        # Print any additional fields
        if news.image:
            print(f"\nImage: {news.image}")
            
        print("="*80 + "\n")

    def get_historical_data(self,
                           date_from: str,
                           date_to: str,
                           tickers: Optional[List[str]] = None,
                           raw: bool = False) -> List[Union[BzRestAPINews, UnifiedNews]]:
        """Get historical news data between dates"""
        return self._fetch_news(
            date_from=date_from,
            date_to=date_to,
            tickers=tickers,
            raw=raw
        )

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

    # Instead using websocket
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