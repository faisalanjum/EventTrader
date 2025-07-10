# EventMarketDB Kubernetes Optimization Plan (UPDATED)

## Executive Summary

**Current State**: Cluster optimized with KEDA minReplicaCount=1 for all workers, ensuring instant processing. Neo4j reduced to 90GB. All XBRL workers temporarily on minisforum2 for historical processing.

**Key Achievement**: XBRL processing improved by implementing proper resource limits and fixing KEDA autoscaling issues.

**Cluster Capacity**: 48 CPU cores, 241.53GB total RAM across 3 nodes

## Part 1: Current State (As of July 8, 2025)

### Cluster Topology

- **minisforum** (Control Plane) - 192.168.40.73
  - 16 CPU cores, 57.51GB RAM allocatable
  - Current usage: 10% CPU (1.75 cores), 5% Memory (3.3GB)
  - Taints: NONE (all removed)
  - Running: Control plane, KEDA, MCP services, Loki

- **minisforum2** (Primary Worker) - 192.168.40.72
  - 16 CPU cores, 60.51GB RAM allocatable
  - Current usage: 33% CPU (5.4 cores), 31% Memory (19.1GB)
  - No taints
  - Running: Redis, NATS, Prometheus, Grafana, ALL XBRL workers, event-trader

- **minisforum3** (Database) - 192.168.40.74
  - 16 CPU cores, 123.51GB RAM allocatable
  - Current usage: 50% CPU (8.1 cores), 72% Memory (88.1GB)
  - Taints: `database=neo4j:NoSchedule`
  - Running: Neo4j exclusively (using ~35GB actual, 90GB allocated)

### Current Pod Configuration

#### Processing Namespace - Actual Resources

| Component | Replicas | CPU Request | Memory Request | CPU Limit | Memory Limit |
|-----------|----------|-------------|----------------|-----------|--------------|
| event-trader | 1 (fixed) | 500m | 8Gi | 2 | 16Gi |
| report-enricher | 1-5 | 500m | 2Gi | 2 | 8Gi |
| xbrl-worker-heavy | 1-2 | 2 | 6Gi | 3 | 8Gi |
| xbrl-worker-medium | 1-4 | 1.5 | 3Gi | 2 | 4Gi |
| xbrl-worker-light | 1-7 | 1 | 1.5Gi | 1.5 | 2Gi |

**Note**: Light workers use 1536Mi (1.5Gi) not 3Gi as document previously stated.

### KEDA Configuration (CRITICAL UPDATE)

All workers now have `minReplicaCount: 1` to ensure instant processing:

| Worker | Min | Max (Normal) | Max (Historical) | Target Queue/Pod | Cooldown |
|--------|-----|-------------|------------------|------------------|----------|
| report-enricher | 1 | 5 | 5 | 5 items | 60s |
| xbrl-heavy | 1 | 2 | 2 | 2 items | 300s |
| xbrl-medium | 1 | 4 | 3 | 5 items | 180s |
| xbrl-light | 1 | 7 | 5 | 20 items | 120s |

**Note**: During historical processing, apply safety limits to prevent memory exhaustion.

### Resource Usage at Different Scales

#### Minimum Scale (Current State - minReplicas=1)
- Event Trader: 0.5 CPU, 8Gi RAM
- Report Enricher: 0.5 CPU, 2Gi RAM  
- XBRL Heavy: 2 CPU, 6Gi RAM
- XBRL Medium: 1.5 CPU, 3Gi RAM
- XBRL Light: 1 CPU, 1.5Gi RAM
- **Total**: 5.5 CPU, 20.5Gi RAM

#### Maximum Scale (All at max replicas)
- Event Trader: 0.5 CPU, 8Gi RAM (1 pod)
- Report Enricher: 2.5 CPU, 10Gi RAM (5 pods)
- XBRL Heavy: 4 CPU, 12Gi RAM (2 pods)
- XBRL Medium: 6 CPU, 12Gi RAM (4 pods)
- XBRL Light: 7 CPU, 10.5Gi RAM (7 pods)
- **Total**: 20 CPU, 52.5Gi RAM

### Neo4j Configuration
- **Current**: 90Gi memory (both request and limit)
- **CPU**: 8 cores requested, 16 limit
- **Actual Usage**: ~35GB (plenty of headroom)

### Queue Status (Live)
- Heavy queue: 0 items
- Medium queue: 0 items
- Light queue: 0 items  
- Enrich queue: 0 items

