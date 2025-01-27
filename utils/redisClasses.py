import redis
import logging
import json
import pandas as pd
from io import StringIO
import os
from datetime import datetime
from typing import List
from benzinga.bz_news_schemas import UnifiedNews


# Create logs directory if it doesn't exist
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Create a log filename with timestamp
log_filename = os.path.join(log_dir, f"redis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()  # This will output to console as well
    ]
)


class EventTraderRedis:
    def __init__(self):
        # Benzinga data sources with distinct prefixes
        self.bz_livenews = RedisClient(prefix='news:benzinga:live:')
        self.bz_histnews = RedisClient(prefix='news:benzinga:hist:')

        # Add config client for stock universe
        self.config = RedisClient(prefix='config:')

        # Other data types
        self.trades = RedisClient(prefix='trades:')
        self.users = RedisClient(prefix='users:')

        # Initialize stock universe on startup
        self.initialize_stock_universe()


    def initialize_stock_universe(self, file_path='../StocksUniverse/final_symbols_filtered.csv'):
        """Initialize stock universe from CSV if not in Redis"""
        logging.info("Attempting to initialize stock universe")
        
        try:
            # Read CSV
            df = pd.read_csv(file_path)
            logging.info(f"Successfully read CSV with {len(df)} rows")
            
            # Convert symbols to strings and clean any whitespace
            df['symbol'] = df['symbol'].astype(str).str.strip()
            
            # Remove any 'nan' or empty values
            df = df[df['symbol'].str.lower() != 'nan']
            df = df[df['symbol'].str.len() > 0]
            
            # Remove duplicates
            df = df.drop_duplicates(subset=['symbol'])
            logging.info(f"After cleaning and removing duplicates: {len(df)} rows")
            
            # Store the entire DataFrame as JSON
            universe_success = self.config.set('stock_universe', df.to_json())
            logging.info(f"Stored stock universe in Redis. Success: {universe_success}")
            
            # Store symbols as comma-separated string
            symbols = sorted(df['symbol'].unique().tolist())  # Sort for consistency
            symbols_str = ','.join(symbols)
            symbols_success = self.config.set('symbols', symbols_str)
            logging.info(f"Stored {len(symbols)} unique symbols in Redis. Success: {symbols_success}")
            
            # Verify both were stored
            stored_universe = self.config.get('stock_universe')
            stored_symbols = self.config.get('symbols')
            logging.info(f"Verification - Universe exists: {bool(stored_universe)}, Symbols exist: {bool(stored_symbols)}")
            
        except FileNotFoundError:
            logging.error(f"Stock universe file not found: {file_path}")
            raise
        except Exception as e:
            logging.error(f"Error initializing stock universe: {e}")
            raise

    def get_symbols(self):
        """Get just the list of stock symbols"""
        symbols_str = self.config.get('symbols')
        logging.info(f"Retrieved symbols string from Redis: {symbols_str}")
        return symbols_str.split(',') if symbols_str else []

    def get_stock_universe(self):
        """Get the full stock universe DataFrame"""
        universe_json = self.config.get('stock_universe')
        if universe_json:
            return pd.read_json(StringIO(universe_json))
        return None

    def get_stock_info(self, symbol):
        """Get information for a specific stock"""
        df = self.get_stock_universe()
        if df is not None:
            stock_info = df[df['symbol'] == symbol]
            return stock_info.to_dict('records')[0] if not stock_info.empty else None
        return None



    def clear(self):
        """Clear all Redis databases for all clients or individual redis.bz_livenews.clear()"""
        clients = [
            self.bz_livenews,
            self.bz_histnews,
            # Add other clients here as you add them
        ]
        
        for client in clients:
            client.clear()



class RedisClient:
    def __init__(self, host='localhost', port=6379, db=0, prefix=''):
        """Initialize Redis client with optional prefix for key namespacing"""
        self.prefix = prefix
        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True
            )
            self.client.ping()
            logging.info("Connected to Redis")
        except redis.ConnectionError as e:
            logging.error(f"Redis connection failed: {e}")
            raise


    def set_news(self, news_item: UnifiedNews, ex=None):
        """Store single unified news item"""
        try:
            key = f"{self.prefix}{news_item.id}"
            json_str = news_item.model_dump_json()
            return self.client.set(key, json_str, ex=ex)
        except Exception as e:
            logging.error(f"Failed to store news item: {e}")
            return False

    def set_news_batch(self, news_items: List[UnifiedNews], ex=None):
        """Store batch of unified news items"""
        pipe = self.client.pipeline(transaction=True)
        try:
            for item in news_items:
                pipe.set(f"{self.prefix}{item.id}", 
                        item.model_dump_json(), 
                        ex=ex)
            return pipe.execute()
        except Exception as e:
            logging.error(f"Failed to store batch: {e}")
            return False

    def set(self, key, value, ex=None):
        """Set key-value pair with optional expiration in seconds"""
        key = f"{self.prefix}{key}" if self.prefix else key
        return self.client.set(key, value, ex=ex)

    def get(self, key):
        """Get value by key"""
        key = f"{self.prefix}{key}" if self.prefix else key
        return self.client.get(key)

    def delete(self, key):
        """Delete a key"""
        key = f"{self.prefix}{key}" if self.prefix else key
        return self.client.delete(key)

    def clear(self):
        """Clear current database"""
        return self.client.flushdb()

    def _connect_to_redis(self):
        """Establish a connection to the Redis server."""
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True
            )
            self.client.ping()
            logging.info(f"Connected to Redis (db={self.db})")
        except redis.ConnectionError as e:
            logging.error(f"Redis connection failed: {e}")
            raise

    def switch_database(self, db):
        """
        Switch to a different Redis logical database.

        :param db: Database index to switch to.
        """
        logging.info(f"Switching to Redis database: db={db}")
        self.db = db
        self._connect_to_redis()

    def clear_database(self, flush_all=False):
        """
        Clear the Redis database.

        :param flush_all: If True, flushes all databases. Defaults to False (current database only).
        """
        try:
            if flush_all:
                self.client.flushall()
                logging.info("All Redis databases cleared.")
            else:
                self.client.flushdb()
                logging.info("Current Redis database cleared.")
        except Exception as e:
            logging.error(f"Error clearing database: {e}")
