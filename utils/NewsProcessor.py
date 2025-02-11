# news_processor.py
import html
import threading
import logging
from typing import Optional
import pandas as pd
from bs4 import BeautifulSoup
import re
from benzinga.bz_news_schemas import UnifiedNews
from utils.EventReturnsManager import EventReturnsManager
from utils.redisClasses import RedisClient
import json
from utils.redisClasses import EventTraderRedis
import time
import unicodedata
from datetime import datetime
import pytz
from dateutil import parser

from eventtrader.keys import POLYGON_API_KEY
from utils.polygonClass import Polygon
from utils.market_session import MarketSessionClassifier
from datetime import timedelta
from utils.EventReturnsManager import EventReturnsManager
from utils.metadata_fields import MetadataFields
from utils.redis_constants import RedisKeys  


 # Using any client for shared queues

class NewsProcessor:
    def __init__(self, event_trader_redis: EventTraderRedis, delete_raw: bool = True):
                
        self.live_client = event_trader_redis.live_client
        self.hist_client = event_trader_redis.history_client
        self.queue_client = self.live_client  # Dedicated client for queue operations
        self.should_run = True
        self._lock = threading.Lock()
        self.delete_raw = delete_raw

        # Cache the allowed symbols list as a set for O(1) lookups
        self.allowed_symbols = {s.strip().upper() for s in event_trader_redis.get_symbols()}

        # Cache the stock universe as a DataFrame for O(1) lookups
        self.stock_universe = event_trader_redis.get_stock_universe()

        self.market_session = MarketSessionClassifier()
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)


        self.source_type = event_trader_redis.source
        
        # Get pubsub channel using RedisKeys
        self.processed_channel = RedisKeys.get_key(
            source_type=self.source_type,
            key_type=RedisKeys.SUFFIX_PROCESSED,
            prefix_type=RedisKeys.PREFIX_LIVE
        )

    def process_all_news(self):
        """Continuously process news from RAW_QUEUE"""
        self.logger.info(f"Starting news processing from {self.queue_client.RAW_QUEUE}")
        consecutive_errors = 0
        while self.should_run:
            try:
                result = self.queue_client.pop_from_queue(self.queue_client.RAW_QUEUE, timeout=1)
                if not result:
                    continue

                _, raw_key = result
                success = self._process_news_item(raw_key)
                if success:
                    consecutive_errors = 0
                else:
                    consecutive_errors += 1

                    
                    if consecutive_errors > 10:  # Reset after too many errors
                        self.logger.error("Too many consecutive errors, reconnecting...")
                        self._reconnect()
                        consecutive_errors = 0

            except Exception as e:
                self.logger.error(f"Processing error: {e}")
                time.sleep(1)
                consecutive_errors += 1

    def _reconnect(self):
        """Reconnect to Redis"""
        try:
            self.live_client = self.live_client.__class__(
                prefix=self.live_client.prefix
            )
            self.hist_client = self.hist_client.__class__(
                prefix=self.hist_client.prefix
            )
            self.queue_client = self.live_client
        except Exception as e:
            self.logger.error(f"Reconnection failed: {e}")

    def _process_news_item(self, raw_key: str) -> bool:
        try:

            # 1. Initial Setup and Validation
            # client = (self.hist_client if ':hist:' in raw_key else self.live_client)         # Instead of searching for hist/live in the key, is there a better way?    
            client = self.hist_client if raw_key.startswith(self.hist_client.prefix) else self.live_client
            raw_content = client.get(raw_key)
            if not raw_content:
                self.logger.error(f"Raw content not found: {raw_key}")
                return False

            news_dict = json.loads(raw_content)

            # 2. Check if any valid symbols exist
            if not self._has_valid_symbols(news_dict):
                self.logger.debug(f"Dropping {raw_key} - no matching symbols in universe")
                client.delete(raw_key)  # Delete news item from "raw" storage (hist/live)
                return True  # Item exits raw queue naturally
                # No tracking maintained, never enters processed queue

            # 3. Clean news content - If we get here, at least one valid symbol exists
            processed_dict = self._clean_news(news_dict)
            
            # 4. Filter to keep only valid symbols
            valid_symbols = {s.strip().upper() for s in processed_dict.get('symbols', [])} & self.allowed_symbols
            processed_dict['symbols'] = list(valid_symbols)

            # **********************************************************************
            # Get Metadata- Needs to be changed - properly formatted metadata
            metadata = self._add_metadata(processed_dict)
            if metadata is None:                
                client.push_to_queue(client.FAILED_QUEUE)
                return False

            # Add metadata to processed_dict
            processed_dict['metadata'] = metadata      

            # **********************************************************************
            # Move to processed queue
            processed_key = raw_key.replace(":raw:", ":processed:")  # Maybe later use RedisKeys 
            pipe = client.client.pipeline(transaction=True)

            # If processed exists, just delete raw if needed
            if client.get(processed_key):
                if self.delete_raw:
                    pipe.delete(raw_key)
                    return all(pipe.execute())
                return True

            # Not processed yet, check queue and process
            queue_items = client.client.lrange(client.PROCESSED_QUEUE, 0, -1)
            if processed_key not in queue_items:  # Only add if not already in queue
                pipe.set(processed_key, json.dumps(processed_dict))
                pipe.lpush(client.PROCESSED_QUEUE, processed_key)

                try:
                    pipe.publish(self.processed_channel, processed_key)
                    # self.logger.info(f"Published processed message: {processed_key}")
                except Exception as e:
                    self.logger.error(f"Failed to publish message: {e}")

                if self.delete_raw:
                    pipe.delete(raw_key)
                return all(pipe.execute())
            return True  # Already in queue

        except Exception as e:
            self.logger.error(f"Failed to process {raw_key}: {e}")
            # client = (self.hist_client if ':hist:' in raw_key else self.live_client)
            client = self.hist_client if raw_key.startswith(self.hist_client.prefix) else self.live_client
            client.push_to_queue(client.FAILED_QUEUE, raw_key)
            return False



    def _add_metadata(self, processed_dict: dict) -> Optional[dict]:
        """Add metadata including return timing and symbol information"""
        try:
            # Parse event time
            event_time = parser.parse(processed_dict.get('created'))
            symbols = processed_dict.get('symbols', [])
            
            # Use EventReturnsManager to generate metadata - shouldn't we create a Global instance of EventReturnsManager?
            event_manager = EventReturnsManager(self.stock_universe)
            metadata = event_manager.process_event_metadata(
                event_time=event_time,
                symbols=symbols
            )
            
            if metadata is None:
                self.logger.info(f"Failed to generate metadata for: {processed_dict}")
                return None
            
            # Validate metadata structure
            required_fields = [
                MetadataFields.EVENT,
                MetadataFields.RETURNS_SCHEDULE,
                MetadataFields.INSTRUMENTS
            ]
            
            if not all(field in metadata['metadata'] for field in required_fields):
                self.logger.error(f"Missing required metadata fields in: {metadata}")
                return None
                
            return metadata['metadata']

        except Exception as e:
            self.logger.info(f"Metadata generation failed: {e} for: {processed_dict}")
            return None


            # The metadata structure is now:
            # {
            #     'metadata': {
            #         'event': {'market_session': '...', 'created': '...'},
            #         'returns_schedule': {'hourly': '...', 'session': '...', 'daily': '...'},
            #         'instruments': [{'symbol': '...', 'benchmarks': {'sector': '...', 'industry': '...'}}]
            #     }
            # }

    # def _add_metadata(self, processed_dict: dict) -> Optional[dict]:

    #     try:
    #         metadata = {'timeforReturns': {}, 'metadata': {}, 'symbolsData': []}

    #         created = processed_dict.get('created')
            
    #         market_session = self.market_session.get_market_session(created)
    #         end_time = self.market_session.get_end_time(created)
    #         interval_start_time = self.market_session.get_interval_start_time(created)     

    #         # This is Incorrect - look at the function where we calcute returns for interval start and end_time                   
    #         interval_end_time = interval_start_time + timedelta(minutes=60) # One hour
            
    #         one_day_impact_times = self.market_session.get_1d_impact_times(created)
    #         oneday_impact_end_time = one_day_impact_times[1]
            
    #         # Required to check if time for returns calculation 
    #         metadata['timeforReturns'].update({
    #             '1h_end_time': interval_end_time.isoformat(),
    #             'session_end_time': end_time.isoformat(),
    #             '1d_end_time': oneday_impact_end_time.isoformat()                                
    #         })

    #         # metadata (to be stored in Neo4j): - Add more metadata as needed
    #         metadata['metadata'].update({'market_session': market_session,})

    #         for symbol in processed_dict.get('symbols', []):
    #             symbol = symbol.strip().upper()
    #             sector_etf = self.get_etf(symbol, 'sector_etf')
    #             industry_etf = self.get_etf(symbol, 'industry_etf')
                                
    #             metadata['symbolsData'].append({ 'symbol': symbol, 'sector_etf': sector_etf, 'industry_etf': industry_etf})


    #         return metadata
                
    #     except Exception as e:
    #         self.logger.error(f"Returns calculation failed: {e} for: {processed_dict}")
    #         return None



    def _clean_news(self, news: dict) -> dict:
        """Clean news content.
        
        Process order:
        1. Clean text content (title, teaser, body)
        2. Convert timestamps to Eastern
        3. Limit body word count
        
        Args:
            news (dict): Raw news dictionary
        Returns:
            dict: Processed news dictionary
        """
        try:
            cleaned = news.copy()

            # 1. Clean text content
            for field in ['title', 'teaser', 'body']:
                if field in cleaned:
                    cleaned[field] = self._clean_content(cleaned[field])

            # 2. Convert timestamps
            for field in ['created', 'updated']:
                if field in cleaned:
                    cleaned[field] = self.convert_to_eastern(cleaned[field])

            # 3. Apply word limit on body
            cleaned = self._limit_body_word_count(cleaned)

            return cleaned
            
        except Exception as e:
            self.logger.error(f"Error in _clean_news: {e}")
            return news  # Return original if cleaning fails



    @staticmethod
    def convert_to_eastern(utc_time_str: str) -> str:
        """Convert UTC ISO 8601 timestamp to US/Eastern timezone.
        
        Args:
            utc_time_str: ISO 8601 string (handles both "+00:00" and "Z" formats)
        Returns:
            str: Eastern timezone ISO 8601 string
        """
        try:
            utc_time = parser.isoparse(utc_time_str)
            eastern_zone = pytz.timezone("America/New_York")
            eastern_time = utc_time.astimezone(eastern_zone)
            return eastern_time.isoformat()
        except Exception as e:
            # self.logger.error(f"Failed to parse timestamp {utc_time_str}: {e}")
            logging.getLogger(__name__).error(f"Failed to parse timestamp {utc_time_str}: {e}")  # ✅ Use global logger
            return utc_time_str



    def _clean_content(self, content: str) -> str:
        """Clean individual text content"""
        if content is None or not isinstance(content, str):
            return content

        if content.startswith(('http://', 'https://', '/')):
            return content
                
        try:
            cleaned_text = BeautifulSoup(content, 'html.parser').get_text(' ')
            
            # Convert HTML entities like &quot; to "
            cleaned_text = html.unescape(cleaned_text)

            # Detect if content is code (basic heuristic)
            is_code = re.search(r"def |print\(|\{.*?\}|=", cleaned_text)

            # Normalize Unicode (fix \u201c, \u201d, etc.) ONLY if it's not code
            if not is_code:
                cleaned_text = unicodedata.normalize("NFKC", cleaned_text)

            cleaned_text = cleaned_text.replace('\xa0', ' ')
            cleaned_text = re.sub(r'\s+([.,;?!])', r'\1', cleaned_text)
            cleaned_text = re.sub(r'([.,;?!])\s+', r'\1 ', cleaned_text)
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
            return cleaned_text.strip()
        except Exception as e:
            self.logger.error(f"Error cleaning content: {e}")
            return content  # Return original if cleaning fails
        


    def _limit_body_word_count(self, news: dict, max_words: int = 3000) -> dict:
        """Limit word count of the 'body' key in the news dictionary.
        
        Args:
            news (dict): The news dictionary
            max_words (int): Maximum allowed words in the 'body' field (default: 800)
        
        Returns:
            dict: News dictionary with truncated 'body' if necessary
        """
        try:
            if 'body' not in news or not isinstance(news['body'], str):
                self.logger.info(f"Body not found in news: {news}")
                return news
            
            words = [w for w in news['body'].split() if w.strip()]
            
            if len(words) <= max_words:  # Skip processing if already within limit
                self.logger.debug(f"Body already within limit: {len(words)} words")
                return news
            
            news['body'] = ' '.join(words[:max_words]).strip() + "..."
            self.logger.debug(f"Truncated body from {len(words)} to {max_words} words")
            
            return news
        
        except Exception as e:
            self.logger.error(f"Error limiting body word count: {e}")
            return news  # Return original if processing fails


    def _has_valid_symbols(self, news: dict) -> bool:
        """Check if news item has at least one valid symbol from stock universe."""
        try:
            news_symbols = {s.strip().upper() for s in news.get('symbols', [])}
            return bool(news_symbols & self.allowed_symbols)  # Set intersection
        except Exception as e:
            self.logger.error(f"Error checking symbols: {e}")
            return False


    def stop(self):
        """Stop processing"""
        self.should_run = False        


    def get_etf(self, ticker: str, col='industry_etf'):  # sector_etf, industry_etf        
        """Get sector or industry ETF for a ticker with consistent formatting"""
        ticker = ticker.strip().upper()
        matches = self.stock_universe[self.stock_universe.symbol == ticker]
        if matches.empty:
            raise ValueError(f"Symbol {ticker} not found in stock universe")
        return matches[col].values[0]   