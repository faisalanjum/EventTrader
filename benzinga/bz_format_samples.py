"""
This module captures and stores sample responses from both Benzinga APIs (REST API and WebSocket)
to document their exact raw formats.
"""

import json
import os
from datetime import datetime, timedelta
import websocket
from benzinga.bz_restAPI import BenzingaNewsRestAPI
from benzinga.bz_websocket import BenzingaNewsWebSocket
from eventtrader.keys import BENZINGANEWS_API_KEY

# Create samples directory if it doesn't exist
SAMPLES_DIR = os.path.join(os.path.dirname(__file__), 'samples')
os.makedirs(SAMPLES_DIR, exist_ok=True)

def save_sample(data: dict, prefix: str):
    """Save sample with timestamp and metadata"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.json"
    filepath = os.path.join(SAMPLES_DIR, filename)
    
    # Add metadata
    sample_data = {
        "captured_at": datetime.now().isoformat(),
        "api_type": prefix,
        "raw_data": data
    }
    
    with open(filepath, 'w') as f:
        json.dump(sample_data, f, indent=2)
    print(f"Sample saved to {filepath}")
    return data

def capture_rest_api_sample():
    """Capture a sample REST API response"""
    try:
        api = BenzingaNewsRestAPI(BENZINGANEWS_API_KEY)
        
        # Get yesterday and today's date
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        news_items = api.get_historical_data(
            date_from=yesterday.strftime("%Y-%m-%d"),
            date_to=today.strftime("%Y-%m-%d"),
            raw=True
        )
        
        if news_items and len(news_items) > 0:
            sample = news_items[0].model_dump()
            return save_sample(sample, "rest_api")
    except Exception as e:
        print(f"Error capturing REST API sample: {e}")
    return None

def capture_websocket_sample():
    """Capture a sample WebSocket message"""
    samples = []
    
    def on_message(ws, message):
        if not message.isdigit():  # Skip ping/pong
            try:
                sample = json.loads(message)
                samples.append(sample)
                save_sample(sample, "websocket")
                ws.close()
            except json.JSONDecodeError as e:
                print(f"Error parsing WebSocket message: {e}")
            except Exception as e:
                print(f"Error processing WebSocket message: {e}")
    
    try:
        # Create WebSocket with custom message handler
        ws = BenzingaNewsWebSocket()
        ws.ws = websocket.WebSocketApp(
            ws.url,
            on_message=on_message
        )
        ws.connect(raw=True)
        
        return samples[0] if samples else None
    except Exception as e:
        print(f"Error capturing WebSocket sample: {e}")
        return None

if __name__ == "__main__":
    print("Capturing REST API sample...")
    rest_sample = capture_rest_api_sample()
    
    print("\nCapturing WebSocket sample...")
    ws_sample = capture_websocket_sample()
    
    if rest_sample and ws_sample:
        print("\nBoth samples captured successfully!")
        print("\nComparing formats:")
        print("\nREST API fields:", sorted(rest_sample.keys()))
        print("\nWebSocket fields:", sorted(ws_sample.get('data', {}).get('content', {}).keys()))
    else:
        print("\nFailed to capture both samples") 