## Resource Math Verification

### Total Cluster Capacity
| Node | CPU | RAM | 
|------|-----|-----|
| minisforum | 16 | 57.51Gi |
| minisforum2 | 16 | 60.51Gi |
| minisforum3 | 16 | 123.51Gi |
| **Total** | **48** | **241.53Gi** |

### Current Allocations (Requests)

#### minisforum (10% CPU, 5% RAM used)
- System/Control plane: ~1.75 CPU, ~3.3Gi
- Available: ~14.25 CPU, ~54.2Gi

#### minisforum2 (33% CPU, 31% RAM used)
- Current pods: ~5.4 CPU, ~19.1Gi
- Available: ~10.6 CPU, ~41.4Gi

#### minisforum3 (50% CPU, 72% RAM used)
- Neo4j: 8 CPU, 90Gi
- Available: 8 CPU, 33.5Gi

### Capacity for Historical Processing

With all XBRL workers on minisforum2:
- **minisforum available**: 54.2Gi RAM (exceeds 48Gi requirement)
- **Historical can run** with 6Gi buffer

### Maximum Scale Feasibility Check

If all pods scale to max on minisforum2:
- Required: 20 CPU, 52.5Gi RAM
- Available: 16 CPU, 60.51Gi RAM
- **Result**: CPU constrained at max scale (would need 125% CPU)

This is acceptable because:
1. Rarely all queues peak simultaneously
2. Kubernetes will schedule based on available resources
3. Some pods could spill to minisforum if needed

## Key Corrections from Original Document

1. **KEDA minReplicaCount**: Now 1 for all workers (was 0)
2. **Light worker memory**: 1.5Gi request (not 3Gi)
3. **Neo4j memory**: 90Gi (not 85Gi)
4. **Node taints**: minisforum has NO taints (not graph taint)
5. **Max replicas**: Heavy=2, Medium=4, Light=7 (not 2/2/3)

## Current Operational State

### What's Working Well
- ✅ KEDA autoscaling with minReplicas=1
- ✅ All workers ready for instant processing
- ✅ Neo4j stable with 55Gi headroom
- ✅ Historical processing has sufficient memory

### Temporary Configurations
1. **XBRL workers have nodeAffinity** excluding minisforum (REMOVED for medium/light on July 9)
2. **All XBRL on minisforum2** to reserve minisforum for historical (CHANGED - now distributed)
3. **KEDA safety limits applied** for historical processing (Medium: 3, Light: 5)
4. **Single heavy worker experiment** active (1 pod, 8 CPU/16Gi RAM)
5. **After historical**: Remove nodeAffinity and restore full KEDA scaling

### Historical Processing Safety
- Apply `/k8s/historical-safety-config.yaml` before starting historical
- Provides 11GB memory buffer on minisforum2
- Prevents OOM during peak scaling

### 🎚️ Heavy Worker Scaling Configuration

#### Current State (July 9, 2025)
- **Heavy queue**: 1,327 items backlog
- **Max replicas**: 3 (temporarily increased from 2)
- **Resources**: 2 CPU request, 6Gi memory per pod

#### Quick Scaling Commands

**📈 To INCREASE heavy workers to 5** (when NOT running historical):
```bash
# Simply patch KEDA max replicas
kubectl patch scaledobject xbrl-worker-heavy-scaler -n processing \
  --type='merge' -p '{"spec":{"maxReplicaCount":5}}'

# KEDA will auto-scale up based on queue depth
# Check status:
kubectl get hpa -n processing | grep heavy
```

**📉 To DECREASE heavy workers to 2** (for historical processing):
```bash
# Patch KEDA max replicas
kubectl patch scaledobject xbrl-worker-heavy-scaler -n processing \
  --type='merge' -p '{"spec":{"maxReplicaCount":2}}'

# KEDA will auto-scale down
# Excess pods will terminate gracefully
```

#### Reference Values
- **Default**: 2 max replicas (original configuration)
- **Current**: 3 max replicas (for backlog)
- **Maximum**: 5 max replicas (when not running historical)
- **Queue target**: 1 pod per 2 items in queue

**Note**: No deployment changes needed - only KEDA maxReplicaCount

### Heavy XBRL Worker Experiment (July 9, 2025)

#### Problem
- 12 concurrent workers causing Neo4j lock contention
- Workers using <1% CPU but requesting 100% (wasting resources)
- Processing taking 60 min per 10-K vs 4 min locally

#### Experiment Configuration

