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

| Worker | Min | Max | Target Queue/Pod | Cooldown |
|--------|-----|-----|------------------|----------|
| report-enricher | 1 | 5 | 5 items | 60s |
| xbrl-heavy | 1 | 2 | 2 items | 300s |
| xbrl-medium | 1 | 4 | 5 items | 180s |
| xbrl-light | 1 | 7 | 20 items | 120s |

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
1. **XBRL workers have nodeAffinity** excluding minisforum
2. **All XBRL on minisforum2** to reserve minisforum for historical
3. **After historical**: Remove nodeAffinity to restore multi-node distribution

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
*Last Updated: July 8, 2025*
*Verified with: kubectl v1.30.12, K3s cluster*