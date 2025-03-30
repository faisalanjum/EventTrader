import logging
import websocket
import json
import time
import ssl
from datetime import datetime, timezone
from typing import Union
from benzinga.bz_news_schemas import BzWebSocketNews, UnifiedNews
from benzinga.bz_news_errors import NewsErrorHandler
from utils.redisClasses import RedisClient
from utils.log_config import get_logger, setup_logging
import threading


class BenzingaNewsWebSocket:
    """WebSocket client for Benzinga news data with production-grade logging and error handling"""
    
    def __init__(self, api_key: str, redis_client: RedisClient, ttl: int = 3600, 
                log_level: int = logging.INFO):
        """
        Initialize Benzinga WebSocket client
        
        Args:
            api_key: Benzinga API key
            redis_client: Redis client instance
            ttl: TTL for news items in Redis (seconds)
            log_level: Logging level (default: logging.INFO)
        """

        # Set up logger using centralized logging
        self.logger = get_logger("benzinga_news_websocket", log_level)

        # Downtime tracking 
        self._connection_time = None
        self._disconnect_time = None
        self._downtime_logged = False
        self._current_downtime_key = None
        self._had_successful_connection = False


        self.redis_client = redis_client
        self.ttl = ttl
        self.api_key = api_key
        self.url = f"wss://api.benzinga.com/api/v1/news/stream?token={self.api_key}"
        self.error_handler = NewsErrorHandler()
        self.connected = False
        self.ws = None
        
        # Connection settings
        self.should_run = True
        self.base_delay = 2
        self.max_delay = 120  # 2 minute max between retries
        self.current_retry = 0
        self.raw = False
        self.last_message_time = None
        self.last_pong_time = None 
        
        # Try to load the last message time from Redis
        try:
            last_time = self.redis_client.get_json("admin:news:last_message_time")
            if last_time and 'timestamp' in last_time:
                self.last_message_time = datetime.fromisoformat(last_time['timestamp'])                
                self.logger.info(f"Loaded last message time from Redis: {self.last_message_time.isoformat()}")
        except Exception as e:
            self.logger.warning(f"Could not load last message time: {e}")

        # Stats tracking
        self.stats = {
            'messages_received': 0,
            'messages_processed': 0,
        }

        # Thread management
        self.heartbeat_thread = None
        self._lock = threading.Lock()
        self._stats_lock = threading.Lock()

        # Feature flag logging state
        self._feature_flag_logged = False

        self.logger.info("=== BENZINGA NEWS WEBSOCKET INITIALIZED ===")

    @staticmethod
    def print_news_item(item: Union[BzWebSocketNews, UnifiedNews], raw: bool = False):
        """Print news item in raw or unified format"""
        item.print()

    def print_error_stats(self):
        """Print current error statistics"""
        self.logger.info(self.error_handler.get_summary())

    def _check_heartbeat(self):
        """Active connection monitoring thread"""
        while self.should_run:
            if not self.check_connection_health():
                self.logger.warning("Heartbeat check failed, initiating reconnect...")
                if self.ws:
                    self.ws.close()
            time.sleep(10)  # Check every 10 seconds

    def connect(self, raw: bool = False, enable_trace: bool = False):
        """
        Start WebSocket connection with retry logic
        
        Args:
            raw: Whether to use raw format (default: False)
            enable_trace: Enable websocket trace for debugging (default: False)
        """
        # Check feature flag
        from utils.feature_flags import ENABLE_LIVE_DATA
        if not ENABLE_LIVE_DATA:
            # Only log the message once
            if not self._feature_flag_logged:
                self.logger.info("Benzinga live data ingestion disabled by feature flag")
                self._feature_flag_logged = True
            return
        
        self.raw = raw
        self.should_run = True
        self.error_handler.reset_stats()

        # Initialize connection time when attempting to connect
        self._connection_time = datetime.now(timezone.utc)
    
        
        # Check for previous shutdown state
        try:
            shutdown_state = self.redis_client.get_json("admin:news:shutdown_state")
            if shutdown_state and 'timestamp' in shutdown_state:
                last_msg_time = shutdown_state.get('timestamp')
                self.logger.info(f"Previous shutdown detected. Last message time: {last_msg_time}")
                # Could add gap-filling logic here in the future
                
                # Add restart detection logic
                if 'shutdown_time' in shutdown_state:
                    last_shutdown = datetime.fromisoformat(shutdown_state['shutdown_time'])
                    now = datetime.now(timezone.utc)
                    offline_duration = (now - last_shutdown).total_seconds()
                    
                    # Log the restart gap
                    self.logger.info(f"System restart detected. Offline for {offline_duration:.1f} seconds")
                    
                    # Flag this information for backfill system to use later
                    self.redis_client.set_json("admin:backfill:news_restart_gap", {
                        'source': 'news',
                        'last_shutdown': shutdown_state['shutdown_time'],
                        'restart_time': now.isoformat(),
                        'offline_seconds': offline_duration,
                        'last_message_time': shutdown_state.get('timestamp'),
                        'requires_backfill': offline_duration > 30  # Simple threshold
                    })
        except Exception as e:
            self.logger.warning(f"Could not check previous shutdown state: {e}")
        
        # Start heartbeat thread
        if not self.heartbeat_thread or not self.heartbeat_thread.is_alive():
            self.heartbeat_thread = threading.Thread(target=self._check_heartbeat)
            self.heartbeat_thread.daemon = True
            self.heartbeat_thread.start()
        
        self.logger.info(f"Starting WebSocket connection (format: {'raw' if raw else 'unified'})...")
        
        while self.should_run:
            try:
                if enable_trace:
                    websocket.enableTrace(True)
                    
                self.ws = websocket.WebSocketApp(
                    self.url,
                    header={"accept": "application/json"},
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_pong=self._on_pong
                )
                
                # Run with ping/pong for connection health
                self.ws.run_forever(
                    ping_interval=15,
                    ping_timeout=5,
                    sslopt={"cert_reqs": ssl.CERT_NONE}
                )
                
                if not self.should_run:
                    break
                    
            except Exception as e:
                self.error_handler.handle_connection_error(e)
                if not self.should_run:
                    break
                    
                delay = min(self.base_delay * (2 ** self.current_retry), self.max_delay)
                self.current_retry += 1
                self.logger.warning(f"Connection failed. Retrying in {delay:.1f} seconds...")
                time.sleep(delay)
    
    def disconnect(self):
        """Clean shutdown of WebSocket connection"""
        # Mark as intentional disconnect to avoid logging downtime
        self._downtime_logged = True
        
        # Store final state before shutdown
        try:
            current_state = {
                'timestamp': self.last_message_time.isoformat() if self.last_message_time else None,
                'shutdown_time': datetime.now(timezone.utc).isoformat(),
                'is_clean_shutdown': True,
                'messages_processed': self.stats['messages_processed']
            }
            self.redis_client.set_json("admin:news:shutdown_state", current_state)
            self.logger.info("Saved shutdown state to Redis.")
        except Exception as e:
            self.logger.error(f"Failed to save shutdown state: {e}")
            
        self.should_run = False
        if self.ws:
            self.ws.close()
        
        # Wait for heartbeat thread to finish
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=5)
        
        self.logger.info("=== BENZINGA NEWS WEBSOCKET DISCONNECTED ===")

    def _on_open(self, ws):
        """Handle WebSocket connection open"""
        try:
            # Reset stats on each successful connection
            self.error_handler.reset_stats()
            
            now = datetime.now(timezone.utc)
            
            # Complete any pending downtime record if exists
            with self._lock:
                if self._disconnect_time and self._current_downtime_key:
                    try:
                        # Calculate downtime duration
                        downtime_seconds = (now - self._disconnect_time).total_seconds()
                        
                        # Update the existing record with end time
                        downtime_record = self.redis_client.get_json(self._current_downtime_key)
                        if downtime_record:
                            downtime_record['end'] = now.isoformat()
                            downtime_record['downtime_seconds'] = downtime_seconds
                            self.redis_client.set_json(self._current_downtime_key, downtime_record)
                            
                            self.logger.info(f"Downtime ended - Duration: {downtime_seconds:.1f}s - Key: {self._current_downtime_key}")

                    
                    except Exception as e:
                        self.logger.error(f"Failed to update downtime record: {e}")

                # Reset connection tracking state
                self.connected = True
                self._had_successful_connection = True  # Mark that we've had at least one successful connection
                self._connection_time = now
                self._disconnect_time = None
                self._downtime_logged = False
                self._current_downtime_key = None
                                            

            self.logger.info("=== BENZINGA NEWS WEBSOCKET CONNECTED ===")
            
            # Subscribe to news stream
            if self.connected and ws and ws.sock:
                subscription = {
                    "action": "subscribe",
                    "data": {"streams": ["news"]}
                }
                ws.send(json.dumps(subscription))
        except Exception as e:
            self.connected = False
            self.logger.error(f"Error in on_open: {e}")
            if ws:
                try:
                    ws.close()
                except:
                    pass

    def _on_message(self, ws, message: str):
        """Handle incoming WebSocket message"""
        with self._stats_lock:
            now = datetime.now(timezone.utc)
            self.last_message_time = now
            self.current_retry = 0  # Reset retry counter on successful message

            try:
                self.stats['messages_received'] += 1
                
                if message.isdigit():
                    # Heartbeat message, no need to process
                    if int(message) % 100 == 0:  # Log only occasionally to reduce noise
                        self.logger.debug(f"Heartbeat received: {message}")
                    
                    return  # Skip processing for heartbeat messages
                
                # Check feature flag to avoid unnecessary processing
                from utils.feature_flags import ENABLE_LIVE_DATA
                if not ENABLE_LIVE_DATA:
                    # Don't log this message for every message received
                    return
                
                data = json.loads(message)
                
                # Process item based on raw setting for display
                processed_item = self.error_handler.process_news_item(data, self.raw)
                if processed_item:
                    # Always store unified version in Redis
                    unified_item = self.error_handler.process_news_item(data, raw=False)
                    if self.redis_client.set_news(unified_item, ex=self.ttl):
                        # Only print news items at debug level to reduce console spam
                        if self.logger.isEnabledFor(logging.DEBUG):
                            self.print_news_item(processed_item)
                        self.stats['messages_processed'] += 1
                        
                        # Persist the last message time to Redis
                        try:
                            self.redis_client.set_json("admin:news:last_message_time", {
                                'timestamp': now.isoformat(),
                                'message_id': getattr(unified_item, 'id', None),
                                'updated_at': datetime.now(timezone.utc).isoformat()
                            })
                        except Exception as e:
                            self.logger.warning(f"Failed to update last message time in Redis: {e}")
                
                # Log stats periodically to reduce console spam
                if self.stats['messages_processed'] % 100 == 0:
                    self._log_stats()
                
            except json.JSONDecodeError as je:
                self.logger.error(f"Failed to parse message: {message[:100]}...")
                self.error_handler.handle_json_error(je, message)
            except Exception as e:
                self.logger.error(f"Unexpected error processing message: {str(e)}")
                self.error_handler.handle_unexpected_error(e)

    def _on_error(self, ws, error):
        """Handle WebSocket error"""
        self.connected = False
        self.logger.error(f"WebSocket error: {error}")
        self.error_handler.handle_connection_error(error)
        
        # Log downtime with appropriate error code
        error_str = str(error)
        if any(msg in error_str.lower() for msg in ["closed", "lost", "timed out", "refused", "reset"]):
            self.logger.warning(f"Network error detected: {error}")
            self._log_downtime(status_code=1001)  # Going Away
        else:
            self._log_downtime(status_code=1006)  # Abnormal Closure

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        self.connected = False
        
        self.logger.info(f"Connection closed. Status: {close_status_code}, Message: {close_msg}")
        
        # Log downtime
        status = close_status_code if close_status_code else 1006
        self._log_downtime(status_code=status)

        # Exit if shutdown requested
        if not self.should_run:
            return
        
        # Check status code
        if close_status_code == 503:
            self.logger.warning("Service temporarily unavailable. Will retry with backoff.")
        
        # Only log error stats at info level or above
        if self.logger.isEnabledFor(logging.INFO):
            self.print_error_stats()
            
        # Calculate delay and attempt reconnection
        delay = min(self.base_delay * (2 ** self.current_retry), self.max_delay)
        self.current_retry += 1
        
        self.logger.info(f"Reconnecting in {delay:.1f} seconds...")
        time.sleep(delay)
        
        # Attempt reconnection
        self.connect(raw=self.raw)

    def _log_stats(self):
        """Log WebSocket statistics - for internal use"""
        stats_summary = (
            f"WebSocket Statistics: "
            f"Received: {self.stats['messages_received']}, "
            f"Processed: {self.stats['messages_processed']}"
        )
        
        if self.last_message_time:
            stats_summary += f", Last Message: {self.last_message_time.isoformat()}"
        
        success_rate = 0
        if self.stats['messages_received'] > 0:
            success_rate = (self.stats['messages_processed']/self.stats['messages_received'])*100
        stats_summary += f", Success Rate: {success_rate:.1f}%"
        
        self.logger.info(stats_summary)
        
        # Periodically update last message timestamp in Redis
        if self.last_message_time and self.stats['messages_processed'] % 100 == 0:
            try:
                self.redis_client.set_json("admin:news:last_message_time", {
                    'timestamp': self.last_message_time.isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat(),
                    'message_count': self.stats['messages_processed']
                })
            except Exception as e:
                self.logger.warning(f"Failed to update periodic stats in Redis: {e}")

    def print_stats(self):
        """Print current statistics (for external calls)"""
        self._log_stats()
        # Log error handler stats at debug level to reduce noise
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(self.error_handler.get_summary())

    def check_connection_health(self):
        """Connection health check"""
        if self.connected and self.ws:
            return True
        return True  # Let _on_error and _on_close handle actual disconnects

    def _on_pong(self, ws, message):
        """Handle pong response"""
        self.last_pong_time = datetime.now(timezone.utc)
        # Only log at debug level to reduce noise
        self.logger.debug(f"Pong received at {self.last_pong_time.isoformat()}")


    def _log_downtime(self, status_code):
        """Log connection downtime to Redis - only called from _on_error and _on_close"""
        # Only log one downtime entry per disconnection
        with self._lock:
            if not self._downtime_logged:
                now = datetime.now(timezone.utc)
                
                # Only log downtime if we've had at least one successful connection
                if self._connection_time and self._had_successful_connection:
                    # Store disconnect time for later update when connection is restored
                    self._disconnect_time = now
                    
                    # Create initial downtime record - will be updated when reconnected
                    downtime = {
                        'start': now.isoformat(),  # When the disconnect occurred
                        'connection_start': self._connection_time.isoformat(),  # When connection started
                        'uptime_seconds': (now - self._connection_time).total_seconds(),
                        'status': str(status_code),
                        'source': 'news',
                        'end': None,  # Will be filled when reconnected
                        'downtime_seconds': None,  # Will be filled when reconnected
                        'backfilled': False  # Flag to indicate whether data for this period has been backfilled
                    }
                    
                    try:
                        key = f"admin:websocket_downtime:news:{now.timestamp()}"
                        success = self.redis_client.set_json(key, downtime)
                        
                        self._current_downtime_key = key
                        self.logger.warning(f"Connection lost at {now.isoformat()}. Status: {status_code}. Key: {key}")
                        
                        # Mark that we logged this disconnection
                        self._downtime_logged = True
                    except Exception as e:
                        self.logger.error(f"Error logging downtime: {e}")
                else:
                    if self._had_successful_connection:
                        self.logger.warning("Connection lost but no connection start time recorded. Skipping downtime logging.")
                    else:
                        self.logger.warning("Connection lost but no successful connection has been established yet. Skipping downtime logging.")