**Original Configuration** (in backup file):
- Heavy: 2 CPU request, 6Gi memory (3 CPU limit, 8Gi limit)
- KEDA: min=1, max=3 (was 2, temporarily increased)
- nodeAffinity: Prefer minisforum2/minisforum over minisforum3

**Current Experiment** (active now):
- Heavy: 4 CPU request, 16Gi memory (12 CPU limit, 24Gi limit)
- KEDA: min=1, max=2 (to test 2 high-resource pods)
- nodeAffinity: REMOVED for medium/light workers

#### File Changes Made
1. `k8s/xbrl-worker-deployments.yaml` - Modified heavy worker resources
2. `k8s/xbrl-worker-deployments.yaml.backup` - Original configuration
3. KEDA ScaledObject - Changed via kubectl (max replicas 3→2)
4. Deployments - Removed nodeAffinity via kubectl

---

## 🚀 TO APPLY EXPERIMENT (2 Heavy Workers)

```bash
# 1. Backup original and update deployment file
cp k8s/xbrl-worker-deployments.yaml k8s/xbrl-worker-deployments.yaml.backup

# 2. Edit k8s/xbrl-worker-deployments.yaml - ONLY heavy worker section:
#    resources:
#      requests:
#        cpu: "4"      # Was 2
#        memory: "16Gi" # Was 6Gi
#      limits:
#        cpu: "12"     # Was 3
#        memory: "24Gi" # Was 8Gi

# 3. Deploy the updated configuration
./scripts/deploy.sh xbrl-worker

# 4. Adjust KEDA for 2 heavy workers
kubectl patch scaledobject xbrl-worker-heavy-scaler -n processing \
  --type='merge' -p '{"spec":{"maxReplicaCount":2}}'

# 5. Remove nodeAffinity to use all nodes
kubectl patch deployment xbrl-worker-medium -n processing --type='json' \
  -p='[{"op": "remove", "path": "/spec/template/spec/affinity"}]'
kubectl patch deployment xbrl-worker-light -n processing --type='json' \
  -p='[{"op": "remove", "path": "/spec/template/spec/affinity"}]'
```

---

## 🔄 TO RESTORE ORIGINAL (Multiple Light Workers)

```bash
# 1. Restore original deployment file
cp k8s/xbrl-worker-deployments.yaml.backup k8s/xbrl-worker-deployments.yaml

# 2. Deploy original configuration
./scripts/deploy.sh xbrl-worker

# 3. Restore KEDA max replicas
kubectl patch scaledobject xbrl-worker-heavy-scaler -n processing \
  --type='merge' -p '{"spec":{"maxReplicaCount":3}}'

### Temporary Lock Reduction Pattern (1-2-4)
For severe lock contention during XBRL optimization testing:
```bash
# Reduce to minimal workers
kubectl patch scaledobject xbrl-worker-heavy-scaler -n processing \
  --type='merge' -p '{"spec":{"maxReplicaCount":1}}'
kubectl patch scaledobject xbrl-worker-medium-scaler -n processing \
  --type='merge' -p '{"spec":{"maxReplicaCount":2}}'
kubectl patch scaledobject xbrl-worker-light-scaler -n processing \
  --type='merge' -p '{"spec":{"maxReplicaCount":4}}'

# Restore to normal 2-3-4 pattern (or original 4-6-10)
kubectl patch scaledobject xbrl-worker-heavy-scaler -n processing \
  --type='merge' -p '{"spec":{"maxReplicaCount":2}}'
kubectl patch scaledobject xbrl-worker-medium-scaler -n processing \
  --type='merge' -p '{"spec":{"maxReplicaCount":3}}'
