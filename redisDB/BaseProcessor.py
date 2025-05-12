from abc import ABC, abstractmethod
import threading
import logging
import json
import time  # Import time for sleep
from typing import Optional, Dict, Any
from .redis_constants import RedisKeys
from .redisClasses import RedisClient
from eventReturns.EventReturnsManager import EventReturnsManager
from datetime import datetime
import pytz
from dateutil import parser
from utils.metadata_fields import MetadataFields
from config import feature_flags # Add this import

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

        # Conditionally set the queue_client based on the run mode flags
        if feature_flags.ENABLE_LIVE_DATA:
            # Covers live-only and live+historical modes
            self.queue_client = self.live_client
            # Log assignment immediately
            logging.getLogger(__name__).info(f"INITIALIZING {event_trader_redis.source}: ENABLE_LIVE_DATA=True. Assigning live_client.")
        elif feature_flags.ENABLE_HISTORICAL_DATA:
            # Covers historical-only mode
            self.queue_client = self.hist_client
            # Log assignment immediately
            logging.getLogger(__name__).info(f"INITIALIZING {event_trader_redis.source}: ENABLE_LIVE_DATA=False, ENABLE_HISTORICAL_DATA=True. Assigning hist_client.")
        else:
            # Fallback/Error case (shouldn't happen with current run_event_trader logic)
            self.queue_client = self.live_client # Default to live_client
            # Log assignment immediately
            logging.getLogger(__name__).info(f"INITIALIZING {event_trader_redis.source}: Both flags False? Falling back to live_client.")
            
        self._lock = threading.Lock()
        self.delete_raw = delete_raw

        # Common initialization
        self.allowed_symbols = {s.strip().upper() for s in event_trader_redis.get_symbols()}
        self.stock_universe = event_trader_redis.get_stock_universe()
        self.source_type = event_trader_redis.source
        
        # Logging setup using standard logging
        self.logger = logging.getLogger(__name__)
        
        # PubSub channel
        self.processed_channel = RedisKeys.get_pubsub_channel(self.source_type)

        # Get pubsub channel using RedisKeys
        # self.processed_channel = RedisKeys.get_key(
        #     source_type=self.source_type,
        #     key_type=RedisKeys.SUFFIX_PROCESSED,
        #     prefix_type=RedisKeys.PREFIX_LIVE
        # )

        self.should_run = True # Initialize should_run after logger is set

    def process_all_items(self):
        """Generic version of process_all_news"""
        self.logger.info(f"Starting processing for {self.source_type} from {self.queue_client.RAW_QUEUE}")
        consecutive_errors = 0
        last_empty_log_time = 0  # Track last time we logged empty queue

        self.logger.info(f"Starting processor for {self.source_type}, should_run: {self.should_run}")

        while self.should_run:
            try:
                result = self.queue_client.pop_from_queue(self.queue_client.RAW_QUEUE, timeout=1)                

                if result:
                    self.logger.debug(f"[{self.source_type}] -Popped item: {result}")
                    consecutive_errors = 0 # Reset processing error counter on successful pop
                else:
                    # Timeout occurred
                    current_time = int(time.time())
                    if current_time - last_empty_log_time >= 60: # Keep original 60s interval for standard log
                        self.logger.info(f"[{self.source_type}] - No items in queue after timeout")
                        last_empty_log_time = current_time

                if not result:
                    continue

                # Assign raw_key FIRST from the non-None result
                _, raw_key = result
                self.logger.debug(f"[{self.source_type}] - Attempting to process item: {raw_key}")
                success = self._process_item(raw_key)
                self.logger.debug(f"[{self.source_type}] - Finished processing item: {raw_key}, Success: {success}")
                
                if success:
                    consecutive_errors = 0
                else:
                    consecutive_errors += 1
                    if consecutive_errors > 10:  # Reset after too many errors
                        self.logger.error(f"[{self.source_type}] - Too many consecutive errors, reconnecting...")
                        self._reconnect()
                        consecutive_errors = 0
                        last_empty_log_time = 0

            except OSError as io_error:
                # Specific handling for I/O errors
                self.logger.error(f"Redis I/O error: {io_error}")
                time.sleep(1)  # Add sleep on I/O error
                consecutive_errors += 1
                if consecutive_errors > 3:  # Be more aggressive with reconnection for I/O errors
                    self.logger.warning(f"[{self.source_type}] - Multiple I/O errors, reconnecting...")
                    self._reconnect()
                    consecutive_errors = 0
                    last_empty_log_time = 0
            except Exception as e:
                self.logger.error(f"[{self.source_type}] - Processing error: {e}")
                time.sleep(0.5)  # Add sleep to prevent rapid error loops
                consecutive_errors += 1
                if consecutive_errors > 10:
                    self._reconnect()
                    consecutive_errors = 0
                    last_empty_log_time = 0

    def _process_item(self, raw_key: str) -> bool:
        """Generic version of _process_news_item"""
        client = None  # Initialize for exception handling scope
        try:
            # 1. Initial Setup and Validation
            client = self.hist_client if raw_key.startswith(self.hist_client.prefix) else self.live_client
            prefix_type = RedisKeys.PREFIX_HIST if raw_key.startswith(self.hist_client.prefix) else RedisKeys.PREFIX_LIVE
            identifier = raw_key.split(':')[-1]
            meta_key = f"tracking:meta:{self.source_type}:{identifier}"

            raw_content = client.get(raw_key)
            if not raw_content:
                pipe = client.client.pipeline(transaction=True)
                pipe = client.mark_lifecycle_timestamp(meta_key, "failed_at", reason="raw_content_not_found", external_pipe=pipe) or pipe
                if self.delete_raw:
                    pipe.delete(raw_key)
                pipe.execute()
                self.logger.warning(f"Raw content not found: {raw_key}")
                return False

            content_dict = json.loads(raw_content)

            # 2. First standardize fields - Important to do this before checking symbols
            standardized_dict = self._standardize_fields(content_dict)

            # 3. Check if any valid symbols exist
            if not self._has_valid_symbols(standardized_dict):
                pipe = client.client.pipeline(transaction=True)
                pipe = client.mark_lifecycle_timestamp(meta_key, "filtered_at", reason="no_valid_symbols", external_pipe=pipe) or pipe
                if self.delete_raw:
                    pipe.delete(raw_key)
                pipe.execute()
                self.logger.info(f"Dropping {raw_key} - no matching symbols in universe")
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
                pipe = client.client.pipeline(transaction=True)
                pipe.lpush(client.FAILED_QUEUE, raw_key)
                pipe = client.mark_lifecycle_timestamp(meta_key, "failed_at", reason="metadata_generation_failed", external_pipe=pipe) or pipe
                if self.delete_raw:
                    pipe.delete(raw_key)
                pipe.execute()
                self.logger.error(f"Metadata generation failed for {raw_key}. Pushing to FAILED_QUEUE.")
                return False

            # Add metadata to processed_dict
            processed_dict['metadata'] = metadata      

            # For processed_key (data key), ALL sources use their full identifier from the raw key
            processed_key = RedisKeys.get_key(source_type=self.source_type, key_type=RedisKeys.SUFFIX_PROCESSED, 
                                prefix_type=prefix_type, identifier=identifier)

            # If processed already exists, just delete raw if needed
            if client.get(processed_key):
                if self.delete_raw:
                    pipe = client.client.pipeline(transaction=True)
                    pipe.delete(raw_key)
                    pipe.execute()
                return True

            # Not processed yet, check queue and process
            queue_items = client.client.lrange(client.PROCESSED_QUEUE, 0, -1)
            if processed_key not in queue_items:  # Only add if not already in queue
                pipe = client.client.pipeline(transaction=True)
                if self.ttl:
                    pipe.set(processed_key, json.dumps(processed_dict), ex=self.ttl)
                else:
                    pipe.set(processed_key, json.dumps(processed_dict))
                pipe.lpush(client.PROCESSED_QUEUE, processed_key)

                try:
                    pipe.publish(self.processed_channel, processed_key)
                except Exception as e:
                    self.logger.error(f"Failed to publish message: {e}")

                pipe = client.mark_lifecycle_timestamp(meta_key, "processed_at", ttl=self.ttl if self.ttl else None, external_pipe=pipe) or pipe
                
                if self.delete_raw:
                    pipe.delete(raw_key)
                
                success = all(pipe.execute())
                return success
            return True  # Already in queue

        except Exception as e:
            self.logger.error(f"Failed to process {raw_key}: {e}")
            final_client = self.hist_client if raw_key.startswith(self.hist_client.prefix) else self.live_client # Use client if available, otherwise fallback
            if final_client:
                pipe = final_client.client.pipeline(transaction=True)
                pipe.lpush(final_client.FAILED_QUEUE, raw_key)
                pipe = final_client.mark_lifecycle_timestamp(meta_key, "failed_at", reason="Exception in _process_item", external_pipe=pipe) or pipe
                if self.delete_raw and client:
                    pipe.delete(raw_key)
                pipe.execute()
            elif self.delete_raw and not client:
                self.logger.warning(f"Could not delete raw_key {raw_key} after failure.")
            
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
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to parse timestamp {utc_time_str}: {e}")
            return utc_time_str




    def _reconnect(self):
        """Reconnect to Redis"""
        try:
            # Store the original configuration before reconnecting
            live_prefix = self.live_client.prefix
            hist_prefix = self.hist_client.prefix

            # # Store the original queue configurations
            # live_raw_queue = self.live_client.RAW_QUEUE if hasattr(self.live_client, 'RAW_QUEUE') else None
            # live_processed_queue = self.live_client.PROCESSED_QUEUE if hasattr(self.live_client, 'PROCESSED_QUEUE') else None
            # live_failed_queue = self.live_client.FAILED_QUEUE if hasattr(self.live_client, 'FAILED_QUEUE') else None
            
            # hist_raw_queue = self.hist_client.RAW_QUEUE if hasattr(self.hist_client, 'RAW_QUEUE') else None
            # hist_processed_queue = self.hist_client.PROCESSED_QUEUE if hasattr(self.hist_client, 'PROCESSED_QUEUE') else None
            # hist_failed_queue = self.hist_client.FAILED_QUEUE if hasattr(self.hist_client, 'FAILED_QUEUE') else None

            # Store the original queue configurations
            live_raw_queue = self.live_client.RAW_QUEUE
            live_processed_queue = self.live_client.PROCESSED_QUEUE
            live_failed_queue = self.live_client.FAILED_QUEUE
            
            hist_raw_queue = self.hist_client.RAW_QUEUE
            hist_processed_queue = self.hist_client.PROCESSED_QUEUE
            hist_failed_queue = self.hist_client.FAILED_QUEUE
            
            # Create new client instances with the same parameters
            self.live_client = RedisClient(
                prefix=live_prefix,
                source_type=self.source_type
            )
            
            self.hist_client = RedisClient(
                prefix=hist_prefix,
                source_type=self.source_type
            )


            # # Restore queue configurations if they weren't properly set
            # if not hasattr(self.live_client, 'RAW_QUEUE') and live_raw_queue:
            #     self.live_client.RAW_QUEUE = live_raw_queue
            #     self.live_client.PROCESSED_QUEUE = live_processed_queue
            #     self.live_client.FAILED_QUEUE = live_failed_queue
                
            # if not hasattr(self.hist_client, 'RAW_QUEUE') and hist_raw_queue:
            #     self.hist_client.RAW_QUEUE = hist_raw_queue
            #     self.hist_client.PROCESSED_QUEUE = hist_processed_queue
            #     self.hist_client.FAILED_QUEUE = hist_failed_queue

            # Always restore queue configurations - no conditional checks
            self.live_client.RAW_QUEUE = live_raw_queue
            self.live_client.PROCESSED_QUEUE = live_processed_queue
            self.live_client.FAILED_QUEUE = live_failed_queue
            
            self.hist_client.RAW_QUEUE = hist_raw_queue
            self.hist_client.PROCESSED_QUEUE = hist_processed_queue
            self.hist_client.FAILED_QUEUE = hist_failed_queue
            
            # Re-assign queue_client based on the current feature flags
            # (Mirrors the logic in __init__)
            if feature_flags.ENABLE_LIVE_DATA:
                self.queue_client = self.live_client
                self.logger.info("RECONNECT: Assigning live_client based on feature flags.")
            elif feature_flags.ENABLE_HISTORICAL_DATA:
                self.queue_client = self.hist_client
                self.logger.info("RECONNECT: Assigning hist_client based on feature flags.")
            else:
                self.queue_client = self.live_client # Fallback
                self.logger.warning("RECONNECT: Both feature flags false? Defaulting queue_client to live_client.")
            
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
                self.logger.error(f"Failed to generate metadata for: {processed_dict}")
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
            self.logger.error(f"Metadata generation failed: {e} for: {processed_dict}")
            return None


    def get_etf(self, ticker: str, col='industry_etf'):  # sector_etf, industry_etf        
        """Get sector or industry ETF for a ticker with consistent formatting"""
        ticker = ticker.strip().upper()
        matches = self.stock_universe[self.stock_universe.symbol == ticker]
        if matches.empty:
            raise ValueError(f"Symbol {ticker} not found in stock universe")
        return matches[col].values[0]   