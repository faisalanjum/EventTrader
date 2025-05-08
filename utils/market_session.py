import pandas as pd
import exchange_calendars as xcals
from datetime import datetime, date, timedelta
import pytz
import logging

logger = logging.getLogger(__name__)

""" Handles market session classification with timezone awareness. Exchange calendar returns UTC times,
while market hours are defined in ET (e.g., 9:30 AM - 4:00 PM ET), requiring consistent timezone handling. """

class MarketSessionClassifier:
    def __init__(self):
        self.calendar = xcals.get_calendar("XNYS")
        self.eastern = pytz.timezone('America/New_York')
        self.add_minutes_to_open = 5

    # Helper Functions
    def _convert_to_eastern_timestamp(self, input_value):
        """
        Converts various date/time inputs to a timezone-aware timestamp in US/Eastern.
        
        Handles:
        - str ('YYYY-MM-DD' or full datetime string)
        - datetime
        - date
        - pd.Timestamp
        """

        if pd.isna(input_value) or input_value is None:
            return None
        
        
        if isinstance(input_value, str):
            try:
                # Try parsing as date first
                input_value = datetime.strptime(input_value, '%Y-%m-%d')
            except ValueError:
                # If that fails, parse as full timestamp
                input_value = pd.Timestamp(input_value)
        elif isinstance(input_value, date) and not isinstance(input_value, datetime):
            # Convert date to datetime
            input_value = datetime.combine(input_value, datetime.min.time())
        
        if not isinstance(input_value, pd.Timestamp):
            input_value = pd.Timestamp(input_value)
        
        # Ensure timezone is US/Eastern
        if input_value.tzinfo is None:
            try:
                input_value = input_value.tz_localize('America/New_York', ambiguous='raise', nonexistent='raise')
            except (pytz.AmbiguousTimeError, pytz.NonExistentTimeError):
                input_value = input_value.tz_localize('UTC').tz_convert('America/New_York')
        elif input_value.tzinfo != self.eastern:
            input_value = input_value.tz_convert('America/New_York')
        
        return input_value


    # Market Session
    def get_market_session(self, timestamp):
        """Get the market session for a given timestamp"""
        if pd.isna(timestamp):
            return 'market_closed'
        
        timestamp = self._convert_to_eastern_timestamp(timestamp)
        date = timestamp.date()
        
        if not self.calendar.is_session(date):
            return 'market_closed'
        
        try:
            session = self.calendar.date_to_session(date, direction='previous')
            schedule = self.calendar.schedule.loc[session]
            
            utc_timestamp = timestamp.tz_convert('UTC')
            session_open = schedule['open']
            session_close = schedule['close']
            
            is_early_close = session in self.calendar.early_closes
            
            pre_market_start = session_open - pd.Timedelta(hours=5.5)
            post_market_end = session_close if is_early_close else session_close + pd.Timedelta(hours=4)
            
            if utc_timestamp < pre_market_start or utc_timestamp >= post_market_end:
                return 'market_closed'
            elif utc_timestamp < session_open:
                return 'pre_market'
            elif utc_timestamp <= session_close:
                return 'in_market'
            else:
                return 'market_closed' if is_early_close else 'post_market'
                
        except (xcals.errors.NotSessionError, ValueError):
            return 'market_closed'



    # Trading Hours
    def get_trading_hours(self, date_input):
        """
        Get trading hours for previous, current, and next trading days.
        
        1. Convert input to date using timezone-aware conversion
        2. Check if current date is trading day using calendar.is_session
        3. Find previous trading day using calendar.previous_session
        4. Find next trading day using calendar.next_session
        5. Return ((prev_times, current_times, next_times), is_trading_day)
        """

        # 1. Convert input to date
        # Handle all possible invalid inputs
        try:
            if pd.isna(date_input) or date_input is None:
                return None, False
                
            # Try to convert, catch any conversion errors
            try:
                date = self._convert_to_eastern_timestamp(date_input)
                if date is None:
                    return None, False
                date = date.date()
            except (ValueError, TypeError, pd.errors.OutOfBoundsDatetime):
                return None, False
        
            # 2. Check if it's a trading day
            is_trading_day = self.calendar.is_session(date)
        

            # 3. Get sessions
            # For current, get the actual date's session (not previous)
            current_session = self.calendar.date_to_session(date) if is_trading_day else date
            # For previous, start from input date and go backwards
            prev_session = self.calendar.date_to_session(date - pd.Timedelta(days=1), direction='previous')
            # For next, start from input date and go forwards
            next_session = self.calendar.date_to_session(date + pd.Timedelta(days=1), direction='next')
            
            def create_session_times(session_date):
                schedule = self.calendar.schedule.loc[session_date]
                is_early = session_date in self.calendar.early_closes
                
                session_open = schedule['open']  # UTC
                session_close = schedule['close']  # UTC
                pre_market_start = session_open - pd.Timedelta(hours=5.5)

                # Actual behavior maybe postmarket closes around 5 pm  on early close days (not sure)
                # post_market_end = (session_close + pd.Timedelta(hours=4) if is_early 
                #                 else session_close + pd.Timedelta(hours=4))
                
                # going with this for now (postmarket closes at session close on early close days)
                post_market_end = (session_close if is_early 
                                else session_close + pd.Timedelta(hours=4))
                
                return tuple(t.tz_convert('America/New_York') for t in 
                            (pre_market_start, session_open, session_close, post_market_end))
            
            # 4. Create session times
            prev_times = create_session_times(prev_session)
            curr_times = 'market_closed' if not is_trading_day else create_session_times(current_session)
            next_times = create_session_times(next_session)
            
            return (prev_times, curr_times, next_times), is_trading_day
            
        except Exception as e:
            logger.error(f"Error in get_trading_hours: {str(e)}", exc_info=True)
            return None, False



    # Trading Hours
    def extract_times(self, trading_hours_tuple):

        previous_day, current_day, next_day = trading_hours_tuple  # Direct unpacking
        
        # Handle market closed days
        if current_day == 'market_closed':
            current_day = (None, None, None, None)
        
        times = {
            'pre_market_current_day': current_day[0],
            'market_open_current_day': current_day[1],
            'market_close_current_day': current_day[2],
            'post_market_current_day': current_day[3],

            'pre_market_previous_day': previous_day[0],
            'market_open_previous_day': previous_day[1],
            'market_close_previous_day': previous_day[2],
            'post_market_previous_day': previous_day[3],
            
            'pre_market_next_day': next_day[0],
            'market_open_next_day': next_day[1],
            'market_close_next_day': next_day[2],
            'post_market_next_day': next_day[3]
        }
        
        return times


    # Helper Functions
    def get_session_data_structure(self, timestamp_str):
        trading_hours, is_trading_day = self.get_trading_hours(timestamp_str)
        times = self.extract_times(trading_hours)
        market_session = self.get_market_session(timestamp_str)
        return market_session, is_trading_day, times




    # Session Returns - Start Time
    def get_start_time(self, timestamp):
        
        market_session, is_trading_day, times = self.get_session_data_structure(timestamp)

        timestamp = self._convert_to_eastern_timestamp(timestamp)
        after_4_pm = timestamp.hour >= 16
        
        if market_session == 'market_closed':
            if is_trading_day and after_4_pm:
                return times['post_market_current_day'] # change to 'market_close_current_day
            else:
                return times['post_market_previous_day'] # change to 'market_close_previous_day'
        return timestamp  # Actual release time for all the rest    

    # def get_start_time(self, timestamp, market_session, is_trading_day, times):
        
        # market_session, is_trading_day, times = self.get_session_data_structure(timestamp)
    #     timestamp = self._convert_to_eastern_timestamp(timestamp)
    #     after_4_pm = timestamp.hour >= 16
        
    #     if market_session == 'market_closed':
    #         if is_trading_day and after_4_pm:
    #             return times['market_close_current_day'] # In QC this was 'post_market_current_day'
    #         else:
    #             return times['market_close_previous_day'] # In QC this was 'post_market_previous_day'
    #     return timestamp  # Actual release time for all the rest

    
    # Session Returns - End Time
    def get_end_time(self, timestamp):
        
        market_session, is_trading_day, times = self.get_session_data_structure(timestamp)
        timestamp = self._convert_to_eastern_timestamp(timestamp)        
        after_4_pm = timestamp.hour >= 16
        
        if market_session == 'market_closed':
            if is_trading_day and not after_4_pm:  # market_closed is before pre_market open
                return times['market_open_current_day'] + pd.Timedelta(minutes=self.add_minutes_to_open)
            else:
                return times['market_open_next_day'] + pd.Timedelta(minutes=self.add_minutes_to_open)
                
        elif market_session == 'in_market':
            return times['market_close_current_day']
            
        elif market_session == 'pre_market':
            return times['market_open_current_day'] + pd.Timedelta(minutes=self.add_minutes_to_open)
            
        else:  # This is post_market - we could also mesure pre-market activity for events that happened during post-market previous day
            return times['market_open_next_day'] + pd.Timedelta(minutes=self.add_minutes_to_open)    
            

    # Inorder to ensure that the returns are calculated correctly, we need to understand if the horizon extends beyond stated market session
    # For example, horizon return for pre_market may include end prices from next session - see QC Code
    def get_interval_start_time(self, timestamp):
        """
        The horizon may extend beyond stated market session so for example 
        horizon return for pre_market may include end prices from next session
        """
        market_session, is_trading_day, times = self.get_session_data_structure(timestamp)
        timestamp = self._convert_to_eastern_timestamp(timestamp)        
        after_4_pm = timestamp.hour >= 16
        
        if market_session == 'market_closed':
            if is_trading_day and not after_4_pm:  # Essentially means this market_closed is before pre_market open
                return times['pre_market_current_day']
            else:
                return times['pre_market_next_day']
        return timestamp  # Actual Release Time for all rest
    
    
    # Respects Session Boundaries - Only works for forward time. so do not use -timedelta in interval_minutes
    def get_interval_end_time(self, timestamp, interval_minutes=60, respect_session_boundary=False):
        if isinstance(timestamp, str):
            timestamp = pd.to_datetime(timestamp)
        market_session, is_trading_day, times = self.get_session_data_structure(timestamp)
        interval_start = self.get_interval_start_time(timestamp)
        proposed_end = interval_start + pd.Timedelta(minutes=interval_minutes)
        after_4_pm = timestamp.hour >= 16

        if not respect_session_boundary:
            return proposed_end

        if market_session == 'market_closed':
            if is_trading_day and not after_4_pm:  # Before Pre (0:00-4:00)
                # Starting from 4:00 AM current day
                # Should end at min(5:00 AM, market_open)
                return min(proposed_end, times['market_open_current_day'])
            else:  # After Post or Weekend
                # Starting from 4:00 AM next day
                # Should end at min(5:00 AM next day, market_open_next_day)
                return min(proposed_end, times['market_open_next_day'])
                
        # For active sessions:
        return min(proposed_end, 
                times['market_open_current_day'] if market_session == 'pre_market'
                else times['market_close_current_day'] if market_session == 'in_market'
                else times['post_market_current_day'])



    # 1D Impact Returns - previous day's close to current day's close
    def get_1d_impact_times(self, timestamp):
        
        """ The 1D impact function compares two trading day closing prices based on when the event occurs: 
            if before 4 PM, it uses previous to current day's close; 
            if after 4 PM or on non-trading days, it uses current to next day's close.  """
        
        market_session, is_trading_day, times = self.get_session_data_structure(timestamp)

        timestamp = self._convert_to_eastern_timestamp(timestamp)
        after_4_pm = timestamp.hour >= 16
        
        # Handle non-trading days first
        if not is_trading_day:
            return (times['market_close_previous_day'], times['market_close_next_day'])
        
        # For trading days, maintain existing logic
        if market_session in ['pre_market', 'in_market']:
            return (times['market_close_previous_day'], times['market_close_current_day'])
        elif market_session == 'post_market':
            return (times['market_close_current_day'], times['market_close_next_day'])
        elif market_session == 'market_closed':
            if not after_4_pm:
                return (times['market_close_previous_day'], times['market_close_current_day'])
            else:
                return (times['market_close_current_day'], times['market_close_next_day'])
                
        raise ValueError(f"Invalid market session: {market_session}")
    



# TO REMOVE

    # # Example usage in your workflow:
    # def process_event(self, event_date):
    #     """Process a single event date"""
    #     trading_hours = self.get_trading_hours(event_date)
    #     times = self.extract_times(trading_hours)
    #     return times

    # def process_multiple_events(self, event_dates):
    #     """Process multiple event dates efficiently"""
    #     return {date: self.process_event(date) for date in event_dates}
