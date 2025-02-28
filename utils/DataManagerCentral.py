import threading
import logging
import time
from typing import Dict, Optional
from datetime import datetime

from utils.redisClasses import EventTraderRedis, RedisKeys

from benzinga.bz_restAPI import BenzingaNewsRestAPI
from benzinga.bz_websocket import BenzingaNewsWebSocket


from utils.NewsProcessor import NewsProcessor
from utils.ReportProcessor import ReportProcessor
from utils.ReturnsProcessor import ReturnsProcessor

from eventtrader.keys import BENZINGANEWS_API_KEY
from eventtrader.keys import SEC_API_KEY


# Change these to absolute imports
import sys
sys.path.append('/Users/macowne/Desktop/Faisal/EventTrader')  # Add project root to path

from SEC_API_Files.sec_websocket import SECWebSocket
from SEC_API_Files.sec_restAPI import SECRestAPI



class DataSourceManager:
    """Base class for managing different data sources"""
    def __init__(
        self,
        source_type: str,
        historical_range: Dict[str, str],  # {'from': 'YYYY-MM-DD', 'to': 'YYYY-MM-DD'}
        api_key: str,
        processor_class=None,
        ttl: int = 7 * 24 * 3600
    ):
        self.source_type = source_type
        self.api_key = api_key
        self.ttl = ttl
        self.date_range = historical_range
        self.running = True

        # Initialize Redis and processors
        self.redis = EventTraderRedis(source=self.source_type)        # ex: source_type = news:benzinga
        # self.processor = NewsProcessor(self.redis, delete_raw=True)
        

        print(f"[Manager Debug] Initializing {source_type} manager")
        print(f"[Manager Debug] Processor class: {processor_class}")

        self.processor = processor_class(self.redis, delete_raw=True,) if processor_class else None

        print(f"[Manager Debug] Processor initialized: {self.processor is not None}")

        self.returns_processor = ReturnsProcessor(self.redis)
        
        # Thread management
        self.ws_thread = None
        self.processor_thread = None
        self.returns_thread = None

    def start(self): raise NotImplementedError
    def check_status(self): raise NotImplementedError
    def stop(self): raise NotImplementedError


class BenzingaNewsManager(DataSourceManager):
    """Manager for Benzinga news source"""
    def __init__(self, historical_range: Dict[str, str]):
        super().__init__(
            source_type=RedisKeys.SOURCE_NEWS,
            historical_range=historical_range,
            api_key=BENZINGANEWS_API_KEY,
            processor_class=NewsProcessor
        )
        
        # Initialize API clients
        self.rest_client = BenzingaNewsRestAPI(
            api_key=self.api_key,
            redis_client=self.redis.history_client,
            ttl=self.ttl
        )
        self.ws_client = BenzingaNewsWebSocket(
            api_key=self.api_key,
            redis_client=self.redis.live_client,
            ttl=self.ttl
        )

    def start(self):
        try:
            # Fetch historical data
            historical_data = self.rest_client.get_historical_data(
                date_from=self.date_range['from'],
                date_to=self.date_range['to'],
                raw=False
            )
            print(f"Fetched {len(historical_data)} historical items")

            # Start all components
            self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
            self.processor_thread = threading.Thread(target=self.processor.process_all_news, daemon=True)
            self.returns_thread = threading.Thread(target=self.returns_processor.process_all_returns, daemon=True)
            
            for thread in [self.ws_thread, self.processor_thread, self.returns_thread]:
                thread.start()
            return True
            
        except Exception as e:
            logging.error(f"Error starting {self.source_type}: {e}")
            return False

    def _run_websocket(self):
        while self.running:
            try:
                self.ws_client.connect(raw=False)
            except Exception as e:
                logging.error(f"WebSocket error: {e}")
                time.sleep(5)

    def check_status(self):
        try:
            live_prefix = RedisKeys.get_prefixes(self.source_type)['live']
            return {
                "websocket": {
                    "connected": self.ws_client.connected,
                    "last_message": self.ws_client.stats.get('last_message_time')
                },
                "redis": {
                    "live_count": len(self.redis.live_client.client.keys(f"{live_prefix}raw:*")),
                    "raw_queue": len(self.redis.live_client.client.lrange(self.redis.live_client.RAW_QUEUE, 0, -1)),
                    "processed_queue": len(self.redis.live_client.client.lrange(self.redis.live_client.PROCESSED_QUEUE, 0, -1))
                }
            }
        except Exception as e:
            logging.error(f"Error checking status: {e}")
            return None

    def stop(self):
        try:
            self.running = False
            self.ws_client.disconnect()
            
            for thread in [self.ws_thread, self.processor_thread, self.returns_thread]:
                if thread and thread.is_alive():
                    thread.join(timeout=5)
            
            self.redis.clear(preserve_processed=True)
            return True
        except Exception as e:
            logging.error(f"Error stopping {self.source_type}: {e}")
            return False

    
