from dataclasses import dataclass, asdict
from typing import Dict, List, Union, Optional, Tuple, Any, cast
from datetime import datetime, timedelta, timezone
import pandas as pd
import pytz
import logging
from eventtrader.keys import POLYGON_API_KEY
from utils.polygonClass import Polygon
from utils.market_session import MarketSessionClassifier
from utils.metadata_fields import MetadataFields 
from utils.log_config import get_logger, setup_logging
from zoneinfo import ZoneInfo


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


@dataclass
class EventReturn:
    """Unified structure for event returns"""
    event_id: str
    metadata: EventMetadata  # Use metadata instead of separate fields
    returns: Optional[Dict[str, Any]] = None


class EventReturnsManager:
    """
    Manages event metadata and return calculations for both news and reports.
    Provides a unified interface regardless of number of symbols.
    """
    def __init__(self, stock_universe_df, polygon_subscription_delay: int):
        self.stock_universe = stock_universe_df
        self.ny_tz          = pytz.timezone("America/New_York")
        self.polygon_subscription_delay = polygon_subscription_delay

        self.market_session = MarketSessionClassifier()
        self.polygon  = Polygon(api_key=POLYGON_API_KEY, polygon_subscription_delay=polygon_subscription_delay)

        self.logger = get_logger(__name__)


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
            interval_end = self.market_session.get_interval_end_time(event_time, 60, respect_session_boundary=False)
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

########################################################################################
# For Returns Calculation

    def process_events(self, events: List[Dict]) -> List[EventReturn]:
        """Process multiple events for returns calculation"""
        if not isinstance(events, list) or not events:
            return []

        event_returns = []
        time_pairs = []
        event_mapping = {}

        # 1. Process events and generate metadata
        for event_idx, event in enumerate(events):
            try:
                # self.logger.info(f"Processing event: {event}")  # Debug print
                
                # Basic validation
                if not all(k in event for k in ['event_id', 'created', 'symbols', 'metadata']):
                    self.logger.error(f"Event missing required fields: {event}")
                    continue

                # Create EventReturn instance using existing metadata
                event_return = EventReturn(
                    event_id=event['event_id'],
                    metadata=EventMetadata(
                        event=EventInfo(**event['metadata']['event']),
                        returns_schedule=ReturnSchedule(**event['metadata']['returns_schedule']),
                        instruments=[
                            Instrument(
                                symbol=i['symbol'],
                                benchmarks=Benchmark(**i['benchmarks'])
                            ) for i in event['metadata']['instruments']
                        ]
                    )
                )
                event_returns.append(event_return)

                # Generate time pairs
                pairs, mapping = self._generate_time_pairs(
                    event_idx=event_idx,
                    event_id=event['event_id'],
                    metadata=event_return.metadata
                )
                time_pairs.extend(pairs)
                event_mapping.update(mapping)
                
            except Exception as e:
                self.logger.error(f"Error processing event {event.get('event_id')}: {e}")
                continue

        if not event_returns:
            return []

        # 2. Batch calculate returns
        try:
            returns_dict = self.polygon.get_returns_indexed(time_pairs)
        except Exception as e:
            self.logger.error(f"Error calculating returns: {e}")
            return event_returns

        # 3. Map returns back to events
        for event_return in event_returns:
            try:
                event_return.returns = self._map_returns(
                    event_return.event_id,
                    returns_dict,
                    event_mapping
                )
            except Exception as e:
                self.logger.error(f"Error mapping returns for {event_return.event_id}: {e}")
                event_return.returns = None

        return event_returns


    def _generate_time_pairs(self, event_idx: int, event_id: str, 
                        metadata: EventMetadata) -> Tuple[List, Dict]:
        """
        Generate time pairs using EventMetadata
        Args:
            event_idx: Index for batch processing
            event_id: Unique event identifier
            metadata: Event metadata
        Returns:
            Tuple[List, Dict]: Time pairs and mapping dictionary
        Raises:
            ValueError: If metadata is invalid
        """
        if not metadata.instruments:
            raise ValueError(f"No valid instruments for event {event_id}")
        

        time_pairs = []
        mapping = {}
        
        created = pd.to_datetime(metadata.event.created)
        return_windows = {
            MetadataFields.HOURLY: (
                self.market_session.get_interval_start_time(created),
                pd.to_datetime(metadata.returns_schedule.hourly)
            ),
            MetadataFields.SESSION: (
                self.market_session.get_start_time(created),
                pd.to_datetime(metadata.returns_schedule.session)
            ),
            MetadataFields.DAILY: (
                self.market_session.get_1d_impact_times(created)[0],
                pd.to_datetime(metadata.returns_schedule.daily)
            )
        }

        # Get current time with delay adjustment for filtering future timestamps
        current_time = datetime.now(timezone.utc).astimezone(pytz.timezone('America/New_York'))
        current_time_with_delay = current_time - timedelta(seconds=self.polygon_subscription_delay)

        for instr_idx, instrument in enumerate(metadata.instruments):
            for return_type, (start, end) in return_windows.items():
                # Skip this return window if the end time is in the future
                if end > current_time_with_delay:
                    self.logger.info(f"Skipping {return_type} for {instrument.symbol} - end time {end} is in the future (current time + delay: {current_time_with_delay})")
                    continue
                    
                base_idx = f"{event_id}:{return_type}:{instr_idx}"
                assets = [
                    ('stock', instrument.symbol),
                    ('sector', instrument.benchmarks.sector),
                    ('industry', instrument.benchmarks.industry),
                    ('macro', 'SPY')
                ]
                
                for asset_idx, (asset_type, symbol) in enumerate(assets):
                    idx = f"{base_idx}:{asset_idx}"
                    time_pairs.append((idx, symbol, start, end))
                    mapping[idx] = {
                        'event_id': event_id,
                        'symbol': instrument.symbol,
                        'return_type': return_type,
                        'asset_type': asset_type
                    }

        return time_pairs, mapping
    

    

    def _map_returns(self, event_id: str, returns_dict: Dict, event_mapping: Dict) -> Dict:
        """Map returns to standard format matching EventMetadata structure"""
        returns = {'symbols': {}}
        
        for idx, value in returns_dict.items():
            if event_mapping[idx]['event_id'] != event_id:
                continue
                
            mapping = event_mapping[idx]
            symbol = mapping['symbol']
            return_type = f"{mapping['return_type']}_return"  # Consistent with MetadataFields
            asset_type = mapping['asset_type']
            
            if symbol not in returns['symbols']:
                returns['symbols'][symbol] = {}
            if return_type not in returns['symbols'][symbol]:
                returns['symbols'][symbol][return_type] = {}
                
            returns['symbols'][symbol][return_type][asset_type] = round(value, 2)

        return returns
    


    def process_single_event(self, event_id: str, created: Union[str, datetime], 
                            symbols: Union[str, List[str]]) -> EventReturn:
        """
        Process a single event (convenience method)
        Args:
            event_id: Unique identifier
            created: Event timestamp
            symbols: Symbol or list of symbols
        Returns:
            EventReturn: Processed event with returns
        """
        return self.process_events([{
            'event_id': event_id,
            'created': created,
            'symbols': [symbols] if isinstance(symbols, str) else symbols
        }])[0]


########################################################################################