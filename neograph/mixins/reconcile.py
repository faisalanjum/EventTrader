import logging
import json
from datetime import datetime, timedelta # For date calculations
import time
from redisDB.redis_constants import RedisKeys
from ..Neo4jInitializer import Neo4jInitializer


logger = logging.getLogger(__name__)

class ReconcileMixin:
    """
    Handles reconciliation tasks, checking for missing items or date nodes.
    """


    def reconcile_missing_items(self, max_items_per_type=1000):
        """
        Identify and process items in Redis that are missing from Neo4j.
        Also checks for date node creation once after midnight.
        
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
                    for key in self.event_trader_redis.history_client.client.scan_iter(pattern):
                        news_id = key.split(':')[-1].split('.')[0]  # Extract base ID
                        redis_news_ids.add(f"bzNews_{news_id}")
                    
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
                        
                        # Process missing items
                        for news_id in list(missing_ids)[:max_items_per_type]:
                            original_id = news_id[7:]  # Remove "bzNews_" prefix
                            
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
                for namespace in ['withreturns', 'withoutreturns']:
                    pattern = RedisKeys.get_key(source_type=RedisKeys.SOURCE_REPORTS, 
                                            key_type=namespace, identifier="*")
                    
                    # Get report IDs from Redis
                    redis_report_ids = set()
                    for key in self.event_trader_redis.history_client.client.scan_iter(pattern):
                        report_id = key.split(':')[-1]
                        redis_report_ids.add(report_id)
                    
                    if not redis_report_ids:
                        continue
                        
                    # Process in batches of 1000
                    for batch in [list(redis_report_ids)[i:i+1000] for i in range(0, len(redis_report_ids), 1000)]:
                        # Query Neo4j for these report IDs
                        cypher = "MATCH (r:Report) WHERE r.accessionNo IN $ids RETURN r.accessionNo as id"
                        result = session.run(cypher, ids=batch)
                        neo4j_report_ids = {record["id"] for record in result}
                        
                        # Find missing report IDs
                        missing_ids = set(batch) - neo4j_report_ids
                        
                        # Process missing items
                        for report_id in list(missing_ids)[:max_items_per_type]:
                            # Try both namespaces
                            for ns in ['withreturns', 'withoutreturns']:
                                key = RedisKeys.get_key(source_type=RedisKeys.SOURCE_REPORTS,
                                                    key_type=ns, identifier=report_id)
                                raw_data = self.event_trader_redis.history_client.get(key)
                                if raw_data:
                                    report_data = json.loads(raw_data)
                                    success = self._process_deduplicated_report(report_id, report_data)
                                    results["reports"] += 1

                                    # Delete key if it's from withreturns namespace
                                    if success and ns == 'withreturns':
                                        try:
                                            self.event_trader_redis.history_client.client.delete(key)
                                            logger.debug(f"Deleted reconciled withreturns key: {key}")
                                        except Exception as e:
                                            logger.warning(f"Error deleting key {key}: {e}")


                                    break
            
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
                            
                            # Process missing items
                            for transcript_id in list(missing_ids)[:max_items_per_type]:
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

                                        # Delete key if it's from withreturns namespace
                                        if success and ns == 'withreturns':
                                            try:
                                                self.event_trader_redis.history_client.client.delete(key)
                                                logger.debug(f"Deleted reconciled withreturns key: {key}")
                                            except Exception as e:
                                                logger.warning(f"Failed to delete key {key}: {e}")

                                        break
                except Exception as e:
                    logger.error(f"Error during transcript reconciliation: {e}")
            
            logger.info(f"Reconciliation completed: {results}")
            return results
        
        except Exception as e:
            logger.error(f"Error reconciling missing items: {e}")
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
        
        return results


    def reconcile_date_nodes(self):
        """Check for yesterday's date node and create it with price relationships if needed"""
        try:
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            day_before = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
            
            # Check both nodes and price relationships in a single query
            query = """
            MATCH (yesterday:Date {date: $yesterday}) 
            OPTIONAL MATCH (yesterday)-[r:HAS_PRICE]->()
            OPTIONAL MATCH (previous:Date {date: $day_before})
            WITH yesterday, [x IN collect(r) WHERE x IS NOT NULL] AS rels, previous
            RETURN 
                1 as yesterday_exists,
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
            
            # Create initializer and connect

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
            
            return 0
        except Exception as e:
            logger.error(f"Error reconciling date nodes: {e}")
            return 0



    def reconcile_dividend_nodes(self):
        """Check for yesterday's dividend nodes and create them if needed"""
        try:
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Check if dividends already exist in a single query
            query = """
            MATCH (yesterday:Date {date: $yesterday})
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
            logger.error(f"Error reconciling dividend nodes: {e}")
            return 0