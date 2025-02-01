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
        self.redis_client = event_trader_redis.bz_livenews
        self.hist_client = event_trader_redis.bz_histnews
        self.queue_client = self.redis_client
        self.should_run = True
        self._lock = threading.Lock()
        
        # Initialize Polygon client
        self.polygon = Polygon(api_key=POLYGON_API_KEY)
        
        # Cache the stock universe for ETF lookups
        self.stock_universe = event_trader_redis.get_stock_universe()

        # Configure logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def process_all_returns(self):
        """Main processing loop to handle returns calculation"""
        self.logger.info("Starting returns processing")
        consecutive_errors = 0
        
        while self.should_run:
            try:
                # Process both hist and live processed queues
                for client in [self.hist_client, self.redis_client]:
                    self._process_returns_for_client(client)
                    consecutive_errors = 0
                time.sleep(1)  # Prevent tight loop
                
            except Exception as e:
                self.logger.error(f"Returns processing error: {e}")
                consecutive_errors += 1
                if consecutive_errors > 10:
                    self.logger.error("Too many consecutive errors, reconnecting...")
                    self._reconnect()
                    consecutive_errors = 0
                time.sleep(1)

    def _reconnect(self):
        """Reconnect to Redis"""
        try:
            self.redis_client = self.redis_client.__class__(
                prefix=self.redis_client.prefix
            )
            self.hist_client = self.hist_client.__class__(
                prefix=self.hist_client.prefix
            )
            self.queue_client = self.redis_client
        except Exception as e:
            self.logger.error(f"Reconnection failed: {e}")

    def _process_returns_for_client(self, client):
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
            # 1. Get and validate data
            content = client.get(key)
            if not content:
                return False
            processed_dict = json.loads(content)

            # 2. Check timestamps and calculate available returns
            returns_info = self._calculate_available_returns(processed_dict)
            
            # 3. Extract ID and create new unified namespace key
            news_id = key.split(':')[-1]  # Get the ID portion
            
            # Debug log to verify namespace decision
            self.logger.info(f"All complete: {returns_info['all_complete']}")
            
            if returns_info['all_complete']:
                new_key = f"news:benzinga:withreturns:{news_id}"
                self.logger.info(f"Moving to withreturns: {new_key}")
            else:
                new_key = f"news:benzinga:withoutreturns:{news_id}"
                self.logger.info(f"Moving to withoutreturns: {new_key}")



            # 4. Update processed_dict with returns
            processed_dict['returns'] = returns_info['returns']

            # 5. Atomic update using pipeline
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
        
        # Convert current time to NY timezone
        ny_tz = pytz.timezone("America/New_York")
        current_time = datetime.now(timezone.utc).astimezone(ny_tz)
        
        returns_data = {'symbols': {}}
        all_complete = True

        for symbol in processed_dict.get('symbols', []):
            try:
                symbol_returns = self._calculate_symbol_returns(
                    symbol, 
                    processed_dict['created'],
                    timefor_returns,
                    current_time
                )
                
                # Safely check for None/empty returns
                returns_data['symbols'][symbol] = symbol_returns
                if any(not returns or returns is None for returns in symbol_returns.values()):
                    all_complete = False
            except Exception as e:
                self.logger.error(f"Error processing returns for symbol {symbol}: {e}")
                returns_data['symbols'][symbol] = {
                    'session': None,
                    '1d_impact': None,
                    '1h_impact': None
                }
                all_complete = False

        return {
            'returns': returns_data,
            'all_complete': all_complete
        }

    def _calculate_symbol_returns(self, symbol: str, created: str, timefor_returns: dict, current_time: datetime) -> dict:
        """Calculate returns for a single symbol"""
        symbol = symbol.strip().upper()
        sector_etf = self.get_etf(symbol, 'sector_etf')
        industry_etf = self.get_etf(symbol, 'industry_etf')
        
        # Add debug logging
        self.logger.info(f"\nProcessing returns for {symbol}")
        self.logger.info(f"Current time (NY): {current_time}")  # current_time is already in NY timezone


        returns = {
            'session': {},
            '1d_impact': {},
            '1h_impact': {}
        }

        return_types = [
            ('session', 'session', None, timefor_returns.get('session_end_time')),
            ('1d_impact', '1d_impact', None, timefor_returns.get('1d_end_time')),
            ('1h_impact', 'horizon', [60], timefor_returns.get('1h_end_time'))
        ]

        for return_key, return_type, horizon, end_time in return_types:
            if end_time:
                end_time_dt = parser.parse(end_time)
                self.logger.info(f"{return_key}: End time = {end_time_dt}, Should calculate = {current_time > end_time_dt}")
                
            if end_time and current_time > parser.parse(end_time):
                try:
                    calc_returns = self.polygon.get_event_returns(
                        ticker=symbol,
                        sector_etf=sector_etf,
                        industry_etf=industry_etf,
                        event_timestamp=created,
                        return_type=return_type,
                        horizon_minutes=horizon
                    )
                    
                    # Handle horizon returns
                    if return_type == 'horizon':
                        calc_returns = {k: v[0] for k, v in calc_returns.items()}
                    
                    # Round returns
                    returns[return_key] = {k: round(v, 2) for k, v in calc_returns.items()}
                    self.logger.info(f"✓ Calculated {return_key} returns")
                except Exception as e:
                    self.logger.error(f"Error calculating {return_key} returns for {symbol}: {e}")
                    returns[return_key] = None
            else:
                self.logger.info(f"✗ Skipping {return_key} - time not reached or no end time")
                returns[return_key] = None

        return returns

    def get_etf(self, ticker: str, col='industry_etf'):
        """Get sector or industry ETF for a ticker"""
        ticker = ticker.strip().upper()
        matches = self.stock_universe[self.stock_universe.symbol == ticker]
        if matches.empty:
            raise ValueError(f"Symbol {ticker} not found in stock universe")
        return matches[col].values[0]

    def stop(self):
        """Stop processing"""
        self.should_run = False