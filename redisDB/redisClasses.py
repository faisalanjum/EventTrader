from pydantic import ValidationError
import redis
import logging
import json
import pandas as pd
from io import StringIO
import os
from datetime import datetime
from typing import List, Optional, Union
from benzinga.bz_news_schemas import UnifiedNews
from datetime import timezone
import time
from .redis_constants import RedisKeys, RedisQueues
from secReports.sec_schemas import SECFilingSchema, UnifiedReport
# Import feature flags to get the CSV path
from config import feature_flags

# Use standard module logger
logger = logging.getLogger(__name__)

# preserve_processed=True by default to maintain both historical and live processed news between runs,
# preventing duplicate processing while allowing new incoming news (both historical and live) to be 
# checked against existing processed entries

class EventTraderRedis:

    def __init__(self, source=RedisKeys.SOURCE_NEWS, clear_config=False, preserve_processed=True):
        self.source = source
        prefixes = RedisKeys.get_prefixes(self.source) # {'live': 'news:live:', 'hist': 'news:hist:'}
        self.logger = logging.getLogger(f"{self.__class__.__name__}.{source}")
        
        # Initialize Redis clients with source-specific prefixes
        self.live_client = RedisClient(
            prefix=prefixes['live'],
            source_type=self.source
        )
        self.history_client = RedisClient(
            prefix=prefixes['hist'],
            source_type=self.source)
        
        self.config = RedisClient(prefix='admin:')
        
        self.clear(preserve_processed)
        self.initialize_stock_universe(clear_config=clear_config)



    def initialize_stock_universe(self, clear_config=False, file_path=None):
        """Initialize stock universe from CSV file"""
        try:
            if clear_config:
                self.config.clear()
            
            # Construct path to file in the correct location
            # Use the path defined directly in feature_flags
            file_path = feature_flags.SYMBOLS_CSV_PATH
            # if file_path is None:
            #     project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            #     # Change path for loading symbols CSV
            #     file_path = os.path.join(project_root, 'config', 'final_symbols.csv')
            
            self.logger.info(f"Loading stock universe from: {file_path}")
            df = pd.read_csv(file_path)
            self.logger.info(f"Successfully read CSV with {len(df)} rows")
            
            df['symbol'] = df['symbol'].astype(str).str.strip()
            df = df[df['symbol'].str.lower() != 'nan']
            df = df[df['symbol'].str.len() > 0]
            df = df.drop_duplicates(subset=['symbol'])
            
            symbols = sorted(df['symbol'].unique().tolist())  # Define symbols here
            
            # Use self.config directly since it now has admin: prefix
            universe_success = self.config.set('admin:tradable_universe:stock_universe', df.to_json())
            symbols_success = self.config.set('admin:tradable_universe:symbols', ','.join(symbols))
            
            # Update verification keys too
            verify_universe = self.config.get('admin:tradable_universe:stock_universe')
            verify_symbols = self.config.get('admin:tradable_universe:symbols')
                
            if not (verify_universe and verify_symbols):
                self.logger.error("Failed to verify config storage")
                return False
                
            self.logger.info(f"Successfully initialized stock universe with {len(symbols)} symbols")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing stock universe: {e}", exc_info=True)
            return False


    def get_symbols(self):
        symbols_str = self.config.get('admin:tradable_universe:symbols')
        return symbols_str.split(',') if symbols_str else []

    def get_stock_universe(self):
        universe_json = self.config.get('admin:tradable_universe:stock_universe')
        return pd.read_json(StringIO(universe_json)) if universe_json else None

    def clear(self, preserve_processed=True): 
        try:
            self.live_client.clear(preserve_processed)
            self.history_client.clear(preserve_processed)
            return True
        except Exception as e:
            self.logger.error(f"Error during clear: {e}", exc_info=True)
            return False

