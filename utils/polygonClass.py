import logging
from polygon.rest import RESTClient
from typing import List, Dict, Tuple, Optional, Union, Generator
from dataclasses import dataclass
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures 
from tqdm import tqdm
import requests
import time
from .ETF_mappings import Sector_Industry_ETFs
from .market_session import MarketSessionClassifier
from utils.metadata_fields import MetadataFields  
from datetime import datetime, timezone, timedelta
import pytz
from utils.log_config import get_logger, setup_logging
import threading

@dataclass
class Polygon:
    api_key: str
    polygon_subscription_delay: int

    
    def __post_init__(self):
        """Initialize market session classifier and client"""

        # Initialize logger using centralized logging
        self.logger = get_logger(__name__)

        # Add semaphore for HTTP request concurrency control
        self.http_semaphore = threading.BoundedSemaphore(50)  # Balance between speed and stability

        self.market_session = MarketSessionClassifier()
        self.client = self.get_rest_client()
        self.executor = ThreadPoolExecutor(max_workers=180)
        self.last_error = {}
        self.ticker_validation_cache = {}
        

        # Add connection pooling configuration
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=100,
            pool_maxsize=100,
            max_retries=5,
            pool_block=False
        )
        self.session.mount('https://', adapter)


    def get_rest_client(self):
        """Return a new RESTClient instance per request."""
        return RESTClient(self.api_key)


    def validate_ticker(self, ticker: str) -> Tuple[bool, str]:
        """Validate if a ticker is an active common stock with caching."""
        # Check cache first
        if ticker in self.ticker_validation_cache:
            return self.ticker_validation_cache[ticker]
            
        try:
            ticker_details = self.get_rest_client().get_ticker_details(ticker)
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
        

    def get_last_trade(self, ticker: str, timestamp: datetime, asset_type: str = "stock", max_days_back: int = 3) -> float:
        
        acquired = False
        try:
            # Try to acquire semaphore with short timeout
            acquired = self.http_semaphore.acquire(timeout=2)
            # If can't acquire, continue without semaphore (less ideal but prevents slowdown)
            
            client = self.get_rest_client()

            # Define initial window and growth factor
            window_size = 300  # Start with 10 seconds
            growth_factor = 2  
            max_window = 86400 * max_days_back  # Convert max_days to seconds        

            # Skip validation for known ETFs
            if ticker not in Sector_Industry_ETFs:
                # Only validate non-ETF tickers
                is_valid, error_message = self.validate_ticker(ticker)
                if not is_valid:
                    self.last_error[ticker] = error_message
                    return np.nan

            timestamp = self.market_session._convert_to_eastern_timestamp(timestamp)
            if timestamp is None:
                raise ValueError("Timestamp cannot be None or NaN")
            
            # Check if timestamp is in the future
            current_time = datetime.now(timezone.utc).astimezone(pytz.timezone('America/New_York'))
            min_allowed_end = timestamp - timedelta(seconds=max_window)
            current_end = timestamp

            # Ideally this should code block never be reached since all filtering should be applied before this
            current_time_with_delay = current_time - timedelta(seconds=self.polygon_subscription_delay)
            if timestamp > current_time_with_delay:
                self.logger.info(f"Cannot fetch price for {ticker} at {timestamp} as it is in the future, current time + delay: {current_time_with_delay}, delay: {self.polygon_subscription_delay} seconds")
                return np.nan
            
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

                    aggs = client.get_aggs(
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
                        self.logger.info(f"NOT AUTHORIZED in error_msg")
                        self.logger.info(f"Ticker: {ticker}")
                        self.logger.info(f"Window size: {window_size}s")
                        self.logger.info(f"Max window: {max_window}s")
                        self.logger.info(f"Current end: {current_end}")
                        self.logger.info(f"Current start: {current_start}")
                        self.logger.info(f"Error message: {error_msg}")
                        self.logger.info(f"--------------------------------")

                        window_size = max(window_size // 2, 10)                    
                        # if current_end < min_allowed_end: return np.nan # Safety check for NOT_AUTHORIZED

                    else:
                        window_size = min(window_size * growth_factor, max_window)
                        # if current_end < min_allowed_end: return np.nan  # Add safety check here too
                        
                    continue
            
            # print(f"No price found for {ticker} in the last {max_days_back} days before {timestamp}")
            return np.nan
        finally:
            if acquired:
                self.http_semaphore.release()



    def _get_last_trade_worker(self, ticker: str, timestamp: datetime, max_days_back: int) -> float:
        """Worker function that creates a new Polygon instance per thread"""
        # Create new instance with its own connection pool
        polygon = Polygon(api_key=self.api_key, polygon_subscription_delay=self.polygon_subscription_delay)
        try:
            return polygon.get_last_trade(ticker, timestamp, max_days_back=max_days_back)
        finally:
            # Ensure cleanup
            polygon.__del__()

    # Using it for Batch or Historical Data
    def get_last_trades(self, ticker_timestamp_pairs: List[Tuple[str, datetime]], max_days_back: int = 1, pbar=None) -> Dict[str, float]:
        # Submit work to thread pool with dedicated worker function
        futures = {
            ticker: self.executor.submit(
                self._get_last_trade_worker, ticker, timestamp, max_days_back
            )
            for ticker, timestamp in ticker_timestamp_pairs
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

        # Calculate valid symbols (total minus validation failures)
        validation_failures = len(not_found_tickers) + len(wrong_market_tickers) + len(not_common_stock)
        valid_symbols = total_tickers - validation_failures
        
        # Calculate success rate based on valid symbols only
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
        

    def _get_price_worker(self, ticker: str, timestamp: datetime) -> float:
        """Worker function for getting prices with dedicated Polygon instance"""
        polygon = Polygon(api_key=self.api_key, polygon_subscription_delay=self.polygon_subscription_delay)
        try:
            # Use the semaphore from the new polygon instance
            return polygon.get_last_trade(ticker, timestamp)
        finally:
            polygon.__del__()


    # Calculates Returns inside
    # Takes in a list of tuples with index, ticker, start_time, end_time and returns a dictionary with index and return value - from QC df Returns
    def get_returns_indexed(self, index_ticker_times: List[Tuple[int, str, datetime, datetime]], pbar=None, debug: bool = False) -> Dict[int, float]:
        
        """
        Get returns with index tracking using concurrent futures
        Args: index_ticker_times: List of (index, ticker, start_time, end_time)
        Returns: Dict[index, return_value] """

        TIMEOUT = 30  # seconds
        
        # Create futures for start and end prices with dedicated instances
        start_futures = {
            (idx, ticker): self.executor.submit(self._get_price_worker, ticker, start_time)
            for idx, ticker, start_time, _ in index_ticker_times
        }
        
        end_futures = {
            (idx, ticker): self.executor.submit(self._get_price_worker, ticker, end_time)
            for idx, ticker, _, end_time in index_ticker_times
        }
        
        # Collect results maintaining index association
        start_prices = {}
        end_prices = {}
        
        # Create O(1) lookups
        start_future_to_key = {f: k for k, f in start_futures.items()}
        
        # Process start prices with O(1) lookup
        for future in concurrent.futures.as_completed(start_futures.values()):
            if pbar: pbar.update(1)
            idx, ticker = start_future_to_key[future]
            try:
                start_prices[(idx, ticker)] = future.result(timeout=TIMEOUT)
            except concurrent.futures.TimeoutError:
                print(f"Timeout getting start price for {ticker}")
                start_prices[(idx, ticker)] = np.nan
            except Exception as e:
                print(f"Error getting start price for {ticker}: {str(e)}")
                start_prices[(idx, ticker)] = np.nan
        
        # Create O(1) lookup for end futures
        end_future_to_key = {f: k for k, f in end_futures.items()}
        
        # Process end prices with O(1) lookup
        for future in concurrent.futures.as_completed(end_futures.values()):
            if pbar: pbar.update(1)
            idx, ticker = end_future_to_key[future]
            try:
                end_prices[(idx, ticker)] = future.result(timeout=TIMEOUT)
            except concurrent.futures.TimeoutError:
                print(f"Timeout getting end price for {ticker}")
                end_prices[(idx, ticker)] = np.nan
            except Exception as e:
                print(f"Error getting end price for {ticker}: {str(e)}")
                end_prices[(idx, ticker)] = np.nan
        
        # Calculate returns (unchanged from original)
        returns = {}
        for idx, ticker, start_time, end_time in index_ticker_times:
            s_price = start_prices.get((idx, ticker))
            e_price = end_prices.get((idx, ticker))
            
            if not (np.isnan(s_price) or np.isnan(e_price)):
                ret = (e_price - s_price) / s_price * 100
                if debug:
                    print(f"Index[{idx}] {ticker:<6}: ${s_price:>7.2f} -> ${e_price:>7.2f} = {ret:>6.2f}%")
                returns[idx] = ret
            else:
                returns[idx] = np.nan
                    
        return returns


    def __del__(self):
        """Cleanup executor on deletion"""
        self.executor.shutdown(wait=False)


    # https://polygon.io/docs/stocks?utm_source=chatgpt.com/get_v3_reference_tickers__ticker
    def get_ticker_details(self, ticker: str) -> Optional[Dict]:

        try:
            # Make API request using the client
            details = self.get_rest_client().get_ticker_details(ticker)
            
            if not details:
                return None
                
            # Return the results portion of the response
            return details
            
        except Exception as e:
            print(f"Error fetching ticker details for {ticker}: {str(e)}")
            return None


    def _fetch_related_companies_worker(self, ticker: str) -> Tuple[str, List[str]]:
        """Worker function for fetching related companies with dedicated instance"""
        polygon = Polygon(api_key=self.api_key, polygon_subscription_delay=self.polygon_subscription_delay)
        try:
            acquired = False
            try:
                # Try to acquire semaphore with short timeout
                acquired = polygon.http_semaphore.acquire(timeout=2)
                
                url = f"https://api.polygon.io/v1/related-companies/{ticker}"
                params = {'apiKey': polygon.api_key}
                response = requests.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'OK':
                        related_tickers = [r['ticker'] for r in data.get('results', [])]
                        return ticker, related_tickers
                return ticker, []
            finally:
                if acquired:
                    polygon.http_semaphore.release()
        finally:
            polygon.__del__()


    # https://polygon.io/docs/stocks?utm_source=chatgpt.com/get_v1_related-companies__ticker
    def get_related_companies(self, tickers: List[str], pbar=None) -> Dict[str, List[str]]:
        
        def _fetch_single_ticker(ticker: str) -> Tuple[str, List[str]]:
            try:
                url = f"https://api.polygon.io/v1/related-companies/{ticker}"
                params = {'apiKey': self.api_key}
                response = requests.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'OK':
                        related_tickers = [r['ticker'] for r in data.get('results', [])]
                        return ticker, related_tickers
                return ticker, []
                
            except Exception as e:
                print(f"Error fetching related companies for {ticker}: {str(e)}")
                return ticker, []

        # Submit all requests to the thread pool
        futures = {
            ticker: self.executor.submit(self._fetch_related_companies_worker, ticker)
            for ticker in tickers
        }
        
        # Process results
        results = {}
        for future in concurrent.futures.as_completed(futures.values()):
            if pbar:
                pbar.update(1)
            for ticker, f in futures.items():
                if f == future:
                    try:
                        original_ticker, related_tickers = future.result()
                        results[original_ticker] = related_tickers
                    except Exception as e:
                        print(f"Error processing {ticker}: {str(e)}")
                        results[ticker] = []
                    break
        
        # Print summary
        total_tickers = len(results)
        tickers_with_related = sum(1 for related in results.values() if related)
        
        print("\n" + "="*60)
        print("RELATED COMPANIES SUMMARY".center(60))
        print("="*60)
        print(f"Total Tickers Processed: {total_tickers}")
        print(f"Tickers with Related Companies: {tickers_with_related}")
        print(f"Success Rate: {(tickers_with_related/total_tickers*100):.1f}%")
        
        return results

    # Useful for single event returns
    # Returns : {'stock': 0.67, 'sector': 0.05, 'industry': -0.6, 'macro': 0.045}
    # return_type # One of MetadataFields.SESSION, DAILY, or HOURLY
    # pass stock, its associated ETFs and event timestamp and return type.
    def get_event_returns(
        self,
        ticker: str,
        sector_etf: str,
        industry_etf: str,
        event_timestamp: str,
        return_type: str,
        horizon_minutes: Optional[List[int]] = None,
        debug: bool = False
    ) -> Dict[str, Union[float, List[float]]]:
        """
        Calculate returns for stock, sector ETF, industry ETF, and SPY based on event timestamp.
        Args:
            return_type: One of MetadataFields.SESSION, DAILY, or HOURLY
            horizon_minutes: Required for HOURLY returns, list of minutes for horizons
        Returns:
            Dictionary with keys: 'stock', 'sector', 'industry', 'macro'.
            For HOURLY returns, each value is a list corresponding to horizon_minutes.
        """
        # Validate ticker
        is_valid, error_msg = self.validate_ticker(ticker)
        if not is_valid:
            return {k: np.nan for k in ['stock', 'sector', 'industry', 'macro']}

        # Define asset order
        assets = [(0, ticker), (1, sector_etf), (2, industry_etf), (3, 'SPY')]
        
        # Get time window based on return type
        if return_type == MetadataFields.SESSION:
            start_time = self.market_session.get_start_time(event_timestamp)
            end_time = self.market_session.get_end_time(event_timestamp)
            time_pairs = [(idx, ticker, start_time, end_time) for idx, ticker in assets]
        
        elif return_type == MetadataFields.DAILY:
            start_time, end_time = self.market_session.get_1d_impact_times(event_timestamp)
            time_pairs = [(idx, ticker, start_time, end_time) for idx, ticker in assets]
        
        # elif return_type == MetadataFields.HOURLY:
        #     horizon_minutes = horizon_minutes or [60]
        #     interval_start = self.market_session.get_interval_start_time(event_timestamp)
        #     time_pairs = [
        #         (idx*4 + asset_idx, asset_ticker, interval_start, interval_start + timedelta(minutes=minutes))
        #         for idx, minutes in enumerate(horizon_minutes)
        #         for asset_idx, asset_ticker in assets
        #     ]

        elif return_type == MetadataFields.HOURLY:
            horizon_minutes = horizon_minutes or [60]
            time_pairs = [
                (idx*4 + asset_idx, asset_ticker, 
                interval_start := self.market_session.get_interval_start_time(event_timestamp),
                self.market_session.get_interval_end_time(event_timestamp, minutes, respect_session_boundary=False))
                for idx, minutes in enumerate(horizon_minutes)
                for asset_idx, asset_ticker in assets
            ]
        
        else:
            raise ValueError(f"return_type must be one of: {MetadataFields.SESSION}, {MetadataFields.DAILY}, {MetadataFields.HOURLY}")
        
        # Calculate returns using concurrent execution
        returns_dict = self.get_returns_indexed(time_pairs, debug=debug)
        
        # Organize results based on return type
        if return_type in [MetadataFields.SESSION, MetadataFields.DAILY]:
            return {asset: returns_dict.get(idx) for idx, asset in enumerate(['stock', 'sector', 'industry', 'macro'])}
        else:
            return {
                asset: [returns_dict.get(i*4 + idx) for i in range(len(horizon_minutes))]
                for idx, asset in enumerate(['stock', 'sector', 'industry', 'macro'])
            }




    # This is a function that prepares time pairs for batch processing.
    # It takes in a news_df, return_type and horizon_minutes and returns a list of tuples ready for get_returns_indexed
    # news_df is a dataframe with columns [symbol, originalTime, sector_etf, industry_etf]
    def prepare_time_pairs(
        self,
        news_df: pd.DataFrame,
        return_type: str,
        horizon_minutes: Optional[List[int]] = None
    ) -> Dict[str, List[Tuple[int, str, datetime, datetime]]]:
        """Prepare (index, ticker, start_time, end_time) pairs organized by asset type."""

        news_df.index = news_df.index.map(lambda x: int(str(x).replace(',', '')))
        timestamps = pd.to_datetime(news_df['originalTime'])
        asset_types = {
            'stock': news_df['symbol'],
            'sector': news_df['sector_etf'],
            'industry': news_df['industry_etf'],
            'macro': pd.Series('SPY', index=news_df.index)
        }
        
        if return_type == MetadataFields.SESSION:
            starts = timestamps.map(self.market_session.get_start_time)
            ends = timestamps.map(self.market_session.get_end_time)
            
            return {
                asset_type: [
                    (int(idx), str(ticker), start, end)
                    for idx, ticker, start, end 
                    in zip(news_df.index, tickers, starts, ends)
                ]
                for asset_type, tickers in asset_types.items()
            }
        
        elif return_type == MetadataFields.DAILY:
            times = timestamps.map(self.market_session.get_1d_impact_times)
            
            return {
                asset_type: [
                    (int(idx), str(ticker), t[0], t[1])
                    for idx, ticker, t 
                    in zip(news_df.index, tickers, times)
                ]
                for asset_type, tickers in asset_types.items()
            }
        
        # elif return_type == MetadataFields.HOURLY:
        #     horizon_minutes = horizon_minutes or [60]
        #     # if not horizon_minutes:
        #     #     raise ValueError("horizon_minutes required for horizon return type")
                    
        #     starts = timestamps.map(self.market_session.get_interval_start_time)
            
        #     return {
        #         h: {
        #             asset_type: [
        #                 (int(idx), str(ticker), 
        #                 min(start, start + pd.Timedelta(minutes=h)),  # Earlier time becomes start
        #                 max(start, start + pd.Timedelta(minutes=h)))  # Later time becomes end
        #                 for idx, ticker, start in zip(news_df.index, tickers, starts)
        #             ]
        #             for asset_type, tickers in asset_types.items()
        #         }
        #         for h in horizon_minutes
        #     }
        
        # only works for forward time. so do not use -timedelta in interval_minutes unlike above commented out code
        elif return_type == MetadataFields.HOURLY:
            horizon_minutes = horizon_minutes or [60]
            return {
                h: {
                    asset_type: [
                        (int(idx), str(ticker), 
                        interval_start := self.market_session.get_interval_start_time(timestamp),
                        self.market_session.get_interval_end_time(timestamp, h, respect_session_boundary=False))
                        for idx, ticker, timestamp in zip(news_df.index, tickers, timestamps)
                    ]
                    for asset_type, tickers in asset_types.items()
                }
                for h in horizon_minutes
            }
                


    def get_structured_returns(self, news_df: pd.DataFrame, return_type: str = MetadataFields.SESSION, horizon_minutes: Optional[List[int]] = None) -> pd.DataFrame:
        """Returns DataFrame of asset returns indexed by news_df rows."""        
        pairs = self.prepare_time_pairs(news_df, return_type, horizon_minutes)
        returns = {
            f"{asset}{h}" if return_type == MetadataFields.HOURLY else f"{asset}_{return_type}": 
            self.get_returns_indexed(pairs[h][asset] if return_type == MetadataFields.HOURLY else pairs[asset])
            for h in (pairs.keys() if return_type == MetadataFields.HOURLY else [''])
            for asset in ['stock', 'sector', 'industry', 'macro']
        }
        return pd.DataFrame.from_dict(returns, orient='columns')
    


    def __del__(self):
        """Cleanup resources on deletion"""
        try:
            self.executor.shutdown(wait=False)
            self.session.close()
        except:
            pass