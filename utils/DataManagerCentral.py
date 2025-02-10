import threading
import time
import logging
from typing import Optional
from benzinga.bz_restAPI import BenzingaNewsRestAPI
from benzinga.bz_websocket import BenzingaNewsWebSocket 
from utils.NewsProcessor import NewsProcessor
from utils.ReturnsProcessor import ReturnsProcessor
from utils.redisClasses import EventTraderRedis, RedisClient
from utils.redis_constants import RedisKeys
from eventtrader.keys import BENZINGANEWS_API_KEY


# Primary Source
news_source = RedisKeys.SOURCE_NEWS

class DataManager:
    def __init__(
        self, 
        date_from: str = "2025-02-06",  # UTC-5 (Before DST)
        date_to: str = "2025-02-07",    # UTC-4 (After DST)
        # date_from="2025-01-31",
        # date_to="2025-02-01",   # changed from "2024-01-07",

        api_key: str = BENZINGANEWS_API_KEY, 
        ttl: int = 7 * 24 * 3600
    ):
        self.running = True

        """Initialize Benzinga News Manager with Redis and API clients"""
        self.ttl = ttl
        self.api_key = api_key
        self.date_from = date_from
        self.date_to = date_to
        
        # Initialize Redis - default: clear_config=False, preserve_processed=True
        self.redis = EventTraderRedis(source=news_source)
        
        # Initialize API clients
        self.rest_client = BenzingaNewsRestAPI(
            api_key=self.api_key,
            redis_client=self.redis.bz_histnews,
            ttl=self.ttl
        )
        
        self.ws_client = BenzingaNewsWebSocket(
            api_key=self.api_key,
            redis_client=self.redis.bz_livenews,
            ttl=self.ttl
        )
        
        # Initialize processors
        self.news_processor = NewsProcessor(self.redis, delete_raw=True)
        self.returns_processor = ReturnsProcessor(self.redis)   # Using same redis instance
        
        # Initialize thread flags
        self.ws_thread = None
        self.news_thread = None
        self.returns_thread = None

    def _run_websocket(self):
        """WebSocket connection loop with auto-reconnect"""
        while self.running:
            try:
                self.ws_client.connect(raw=False)
            except Exception as e:
                logging.error(f"WebSocket error: {e}")
                time.sleep(5)

    def start(self):
        """Start all components: WebSocket, News Processor, and Returns Processor"""
        try:

            # Fetch historical data
            historical_news = self.rest_client.get_historical_data(
                date_from=self.date_from,
                date_to=self.date_to,
                raw=False
            )
            print(f"Fetched {len(historical_news)} historical news items")

            # Start WebSocket
            self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
            self.ws_thread.start()
            
            # Start processors
            self.news_thread = threading.Thread(target=self.news_processor.process_all_news, daemon=True)
            self.returns_thread = threading.Thread(target=self.returns_processor.process_all_returns, daemon=True)
            
            self.news_thread.start()
            self.returns_thread.start()
            
            # Give threads time to initialize
            time.sleep(2)
            
            print("BenzingaNewsManager started successfully")
            return True
            
        except Exception as e:
            logging.error(f"Error starting BenzingaNewsManager: {e}")
            return False

    def check_status(self):
        """Check the status of WebSocket and Redis queues"""
        try:
            ws_status = {
                "connected": self.ws_client.connected,
                "last_message": self.ws_client.stats.get('last_message_time')
            }


            # Get the live prefix from RedisKeys
            live_prefix = RedisKeys.get_prefixes(news_source)['live']


            redis_status = {
                # "live_news_count": len(self.redis.bz_livenews.client.keys('news:benzinga:live:raw:*')),
                "live_news_count": len(self.redis.bz_livenews.client.keys(f"{live_prefix}raw:*")),

                "raw_queue": len(self.redis.bz_livenews.client.lrange(self.redis.bz_livenews.RAW_QUEUE, 0, -1)),
                "processed_queue": len(self.redis.bz_livenews.client.lrange(self.redis.bz_livenews.PROCESSED_QUEUE, 0, -1))
            }
            
            return {"websocket": ws_status, "redis": redis_status}
            
        except Exception as e:
            logging.error(f"Error checking status: {e}")
            return None

    def stop(self):
        """Clean shutdown of all components"""
        try:
            self.running = False  # Set flag to stop the websocket loop
            self.ws_client.disconnect()
            
            # Wait for threads to finish
            if self.ws_thread and self.ws_thread.is_alive():
                self.ws_thread.join(timeout=5)  # Wait up to 5 seconds
                
            if self.news_thread and self.news_thread.is_alive():
                self.news_thread.join(timeout=5)
                
            if self.returns_thread and self.returns_thread.is_alive():
                self.returns_thread.join(timeout=5)
            
            self.redis.clear(preserve_processed=True)
            print("DataManager stopped successfully")
            return True
        
        except Exception as e:
            logging.error(f"Error stopping DataManager: {e}")
            return False                