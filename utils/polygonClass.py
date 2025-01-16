from polygon.rest import RESTClient
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures 
from tqdm import tqdm
import requests

@dataclass
class Polygon:
    api_key: str
    
    def __post_init__(self):
        """Initialize market session classifier and client"""
        from .market_session import MarketSessionClassifier
        self.market_session = MarketSessionClassifier()
        self.client = RESTClient(self.api_key)
        self.executor = ThreadPoolExecutor(max_workers=220)
        self.last_error = {}
        self.ticker_validation_cache = {}  # Add validation cache



    def validate_ticker(self, ticker: str) -> Tuple[bool, str]:
        """Validate if a ticker is an active common stock with caching."""
        # Check cache first
        if ticker in self.ticker_validation_cache:
            return self.ticker_validation_cache[ticker]
            
        try:
            ticker_details = self.client.get_ticker_details(ticker)
            if not ticker_details:
                result = (False, f"Invalid ticker: {ticker}")
                self.ticker_validation_cache[ticker] = result
                return result
            
            try:
                security_type = getattr(ticker_details, 'type', '').lower()
            except AttributeError:
                result = (False, f"Invalid security type for {ticker}")
                self.ticker_validation_cache[ticker] = result
                return result
            
            if security_type == 'etf':
                result = (False, f"{ticker} is an ETF, not a stock")  # Missing cache
                self.ticker_validation_cache[ticker] = result
                return result
            elif security_type not in ['cs', 'common_stock']:
                result = (False, f"{ticker} is not a common stock (type: {security_type})")  # Missing cache
                self.ticker_validation_cache[ticker] = result
                return result
            elif not ticker_details.active:
                result = (False, f"{ticker} is not an active security")  # Missing cache
                self.ticker_validation_cache[ticker] = result
                return result
            elif ticker_details.market != "stocks":
                result = (False, f"{ticker} is not in the stocks market")  # Missing cache
                self.ticker_validation_cache[ticker] = result
                return result
                
            result = (True, "")  # Missing cache for successful validation
            self.ticker_validation_cache[ticker] = result
            return result
            
        except Exception as e:
            error_msg = str(e)
            if "NOT_FOUND" in error_msg:
                result = (False, f"Ticker not found: {ticker}")
            else:
                result = (False, f"Error validating {ticker}: {error_msg}")
            self.ticker_validation_cache[ticker] = result
            return result
        


    def get_last_trade(self, ticker: str, timestamp: datetime, max_days_back: int = 3) -> float:
        # Validate ticker first
        is_valid, error_message = self.validate_ticker(ticker)
        if not is_valid:
            # print(f"Warning: {error_message}\n")
            self.last_error[ticker] = error_message  # Store the error message
            return np.nan

        timestamp = self.market_session._convert_to_eastern_timestamp(timestamp)
        if timestamp is None:
            raise ValueError("Timestamp cannot be None or NaN")
        
        # Define initial window and growth factor
        window_size = 300  # Start with 10 seconds
        growth_factor = 2  
        max_window = 86400 * max_days_back  # Convert max_days to seconds
        min_allowed_end = timestamp - timedelta(seconds=max_window)

        current_end = timestamp
        
        while window_size <= max_window:
            if current_end < min_allowed_end:
                print(f"No price found for {ticker} between {min_allowed_end} and {timestamp}")
                return np.nan
            try:
                current_start = current_end - timedelta(seconds=window_size)

                # Use smaller limit for small windows, larger for bigger windows
                if window_size <= 300:  # 5 minutes or less
                    limit = 5000  # Default limit for small windows
                else:
                    limit = 49998  # Max limit for larger windows

                aggs = self.client.get_aggs(
                    ticker=ticker,
                    multiplier=1,
                    timespan="second",
                    from_=int(current_start.timestamp() * 1000),
                    to=int(current_end.timestamp() * 1000),
                    adjusted=True,
                    sort="desc",
                    limit=limit
                )
                
                if aggs and len(aggs) > 0:
                    for agg in aggs:
                        agg_timestamp = pd.Timestamp(agg.timestamp, unit='ms', tz='US/Eastern')
                        if agg_timestamp <= timestamp:
                            # print(f"Found price at: {agg_timestamp} using {window_size}s window")
                            return agg.close
                
                current_end = current_end - timedelta(seconds=window_size)
                window_size = min(window_size * growth_factor, max_window)
                
            except Exception as e:
                error_msg = str(e)

                print(f"Exact error for {ticker}: {error_msg}")

                if "NOT_AUTHORIZED" in error_msg:
                    # To be Removed
                    print(f"Ticker: {ticker}")
                    print(f"Window size: {window_size}s")
                    print(f"Max window: {max_window}s")
                    print(f"Current end: {current_end}")
                    print(f"Current start: {current_start}")
                    print(f"Error message: {error_msg}")

                    window_size = max(window_size // 2, 10)                    
                    # if current_end < min_allowed_end: return np.nan # Safety check for NOT_AUTHORIZED

                else:
                    window_size = min(window_size * growth_factor, max_window)
                    # if current_end < min_allowed_end: return np.nan  # Add safety check here too
                    
                continue
        
        print(f"No price found for {ticker} in the last {max_days_back} days before {timestamp}")
        return np.nan



    def get_last_trades(self, tickers: List[str], timestamp: datetime, max_days_back: int = 3, pbar=None) -> Dict[str, float]:
        futures = {
            ticker: self.executor.submit(self.get_last_trade, ticker, timestamp, max_days_back)
            for ticker in tickers
        }
        
        results = {}
        exception_count = 0
        not_found_tickers = []
        wrong_market_tickers = []
        not_common_stock = []
        no_price_tickers = []
        
        for future in concurrent.futures.as_completed(futures.values()):
            if pbar:
                pbar.update(1)
            for ticker, f in futures.items():
                if f == future:
                    try:
                        results[ticker] = future.result()
                        if np.isnan(results[ticker]):
                            # Use the warning message that was already printed in get_last_trade
                            if "not found" in self.last_error.get(ticker, "").lower():
                                not_found_tickers.append(ticker)
                            elif "not in the stocks market" in self.last_error.get(ticker, ""):
                                wrong_market_tickers.append(ticker)
                            elif "not a common stock" in self.last_error.get(ticker, "") or "is an ETF" in self.last_error.get(ticker, ""):
                                not_common_stock.append(ticker)
                            else:
                                no_price_tickers.append(ticker)
                    except Exception as e:
                        print(f"Error processing {ticker}: {str(e)}")
                        results[ticker] = np.nan
                        exception_count += 1
                        no_price_tickers.append(ticker)
                    break
        
        # Complete summary
        total_tickers = len(results)
        valid_prices = sum(1 for price in results.values() if not np.isnan(price))
        nan_prices = sum(1 for price in results.values() if np.isnan(price))
        
        # Before returning results, filter out validation failures
        filtered_results = {}
        for ticker, price in results.items():
            error_msg = self.last_error.get(ticker, "")
            # Only include if it's not a validation failure
            if not any(msg in error_msg for msg in ["not found", "not in the stocks market", "not a common stock", "is an ETF"]):
                filtered_results[ticker] = price


        # print(f"\nComplete Summary:")
        # print(f"Total tickers processed: {total_tickers}")
        # print(f"Valid prices found: {valid_prices}")
        # print(f"NaN prices (including validation failures): {nan_prices}")
        # print(f"Exceptions during processing: {exception_count}")
        # print(f"Success rate: {(valid_prices/total_tickers*100):.1f}%")
        # print(f"\nFailure Breakdown:")
        # print(f"Tickers not found: {len(not_found_tickers)}")
        # print(f"Tickers not in stocks market: {len(wrong_market_tickers)}")
        # print(f"Tickers not common stock: {len(not_common_stock)}")
        # print(f"Tickers with no price data: {len(no_price_tickers)}, -> {no_price_tickers}")

        # Calculate valid symbols (total minus validation failures)
        validation_failures = len(not_found_tickers) + len(wrong_market_tickers) + len(not_common_stock)
        valid_symbols = total_tickers - validation_failures
        
        # Calculate true success rate based on valid symbols only
        success_rate = (valid_prices/valid_symbols*100) if valid_symbols > 0 else 0


        print("\n" + "="*60)
        print("COMPLETE SUMMARY".center(60))
        print("="*60)
        print(f"Total Tickers Processed: {total_tickers}")
        print("-"*60)
        
        print("VALIDATION METRICS".center(60))
        print(f"Valid Symbols:           {valid_symbols:>6}")
        print(f"Invalid Symbols:         {validation_failures:>6}")
        print("-"*60)
        
        print("SUCCESS METRICS (Based on Valid Symbols Only)".center(60))
        print(f"✓ Prices Found :         {valid_prices:>6}")
        print(f"✗ No Data Found:         {len(no_price_tickers):>6}")
        print(f"  Success Rate :         {success_rate:>6.1f}%")
        print("-"*60)
        
        print("FAILURE BREAKDOWN".center(60))
        print(f"Validation Failures:      {validation_failures:>6}")
        print(f"  ├─ Not Found:          {len(not_found_tickers):>6}")
        print(f"  ├─ Not Stocks Market:  {len(wrong_market_tickers):>6}")
        print(f"  └─ Not Common Stock:   {len(not_common_stock):>6}")
        print()
        print(f"Data Failures:           {len(no_price_tickers):>6}, -> {no_price_tickers}")
        

        return filtered_results
        





    def __del__(self):
        """Cleanup executor on deletion"""
        self.executor.shutdown(wait=False)