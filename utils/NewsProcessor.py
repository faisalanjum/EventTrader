# news_processor.py
import html
import threading
import logging
from typing import Optional
import pandas as pd
from bs4 import BeautifulSoup
import re
from benzinga.bz_news_schemas import UnifiedNews
from utils.redisClasses import RedisClient
import json
from utils.redisClasses import EventTraderRedis
import time
import unicodedata
from datetime import datetime
import pytz
from dateutil import parser

 # Using any client for shared queues

class NewsProcessor:
    def __init__(self, event_trader_redis: EventTraderRedis, delete_raw: bool = True):
                
        self.redis_client = event_trader_redis.bz_livenews
        self.hist_client = event_trader_redis.bz_histnews
        self.queue_client = self.redis_client  # Dedicated client for queue operations
        self.should_run = True
        self._lock = threading.Lock()
        self.delete_raw = delete_raw

        # Cache the allowed symbols list as a set for O(1) lookups
        self.allowed_symbols = {s.strip().upper() for s in event_trader_redis.get_symbols()}

    def process_all_news(self):
        """Continuously process news from RAW_QUEUE"""
        logging.info(f"Starting news processing from {RedisClient.RAW_QUEUE}")
        consecutive_errors = 0
        while self.should_run:
            try:
                result = self.queue_client.pop_from_queue(RedisClient.RAW_QUEUE, timeout=1)
                if not result:
                    continue

                _, raw_key = result
                success = self._process_news_item(raw_key)
                if success:
                    consecutive_errors = 0
                else:
                    consecutive_errors += 1
                    if consecutive_errors > 10:  # Reset after too many errors
                        logging.error("Too many consecutive errors, reconnecting...")
                        self._reconnect()
                        consecutive_errors = 0

            except Exception as e:
                logging.error(f"Processing error: {e}")
                time.sleep(1)
                consecutive_errors += 1

    def _reconnect(self):
        """Reconnect to Redis"""
        try:
            self.redis_client = self.redis_client.__class__(
                prefix=self.redis_client.prefix
            )
            self.hist_client = self.hist_client.__class__(
                prefix=self.hist_client.prefix
            )
            self.queue_client = self.redis_client
        except Exception as e:
            logging.error(f"Reconnection failed: {e}")

    def _process_news_item(self, raw_key: str) -> bool:
        try:
            client = (self.hist_client if ':hist:' in raw_key else self.redis_client)
            
            raw_content = client.get(raw_key)
            if not raw_content:
                logging.error(f"Raw content not found: {raw_key}")
                return False

            news_dict = json.loads(raw_content)

            # Check if news has valid symbols
            if not self._has_valid_symbols(news_dict):
                logging.debug(f"Dropping {raw_key} - no matching symbols in universe")
                client.delete(raw_key)  # Delete invalid item from raw storage
                return True  # Continue processing without error


            processed_dict = self._clean_news(news_dict)
            
            processed_key = raw_key.replace(":raw:", ":processed:")            
            pipe = client.client.pipeline(transaction=True)

            # If processed exists, just delete raw if needed
            if client.get(processed_key):
                if self.delete_raw:
                    pipe.delete(raw_key)
                    return all(pipe.execute())
                return True

            # Not processed yet, check queue and process
            queue_items = client.client.lrange(RedisClient.PROCESSED_QUEUE, 0, -1)
            if processed_key not in queue_items:  # Only add if not already in queue
                pipe.set(processed_key, json.dumps(processed_dict))
                pipe.lpush(RedisClient.PROCESSED_QUEUE, processed_key)
                if self.delete_raw:
                    pipe.delete(raw_key)
                return all(pipe.execute())
            return True  # Already in queue

        except Exception as e:
            logging.error(f"Failed to process {raw_key}: {e}")
            client = (self.hist_client if ':hist:' in raw_key else self.redis_client)
            client.push_to_queue(RedisClient.FAILED_QUEUE, raw_key)
            return False

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
            logging.error(f"Error in _clean_news: {e}")
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
            logging.error(f"Failed to parse timestamp {utc_time_str}: {e}")
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
            logging.error(f"Error cleaning content: {e}")
            return content  # Return original if cleaning fails
        


    def _limit_body_word_count(self, news: dict, max_words: int = 1000) -> dict:
        """Limit word count of the 'body' key in the news dictionary.
        
        Args:
            news (dict): The news dictionary
            max_words (int): Maximum allowed words in the 'body' field (default: 800)
        
        Returns:
            dict: News dictionary with truncated 'body' if necessary
        """
        try:
            if 'body' not in news or not isinstance(news['body'], str):
                return news
            
            words = [w for w in news['body'].split() if w.strip()]
            
            if len(words) <= max_words:  # Skip processing if already within limit
                return news
            
            news['body'] = ' '.join(words[:max_words]).strip() + "..."
            logging.debug(f"Truncated body from {len(words)} to {max_words} words")
            
            return news
        
        except Exception as e:
            logging.error(f"Error limiting body word count: {e}")
            return news  # Return original if processing fails


    def _has_valid_symbols(self, news: dict) -> bool:
        """Check if news item has at least one valid symbol from stock universe."""
        try:
            news_symbols = {s.strip().upper() for s in news.get('symbols', [])}
            return bool(news_symbols & self.allowed_symbols)  # Set intersection
        except Exception as e:
            logging.error(f"Error checking symbols: {e}")
            return False


    def stop(self):
        """Stop processing"""
        self.should_run = False        