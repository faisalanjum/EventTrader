"""
Edge Writer Service - Single writer pattern to eliminate Neo4j lock contention
for high-volume relationship types (HAS_CONCEPT, HAS_UNIT, HAS_PERIOD, REPORTS, FACT_MEMBER)
"""
import json
import logging
import os
import time
from typing import List, Dict, Tuple
from neograph.Neo4jConnection import get_manager
from config.feature_flags import ENABLE_EDGE_WRITER

logger = logging.getLogger(__name__)

def get_node_labels(item: Dict) -> Tuple[str, str]:
    """Get source and target labels from queued data"""
    # Use provided types if available (new format with node type info)
    if "source_type" in item and "target_type" in item:
        source_type = item["source_type"].strip()  # Remove any whitespace
        target_type = item["target_type"].strip()  # Remove any whitespace
        
        # Validate non-empty after stripping
        if not source_type or not target_type:
            logger.warning(f"Empty node types after stripping: source='{item['source_type']}', target='{item['target_type']}', rel_type={item.get('rel_type')}")
            # Fall back to static mapping
            rel_type = item.get("rel_type", "")
            static_mapping = {
                "REPORTS": ("Fact", "XBRLNode"),
                "HAS_CONCEPT": ("Fact", "Concept"),
                "HAS_UNIT": ("Fact", "Unit"),
                "HAS_PERIOD": ("Fact", "Period"),  # Default to Fact->Period
                "FACT_MEMBER": ("Fact", "Member"),
                "FOR_COMPANY": ("Context", "Company"),
                "HAS_DIMENSION": ("Context", "Dimension"),
                "HAS_MEMBER": ("Context", "Member"),
                "CALCULATION_EDGE": ("Fact", "Fact"),  # Calculation relationships
                "IN_CONTEXT": ("Fact", "Context"),  # Fact to context relationships
            }
            return static_mapping.get(rel_type, ("", ""))
        
        # NodeType enum values are already in correct PascalCase format
        return source_type, target_type
    
    # Fallback to static mapping for backward compatibility
    rel_type = item["rel_type"]
    static_mapping = {
        "REPORTS": ("Fact", "XBRLNode"),
        "HAS_CONCEPT": ("Fact", "Concept"),
        "HAS_UNIT": ("Fact", "Unit"),
        "HAS_PERIOD": ("Fact", "Period"),  # Default to Fact->Period
        "FACT_MEMBER": ("Fact", "Member"),
        "FOR_COMPANY": ("Context", "Company"),
        "HAS_DIMENSION": ("Context", "Dimension"),
        "HAS_MEMBER": ("Context", "Member"),
        "CALCULATION_EDGE": ("Fact", "Fact"),  # Calculation relationships
        "IN_CONTEXT": ("Fact", "Context"),  # Fact to context relationships
    }
    return static_mapping.get(rel_type, ("", ""))

def process_edge_batch(neo4j_manager, batch: List[Dict]) -> int:
    """Process a batch of edges in a single transaction"""
    if not batch:
        return 0
    
    # Group by relationship type AND label combination for efficient processing
    from collections import defaultdict
    grouped = defaultdict(list)
    
    for item in batch:
        # Get labels for this item
        source_label, target_label = get_node_labels(item)
        # Create a key that includes both rel_type and labels
        group_key = (item["rel_type"], source_label, target_label)
        
        grouped[group_key].append({
            "source_id": item["source_id"],
            "target_id": item["target_id"],
            "properties": item.get("properties", {})
        })
    
    # Single transaction per batch for all relationship types
    with neo4j_manager.driver.session() as session:
        def create_relationships_tx(tx):
            created = 0
            
            for (rel_type, source_label, target_label), params in grouped.items():
                # Skip if we couldn't determine labels
                if not source_label or not target_label:
                    logger.warning(f"Skipping {len(params)} relationships of type {rel_type} - missing labels")
                    continue
                
                # Use the same merge query with key property for shared node relationships
                if rel_type in ["HAS_CONCEPT", "HAS_UNIT", "HAS_PERIOD"]:
                    query = f"""
                        UNWIND $params AS param
                        MATCH (s:{source_label} {{id: param.source_id}})
                        MATCH (t:{target_label} {{id: param.target_id}})
                        MERGE (s)-[r:{rel_type} {{key: param.source_id}}]->(t)
                        SET r += param.properties
                        RETURN count(r) as created
                    """
                elif rel_type == "PRESENTATION_EDGE":
                    # Special handling for PRESENTATION_EDGE with its 7-property constraint
                    # Must match the constraint exactly to avoid duplicates
                    query = f"""
                        UNWIND $params AS param
                        MATCH (s {{id: param.source_id}})
                        MATCH (t {{id: param.target_id}})
                        MERGE (s)-[r:PRESENTATION_EDGE {{
                            cik: param.properties.company_cik,
                            report_id: param.properties.report_id,
                            network_name: param.properties.network_name,
                            parent_id: param.source_id,
                            child_id: param.target_id,
                            parent_level: toInteger(param.properties.parent_level),
                            child_level: toInteger(param.properties.child_level)
                        }}]->(t)
                        SET r += param.properties
                        RETURN count(r) as created
                    """
                else:
                    # For other relationships, use standard merge
                    query = f"""
                        UNWIND $params AS param
                        MATCH (s:{source_label} {{id: param.source_id}})
                        MATCH (t:{target_label} {{id: param.target_id}})
                        MERGE (s)-[r:{rel_type}]->(t)
                        SET r += param.properties
                        RETURN count(r) as created
                    """
                
                result = tx.run(query, {"params": params})
                
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
    logger.info("Importing RedisClient...")
    from redisDB.redisClasses import RedisClient
    logger.info("Creating RedisClient...")
    redis_client = RedisClient(prefix="")
    batch_size = 200  # Reduced from 1000 for faster commits
    log_interval = 10  # Log queue depth every 10 iterations
    iteration = 0
    
    logger.info("Getting Neo4j manager...")
    neo4j_manager = get_manager()
    logger.info("Got Neo4j manager, entering main loop...")
    logger.info(f"About to start while loop, batch_size={batch_size}, log_interval={log_interval}")
    
    while True:
        logger.info(f"While loop iteration {iteration + 1} starting...")
        try:
            iteration += 1
            if iteration == 1:
                logger.info(f"First iteration starting...")
            
            # Log queue depth periodically
            if iteration % log_interval == 0:
                logger.info("Checking queue depth...")
                queue_len = redis_client.client.llen(edge_queue)
                logger.info(f"Queue depth: {queue_len}")
            
            # Get batch from queue
            batch = []
            if iteration == 1:
                logger.info("Creating first pipeline...")
            pipeline = redis_client.client.pipeline()
            
            # Use pipeline for efficient batch retrieval
            if iteration == 1:
                logger.info(f"Building pipeline for {batch_size} items...")
            for _ in range(batch_size):
                pipeline.lpop(edge_queue)
            
            if iteration == 1:
                logger.info("Executing first pipeline...")
            results = pipeline.execute()
            if iteration == 1:
                logger.info(f"First pipeline returned {len(results)} results")
            
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