# Disaster Recovery Updates - July 8, 2025

## Critical Changes Since Original Backup

### 1. KEDA Configuration (CRITICAL)
- **All workers now have `minReplicaCount: 1`** (was 0)
- **Normal max replicas**: Heavy=2, Medium=4, Light=7, Enricher=5
- **Historical safety limits**: Heavy=2, Medium=3, Light=5, Enricher=5
- **Files updated**: 
  - `/k8s/report-enricher-scaledobject.yaml`
  - `/k8s/xbrl-worker-scaledobjects.yaml`
  - `/k8s/historical-safety-config.yaml` (apply during historical)
- **Reason**: KEDA had activation issues with minReplicas=0

### 2. Node Configuration
- **minisforum**: All taints removed (no control-plane or graph taints)
- **minisforum2**: No taints (worker node)
- **minisforum3**: Only `database=neo4j:NoSchedule` taint remains

### 3. XBRL Worker Distribution
- **Temporary**: All XBRL workers have nodeAffinity to exclude minisforum
- **Reason**: Reserve minisforum memory for historical processing
- **To revert after historical**: Remove nodeAffinity from deployments

### 4. Neo4j Memory
- **Updated**: 90GB limit (was 95GB)
- **Actual usage**: ~35GB

## Restore Order (Updated)

1. Apply node labels and taints (only database taint on minisforum3)
2. Create namespaces
3. Apply storage and CRDs
4. Deploy KEDA first
5. Deploy infrastructure (Redis, etc)
6. Deploy Neo4j and wait for ready
7. Deploy processing namespace
8. **NEW**: Verify KEDA configs have minReplicaCount=1
9. Apply temporary nodeAffinity for XBRL workers

## Quick Commands

```bash
# After restore, verify KEDA configs
kubectl get scaledobjects -n processing -o custom-columns=NAME:.metadata.name,MIN:.spec.minReplicaCount

# All should show MIN=1

# If any show MIN=0, apply fix:
kubectl apply -f KEDA_CRITICAL_UPDATE.yaml
```

## Files in This Backup

- **Original backup**: As of backup creation time
- **KEDA_CRITICAL_UPDATE.md**: Explains KEDA changes
- **KEDA_CRITICAL_UPDATE.yaml**: Fixed ScaledObject definitions
- **This file**: Summary of all updates

Always use the updated configurations for reliable autoscaling!