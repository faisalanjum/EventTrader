import websocket
import json
import time
import ssl
from datetime import datetime, timezone
from typing import Optional, Union, Dict
from redisDB.redisClasses import RedisClient
import threading
from .sec_schemas import SECFilingSchema, UnifiedReport
from .sec_errors import FilingErrorHandler
import logging

class SECWebSocket:

    # Define constants matching run_forever parameters for health checks
    PING_INTERVAL = 15 # Default seconds
    PING_TIMEOUT = 5   # Default seconds

    def __init__(self, api_key: str, redis_client: RedisClient, ttl: int = 7*24*3600, log_level: int = logging.INFO):
        # Core configuration
        self.redis_client = redis_client
        self.ttl = ttl
        self.api_key = api_key
        self.url = f"wss://stream.sec-api.io?apiKey={self.api_key}"
        
        # Use standard logger
        self.logger = logging.getLogger(__name__)
        
        # State tracking
        self.connected = False
        self.ws = None
        self.should_run = True
        self.raw = False
        
        # Timing tracking
        self.last_message_time = None
        self.last_pong_time = None
        
        # Try to load the last message time from Redis
        try:
            last_time = self.redis_client.get_json("admin:reports:last_message_time")
            if last_time and 'timestamp' in last_time:
                self.last_message_time = datetime.fromisoformat(last_time['timestamp'])
                self.logger.info(f"Loaded last message time from Redis: {self.last_message_time.isoformat()}")
        except Exception as e:
            self.logger.warning(f"Could not load last message time: {e}")
        
        # Reconnection parameters
        self.base_delay = 2
        self.max_delay = 60
        self.current_retry = 0
        
        # Stats tracking
        self.stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'connection_attempts': 0,
        }
        
        # Thread management
        self.heartbeat_thread = None
        self._lock = threading.Lock()
        self._stats_lock = threading.Lock()
        
        # Error handling
        self.error_handler = FilingErrorHandler()
        
        # Downtime tracking
        self._connection_time = None
        self._disconnect_time = None
        self._downtime_logged = False
        self._current_downtime_key = None
        self._had_successful_connection = False
        
        # Feature flag logging state
        self._feature_flag_logged = False
            
        self.logger.info("=== SEC REPORTS WEBSOCKET INITIALIZED ===")

    def connect(self, raw: bool = False, enable_trace: bool = False):
        """Start WebSocket connection"""
        # Check feature flag
        from config.feature_flags import ENABLE_LIVE_DATA
        if not ENABLE_LIVE_DATA:
            # Only log the message once
            if not self._feature_flag_logged:
                self.logger.info("SEC live data ingestion disabled by feature flag")
                self._feature_flag_logged = True
            return
        
        self.raw = raw
        self.should_run = True
        self.error_handler.reset_stats()
        
        # Initialize connection time if first connection
        if self._connection_time is None:
            self._connection_time = datetime.now(timezone.utc)
            self.logger.info(f"Initializing first connection time: {self._connection_time.isoformat()}")
        
        # Check for previous shutdown state
        try:
            shutdown_state = self.redis_client.get_json("admin:reports:shutdown_state")
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
                    self.redis_client.set_json("admin:backfill:reports_restart_gap", {
                        'source': 'reports',
                        'last_shutdown': shutdown_state['shutdown_time'],
                        'restart_time': now.isoformat(),
                        'offline_seconds': offline_duration,
                        'last_message_time': shutdown_state.get('timestamp'),
                        'requires_backfill': offline_duration > 30  # Simple threshold
                    })
        except Exception as e:
            self.logger.warning(f"Could not check previous shutdown state: {e}")
        
        # Start heartbeat thread if not already running
        if not self.heartbeat_thread or not self.heartbeat_thread.is_alive():
            self.heartbeat_thread = threading.Thread(target=self._check_heartbeat)
            self.heartbeat_thread.daemon = True
            self.heartbeat_thread.start()
            self.logger.info("Started heartbeat monitoring thread")
        
        self.logger.info("Starting SEC WebSocket connection...")
        
        while self.should_run:
            try:
                self.stats['connection_attempts'] += 1
                self.logger.info(f"Connection attempt #{self.stats['connection_attempts']}")
                
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
                    ping_interval=self.PING_INTERVAL,
                    ping_timeout=self.PING_TIMEOUT,
                    sslopt={"cert_reqs": ssl.CERT_NONE}
                )
                
                if not self.should_run:
                    self.logger.info("SEC WebSocket shutting down...")
                    break
                
                # Calculate delay with exponential backoff
                delay = min(self.base_delay * (2 ** self.current_retry), self.max_delay)
                self.current_retry += 1
                
                self.logger.info(f"Reconnecting in {delay:.1f} seconds...")
                time.sleep(delay)
                
            except Exception as e:
                self.logger.error(f"Connection error: {str(e)}", exc_info=True)
                
                if not self.should_run:
                    break
                
                # Use backoff for exceptions as well
                delay = min(self.base_delay * (2 ** self.current_retry), self.max_delay)
                self.current_retry += 1
                time.sleep(delay)

    # def _check_heartbeat(self):
    #     """Active connection monitoring"""
    #     self.logger.info("Heartbeat monitoring started")
        
    #     while self.should_run:
    #         try:
    #             if not self.check_connection_health():
    #                 self.logger.warning("Heartbeat check failed, initiating reconnect...")
    #                 if self.ws:
    #                     self.ws.close()
    #             time.sleep(10)  # Check every 10 seconds
    #         except Exception as e:
    #             self.logger.error(f"Error in heartbeat check: {str(e)}")
    #             time.sleep(1)



    def _check_heartbeat(self):
        """Active connection monitoring thread. Checks health and forces close if needed."""
        # Add a small initial delay to allow connection setup before first check
        initial_delay = self.PING_INTERVAL # Wait at least one ping interval
        self.logger.info(f"Heartbeat thread started. Initial check in {initial_delay}s.")
        time.sleep(initial_delay)

        while self.should_run:
            # Use PING_INTERVAL as the base check frequency
            check_interval = self.PING_INTERVAL
            try:
                if not self.check_connection_health():
                    self.logger.warning("Heartbeat check failed (unhealthy connection detected), initiating close for reconnect...")
                    if self.ws:
                        try:
                            # Closing the ws triggers _on_close, which handles reconnect logic
                            self.ws.close()
                            # After forcing close, wait longer before the *next* check
                            # to give the reconnect attempt time. _on_close handles immediate retry delay.
                            check_interval = self.max_delay / 2
                        except Exception as e:
                            self.logger.error(f"Exception during ws.close() in heartbeat: {e}", exc_info=True)
                            # Still wait longer if close fails to avoid hammering
                            check_interval = self.max_delay / 2
                else:
                    if self.logger.isEnabledFor(logging.DEBUG):
                       self.logger.debug("Heartbeat check passed.")

            except Exception as e:
                self.logger.error(f"Unexpected error in heartbeat check loop: {e}", exc_info=True)
                # Prevent tight loop on unexpected error, wait a bit longer
                check_interval = 30

            # Wait before next check
            # Ensure we don't sleep for a negative or zero interval
            sleep_time = max(1, check_interval)
            time.sleep(sleep_time)

    
    # def check_connection_health(self):
    #     """Simplest possible connection check that won't false positive"""
    #     if self.connected and self.ws:
    #         return True
    #     return True  # Let _on_error and _on_close handle actual disconnects




    def check_connection_health(self):
        """Accurate WebSocket health check using connection status and PONG activity."""
        # 1. Check basic connection flags and objects
        if not self.connected or not self.ws or not self.ws.sock:
            self.logger.debug("Health check failed: Not connected or ws/socket object missing.")
            return False

        # 2. Check time since last PONG received
        now = datetime.now(timezone.utc)
        # Calculate threshold dynamically based on defined constants + buffer
        max_pong_silence = max(30, self.PING_INTERVAL * 2 + self.PING_TIMEOUT)

        if self.last_pong_time:
            # last_pong_time is already timezone-aware
            time_since_last_pong = (now - self.last_pong_time).total_seconds()
            if time_since_last_pong > max_pong_silence:
                self.logger.warning(f"No PONG received in {time_since_last_pong:.1f}s (threshold: {max_pong_silence}s). Assuming low-level connection issue.")
                return False
        else:
            # No pongs received yet since connection or last check. Check how long we've been connected.
            if self._connection_time:
                time_since_connect = (now - self._connection_time).total_seconds()
                # Don't fail immediately, give time for the first pong exchange(s)
                if time_since_connect > max_pong_silence:
                    self.logger.warning(f"Connected for {time_since_connect:.1f}s but no PONG received yet (threshold: {max_pong_silence}s). Assuming connection issue.")
                    return False
            # else: _connection_time not set, unlikely state, can't check duration yet.

        # If all checks pass, connection seems healthy
        return True



    def disconnect(self):
        """Clean shutdown"""
        # Mark as intentional disconnect to avoid logging downtime
        self._downtime_logged = True
        
        # Always store final state before shutdown
        try:
            current_state = {
                'timestamp': self.last_message_time.isoformat() if self.last_message_time else None,
                'shutdown_time': datetime.now(timezone.utc).isoformat(),
                'is_clean_shutdown': True,
                'filings_processed': self.stats['messages_processed']
            }
            self.redis_client.set_json("admin:reports:shutdown_state", current_state)
            self.logger.info("Saved shutdown state to Redis.")
        except Exception as e:
            self.logger.error(f"Failed to save shutdown state: {e}", exc_info=True)
        
        self.logger.info("Initiating WebSocket shutdown...")
        self.should_run = False
        
        if self.ws:
            self.ws.close()
            
        # Wait for heartbeat thread to complete
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=5)
            
        self.logger.info("=== SEC REPORTS WEBSOCKET DISCONNECTED ===")

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
                        self.logger.error(f"Failed to update downtime record: {e}", exc_info=True)
                
                # Reset connection tracking state
                self.connected = True
                self._had_successful_connection = True
                self._connection_time = now
                self._disconnect_time = None
                self._downtime_logged = False
                self._current_downtime_key = None
                self.current_retry = 0
            
            self.logger.info("=== SEC REPORTS WEBSOCKET CONNECTED ===")
        except Exception as e:
            self.logger.error(f"Error in on_open: {e}", exc_info=True)

    def _on_message(self, ws, message: str):
        """Handle incoming WebSocket message"""
        # Check feature flag to avoid unnecessary processing
        from config.feature_flags import ENABLE_LIVE_DATA
        if not ENABLE_LIVE_DATA:
            # Don't log this message for every message received
            return
            
        with self._stats_lock:
            # Always update message time, even for heartbeats
            now = datetime.now(timezone.utc)
            self.last_message_time = now
            self.current_retry = 0  # Reset retry counter on successful message
            
            try:
                self.stats['messages_received'] += 1
                
                # Consider numeric messages as heartbeats
                if message.isdigit():
                    if int(message) % 100 == 0:  # Log only occasionally to reduce noise
                        self.logger.debug(f"Heartbeat: {message}")
                    
                    # Removing heartbeat Redis update to ensure last_message_time only shows actual filings
                    return
                    
                filings = json.loads(message)
                self.logger.info(f"Parsed {len(filings)} filings from message")
                
                processed_count = 0
                for idx, filing in enumerate(filings, 1):
                    self.logger.info(f"Processing filing {idx}/{len(filings)}")
                    self.logger.debug(f"Form Type: {filing.get('formType')}")
                    self.logger.debug(f"Accession No: {filing.get('accessionNo')}")
                    
                    # First attempt to process filing
                    unified_filing = self.error_handler.process_filing(filing, raw=False)
                    if unified_filing:
                        self.logger.debug(f"Successfully created UnifiedReport")
                        
                        # Attempt to store in Redis
                        if self.redis_client.set_filing(unified_filing, ex=self.ttl):
                            self.logger.debug(f"Successfully stored in Redis")
                            
                            # If raw display needed, get raw version
                            if self.raw and self.logger.isEnabledFor(logging.DEBUG):
                                display_filing = self.error_handler.process_filing(filing, raw=True)
                                if display_filing:
                                    display_filing.print()
                            elif self.logger.isEnabledFor(logging.DEBUG):
                                unified_filing.print()
                                
                            processed_count += 1
                        else:
                            self.logger.error(f"Failed to store in Redis")
                    else:
                        self.logger.error(f"Failed to create UnifiedReport")
                        self.logger.error(f"Original filing data: {json.dumps(filing, indent=2)}")
                
                # Update stats
                self.stats['messages_processed'] += processed_count
                
                # Persist the last message time to Redis after successful processing
                if processed_count > 0:
                    try:
                        accession_no = filings[-1].get('accessionNo', 'unknown') if filings else 'unknown'
                        message_data = {
                            'timestamp': now.isoformat(),
                            'accession_no': accession_no,
                            'filings_count': len(filings),
                            'updated_at': datetime.now(timezone.utc).isoformat()
                        }
                        self.redis_client.set_json("admin:reports:last_message_time", message_data)
                        self.logger.debug(f"Updated last message time in Redis: {accession_no}")
                    except Exception as e:
                        self.logger.warning(f"Failed to update last message time in Redis: {e}")
                
                # Only log stats occasionally to reduce noise
                if self.stats['messages_processed'] % 5 == 0 or processed_count > 0:
                    self._log_stats()
                
            except json.JSONDecodeError as je:
                self.logger.error(f"JSON decode error: {str(je)}", exc_info=True)
                self.error_handler.handle_json_error(je, message)
            except Exception as e:
                self.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
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
        elif "429" in error_str:
            self.logger.warning("Rate limit hit - using exponential backoff")
            self.current_retry = max(self.current_retry, 3)
            self._log_downtime(status_code=429)  # Rate limit exceeded
        else:
            self._log_downtime(status_code=1006)  # Abnormal Closure

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        self.connected = False
        
        self.logger.info(f"=== SEC REPORTS WEBSOCKET DISCONNECTED ===")
        self.logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")
        
        # Log downtime
        status = close_status_code if close_status_code else 1006   # Default toAbnormal Closure
        self._log_downtime(status_code=status)

        # Exit if shutdown requested
        if not self.should_run:
            self.logger.info("Shutdown requested, not attempting reconnect.")
            return
            
        # Reconnection is handled by the main connect loop's retry mechanism
        self.logger.info("Connection closed. Reconnect will be attempted by the main loop.")



    def _on_pong(self, ws, message):
        """Handle pong response"""
        with self._lock:
            self.last_pong_time = datetime.now(timezone.utc)

            # Only log at debug level to reduce noise
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(f"Received pong at {self.last_pong_time.isoformat()}")            

    def _log_stats(self):
        """Log WebSocket statistics (internal use)"""
        stats_summary = (
            f"SEC WebSocket Stats: "
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
        
    def print_stats(self):
        """Print WebSocket statistics (for external calls)"""
        self._log_stats()
        
        # Detailed stats for debug level
        if self.logger.isEnabledFor(logging.DEBUG):
            self.error_handler.print_stats()

    def _log_downtime(self, status_code):
        """Log connection downtime to Redis - only called from _on_error and _on_close"""
        # Only log one downtime entry per disconnection
        with self._lock:
            self.logger.debug(f"_log_downtime called with status_code={status_code}, _downtime_logged={self._downtime_logged}, _connection_time={self._connection_time}")
            if not self._downtime_logged:
                now = datetime.now(timezone.utc)
                
                # Only log downtime if we've ever had a successful connection
                if self._connection_time and self._had_successful_connection:
                    # Store disconnect time for later update when connection is restored
                    self._disconnect_time = now
                    
                    # Create initial downtime record - will be updated when reconnected
                    downtime = {
                        'start': now.isoformat(),  # When the disconnect occurred
                        'connection_start': self._connection_time.isoformat(),  # When connection started
                        'uptime_seconds': (now - self._connection_time).total_seconds(),
                        'status': str(status_code),
                        'source': 'reports',  # Hardcode to 'reports' for SEC
                        'end': None,  # Will be filled when reconnected
                        'downtime_seconds': None,  # Will be filled when reconnected
                        'backfilled': False  # Flag to indicate whether data for this period has been backfilled
                    }
                    
                    try:
                        key = f"admin:websocket_downtime:reports:{now.timestamp()}"
                        success = self.redis_client.set_json(key, downtime)
                        
                        if success:
                            self._current_downtime_key = key
                            self.logger.warning(f"Connection lost at {now.isoformat()}. Status: {status_code}. Key: {key}")
                            
                            # Mark that we logged this disconnection
                            self._downtime_logged = True
                        else:
                            self.logger.error(f"Failed to save downtime to Redis: {key}")
                    except Exception as e:
                        self.logger.error(f"Error logging downtime: {e}", exc_info=True)
                else:
                    if self._had_successful_connection:
                        self.logger.warning("Connection lost but no connection start time recorded. Skipping downtime logging.")
                    else:
                        self.logger.warning("Connection lost but no successful connection has been established yet. Skipping downtime logging.")
            else:
                self.logger.debug(f"Skipping duplicate downtime logging for status_code={status_code}")