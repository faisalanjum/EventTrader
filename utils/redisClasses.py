from pydantic import ValidationError
import redis
import logging
import json
import pandas as pd
from io import StringIO
import os
from datetime import datetime
from typing import List, Optional
from benzinga.bz_news_schemas import UnifiedNews
from datetime import timezone
import time
from utils.redis_constants import RedisKeys

# Create logs directory if it doesn't exist
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO, # for production, use INFO, DEBUG for development
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, f"redis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")),
        logging.StreamHandler()
    ]
)


# preserve_processed=True by default to maintain both historical and live processed news between runs,
# preventing duplicate processing while allowing new incoming news (both historical and live) to be 
# checked against existing processed entries

class EventTraderRedis:

    def __init__(self, clear_config=False, preserve_processed=True, source=RedisKeys.SOURCE_NEWS):
        self.source = source
        self.bz_livenews = RedisClient(prefix=RedisKeys.get_prefixes(self.source)['live'])
        self.bz_histnews = RedisClient(prefix=RedisKeys.get_prefixes(self.source)['hist'])
        self.config = RedisClient(prefix='config:')
        
        self.clear(preserve_processed)
        self.initialize_stock_universe(clear_config=clear_config)


    def initialize_stock_universe(self, clear_config=False, file_path='../StocksUniverse/final_symbols.csv'):
        try:
            if clear_config:
                self.config.clear()
                
            df = pd.read_csv(file_path)
            logging.info(f"Successfully read CSV with {len(df)} rows")
            
            df['symbol'] = df['symbol'].astype(str).str.strip()
            df = df[df['symbol'].str.lower() != 'nan']
            df = df[df['symbol'].str.len() > 0]
            df = df.drop_duplicates(subset=['symbol'])
            
            symbols = sorted(df['symbol'].unique().tolist())  # Define symbols here
            
            # Use config: prefix consistently
            universe_success = self.config.set('config:stock_universe', df.to_json())
            symbols_success = self.config.set('config:symbols', ','.join(symbols))
            
            # Update verification keys too
            verify_universe = self.config.get('config:stock_universe')
            verify_symbols = self.config.get('config:symbols')
            
            if not (verify_universe and verify_symbols):
                logging.error("Failed to verify config storage")
                return False
                
            logging.info(f"Successfully initialized stock universe with {len(symbols)} symbols")
            return True
            
        except Exception as e:
            logging.error(f"Error initializing stock universe: {e}")
            return False


    def get_symbols(self):
        symbols_str = self.config.get('config:symbols')  # Match the prefix
        return symbols_str.split(',') if symbols_str else []

    def get_stock_universe(self):
        universe_json = self.config.get('config:stock_universe')  # Match the prefix
        return pd.read_json(StringIO(universe_json)) if universe_json else None

    def clear(self, preserve_processed=True): 
        try:
            self.bz_livenews.clear(preserve_processed) # If True, Only clear raw keys, not processed keys else clear all keys
            self.bz_histnews.clear(preserve_processed)
            return True
        except Exception as e:
            logging.error(f"Error during clear: {e}")
            return False

