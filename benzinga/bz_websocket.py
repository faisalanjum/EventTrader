import websocket
import json
import time
import ssl
from datetime import datetime, timezone
from typing import Optional, Union
from pydantic import ValidationError
from eventtrader.keys import BENZINGANEWS_API_KEY
from benzinga.bz_news_schemas import BzWebSocketNews, UnifiedNews
from benzinga.bz_news_errors import NewsErrorHandler
import random


class BenzingaNewsWebSocket:
    """WebSocket client for Benzinga news data"""
    
    def __init__(self):
        self.url = f"wss://api.benzinga.com/api/v1/news/stream?token={BENZINGANEWS_API_KEY}"
        self.error_handler = NewsErrorHandler()
        self.connected = False
        self.ws = None
        self.max_retries = 5
        self.base_delay = 1
        self.raw = False
        self.stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'last_message_time': None
        }
    
    @staticmethod
    def print_news_item(item: Union[BzWebSocketNews, UnifiedNews], raw: bool = False):
        """Print news item in raw or unified format"""
        if isinstance(item, BzWebSocketNews) and raw:
            BenzingaNewsWebSocket._print_raw_news(item)
        elif isinstance(item, UnifiedNews):
            BenzingaNewsWebSocket._print_unified_news(item)

    @staticmethod
    def _print_unified_news(news: UnifiedNews):
        """Print unified news format"""
        print("\n" + "="*80)
        print(f"ID: {news.id}")
        print(f"Title: {news.title}")
        print(f"Authors: {', '.join(news.authors)}")
        print(f"Created: {news.created}")
        print(f"Updated: {news.updated}")
        print(f"URL: {news.url}")
        print(f"\nStocks: {', '.join(news.symbols)}")
        print(f"Channels: {', '.join(news.channels)}")
        print(f"Tags: {', '.join(news.tags)}")
        print(f"\nTeaser: {news.teaser}")
        print(f"\nBody: {news.body}")
        print("="*80 + "\n")

    @staticmethod
    def _print_raw_news(news: BzWebSocketNews):
        """Print raw WebSocket format"""
        print("\n" + "="*80)
        print(f"API Version: {news.api_version}")
        print(f"Kind: {news.kind}")
        
        # Data level
        print(f"\nData:")
        print(f"Action: {news.data.action}")
        print(f"ID: {news.data.id}")
        print(f"Timestamp: {news.data.timestamp}")
        
        # Content level
        content = news.data.content
        print(f"\nContent:")
        print(f"ID: {content.id}")
        print(f"Title: {content.title}")
        print(f"Authors: {', '.join(content.authors)}")
        print(f"Created: {content.created_at}")
        print(f"Updated: {content.updated_at}")
        print(f"URL: {content.url}")
        
        # Securities with all details
        print("\nSecurities:")
        for sec in content.securities:
            print(f"  - Symbol: {sec.symbol}")
            print(f"    Exchange: {sec.exchange}")
            print(f"    Primary: {sec.primary}")
        
        print(f"\nChannels: {', '.join(content.channels)}")
        print(f"Tags: {', '.join(content.tags) if content.tags else ''}")
        print(f"\nTeaser: {content.teaser}")
        print(f"\nBody: {content.body}")
        
        if content.image:
            print(f"\nImage: {content.image}")
            
        print("="*80 + "\n")

    def print_error_stats(self):
        """Print current error statistics"""
        print(self.error_handler.get_summary())

    def connect(self, raw: bool = False, enable_trace: bool = False):
        """Start WebSocket connection with retry logic
        
        Args:
            raw: If True, returns news in original WebSocket format (BzWebSocketNews)
                 If False, converts to unified format with additional validation (UnifiedNews)
                 Basic WebSocket format validation happens in both cases
            enable_trace: Enable WebSocket trace logging
        """
        self.raw = raw
        # Reset error stats at start of connection
        self.error_handler.reset_stats()
        
        websocket.enableTrace(enable_trace)
        print(f"Starting WebSocket connection (format: {'raw' if raw else 'unified'})...")
        
        retries = 0
        while retries < self.max_retries:
            try:
                self.ws = websocket.WebSocketApp(
                    self.url,
                    header={"accept": "application/json"},
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )
                
                print(f"Attempt {retries + 1} of {self.max_retries}")
                
                self.ws.run_forever(
                    sslopt={"cert_reqs": ssl.CERT_NONE},
                    ping_interval=30,
                    ping_timeout=10
                )
                
                # If we get here and connected is True, break the retry loop
                if self.connected:
                    break
                    
            except Exception as e:
                print(f"Connection error: {e}")
            
            # If we get here, connection failed
            retries += 1
            if retries < self.max_retries:
                delay = min(300, self.base_delay * (2 ** retries))  # Exponential backoff, max 5 minutes
                jitter = random.uniform(0, 0.1 * delay)  # Add 0-10% jitter
                total_delay = delay + jitter
                
                print(f"Retrying in {total_delay:.1f} seconds...")
                time.sleep(total_delay)
            else:
                print("Max retries reached. Please check the service status and try again later.")
                break

    def _on_open(self, ws):
        """Handle WebSocket connection open"""
        # Reset stats on each successful connection
        self.error_handler.reset_stats()
        
        print(f"Connected to Benzinga WebSocket at {datetime.now()}")
        self.connected = True
        self.stats['last_message_time'] = time.time()
        
        subscription = {
            "action": "subscribe",
            "data": {"streams": ["news"]}
        }
        ws.send(json.dumps(subscription))

    def _on_message(self, ws, message: str):
        """Handle incoming WebSocket message"""
        try:
            self.stats['messages_received'] += 1
            self.stats['last_message_time'] = datetime.now(timezone.utc)
            
            if message.isdigit():
                print(f"Heartbeat: {message}")
                return
            
            data = json.loads(message)
            
            # Use centralized processing
            processed_item = self.error_handler.process_news_item(data, self.raw)
            if processed_item:
                self.print_news_item(processed_item)
                self.stats['messages_processed'] += 1  # Count successful processing
            
            # Always print stats regardless of raw mode
            self.print_stats()
            
        except json.JSONDecodeError as je:
            print(f"Failed to parse message: {message[:100]}...")
            self.error_handler.handle_json_error(je, message)
        except Exception as e:
            self.error_handler.handle_unexpected_error(e)

    def _on_error(self, ws, error):
        """Handle WebSocket error"""
        self.connected = False
        self.error_handler.handle_connection_error(error)

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        print(f"WebSocket disconnected at {datetime.now()}")
        print(f"Status code: {close_status_code}")
        print(f"Close message: {close_msg}")
        self.connected = False
        
        if close_status_code == 503:
            print("Service temporarily unavailable. Will retry with backoff.")
        
        self.print_error_stats()

    def print_stats(self):
        """Print WebSocket statistics"""
        print("\nWebSocket Statistics:")
        print(f"Messages Received: {self.stats['messages_received']}")
        print(f"Messages Processed: {self.stats['messages_processed']}")
        if self.stats['last_message_time']:
            print(f"Last Message: {self.stats['last_message_time'].isoformat()}")
        print(f"Success Rate: {(self.stats['messages_processed']/max(1, self.stats['messages_received']))*100:.1f}%")
        print(self.error_handler.get_summary())

    def check_connection_health(self):
        """Check if connection is healthy"""
        if self.stats['last_message_time']:
            time_since_last = datetime.now(timezone.utc) - self.stats['last_message_time']
            if time_since_last.seconds > 30:  # No message in 30 seconds
                print(f"\nWARNING: No messages received in {time_since_last.seconds} seconds")
                return False
        return True