class RedisClient:
    # Queue names (shared between live and hist)
    # RAW_QUEUE = "news:raw:queue"     
    # PROCESSED_QUEUE = "news:processed:queue"
    # FAILED_QUEUE = "news:failed:queue"

    # Queue names organized under queues/ directory
    # RAW_QUEUE = "news:queues:raw"     
    # PROCESSED_QUEUE = "news:queues:processed"
    # FAILED_QUEUE = "news:queues:failed"    

    # Redis connection settings
    REDIS_CONN_SETTINGS = {
        'socket_keepalive': True,
        'socket_timeout': 30.0,          # Increased from 15.0 to allow more time for operations
        'socket_connect_timeout': 5.0,   # Increased from 3.0 for more reliable connections
        'health_check_interval': 60,
        'retry_on_timeout': True         # Added to automatically retry on timeout errors
    }

    def __init__(self, host='localhost', port=6379, db=0, prefix='', source_type=None):

        self.host = host
        self.port = port
        self.db = db
        self.prefix = prefix  # Will be 'news:live:' or 'news:hist:'
        self.source_type = source_type  # Needed later for lifecycle meta-key construction
        self.logger = logging.getLogger(f"{self.__class__.__name__}.{prefix or 'admin'}")

        # Get source-specific queue names
        if source_type:
            queues = RedisQueues.get_queues(source_type) # {'RAW_QUEUE': 'news:queues:raw', 'PROCESSED_QUEUE': 'news:queues:processed'
            self.RAW_QUEUE = queues['RAW_QUEUE']
            self.PROCESSED_QUEUE = queues['PROCESSED_QUEUE']
            self.FAILED_QUEUE = queues['FAILED_QUEUE']


        self.pool = redis.ConnectionPool(
            host=host, 
            port=port, 
            db=db, 
            decode_responses=True,
            **self.REDIS_CONN_SETTINGS
        )
        self._connect_to_redis()

    def _connect_to_redis(self):
        max_retries = 10
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                self.client = redis.Redis(connection_pool=self.pool)
                self.client.ping()
                self.logger.info(f"Connected to Redis (prefix={self.prefix})")
                return
            except redis.ConnectionError as e:
                if attempt == max_retries - 1:
                    self.logger.error(f"Failed to connect to Redis after {max_retries} attempts", exc_info=True)
                    raise
                self.logger.warning(f"Redis connection attempt {attempt + 1} failed, retrying...")
                time.sleep(retry_delay)



    def create_new_connection(self):
        """Creates a new Redis client with same configuration"""
        return redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            decode_responses=True,
            **self.REDIS_CONN_SETTINGS
        )

    # Used in bz_websocket.py
    def set_news(self, news_item: UnifiedNews, ex: int = None) -> bool: 
        """For live news ingestion from WebSocket"""
        try:
            # Replace colons in updated timestamp with dots
            updated_key = news_item.updated.replace(':', '.')

            # Checks if the news item is already in the processed queue to avoid duplicates
            processed_key = f"{self.prefix}processed:{news_item.id}.{updated_key}"            
            if processed_key in self.client.lrange(self.PROCESSED_QUEUE, 0, -1):
                # self.logger.info(f"Skipping duplicate news (WebSocket): {processed_key}")
                return False

            # Store as news:live:raw:{id}:{updated}
            storage_key = f"{self.prefix}raw:{news_item.id}.{updated_key}"
            updated_key_safe = news_item.updated.replace(':', '.') if news_item.updated else ''
            meta_key = f"tracking:meta:{self.source_type}:{news_item.id}.{updated_key_safe}"
            
            # Create a single atomic pipeline for all operations
            pipe = self.client.pipeline(transaction=True)
            pipe.set(storage_key, news_item.model_dump_json(), ex=ex)  # store content
            pipe.lpush(self.RAW_QUEUE, storage_key)
            
            # Add tracking to the same pipeline
            pipe = self.mark_lifecycle_timestamp(meta_key, "ingested_at", ttl=ex if ex else None, external_pipe=pipe) or pipe
            if hasattr(news_item, 'updated') and news_item.updated:
                pipe = self.set_lifecycle_data(meta_key, "source_api_timestamp", news_item.updated, ttl=ex if ex else None, external_pipe=pipe) or pipe
            
            # Execute all operations atomically
            success = all(pipe.execute())
            return success
                
        except Exception as e:
            self.logger.error(f"Live news storage failed: {e}", exc_info=True)
            return False


    def set_filing(self, filing: UnifiedReport, ex: int = None) -> bool:
        """Store SEC filing with proper namespace handling"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                filed_at = filing.filedAt.replace(':', '.') # 2025-02-13T08:07:15-05:00 -> 2025-02-13T08.07.15-05.00

                # Check processed queue for duplicates
                processed_key = f"{self.prefix}processed:{filing.accessionNo}.{filed_at}"
                processed_items = self.client.lrange(self.PROCESSED_QUEUE, 0, -1)
            
                if processed_key in processed_items:
                    self.logger.info(f"Skipping duplicate filing: {processed_key}")
                    return False  # ✅ Clearly indicates "not processed"
                
                storage_key = f"{self.prefix}raw:{filing.accessionNo}.{filed_at}"
                meta_key = f"tracking:meta:{self.source_type}:{filing.accessionNo}.{filed_at}"   

                # Create a single atomic pipeline for all operations
                pipe = self.client.pipeline(transaction=True)
                
                # 1. Store the filing content in raw namespace
                pipe.set(storage_key, filing.model_dump_json(), ex=ex)
                
                # 2. Add to RAW_QUEUE
                pipe.lpush(self.RAW_QUEUE, storage_key)

                # Add tracking to the same pipeline
                pipe = self.mark_lifecycle_timestamp(meta_key, "ingested_at", ttl=ex if ex else None, external_pipe=pipe) or pipe
                if hasattr(filing, 'filedAt') and filing.filedAt:
                    pipe = self.set_lifecycle_data(meta_key, "source_api_timestamp", filing.filedAt, ttl=ex, external_pipe=pipe) or pipe
                
                success = all(pipe.execute())

                # If it fails, it will return False - so not store in rawqueue - 
                # for meta tracking - not track pre-RAW_QUEUE rejections
                return success
                    
            except Exception as e:
                self.logger.error(f"Filing storage attempt {attempt+1}/{max_retries} failed: {e}", exc_info=True)
                if attempt < max_retries - 1:
                    # Try to reconnect on connection errors
                    try:
                        self.client = redis.Redis(connection_pool=self.pool)
                    except:
                        pass
                    time.sleep(1)  # Wait before retry
                else:
                    self.logger.error(f"Filing storage failed after {max_retries} attempts")
                    return False
                
        return False  # Should never reach here, but just in case


    def set_news_batch(self, news_items: List[UnifiedNews], ex=None):
        """For historical news ingestion (batch mode)"""
        try:
            processed_items = set(self.client.lrange(self.PROCESSED_QUEUE, 0, -1))
            pipe = self.client.pipeline(transaction=True)
            
            total_items = 0
            skipped_items = 0

            for item in news_items:
                updated_key = item.updated.replace(':', '.') if item.updated else ''
                processed_key = f"{self.prefix}processed:{item.id}.{updated_key}"

                if processed_key in processed_items:
                    self.logger.info(f"Skipping duplicate news (RestAPI): {processed_key}")
                    skipped_items += 1
                    continue

                total_items += 1
                storage_key = f"{self.prefix}raw:{item.id}.{updated_key}"
                meta_key = f"tracking:meta:{self.source_type}:{item.id}.{updated_key}"

                pipe.set(storage_key, item.model_dump_json(), ex=ex)
                pipe.lpush(self.RAW_QUEUE, storage_key)

                pipe = self.mark_lifecycle_timestamp(meta_key, "ingested_at", ttl=ex if ex else None, external_pipe=pipe) or pipe
                if item.updated:
                    pipe = self.set_lifecycle_data(meta_key, "source_api_timestamp", item.updated, ttl=ex if ex else None, external_pipe=pipe) or pipe

            # Only execute if we have operations in the pipeline
            if total_items > 0:
                results = pipe.execute()
                self.logger.info(f"Batch news ingestion: {total_items} items processed, {skipped_items} items skipped")
                return all(results)
            else:
                self.logger.info(f"Batch news ingestion: No items to process, {skipped_items} items skipped")
                return True

        except Exception as e:
            self.logger.error(f"Historical news batch storage failed: {e}", exc_info=True)
            return False

    def get(self, key: str) -> Optional[str]:
        try:
            return self.client.get(key)
        except Exception as e:
            self.logger.error(f"Get failed for key {key}: {e}", exc_info=True)
            return None

    def set(self, key: str, value: str, ex=None) -> bool:
        try:
            return bool(self.client.set(key, value, ex=ex))
        except Exception as e:
            self.logger.error(f"Set failed for key {key}: {e}", exc_info=True)
            return False

    def push_to_queue(self, queue_name: str, value: str) -> bool:
        """Push to queue"""
        try:
            return bool(self.client.lpush(queue_name, value))
        except Exception as e:
            self.logger.error(f"Queue push failed: {e}", exc_info=True)
            return False

    def pop_from_queue(self, queue_name: str, timeout: int = 1) -> Optional[tuple]:
        """Pop from queue with timeout"""
        try:
            return self.client.brpop(queue_name, timeout)
        except Exception as e:
            self.logger.error(f"Queue pop failed: {e}", exc_info=True)
            return None

    def clear(self, preserve_processed=True):  # Same default as EventTraderRedis
        """Clear keys with prefix, optionally preserving processed news"""
        try:
            if preserve_processed:
                pattern = f"{self.prefix}raw:*"  # Only clear raw keys
            else:
                pattern = f"{self.prefix}*" if self.prefix else "*"  # Clear all keys
                
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return True
        except Exception as e:
            self.logger.error(f"Clear failed: {e}", exc_info=True)
            return False
        
    def set_json(self, key: str, value: dict) -> bool:
        """Store JSON data in Redis"""
        try:
            return self.client.set(key, json.dumps(value))
        except Exception as e:
            self.logger.error(f"Error storing JSON in Redis: {e}", exc_info=True)
            return False
            
    def get_json(self, key: str) -> dict:
        """Retrieve JSON data from Redis"""
        try:
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            self.logger.error(f"Error retrieving JSON from Redis: {e}", exc_info=True)
            return None        
            
    def delete(self, key: str) -> bool:
        """Delete a key from Redis"""
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            self.logger.error(f"Delete failed for key {key}: {e}", exc_info=True)
            return False
        
    def batch_delete_keys(self, keys: list) -> int:
        """
        Delete multiple keys from Redis in a single operation
        
        Args:
            keys: List of keys to delete
            
        Returns:
            int: Number of keys that were actually deleted
        """
        if not keys or len(keys) == 0:
            return 0
            
        try:
            # Redis DEL command can take multiple keys at once
            result = self.client.delete(*keys)
            return result
        except Exception as e:
            self.logger.error(f"Batch delete failed: {e}", exc_info=True)
            return 0

    def get_queue_length(self, queue_name: str) -> int:
        """Get the length of a queue"""
        try:
            return self.client.llen(queue_name)
        except Exception as e:
            self.logger.error(f"Error getting queue length for {queue_name}: {e}", exc_info=True)
            return 0
        

    def create_pubsub_connection(self):
        """Creates a new Redis pubsub connection"""
        return redis.Redis(host=self.host, 
                           port=self.port, 
                           db=self.db, 
                           decode_responses=True).pubsub()        





    # ------------------------------------------------------------------
    # Lifecycle tracking helper
    # ------------------------------------------------------------------
    def mark_lifecycle_timestamp(self, key: str, field: str, reason: str = None, ttl: int = None, external_pipe=None):
        """Write a timestamp into a lifecycle hash if not already set"""
        try:
            if not self.client.hexists(key, field):
                payload = {field: datetime.now(timezone.utc).isoformat(timespec="seconds")}
                if reason:
                    payload[f"{field}_reason"] = reason
                    
                pipe = external_pipe or self.client.pipeline()
                pipe.hset(key, mapping=payload)
                if ttl:
                    pipe.expire(key, ttl)

                # ------------------------------------------------------------------
                # Pending-set maintenance (minimalistic)
                # ------------------------------------------------------------------
                # Determine source_type (second element after 'tracking:meta')
                parts = key.split(":")
                if len(parts) >= 3:
                    source_type = parts[2]
                    pending_set_key = f"tracking:pending:{source_type}"

                    # 1) When item is first ingested → add to pending set
                    if field == "ingested_at":
                        pipe.sadd(pending_set_key, key)

                    # 2) Remove from pending set when item is finalised (success or dropped)
                    if field in {"inserted_into_neo4j_at", "filtered_at", "failed_at"} and feature_flags.REMOVE_FROM_PENDING_SET:
                        pipe.srem(pending_set_key, key)

                if not external_pipe:
                    pipe.execute()
                    return True

            # return pipe if external_pipe else None
            return external_pipe if external_pipe else None

        except Exception as e:
            self.logger.error(f"Lifecycle timestamp update failed for {key}:{field}: {e}", exc_info=True)
            # return pipe if external_pipe else None
            return external_pipe if external_pipe else None


    def set_lifecycle_data(self, key: str, field: str, value: str, ttl: int = None, external_pipe=None):
        """Set a specific field with a value in a lifecycle hash if not already set."""
        try:
            if not self.client.hexists(key, field):
                if field == "source_api_timestamp" and value:
                    dt = pd.to_datetime(value, utc=True)
                    value = dt.isoformat(timespec="seconds")

                pipe = external_pipe or self.client.pipeline()
                pipe.hset(key, field, value)
                if ttl: # Ensure key expiration is also set/updated
                    pipe.expire(key, ttl)
                if not external_pipe:
                    pipe.execute()
                    return True
            # return pipe if external_pipe else None
            return external_pipe if external_pipe else None
        except Exception as e:
            self.logger.error(f"Lifecycle data set failed for {key}:{field}: {e}", exc_info=True)
            # return pipe if external_pipe else None
            return external_pipe if external_pipe else None
