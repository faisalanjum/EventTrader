import websocket
import json
import time
import ssl
from datetime import datetime, timezone
from typing import Optional, Union, Dict
from utils.redisClasses import RedisClient
import threading
from SEC_API_Files.sec_schemas import SECFilingSchema, UnifiedReport
from SEC_API_Files.sec_errors import FilingErrorHandler
import logging

class SECWebSocket:
    def __init__(self, api_key: str, redis_client: RedisClient, ttl: int = 7*24*3600):
        # Core configuration
        self.redis_client = redis_client
        self.ttl = ttl
        self.api_key = api_key
        self.url = f"wss://stream.sec-api.io?apiKey={self.api_key}"
        
        # State tracking
        self.connected = False
        self.ws = None
        self.should_run = True
        self.raw = False
        
        # Timing tracking
        self.last_message_time = None
        self.last_pong_time = None
        self._connection_time = None
        
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
        
        # Logging setup
        self.logger = logging.getLogger("reports_websocket")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            
        print("=== SEC REPORTS WEBSOCKET INITIALIZED ===")
        self.logger.info("=== SEC REPORTS WEBSOCKET INITIALIZED ===")

    def connect(self, raw: bool = False, enable_trace: bool = False):
        """Start WebSocket connection"""
        self.raw = raw
        self.should_run = True
        self.error_handler.reset_stats()
        
        # Start heartbeat thread if not already running
        if not self.heartbeat_thread or not self.heartbeat_thread.is_alive():
            self.heartbeat_thread = threading.Thread(target=self._check_heartbeat)
            self.heartbeat_thread.daemon = True
            self.heartbeat_thread.start()
            print("Started heartbeat monitoring thread")
            self.logger.info("Started heartbeat monitoring thread")
        
        print("Starting SEC WebSocket connection...")
        self.logger.info("Starting SEC WebSocket connection...")
        
        while self.should_run:
            try:
                self.stats['connection_attempts'] += 1
                print(f"Connection attempt #{self.stats['connection_attempts']}")
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
                    ping_interval=15,
                    ping_timeout=5,
                    sslopt={"cert_reqs": ssl.CERT_NONE}
                )
                
                if not self.should_run:
                    self.logger.info("SEC WebSocket shutting down...")
                    break
                
                # Calculate delay with exponential backoff
                delay = min(self.base_delay * (2 ** self.current_retry), self.max_delay)
                self.current_retry += 1
                
                print(f"Reconnecting in {delay:.1f} seconds...")
                self.logger.info(f"Reconnecting in {delay:.1f} seconds...")
                time.sleep(delay)
                
            except Exception as e:
                self.logger.error(f"Connection error: {str(e)}")
                print(f"Connection error: {str(e)}")
                
                if not self.should_run:
                    break
                
                # Use backoff for exceptions as well
                delay = min(self.base_delay * (2 ** self.current_retry), self.max_delay)
                self.current_retry += 1
                time.sleep(delay)

    def _check_heartbeat(self):
        """Active connection monitoring"""
        self.logger.info("Heartbeat monitoring started")
        print("Heartbeat monitoring started")
        
        while self.should_run:
            try:
                if not self.check_connection_health():
                    self.logger.warning("Heartbeat check failed, initiating reconnect...")
                    print("Heartbeat check failed, initiating reconnect...")
                    if self.ws:
                        self.ws.close()
                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                self.logger.error(f"Error in heartbeat check: {str(e)}")
                time.sleep(1)
    
    def check_connection_health(self):
        """Simplest possible connection check that won't false positive"""
        # Only consider a connection down if the socket itself is gone or we've 
        # received an explicit error/close event
        if self.connected and self.ws:
            # The WebSocket is still connected as far as we know
            # Don't log any downtime based on message timing
            return True
        return True  # Always return True - let _on_error and _on_close handle actual disconnects


    def disconnect(self):
        """Clean shutdown"""
        self.logger.info("Initiating WebSocket shutdown...")
        self.should_run = False
        if self.ws:
            self.ws.close()
        
        # Wait for heartbeat thread to finish
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=5)

    def _on_open(self, ws):
        """Handle WebSocket connection open"""
        self.connected = True
        self._connection_time = datetime.now(timezone.utc)
        self.current_retry = 0
        self._disconnection_logged = False 
        
        self.logger.info("=== SEC REPORTS WEBSOCKET CONNECTED ===")
        print("=== SEC REPORTS WEBSOCKET CONNECTED ===")

    def _on_message(self, ws, message: str):
        """Handle incoming WebSocket message"""
        with self._stats_lock:
            # Always update message time, even for heartbeats
            self.last_message_time = datetime.now(timezone.utc)
            self.current_retry = 0  # Reset retry counter on successful message
            
            try:
                self.stats['messages_received'] += 1
                
                # Consider numeric messages as heartbeats
                if message.isdigit():
                    self.logger.info(f"Heartbeat: {message}")
                    return
                    
                filings = json.loads(message)
                self.logger.info(f"Parsed {len(filings)} filings from message")
                
                for idx, filing in enumerate(filings, 1):
                    self.logger.info(f"Processing filing {idx}/{len(filings)}")
                    self.logger.info(f"Form Type: {filing.get('formType')}")
                    self.logger.info(f"Accession No: {filing.get('accessionNo')}")
                    
                    # First attempt to process filing
                    unified_filing = self.error_handler.process_filing(filing, raw=False)
                    if unified_filing:
                        self.logger.info(f"Successfully created UnifiedReport")
                        
                        # Attempt to store in Redis
                        if self.redis_client.set_filing(unified_filing, ex=self.ttl):
                            self.logger.info(f"Successfully stored in Redis")
                            
                            # If raw display needed, get raw version
                            if self.raw:
                                display_filing = self.error_handler.process_filing(filing, raw=True)
                                if display_filing:
                                    display_filing.print()
                            else:
                                unified_filing.print()
                                
                            self.stats['messages_processed'] += 1
                        else:
                            self.logger.error(f"Failed to store in Redis")
                    else:
                        self.logger.error(f"Failed to create UnifiedReport")
                        self.logger.error(f"Original filing data: {json.dumps(filing, indent=2)}")
                
                self.print_stats()
                
            except json.JSONDecodeError as je:
                self.logger.error(f"JSON decode error: {str(je)}")
                self.error_handler.handle_json_error(je, message)
            except Exception as e:
                self.logger.error(f"Unexpected error: {str(e)}")
                self.error_handler.handle_unexpected_error(e)

    def _on_error(self, ws, error):
        """Handle WebSocket error"""
        self.connected = False
        self.logger.error(f"WebSocket error: {error}")
        print(f"WebSocket error: {error}")
        
        # Log network-related errors as disconnections
        error_str = str(error)
        if any(msg in error_str.lower() for msg in ["closed", "lost", "timed out", "refused", "reset"]):
            self.logger.warning(f"Network error detected: {error}")
            self._log_downtime(status_code=1001)  # Going Away
        
        # Rate limiting
        elif "429" in error_str:
            self.logger.warning("Rate limit hit - using exponential backoff")
            self.current_retry = max(self.current_retry, 3)
            self._log_downtime(status_code=429)
        
        # Other errors
        else:
            self._log_downtime(status_code=1006)  # Abnormal Closure

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        self.connected = False
        self.logger.info(f"=== SEC REPORTS WEBSOCKET DISCONNECTED ===")
        print(f"=== SEC REPORTS WEBSOCKET DISCONNECTED ===")
        self.logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")
        
        # Log downtime with appropriate status code
        status = close_status_code if close_status_code else 1006
        self._log_downtime(status_code=status)

    def _on_pong(self, ws, message):
        """Handle pong response"""
        with self._lock:
            self.last_pong_time = datetime.now(timezone.utc)
            self.logger.debug(f"Received pong at {self.last_pong_time.isoformat()}")



    def _log_downtime(self, status_code):
        """Log connection downtime to Redis - only called from _on_error and _on_close"""
        # Only log one downtime entry per disconnection
        with self._lock:
            # Check if we already logged this disconnection
            if not hasattr(self, '_disconnection_logged') or not self._disconnection_logged:
                disconnect_time = datetime.now(timezone.utc)
                reference_time = self._connection_time
                
                if reference_time:
                    duration = (disconnect_time - reference_time).total_seconds()
                    
                    downtime = {
                        'start': reference_time.isoformat(),
                        'end': disconnect_time.isoformat(),
                        'duration': duration,
                        'status': str(status_code),
                        'source': 'reports',  # Hardcode to 'reports' for SEC
                    }
                    
                    try:
                        # Simple key format that works for news without duplicates
                        key = f"admin:websocket_downtime:{downtime['source']}:{disconnect_time.timestamp()}"
                        success = self.redis_client.set_json(key, downtime)
                        
                        if success:
                            log_msg = f"{downtime['source'].upper()} connection lost. Status: {status_code}. Key: {key}"
                            self.logger.warning(log_msg)
                            print(f"DOWNTIME LOGGED: {log_msg}")
                            
                            # Mark that we logged this disconnection
                            self._disconnection_logged = True
                        else:
                            self.logger.error(f"Failed to save downtime to Redis: {key}")
                    except Exception as e:
                        self.logger.error(f"ERROR LOGGING DOWNTIME: {e}")
                        print(f"ERROR LOGGING DOWNTIME: {e}")


                    

    def print_stats(self):
        """Print WebSocket statistics"""
        stats_summary = (
            f"\nSEC WebSocket Statistics:\n"
            f"Messages Received: {self.stats['messages_received']}\n"
            f"Filings Processed: {self.stats['messages_processed']}\n"
        )
        
        if self.last_message_time:
            stats_summary += f"Last Message: {self.last_message_time.isoformat()}\n"
            
        stats_summary += f"Success Rate: {(self.stats['messages_processed']/max(1, self.stats['messages_received']))*100:.1f}%"
        
        self.logger.info(stats_summary)
        print(stats_summary)