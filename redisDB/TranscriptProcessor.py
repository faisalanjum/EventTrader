# utils/TranscriptProcessor.py
from datetime import datetime, timedelta
import time
import pytz
from .BaseProcessor import BaseProcessor
import threading
from transcripts.EarningsCallTranscripts import EarningsCallProcessor
from eventtrader.keys import EARNINGS_CALL_API_KEY
from .redis_constants import RedisKeys
from config.feature_flags import MAX_TRANSCRIPT_SLEEP_SECONDS, TRANSCRIPT_RESCHEDULE_INTERVAL
from config import feature_flags


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
        self.earnings_call_client = None
        self._last_rescan_hour = None

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
        if not feature_flags.ENABLE_LIVE_DATA:
            self.logger.info("Live data is disabled, transcript scheduling thread will not run.")
            self.scheduling_thread_running = False # Ensure the flag is set correctly for cleanup
            return # Exit the thread function immediately

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
                        self.logger.info(f"Date transition detected: {today}")
                        if self._refresh_daily_schedule(today):
                            self.last_date = today
                            self._last_rescan_hour = None

                    # Intra-day rescan every 2h during 7AM-5PM ET (catches late calendar adds)
                    elif (7 <= now.hour <= 17
                          and now.hour % 2 == 1
                          and self._last_rescan_hour != now.hour):
                        self.logger.info(f"Intra-day calendar rescan at {now.strftime('%H:%M %Z')}")
                        if self._refresh_daily_schedule(today):
                            self._last_rescan_hour = now.hour
                    
                    # Process any due transcripts
                    self._process_due_transcripts(now_ts)
                    
                    # Sleep until next scheduled item or notification
                    self._sleep_until_next_transcript(pubsub, now_ts)
                    
                except Exception as e:
                    self.logger.error(f"Error in transcript scheduling: {e}", exc_info=True)
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
            self.logger.error(f"Error processing due transcripts: {e}", exc_info=True)


    # Checks if transcript exists either in raw storage (fetched but not processed)
    # or in the processed queue (already processed and published)
    def _transcript_exists(self, symbol, conference_datetime):
        """Check if transcript exists in raw or processed Redis structures"""
        # Standardize format (safe fallback)
        if " " in conference_datetime and "T" not in conference_datetime:
            conference_datetime = conference_datetime.replace(" ", "T")

        key_id = RedisKeys.get_transcript_key_id(symbol, conference_datetime)

        try:
            # Processed queues (both live and hist)
            live_processed = self.live_client.client.lrange(self.live_client.PROCESSED_QUEUE, 0, -1)
            hist_processed = self.event_trader_redis.history_client.client.lrange(
                self.event_trader_redis.history_client.PROCESSED_QUEUE, 0, -1
            )

            found_in_processed = any(k.endswith(key_id) for k in live_processed) or \
                                any(k.endswith(key_id) for k in hist_processed)

            # return len(raw_keys) > 0 or found_in_processed

            # Only check processed queue since we also need to remove from raw queue
            return found_in_processed
            
        except Exception as e:
            self.logger.error(f"Error checking transcript existence: {e}", exc_info=True)
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

            # STEP 1 — Canonical-aware processed-queue check.
            # Handles: restart catchup, timestamp-mismatch resolution, and
            # confirmation after a prior tick's fetch+store.
            canonical_processed = self._find_processed_for_symbol_date(symbol, conference_datetime)
            if len(canonical_processed) == 1:
                self._mark_transcript_schedule_satisfied(event_key, canonical_processed)
                return
            elif len(canonical_processed) > 1:
                # Ambiguity guard: one earnings call per symbol per day is expected.
                # Log and fall through to a fresh fetch to be safe.
                self.logger.warning(
                    f"Ambiguous processed match for {symbol} on {conference_datetime[:10]}: "
                    f"{canonical_processed}; falling through to fresh fetch."
                )

            # STEP 2 — Universe check.
            universe_symbols = set(s.upper() for s in self.event_trader_redis.get_symbols())
            if symbol.upper() not in universe_symbols:
                self.logger.info(f"Symbol {symbol} not in universe, removing from schedule")
                self.live_client.client.zrem(self.schedule_key, event_key)
                return

            # STEP 3 — Raw-queue check + orphan recovery.
            # If a raw key for this symbol+date exists, downstream owns processing.
            # Re-LPUSH if orphaned (exists but not in queue). Skip fetch either way.
            if self._ensure_raw_queued_for_symbol_date(symbol, conference_datetime):
                self.logger.info(
                    f"Raw key for {symbol} on {conference_datetime[:10]} already queued "
                    f"(or re-queued from orphan); awaiting downstream confirmation"
                )
                self._schedule_transcript_retry(event_key, symbol, conference_datetime, now_ts)
                return

            # STEP 3.5 — Race guard: re-check processed queue immediately before fetch.
            # Closes the tiny window where downstream completes between STEP 1 and STEP 3.
            canonical_processed = self._find_processed_for_symbol_date(symbol, conference_datetime)
            if len(canonical_processed) == 1:
                self._mark_transcript_schedule_satisfied(event_key, canonical_processed)
                return
            elif len(canonical_processed) > 1:
                self.logger.warning(
                    f"Ambiguous processed match (race guard) for {symbol} on {conference_datetime[:10]}: "
                    f"{canonical_processed}; falling through to fresh fetch."
                )

            # STEP 4 — Fetch (symbol-filtered, no date-wide fan-out, no fallback-to-today).
            # Parse conf_date BEFORE constructing EarningsCallProcessor so a malformed
            # event_key doesn't pay the client-construction cost (load_companies).
            # Parse errors and calendar-fetch errors propagate to outer except → 30-min retry.
            from dateutil import parser as dateutil_parser
            conf_date = dateutil_parser.parse(conference_datetime.replace('.', ':')).date()

            earnings_call_client = EarningsCallProcessor(
                api_key=EARNINGS_CALL_API_KEY,
                redis_client=self.event_trader_redis,
                ttl=self.ttl
            )
            transcripts = earnings_call_client.get_single_transcript(symbol, conf_date)

            # STEP 5 — Store (does not mark processed_set; downstream confirms next tick).
            if transcripts:
                for transcript in transcripts:
                    earnings_call_client.store_transcript_in_redis(transcript, is_live=True)

            # STEP 6 — Reschedule 5 min. Next tick's STEP 1 confirms via processed queue.
            # If downstream fails, raw disappears without processed entry → next tick
            # re-enters fetch path (preserves "wait for downstream confirmation" invariant).
            self._schedule_transcript_retry(event_key, symbol, conference_datetime, now_ts)

        except Exception as e:
            self.logger.error(f"Error fetching transcript {event_key}: {e}", exc_info=True)
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

        # NOT WORKING - but since ttl is 2 days, it will be removed eventually
        # Remove any lingering raw keys if they exist
        if " " in conference_datetime and "T" not in conference_datetime:
            conference_datetime = conference_datetime.replace(" ", "T")

        key_id = RedisKeys.get_transcript_key_id(symbol, conference_datetime)

        try:
            # Raw namespace (live only)
            raw_ns = RedisKeys.get_key(
                source_type=RedisKeys.SOURCE_TRANSCRIPTS,
                key_type=RedisKeys.SUFFIX_RAW,
                prefix_type=RedisKeys.PREFIX_LIVE
            )

            # Try exact match first
            raw_key = f"{raw_ns}:{key_id}"
            if self.live_client.client.exists(raw_key):
                self.live_client.client.delete(raw_key)
                self.logger.info(f"Removed raw key for {symbol} at {conference_datetime}")
            else:
                # Fall back to pattern matching if exact match not found
                raw_keys = self.live_client.client.keys(f"{raw_ns}:{key_id}*")
                if raw_keys:
                    self.live_client.client.delete(*raw_keys)
                    self.logger.info(f"Removed {len(raw_keys)} raw keys with pattern matching for {symbol} at {conference_datetime}")
        except Exception as e:
            self.logger.error(f"Error removing raw keys: {e}", exc_info=True)


        # Publish notification
        self.live_client.client.publish(self.notification_channel, f"processed:{event_key}")


    def _find_processed_for_symbol_date(self, symbol, conference_datetime):
        """Return canonical key_ids in processed queues matching symbol + date.

        Prefix-matches on symbol + YYYY-MM-DD (ignoring time-of-day). Returns []
        on no match or Redis error. Caller handles the ambiguous >1 case.
        """
        if " " in conference_datetime and "T" not in conference_datetime:
            conference_datetime = conference_datetime.replace(" ", "T")
        date_portion = conference_datetime[:10]
        match_prefix = f"{symbol.upper()}_{date_portion}T"

        try:
            live_processed = self.live_client.client.lrange(self.live_client.PROCESSED_QUEUE, 0, -1)
            hist_processed = self.event_trader_redis.history_client.client.lrange(
                self.event_trader_redis.history_client.PROCESSED_QUEUE, 0, -1
            )
            matched = set()
            for k in list(live_processed) + list(hist_processed):
                tail = k.rsplit(':', 1)[-1]
                if tail.startswith(match_prefix):
                    matched.add(tail)
            return list(matched)
        except Exception as e:
            self.logger.error(
                f"Error finding processed transcripts for {symbol} on {date_portion}: {e}",
                exc_info=True,
            )
            return []

    def _ensure_raw_queued_for_symbol_date(self, symbol, conference_datetime):
        """Return True if a raw key for this symbol+date exists (re-queue orphans).

        An orphaned raw key (exists in Redis SET but missing from RAW_QUEUE) can
        occur if downstream BRPOPs but crashes before completing processing.
        Detects orphans and re-LPUSHes them so downstream retries within 5 min.

        Returns True if any matching raw key was found (caller should skip fetch
        to avoid redundant OpenAI cost — downstream will handle the in-queue raw).
        """
        if " " in conference_datetime and "T" not in conference_datetime:
            conference_datetime = conference_datetime.replace(" ", "T")
        date_portion = conference_datetime[:10]
        symbol_upper = symbol.upper()

        raw_ns = RedisKeys.get_key(
            source_type=RedisKeys.SOURCE_TRANSCRIPTS,
            key_type=RedisKeys.SUFFIX_RAW,
            prefix_type=RedisKeys.PREFIX_LIVE,
        )
        pattern = f"{raw_ns}:{symbol_upper}_{date_portion}T*"

        try:
            matching_raw_keys = list(self.live_client.client.scan_iter(match=pattern, count=10))
            if not matching_raw_keys:
                return False

            queue_items = set(self.live_client.client.lrange(self.live_client.RAW_QUEUE, 0, -1))
            for raw_key in matching_raw_keys:
                if raw_key not in queue_items:
                    # TOCTOU defense: re-check raw still exists before LPUSH.
                    if self.live_client.client.exists(raw_key):
                        self.live_client.client.lpush(self.live_client.RAW_QUEUE, raw_key)
                        self.logger.warning(f"Re-queued orphaned raw key: {raw_key}")
            return True
        except Exception as e:
            self.logger.error(
                f"Error ensuring raw queued for {symbol} on {date_portion}: {e}",
                exc_info=True,
            )
            return False

    def _mark_transcript_schedule_satisfied(self, event_key, canonical_event_keys=None):
        """Mark scheduled event_key (and canonical variants) as satisfied.

        Unlike _handle_transcript_found, does NOT delete raw keys. Only called
        after downstream processed-queue confirmation, so raw cleanup has already
        happened on the downstream side.
        """
        canonical_event_keys = canonical_event_keys or []
        keys_to_mark = list({event_key, *canonical_event_keys})
        self.logger.info(
            f"Transcript schedule satisfied for {event_key}"
            + (f" (canonical keys: {canonical_event_keys})" if canonical_event_keys else "")
        )
        pipe = self.live_client.client.pipeline()
        pipe.zrem(self.schedule_key, *keys_to_mark)
        pipe.sadd(self.processed_set, *keys_to_mark)
        pipe.expire(self.processed_set, self.ttl)
        pipe.publish(self.notification_channel, f"processed:{event_key}")
        pipe.execute()


    def _schedule_transcript_retry(self, event_key, symbol, conference_datetime, now_ts):
        """Schedule transcript for retry when not found"""
        self.logger.info(f"Transcript not ready for {symbol} at {conference_datetime}, will retry in 5 minutes")
        
        # Use first retry with 5 minutes
        # reschedule_time = now_ts + 300  # 5 minutes later
        reschedule_time = now_ts + TRANSCRIPT_RESCHEDULE_INTERVAL  # Default 5 minutes later
        
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
            self.logger.error(f"Error in sleep operation: {e}", exc_info=True)
            time.sleep(1)  # Short error recovery sleep

    def _refresh_daily_schedule(self, today):
        """Returns True on success, False on failure."""
        if self.earnings_call_client is None:
            self.logger.error("earnings_call_client not injected")
            return False

        try:
            events = self.earnings_call_client.get_earnings_events(today)
            universe = set(s.upper() for s in self.event_trader_redis.get_symbols())
            relevant = [e for e in events if e.symbol.upper() in universe]

            if not relevant:
                self.logger.info(f"No earnings events in universe for {today}")
                return True

            scheduled = 0
            pipe = self.live_client.client.pipeline()
            for event in relevant:
                conf_date_eastern = event.conference_date
                process_time = int(conf_date_eastern.timestamp() + 1800)
                event_key = RedisKeys.get_transcript_key_id(event.symbol, conf_date_eastern)

                if self.live_client.client.sismember(self.processed_set, event_key):
                    continue

                pipe.zadd(self.schedule_key, {event_key: process_time})
                scheduled += 1
                self.logger.info(
                    f"Scheduled {event_key} - Conference: "
                    f"{conf_date_eastern.strftime('%Y-%m-%d %H:%M:%S %Z')}, "
                    f"Processing: {datetime.fromtimestamp(process_time, self.ny_tz).strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )

            pipe.execute()
            self.live_client.client.publish(self.notification_channel, "schedule_updated")
            self.logger.info(f"Scheduled {scheduled} transcripts for {today}")
            return True

        except Exception as e:
            self.logger.error(f"Error refreshing daily schedule: {e}", exc_info=True)
            return False

    def _standardize_fields(self, content: dict) -> dict:
        """Transform transcript fields to standard format"""
        try:
            # Add debug log to see raw content structure
            self.logger.debug(f"Raw transcript content keys: {list(content.keys())}")
            self.logger.debug(f"Raw transcript content sample: {str(content)[:500]}...")
            
            standardized = content.copy()
            
            # Check for required fields
            required_fields = ['symbol', 'fiscal_year', 'fiscal_quarter', 'conference_datetime']
            missing_fields = [f for f in required_fields if f not in content]
            if missing_fields:
                self.logger.error(f"Missing required fields in transcript: {missing_fields}")
                return {}
            
            # GAP-12: Validate conference_datetime is truthy before using it for ID generation
            conference_datetime = content.get('conference_datetime')
            if not conference_datetime:
                self.logger.error("conference_datetime is None/empty — cannot generate transcript ID")
                return {}

            # Ensure required fields are present for BaseProcessor
            standardized.update({
                'id': RedisKeys.get_transcript_key_id(content['symbol'], content['conference_datetime']),
                'quarter_key': f"{content['symbol']}_{content['fiscal_year']}_{content['fiscal_quarter']}",
                'created': self._ensure_iso_format(content['conference_datetime']),
                'updated': self._ensure_iso_format(content['conference_datetime']),
                'symbols': [content['symbol']],
                'formType': f"TRANSCRIPT_Q{content['fiscal_quarter']}"
            })
            
            return standardized
        except Exception as e:
            self.logger.error(f"Error standardizing transcript: {e}", exc_info=True)
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
            self.logger.error(f"Error cleaning transcript: {e}", exc_info=True)
            return content
    
    def _ensure_iso_format(self, dt) -> str:
        """Ensure datetime is in ISO format"""
        if isinstance(dt, str):
            return dt
        if hasattr(dt, 'isoformat'):
            return dt.isoformat()
        return str(dt)
    
