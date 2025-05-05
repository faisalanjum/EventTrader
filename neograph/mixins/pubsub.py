# neograph/mixins/pubsub.py

# --- Add necessary imports used by the methods below ---
import logging
import json
import threading
import time # Likely needed for sleep in the loop
from typing import Dict, List, Optional, Any
from redisDB.redis_constants import RedisKeys
from config.feature_flags import ENABLE_NEWS_EMBEDDINGS, PUBSUB_RECONCILIATION_INTERVAL

logger = logging.getLogger(__name__)

class PubSubMixin:
    """
    Handles real-time data processing via Redis Pub/Sub.
    """

    def _process_pubsub_item(self, channel, item_id, content_type='news'):
        """
        Process an item update from PubSub (works for all 3 news, reports and transcripts)
        
        Args:
            channel: The Redis channel the message came from
            item_id: The ID of the item to process
            content_type: 'news' or 'report' or 'transcript'
        """
        try:
            logger.info(f"Processing {content_type} update from {channel}: {item_id}")
            
            # Determine namespace from channel
            namespace = RedisKeys.SUFFIX_WITHRETURNS if RedisKeys.SUFFIX_WITHRETURNS in channel else RedisKeys.SUFFIX_WITHOUTRETURNS
            
            
            # Process based on content type
            if content_type == 'news':
                # Get the news data using standard key format
                key = RedisKeys.get_key(
                    source_type=self.event_trader_redis.source,
                    key_type=namespace,
                    identifier=item_id
                )
                
                # Get and process the news item
                raw_data = self.event_trader_redis.history_client.get(key)

                # If not found, try with live_client as fallback
                if not raw_data:
                    raw_data = self.event_trader_redis.live_client.get(key)
                    if raw_data:
                        logger.warning(f"[FALLBACK] Found {item_id} in live_client instead of history_client (channel: {channel})")

                if raw_data:
                    news_data = json.loads(raw_data)
                    news_id = f"bzNews_{item_id.split('.')[0]}"
                    success = self._process_deduplicated_news(
                        news_id=news_id, 
                        news_data=news_data
                    )

                    logger.info(f"Successfully processed news before generating embeddings: {item_id}")

                    # Generate embeddings if processing was successful
                    if success:
                        try:
                            self._generate_embeddings_for_pubsub_item(news_id)
                        except Exception as e:
                            logger.warning(f"Failed to generate embeddings for {item_id}: {e}")

                    # Delete key if it's from withreturns namespace
                    if success and namespace == RedisKeys.SUFFIX_WITHRETURNS:
                        try:
                            self.event_trader_redis.history_client.client.delete(key)
                            logger.info(f"Deleted processed withreturns key: {key}")
                        except Exception as e:
                            logger.warning(f"Error deleting key {key}: {e}")

                else:
                    logger.warning(f"No data found for news {item_id}")
            
            elif content_type == 'report':    
                # Get the report data using standard key format
                key = RedisKeys.get_key(
                    source_type=RedisKeys.SOURCE_REPORTS,
                    key_type=namespace,
                    identifier=item_id
                )
                
                # Get and process the report
                raw_data = self.event_trader_redis.history_client.get(key)
                # If not found, try with live_client as fallback
                if not raw_data:
                    raw_data = self.event_trader_redis.live_client.get(key)
                    if raw_data:
                        logger.warning(f"[FALLBACK] Found {item_id} in live_client instead of history_client (channel: {channel})")
                
                if raw_data:
                    report_data = json.loads(raw_data)
                    
                    # Use accessionNo as report ID if available
                    report_id = report_data.get('accessionNo', item_id)
                    
                    # Process report with deduplication (same approach as news)
                    success = self._process_deduplicated_report(
                        report_id=report_id,
                        report_data=report_data
                    )
                    
                    # Note: No need to process extracted sections here as it's already handled in _execute_report_database_operations
                    
                    logger.info(f"Successfully processed report {item_id}")

                    # Delete key if it's from withreturns namespace
                    if success and namespace == RedisKeys.SUFFIX_WITHRETURNS:
                        try:
                            self.event_trader_redis.history_client.client.delete(key)
                            logger.info(f"Deleted processed withreturns key: {key}")
                        except Exception as e:
                            logger.warning(f"Error deleting key {key}: {e}")

            elif content_type == 'transcript':
                # Get the transcript data using standard key format
                key = RedisKeys.get_key(
                    source_type=RedisKeys.SOURCE_TRANSCRIPTS,
                    key_type=namespace,
                    identifier=item_id
                )
                
                # Get and process the transcript
                raw_data = self.event_trader_redis.history_client.get(key)
                # If not found, try with live_client as fallback
                if not raw_data:
                    raw_data = self.event_trader_redis.live_client.get(key)
                    if raw_data:
                        logger.warning(f"[FALLBACK] Found {item_id} in live_client instead of history_client (channel: {channel})")
                
                if raw_data:
                    transcript_data = json.loads(raw_data)
                    
                    # Process transcript with deduplication
                    success = self._process_deduplicated_transcript(
                        transcript_id=item_id,
                        transcript_data=transcript_data
                    )
                    

                    # After successful processing, generate QAExchange embeddings
                    if success:
                        
                        logger.info(f"Successfully processed transcript {item_id}")

                        try:
                            # Get ALL QAExchange nodes for this transcript
                            query = f"""
                            MATCH (t:Transcript {{id: '{item_id}'}})-[:HAS_QA_EXCHANGE]->(q:QAExchange)
                            WHERE q.embedding IS NULL
                            RETURN q.id as id
                            """
                            # results = self.manager.execute_cypher_query(query, {})
                            
                            # # Process each QAExchange node for this transcript
                            # if results:
                            #     qa_nodes = results if isinstance(results, list) else [results]
                            #     for qa_node in qa_nodes:
                            qa_nodes = self.manager.execute_cypher_query_all(query, {})
                            for qa_node in qa_nodes:
                                    try:
                                        # Process this specific QAExchange node
                                        self._create_qaexchange_embedding(qa_node["id"])


                                    except Exception as inner_e:
                                        logger.warning(f"Failed to generate embedding for QAExchange {qa_node['id']}: {inner_e}")
                        except Exception as e:
                            logger.warning(f"Failed to generate QAExchange embeddings for transcript {item_id}: {e}")

                    # Delete key if it's from withreturns namespace
                    if success and namespace == RedisKeys.SUFFIX_WITHRETURNS:
                        try:
                            self.event_trader_redis.history_client.client.delete(key)
                            logger.info(f"Deleted processed withreturns key: {key}")
                        except Exception as e:
                            logger.warning(f"Error deleting key {key}: {e}")

                else:
                    logger.warning(f"No data found for transcript {item_id}")

        except Exception as e:
            logger.error(f"Error processing {content_type} update for {item_id}: {e}")


    def _generate_embeddings_for_pubsub_item(self, news_id):
        """Generate embedding for a news item received via PubSub"""
        
        if not ENABLE_NEWS_EMBEDDINGS:
            return False
        
        # Ensure vector index exists
        if not self._create_news_vector_index():
            logger.warning(f"Failed to create vector index for news {news_id}")
            
        # Generate embedding
        return self._create_news_embedding(news_id)




    # ToDo: is designed to run indefinitely, so it will block the main thread. You need to handle this appropriately.
    def process_with_pubsub(self):
        """
        Process news, reports, and transcripts from Redis to Neo4j using PubSub for immediate notification.
        Non-blocking and highly efficient compared to polling.
        """
        logger.info("Starting event-driven Neo4j processing")
        
        if not hasattr(self, 'event_trader_redis') or not self.event_trader_redis:
            logger.error("No Redis client available for event-driven processing")
            return
        
        # Ensure Neo4j connection is established
        if not self.manager:
            if not self.connect():
                logger.error("Failed to connect to Neo4j, cannot proceed with processing")
                return
        
        # Create a dedicated PubSub client
        pubsub = self.event_trader_redis.live_client.create_pubsub_connection()
        
        # Subscribe to news channels using consistent RedisKeys methods
        news_returns_keys = RedisKeys.get_returns_keys(self.event_trader_redis.source)
        withreturns_channel = news_returns_keys['withreturns']
        withoutreturns_channel = news_returns_keys['withoutreturns']
        pubsub.subscribe(withreturns_channel, withoutreturns_channel)
        logger.info(f"Subscribed to news channels: {withreturns_channel}, {withoutreturns_channel}")
        
        # Subscribe to report channels using the same RedisKeys methods
        report_returns_keys = RedisKeys.get_returns_keys(RedisKeys.SOURCE_REPORTS)
        report_withreturns_channel = report_returns_keys['withreturns']
        report_withoutreturns_channel = report_returns_keys['withoutreturns']
        pubsub.subscribe(report_withreturns_channel, report_withoutreturns_channel)
        logger.info(f"Subscribed to report channels: {report_withreturns_channel}, {report_withoutreturns_channel}")

        # Subscribe to transcript channels using the same RedisKeys methods
        transcript_returns_keys = RedisKeys.get_returns_keys(RedisKeys.SOURCE_TRANSCRIPTS)
        transcript_withreturns_channel = transcript_returns_keys['withreturns']
        transcript_withoutreturns_channel = transcript_returns_keys['withoutreturns']
        pubsub.subscribe(transcript_withreturns_channel, transcript_withoutreturns_channel)
        logger.info(f"Subscribed to transcript channels: {transcript_withreturns_channel}, {transcript_withoutreturns_channel}")

        # Control flag
        self.pubsub_running = True


        # [NEW CODE]: Track reconciliation time
        last_reconciliation = 0
        reconciliation_interval = PUBSUB_RECONCILIATION_INTERVAL  # Import from feature_flags

        # Process any existing items first (one-time batch processing)
        self.process_news_to_neo4j(batch_size=50, max_items=None, include_without_returns=True)
        self.process_reports_to_neo4j(batch_size=50, max_items=None, include_without_returns=True)
        self.process_transcripts_to_neo4j(batch_size=5, max_items=None, include_without_returns=True)

        # Event-driven processing loop
        while self.pubsub_running:
            try:
                # Non-blocking message check with 0.1s timeout
                message = pubsub.get_message(timeout=0.1)
                
                if message and message['type'] == 'message':
                    channel = message['channel']
                    
                    item_id = message.get('data')
                    if isinstance(item_id, bytes):
                        item_id = item_id.decode()
                    
                    if not item_id:
                        continue
                    
                    # Determine content type based on channel prefix
                    # if channel.startswith(self.event_trader_redis.source):
                    if channel.startswith(RedisKeys.SOURCE_NEWS):
                        # Process news
                        self._process_pubsub_item(channel, item_id, 'news')
                    elif channel.startswith(RedisKeys.SOURCE_REPORTS):
                        # Process report
                        self._process_pubsub_item(channel, item_id, 'report')
                    elif channel.startswith(RedisKeys.SOURCE_TRANSCRIPTS):
                        # Process transcript
                        self._process_pubsub_item(channel, item_id, 'transcript')
                
                # Periodically check for items that might have been missed (every 60 seconds)
                # This is a safety net, not the primary mechanism
                # current_time = int(time.time())
                # if current_time % 60 == 0:
                #     self.process_news_to_neo4j(batch_size=10, max_items=10, include_without_returns=False)
                #     self.process_reports_to_neo4j(batch_size=10, max_items=10, include_without_returns=False)
                #     time.sleep(1)  # Prevent repeated execution in the same second

                # Periodic reconciliation
                current_time = int(time.time())
                if current_time - last_reconciliation >= reconciliation_interval:
                    # logger.info("Starting hourly reconciliation...")
                    logger.info(f"Starting periodic reconciliation (every {reconciliation_interval} seconds)...")
                    self.reconcile_missing_items()
                    last_reconciliation = current_time


            except Exception as e:
                logger.error(f"Error in PubSub processing: {e}")
                # Try to reconnect to Neo4j if connection appears to be lost
                if not self.manager or "Neo4j" in str(e) or "Connection" in str(e):
                    logger.warning("Attempting to reconnect to Neo4j")
                    self.connect()
                time.sleep(1)
        
        # Clean up
        try:
            pubsub.unsubscribe()
            pubsub.close()
        except:
            pass
            
        logger.info("Stopped event-driven Neo4j processing")
    


    def stop_pubsub_processing(self):
        """
        Stop the PubSub processing loop gracefully.
        Called by DataManagerCentral during shutdown.
        """
        logger.info("Stopping PubSub processing...")
        self.pubsub_running = False
        # Give time for the thread to exit gracefully
        time.sleep(0.5)
        logger.info("PubSub processing flag set to stop")
        return True