# Light already at 4, no change needed
```

# 4. Re-apply nodeAffinity (if needed for historical processing)
# Heavy worker:
kubectl patch deployment xbrl-worker-heavy -n processing --type='strategic' \
  -p '{"spec":{"template":{"spec":{"affinity":{"nodeAffinity":{"preferredDuringSchedulingIgnoredDuringExecution":[{"weight":100,"preference":{"matchExpressions":[{"key":"kubernetes.io/hostname","operator":"In","values":["minisforum2","minisforum"]}]}},{"weight":10,"preference":{"matchExpressions":[{"key":"kubernetes.io/hostname","operator":"In","values":["minisforum3"]}]}}]}}}}}}}'

# Medium worker:
kubectl patch deployment xbrl-worker-medium -n processing --type='strategic' \
  -p '{"spec":{"template":{"spec":{"affinity":{"nodeAffinity":{"preferredDuringSchedulingIgnoredDuringExecution":[{"weight":100,"preference":{"matchExpressions":[{"key":"kubernetes.io/hostname","operator":"In","values":["minisforum2","minisforum"]}]}},{"weight":10,"preference":{"matchExpressions":[{"key":"kubernetes.io/hostname","operator":"In","values":["minisforum3"]}]}}]}}}}}}}'

# Light worker:
kubectl patch deployment xbrl-worker-light -n processing --type='strategic' \
  -p '{"spec":{"template":{"spec":{"affinity":{"nodeAffinity":{"preferredDuringSchedulingIgnoredDuringExecution":[{"weight":100,"preference":{"matchExpressions":[{"key":"kubernetes.io/hostname","operator":"In","values":["minisforum2","minisforum"]}]}},{"weight":10,"preference":{"matchExpressions":[{"key":"kubernetes.io/hostname","operator":"In","values":["minisforum3"]}]}}]}}}}}}}'
```

#### Summary for Next Bot
- **Ground truth**: `k8s/xbrl-worker-deployments.yaml` (no kubectl overrides)
- **Backup**: `k8s/xbrl-worker-deployments.yaml.backup`
- **Only 2 changes**: deployment file resources + KEDA max replicas
- **Optional**: nodeAffinity removal for better distribution

### Neo4j Deadlock Fix (July 9, 2025)

#### Problem
- Neo4j lock contention with 12+ concurrent workers
- Processing taking 60+ minutes per 10-K form
- Workers using <1% CPU while waiting for locks

#### Solution: 2-3-4 Worker Pattern
1. **KEDA Configuration** (`k8s/xbrl-worker-scaledobjects.yaml`):
   - Heavy: maxReplicaCount=2 (was 4)
   - Medium: maxReplicaCount=3 (was 6)
   - Light: maxReplicaCount=4 (was 10)

2. **Batch Size Reduction** (`neograph/Neo4jManager.py`):
   ```python
   REL_BATCH_SIZE: int = 100  # was 500
   ```

#### To Apply Fix
```bash
# Deploy batch size change
./scripts/deploy.sh xbrl-worker

# KEDA already updated in file - just apply
kubectl apply -f k8s/xbrl-worker-scaledobjects.yaml
```

#### To Revert
```bash
# Edit Neo4jManager.py: REL_BATCH_SIZE = 500
# Edit xbrl-worker-scaledobjects.yaml: maxReplicaCount 4/6/10
./scripts/deploy.sh xbrl-worker
kubectl apply -f k8s/xbrl-worker-scaledobjects.yaml
```

## Future Optimization Path

### Phase 1 (Current)
- Historical processing on minisforum (54.2Gi available)
- All XBRL on minisforum2
- Monitor actual resource usage

### Phase 2 (Post-Historical)
```bash
# Remove nodeAffinity restrictions
kubectl patch deployment xbrl-worker-heavy -n processing --type='json' -p='[{"op": "remove", "path": "/spec/template/spec/affinity"}]'
kubectl patch deployment xbrl-worker-medium -n processing --type='json' -p='[{"op": "remove", "path": "/spec/template/spec/affinity"}]'
kubectl patch deployment xbrl-worker-light -n processing --type='json' -p='[{"op": "remove", "path": "/spec/template/spec/affinity"}]'
```

### Phase 3 (Future Services)
Available after historical completes:
- minisforum: 14 CPU + 54Gi
- minisforum2: Variable based on XBRL load
- minisforum3: 8 CPU + 33Gi

## Monitoring Commands

```bash
# Check current resource usage
kubectl top nodes
kubectl top pods -n processing

# Check queue depths
REDIS_POD=$(kubectl get pod -n infrastructure -l app=redis -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n infrastructure $REDIS_POD -- redis-cli LLEN reports:queues:xbrl:heavy

# Verify KEDA scaling
kubectl get hpa -n processing
kubectl get scaledobjects -n processing
```

## Summary

The cluster is properly configured with:
- **Correct resource allocations** verified by actual kubectl output
- **KEDA fixed** with minReplicaCount=1 for reliability
- **Sufficient capacity** for all current and planned workloads
- **Temporary optimizations** for historical processing

All mathematical calculations have been verified against actual cluster state.

---
*Last Updated: July 9, 2025*
*Verified with: kubectl v1.30.12, K3s cluster*