class RedisClient:
    # Queue names (shared between live and hist)
    # RAW_QUEUE = "news:benzinga:raw:queue"     
    # PROCESSED_QUEUE = "news:benzinga:processed:queue"
    # FAILED_QUEUE = "news:benzinga:failed:queue"

    # Queue names organized under queues/ directory
    RAW_QUEUE = "news:benzinga:queues:raw"     
    PROCESSED_QUEUE = "news:benzinga:queues:processed"
    FAILED_QUEUE = "news:benzinga:queues:failed"    

    def __init__(self, host='localhost', port=6379, db=0, prefix=''):
        self.host = host
        self.port = port
        self.db = db
        self.prefix = prefix  # Will be 'news:benzinga:live:' or 'news:benzinga:hist:'

        self.pool = redis.ConnectionPool( host=host, port=port, db=db, decode_responses=True)
        self._connect_to_redis()

    def _connect_to_redis(self):
        max_retries = 10
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                self.client = redis.Redis(connection_pool=self.pool)
                self.client.ping()
                logging.info(f"Connected to Redis (prefix={self.prefix})")
                return
            except redis.ConnectionError as e:
                if attempt == max_retries - 1:
                    logging.error(f"Failed to connect to Redis after {max_retries} attempts")
                    raise
                logging.warning(f"Redis connection attempt {attempt + 1} failed, retrying...")
                time.sleep(retry_delay)



    def create_new_connection(self):
        """Creates a new Redis client with same configuration"""
        return redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            decode_responses=True
        )

    # Used in bz_websocket.py
    def set_news(self, news_item: UnifiedNews, ex=None):
        """For live news ingestion from WebSocket"""
        try:
            # Replace colons in updated timestamp with dots
            updated_key = news_item.updated.replace(':', '.')

            # Checks if the news item is already in the processed queue to avoid duplicates
            processed_key = f"{self.prefix}processed:{news_item.id}.{updated_key}"            
            if processed_key in self.client.lrange(self.PROCESSED_QUEUE, 0, -1):
                logging.info(f"Skipping duplicate news (WebSocket): {processed_key}")
                return True

            # Store as news:benzinga:live:raw:{id}:{updated}
            storage_key = f"{self.prefix}raw:{news_item.id}.{updated_key}"
            
            pipe = self.client.pipeline(transaction=True)
            pipe.set(storage_key, news_item.model_dump_json(), ex=ex) # stores the news content in Redis
            pipe.lpush(self.RAW_QUEUE, storage_key) 
            return all(pipe.execute())
                
        except Exception as e:
            logging.error(f"Live news storage failed: {e}")
            return False

    def set_news_batch(self, news_items: List[UnifiedNews], ex=None):
        """For historical news ingestion"""
        try:
        
            # Get processed queue items once for efficiency since will compare with each newsitem to avoid duplicates
            processed_items = self.client.lrange(self.PROCESSED_QUEUE, 0, -1)

            pipe = self.client.pipeline(transaction=True)
            
            for item in news_items:
                # Replace colons in updated timestamp with dots
                updated_key = item.updated.replace(':', '.')
                processed_key = f"{self.prefix}processed:{item.id}.{updated_key}"

                # Skip if already in processed queue
                if processed_key in processed_items:
                    logging.info(f"Skipping duplicate news (RestAPI): {processed_key}")
                    continue

                storage_key = f"{self.prefix}raw:{item.id}.{updated_key}"
                pipe.set(storage_key, item.model_dump_json(), ex=ex)
                pipe.lpush(self.RAW_QUEUE, storage_key)
            
            return all(pipe.execute())
        except Exception as e:
            logging.error(f"Historical news batch storage failed: {e}")
            return False

    def get(self, key: str) -> Optional[str]:
        try:
            return self.client.get(key)
        except Exception as e:
            logging.error(f"Get failed for key {key}: {e}")
            return None

    def set(self, key: str, value: str, ex=None) -> bool:
        try:
            return bool(self.client.set(key, value, ex=ex))
        except Exception as e:
            logging.error(f"Set failed for key {key}: {e}")
            return False

    def push_to_queue(self, queue_name: str, value: str) -> bool:
        """Push to queue"""
        try:
            return bool(self.client.lpush(queue_name, value))
        except Exception as e:
            logging.error(f"Queue push failed: {e}")
            return False

    def pop_from_queue(self, queue_name: str, timeout: int = 1) -> Optional[tuple]:
        """Pop from queue with timeout"""
        try:
            return self.client.brpop(queue_name, timeout)
        except Exception as e:
            logging.error(f"Queue pop failed: {e}")
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
            logging.error(f"Clear failed: {e}")
            return False
        
    def set_json(self, key: str, value: dict) -> bool:
        """Store JSON data in Redis"""
        try:
            return self.client.set(key, json.dumps(value))
        except Exception as e:
            logging.error(f"Error storing JSON in Redis: {e}")
            return False
            
    def get_json(self, key: str) -> dict:
        """Retrieve JSON data from Redis"""
        try:
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logging.error(f"Error retrieving JSON from Redis: {e}")
            return None        
            
    def delete(self, key: str) -> bool:
        """Delete a key from Redis"""
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logging.error(f"Delete failed for key {key}: {e}")
            return False
        

    def get_queue_length(self, queue_name: str) -> int:
        """Get the length of a queue"""
        try:
            return self.client.llen(queue_name)
        except Exception as e:
            logging.error(f"Error getting queue length for {queue_name}: {e}")
            return 0
        

    def create_pubsub_connection(self):
        """Creates a new Redis pubsub connection"""
        return redis.Redis(host=self.host, 
                           port=self.port, 
                           db=self.db, 
                           decode_responses=True).pubsub()        