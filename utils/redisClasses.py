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

# Create logs directory if it doesn't exist
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, f"redis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")),
        logging.StreamHandler()
    ]
)

class EventTraderRedis:

    def __init__(self, clear_config=False):
        self.bz_livenews = RedisClient(prefix='news:benzinga:live:')
        self.bz_histnews = RedisClient(prefix='news:benzinga:hist:')
        self.config = RedisClient(prefix='config:')
        
        self.clear()
        self.initialize_stock_universe(clear_config=clear_config)



    def initialize_stock_universe(self, clear_config=False, file_path='../StocksUniverse/final_symbols_filtered.csv'):
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

    def clear(self):
        try:
            self.bz_livenews.clear()
            self.bz_histnews.clear()
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

        self.pool = redis.ConnectionPool(
        host=host, 
        port=port, 
        db=db,
        decode_responses=True)

        self._connect_to_redis()

    def _connect_to_redis(self):
        max_retries = 3
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

    def set_news(self, news_item: UnifiedNews, ex=None):
        """For live news ingestion from WebSocket"""
        try:
            # Store as news:benzinga:live:raw:{id}:{updated}
            storage_key = f"{self.prefix}raw:{news_item.id}:{news_item.updated}"
            
            pipe = self.client.pipeline(transaction=True)
            pipe.set(storage_key, news_item.model_dump_json(), ex=ex)
            pipe.lpush(self.RAW_QUEUE, storage_key)
            return all(pipe.execute())
                
        except Exception as e:
            logging.error(f"Live news storage failed: {e}")
            return False

    def set_news_batch(self, news_items: List[UnifiedNews], ex=None):
        """For historical news ingestion"""
        try:
            pipe = self.client.pipeline(transaction=True)
            
            for item in news_items:
                storage_key = f"{self.prefix}raw:{item.id}:{item.updated}"
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

    def clear(self):
        """Clear all keys with prefix"""
        try:
            pattern = f"{self.prefix}*" if self.prefix else "*"
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
            
