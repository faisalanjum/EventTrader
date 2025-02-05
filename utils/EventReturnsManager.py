from dataclasses import dataclass, asdict
from typing import Dict, List, Union, Optional
from datetime import datetime, timedelta
import pytz
import logging
from eventtrader.keys import POLYGON_API_KEY
from utils.polygonClass import Polygon
from utils.market_session import MarketSessionClassifier
from utils.metadata_fields import MetadataFields 



@dataclass
class Benchmark:
    """Benchmark ETFs for sector and industry comparisons"""
    sector: str
    industry: str


@dataclass
class Instrument:
    """Financial instrument with its benchmark information"""
    symbol: str
    benchmarks: Benchmark


@dataclass
class ReturnSchedule:
    """Schedule for calculating returns at different intervals"""
    hourly: str
    session: str
    daily: str


@dataclass
class EventInfo:
    """Event metadata including market session and creation time"""
    market_session: str
    created: str


@dataclass
class EventMetadata:
    """Complete metadata structure for an event"""
    event: EventInfo
    returns_schedule: ReturnSchedule
    instruments: List[Instrument]
    
    def to_dict(self) -> Dict:
        """Convert to dict format maintaining backward compatibility"""
        return {
            'metadata': {
                MetadataFields.EVENT: asdict(self.event),
                MetadataFields.RETURNS_SCHEDULE: asdict(self.returns_schedule),
                MetadataFields.INSTRUMENTS: [asdict(i) for i in self.instruments]
            }
        }


class EventReturnsManager:
    """
    Manages event metadata and return calculations for both news and reports.
    Provides a unified interface regardless of number of symbols.
    """
    def __init__(self, stock_universe_df):
        self.stock_universe = stock_universe_df
        self.ny_tz          = pytz.timezone("America/New_York")

        self.market_session = MarketSessionClassifier()
        self.polygon        = Polygon(api_key=POLYGON_API_KEY)

        self.logger         = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)



    def process_event_metadata(self, 
                            event_time: datetime,
                            symbols: Union[str, List[str]]) -> Optional[Dict]:
        """Process event metadata for either news or reports
        
        Args:
            event_time: Event timestamp
            symbols: Single symbol or list of symbols
            
        Returns:
            Optional[Dict]: Metadata dictionary or None if processing fails
        """
        try:
            # Normalize input to list
            symbol_list = [symbols] if isinstance(symbols, str) else symbols
            
            # Generate event info
            event_info = EventInfo(
                market_session=self._get_market_metadata(event_time),
                created=event_time.isoformat()
            )
            
            # Generate return schedule
            returns_schedule = self._calculate_return_times(event_time)

            
            # Generate instruments data with per-symbol error handling
            instruments = []
            for symbol in symbol_list:
                try:
                    benchmarks = Benchmark(
                        sector=self._get_etf(symbol, 'sector_etf'),
                        industry=self._get_etf(symbol, 'industry_etf')
                    )
                    instruments.append(Instrument(symbol=symbol, benchmarks=benchmarks))
                except Exception as e:
                    self.logger.error(f"Error processing symbol {symbol}: {e}")
                    continue
            
            # Create metadata object
            metadata = EventMetadata(
                event=event_info,
                returns_schedule=returns_schedule,
                instruments=instruments
            )
            
            return metadata.to_dict()
            
        except Exception as e:
            self.logger.error(f"Metadata generation failed: {e}")
            return None
        

    def _calculate_return_times(self, event_time: datetime) -> ReturnSchedule:
        """Calculate all return timing windows
        
        Args:
            event_time: Event timestamp
        
        Returns:
            dict: Return schedule times in format compatible with ReturnSchedule
            
        Raises:
            Exception: If calculation fails
        """
        try:
            interval_start = self.market_session.get_interval_start_time(event_time)
            interval_end = interval_start + timedelta(minutes=60)
            session_end = self.market_session.get_end_time(event_time)
            one_day_impact_times = self.market_session.get_1d_impact_times(event_time)
            
            return ReturnSchedule(
                hourly=interval_end.isoformat(),
                session=session_end.isoformat(),
                daily=one_day_impact_times[1].isoformat()
            )
        except Exception as e:
            self.logger.error(f"Error calculating return times: {e}")
            raise



    def _get_market_metadata(self, event_time: datetime) -> str:
        """Get market session information"""
        return self.market_session.get_market_session(event_time)



    def _get_etf(self, symbol: str, etf_type: str) -> str:
        """Get ETF information for a symbol
        
        Args:
            symbol: Stock symbol to look up
            etf_type: Either 'sector_etf' or 'industry_etf'
        
        Returns:
            str: ETF symbol
            
        Raises:
            ValueError: If symbol not found in universe
        """
        symbol = symbol.strip().upper()
        matches = self.stock_universe[self.stock_universe.symbol == symbol]
        if matches.empty:
            raise ValueError(f"Symbol {symbol} not found in stock universe")
        return matches[etf_type].values[0]