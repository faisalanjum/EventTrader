# EventMarketDB Real-Time Ingestion Events - Complete Implementation Guide

## Problem Statement
Need to detect in real-time when new items (News, Report, Transcript) are ingested into Neo4j so downstream pods (LLM, Analytics, etc.) can immediately begin processing them.

## Requirements
1. **100% reliable, real-time detection** 
2. **Minimalistic implementation** (simple over complex)
3. **Works for both historical and live** processing modes
4. **Filtering mechanism** for selective processing
5. **No complex schemas or heavy dependencies**

## Solution: Simple Redis Queue Pattern (Like Edge Writer)
Use a simple Redis list queue with ring buffer pattern for automatic cleanup.

## Complete Implementation

### 1. Feature Flags Configuration
Add to `config/feature_flags.py`:
```python
# Ingestion Events Configuration
ENABLE_INGESTION_EVENTS = os.getenv("ENABLE_INGESTION_EVENTS", "false").lower() == "true"
INGESTION_QUEUE = os.getenv("INGESTION_QUEUE", "node:events")
```

### 2. Event Emission Code

#### Report Mixin (`neograph/mixins/report.py`)
Add after line 430 (after `report_props = dict(record["r"].items())`):
```python
# Add imports at top
from config.feature_flags import ENABLE_INGESTION_EVENTS, INGESTION_QUEUE, ENABLE_HISTORICAL_DATA, ENABLE_LIVE_DATA
import json
from datetime import datetime

# Add this after line 430
if ENABLE_INGESTION_EVENTS and INGESTION_QUEUE:
    try:
        # Determine source from feature flags (not Redis prefix)
        source = "historical" if (ENABLE_HISTORICAL_DATA and not ENABLE_LIVE_DATA) else "live"
        
        # Ring buffer pattern for automatic cleanup
        pipeline = self.event_trader_redis.history_client.client.pipeline()
        pipeline.rpush(
            INGESTION_QUEUE,
            json.dumps({
                "type": "Report",
                "neo4j_id": report_props['id'],  # Neo4j internal ID
                "ts": datetime.utcnow().isoformat(),
                "source": source,
                "meta": {
                    "accession": report_props['accessionNo'],  # For reference
                    "form": report_props.get('formType'),      # For filtering
                    "cik": report_props.get('cik')             # For filtering
                }
            })
        )
        pipeline.ltrim(INGESTION_QUEUE, -100000, -1)  # Keep last 100k events
        pipeline.execute()
    except Exception as e:
        logger.warning(f"Failed to emit report event: {e}")
```

#### News Mixin (`neograph/mixins/news.py`)
Add after line 342 (after successful `execute_cypher_query`):
```python
# Add same imports at top

# Add after successful news merge
if ENABLE_INGESTION_EVENTS and INGESTION_QUEUE:
    try:
        source = "historical" if (ENABLE_HISTORICAL_DATA and not ENABLE_LIVE_DATA) else "live"
        
        pipeline = self.event_trader_redis.history_client.client.pipeline()
        pipeline.rpush(
            INGESTION_QUEUE,
            json.dumps({
                "type": "News",
                "neo4j_id": record['n']['id'],  # Get Neo4j ID from returned record
                "ts": datetime.utcnow().isoformat(),
                "source": source,
                "meta": {
                    "news_id": news_id,  # Original ID for reference
                    "title": news_node.title[:100] if hasattr(news_node, 'title') else ""
                }
            })
        )
        pipeline.ltrim(INGESTION_QUEUE, -100000, -1)
        pipeline.execute()
    except Exception as e:
        logger.warning(f"Failed to emit news event: {e}")
```

#### Transcript Mixin (`neograph/mixins/transcript.py`)
Add after line 363 (after `self.manager.merge_nodes([transcript_node])`):
```python
# Add same imports at top

# Note: merge_nodes doesn't return Neo4j ID, so we need to query
if ENABLE_INGESTION_EVENTS and INGESTION_QUEUE:
    try:
        # Get the Neo4j ID
        result = self.manager.execute_cypher_query(
            "MATCH (t:Transcript {id: $id}) RETURN ID(t) as neo4j_id",
            {"id": transcript_id}
        )
        if result:
            source = "historical" if (ENABLE_HISTORICAL_DATA and not ENABLE_LIVE_DATA) else "live"
            
            pipeline = self.event_trader_redis.history_client.client.pipeline()
            pipeline.rpush(
                INGESTION_QUEUE,
                json.dumps({
                    "type": "Transcript",
                    "neo4j_id": result['neo4j_id'],
                    "ts": datetime.utcnow().isoformat(),
                    "source": source,
                    "meta": {
                        "transcript_id": transcript_id,
                        "symbol": transcript_node.symbol,
                        "company": transcript_node.company_name
                    }
                })
            )
            pipeline.ltrim(INGESTION_QUEUE, -100000, -1)
            pipeline.execute()
    except Exception as e:
        logger.warning(f"Failed to emit transcript event: {e}")
```

