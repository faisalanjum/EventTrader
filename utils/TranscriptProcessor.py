# utils/TranscriptProcessor.py
from datetime import datetime, timedelta
import time
import pytz
from utils.BaseProcessor import BaseProcessor
import threading
from transcripts.EarningsCallTranscripts import EarningsCallProcessor
from eventtrader.keys import EARNINGS_CALL_API_KEY
from utils.redis_constants import RedisKeys
from utils.feature_flags import MAX_TRANSCRIPT_SLEEP_SECONDS


class TranscriptProcessor(BaseProcessor):
    """Transcript-specific processor implementation"""
    
    def __init__(self, event_trader_redis, delete_raw=True, polygon_subscription_delay=None, ttl=None):
        super().__init__(event_trader_redis, delete_raw, polygon_subscription_delay)
        self.event_trader_redis = event_trader_redis
        self.ttl = ttl or 2 * 24 * 3600  # default to 2 days if not provided
        # Initialize transcript-specific attributes
        self.schedule_key = "admin:transcripts:schedule"
        self.notification_channel = "admin:transcripts:notifications"
        self.processed_set = "admin:transcripts:processed"
        self.ny_tz = pytz.timezone('America/New_York')
        self.last_date = None
        
        # Scheduling thread control
        self.scheduling_thread = None
        self.scheduling_thread_running = False
    
    def process_all_transcripts(self):
        """Process all transcripts in queue using BaseProcessor's logic"""
        self.logger.info("Starting transcript processor")
        
        # Start scheduling thread
        self.scheduling_thread_running = True
        
        # Daemon thread exits when main thread exits
        self.scheduling_thread = threading.Thread(target=self._run_transcript_scheduling, daemon=True)
        self.scheduling_thread.start()
        self.logger.info("Started transcript scheduling thread")
        
        # Call BaseProcessor's queue processing (runs in main thread)
        result = self.process_all_items()
        
        # When process_all_items returns, stop scheduling thread
        self.scheduling_thread_running = False
        if self.scheduling_thread and self.scheduling_thread.is_alive():
            self.scheduling_thread.join(timeout=5)
        
        return result

    def _run_transcript_scheduling(self):
        """Run transcript scheduling in a separate thread"""
        self.logger.info("Transcript scheduling thread started")
        
        # Set up pubsub for notifications
        pubsub = self.live_client.create_pubsub_connection()
        pubsub.subscribe(self.notification_channel)
        self.logger.info(f"Subscribed to notifications on channel: {self.notification_channel}")
        
        try:
            while self.scheduling_thread_running and self.should_run:
                try:
                    # Check schedule and date transitions
                    now = datetime.now(self.ny_tz)
                    now_ts = int(time.time())
                    
                    # Date transition check (once per day)
                    today = now.date()
                    if self.last_date != today:
                        self.last_date = today
                        self.logger.info(f"Date transition detected: {today}")
                    
                    # Process any due transcripts
                    self._process_due_transcripts(now_ts)
                    
                    # Sleep until next scheduled item or notification
                    self._sleep_until_next_transcript(pubsub, now_ts)
                    
                except Exception as e:
                    self.logger.error(f"Error in transcript scheduling: {e}")
                    time.sleep(1)
        finally:
            # Clean up
            try:
                pubsub.unsubscribe()
                pubsub.close()
            except:
                pass
            self.logger.info("Transcript scheduling thread stopped")

    def _process_due_transcripts(self, now_ts):
        """Process transcripts that are scheduled to be processed now"""
        try:
            # Get due items with timestamp ≤ now_ts (up to 5 at once)
            due_items = self.live_client.client.zrangebyscore(self.schedule_key, 0, now_ts, start=0, num=5)
            
            if due_items:
                self.logger.info(f"Processing {len(due_items)} due transcripts")
                
            for event_key in due_items:
                # Skip if already processed
                if self.live_client.client.sismember(self.processed_set, event_key):
                    self.live_client.client.zrem(self.schedule_key, event_key)
                    self.logger.info(f"Transcript {event_key} already processed, removing from schedule")
                    continue
                
                self._fetch_and_process_transcript(event_key, now_ts)
        
        except Exception as e:
            self.logger.error(f"Error processing due transcripts: {e}")


    # Checks if transcript exists either in raw storage (fetched but not processed)
    # or in the processed queue (already processed and published)
    def _transcript_exists(self, symbol, conference_datetime):
        """Check if transcript exists in raw or processed Redis structures"""
        # Standardize format (safe fallback)
        if " " in conference_datetime and "T" not in conference_datetime:
            conference_datetime = conference_datetime.replace(" ", "T")

        key_id = f"{symbol}_{conference_datetime.replace(':', '.')}"

        try:
            # Raw namespace (live only)
            raw_ns = RedisKeys.get_key(
                source_type=RedisKeys.SOURCE_TRANSCRIPTS,
                key_type=RedisKeys.SUFFIX_RAW,
                prefix_type=RedisKeys.PREFIX_LIVE
            )
            raw_keys = self.live_client.client.keys(f"{raw_ns}*{key_id}*")

            # Processed queues (both live and hist)
            live_processed = self.live_client.client.lrange(self.live_client.PROCESSED_QUEUE, 0, -1)
            hist_processed = self.event_trader_redis.history_client.client.lrange(
                self.event_trader_redis.history_client.PROCESSED_QUEUE, 0, -1
            )

            found_in_processed = any(k.endswith(key_id) for k in live_processed) or \
                                any(k.endswith(key_id) for k in hist_processed)

            return len(raw_keys) > 0 or found_in_processed
        except Exception as e:
            self.logger.error(f"Error checking transcript existence: {e}")
            return False # Safer to say it doesn't exist if we can't verify


    # def _transcript_exists(self, symbol, conference_datetime):
    #     """Check if transcript exists in raw or processed Redis structures"""
    #     key_id = f"{symbol}_{conference_datetime.replace(':', '.')}"

    #     raw_ns = RedisKeys.get_key(
    #         source_type=RedisKeys.SOURCE_TRANSCRIPTS, 
    #         key_type=RedisKeys.SUFFIX_RAW,
    #         prefix_type=RedisKeys.PREFIX_LIVE
    #     )

    #     raw_keys = self.live_client.client.keys(f"{raw_ns}*{key_id}*")

    #     processed_queue = self.live_client.PROCESSED_QUEUE
    #     processed_items = self.live_client.client.lrange(processed_queue, 0, -1)
    #     matching_processed = [k for k in processed_items if k.endswith(key_id)]

    #     return len(raw_keys) > 0 or len(matching_processed) > 0



    def _fetch_and_process_transcript(self, event_key, now_ts):
        """Fetch and process a single transcript"""
        try:
            # Parse event key
            parts = event_key.split('_', 1)
            if len(parts) != 2:
                self.logger.error(f"Invalid event key format: {event_key}")
                self.live_client.client.zrem(self.schedule_key, event_key)
                return
            
            symbol, conference_datetime = parts
            self.logger.info(f"Fetching transcript for {symbol} at {conference_datetime}")
            
            # Get our universe of companies
            universe_symbols = set(s.upper() for s in self.event_trader_redis.get_symbols())
            if symbol.upper() not in universe_symbols:
                self.logger.info(f"Symbol {symbol} not in universe, removing from schedule")
                self.live_client.client.zrem(self.schedule_key, event_key)
                return
            
            # Initialize API client
            
            earnings_call_client = EarningsCallProcessor(
                api_key=EARNINGS_CALL_API_KEY,
                redis_client=self.event_trader_redis,
                ttl=self.ttl
            )
            
            # Fetch transcript using today's date
            # today = datetime.now(self.ny_tz).date()
            # transcripts = earnings_call_client.get_transcripts_for_single_date(today)

            from dateutil import parser as dateutil_parser

            try:
                conf_date = dateutil_parser.parse(conference_datetime.replace('.', ':')).date()
                transcripts = earnings_call_client.get_transcripts_for_single_date(conf_date)
                if not transcripts:
                    transcripts = earnings_call_client.get_transcripts_for_single_date(datetime.now(self.ny_tz).date())
            except Exception:
                transcripts = earnings_call_client.get_transcripts_for_single_date(datetime.now(self.ny_tz).date())

            # Store each transcript in historical Redis immediately
            if transcripts:
                for transcript in transcripts:
                    earnings_call_client.store_transcript_in_redis(transcript, is_live=True)

            transcript_found = self._transcript_exists(symbol, conference_datetime)

            if transcript_found:
                self._handle_transcript_found(event_key, symbol, conference_datetime)
            else:
                self._schedule_transcript_retry(event_key, symbol, conference_datetime, now_ts)
                
        except Exception as e:
            self.logger.error(f"Error fetching transcript {event_key}: {e}")
            # Reschedule with 30-min delay on error
            reschedule_time = now_ts + 1800  # 30 minutes later
            self.live_client.client.zadd(self.schedule_key, {event_key: reschedule_time})


    def _handle_transcript_found(self, event_key, symbol, conference_datetime):
        """Handle when transcript is successfully found and processed"""
        self.logger.info(f"Successfully fetched transcript for {symbol} at {conference_datetime}")
        
        # Remove from schedule
        self.live_client.client.zrem(self.schedule_key, event_key)
        
        # Mark as processed
        self.live_client.client.sadd(self.processed_set, event_key)
        self.live_client.client.expire(self.processed_set, self.ttl)  # 2 days default TTL
        
        # Publish notification
        self.live_client.client.publish(self.notification_channel, f"processed:{event_key}")


    def _schedule_transcript_retry(self, event_key, symbol, conference_datetime, now_ts):
        """Schedule transcript for retry when not found"""
        self.logger.info(f"Transcript not ready for {symbol} at {conference_datetime}, will retry in 5 minutes")
        
        # Use first retry with 5 minutes
        reschedule_time = now_ts + 300  # 5 minutes later
        
        # Add to schedule
        self.live_client.client.zadd(self.schedule_key, {event_key: reschedule_time})
        
        # Publish notification
        self.live_client.client.publish(self.notification_channel, f"rescheduled:{event_key}")

    def _sleep_until_next_transcript(self, pubsub, now_ts, default_sleep=1):
        """Sleep until next transcript with exact timing (same pattern as ReturnsProcessor)"""
        try:
            # Get next scheduled transcript
            next_item = self.live_client.client.zrange(self.schedule_key, 0, 0, withscores=True)
            
            if next_item:
                # Get exact timestamp when the next transcript is due
                event_key, next_timestamp = next_item[0]
                sleep_time = max(0, min(MAX_TRANSCRIPT_SLEEP_SECONDS, next_timestamp - now_ts))
                
                # Debug log for timestamp conversion
                scheduled_time = datetime.fromtimestamp(next_timestamp, self.ny_tz)
                self.logger.info(f"Next scheduled transcript: {event_key} at {scheduled_time.strftime('%Y-%m-%d %H:%M:%S %Z')} (Unix: {next_timestamp})")
            else:
                sleep_time = default_sleep  # Default short sleep
                self.logger.debug("No scheduled transcripts found")
            
            # Wait for notification or timeout
            message = pubsub.get_message(timeout=sleep_time)
            if message and message.get('type') == 'message':
                self.logger.debug("Woke up due to new notification")
            
            return
            
        except Exception as e:
            self.logger.error(f"Error in sleep operation: {e}")
            time.sleep(1)  # Short error recovery sleep

    def _standardize_fields(self, content: dict) -> dict:
        """Transform transcript fields to standard format"""
        try:
            # Add debug log to see raw content structure
            self.logger.info(f"Raw transcript content keys: {list(content.keys())}")
            self.logger.info(f"Raw transcript content sample: {str(content)[:500]}...")
            
            standardized = content.copy()
            
            # Check for required fields
            required_fields = ['symbol', 'fiscal_year', 'fiscal_quarter', 'conference_datetime']
            missing_fields = [f for f in required_fields if f not in content]
            if missing_fields:
                self.logger.error(f"Missing required fields in transcript: {missing_fields}")
                return {}
            
            # Ensure required fields are present for BaseProcessor
            standardized.update({
                'id': f"{content['symbol']}_{content['fiscal_year']}_{content['fiscal_quarter']}",
                'created': self._ensure_iso_format(content['conference_datetime']),
                'updated': self._ensure_iso_format(content['conference_datetime']),
                'symbols': [content['symbol']],
                'formType': f"TRANSCRIPT_Q{content['fiscal_quarter']}"
            })
            
            return standardized
        except Exception as e:
            self.logger.error(f"Error standardizing transcript: {e}")
            return {}
    
    def _clean_content(self, content: dict) -> dict:
        """Clean transcript content"""
        try:
            cleaned = content.copy()
            
            # Convert timestamps to Eastern
            for field in ['created', 'updated']:
                if field in cleaned:
                    cleaned[field] = self.convert_to_eastern(cleaned[field])
            
            return cleaned
        except Exception as e:
            self.logger.error(f"Error cleaning transcript: {e}")
            return content
    
    def _ensure_iso_format(self, dt) -> str:
        """Ensure datetime is in ISO format"""
        if isinstance(dt, str):
            return dt
        if hasattr(dt, 'isoformat'):
            return dt.isoformat()
        return str(dt)
    