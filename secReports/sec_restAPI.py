from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time
import json
import logging
import backoff
import requests
from redisDB.redisClasses import RedisClient, EventTraderRedis
from .sec_errors import FilingErrorHandler
from config.feature_flags import VALID_FORM_TYPES
from sec_api import QueryApi
from utils.log_config import get_logger, setup_logging

class SECRestAPI:
    """REST API client for historical SEC filing data"""
    
    def __init__(self, api_key: str, redis: EventTraderRedis, ttl: int = 7*24*3600):
        """Initialize the REST API client"""
        self.api_key = api_key
        self.redis = redis
        self.redis_client = redis.history_client
        self.ttl = ttl
        self.error_handler = FilingErrorHandler()
        self.query_api = QueryApi(api_key=api_key)
        self.logger = get_logger("sec_rest_api")  # Add centralized logger
        
        # API Limits
        self.MAX_QUERY_LENGTH = 3500  # Maximum query string length
        self.MAX_PAGE_SIZE = 50      # Maximum results per page
        self.MAX_RESULTS = 10000     # Maximum total results per query
        self.RATE_LIMIT_DELAY = 0.1  # 100ms between requests
        self.MAX_RETRIES = 3
        self.RETRY_DELAY = 1  # Start with 1 second
        self.MAX_RETRY_DELAY = 10  # Max backoff of 10 seconds

        # Stats tracking (match WebSocket stats)
        self.stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'queries_made': 0,
            'filings_found': 0,
            'tickers_processed': 0,
            'errors': 0,
            'pagination_limits_hit': 0
        }

    @backoff.on_exception(
        backoff.expo,
        (
            requests.exceptions.RequestException,  # Base class for all requests exceptions
            requests.exceptions.HTTPError,         # Handles 429 Too Many Requests
            requests.exceptions.Timeout,           # Handles timeouts
            requests.exceptions.ConnectionError    # Handles connection issues
        ),
        max_tries=3,
        max_time=30,
        base=2,
        factor=1,
        jitter=None,
        # We'll get the logger dynamically inside the method to avoid using root logger
        logger=None
    )

    def get_historical_data(self, date_from: str, date_to: str, raw: bool = False) -> List[Dict]:
        """Get historical SEC filings data between dates"""
        # Local import to avoid module-level dependencies
        from config.feature_flags import ENABLE_HISTORICAL_DATA
        
        # Check feature flag
        if not ENABLE_HISTORICAL_DATA:
            self.logger.info("SEC historical data ingestion disabled by feature flag")
            return []
        
        try:
            admin_client = RedisClient(prefix='admin:')
            symbols_str = admin_client.get('admin:tradable_universe:symbols')
            tickers = symbols_str.split(',') if symbols_str else []
            total_tickers = len(tickers)
            
            self.logger.info(f"Fetching SEC filings from {date_from} to {date_to} for {total_tickers} tickers")
            
            processed_filings = []
            for ticker in tickers:
                try:
                    ticker_filings = self._process_ticker(ticker, date_from, date_to, raw)
                    processed_filings.extend(ticker_filings)
                    
                    self.stats['tickers_processed'] += 1
                    if self.stats['tickers_processed'] % 10 == 0:
                        self._log_stats()
                        
                except Exception as e:
                    self.stats['errors'] += 1
                    self.logger.error(f"Error processing ticker {ticker}: {str(e)}")
                    continue
                
                time.sleep(self.RATE_LIMIT_DELAY)
            
            # --- Fetch Complete Signal --- Start
            try:
                batch_id = f"reports:{date_from}-{date_to}"
                self.redis_client.set(f"batch:{batch_id}:fetch_complete", "1", ex=86400)
                self.logger.info(f"Set fetch_complete flag for batch: {batch_id}")
            except Exception as e:
                self.logger.error(f"Failed to set fetch_complete flag for reports batch {batch_id}: {e}")
            # --- Fetch Complete Signal --- End
            
            self._log_stats()
            return processed_filings
            
        except Exception as e:
            self.logger.error(f"Error in get_historical_data: {str(e)}")
            return []


    def _process_ticker(self, ticker: str, date_from: str, date_to: str, raw: bool) -> List[Dict]:
        ticker_filings = []
        
        for form_type in VALID_FORM_TYPES:
            try:
                filings = self._fetch_filings(ticker, form_type, date_from, date_to)
                
                # Process each filing (matching WebSocket pattern)
                for filing in filings:
                    self.stats['messages_received'] += 1
                    self.logger.info(f"\nProcessing filing #{self.stats['messages_received']}")
                    self.logger.info(f"Form Type: {filing.get('formType')}")
                    self.logger.info(f"Accession No: {filing.get('accessionNo')}")
                    
                    # First process to unified format
                    unified_filing = self.error_handler.process_filing(filing, raw=False)
                    if unified_filing:
                        self.logger.info("✅ Successfully created UnifiedReport")
                        
                        # Store in Redis
                        if self.redis_client.set_filing(unified_filing, ex=self.ttl):
                            self.logger.info("✅ Successfully stored in Redis")
                            
                            # Handle raw display if needed
                            if raw:
                                display_filing = self.error_handler.process_filing(filing, raw=True)
                                if display_filing:
                                    display_filing.print()
                                    ticker_filings.append(display_filing)
                            else:
                                unified_filing.print()
                                ticker_filings.append(unified_filing)
                                
                            self.stats['messages_processed'] += 1
                        else:
                            self.logger.error("❌ Failed to store in Redis")
                    else:
                        self.logger.error("❌ Failed to create UnifiedReport")
                        self.logger.error(f"Original filing data: {json.dumps(filing, indent=2)}")
                
                if len(filings) >= self.MAX_RESULTS:
                    self.stats['pagination_limits_hit'] += 1
                    self.logger.warning(
                        f"Retrieved maximum {self.MAX_RESULTS} filings for "
                        f"{ticker} {form_type} from {date_from} to {date_to}"
                    )
                
            except Exception as e:
                self.stats['errors'] += 1
                self.logger.error(f"Error processing {ticker} {form_type}: {str(e)}")
                continue
                
            time.sleep(self.RATE_LIMIT_DELAY)
        
        return ticker_filings

    def _fetch_filings(self, ticker: str, form_type: str, 
                            date_from: str, date_to: str) -> List[Dict]:
        all_filings = []
        from_index = 0
        
        while True:
            try:
                search_query = (
                    f'ticker:{ticker} AND '
                    f'formType:"{form_type}" AND '
                    f'filedAt:[{date_from} TO {date_to}]'
                )
                
                if len(search_query) > self.MAX_QUERY_LENGTH:
                    self.logger.error(f"Query too long for {ticker} {form_type}")
                    break
                
                parameters = {
                    "query": search_query,
                    "from": str(from_index),
                    "size": str(self.MAX_PAGE_SIZE),
                    "sort": [{"filedAt": {"order": "desc"}}]
                }
                
                self.stats['queries_made'] += 1
                
                # Get response data
                response_data = self.query_api.get_filings(parameters)
                
                # Check total results
                if 'total' in response_data:
                    total = response_data['total']
                    if total.get('relation') == 'gte' and total.get('value', 0) >= self.MAX_RESULTS:
                        self.logger.warning(f"Query for {ticker} {form_type} has more than {self.MAX_RESULTS} results")
                        self.stats['pagination_limits_hit'] += 1
                
                # Get filings array
                filings = response_data.get('filings', [])
                if not filings:
                    break
                    
                # Process valid filings
                self.stats['filings_found'] += len(filings)
                all_filings.extend(filings)
                
                # Check pagination
                from_index += len(filings)
                if from_index >= self.MAX_RESULTS or len(filings) < self.MAX_PAGE_SIZE:
                    break
                    
            except Exception as e:
                self.stats['errors'] += 1
                self.logger.error(f"Error fetching {ticker} {form_type} at index {from_index}: {str(e)}")
                break
                
            time.sleep(self.RATE_LIMIT_DELAY)
            
        return all_filings

    def _log_stats(self):
        """Log current processing statistics"""
        self.logger.info("\nSEC REST API Statistics:")
        self.logger.info(f"Tickers Processed: {self.stats['tickers_processed']}")
        self.logger.info(f"Messages Received: {self.stats['messages_received']}")
        self.logger.info(f"Messages Processed: {self.stats['messages_processed']}")
        self.logger.info(f"Queries Made: {self.stats['queries_made']}")
        self.logger.info(f"Filings Found: {self.stats['filings_found']}")
        self.logger.info(f"Pagination Limits Hit: {self.stats['pagination_limits_hit']}")
        self.logger.info(f"Errors: {self.stats['errors']}")