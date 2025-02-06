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
from utils.metadata_fields import MetadataFields
from utils.EventReturnsManager import EventReturnsManager
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

        self.event_returns_manager = EventReturnsManager(self.stock_universe)
        self.BATCH_SIZE = 100 


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
                # self._process_live_news(self.hist_client)
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

    # Sleep until next scheduled return time in ZSET, interrupts if new processed message is published (PubSub)
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
                self.logger.debug(f"No pending returns, sleeping for {sleep_time} seconds")

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
        
        """Process returns for historical news in batches"""
        pattern = f"{client.prefix}processed:*"
        
        events = []
        successful_returns = 0
        failed_returns = 0
        

        # Collect all events first
        for key in client.client.scan_iter(pattern):
            try:
                content = client.get(key)
                if not content:
                    continue
                    
                news_dict = json.loads(content)
                event = {
                    'event_id': news_dict['id'],
                    'created': news_dict['metadata']['event']['created'],
                    'symbols': news_dict['symbols'],
                    'metadata': news_dict['metadata']
                }
                events.append(event)
                    
            except Exception as e:
                self.logger.error(f"Failed to process {key}: {e}")
        
        if events:
            self.logger.info(f"Processing batch of {len(events)} events")
            event_returns = self.event_returns_manager.process_events(events)
            
            # Count successes and failures
            for result in event_returns:
                if result.returns:
                    successful_returns += 1
                else:
                    failed_returns += 1
            
            # Print summary
            self.logger.info(f"\nReturns Calculation Summary:")
            self.logger.info(f"Total Events: {len(events)}")
            self.logger.info(f"Successful Returns: {successful_returns}")
            self.logger.info(f"Failed Returns: {failed_returns}")
            
            # Log the result
            # self.logger.info(f"Event returns (First): {event_returns[0]}")  
            # self.logger.info(f"Event returns (Last): {event_returns[-1]}")

        # This is wrong but temporary to check
        # pattern = f"{client.prefix}processed:*"
        
        # # Collect all events first
        # for key in client.client.scan_iter(pattern):
        #     news_id = key.split(':')[-1]  # Get the ID portion- Extract ID and create new unified namespace key
        #     new_key = f"news:benzinga:withreturns:{news_id}"
        #     # self.logger.info(f"Moving to withreturns: {new_key}")
        #     # 6. Atomic update using pipeline
        #     pipe = client.client.pipeline(transaction=True)
        #     pipe.set(new_key, json.dumps(processed_dict))
        #     pipe.delete(key)
        #     return all(pipe.execute())



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
            
            # 4. Determine destination namespace based on completion
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
        try:
            # 1. Extract metadata and setup
            metadata = processed_dict.get('metadata', {})
            returns_schedule = metadata.get(MetadataFields.RETURNS_SCHEDULE, {})
            instruments = metadata.get(MetadataFields.INSTRUMENTS, [])
            current_time = datetime.now(timezone.utc).astimezone(self.ny_tz)
            
            # 2. Initialize return structure
            returns_data = {'symbols': {}}
            all_complete = True

            # 3. Setup empty return structure for each symbol
            for instrument in instruments:
                symbol = instrument['symbol']
                # Initialize all return types as None
                returns_data['symbols'][symbol] = {
                    f"{rt}_return": None 
                    for rt in [MetadataFields.HOURLY, MetadataFields.SESSION, MetadataFields.DAILY]}

            # 4. Process each return type (hourly, session, daily)
            for return_type in [MetadataFields.HOURLY, MetadataFields.SESSION, MetadataFields.DAILY]:
                schedule_time = returns_schedule.get(return_type)
                if schedule_time:
                    schedule_dt = parser.parse(schedule_time).astimezone(self.ny_tz)
                    
                    # 5. If scheduled time has passed, calculate returns
                    if current_time >= schedule_dt:  
                        for instrument in instruments:
                            try:
                                symbol = instrument['symbol']
                                benchmarks = instrument['benchmarks']
                                
                                # 6. Calculate returns using Polygon
                                calc_returns = self.polygon.get_event_returns(
                                    ticker=symbol,
                                    sector_etf=benchmarks['sector'],
                                    industry_etf=benchmarks['industry'],
                                    event_timestamp=processed_dict['created'],
                                    return_type=return_type,
                                    horizon_minutes=[60] if return_type == MetadataFields.HOURLY else None
                                )
                                
                                # 7. Special handling for hourly returns
                                if return_type == MetadataFields.HOURLY:
                                    calc_returns = {k: v[0] for k, v in calc_returns.items()}
                                
                                # 8. Store calculated returns
                                return_field = MetadataFields.RETURN_TYPE_MAP[return_type]
                                returns_data['symbols'][symbol][return_field] = {
                                    k: round(v, 2) for k, v in calc_returns.items()
                                }
                            except Exception as e:
                                self.logger.error(f"Error processing {return_field} for {symbol}: {e}")
                                all_complete = False

            # 9. Check if all returns are complete
            for symbol_returns in returns_data['symbols'].values():
                if any(ret is None for ret in symbol_returns.values()):
                    all_complete = False
                    break

            return {
                'returns': returns_data,
                'all_complete': all_complete
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate returns: {e}")
            return {'returns': {'symbols': {}}, 'all_complete': False}



    def _calculate_symbol_returns(self, symbol: str, created: str, timefor_returns: dict, current_time: datetime) -> dict:
        """Calculate returns for a single symbol"""
        symbol = symbol.strip().upper()
        sector_etf = self.get_etf(symbol, 'sector_etf')
        industry_etf = self.get_etf(symbol, 'industry_etf')
        
        self.logger.info(f"\nProcessing returns for {symbol}")
        self.logger.info(f"Current time (NY): {current_time}")

        # Initialize returns dict with all return types set to None
        returns = {f"{rt}_return": None for rt in [MetadataFields.SESSION, MetadataFields.DAILY, MetadataFields.HOURLY]}

        # Define return configurations
        return_configs = {
            MetadataFields.SESSION: (None, timefor_returns.get(MetadataFields.SESSION)),
            MetadataFields.DAILY: (None, timefor_returns.get(MetadataFields.DAILY)),
            MetadataFields.HOURLY: ([60], timefor_returns.get(MetadataFields.HOURLY))
        }

        for return_type, (horizon, end_time) in return_configs.items():
            return_key = MetadataFields.RETURN_TYPE_MAP[return_type]
            
            if not end_time:
                self.logger.info(f"✗ Skipping {return_key} - no end time")
                continue

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
                    
                    if return_type == MetadataFields.HOURLY:
                        calc_returns = {k: v[0] for k, v in calc_returns.items()}
                    
                    returns[return_key] = {k: round(v, 2) for k, v in calc_returns.items()}
                    self.logger.info(f"✓ Calculated {return_key} returns")
                except Exception as e:
                    self.logger.error(f"Error calculating {return_key} returns for {symbol}: {e}")
                    returns[return_key] = None
            else:
                self.logger.info(f"✗ Skipping {return_key} - time not reached")

        return returns

    # ZSET Scheduling
    def _schedule_pending_returns(self, news_id: str, processed_dict: dict):
        """Schedule future return calculations"""
        try:
            # Get returns schedule from new metadata structure
            returns_schedule = processed_dict.get('metadata', {}).get(MetadataFields.RETURNS_SCHEDULE, {})
            pipe = self.live_client.client.pipeline()
            
            current_time = datetime.now(timezone.utc).astimezone(self.ny_tz).timestamp()

            # Map the new schedule fields to timestamps
            schedule_mapping = {return_type: returns_schedule.get(return_type)
                for return_type in [MetadataFields.HOURLY, MetadataFields.SESSION, MetadataFields.DAILY]}

            for return_type, time_str in schedule_mapping.items():
                if time_str:
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
                
            # Use MetadataFields mapping instead of hardcoded dict
            return_key = MetadataFields.RETURN_TYPE_MAP[return_type]
                
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
            returns_schedule = news_data.get('metadata', {}).get(MetadataFields.RETURNS_SCHEDULE, {})
            
            # Create schedule dict with only the specific return type
            specific_schedule = {return_type: returns_schedule.get(return_type)}
            self.logger.info(f"Processing {return_type} with time: {specific_schedule}")
            
            returns = {}
            # Get symbols from instruments list
            instruments = news_data.get('metadata', {}).get(MetadataFields.INSTRUMENTS, [])
            
            for instrument in instruments:
                symbol = instrument['symbol']
                symbol_returns = self._calculate_symbol_returns(
                    symbol,
                    news_data['created'],
                    specific_schedule,
                    current_time
                )
                
                # Use MetadataFields mapping for return keys
                return_key = MetadataFields.RETURN_TYPE_MAP[return_type]
                returns[symbol] = symbol_returns.get(return_key)

            return returns
        except Exception as e:
            self.logger.error(f"Error calculating specific return {return_type}: {e}")
            return None


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


    # Is this enough?
    def _reconnect(self):
        """Reconnect to Redis"""
        try:
            self.live_client = self.live_client.__class__(prefix=self.live_client.prefix)
            self.hist_client = self.hist_client.__class__(prefix=self.hist_client.prefix)
            self.queue_client = self.live_client.create_new_connection()

            self.pubsub_client = self.live_client.create_pubsub_connection()
            self.pubsub_client.subscribe('news:benzinga:live:processed')
            self.logger.debug("Reconnected to Redis")

        except Exception as e:
            self.logger.error(f"Reconnection failed: {e}")