class ReportsManager(DataSourceManager):
    """Manager for SEC filing reports"""
    def __init__(self, historical_range: Dict[str, str]):
        super().__init__(
            source_type=RedisKeys.SOURCE_REPORTS,
            historical_range=historical_range,
            api_key=SEC_API_KEY,
            processor_class=ReportProcessor
        )
        
        # Initialize API clients (similar to BenzingaNewsManager)
        self.rest_client = SECRestAPI(  
            api_key=self.api_key,
            # redis_client=self.redis.history_client,
            redis=self.redis,
            ttl=self.ttl
        )

        self.ws_client = SECWebSocket(
            api_key=self.api_key,
            redis_client=self.redis.live_client,
            ttl=self.ttl
        )

    def start(self):
        try:
            # Start all components in threads
            self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
            self.processor_thread = threading.Thread(target=self.processor.process_all_reports, daemon=True)
            self.returns_thread = threading.Thread(target=self.returns_processor.process_all_returns, daemon=True)
            
            # Fetch historical data in separate thread
            self.historical_thread = threading.Thread(
                target=self.rest_client.get_historical_data,
                args=(self.date_range['from'], self.date_range['to'], False),  # Include raw=False
                daemon=True
            )
            
            print(f"[Manager Debug] Starting threads:")
            # Start all threads including historical
            for thread in [self.ws_thread, self.processor_thread, self.returns_thread, self.historical_thread]:
                thread.start()
                print(f"[Manager Debug] Thread {thread.name} started: {thread.is_alive()}")
            
            return True

        except Exception as e:
            logging.error(f"Error starting {self.source_type}: {e}")
            return False

    # def start(self):
    #     try:
    #         # Fetch historical data
    #         historical_data = self.rest_client.get_historical_data(
    #             date_from=self.date_range['from'],
    #             date_to=self.date_range['to'],
    #             raw=False
    #         )
    #         print(f"Fetched {len(historical_data)} historical SEC filings")

    #         # Start all components in threads
    #         self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
    #         self.processor_thread = threading.Thread(target=self.processor.process_all_reports, daemon=True)
    #         self.returns_thread = threading.Thread(target=self.returns_processor.process_all_returns, daemon=True)
            
    #         print(f"[Manager Debug] Starting threads:")
    #         for thread in [self.ws_thread, self.processor_thread, self.returns_thread]:
    #             thread.start()
    #             print(f"[Manager Debug] Thread {thread.name} started: {thread.is_alive()}")
    #         return True

    #     except Exception as e:
    #         logging.error(f"Error starting {self.source_type}: {e}")
    #         return False

    def _run_websocket(self):
        """Manage WebSocket connection with proper retry logic"""
        retry_delay = 5
        max_retries = 3
        
        while self.running:
            try:
                if not self.ws_client.connected:
                    self.ws_client.connect(raw=False)
                time.sleep(1)  # Check connection status periodically
                
            except Exception as e:
                logging.error(f"SEC WebSocket error: {e}")
                time.sleep(retry_delay)

    def check_status(self):
        try:
            live_prefix = RedisKeys.get_prefixes(self.source_type)['live']
            return {
                "websocket": {
                    "connected": self.ws_client.connected,
                    "last_message": self.ws_client.last_message_time  

                },
                "redis": {
                    "live_count": len(self.redis.live_client.client.keys(f"{live_prefix}raw:*")),
                    "raw_queue": len(self.redis.live_client.client.lrange(self.redis.live_client.RAW_QUEUE, 0, -1)),
                    "processed_queue": len(self.redis.live_client.client.lrange(self.redis.live_client.PROCESSED_QUEUE, 0, -1))
                }
            }
        except Exception as e:
            logging.error(f"Error checking status: {e}")
            return None

    def stop(self):
        try:
            self.running = False
            self.ws_client.disconnect()
            
            for thread in [self.ws_thread, self.processor_thread, self.returns_thread]:
                if thread and thread.is_alive():
                    thread.join(timeout=5)
            
            self.redis.clear(preserve_processed=True)
            return True
        except Exception as e:
            logging.error(f"Error stopping {self.source_type}: {e}")
            return False
        

class DataManager:
    """Central manager for all data sources"""
    def __init__(self, date_from: str, date_to: str):
        self.historical_range = {'from': date_from, 'to': date_to}
        self.sources = {}
        self.initialize_sources()

    def initialize_sources(self):
        # self.sources['news'] = BenzingaNewsManager(self.historical_range)
        self.sources['reports'] = ReportsManager(self.historical_range)
        # Add other sources as needed:
        # self.sources['transcripts'] = TranscriptsManager(self.historical_range)

    def start(self):
        return {name: manager.start() for name, manager in self.sources.items()}

    def stop(self):
        return {name: manager.stop() for name, manager in self.sources.items()}

    def check_status(self):
        return {name: manager.check_status() for name, manager in self.sources.items()}

    def get_source(self, name: str):
        return self.sources.get(name)
    



"""
class TranscriptsManager(DataSourceManager):
    def __init__(self, historical_range: Dict[str, str]):
        super().__init__(
            source_type=RedisKeys.SOURCE_TRANSCRIPTS,
            historical_range=historical_range,
            api_key=TRANSCRIPTS_API_KEY  # You would define this
        )
        
        # Initialize API clients
        self.rest_client = TranscriptsRestAPI(...)
        self.ws_client = TranscriptsWebSocket(...)

    # Rest of implementation matches BenzingaNewsManager
"""