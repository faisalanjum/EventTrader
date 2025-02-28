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


class SECWebSocket:
    """WebSocket client for SEC filing data"""
    
    def __init__(self, api_key: str, redis_client: RedisClient, ttl: int = 7*24*3600):
        self.redis_client = redis_client
        self.ttl = ttl
        self.api_key = api_key
        self.url = f"wss://stream.sec-api.io?apiKey={self.api_key}"
        self.error_handler = FilingErrorHandler()
        self.connected = False
        self.ws = None
        
        self.should_run = True
        self.base_delay = 2
        self.max_delay = 300 # 5 minutes max between retries
        self.current_retry = 0
        self.raw = False
        self.last_message_time = None
        self.last_pong_time = None

        self.stats = {
            'messages_received': 0,
            'messages_processed': 0,
        }

        self.heartbeat_thread = None
        self._lock = threading.Lock()   # Add thread lock
        self._stats_lock = threading.Lock() # Separate lock for stats


    def _check_heartbeat(self):
        """Active connection monitoring"""
        while self.should_run:
            if not self.check_connection_health():
                print("Heartbeat check failed, initiating reconnect...")
                if self.ws:
                    self.ws.close()
            time.sleep(10) # Check every 10 seconds

    def connect(self, raw: bool = False, enable_trace: bool = False):
        """Start WebSocket connection with retry logic"""
        self.raw = raw
        self.should_run = True
        self.error_handler.reset_stats()
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self._check_heartbeat)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
        
        print(f"Starting SEC WebSocket connection...")
        
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
                
                self.ws.run_forever(
                    ping_interval=15,
                    ping_timeout=5,
                    sslopt={"cert_reqs": ssl.CERT_NONE}
                )
                
                if not self.should_run:
                    break
                    
            except Exception as e:
                print(f"Connection error: {e}")
                if not self.should_run:
                    break
                    
                delay = min(self.base_delay * (2 ** self.current_retry), self.max_delay)
                self.current_retry += 1
                print(f"Connection failed. Retrying in {delay:.1f} seconds...")
                time.sleep(delay)

    def disconnect(self):
        """Clean shutdown"""
        self.should_run = False
        if self.ws:
            self.ws.close()
        
        # Wait for heartbeat thread to finish
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=5)

    def _on_open(self, ws):
        """Handle WebSocket connection open"""
        print(f"Connected to SEC WebSocket at {datetime.now()}")
        self.connected = True



    def _on_message(self, ws, message: str):
        """Handle incoming WebSocket message"""
        with self._stats_lock:
            self.last_message_time = datetime.now(timezone.utc)
            self.current_retry = 0

            try:
                self.stats['messages_received'] += 1
                print(f"\n[WebSocket Debug] Received message #{self.stats['messages_received']}")
                
                if message.isdigit():
                    print(f"[WebSocket Debug] Heartbeat: {message}")
                    return
                    
                filings = json.loads(message)
                print(f"[WebSocket Debug] Parsed {len(filings)} filings from message")
                
                for idx, filing in enumerate(filings, 1):
                    print(f"\n[WebSocket Debug] Processing filing {idx}/{len(filings)}")
                    print(f"[WebSocket Debug] Form Type: {filing.get('formType')}")
                    print(f"[WebSocket Debug] Accession No: {filing.get('accessionNo')}")
                    
                    # First attempt to process filing
                    unified_filing = self.error_handler.process_filing(filing, raw=False)
                    if unified_filing:
                        print(f"[WebSocket Debug] ✅ Successfully created UnifiedReport")
                        
                        # Attempt to store in Redis
                        if self.redis_client.set_filing(unified_filing, ex=self.ttl):
                            print(f"[WebSocket Debug] ✅ Successfully stored in Redis")
                            
                            # If raw display needed, get raw version
                            if self.raw:
                                display_filing = self.error_handler.process_filing(filing, raw=True)
                                if display_filing:
                                    display_filing.print()
                            else:
                                unified_filing.print()
                                
                            self.stats['messages_processed'] += 1
                        else:
                            print(f"[WebSocket Debug] ❌ Failed to store in Redis")
                    else:
                        print(f"[WebSocket Debug] ❌ Failed to create UnifiedReport")
                        print(f"[WebSocket Debug] Original filing data: {json.dumps(filing, indent=2)}")
                
                self.print_stats()
                
            except json.JSONDecodeError as je:
                print(f"[WebSocket Debug] ❌ JSON decode error: {str(je)}")
                self.error_handler.handle_json_error(je, message)
            except Exception as e:
                print(f"[WebSocket Debug] ❌ Unexpected error: {str(e)}")
                self.error_handler.handle_unexpected_error(e)

                
                # for filing in filings:
                #     try:
                #         # First validate with schema but don't convert to unified yet
                #         filing_obj = SECWebSocketFiling(**filing)
                        
                #         # Keep existing storage logic for now
                #         key = f"sec:raw:{filing['accessionNo']}"
                #         if self.redis_client.set_json(key, filing):
                #             self.stats['messages_processed'] += 1
                #             filing_obj.print()  # Use schema's print method
                #     except Exception as e:
                #         self.error_handler.handle_validation_error(e, filing)
                #         continue
                
            #     self.print_stats()
                
            # except Exception as e:
            #     self.error_handler.handle_unexpected_error(e)



    def _on_error(self, ws, error):
        """Handle WebSocket error"""
        self.connected = False
        print(f"WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        self.connected = False
        
        print(f"Status code: {close_status_code}")
        print(f"Close message: {close_msg}")

        if not self.should_run:
            return
            
        if close_status_code == 503:
            print("Service temporarily unavailable. Will retry with backoff.")
            
        delay = min(self.base_delay * (2 ** self.current_retry), self.max_delay)
        self.current_retry += 1
        
        print(f"Reconnecting in {delay:.1f} seconds...")
        time.sleep(delay)
        
        self.connect(raw=self.raw)

    def print_stats(self):
        """Print WebSocket statistics"""
        print("\nSEC WebSocket Statistics:")
        print(f"Messages Received: {self.stats['messages_received']}")
        print(f"Filings Processed: {self.stats['messages_processed']}")
        if self.last_message_time:
            print(f"Last Message: {self.last_message_time.isoformat()}")
        print(f"Success Rate: {(self.stats['messages_processed']/max(1, self.stats['messages_received']))*100:.1f}%")

    def check_connection_health(self):
        """Thread-safe connection health check"""
        with self._lock:
            if self.last_pong_time:
                time_since_pong = datetime.now(timezone.utc) - self.last_pong_time
                if time_since_pong.seconds > 20:
                    print(f"\nWARNING: No pong response in {time_since_pong.seconds} seconds")
                    self._log_downtime(status_code=408)
                    return False
        return True

    def _on_pong(self, ws, message):
        """Handle pong response"""
        self.last_pong_time = datetime.now(timezone.utc)

    def _log_downtime(self, status_code):
        """Log connection downtime to Redis"""
        disconnect_time = datetime.now(timezone.utc)
        if self.last_pong_time:
            duration = (disconnect_time - self.last_pong_time).total_seconds()
            downtime = {
                'start': self.last_pong_time.isoformat(),
                'end': disconnect_time.isoformat(),
                'duration': duration,
                'status': str(status_code) if status_code is not None else 'unknown'
            }
            
            try:
                key = f"admin:websocket_downtime:{disconnect_time.timestamp()}"
                self.redis_client.set_json(key, downtime)
                print(f"Connection lost after {duration:.2f}s. Recorded at {key}")
            except Exception as e:
                print(f"Failed to record downtime: {e}")