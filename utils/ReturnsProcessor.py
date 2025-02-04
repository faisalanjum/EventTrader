# returns_processor.py
import threading
import logging
from typing import Optional, Dict, Any
import json
from datetime import datetime, timezone
from dateutil import parser
import time

from utils.redisClasses import EventTraderRedis
from utils.polygonClass import Polygon
from eventtrader.keys import POLYGON_API_KEY
import pytz

class ReturnsProcessor:
    def __init__(self, event_trader_redis: EventTraderRedis):
        self.live_client = event_trader_redis.bz_livenews
        self.hist_client = event_trader_redis.bz_histnews
        self.queue_client = self.live_client.create_new_connection() # create new connection for queue checks
        self.pubsub_client = self.live_client.create_pubsub_connection()
        self.pubsub_client.subscribe('news:benzinga:live:processed')


        self.should_run = True
        self._lock = threading.Lock()
        
        # Initialize Polygon client
        self.polygon = Polygon(api_key=POLYGON_API_KEY)
        
        # Cache the stock universe for ETF lookups
        self.stock_universe = event_trader_redis.get_stock_universe()

        # Configure logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        self.pending_zset = "news:benzinga:pending_news_returns"         
        self.ny_tz = pytz.timezone("America/New_York")

    def _has_unprocessed_news(self, client):
        """Check for unprocessed news"""
        pattern = f"{client.prefix}processed:*"
        keys = client.client.scan(0, pattern, 1)[1]
        self.logger.info(f"Checking pattern: {pattern}, Found keys: {keys}")  # More detailed logging
        return bool(keys)

    def process_all_returns(self):
        """Main processing loop to handle returns calculation"""
        self.logger.info("Starting returns processing")
        consecutive_errors = 0
        
        while self.should_run:
            try:
                # Process Live News
                self._process_live_news(self.live_client)
                consecutive_errors = 0

                # Process Hist News
                self._process_hist_news(self.hist_client)
                consecutive_errors = 0

                # 2. Process any pending returns that are now ready
                self._process_pending_returns()

                # time.sleep(0.1)  # Prevent tight loop
                self._sleep_until_next_return(default_sleep_time=1)
                
            except Exception as e:
                self.logger.error(f"Returns processing error: {e}")
                consecutive_errors += 1
                if consecutive_errors > 10:
                    self.logger.error("Too many consecutive errors, reconnecting...")
                    self._reconnect()
                    consecutive_errors = 0
                time.sleep(1)


    def _sleep_until_next_return(self, default_sleep_time=5):
        """Sleep until next scheduled return time in ZSET"""
        try:
            # Use queue_client directly since it's a Redis instance
            next_item = self.queue_client.zrange(self.pending_zset, 0, 0, withscores=True)
            
            if next_item:
                self.logger.info(f"Found next item: {next_item}")
                # zrange with withscores=True returns [(member, score)]
                _, next_timestamp = next_item[0]  # Correctly unpack tuple of (member, score)
                now_timestamp = datetime.now(timezone.utc).timestamp()
                sleep_time = max(0, next_timestamp - now_timestamp)  # Sleep only until next return is due
                self.logger.info(f"Sleeping for {sleep_time} seconds until next return")
            else:
                sleep_time = default_sleep_time  # Default sleep time if no pending returns
                self.logger.info(f"No pending returns, sleeping for {sleep_time} seconds")

            # Check for new messages while sleeping
            message = self.pubsub_client.get_message(timeout=sleep_time)
            if message and message['type'] == 'message':
                self.logger.info(f"Woke up due to new processed message: {message['data']}")
                return

            return

        except Exception as e:
            self.logger.error(f"Error in sleep/pubsub operation: {e}")
            time.sleep(0.1)  # Minimal sleep on error
            return



    def _process_live_news(self, client):
        """Process returns for a specific client (hist/live)"""
        pattern = f"{client.prefix}processed:*"
        for key in client.client.scan_iter(pattern):
            try:
                success = self._process_single_item(key, client)
                if not success:
                    self.logger.error(f"Failed to process returns for {key}")
            except Exception as e:
                self.logger.error(f"Failed to process returns for {key}: {e}")


    def _process_hist_news(self, client):
        """Process returns for a specific client (hist/live)"""
        pattern = f"{client.prefix}processed:*"
        for key in client.client.scan_iter(pattern):
            try:
                success = self._process_single_item(key, client)
                if not success:
                    self.logger.error(f"Failed to process returns for {key}")
            except Exception as e:
                self.logger.error(f"Failed to process returns for {key}: {e}")



    def _process_single_item(self, key: str, client) -> bool:
        """Process returns for a single news item"""
        try:
            
            # 1. Gets news from processed namespace
            content = client.get(key)
            if not content:
                return False
            processed_dict = json.loads(content)

            # 2. Calculates any immediately available returns
            returns_info = self._calculate_available_returns(processed_dict)
            
            # 3. Schedule future return calculations in ZSET
            news_id = key.split(':')[-1]  # Get the ID portion- Extract ID and create new unified namespace key
            self._schedule_pending_returns(news_id, processed_dict)
            self.logger.info(f"All complete: {returns_info['all_complete']}")
            
            # 4. Moves to appropriate namespace
            if returns_info['all_complete']:
                new_key = f"news:benzinga:withreturns:{news_id}"
                self.logger.info(f"Moving to withreturns: {new_key}")
            else:
                new_key = f"news:benzinga:withoutreturns:{news_id}"
                self.logger.info(f"Moving to withoutreturns: {new_key}")

            # 5. Update processed_dict with returns
            processed_dict['returns'] = returns_info['returns']

            # 6. Atomic update using pipeline
            pipe = client.client.pipeline(transaction=True)
            pipe.set(new_key, json.dumps(processed_dict))
            pipe.delete(key)
            return all(pipe.execute())

        except Exception as e:
            self.logger.error(f"Error processing returns for {key}: {e}")
            return False


    def _calculate_available_returns(self, processed_dict: dict) -> dict:
        """Calculate returns based on available timestamps"""
        timefor_returns = processed_dict.get('metadata', {}).get('timeforReturns', {})
        
        # Get timezone-aware NY time by first getting UTC (to avoid server timezone issues) then converting
        current_time = datetime.now(timezone.utc).astimezone(self.ny_tz)
        
        returns_data = {'symbols': {}}
        all_complete = True

        # Initialize returns structure for each symbol
        for symbol in processed_dict.get('symbols', []):
            returns_data['symbols'][symbol] = {
                'session': None,
                '1d_impact': None,
                '1h_impact': None
            }

        # Process each return type separately
        return_types = {
            'session_end_time': 'session',
            '1d_end_time': '1d_impact',
            '1h_end_time': '1h_impact'
        }

        for zset_type, return_key in return_types.items():
            if timefor_returns.get(zset_type):
                specific_timefor_returns = {zset_type: timefor_returns[zset_type]}
                
                for symbol in processed_dict.get('symbols', []):
                    try:
                        symbol_returns = self._calculate_symbol_returns(
                            symbol,
                            processed_dict['created'],
                            specific_timefor_returns,
                            current_time
                        )
                        returns_data['symbols'][symbol][return_key] = symbol_returns.get(return_key)
                    except Exception as e:
                        self.logger.error(f"Error processing {return_key} for {symbol}: {e}")
                        all_complete = False

        # Check if all returns are complete
        for symbol_returns in returns_data['symbols'].values():
            if any(ret is None for ret in symbol_returns.values()):
                all_complete = False
                break

        return {
            'returns': returns_data,
            'all_complete': all_complete
        }



    def _calculate_symbol_returns(self, symbol: str, created: str, timefor_returns: dict, current_time: datetime) -> dict:
        """Calculate returns for a single symbol"""
        symbol = symbol.strip().upper()
        sector_etf = self.get_etf(symbol, 'sector_etf')
        industry_etf = self.get_etf(symbol, 'industry_etf')
        
        self.logger.info(f"\nProcessing returns for {symbol}")
        self.logger.info(f"Current time (NY): {current_time}")
        self.logger.info(f"Available timefor_returns keys: {timefor_returns.keys()}")  # Debug line


        returns = {
            'session': None,
            '1d_impact': None,
            '1h_impact': None
        }

        return_types = [
            ('session', 'session', None, timefor_returns.get('session_end_time')),
            ('1d_impact', '1d_impact', None, timefor_returns.get('1d_end_time')),
            ('1h_impact', 'horizon', [60], timefor_returns.get('1h_end_time'))
        ]

        for return_key, return_type, horizon, end_time in return_types:
            if end_time:
                end_time_dt = parser.parse(end_time).astimezone(self.ny_tz)
                self.logger.info(f"{return_key}: End time = {end_time_dt}, Should calculate = {current_time >= end_time_dt}")

                if current_time >= end_time_dt:  
                    try:
                        calc_returns = self.polygon.get_event_returns(
                            ticker=symbol,
                            sector_etf=sector_etf,
                            industry_etf=industry_etf,
                            event_timestamp=created,
                            return_type=return_type,
                            horizon_minutes=horizon
                        )
                        
                        if return_type == 'horizon':
                            calc_returns = {k: v[0] for k, v in calc_returns.items()}
                        
                        returns[return_key] = {k: round(v, 2) for k, v in calc_returns.items()}
                        self.logger.info(f"✓ Calculated {return_key} returns")
                    except Exception as e:
                        self.logger.error(f"Error calculating {return_key} returns for {symbol}: {e}")
                        returns[return_key] = None
                else:
                    self.logger.info(f"✗ Skipping {return_key} - time not reached")
            else:
                self.logger.info(f"✗ Skipping {return_key} - no end time")

        return returns

    def get_etf(self, ticker: str, col='industry_etf'):
        """Get sector or industry ETF for a ticker"""
        ticker = ticker.strip().upper()
        matches = self.stock_universe[self.stock_universe.symbol == ticker]
        if matches.empty:
            raise ValueError(f"Symbol {ticker} not found in stock universe")
        return matches[col].values[0]

    def stop(self):
        """Stop processing and cleanup"""
        self.should_run = False
        try:
            self.pubsub_client.unsubscribe()
            self.pubsub_client.close()
        except Exception as e:
            self.logger.error(f"Error cleaning up pubsub: {e}")


    # ZSET Scheduling
    def _schedule_pending_returns(self, news_id: str, processed_dict: dict):
        """Schedule future return calculations"""
        try:
            timefor_returns = processed_dict.get('metadata', {}).get('timeforReturns', {})
            pipe = self.live_client.client.pipeline()
            
            current_time = datetime.now(timezone.utc).astimezone(self.ny_tz).timestamp()

            for return_type, time_str in timefor_returns.items():
                # Convert scheduled time to NY timestamp for comparison, but .timestamp() always stores as UTC
                calc_time = parser.parse(time_str).astimezone(self.ny_tz).timestamp()
                
                if calc_time > current_time:
                    # Adds to ZSET: "news:benzinga:pending_news_returns" : # Format: "43420311:1h_end_time" -> timestamp
                    pipe.zadd(self.pending_zset, {f"{news_id}:{return_type}": calc_time})
                    self.logger.debug(f"Scheduled {return_type} for {datetime.fromtimestamp(calc_time, self.ny_tz)}")
            
            pipe.execute()
            
        except Exception as e:
            self.logger.error(f"Failed to schedule returns: {e}")

    # Continuous Monitoring
    def _process_pending_returns(self):
        """Process any returns that are now ready"""
        try:
            # Convert current time to NY timestamp
            current_time = datetime.now(timezone.utc).astimezone(self.ny_tz).timestamp()
            
            # Continuously checks ZSET for ready returns
            ready_items = self.live_client.client.zrangebyscore(self.pending_zset, 0, current_time )

            if ready_items:
                ny_time = datetime.fromtimestamp(current_time, self.ny_tz)
                self.logger.info(f"Processing {len(ready_items)} pending returns (NY Time: {ny_time})")

            for item in ready_items:
                news_id, return_type = item.split(':')

                # Gets news from withoutreturns namespace
                key = f"news:benzinga:withoutreturns:{news_id}"
                
                # Return Updates
                if self._update_return(key, return_type):

                    # Remove from ZSET after successful processing
                    self.live_client.client.zrem(self.pending_zset, item)
                    self.logger.debug(f"Successfully processed pending return: {item}")
                    
        except Exception as e:
            self.logger.error(f"Error processing pending returns: {e}")


    # Return Updates
    def _update_return(self, key: str, return_type: str) -> bool:
        """Update returns for a specific return type"""
        try:

            # 1. Gets news from withoutreturns
            news_data = json.loads(self.live_client.get(key))
            if not news_data:
                return True  # Key no longer exists, remove from pending
                
            # 2. Calculates specific return
            updated_returns = self._calculate_specific_return(news_data, return_type)
            if not updated_returns:
                return False
                
            # Map ZSET return type to returns structure
            return_key = {
                '1h_end_time': '1h_impact',
                'session_end_time': 'session',
                '1d_end_time': '1d_impact'
            }[return_type]
                
            # Update returns in news data using the mapped return key
            # 3. Updates returns in news data
            for symbol, values in updated_returns.items():
                news_data['returns']['symbols'][symbol][return_key] = values
                
            # 4. If all returns complete, moves to withreturns
            all_complete = all(
                all(ret is not None for ret in symbol_returns.values()) 
                for symbol_returns in news_data['returns']['symbols'].values()
            )
            
            pipe = self.live_client.client.pipeline(transaction=True)
            if all_complete:
                new_key = key.replace('withoutreturns', 'withreturns')
                pipe.set(new_key, json.dumps(news_data))
                pipe.delete(key)
                self.logger.info(f"Moving to withreturns: {new_key}")
            else:
                pipe.set(key, json.dumps(news_data))
                
            return all(pipe.execute())
                
        except Exception as e:
            self.logger.error(f"Failed to update return {return_type} for {key}: {e}")
            return False
        

    def _calculate_specific_return(self, news_data: dict, return_type: str) -> dict:
        """Calculate a specific return type for all symbols"""
        try:
            current_time = datetime.now(timezone.utc).astimezone(self.ny_tz)
            timefor_returns = news_data.get('metadata', {}).get('timeforReturns', {})
            
            # Create a dict with only the specific return type we want to calculate
            specific_timefor_returns = {return_type: timefor_returns.get(return_type)}
            
            self.logger.info(f"Processing {return_type} with time: {specific_timefor_returns}")
            
            returns = {}
            for symbol in news_data.get('symbols', []):
                symbol_returns = self._calculate_symbol_returns(
                    symbol,
                    news_data['created'],
                    specific_timefor_returns,  # Only pass the specific return type we want to calculate
                    current_time
                )
                
                # Map ZSET return type to returns structure
                return_key = {
                    '1h_end_time': '1h_impact',
                    'session_end_time': 'session',
                    '1d_end_time': '1d_impact'
                }[return_type]
                
                returns[symbol] = symbol_returns.get(return_key)

            return returns
        except Exception as e:
            self.logger.error(f"Error calculating specific return {return_type}: {e}")
            return None
        

    # Is this enough?
    def _reconnect(self):
        """Reconnect to Redis"""
        try:
            self.live_client = self.live_client.__class__(prefix=self.live_client.prefix)
            self.hist_client = self.hist_client.__class__(prefix=self.hist_client.prefix)
            self.queue_client = self.live_client
            
        except Exception as e:
            self.logger.error(f"Reconnection failed: {e}")