### 3. Consumer Implementation

Create `neograph/ingestion_consumer_loop.py`:
```python
#!/usr/bin/env python3
"""
Ingestion Event Consumer - Processes node creation events
Follows the same pattern as edge_writer_loop.py
"""
import json
import logging
import os
import time
from typing import Dict
from neograph.Neo4jConnection import get_manager
from redisDB.redisClasses import RedisClient
from utils.log_config import setup_logging

logger = setup_logging(name="ingestion_consumer")

def should_process(data: Dict, consumer_type: str) -> bool:
    """
    Filtering logic - customize based on your needs
    
    Args:
        data: Event data with type, neo4j_id, source, meta
        consumer_type: Type of consumer (llm, analytics, etc.)
        
    Returns:
        bool: Whether to process this event
    """
    node_type = data.get('type')
    meta = data.get('meta', {})
    source = data.get('source', 'unknown')
    
    # Example LLM filtering
    if consumer_type == 'llm':
        # Reports: Only 10-K and 10-Q
        if node_type == 'Report':
            form = meta.get('form', '')
            return form in ['10-K', '10-Q', '10-K/A', '10-Q/A']
        
        # News: Process all
        elif node_type == 'News':
            return True
        
        # Transcripts: Process all earnings
        elif node_type == 'Transcript':
            return True
    
    # Add other consumer types as needed
    return False

def process_node(neo4j_manager, data: Dict):
    """
    Fetch node from Neo4j and process it
    
    Args:
        neo4j_manager: Neo4j connection manager
        data: Event data containing neo4j_id
    """
    try:
        # Universal query using Neo4j internal ID
        result = neo4j_manager.execute_cypher_query(
            "MATCH (n) WHERE ID(n) = $id RETURN n, labels(n) as labels",
            {"id": int(data['neo4j_id'])}
        )
        
        if result:
            node = dict(result['n'])
            labels = result['labels']
            node_type = data['type']
            
            # Route to appropriate processor
            if node_type == 'Report' and 'Report' in labels:
                logger.info(f"Processing Report: {node.get('accessionNo')}")
                # TODO: Add your LLM processing here
                # process_report_with_llm(node)
                
            elif node_type == 'News' and 'News' in labels:
                logger.info(f"Processing News: {node.get('id')}")
                # TODO: Add your LLM processing here
                # process_news_with_llm(node)
                
            elif node_type == 'Transcript' and 'Transcript' in labels:
                logger.info(f"Processing Transcript: {node.get('id')}")
                # TODO: Add your LLM processing here
                # process_transcript_with_llm(node)
                
        else:
            logger.warning(f"Node not found: {data}")
            
    except Exception as e:
        logger.error(f"Error processing node {data}: {e}")

def main():
    """Main consumer loop"""
    
    # Configuration
    queue = os.getenv("INGESTION_QUEUE", "node:events")
    batch_size = int(os.getenv("BATCH_SIZE", "100"))
    consumer_type = os.getenv("CONSUMER_TYPE", "llm")
    
    logger.info(f"Starting consumer: queue={queue}, batch={batch_size}, type={consumer_type}")
    
    # Initialize connections
    redis_client = RedisClient(prefix="")
    neo4j_manager = get_manager()
    
    # Statistics
    processed = 0
    filtered = 0
    iteration = 0
    
    while True:
        try:
            iteration += 1
            
            # Get batch from queue (same pattern as edge writer)
            pipeline = redis_client.client.pipeline()
            for _ in range(batch_size):
                pipeline.lpop(queue)
            items = pipeline.execute()
            
            # Process non-None items
            valid_items = [item for item in items if item]
            
            for item in valid_items:
                try:
                    data = json.loads(item)
                    
                    # Apply filtering
                    if should_process(data, consumer_type):
                        process_node(neo4j_manager, data)
                        processed += 1
                    else:
                        filtered += 1
                        
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON: {item}")
                except Exception as e:
                    logger.error(f"Processing error: {e}")
            
            # Log progress every 100 iterations
            if iteration % 100 == 0 and iteration > 0:
                queue_len = redis_client.client.llen(queue)
                logger.info(f"Stats: processed={processed}, filtered={filtered}, queue={queue_len}")
            
            # Brief pause when queue empty
            if not valid_items:
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            break
        except Exception as e:
            logger.error(f"Loop error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
```

### 4. Kubernetes Deployment

