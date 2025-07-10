"""
Edge Writer Pattern Implementation - Minimalistic Changes Required

This demonstrates the exact minimal changes needed to implement single-writer pattern
for HAS_CONCEPT, HAS_UNIT, HAS_PERIOD relationships to eliminate lock contention.
"""

# ============================================================================
# STEP 1: Add Feature Flag (config/feature_flags.py)
# ============================================================================
# Add this line:
# ENABLE_EDGE_WRITER = True  # Queue fact relationships instead of direct merge

# ============================================================================
# STEP 2: Modify XBRL Processor (XBRL/xbrl_processor.py)
# ============================================================================
# In populate_report_nodes() method, replace this section:

"""
OLD CODE (lines ~1665-1676):
        # PHASE 2 OPTIMIZATION: Group relationships by type before merging
        if fact_relationships:
            # Group by relationship type
            from collections import defaultdict
            grouped = defaultdict(list)
            for rel in fact_relationships:
                grouped[rel[2]].append(rel)
            
            # Merge each type separately to reduce lock contention
            for rel_type, rels in grouped.items():
                self.neo4j.merge_relationships(rels)
"""

# With this:
"""
NEW CODE:
        # PHASE 3 OPTIMIZATION: Queue fact relationships to edge writer
        if fact_relationships and ENABLE_EDGE_WRITER:
            # Queue to Redis for single-writer processing
            import json
            from redisDB.redisClasses import RedisClient
            
            redis_client = RedisClient(prefix="")
            edge_queue = "edge_writer:queue"
            
            for rel in fact_relationships:
                source, target, rel_type, *props = rel
                properties = props[0] if props else {}
                
                # Queue the relationship data
                redis_client.client.rpush(edge_queue, json.dumps({
                    "source_id": source.id,
                    "target_id": target.id,
                    "rel_type": rel_type.value,
                    "properties": properties
                }))
            
            logger.info(f"Queued {len(fact_relationships)} fact relationships to edge writer")
        elif fact_relationships:
            # Original code path (fallback)
            from collections import defaultdict
            grouped = defaultdict(list)
            for rel in fact_relationships:
                grouped[rel[2]].append(rel)
            
            for rel_type, rels in grouped.items():
                self.neo4j.merge_relationships(rels)
"""

# ============================================================================
# STEP 3: Create Edge Writer Service (neograph/edge_writer_loop.py)
# ============================================================================
"""
import json
import logging
import time
from typing import List, Dict
from redisDB.redisClasses import RedisClient
from neograph.Neo4jConnection import get_manager
from config.feature_flags import ENABLE_EDGE_WRITER

logger = logging.getLogger(__name__)

def process_edge_batch(neo4j_manager, batch: List[Dict]) -> int:
    '''Process a batch of edge relationships'''
    if not batch:
        return 0
    
    # Group by relationship type
    from collections import defaultdict
    grouped = defaultdict(list)
    
    for item in batch:
        # Create simplified relationship tuple
        rel = (
            {"id": item["source_id"]},  # Minimal source object
            {"id": item["target_id"]},  # Minimal target object
            {"value": item["rel_type"]},  # Relationship type enum
            item.get("properties", {})
        )
        grouped[item["rel_type"]].append(rel)
    
    # Use existing merge_relationships logic
    total_created = 0
    with neo4j_manager.driver.session() as session:
        for rel_type, rels in grouped.items():
            # Build params for the specific relationship type
            params = []
            for source, target, _, properties in rels:
                params.append({
                    "source_id": source["id"],
                    "target_id": target["id"],
                    "properties": properties
                })
            
            # Execute the merge with key property
            tx_result = session.run(f'''
                UNWIND $params AS param
                MATCH (s {{id: param.source_id}})
                MATCH (t {{id: param.target_id}})
                MERGE (s)-[r:{rel_type} {{key: param.source_id}}]->(t)
                SET r += param.properties
                RETURN count(r) as created
            ''', {"params": params})
            
            result = tx_result.single()
            if result:
                total_created += result["created"]
    
    return total_created

def main():
    '''Main edge writer loop'''
    logger.info("Edge Writer started")
    
    if not ENABLE_EDGE_WRITER:
        logger.warning("Edge writer is disabled by feature flag")
        return
    
    redis_client = RedisClient(prefix="")
    edge_queue = "edge_writer:queue"
    batch_size = 1000  # Process in batches
    
    neo4j_manager = get_manager()
    
    while True:
        try:
            # Get batch from queue
            batch = []
            for _ in range(batch_size):
                item = redis_client.client.lpop(edge_queue)
                if not item:
                    break
                batch.append(json.loads(item))
            
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
"""

# ============================================================================
# STEP 4: Create Kubernetes Deployment (k8s/edge-writer-deployment.yaml)
# ============================================================================
"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: edge-writer
  namespace: processing
spec:
  replicas: 1  # MUST BE 1 - single writer pattern
  selector:
    matchLabels:
      app: edge-writer
  template:
    metadata:
      labels:
        app: edge-writer
    spec:
      containers:
      - name: edge-writer
        image: faisalanjum/xbrl-worker:latest  # Same image
        command: ["python", "-m", "neograph.edge_writer_loop"]
        resources:
          requests:
            cpu: "1"
            memory: "1Gi"
          limits:
            cpu: "2"
            memory: "2Gi"
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        envFrom:
        - secretRef:
            name: eventtrader-secrets
        volumeMounts:
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: logs
        hostPath:
          path: /home/faisal/EventMarketDB/logs
          type: DirectoryOrCreate
      nodeSelector:
        kubernetes.io/hostname: minisforum2  # Or any node
"""

# ============================================================================
# EXPECTED PERFORMANCE IMPROVEMENT
# ============================================================================
"""
Current (with lock contention):
- HAS_CONCEPT: 13 minutes for 1477 relationships
- HAS_UNIT: 11.5 minutes for 1265 relationships  
- HAS_PERIOD: 12 minutes for 1477 relationships
- Total: ~36.5 minutes just for relationships

Expected (single writer, no locks):
- Processing rate: ~1000-2000 relationships/second
- Total for ~4200 relationships: 2-4 seconds
- Including overhead: < 30 seconds total

Overall 10-K processing time:
- From: 44+ minutes
- To: < 10 minutes
"""

# ============================================================================
# TESTING STRATEGY
# ============================================================================
"""
1. Deploy with feature flag OFF (safe fallback)
2. Deploy edge-writer pod
3. Turn feature flag ON for one 10-K
4. Monitor:
   - Queue length: redis-cli llen edge_writer:queue
   - Processing rate in edge-writer logs
   - Total time for 10-K completion
5. If successful, enable for all processing
"""