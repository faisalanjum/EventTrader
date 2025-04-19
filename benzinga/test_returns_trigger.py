# test_returns_trigger.py
import time
import threading
from datetime import datetime, timedelta
import pytz
from redisDB.redisClasses import EventTraderRedis
from utils.ReturnsProcessor import ReturnsProcessor
from redisDB.NewsProcessor import NewsProcessor
import json


def setup_test_triggers():
    redis = EventTraderRedis()
    
    # Start both processors
    news_processor = NewsProcessor(redis, delete_raw=True)
    returns_processor = ReturnsProcessor(redis)
    
    news_thread = threading.Thread(target=news_processor.process_all_news)
    returns_thread = threading.Thread(target=returns_processor.process_all_returns)
    
    news_thread.daemon = True
    returns_thread.daemon = True
    
    news_thread.start()
    returns_thread.start()
    
    # Get one pending return
    pending_items = redis.live_client.client.zrange("news:benzinga:pending_returns", 0, -1)
    if not pending_items:
        print("No pending returns found!")
        return None

    # Get news_id and check which return types exist
    news_id = pending_items[4].split(':')[0]
    print(f"News ID: {news_id}, length: {len(pending_items)}")
    
    # Get the news data
    news_key = f"news:benzinga:withoutreturns:{news_id}"
    news_data = redis.live_client.get_json(news_key)
    if not news_data:
        print("Error: News item not found in withoutreturns!")
        return None
    
    # Set new times based on current time
    current_time = datetime.now(pytz.timezone('America/New_York'))
    test_items = {}
    pipe = redis.live_client.client.pipeline()
    
    print(f"\n1. Found news ID: {news_id} with pending returns")
    print("2. Original timeforReturns:")
    print(json.dumps(news_data.get('metadata', {}).get('timeforReturns', {}), indent=2))
    
    # Update both the news data and ZSET
    return_types = ['hourly', 'session', 'daily']
    # return_types = ['hourly', 'session']
    for i, rt in enumerate(return_types, 1):
        future_time = current_time + timedelta(seconds=20*i)
        item_key = f"{news_id}:{rt}"
        timestamp = future_time.timestamp()
        
        # Update ZSET
        pipe.zadd("news:benzinga:pending_returns", {item_key: timestamp})
        
        # Update news data timeforReturns
        if 'metadata' not in news_data:
            news_data['metadata'] = {}
        if 'returns_schedule' not in news_data['metadata']:  # Changed from 'timeforReturns'
            news_data['metadata']['returns_schedule'] = {}
            
        news_data['metadata']['returns_schedule'][rt] = future_time.isoformat()
        
        test_items[rt] = (item_key, timestamp)
        print(f"   • Updated {rt} trigger for {future_time.strftime('%H:%M:%S')} EST")
    
    # Save updated news data
    pipe.set(news_key, json.dumps(news_data))
    pipe.execute()
    
    print("\n3. Updated timeforReturns:")
    print(json.dumps(news_data.get('metadata', {}).get('timeforReturns', {}), indent=2))
    
    return test_items




def monitor_processing(test_items):
    redis = EventTraderRedis()
    news_id = list(test_items.values())[0][0].split(':')[0]
    
    print("\n4. Starting monitoring process")
    print(f"   Current time: {datetime.now(pytz.timezone('America/New_York')).strftime('%H:%M:%S')} EST")
    
    while test_items:
        current_time = datetime.now(pytz.timezone("America/New_York"))
        print(f"\nStatus Check [{current_time.strftime('%H:%M:%S')} EST]:")
        
        # Check namespace status
        withoutreturns_key = f"news:benzinga:withoutreturns:{news_id}"
        withreturns_key = f"news:benzinga:withreturns:{news_id}"
        
        # First print ZSET status
        for return_type, (item_key, timestamp) in list(test_items.items()):
            score = redis.live_client.client.zscore("news:benzinga:pending_returns", item_key)
            if score is None:
                print(f"   ✓ {return_type} processed")
                test_items.pop(return_type)
            else:
                process_time = datetime.fromtimestamp(timestamp, pytz.timezone("America/New_York"))
                time_left = process_time - current_time
                if time_left.seconds > 85000:  # Fix for the 86399 display
                    continue
                print(f"   • {return_type}: {time_left.seconds} seconds remaining")

        # Then print returns status
        if redis.live_client.client.exists(withoutreturns_key):
            news_data = redis.live_client.get_json(withoutreturns_key)
            if news_data and 'returns' in news_data:
                print("\n   Returns Status:")
                for symbol, returns in news_data['returns']['symbols'].items():
                    print(f"   • {symbol}:")
                    for return_type, value in returns.items():
                        status = "✓" if value is not None else "⨯"
                        print(f"     - {return_type}: {status}")
        
        if redis.live_client.client.exists(withreturns_key):
            print("\n   🎯 Processing Complete!")
            news_data = redis.live_client.get_json(withreturns_key)
            if news_data and 'returns' in news_data:
                print("   Final Returns:")
                for symbol, returns in news_data['returns']['symbols'].items():
                    print(f"   • {symbol}:")
                    for return_type, values in returns.items():
                        print(f"     - {return_type}: {values}")
            break
            
        time.sleep(10)  # Check every 10 seconds

def main():
    try:
        print("Starting Returns Trigger Test")
        print("============================")
        
        # 1. Setup test triggers and start processors
        test_items = setup_test_triggers()
        if not test_items:
            return
        
        # 2. Monitor the processing
        monitor_processing(test_items)
        
    except KeyboardInterrupt:
        print("\nTest stopped by user")
    except Exception as e:
        print(f"Error during test: {e}")


if __name__ == "__main__":
    main()