import websocket
import json
import time
import ssl
from datetime import datetime
from pydantic import ValidationError
from eventtrader.keys import BENZINGANEWS_API_KEY
from benzinga.bz_news_schemas import BenzingaNews
from benzinga.bz_news_errors import NewsErrorHandler


class BenzingaNewsHandler:
    def __init__(self):
        self.error_handler = NewsErrorHandler()
        self.connected = False  # Track connection state
        self.last_message_time = None  # Track last message received
    
    def print_news(self, message):
        try:
            # Parse JSON
            try:
                data = json.loads(message)
            except json.JSONDecodeError as je:
                error = self.error_handler.handle_error(je, message)
                print(f"\nJSON ERROR at {error.timestamp}:")
                print(f"Details: {error.details}")
                return

            # Validate with Pydantic
            try:
                news = BenzingaNews(**data)
                unified_news = BenzingaNews.from_websocket(news)
                print(f"Unified News: {unified_news}")
            except ValidationError as ve:
                error = self.error_handler.handle_error(ve, message)
                print(f"\nVALIDATION ERROR at {error.timestamp}:")
                print(f"Details: {error.details}")
                return

            # Print news data (your existing print code)
            print("\n" + "="*80)
            print(f"NEWS RECEIVED at {datetime.now()}")

            print("="*80)

            # Top Level
            print("TOP LEVEL:")
            print(f"API Version: {news.api_version}")
            print(f"Kind: {news.kind}")
            
            # Data Level
            print("\nDATA LEVEL:")
            print(f"Action: {news.data.action}")
            print(f"Data ID: {news.data.id}")
            print(f"Timestamp: {news.data.timestamp}")
            
            # Content Level
            content = news.data.content
            print("\nCONTENT LEVEL:")
            print(f"Content ID: {content.id}")
            print(f"Revision ID: {content.revision_id}")
            print(f"Type: {content.type}")
            print(f"Title: {content.title}")
            print(f"Body: {content.body}")
            print(f"Authors: {', '.join(content.authors)}")
            print(f"Teaser: {content.teaser}")
            print(f"URL: {content.url}")
            print(f"Tags: {content.tags}")
            
            # Securities
            print("\nSECURITIES:")
            for security in content.securities:
                print(f"  Symbol: {security.symbol}")
                print(f"  Exchange: {security.exchange}")
                print(f"  Primary: {security.primary}")
            
            # Channels
            print("\nCHANNELS:")
            print(f"{', '.join(content.channels)}")
            
            # Image
            print("\nIMAGE:")
            print(f"{content.image}")
            
            # Timestamps
            print("\nTIMESTAMPS:")
            print(f"Created: {content.created_at}")
            print(f"Updated: {content.updated_at}")
            
            print("="*80 + "\n")
            
        except Exception as e:
            error = self.error_handler.handle_error(e, message)
            print(f"\nUNEXPECTED ERROR at {error.timestamp}:")
            print(f"Type: {error.error_type}")
            print(f"Details: {error.details}")
            
            print("ERROR BOSS STATS")
            self.print_error_stats() # Print error stats when an error occurs

    def print_error_stats(self):
        """Print current error statistics"""
        stats = self.error_handler.get_error_stats()
        print("\nERROR STATISTICS:")
        for error_type, count in stats.items():
            print(f"{error_type}: {count}")


class BenzingaWebSocket:
    def __init__(self):        
        self.url = f"wss://api.benzinga.com/api/v1/news/stream?token={BENZINGANEWS_API_KEY}"
        self.news_handler = BenzingaNewsHandler()
        
        
    def on_open(self,ws):
        print(f"Successfully connected to Benzinga WebSocket at {datetime.now()}")
        ws.last_message_time = time.time()
        
        # Standard Benzinga subscription format
        subscription_message = {
            "action": "subscribe",
            "data": {
                "streams": ["news"]  
            }
        }
        ws.send(json.dumps(subscription_message))
        print(f"Sent subscription request: {subscription_message}")  # Debug print


    def on_message(self, ws, message):
        ws.last_message_time = time.time()
        print(f"\nReceived raw message type: {type(message)}")  # Outputs <class 'str'>
        
        if message.isdigit():
            print(f"Ping/Pong message: {message}")
        else:
            print(f"Received news message at {datetime.now()}")
            try:
                # Try to parse as JSON to see the structure
                data = json.loads(message)
                
                # Print all field levels
                print("\nALL AVAILABLE FIELDS:")
                print(f"Top Level: {list(data.keys())}")
                if 'data' in data:
                    print(f"Data Level: {list(data['data'].keys())}")
                    if 'content' in data['data']:
                        print(f"Content Level: {list(data['data']['content'].keys())}")
                
                # Your existing code continues...
                print(f"Message structure: {list(data.keys())}")  
                self.news_handler.print_news(message)
                
            except json.JSONDecodeError as e:
                print(f"Failed to parse message: {message[:100]}...")  # Show first 100 chars
                print(f"Parse error: {e}")
    
    def on_error(self, ws, error):
        print(f"WebSocket error at {datetime.now()}: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print(f"WebSocket disconnected at {datetime.now()}")
        print(f"Close status code: {close_status_code}")
        print(f"Close message: {close_msg}")
        self.news_handler.print_error_stats()


    def connect_websocket(self):
        while True:
            try:
                print(f"\nAttempting to connect to Benzinga at {datetime.now()}...")
                
                ws = websocket.WebSocketApp(
                    self.url,
                    header={"accept": "application/json"},
                    on_open=lambda ws: self.on_open(ws),
                    on_message=lambda ws, msg: self.on_message(ws, msg),
                    on_error=lambda ws, err: self.on_error(ws, err),
                    on_close=lambda ws, code, msg: self.on_close(ws, code, msg)
                )
            
                print("Starting WebSocket connection...")
                ws.run_forever(
                    sslopt={"cert_reqs": ssl.CERT_NONE},            
                    ping_interval=30, # Send ping every 30 seconds
                    ping_timeout=10   # Wait 10 seconds for pong
                )
                
                print("Connection ended, retrying in 5 seconds...")
                time.sleep(5)
            except Exception as e:
                print(f"Connection error: {e}")
                print(f"Error type: {type(e)}")
                time.sleep(5)
