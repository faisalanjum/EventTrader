import threading
import logging
import time
import pytz
from typing import Dict, Optional
from datetime import datetime, timedelta
from utils.Neo4jProcessor import Neo4jProcessor
from utils.Neo4jInitializer import Neo4jInitializer


from utils.redisClasses import EventTraderRedis, RedisKeys, RedisClient
from utils.log_config import get_logger, setup_logging

from benzinga.bz_restAPI import BenzingaNewsRestAPI
from benzinga.bz_websocket import BenzingaNewsWebSocket

from transcripts.EarningsCallTranscripts import EarningsCallProcessor
from utils.TranscriptProcessor import TranscriptProcessor
from eventtrader.keys import EARNINGS_CALL_API_KEY
import json


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
        # ttl: int = 7 * 24 * 3600
        ttl: int = 2 * 24 * 3600
    ):
        self.source_type = source_type
        self.api_key = api_key
        self.ttl = ttl
        self.date_range = historical_range
        self.running = True
        
        # Set up logger
        self.logger = get_logger(f"{self.__class__.__name__}")

        # Initialize Redis and processors
        self.redis = EventTraderRedis(source=self.source_type)        # ex: source_type = news:benzinga
        # self.processor = NewsProcessor(self.redis, delete_raw=True)
        self.polygon_subscription_delay = (17 * 60)  # (in seconds) Lower tier subscription has 15 mins delayed data

        self.logger.debug(f"Initializing {source_type} manager")
        self.logger.debug(f"Processor class: {processor_class}")

        self.processor = processor_class(self.redis, delete_raw=True,polygon_subscription_delay=self.polygon_subscription_delay) if processor_class else None

        self.logger.debug(f"Processor initialized: {self.processor is not None}")

        self.returns_processor = ReturnsProcessor(self.redis, polygon_subscription_delay=self.polygon_subscription_delay)
        
        # Thread management
        self.ws_thread = None
        self.processor_thread = None
        self.returns_thread = None

    def start(self): raise NotImplementedError
    def check_status(self): raise NotImplementedError
    def stop(self): raise NotImplementedError


