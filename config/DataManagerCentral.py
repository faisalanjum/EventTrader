import threading
import logging
import time
import pytz
from typing import Dict, Optional
from datetime import datetime, timedelta
from neograph.Neo4jProcessor import Neo4jProcessor
from neograph.Neo4jInitializer import Neo4jInitializer


from redisDB.redisClasses import EventTraderRedis, RedisKeys, RedisClient
from benzinga.bz_restAPI import BenzingaNewsRestAPI
from benzinga.bz_websocket import BenzingaNewsWebSocket

from transcripts.EarningsCallTranscripts import EarningsCallProcessor
from redisDB.TranscriptProcessor import TranscriptProcessor
from eventtrader.keys import EARNINGS_CALL_API_KEY
import json


from redisDB.NewsProcessor import NewsProcessor
from redisDB.ReportProcessor import ReportProcessor
from eventReturns.ReturnsProcessor import ReturnsProcessor

from eventtrader.keys import BENZINGANEWS_API_KEY
from eventtrader.keys import SEC_API_KEY

# Change these to absolute imports
import sys
# sys.path.append('/Users/macowne/Desktop/Faisal/EventTrader')  # Add project root to path - REMOVED

from secReports.sec_websocket import SECWebSocket
from secReports.sec_restAPI import SECRestAPI

from . import feature_flags



