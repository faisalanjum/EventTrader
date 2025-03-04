from abc import ABC, abstractmethod
import threading
import logging
import json
from typing import Optional, Dict, Any
from utils.redis_constants import RedisKeys
from utils.redisClasses import RedisClient
from utils.EventReturnsManager import EventReturnsManager
from datetime import datetime
import pytz
from dateutil import parser
from utils.metadata_fields import MetadataFields

class BaseProcessor(ABC):
    """Base class for all processors (news, reports, transcripts)"""
    
    def __init__(self, event_trader_redis, delete_raw: bool = True, polygon_subscription_delay: int = None):

        self.polygon_subscription_delay = polygon_subscription_delay

        # Core fields needed across system
        self.REQUIRED_FIELDS = {
            'id',          # Used for unique identification in ReturnsProcessor
            'created',     # Used in EventReturnsManager for timing/returns
            'updated',     # Used in ReturnsProcessor for key generation
            'symbols',     # Used everywhere for symbol processing
            'metadata',    # Added by _add_metadata, used in returns processing
            'returns',     # Added by ReturnsProcessor
            'formType',    # Source-specific but used in filtering/processing
        }



        # Direct copy from NewsProcessor.__init__
        self.live_client = event_trader_redis.live_client
        self.hist_client = event_trader_redis.history_client
        self.queue_client = self.live_client  # Dedicated client for queue operations
        self.should_run = True
        self._lock = threading.Lock()
        self.delete_raw = delete_raw

        # Common initialization
        self.allowed_symbols = {s.strip().upper() for s in event_trader_redis.get_symbols()}
        self.stock_universe = event_trader_redis.get_stock_universe()
        self.source_type = event_trader_redis.source
        
        # Logging setup
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # PubSub channel
        self.processed_channel = RedisKeys.get_pubsub_channel(self.source_type)

        # Get pubsub channel using RedisKeys
        # self.processed_channel = RedisKeys.get_key(
        #     source_type=self.source_type,
        #     key_type=RedisKeys.SUFFIX_PROCESSED,
        #     prefix_type=RedisKeys.PREFIX_LIVE
        # )

    def process_all_items(self):
        """Generic version of process_all_news"""
        self.logger.info(f"Starting processing for {self.source_type} from {self.queue_client.RAW_QUEUE}")
        consecutive_errors = 0

        print(f"\n[Processor Debug] Starting processor")
        print(f"[Processor Debug] Source type: {self.source_type}")
        # print(f"[Processor Debug] Queue client prefix: {self.queue_client.prefix}")
        # print(f"[Processor Debug] Watching queue: {self.queue_client.RAW_QUEUE}")


        while self.should_run:
            try:
                result = self.queue_client.pop_from_queue(self.queue_client.RAW_QUEUE, timeout=1)
                

                if result:
                    print(f"[Processor Debug] Popped item: {result}")
                    pass
                else:
                    print(f"[Processor Debug] No items in queue after timeout")
                    pass


                if not result:
                    continue

                _, raw_key = result
                success = self._process_item(raw_key)
                
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
                consecutive_errors += 1
                if consecutive_errors > 10:
                    self._reconnect()
                    consecutive_errors = 0

    def _process_item(self, raw_key: str) -> bool:
        """Generic version of _process_news_item"""
        try:
            # 1. Initial Setup and Validation
            client = self.hist_client if raw_key.startswith(self.hist_client.prefix) else self.live_client
            prefix_type = RedisKeys.PREFIX_HIST if raw_key.startswith(self.hist_client.prefix) else RedisKeys.PREFIX_LIVE
            identifier = raw_key.split(':')[-1]

            raw_content = client.get(raw_key)
            if not raw_content:
                self.logger.debug(f"Raw content not found: {raw_key}")  # Change from error to debug
                return False

            content_dict = json.loads(raw_content)

            # 2. First standardize fields - Important to do this before checking symbols
            standardized_dict = self._standardize_fields(content_dict)

            # print(f"[^BASE Processor Debug] Standardized dict: {standardized_dict}")

            # 3. Check if any valid symbols exist
            if not self._has_valid_symbols(standardized_dict):
                self.logger.debug(f"Dropping {raw_key} - no matching symbols in universe")
                client.delete(raw_key)
                return True  # Item exits raw queue naturally
                # No tracking maintained, never enters processed queue

            # 4. Clean content - Source specific
            processed_dict = self._clean_content(standardized_dict)
            
            # 5. Filter to keep only valid symbols
            valid_symbols = {s.strip().upper() for s in processed_dict.get('symbols', [])} & self.allowed_symbols
            processed_dict['symbols'] = list(valid_symbols)

            # 6. Add metadata
            metadata = self._add_metadata(processed_dict)
            if metadata is None:
                client.push_to_queue(client.FAILED_QUEUE)
                return False

            # Rest of processing remains the same...

            # Add metadata to processed_dict
            processed_dict['metadata'] = metadata      

            # **********************************************************************
            # Move to processed queue
            # processed_key = raw_key.replace(":raw:", ":processed:")  
            
            # Generate processed key using RedisKeys
            processed_key = RedisKeys.get_key(source_type=self.source_type,key_type=RedisKeys.SUFFIX_PROCESSED, 
                                prefix_type=prefix_type, identifier=identifier)


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


    def _has_valid_symbols(self, content: dict) -> bool:
        """Check if content has valid symbols from universe"""
        try:
            content_symbols = {s.strip().upper() for s in content.get('symbols', [])}
            return bool(content_symbols & self.allowed_symbols)
        except Exception as e:
            self.logger.error(f"Error checking symbols: {e}")
            return False

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
            logging.getLogger(__name__).error(f"Failed to parse timestamp {utc_time_str}: {e}")
            return utc_time_str

    # def _reconnect(self):
    #     """Reconnect to Redis"""
    #     try:
    #         self.live_client = self.live_client.__class__(prefix=self.live_client.prefix)
    #         self.hist_client = self.hist_client.__class__(prefix=self.hist_client.prefix)
    #         self.queue_client = self.live_client
    #     except Exception as e:
    #         self.logger.error(f"Reconnection failed: {e}")

    def _reconnect(self):
        """Reconnect to Redis"""
        try:
            # Store the original configuration before reconnecting
            live_prefix = self.live_client.prefix
            hist_prefix = self.hist_client.prefix
            
            # Store the original queue configurations
            live_raw_queue = self.live_client.RAW_QUEUE if hasattr(self.live_client, 'RAW_QUEUE') else None
            live_processed_queue = self.live_client.PROCESSED_QUEUE if hasattr(self.live_client, 'PROCESSED_QUEUE') else None
            live_failed_queue = self.live_client.FAILED_QUEUE if hasattr(self.live_client, 'FAILED_QUEUE') else None
            
            hist_raw_queue = self.hist_client.RAW_QUEUE if hasattr(self.hist_client, 'RAW_QUEUE') else None
            hist_processed_queue = self.hist_client.PROCESSED_QUEUE if hasattr(self.hist_client, 'PROCESSED_QUEUE') else None
            hist_failed_queue = self.hist_client.FAILED_QUEUE if hasattr(self.hist_client, 'FAILED_QUEUE') else None
            
            # Create new client instances with the same parameters
            self.live_client = RedisClient(
                prefix=live_prefix,
                source_type=self.source_type
            )
            
            self.hist_client = RedisClient(
                prefix=hist_prefix,
                source_type=self.source_type
            )
            
            # Restore queue configurations if they weren't properly set
            if not hasattr(self.live_client, 'RAW_QUEUE') and live_raw_queue:
                self.live_client.RAW_QUEUE = live_raw_queue
                self.live_client.PROCESSED_QUEUE = live_processed_queue
                self.live_client.FAILED_QUEUE = live_failed_queue
                
            if not hasattr(self.hist_client, 'RAW_QUEUE') and hist_raw_queue:
                self.hist_client.RAW_QUEUE = hist_raw_queue
                self.hist_client.PROCESSED_QUEUE = hist_processed_queue
                self.hist_client.FAILED_QUEUE = hist_failed_queue
            
            # Reset queue_client to live_client
            self.queue_client = self.live_client
            
            self.logger.info("Successfully reconnected to Redis clients")
        except Exception as e:
            self.logger.error(f"Reconnection failed: {e}")



    def stop(self):
        """Stop processing"""
        self.should_run = False


    @abstractmethod
    def _standardize_fields(self, content: dict) -> dict:
        """Transform source-specific fields to standard format"""
        pass

    @abstractmethod
    def _clean_content(self, content: dict) -> dict:
        """Source-specific content cleaning"""
        pass


    def _add_metadata(self, processed_dict: dict) -> Optional[dict]:
        """Add metadata including return timing and symbol information"""
        try:
            # Parse event time
            event_time = parser.parse(processed_dict.get('created'))
            symbols = processed_dict.get('symbols', [])
            
            # Use EventReturnsManager to generate metadata - shouldn't we create a Global instance of EventReturnsManager?
            event_manager = EventReturnsManager(self.stock_universe, polygon_subscription_delay=self.polygon_subscription_delay)
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


    def get_etf(self, ticker: str, col='industry_etf'):  # sector_etf, industry_etf        
        """Get sector or industry ETF for a ticker with consistent formatting"""
        ticker = ticker.strip().upper()
        matches = self.stock_universe[self.stock_universe.symbol == ticker]
        if matches.empty:
            raise ValueError(f"Symbol {ticker} not found in stock universe")
        return matches[col].values[0]   