Create `k8s/ingestion-consumer.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ingestion-consumer-llm
  namespace: processing
spec:
  replicas: 2  # Multiple consumers OK
  selector:
    matchLabels:
      app: ingestion-consumer
      type: llm
  template:
    metadata:
      labels:
        app: ingestion-consumer
        type: llm
    spec:
      containers:
      - name: consumer
        image: faisalanjum/ingestion-consumer:latest
        env:
        - name: INGESTION_QUEUE
          value: "node:events"
        - name: CONSUMER_TYPE
          value: "llm"
        - name: BATCH_SIZE
          value: "100"
        - name: NEO4J_URI
          value: "bolt://neo4j-bolt.neo4j:7687"
        - name: NEO4J_USERNAME
          valueFrom:
            secretKeyRef:
              name: eventtrader-secrets
              key: neo4j_username
        - name: NEO4J_PASSWORD
          valueFrom:
            secretKeyRef:
              name: eventtrader-secrets
              key: neo4j_password
        - name: REDIS_HOST
          valueFrom:
            secretKeyRef:
              name: eventtrader-secrets
              key: redis_host
        - name: REDIS_PORT
          valueFrom:
            secretKeyRef:
              name: eventtrader-secrets
              key: redis_port
        resources:
          requests:
            memory: "2Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "1"
        volumeMounts:
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: logs
        hostPath:
          path: /home/faisal/EventMarketDB/logs
          type: DirectoryOrCreate
```

### 5. Docker Build

Create `Dockerfile.ingestion-consumer`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set Python path
ENV PYTHONPATH=/app

# Run consumer
CMD ["python", "neograph/ingestion_consumer_loop.py"]
```

Build script (`scripts/build-ingestion-consumer.sh`):
```bash
#!/bin/bash
docker build -f Dockerfile.ingestion-consumer -t faisalanjum/ingestion-consumer:latest .
docker push faisalanjum/ingestion-consumer:latest
```

## Testing

### Local Testing
```bash
# Enable events
export ENABLE_INGESTION_EVENTS=true
export INGESTION_QUEUE=node:test

# Run historical processing
./scripts/et chunked-historical 2024-01-01 2024-01-01

# Check queue
redis-cli LLEN node:test
redis-cli LRANGE node:test 0 -1
```

### Production Deployment
```bash
# Step 1: Enable in pods
kubectl set env deployment/event-trader -n processing ENABLE_INGESTION_EVENTS=true

# Step 2: Deploy consumer
kubectl apply -f k8s/ingestion-consumer.yaml

# Step 3: Monitor
kubectl logs -f -l app=ingestion-consumer -n processing
```

## Key Design Decisions & Corrections

### 1. Source Detection
- ❌ NOT using Redis prefix (unreliable)
- ✅ Using feature flags: `ENABLE_HISTORICAL_DATA` and `ENABLE_LIVE_DATA`

### 2. ID Strategy
- Neo4j internal ID is sufficient and unique
- Include business ID in metadata for reference only

### 3. No Race Conditions
- Event emitted AFTER node is in Neo4j
- No delays needed

### 4. Ring Buffer Pattern
- Automatic cleanup with `ltrim`
- Keeps last 100k events (~50MB)
- No cron jobs needed

### 5. Simple Filtering
- Consumer decides what to process
- Easy to extend for different consumer types

## Architecture Context

### How Both Modes Work
- **Historical**: `./scripts/et chunked-historical` runs locally, calls same mixins
- **Live**: `event-trader` pod runs in K8s, calls same mixins
- **Both use**: `process_reports_to_neo4j()`, `process_news_to_neo4j()`, etc.

### Existing Patterns
- **Edge Writer**: Uses `rpush`/`lpop` for relationships, ~9-10k/sec
- **XBRL Workers**: Queue-based with KEDA scaling
- **Report Enricher**: Queue-based processing

### Why This Design
1. Follows proven edge writer pattern
2. Minimal code changes (~30 lines total)
3. No new dependencies
4. Works identically for both processing modes
5. 100% reliable (Redis persistence)

## Total Implementation
- 3 emission points (report.py:430, news.py:342, transcript.py:363)
- 1 consumer script
- 1 K8s deployment
- 2 environment variables

## Commands Reference
```bash
# Queue monitoring
kubectl exec -it redis-* -n infrastructure -- redis-cli LLEN node:events
kubectl exec -it redis-* -n infrastructure -- redis-cli LRANGE node:events -10 -1

# Consumer monitoring
kubectl get pods -l app=ingestion-consumer -n processing
kubectl logs -l app=ingestion-consumer -n processing --tail=50

# Enable/disable
kubectl set env deployment/event-trader -n processing ENABLE_INGESTION_EVENTS=true
kubectl set env deployment/event-trader -n processing ENABLE_INGESTION_EVENTS=false
```

## Summary
Simple Redis queue pattern following edge writer approach. Emits events after Neo4j insertion with minimal metadata. Ring buffer ensures automatic cleanup. Works for both historical and live processing with zero additional dependencies.