class TranscriptsManager(DataSourceManager):
    """Manager for earnings call transcripts"""
    def __init__(self, historical_range: Dict[str, str]):
        super().__init__(
            source_type=RedisKeys.SOURCE_TRANSCRIPTS,
            historical_range=historical_range,
            api_key=EARNINGS_CALL_API_KEY,
            processor_class=TranscriptProcessor
        )
        
        # Initialize the EarningsCall client with Redis client for accessing universe data
        self.earnings_call_client = EarningsCallProcessor(
            api_key=self.api_key,
            redis_client=self.redis,
            ttl=self.ttl
        )
        
        # For live data polling
        self.last_poll_time = None
    
    def start(self):
        try:
            # Start processor thread
            self.processor_thread = threading.Thread(
                target=self.processor.process_all_transcripts, 
                daemon=True
            )
            
            # Start returns processor thread
            self.returns_thread = threading.Thread(
                target=self.returns_processor.process_all_returns, 
                daemon=True
            )
            
            # Start historical data processing in background
            self.historical_thread = threading.Thread(
                target=self._fetch_historical_data,
                daemon=True
            )
            
            # Start threads
            self.processor_thread.start()
            self.returns_thread.start()
            self.historical_thread.start()
            
            self.logger.info(f"Started transcript processing threads")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting {self.source_type}: {e}")
            return False




    def _fetch_historical_data(self):
        """Process historical transcripts"""
        try:
            self.logger.info(f"Fetching historical transcripts from {self.date_range['from']} to {self.date_range['to']}")
            
            # Convert date_range to list of individual dates
            start_date = datetime.strptime(self.date_range['from'], "%Y-%m-%d").date()
            end_date = datetime.strptime(self.date_range['to'], "%Y-%m-%d").date()
            
            # Iterate through each date in range
            current_date = start_date
            while current_date <= end_date:
                try:
                    self.logger.info(f"Fetching transcripts for date {current_date}")
                    transcripts = self.earnings_call_client.get_transcripts_for_single_date(current_date)
                    
                    if not transcripts:
                        self.logger.info(f"No transcripts found for {current_date}")
                        current_date += timedelta(days=1)
                        continue
                        
                    self.logger.info(f"Found {len(transcripts)} transcripts for {current_date}")
                    
                    # Store each transcript in historical Redis immediately
                    for transcript in transcripts:
                        self.earnings_call_client.store_transcript_in_redis(transcript, is_live=False)
                        
                    # Add a small delay to respect API rate limits between date calls
                    time.sleep(1)
                        
                except Exception as e:
                    self.logger.error(f"Error processing transcripts for {current_date}: {e}")
                    # Add a longer delay after errors
                    time.sleep(5)
                
                # Move to next day
                current_date += timedelta(days=1)
                    
        except Exception as e:
            self.logger.error(f"Error in historical transcript processing: {e}")


    # def _fetch_historical_data(self):
    #     """Process historical transcripts"""
    #     try:
    #         self.logger.info(f"Fetching historical transcripts from {self.date_range['from']} to {self.date_range['to']}")
            
    #         # Get a limited set of symbols for testing
    #         # symbols = self.redis.get_symbols()[:10]  # Limit to 10 for testing
    #         symbols = ['NVDA']
            
    #         for symbol in symbols:
    #             try:
    #                 self.logger.info(f"Fetching transcripts for {symbol}")
    #                 transcripts = self.earnings_call_client.get_transcripts_by_date_range(
    #                     ticker=symbol,
    #                     start_date=self.date_range['from'],
    #                     end_date=self.date_range['to']
    #                 )
                    
    #                 if not transcripts:
    #                     continue
                        
    #                 self.logger.info(f"Found {len(transcripts)} transcripts for {symbol}")
                    
    #                 # Store each transcript in historical Redis
    #                 for transcript in transcripts:
    #                     self.earnings_call_client.store_transcript_in_redis(transcript, is_live=False)
                        
    #             except Exception as e:
    #                 self.logger.error(f"Error processing transcripts for {symbol}: {e}")
    #                 continue
                    
    #     except Exception as e:
    #         self.logger.error(f"Error in historical transcript processing: {e}")
    
    def fetch_live_transcripts(self, target_date=None):
        """Public method to manually fetch 'live' transcripts for a date"""
        try:
            # Use current date if none provided
            if target_date is None:
                target_date = datetime.now(pytz.timezone('America/New_York')).date()
                
            self.logger.info(f"Manually fetching transcripts for {target_date}")
            
            # Fetch transcripts for the date
            transcripts = self.earnings_call_client.get_transcripts_for_single_date(target_date)
            
            if not transcripts:
                self.logger.info(f"No transcripts found for {target_date}")
                return 0
                
            # Store in Redis live queue
            count = 0
            for transcript in transcripts:
                # Store transcript in live Redis
                self.earnings_call_client.store_transcript_in_redis(transcript, is_live=True)
                count += 1
                
            self.last_poll_time = datetime.now(pytz.timezone('America/New_York'))
            self.logger.info(f"Added {count} transcripts to live queue")
            return count
            
        except Exception as e:
            self.logger.error(f"Error fetching live transcripts: {e}")
            return 0
    
    def check_status(self):
        """Check system status"""
        try:
            live_prefix = RedisKeys.get_prefixes(self.source_type)['live']
            
            return {
                "live_data": {
                    "last_poll": self.last_poll_time.isoformat() if self.last_poll_time else None,
                    "processor_running": self.processor_thread.is_alive() if hasattr(self, 'processor_thread') else False
                },
                "redis": {
                    "live_count": len(self.redis.live_client.client.keys(f"{live_prefix}raw:*")),
                    "raw_queue": len(self.redis.live_client.client.lrange(self.redis.live_client.RAW_QUEUE, 0, -1)),
                    "processed_queue": len(self.redis.live_client.client.lrange(self.redis.live_client.PROCESSED_QUEUE, 0, -1))
                }
            }
        except Exception as e:
            self.logger.error(f"Error checking status: {e}")
            return None
    
    def stop(self):
        """Stop all processing"""
        try:
            # Signal threads to stop
            self.running = False
            
            # Wait for threads to finish
            for thread in [self.processor_thread, self.returns_thread, self.historical_thread]:
                if thread and thread.is_alive():
                    thread.join(timeout=5)
            
            self.redis.clear(preserve_processed=True)
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping {self.source_type}: {e}")
            return False



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
            self.logger.info(f"Fetched {len(historical_data)} historical items")

            # Start all components
            self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
            self.processor_thread = threading.Thread(target=self.processor.process_all_news, daemon=True)
            self.returns_thread = threading.Thread(target=self.returns_processor.process_all_returns, daemon=True)
            
            for thread in [self.ws_thread, self.processor_thread, self.returns_thread]:
                thread.start()
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting {self.source_type}: {e}")
            return False

    def _run_websocket(self):
        while self.running:
            try:
                self.ws_client.connect(raw=False)
            except Exception as e:
                self.logger.error(f"WebSocket error: {e}")
                time.sleep(5)


    # def _run_websocket(self):
    #     """Manage WebSocket connection with proper retry logic"""
    #     while self.running:
    #         try:
    #             if not self.ws_client.connected:
    #                 print(f"Starting {self.source_type} WebSocket connection...")
    #                 # Direct call to connect - don't wrap in another thread
    #                 self.ws_client.connect(raw=False)
    #             time.sleep(2)  # Brief check interval
    #         except Exception as e:
    #             logging.error(f"{self.source_type} WebSocket error: {e}")
    #             time.sleep(5)    

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
            self.logger.error(f"Error checking status: {e}")
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
            self.logger.error(f"Error stopping {self.source_type}: {e}")
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
            
            self.logger.debug(f"[Manager Debug] Starting threads:")
            # Start all threads including historical
            for thread in [self.ws_thread, self.processor_thread, self.returns_thread, self.historical_thread]:
                thread.start()
                self.logger.debug(f"[Manager Debug] Thread {thread.name} started: {thread.is_alive()}")
            
            return True

        except Exception as e:
            self.logger.error(f"Error starting {self.source_type}: {e}")
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

    # def _run_websocket(self):
    #     """Manage WebSocket connection with proper retry logic"""
    #     retry_delay = 5
    #     max_retries = 3
        
    #     while self.running:
    #         try:
    #             if not self.ws_client.connected:
    #                 self.ws_client.connect(raw=False)
    #             time.sleep(1)  # Check connection status periodically
                
    #         except Exception as e:
    #             logging.error(f"SEC WebSocket error: {e}")
    #             time.sleep(retry_delay)


    def _run_websocket(self):
        while self.running:
            try:
                # Direct call without checking - connect() should block until disconnected
                self.ws_client.connect(raw=False)
            except Exception as e:
                self.logger.error(f"SEC WebSocket error: {e}")
                time.sleep(5)


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
            self.logger.error(f"Error checking status: {e}")
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
            self.logger.error(f"Error stopping {self.source_type}: {e}")
            return False
        