class DataSourceManager:
    """Base class for managing different data sources"""
    def __init__(
        self,
        source_type: str,
        historical_range: Dict[str, str],  # {'from': 'YYYY-MM-DD', 'to': 'YYYY-MM-DD'}
        api_key: str,
        processor_class=None,
        ttl: int = 2 * 24 * 3600 # 2 days
    ):
        self.source_type = source_type
        self.api_key = api_key
        self.ttl = ttl # self.ttl is used by worker for individual processed keys
        self.date_range = historical_range
        self.running = True

        # Set up logger using standard logging
        self.logger = logging.getLogger(__name__)

        # Initialize Redis and processors
        self.redis = EventTraderRedis(source=self.source_type)        # ex: source_type = news:benzinga

        # Set TTL for queue LIST KEYS only if they exist and TTL is configured
        if self.ttl and self.ttl > 0:
            for client_instance in [self.redis.live_client, self.redis.history_client]:
                queues_to_check = [
                    client_instance.RAW_QUEUE,
                    client_instance.PROCESSED_QUEUE,
                    client_instance.FAILED_QUEUE
                ]
                # Check for ENRICH_QUEUE only if it's relevant for this client (reports client)
                if hasattr(client_instance, 'ENRICH_QUEUE'): # ENRICH_QUEUE is a global RedisKeys constant, not on client
                    # Correct check would be if client_instance.source_type == RedisKeys.SOURCE_REPORTS
                    # However, ENRICH_QUEUE is defined as RedisKeys.ENRICH_QUEUE directly.
                    # We should check if RedisKeys.ENRICH_QUEUE exists for reports.
                    # For now, this part of the original code was trying to expire client.ENRICH_QUEUE
                    # which doesn't exist. The global RedisKeys.ENRICH_QUEUE is the one.
                    pass # Original loop was trying to iterate client.ENRICH_QUEUE which is wrong.
                
                pipe = client_instance.client.pipeline()
                keys_to_expire = []
                for queue_key_name in queues_to_check:
                    if client_instance.client.exists(queue_key_name):
                        keys_to_expire.append(queue_key_name)
                
                # For reports source, also check the global ENRICH_QUEUE if it exists
                if self.source_type == RedisKeys.SOURCE_REPORTS:
                    if client_instance.client.exists(RedisKeys.ENRICH_QUEUE):
                        keys_to_expire.append(RedisKeys.ENRICH_QUEUE)

                if keys_to_expire:
                    for key in keys_to_expire:
                        pipe.expire(key, self.ttl)
                    try:
                        pipe.execute()
                        self.logger.info(f"Applied TTL of {self.ttl}s to existing queues: {keys_to_expire} for {client_instance.prefix}")
                    except Exception as e:
                        self.logger.error(f"Error setting TTL on queues for {client_instance.prefix}: {e}", exc_info=True)

        # self.processor = NewsProcessor(self.redis, delete_raw=True)
        self.polygon_subscription_delay = (17 * 60)  # (in seconds) Lower tier subscription has 15 mins delayed data

        self.logger.debug(f"Initializing {source_type} manager")
        self.logger.debug(f"Processor class: {processor_class}")

        self.processor = processor_class(self.redis, delete_raw=True,polygon_subscription_delay=self.polygon_subscription_delay, ttl=self.ttl) if processor_class else None

        self.logger.debug(f"Processor initialized: {self.processor is not None}")

        self.returns_processor = ReturnsProcessor(self.redis, polygon_subscription_delay=self.polygon_subscription_delay)
        
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
        self.ws_thread = None # Initialize optional thread

    def start(self):
        try:
            # Fetch historical data if enabled
            if feature_flags.ENABLE_HISTORICAL_DATA:
                historical_data = self.rest_client.get_historical_data(
                    date_from=self.date_range['from'],
                    date_to=self.date_range['to'],
                    raw=False
                )
                self.logger.info(f"Fetched {len(historical_data)} historical News items")
            else:
                self.logger.info("Historical data fetching disabled for Benzinga News.")

            # Start processing threads (always needed)
            self.processor_thread = threading.Thread(target=self.processor.process_all_news, daemon=True)
            self.returns_thread = threading.Thread(target=self.returns_processor.process_all_returns, daemon=True)
            
            threads_to_start = [self.processor_thread, self.returns_thread]

            # --- CONDITIONALLY START WEBSOCKET THREAD ---
            if feature_flags.ENABLE_LIVE_DATA:
                self.logger.info("Live data enabled, starting WebSocket thread for Benzinga News.")
                self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
                threads_to_start.append(self.ws_thread)
            else:
                self.logger.info("Live data disabled, WebSocket thread for Benzinga News will not be started.")
            # -------------------------------------------
            
            for thread in threads_to_start:
                thread.start()
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting {self.source_type}: {e}", exc_info=True)
            return False

    def _run_websocket(self):
        while self.running:
            try:
                self.ws_client.connect(raw=False)
            except Exception as e:
                self.logger.error(f"WebSocket error: {e}", exc_info=True)
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
            
            # Safely access WebSocket client attributes
            ws_connected = False
            last_msg_time = None
            if hasattr(self, 'ws_client'): # Ensure ws_client itself exists
                ws_connected = getattr(self.ws_client, 'connected', False)
                ws_stats = getattr(self.ws_client, 'stats', {})
                last_msg_time = ws_stats.get('last_message_time')

            return {
                "websocket": {
                    "connected": ws_connected,
                    "last_message": last_msg_time
                },
                "redis": {
                    "live_count": len(self.redis.live_client.client.keys(f"{live_prefix}raw:*")),
                    "raw_queue": len(self.redis.live_client.client.lrange(self.redis.live_client.RAW_QUEUE, 0, -1)),
                    "processed_queue": len(self.redis.live_client.client.lrange(self.redis.live_client.PROCESSED_QUEUE, 0, -1))
                }
            }
        except Exception as e:
            self.logger.error(f"Error checking status for {self.source_type}: {e}", exc_info=True)
            return None

    def stop(self):
        try:
            self.running = False
            if hasattr(self, 'ws_client'): # ws_client might not be init if live disabled
                self.ws_client.disconnect()
            
            current_thread = threading.current_thread()
            threads_to_join = [
                getattr(self, 'ws_thread', None),
                getattr(self, 'processor_thread', None),
                getattr(self, 'returns_thread', None)
                # BenzingaNewsManager doesn't have self.historical_thread explicitly
            ]
            for thread in threads_to_join:
                if thread and thread.is_alive() and thread != current_thread:
                    thread.join(timeout=5)
            
            self.redis.clear(preserve_processed=True)
            return True
        except Exception as e:
            self.logger.error(f"Error stopping {self.source_type}: {e}", exc_info=True)
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
        self.ws_thread = None # Initialize optional thread
        self.historical_thread = None # Initialize optional thread
        self.enrichment_workers = [] # Initialize, though it's also done in start()

    def start(self):
        try:
            # Start processing threads (always needed)
            self.processor_thread = threading.Thread(target=self.processor.process_all_reports, daemon=True)
            self.returns_thread = threading.Thread(target=self.returns_processor.process_all_returns, daemon=True)
            
            threads_to_start = [self.processor_thread, self.returns_thread]
            
            # Fetch historical data in separate thread if enabled
            if feature_flags.ENABLE_HISTORICAL_DATA:
                self.historical_thread = threading.Thread(
                    target=self.rest_client.get_historical_data,
                    args=(self.date_range['from'], self.date_range['to'], False), # Include raw=False
                    daemon=True
                )
                
                threads_to_start.append(self.historical_thread)
            else:
                 self.logger.info("Historical data fetching disabled for SEC Reports.")

            # --- CONDITIONALLY START WEBSOCKET THREAD ---
            if feature_flags.ENABLE_LIVE_DATA:
                self.logger.info("Live data enabled, starting WebSocket thread for SEC Reports.")
                self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
                threads_to_start.append(self.ws_thread)
            else:
                self.logger.info("Live data disabled, WebSocket thread for SEC Reports will not be started.")
            # -------------------------------------------
            
            # --- START ENRICHMENT WORKERS ---
            if feature_flags.ENABLE_REPORT_ENRICHER:
                self.logger.info("Report enrichment handled by Kubernetes pods")
                self.enrichment_workers = []  # Empty list for compatibility
            
            # ALWAYS START ESSENTIAL THREADS (processor, returns, ws, historical if enabled)
            self.logger.debug(f"[Manager Debug] Starting essential threads:")
            for thread in threads_to_start: # threads_to_start was prepared earlier
                thread.start()
                self.logger.debug(f"[Manager Debug] Thread {thread.name} started: {thread.is_alive()}")
            
            return True # ReportsManager.start() now always returns True if it reaches here, failure to start workers is logged.

        except Exception as e:
            self.logger.error(f"Critical error during ReportsManager.start(): {e}", exc_info=True)
            return False # Return False on critical startup errors for main threads


    def _run_websocket(self):
        while self.running:
            try:
                # Direct call without checking - connect() should block until disconnected
                self.ws_client.connect(raw=False)
            except Exception as e:
                self.logger.error(f"SEC WebSocket error: {e}", exc_info=True)
                time.sleep(5)


    def check_status(self):
        try:
            live_prefix = RedisKeys.get_prefixes(self.source_type)['live']
            
            # Safely access WebSocket client attributes
            ws_connected = False
            last_msg_time = None # SECWebSocket uses last_message_time directly
            if hasattr(self, 'ws_client'): # Ensure ws_client itself exists
                ws_connected = getattr(self.ws_client, 'connected', False)
                last_msg_time = getattr(self.ws_client, 'last_message_time', None)

            return {
                "websocket": {
                    "connected": ws_connected,
                    "last_message": last_msg_time
                },
                "redis": {
                    "live_count": len(self.redis.live_client.client.keys(f"{live_prefix}raw:*")),
                    "raw_queue": len(self.redis.live_client.client.lrange(self.redis.live_client.RAW_QUEUE, 0, -1)),
                    "processed_queue": len(self.redis.live_client.client.lrange(self.redis.live_client.PROCESSED_QUEUE, 0, -1))
                }
            }
        except Exception as e:
            self.logger.error(f"Error checking status for {self.source_type}: {e}", exc_info=True)
            return None

    def stop(self):
        try:
            self.running = False
            if hasattr(self, 'ws_client'): # ws_client might not be init if live disabled
                self.ws_client.disconnect()
            
            current_thread = threading.current_thread()
            threads_to_join = [
                getattr(self, 'ws_thread', None),
                getattr(self, 'processor_thread', None),
                getattr(self, 'returns_thread', None),
                getattr(self, 'historical_thread', None) # ReportsManager has historical_thread
            ]
            for thread in threads_to_join:
                if thread and thread.is_alive() and thread != current_thread:
                    thread.join(timeout=5)
            
            if hasattr(self, 'enrichment_workers') and self.enrichment_workers:
                self.logger.info(f"Stopping {len(self.enrichment_workers)} enrichment workers...")
                for p in self.enrichment_workers:
                    if p.is_alive():
                        p.terminate()
                for p in self.enrichment_workers:
                    p.join(timeout=3)
            
            self.redis.clear(preserve_processed=True)
            return True
        except Exception as e:
            self.logger.error(f"Error stopping {self.source_type}: {e}", exc_info=True)
            return False
        



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
        self.historical_thread = None # Initialize optional thread
    
    def start(self):
        try:
            # Initialize schedule at startup (Should this be conditional too? Seems safe to run always)
            self._initialize_transcript_schedule()

            # Start processor thread (Always needed to process potential live scheduled items)
            self.processor_thread = threading.Thread(
                target=self.processor.process_all_transcripts, 
                daemon=True
            )
            
            # Start returns processor thread (Always needed)
            self.returns_thread = threading.Thread(
                target=self.returns_processor.process_all_returns, 
                daemon=True
            )
            
            threads_to_start = [self.processor_thread, self.returns_thread]

            # --- CONDITIONALLY START HISTORICAL THREAD ---
            if feature_flags.ENABLE_HISTORICAL_DATA:
                 self.logger.info("Historical data enabled, starting historical transcript fetch thread.")
                 self.historical_thread = threading.Thread(
                     target=self._fetch_historical_data,
                     daemon=True
                 )
                 threads_to_start.append(self.historical_thread)
            else:
                 self.logger.info("Historical data disabled, historical transcript fetch thread will not be started.")
            # ------------------------------------------
            
            # Start threads
            # self.processor_thread.start()
            # self.returns_thread.start()
            # self.historical_thread.start()
            for thread in threads_to_start:
                 thread.start()
            
            self.logger.info(f"Started transcript processing threads")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting {self.source_type}: {e}", exc_info=True)
            return False

    def _initialize_transcript_schedule(self):
        """Schedule transcripts for today"""
        try:
            # Use Eastern timezone consistently
            eastern_tz = pytz.timezone('America/New_York')
            today = datetime.now(eastern_tz).date()
            
            # Get events (already in Eastern time) and filter to our universe
            events = self.earnings_call_client.get_earnings_events(today)
            universe = set(s.upper() for s in self.redis.get_symbols())
            relevant = [e for e in events if e.symbol.upper() in universe]
            
            if not relevant:
                return
                
            # Set up Redis pipeline and clear previous schedule
            pipe = self.redis.live_client.client.pipeline()
            notification_channel = "admin:transcripts:notifications"
            pipe.delete("admin:transcripts:schedule")
            
            # Schedule each relevant event
            for event in relevant:
                # Add 30 minutes to conference time for the processing schedule
                # No timezone conversion needed since events are already in Eastern time
                conf_date_eastern = event.conference_date
                process_time = int(conf_date_eastern.timestamp() + 1800)
                
                # Create event key using the simple string conversion approach
                event_key = f"{event.symbol}_{str(conf_date_eastern).replace(':', '.')}"
                pipe.zadd("admin:transcripts:schedule", {event_key: process_time})
                
                # Log with clear human-readable times
                self.logger.info(f"Scheduled {event_key} - Conference: {conf_date_eastern.strftime('%Y-%m-%d %H:%M:%S %Z')}, Processing: {datetime.fromtimestamp(process_time, eastern_tz).strftime('%Y-%m-%d %H:%M:%S %Z')}")
                
                # Publish notification
                pipe.publish(notification_channel, event_key)
            
            # Execute all Redis commands and send final notification
            pipe.execute()
            self.redis.live_client.client.publish(notification_channel, "schedule_updated")
            
            self.logger.info(f"Scheduled {len(relevant)} transcripts for {today}")
        except Exception as e:
            self.logger.error(f"Error scheduling transcripts: {e}", exc_info=True)



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
                    self.logger.error(f"Error processing transcripts for {current_date}: {e}", exc_info=True)
                    # Add a longer delay after errors
                    time.sleep(5)
                
                # Move to next day
                current_date += timedelta(days=1)
            
            # --- Fetch Complete Signal --- Start (After loop finishes)
            batch_id = f"transcripts:{self.date_range['from']}-{self.date_range['to']}"
            self.redis.history_client.client.set(f"batch:{batch_id}:fetch_complete", "1", ex=86400)
            self.logger.info(f"Set fetch_complete flag for batch: {batch_id}")
            # --- Fetch Complete Signal --- End
                    
        except Exception as e:
            # Log error but DO NOT set completion flag if loop failed
            self.logger.error(f"Error in historical transcript processing: {e}", exc_info=True)


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
            self.logger.error(f"Error fetching live transcripts: {e}", exc_info=True)
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
            self.logger.error(f"Error checking status: {e}", exc_info=True)
            return None
    
    def stop(self):
        """Stop all processing"""
        try:
            self.running = False # Signal polling loops to stop if any
            
            current_thread = threading.current_thread()
            threads_to_join = [
                getattr(self, 'processor_thread', None),
                getattr(self, 'returns_thread', None),
                getattr(self, 'historical_thread', None) # TranscriptsManager has historical_thread
                # TranscriptsManager doesn't have self.ws_thread
            ]
            for thread in threads_to_join:
                if thread and thread.is_alive() and thread != current_thread:
                    thread.join(timeout=5)
            
            self.redis.clear(preserve_processed=True)
            return True
        except Exception as e:
            self.logger.error(f"Error stopping {self.source_type}: {e}", exc_info=True)
            return False




