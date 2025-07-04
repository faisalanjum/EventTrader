import logging
import json
from datetime import datetime, timedelta # For date calculations
import time
from redisDB.redis_constants import RedisKeys
from ..Neo4jInitializer import Neo4jInitializer
from utils.id_utils import canonicalise_news_full_id


logger = logging.getLogger(__name__)

class ReconcileMixin:
    """
    Handles reconciliation tasks, checking for missing items or date nodes.
    """

     # Should be optimized to handle large number of items
    def reconcile_missing_items(self, max_items_per_type=5000):
        """
        Identify and process items in Redis that are missing from Neo4j.
        Also checks for date node creation once after midnight.
        
        Args:
            max_items_per_type: Maximum items to process per type, or None for unlimited
        
        Returns:
            dict: results keyed by item type with counts
        """
        results = {"news": 0, "reports": 0, "transcripts": 0, "dates": 0}

        
        try:
            # Extract midnight operations to separate method
            self._handle_midnight_operations(results)
            
            with self.manager.driver.session() as session:
                # 1. NEWS RECONCILIATION
                for namespace in ['withreturns', 'withoutreturns']:
                    pattern = RedisKeys.get_key(source_type=self.event_trader_redis.source, 
                                            key_type=namespace, identifier="*")
                    
                    # Get news IDs from Redis
                    redis_news_ids = set()
                    canon_to_raw = {}                                          # Store mapping from canonical to raw IDs
                    canon_to_full_meta = {}                                    # NEW: Store mapping to canonical full ID for meta keys
                    for key in self.event_trader_redis.history_client.client.scan_iter(pattern):
                        raw_full_id = key.split(':')[-1]                        # '30661575.2023-02-01T04.29.49-05.00'
                        canon_full_id = canonicalise_news_full_id(raw_full_id)  # '30661575.2023-02-01T09.29.49+00.00'
                        base_id = canon_full_id.split('.')[0]                   # '30661575' (digits only)
                        news_id = f"bzNews_{base_id}"                           # Neo4j format (NO timestamp)
                        redis_news_ids.add(news_id)
                        canon_to_raw[news_id] = raw_full_id                     # Map to raw ID for Redis lookup
                        canon_to_full_meta[news_id] = canon_full_id             # Map to canonical full ID for meta keys
                    
                    if not redis_news_ids:
                        continue
                        
                    # Process in batches of 1000
                    for batch in [list(redis_news_ids)[i:i+1000] for i in range(0, len(redis_news_ids), 1000)]:
                        # Query Neo4j for these news IDs
                        cypher = "MATCH (n:News) WHERE n.id IN $ids RETURN n.id as id"
                        result = session.run(cypher, ids=batch)
                        neo4j_news_ids = {record["id"] for record in result}
                        
                        # Find missing news IDs
                        missing_ids = set(batch) - neo4j_news_ids
                        
                        # Process missing items - MODIFIED to support unlimited items
                        item_limit = None if max_items_per_type is None else max_items_per_type
                        for news_id in list(missing_ids)[:item_limit]:
                            # --- BEGIN GUARD for RECONCILE NEWS ---
                            # Use canonical full-ID (no bzNews_) for meta look-up
                            meta_key_for_news_guard = f"tracking:meta:{RedisKeys.SOURCE_NEWS}:{canon_to_full_meta[news_id]}"
                            if self.event_trader_redis.history_client.client.hexists(meta_key_for_news_guard, "inserted_into_neo4j_at"):
                                logger.info(f"[RECONCILE SKIP] News {news_id} already has 'inserted_into_neo4j_at'. Skipping reconciliation processing.")
                                raw_full_id = canon_to_raw[news_id]            # Use the raw ID with original timezone
                                for ns_cleanup in [RedisKeys.SUFFIX_WITHRETURNS, RedisKeys.SUFFIX_WITHOUTRETURNS]:
                                    stale_key_path = RedisKeys.get_key(source_type=RedisKeys.SOURCE_NEWS, # Explicitly use SOURCE_NEWS
                                                                     key_type=ns_cleanup, 
                                                                     identifier=raw_full_id)
                                    if self.event_trader_redis.history_client.client.exists(stale_key_path):
                                        try:
                                            self.event_trader_redis.history_client.client.delete(stale_key_path)
                                            logger.info(f"[RECONCILE SKIP] Cleaned up stale key {stale_key_path} for already processed news {news_id}")
                                        except Exception as e_del_news_reconcile:
                                            logger.warning(f"[RECONCILE SKIP] Could not delete stale key {stale_key_path}: {e_del_news_reconcile}")
                                continue # Skip to the next news_id
                            # --- END GUARD for RECONCILE NEWS ---

                            raw_full_id = canon_to_raw[news_id]                  # Get original raw ID with timezone
                            original_id = raw_full_id                            # Use the raw ID for Redis key lookup
                            
                            # Try both namespaces
                            for ns in ['withreturns', 'withoutreturns']:
                                key = RedisKeys.get_key(source_type=self.event_trader_redis.source,
                                                    key_type=ns, identifier=original_id)
                                raw_data = self.event_trader_redis.history_client.get(key)
                                if raw_data:
                                    news_data = json.loads(raw_data)
                                    success = self._process_deduplicated_news(news_id, news_data)
                                    results["news"] += 1

                                    # Delete key if it's from withreturns namespace
                                    if success and ns == 'withreturns':
                                        try:
                                            self.event_trader_redis.history_client.client.delete(key)
                                            logger.debug(f"Deleted reconciled withreturns key: {key}")
                                        except Exception as e:
                                            logger.warning(f"Error deleting key {key}: {e}")


                                    break
                
                # 2. REPORTS RECONCILIATION
                # We identify two types of "missing" reports:
                # (1) accessionNo exists in Redis but not in Neo4j
                # (2) accessionNo exists in both, but Redis version is newer (based on filedAt/created timestamp)

                # Redis full_id format: <accessionNo>.<timestamp> (UTC, dots instead of colons)
                # Example: "0000010795-23-000009.2023-01-06T11.54.38+00.00"

                # STEP 1: Collect latest Redis full_id per accessionNo
                redis_report_full_ids = {}  # accessionNo → full Redis ID (latest)
                for ns in ['withreturns', 'withoutreturns']:
                    pattern = RedisKeys.get_key(RedisKeys.SOURCE_REPORTS, ns, "*")
                    for key in self.event_trader_redis.history_client.client.scan_iter(pattern):
                        full_id = key.split(':')[-1]
                        accession_no, timestamp = full_id[:20], full_id[21:]
                        if accession_no not in redis_report_full_ids or timestamp > redis_report_full_ids[accession_no][21:]:
                            redis_report_full_ids[accession_no] = full_id

                if not redis_report_full_ids:
                    return results  # Nothing to reconcile

                # STEP 2: Fetch existing accessionNos and created timestamps from Neo4j
                accession_list = list(redis_report_full_ids.keys())
                cypher = """
                MATCH (r:Report)
                WHERE r.accessionNo IN $ids
                RETURN r.accessionNo AS id, r.created AS created
                """
                result = session.run(cypher, ids=accession_list)
                neo4j_created_map = {r["id"]: r["created"] for r in result}

                # STEP 3: Compare timestamps to find missing or outdated reports
                from dateutil.parser import parse as parse_datetime

                missing_or_newer = []
                for accession_no, full_id in redis_report_full_ids.items():
                    redis_ts_str = full_id[21:].replace('.', ':')
                    try:
                        redis_dt = parse_datetime(redis_ts_str)
                    except Exception:
                        logger.warning(f"Bad timestamp {redis_ts_str} for {accession_no}")
                        continue

                    neo4j_created = neo4j_created_map.get(accession_no)
                    if not neo4j_created or redis_dt > parse_datetime(neo4j_created):
                        missing_or_newer.append((accession_no, full_id))


                # STEP 4: Fetch and process those reports using latest full_id
                for accession_no, full_id in missing_or_newer[:max_items_per_type or len(missing_or_newer)]:
                    # --- BEGIN GUARD for RECONCILE ---
                    meta_key_for_reconcile_guard = f"tracking:meta:{RedisKeys.SOURCE_REPORTS}:{full_id}"
                    if self.event_trader_redis.history_client.client.hexists(meta_key_for_reconcile_guard, "inserted_into_neo4j_at"):
                        logger.info(f"[RECONCILE SKIP] Report {full_id} already has 'inserted_into_neo4j_at'. Skipping reconciliation processing.")
                        # Optionally, ensure any raw keys for this full_id are cleaned up from withreturns/withoutreturns
                        for ns_cleanup in [RedisKeys.SUFFIX_WITHRETURNS, RedisKeys.SUFFIX_WITHOUTRETURNS]:
                            stale_key_path = RedisKeys.get_key(RedisKeys.SOURCE_REPORTS, ns_cleanup, full_id)
                            if self.event_trader_redis.history_client.client.exists(stale_key_path):
                                try:
                                    self.event_trader_redis.history_client.client.delete(stale_key_path)
                                    logger.info(f"[RECONCILE SKIP] Cleaned up stale key {stale_key_path} for already processed report {full_id}")
                                except Exception as e_del_reconcile:
                                    logger.warning(f"[RECONCILE SKIP] Could not delete stale key {stale_key_path}: {e_del_reconcile}")
                        continue # Skip to the next item in missing_or_newer
                    # --- END GUARD for RECONCILE ---

                    for ns in ['withreturns', 'withoutreturns']:
                        key = RedisKeys.get_key(RedisKeys.SOURCE_REPORTS, ns, full_id)
                        raw_data = self.event_trader_redis.history_client.get(key)
                        if raw_data:
                            report_data = json.loads(raw_data)
                            success = self._process_deduplicated_report(full_id, report_data)
                            results["reports"] += 1

                            # Add the missing lifecycle timestamp
                            if success:
                                meta_key = f"tracking:meta:{RedisKeys.SOURCE_REPORTS}:{full_id}"
                                try:
                                    self.event_trader_redis.history_client.mark_lifecycle_timestamp(
                                        meta_key, "inserted_into_neo4j_at"
                                    )
                                except Exception:
                                    pass

                            if success and ns == 'withreturns':
                                try:
                                    self.event_trader_redis.history_client.client.delete(key)
                                except Exception as e:
                                    logger.warning(f"Failed to delete key {key}: {e}")
                            break  # Stop after first successful namespace match

            
                # 3. TRANSCRIPTS RECONCILIATION
                try:
                    for namespace in ['withreturns', 'withoutreturns']:
                        pattern = RedisKeys.get_key(
                            source_type=RedisKeys.SOURCE_TRANSCRIPTS,
                            key_type=namespace,
                            identifier="*"
                        )
                        
                        # Get transcript IDs from Redis
                        redis_transcript_ids = set()
                        for key in self.event_trader_redis.history_client.client.scan_iter(pattern):
                            transcript_id = key.split(':')[-1]  # Get the entire ID portion
                            redis_transcript_ids.add(transcript_id)
                        
                        if not redis_transcript_ids:
                            continue
                            
                        # Process in batches of 1000
                        for batch in [list(redis_transcript_ids)[i:i+1000] for i in range(0, len(redis_transcript_ids), 1000)]:
                            # Query Neo4j for these transcript IDs
                            cypher = "MATCH (t:Transcript) WHERE t.id IN $ids RETURN t.id as id"
                            result = session.run(cypher, ids=batch)
                            neo4j_transcript_ids = {record["id"] for record in result}
                            
                            # Find missing transcript IDs
                            missing_ids = set(batch) - neo4j_transcript_ids
                            
                            # Process missing items - MODIFIED to support unlimited items
                            item_limit = None if max_items_per_type is None else max_items_per_type
                            for transcript_id in list(missing_ids)[:item_limit]:
                                # --- BEGIN GUARD for RECONCILE TRANSCRIPTS ---
                                meta_key_for_transcript_guard = f"tracking:meta:{RedisKeys.SOURCE_TRANSCRIPTS}:{transcript_id}"
                                if self.event_trader_redis.history_client.client.hexists(meta_key_for_transcript_guard, "inserted_into_neo4j_at"):
                                    logger.info(f"[RECONCILE SKIP] Transcript {transcript_id} already has 'inserted_into_neo4j_at'. Skipping reconciliation processing.")
                                    # Optionally, clean up raw keys if they exist for this transcript_id
                                    for ns_cleanup in [RedisKeys.SUFFIX_WITHRETURNS, RedisKeys.SUFFIX_WITHOUTRETURNS]:
                                        stale_key_path = RedisKeys.get_key(source_type=RedisKeys.SOURCE_TRANSCRIPTS, 
                                                                         key_type=ns_cleanup, 
                                                                         identifier=transcript_id)
                                        if self.event_trader_redis.history_client.client.exists(stale_key_path):
                                            try:
                                                self.event_trader_redis.history_client.client.delete(stale_key_path)
                                                logger.info(f"[RECONCILE SKIP] Cleaned up stale key {stale_key_path} for already processed transcript {transcript_id}")
                                            except Exception as e_del_transcript_reconcile:
                                                logger.warning(f"[RECONCILE SKIP] Could not delete stale key {stale_key_path}: {e_del_transcript_reconcile}")
                                    continue # Skip to the next transcript_id
                                # --- END GUARD for RECONCILE TRANSCRIPTS ---

                                # Try both namespaces
                                for ns in ['withreturns', 'withoutreturns']:
                                    key = RedisKeys.get_key(
                                        source_type=RedisKeys.SOURCE_TRANSCRIPTS,
                                        key_type=ns,
                                        identifier=transcript_id
                                    )
                                    raw_data = self.event_trader_redis.history_client.get(key)
                                    if raw_data:
                                        transcript_data = json.loads(raw_data)
                                        success = self._process_deduplicated_transcript(transcript_id, transcript_data)
                                        results["transcripts"] += 1

                                        # Add the missing lifecycle timestamp
                                        if success:
                                            meta_key = f"tracking:meta:{RedisKeys.SOURCE_TRANSCRIPTS}:{transcript_id}"
                                            try:
                                                self.event_trader_redis.history_client.mark_lifecycle_timestamp(
                                                    meta_key, "inserted_into_neo4j_at"
                                                )
                                            except Exception:
                                                pass

                                        # Delete key if it's from withreturns namespace
                                        if success and ns == 'withreturns':
                                            try:
                                                self.event_trader_redis.history_client.client.delete(key)
                                                logger.debug(f"Deleted reconciled withreturns key: {key}")
                                            except Exception as e:
                                                logger.warning(f"Failed to delete key {key}: {e}")

                                        break
                except Exception as e:
                    logger.error(f"Error during transcript reconciliation: {e}", exc_info=True)
            
            # Ensure any XBRL reports stuck for >1 hour are re-queued
            if hasattr(self, "_reconcile_interrupted_xbrl_tasks"):
                self._reconcile_interrupted_xbrl_tasks()

            logger.info(f"Reconciliation completed: {results}")
            return results
        
        except Exception as e:
            logger.error(f"Error reconciling missing items: {e}", exc_info=True)
            return results

    def _handle_midnight_operations(self, results):
        """Check for and create yesterday's date node and dividends if missing"""
        
        # First ensure date nodes are created
        date_nodes_created = self.reconcile_date_nodes()
        results["dates"] = date_nodes_created
        if date_nodes_created > 0:
            logger.info(f"Created {date_nodes_created} date node(s) during reconciliation")
        
        # Then reconcile dividend data for yesterday
        dividend_nodes_created = self.reconcile_dividend_nodes()
        results["dividends"] = dividend_nodes_created
        if dividend_nodes_created > 0:
            logger.info(f"Created {dividend_nodes_created} dividend node(s) during reconciliation")

        # Then reconcile split data for yesterday
        split_nodes_created = self.reconcile_split_nodes()
        results["splits"] = split_nodes_created
        if split_nodes_created > 0:
            logger.info(f"Created {split_nodes_created} split node(s) during reconciliation")

        return results


    def reconcile_date_nodes(self):
        """Check for yesterday's date node and create it with price relationships if needed"""
        try:
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            day_before = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
            
            # Check both nodes and price relationships in a single query
            query = """
            OPTIONAL MATCH (yesterday:Date {date: $yesterday}) 
            OPTIONAL MATCH (yesterday)-[r:HAS_PRICE]->()
            OPTIONAL MATCH (previous:Date {date: $day_before})
            WITH yesterday, [x IN collect(r) WHERE x IS NOT NULL] AS rels, previous
            RETURN 
                CASE WHEN yesterday IS NOT NULL THEN 1 ELSE 0 END as yesterday_exists,
                size(rels) as has_prices,
                CASE WHEN previous IS NOT NULL THEN 1 ELSE 0 END as previous_exists
            """
            result = self.manager.execute_cypher_query(query, 
                                                      {"yesterday": yesterday, 
                                                       "day_before": day_before})
            
            # Skip if everything is in place
            if (result and result["yesterday_exists"] > 0 and 
                result["has_prices"] > 0):
                return 0
                
            # Initialize needed components
            if not self.universe_data:
                self.universe_data = self._get_universe()
                if not self.universe_data:
                    return 0
            
            # Create initializer and connect, with simple retry
            for attempt in range(3):  # Try up to 3 times
                try:
                    initializer = Neo4jInitializer(
                        uri=self.uri, 
                        username=self.username,
                        password=self.password,
                        universe_data=self.universe_data
                    )
                    
                    if initializer.connect():
                        try:
                            initializer.prepare_universe_data()
                            
                            # Create previous date first if needed
                            if not result or result["previous_exists"] == 0:
                                initializer.create_single_date(day_before)
                            
                            # Create yesterday with price relationships
                            return 1 if initializer.create_single_date(yesterday) else 0
                        finally:
                            initializer.close()
                    
                    break  # If we got here without errors, break the retry loop
                    
                except Exception as e:
                    # Log error but continue retrying
                    logger.warning(f"Date reconciliation attempt {attempt+1} failed: {e}")
                    
                    # Force clean up before retry
                    import gc
                    gc.collect()
                    
                    # Only retry if not the last attempt
                    if attempt < 2:  # 0, 1 = first two attempts
                        time.sleep(1)  # Simple delay between attempts
                    else:
                        # On last attempt, re-raise the error
                        raise
            
            return 0
        except Exception as e:
            logger.error(f"Error reconciling date nodes: {e}", exc_info=True)
            return 0



    def reconcile_dividend_nodes(self):
        """Check for yesterday's dividend nodes and create them if needed"""
        try:
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Check if dividends already exist in a single query
            query = """
            OPTIONAL MATCH (yesterday:Date {date: $yesterday})
            OPTIONAL MATCH (yesterday)-[r:HAS_DIVIDEND]->()
            WITH yesterday, [x IN collect(r) WHERE x IS NOT NULL] AS rels
            RETURN 
                CASE WHEN yesterday IS NOT NULL THEN 1 ELSE 0 END as yesterday_exists,
                size(rels) as has_dividends
            """
            result = self.manager.execute_cypher_query(query, {"yesterday": yesterday})
            
            # Skip if we already have dividends for yesterday
            if (result and result["yesterday_exists"] > 0 and 
                result["has_dividends"] > 0):
                return 0
                
            # Initialize needed components
            if not self.universe_data:
                self.universe_data = self._get_universe()
                if not self.universe_data:
                    return 0
            
            # Create initializer and connect
            initializer = Neo4jInitializer(
                uri=self.uri, 
                username=self.username,
                password=self.password,
                universe_data=self.universe_data
            )
            
            if initializer.connect():
                try:
                    # Create yesterday's dividends
                    return initializer.create_single_dividend(yesterday)
                finally:
                    initializer.close()
            
            return 0
            
        except Exception as e:
            logger.error(f"Error reconciling dividend nodes: {e}", exc_info=True)
            return 0
        


    def reconcile_split_nodes(self):
        """Check for yesterday's split nodes and create them if needed"""
        try:
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Check if splits already exist in a single query
            query = """
            OPTIONAL MATCH (yesterday:Date {date: $yesterday})
            OPTIONAL MATCH (yesterday)-[r:HAS_SPLIT]->()
            WITH yesterday, [x IN collect(r) WHERE x IS NOT NULL] AS rels
            RETURN 
                CASE WHEN yesterday IS NOT NULL THEN 1 ELSE 0 END as yesterday_exists,
                size(rels) as has_splits
            """
            result = self.manager.execute_cypher_query(query, {"yesterday": yesterday})
            
            # Skip if we already have splits for yesterday
            if (result and result["yesterday_exists"] > 0 and 
                result["has_splits"] > 0):
                return 0
                
            # Initialize needed components
            if not self.universe_data:
                self.universe_data = self._get_universe()
                if not self.universe_data:
                    return 0
            
            # Create initializer and connect
            initializer = Neo4jInitializer(
                uri=self.uri, 
                username=self.username,
                password=self.password,
                universe_data=self.universe_data
            )
            
            if initializer.connect():
                try:
                    # Create yesterday's splits (handles only NEW announcements)
                    new_nodes_count = initializer.create_single_split(yesterday)

                    # Attempt to link existing splits whose execution_date was yesterday
                    logger.info(f"Reconciliation: Attempting to link existing splits for execution date {yesterday}...")
                    link_query = """
                    MATCH (s:Split) // Find ALL splits
                    WHERE s.execution_date < $today // Only consider past/present execution dates
                      AND NOT EXISTS { (:Date)-[:HAS_SPLIT]->(s) } // That are currently missing the Date link
                    WITH s
                    MATCH (dt:Date {date: s.execution_date}) // Find the corresponding Date node (MUST exist for linking)
                    MATCH (c:Company {ticker: s.ticker}) // Find the corresponding company
                    MERGE (dt)-[r1:HAS_SPLIT]->(s) // Create the missing Date link
                    MERGE (c)-[r2:DECLARED_SPLIT]->(s) // Ensure Company link exists (MERGE is safe)
                    RETURN count(s) as linked_count
                    """
                    # Pass today's date for the comparison
                    today = datetime.now().strftime('%Y-%m-%d')
                    result = self.manager.execute_cypher_query(link_query, {"today": today})
                    linked_count = result.get("linked_count", 0) if result else 0
                    if linked_count > 0:
                        logger.info(f"Reconciliation: Successfully created missing HAS_SPLIT links for {linked_count} existing Split nodes (execution_date < {today}).")
                    else:
                        logger.info(f"Reconciliation: No existing Split nodes found needing HAS_SPLIT links for execution_date < {today}.")

                    return new_nodes_count # Return count of NEW nodes created

                finally:
                    initializer.close()
            
            return 0
            
        except Exception as e:
            logger.error(f"Error reconciling split nodes: {e}", exc_info=True)
            return 0

    def check_withreturns_status(self):
        """
        Check if any items remain in withreturns namespace across all sources.
        
        Returns:
            dict: Count of items in withreturns namespace by source
        """
        counts = {"news": 0, "reports": 0, "transcripts": 0}
        
        try:
            # Check each source
            for source, source_type in [
                ("news", RedisKeys.SOURCE_NEWS), 
                ("reports", RedisKeys.SOURCE_REPORTS),
                ("transcripts", RedisKeys.SOURCE_TRANSCRIPTS)
            ]:
                pattern = RedisKeys.get_key(source_type=source_type, key_type="withreturns", identifier="*")
                keys = list(self.event_trader_redis.history_client.client.scan_iter(pattern))
                counts[source] = len(keys)
                
            total = sum(counts.values())
            if total > 0:
                logger.warning(f"[CHECK] Items remaining in withreturns: {counts} (total: {total})")
            else:
                logger.info(f"[CHECK] No items remaining in withreturns namespace")
                
            return counts
        except Exception as e:
            logger.error(f"[CHECK] Error checking withreturns status: {e}", exc_info=True)
            return counts