class DataManager:
    """Central data manager that coordinates all data sources and processors"""
    
    def __init__(self, date_from: str, date_to: str):
        # Use existing logger instead of setting up a new one
        self.logger = get_logger("utils.DataManagerCentral")
        
        # Store settings
        self.historical_range = {'from': date_from, 'to': date_to}
        self.sources = {}
        
        # Initialize sources first
        self.initialize_sources()
        
        # Initialize Neo4j processor
        self.initialize_neo4j()
        
        # Set up signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
    def initialize_sources(self):
        self.sources['news'] = BenzingaNewsManager(self.historical_range)
        self.sources['reports'] = ReportsManager(self.historical_range)
        self.sources['transcripts'] = TranscriptsManager(self.historical_range)

    def initialize_neo4j(self):
        """Initialize Neo4j processor"""
        self.logger.info("Initializing Neo4j processor")
        
        try:
            # Get Redis client if available
            # event_trader_redis = None
            # if hasattr(self, 'sources') and 'news' in self.sources:
            #     source_manager = self.sources['news']
            #     if hasattr(source_manager, 'redis'):
            #         event_trader_redis = source_manager.redis
            #         self.logger.info("Using Redis client from news source")


            # Find first available Redis client
            event_trader_redis = None
            for source_name in self.sources:
                if hasattr(self.sources[source_name], 'redis'):
                    event_trader_redis = self.sources[source_name].redis
                    self.logger.info(f"Using Redis client from {source_name}")
                    break
            
            if event_trader_redis:
                self.neo4j_processor = Neo4jProcessor(event_trader_redis)


            # Create Neo4j processor with default connection settings
            # self.neo4j_processor = Neo4jProcessor(event_trader_redis=event_trader_redis)
            
            # Connect to Neo4j
            if not self.neo4j_processor.connect():
                self.logger.error("Failed to connect to Neo4j")
                return False
                
            # Check if Neo4j is already initialized
            if self.neo4j_processor.is_initialized():
                self.logger.info("Neo4j already initialized, skipping initialization")
                # Even if initialized, process news and report data
                self.process_news_data()
                self.process_report_data()
            else:
                # Initialize Neo4j if not already initialized
                self.logger.info("Neo4j not initialized, initializing database")
                # Pass the start date from historical range
                start_date = self.historical_range.get('from')
                self.logger.info(f"Using start date for date nodes: {start_date}")
                if not self.neo4j_processor.initialize(start_date=start_date):
                    self.logger.error("Failed to initialize Neo4j database")
                    return False
                    
                self.logger.info("Neo4j initialization completed successfully")
                
                # Process news and report data after successful initialization
                self.process_news_data()
                self.process_report_data()
            
            # Start the PubSub-based continuous processing thread
            self.neo4j_thread = threading.Thread(
                target=self.neo4j_processor.process_with_pubsub,
                daemon=True
            )
            self.neo4j_thread.start()
            self.logger.info("Started Neo4j event-driven processing thread")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing Neo4j: {e}")
            return False

    def process_news_data(self, batch_size=100, max_items=1000, include_without_returns=True):
        """
        Process news data into Neo4j from Redis
        
        Args:
            batch_size: Number of items to process in each batch
            max_items: Maximum number of items to process
            include_without_returns: Whether to process news from the withoutreturns namespace
        """
        if not hasattr(self, 'neo4j_processor') or not self.neo4j_processor:
            self.logger.error("Neo4j processor not initialized, cannot process news")
            return False
            
        try:
            self.logger.info(f"Processing news data to Neo4j (batch_size={batch_size}, max_items={max_items}, include_without_returns={include_without_returns})...")
            success = self.neo4j_processor.process_news_to_neo4j(batch_size, max_items, include_without_returns)
            
            if success:
                self.logger.info("News data processing completed successfully")
            else:
                self.logger.warning("News data processing returned with errors")
                
            return success
        
        except Exception as e:
            self.logger.error(f"Error processing news data: {e}")
            return False

    def process_report_data(self, batch_size=100, max_items=1000, include_without_returns=True):
        """
        Process SEC report data into Neo4j from Redis
        
        Args:
            batch_size: Number of items to process in each batch
            max_items: Maximum number of items to process
            include_without_returns: Whether to process reports without returns
        """
        if not hasattr(self, 'neo4j_processor') or not self.neo4j_processor:
            self.logger.error("Neo4j processor not initialized, cannot process reports")
            return False
            
        try:
            self.logger.info(f"Processing SEC report data to Neo4j (batch_size={batch_size}, max_items={max_items}, include_without_returns={include_without_returns})...")
            success = self.neo4j_processor.process_reports_to_neo4j(batch_size, max_items, include_without_returns)
            
            if success:
                self.logger.info("SEC report data processing completed successfully")
            else:
                self.logger.warning("SEC report data processing returned with errors")
                
            return success
        
        except Exception as e:
            self.logger.error(f"Error processing SEC report data: {e}")
            return False

    def has_neo4j(self):
        """Check if Neo4j processor is available and initialized"""
        return hasattr(self, 'neo4j_processor') and self.neo4j_processor is not None


    def start(self):
        return {name: manager.start() for name, manager in self.sources.items()}


    def stop(self):
        results = {name: manager.stop() for name, manager in self.sources.items()}
        
        # Close Neo4j connection if initialized
        if hasattr(self, 'neo4j_processor'):
            try:
                # Stop the PubSub processing thread if running
                if hasattr(self, 'neo4j_thread') and self.neo4j_thread.is_alive():
                    self.neo4j_processor.stop_pubsub_processing()
                    self.neo4j_thread.join(timeout=5)
                    
                self.neo4j_processor.close()
                self.logger.info("Neo4j processor closed")
            except Exception as e:
                self.logger.error(f"Error closing Neo4j processor: {e}")
                
        return results


    def check_status(self):
        return {name: manager.check_status() for name, manager in self.sources.items()}


    def get_source(self, name: str):
        return self.sources.get(name)

    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""
        import signal
        import sys
        
        def signal_handler(sig, frame):
            self.logger.info("Shutdown signal received. Stopping all components gracefully...")
            self.stop()
            self.logger.info("Shutdown complete. Exiting.")
            sys.exit(0)
            
        # Register for SIGINT (Ctrl+C) and SIGTERM
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        self.logger.info("Signal handlers registered for graceful shutdown")


    
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