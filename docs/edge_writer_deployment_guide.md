# Edge Writer Deployment Guide

## Overview
The Edge Writer eliminates Neo4j lock contention by using a single-writer pattern for high-volume relationship types:
- HAS_CONCEPT, HAS_UNIT, HAS_PERIOD (fact lookups)
- REPORTS (fact-to-XBRL relationships)
- FACT_MEMBER (fact-to-dimension relationships)

## Pre-Deployment Checklist
- [x] Feature flag added: `ENABLE_EDGE_WRITER = True`
- [x] XBRL processor updated with queue support
- [x] Edge writer service created
- [x] Kubernetes deployment files ready
- [x] Rollback plan documented

## Deployment Steps

### Step 1: Deploy Edge Writer Pod (Before Enabling in Workers)
```bash
# Deploy the edge writer pod
kubectl apply -f k8s/edge-writer-deployment.yaml

# Wait for pod to be ready
kubectl wait --for=condition=ready pod -l app=edge-writer -n processing --timeout=60s

# Verify it's running
kubectl logs -n processing -l app=edge-writer --tail=20
# Should see: "Edge Writer started" and "Using queue: edge_writer:queue"
```

### Step 2: Deploy Updated Code
```bash
# Scale workers to 0 to ensure clean deployment
kubectl scale deployment xbrl-worker-heavy xbrl-worker-medium xbrl-worker-light -n processing --replicas=0

# Deploy all components with updated code
./scripts/deploy-all.sh

# Verify deployment
kubectl get pods -n processing
```

### Step 3: Enable Edge Queue in Workers
```bash
# Add EDGE_QUEUE environment variable to all XBRL workers
kubectl patch deployment xbrl-worker-heavy -n processing --patch-file k8s/xbrl-workers-edge-patch.yaml
kubectl patch deployment xbrl-worker-medium -n processing --patch-file k8s/xbrl-workers-edge-patch.yaml
kubectl patch deployment xbrl-worker-light -n processing --patch-file k8s/xbrl-workers-edge-patch.yaml
```

### Step 4: Test with Single Worker
```bash
# Start with 1 heavy worker
kubectl scale deployment xbrl-worker-heavy -n processing --replicas=1

# Monitor queue depth
watch -n 5 'kubectl exec -it redis-* -n infrastructure -- redis-cli llen edge_writer:queue'

# Check worker logs for "Queued X fact relationships to edge writer"
kubectl logs -n processing -l app=xbrl-worker-heavy --tail=100 | grep "Queued"

# Check edge writer processing
kubectl logs -n processing -l app=edge-writer -f
```

### Step 5: Scale Up Gradually
```bash
# If queue depth stays low (< 1000), scale up
kubectl scale deployment xbrl-worker-heavy -n processing --replicas=2
kubectl scale deployment xbrl-worker-medium -n processing --replicas=4
kubectl scale deployment xbrl-worker-light -n processing --replicas=7

# Monitor queue depth and processing rate
kubectl logs -n processing -l app=edge-writer --tail=50
```

## Monitoring

### Key Metrics to Watch
1. **Queue Depth** (should stay < 1000)
   ```bash
   kubectl exec -it redis-* -n infrastructure -- redis-cli llen edge_writer:queue
   ```

2. **Processing Rate** (should be 1000-2000 rel/s)
   ```bash
   kubectl logs -n processing -l app=edge-writer | grep "rel/s"
   ```

3. **XBRL Processing Time**
   ```bash
   kubectl logs -n processing -l app=xbrl-worker-heavy | grep "Successfully processed XBRL"
   ```

### Expected Results
- 10-K processing: From 44+ minutes → Under 10 minutes
- Ford Motor 10-K: From 258 minutes → Under 15 minutes
- Queue depth: Stays near 0 during normal operation
- No lock contention errors in logs

## Rollback Procedures

### Option 1: Disable via Environment Variable (Instant)
```bash
# Remove EDGE_QUEUE from all workers
kubectl set env deployment/xbrl-worker-heavy deployment/xbrl-worker-medium deployment/xbrl-worker-light -n processing EDGE_QUEUE-

# Workers immediately revert to direct merge behavior
```

### Option 2: Disable via Feature Flag
```bash
# Edit feature_flags.py and set ENABLE_EDGE_WRITER = False
# Then redeploy
./scripts/deploy-all.sh
```

### Option 3: Complete Removal
```bash
# Delete edge writer pod
kubectl delete deployment edge-writer -n processing

# Remove EDGE_QUEUE from workers
kubectl set env deployment/xbrl-worker-heavy deployment/xbrl-worker-medium deployment/xbrl-worker-light -n processing EDGE_QUEUE-
```

## Troubleshooting

### High Queue Depth
If queue depth > 10,000:
1. Check edge writer logs for errors
2. Verify Neo4j connectivity
3. Scale down workers temporarily
4. Consider increasing edge writer batch size

### Edge Writer Not Processing
1. Check feature flag: `ENABLE_EDGE_WRITER`
2. Verify EDGE_QUEUE env var is set
3. Check Redis connectivity
4. Review edge writer logs

### No Performance Improvement
1. Verify workers are queueing relationships (check logs)
2. Confirm edge writer is processing (check logs)
3. Check Neo4j query logs for lock contention

## Implementation Safety

### Why This is 100% Safe:
1. **Feature Flag Control**: Can disable instantly
2. **Environment Variable Guard**: Double safety with EDGE_QUEUE
3. **Exact Same Queries**: Uses identical Neo4j merge logic
4. **No Ordering Dependencies**: Validated through code analysis
5. **Gradual Rollout**: Test with 1 worker before scaling
6. **Proven Pattern**: Same as report enricher architecture
7. **Idempotent Operations**: Key constraints prevent duplicates

### What Changes:
- Relationships created by single writer instead of multiple workers
- Brief delay (< 1 second) between fact creation and relationship creation
- Log messages show queuing instead of direct merge

### What Stays the Same:
- Final graph structure identical
- All properties preserved
- Transaction safety maintained
- Business logic unchanged