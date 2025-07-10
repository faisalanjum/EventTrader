"""
Edge Writer Service - Single writer pattern to eliminate Neo4j lock contention
for high-volume relationship types (HAS_CONCEPT, HAS_UNIT, HAS_PERIOD, REPORTS, FACT_MEMBER)
"""
import json
import logging
import os
import time
from typing import List, Dict
from neograph.Neo4jConnection import get_manager
from config.feature_flags import ENABLE_EDGE_WRITER

logger = logging.getLogger(__name__)

def process_edge_batch(neo4j_manager, batch: List[Dict]) -> int:
    """Process a batch of edges in a single transaction"""
    if not batch:
        return 0
    
    # Group by relationship type for efficient processing
    from collections import defaultdict
    grouped = defaultdict(list)
    
    for item in batch:
        grouped[item["rel_type"]].append({
            "source_id": item["source_id"],
            "target_id": item["target_id"],
            "properties": item.get("properties", {})
        })
    
    # Single transaction per batch for all relationship types
    with neo4j_manager.driver.session() as session:
        def create_relationships_tx(tx):
            created = 0
            for rel_type, params in grouped.items():
                # Use the same merge query with key property for shared node relationships
                if rel_type in ["HAS_CONCEPT", "HAS_UNIT", "HAS_PERIOD"]:
                    result = tx.run(f"""
                        UNWIND $params AS param
                        MATCH (s {{id: param.source_id}})
                        MATCH (t {{id: param.target_id}})
                        MERGE (s)-[r:{rel_type} {{key: param.source_id}}]->(t)
                        SET r += param.properties
                        RETURN count(r) as created
                    """, {"params": params})
                else:
                    # For REPORTS and FACT_MEMBER, use standard merge
                    result = tx.run(f"""
                        UNWIND $params AS param
                        MATCH (s {{id: param.source_id}})
                        MATCH (t {{id: param.target_id}})
                        MERGE (s)-[r:{rel_type}]->(t)
                        SET r += param.properties
                        RETURN count(r) as created
                    """, {"params": params})
                
                record = result.single()
                if record:
                    created += record["created"]
            return created
        
        total_created = session.execute_write(create_relationships_tx)
    
    return total_created

def main():
    """Main edge writer loop"""
    logger.info("Edge Writer started")
    
    # Check feature flag
    if not ENABLE_EDGE_WRITER:
        logger.warning("Edge writer is disabled by feature flag (ENABLE_EDGE_WRITER=False)")
        return
    
    # Check environment variable
    edge_queue = os.getenv("EDGE_QUEUE")
    if not edge_queue:
        logger.error("EDGE_QUEUE environment variable not set, exiting")
        return
    
    logger.info(f"Using queue: {edge_queue}")
    
    # Import Redis client only when actually needed
    from redisDB.redisClasses import RedisClient
    redis_client = RedisClient(prefix="")
    batch_size = 200  # Reduced from 1000 for faster commits
    log_interval = 10  # Log queue depth every 10 iterations
    iteration = 0
    
    neo4j_manager = get_manager()
    
    while True:
        try:
            iteration += 1
            
            # Log queue depth periodically
            if iteration % log_interval == 0:
                queue_len = redis_client.client.llen(edge_queue)
                logger.info(f"Queue depth: {queue_len}")
            
            # Get batch from queue
            batch = []
            pipeline = redis_client.client.pipeline()
            
            # Use pipeline for efficient batch retrieval
            for _ in range(batch_size):
                pipeline.lpop(edge_queue)
            
            results = pipeline.execute()
            
            for item in results:
                if item:
                    try:
                        batch.append(json.loads(item))
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in queue: {item}")
            
            if batch:
                start_time = time.time()
                created = process_edge_batch(neo4j_manager, batch)
                duration = time.time() - start_time
                
                logger.info(f"Processed {len(batch)} relationships, "
                          f"created {created} in {duration:.2f}s "
                          f"({len(batch)/duration:.0f} rel/s)")
            else:
                # No items, sleep briefly
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error in edge writer: {e}", exc_info=True)
            time.sleep(1)  # Brief pause on error

if __name__ == "__main__":
    from utils.log_config import setup_logging
    setup_logging(name="edge_writer")
    main()