class DataManager:
    """Central data manager that coordinates all data sources and processors"""
    
    def __init__(self, date_from: str, date_to: str):
        # Use standard logger
        self.logger = logging.getLogger("config.DataManagerCentral")
        
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
            # Find first available Redis client
            event_trader_redis = None
            for source_name in self.sources:
                if hasattr(self.sources[source_name], 'redis'):
                    event_trader_redis = self.sources[source_name].redis
                    self.logger.info(f"Using Redis client from {source_name}")
                    break
            
            if event_trader_redis:
                self.neo4j_processor = Neo4jProcessor(event_trader_redis)
            
            # Connect to Neo4j
            if not self.neo4j_processor.connect():
                self.logger.error("Failed to connect to Neo4j")
                return False
            
            # Explicitly call XBRL reconciliation after connection is established
            self.logger.info("Neo4j connection established, explicitly triggering XBRL reconciliation")
            self.neo4j_processor.reconcile_xbrl_after_connect()
                
            # Check if Neo4j is already initialized
            if self.neo4j_processor.is_initialized():
                self.logger.info("Neo4j already initialized, skipping initialization")
                # Even if initialized, process news and report data
                self.process_news_data()
                self.process_report_data()
                self.process_transcript_data()
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
                self.process_transcript_data()
            
            # Start the PubSub-based continuous processing thread
            self.neo4j_thread = threading.Thread(
                target=self.neo4j_processor.process_with_pubsub,
                daemon=True
            )
            self.neo4j_thread.start()
            self.logger.info("Started Neo4j event-driven processing thread")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing Neo4j: {e}", exc_info=True)
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
            self.logger.error(f"Error processing news data: {e}", exc_info=True)
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
            self.logger.error(f"Error processing SEC report data: {e}", exc_info=True)
            return False

    def process_transcript_data(self, batch_size=100, max_items=1000, include_without_returns=True):
        """
        Process transcript data into Neo4j from Redis
        
        Args:
            batch_size: Number of items to process in each batch
            max_items: Maximum number of items to process
            include_without_returns: Whether to process transcripts without returns
        """
        if not hasattr(self, 'neo4j_processor') or not self.neo4j_processor:
            self.logger.error("Neo4j processor not initialized, cannot process transcripts")
            return False
            
        try:
            self.logger.info(f"Processing transcript data to Neo4j (batch_size={batch_size}, max_items={max_items}, include_without_returns={include_without_returns})...")
            success = self.neo4j_processor.process_transcripts_to_neo4j(batch_size, max_items, include_without_returns)
            
            if success:
                self.logger.info("Transcript data processing completed successfully")
            else:
                self.logger.warning("Transcript data processing returned with errors")
                
            return success
        
        except Exception as e:
            self.logger.error(f"Error processing transcript data: {e}", exc_info=True)
            return False

    def has_neo4j(self):
        """Check if Neo4j processor is available and initialized"""
        return hasattr(self, 'neo4j_processor') and self.neo4j_processor is not None


    def start(self):
        return {name: manager.start() for name, manager in self.sources.items()}


    def stop(self):
        """
        Stop all sources and perform final cleanup.
        """
        # Run final reconciliation before stopping sources
        try:
            self.logger.info("[STOP] Performing final reconciliation before stopping sources")
            if hasattr(self, 'neo4j_processor') and self.neo4j_processor:
                self.neo4j_processor.reconcile_missing_items(max_items_per_type=None)
        except Exception as e:
            self.logger.error(f"[STOP] Error during final reconciliation: {e}", exc_info=True)
        
        results = {name: manager.stop() for name, manager in self.sources.items()}
        
        if hasattr(self, 'neo4j_processor'):
            try:
                if hasattr(self, 'neo4j_thread') and self.neo4j_thread.is_alive():
                    self.logger.info("[STOP] Signaling Neo4j PubSub thread to stop...")
                    self.neo4j_processor.stop_pubsub_processing()
                    self.logger.info("[STOP] Waiting for Neo4j PubSub thread to join...")
                    self.neo4j_thread.join(timeout=10) # Increased timeout for safety
                    if self.neo4j_thread.is_alive():
                        self.logger.warning("[STOP] Neo4j PubSub thread did not join in time.")
                    else:
                        self.logger.info("[STOP] Neo4j PubSub thread joined successfully.")
                
                try:
                    remaining = self.neo4j_processor.check_withreturns_status()
                    if sum(remaining.values()) > 0:
                        self.logger.warning(f"[STOP] Some items remain in withreturns after stop: {remaining}")
                except Exception as e:
                    self.logger.error(f"[STOP] Error during final status check: {e}", exc_info=True)
                
                self.neo4j_processor.close()
                self.logger.info("[STOP] Neo4j processor closed")
            except Exception as e:
                self.logger.error(f"[STOP] Error closing Neo4j processor: {e}", exc_info=True)
                
        return results


    def check_status(self):
        return {name: manager.check_status() for name, manager in self.sources.items()}


    def get_source(self, name: str):
        return self.sources.get(name)



    # def _setup_signal_handlers(self):
    #     """Set up signal handlers for graceful shutdown"""
    #     import signal
    #     import sys
        
    #     def signal_handler(sig, frame):
    #         # Check if the handler is running in the main thread
    #         if threading.current_thread() is threading.main_thread():
    #             self.logger.info("Shutdown signal received in main thread. Stopping all components gracefully...")
    #             self.stop()
    #             self.logger.info("Shutdown complete. Exiting.")
    #             sys.exit(0)
    #         else:
    #             # If run in a worker thread (likely due to os._exit triggering signals),
    #             # log it but do NOT call stop() to prevent join errors.
    #             # The process is already terminating via os._exit.
    #             thread_name = threading.current_thread().name
    #             self.logger.warning(f"Shutdown signal {sig} received in worker thread '{thread_name}'. Process is already exiting.")
            
    #     # Register for SIGINT (Ctrl+C) and SIGTERM
    #     signal.signal(signal.SIGINT, signal_handler)
    #     signal.signal(signal.SIGTERM, signal_handler)
    #     self.logger.info("Signal handlers registered for graceful shutdown")

    
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