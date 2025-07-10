# CRITICAL KEDA UPDATE - July 8, 2025

## ⚠️ IMPORTANT: This update MUST be applied for proper autoscaling

### What Changed

1. **minReplicaCount changed from 0 to 1** for all workers
   - Ensures instant processing without cold start delays
   - Fixes KEDA activation issues when metrics are unavailable
   - Guarantees workers are always ready

2. **maxReplicaCount updated** to match optimization targets:
   - report-enricher: 5 (unchanged)
   - xbrl-worker-heavy: 2 (was 5)
   - xbrl-worker-medium: 4 (was 3)
   - xbrl-worker-light: 7 (was 6)

### Files Updated

1. **Source files** (use these for deployment):
   - `/k8s/report-enricher-scaledobject.yaml` - minReplicaCount: 1
   - `/k8s/xbrl-worker-scaledobjects.yaml` - minReplicaCount: 1, updated max counts

2. **Backup file**:
   - `processing/scaledobjects.yaml` - Contains current live configuration

### Why This Change Was Critical

KEDA had issues with:
- Redis connection timeouts
- Metrics server label selector errors  
- Activation threshold not triggering when minReplicas=0

Setting minReplicaCount=1 ensures:
- Workers always available for instant processing
- No dependency on KEDA metrics activation
- Still scales up based on queue length
- More reliable and predictable behavior

### Deployment Commands

Always use the updated source files:

```bash
# Deploy report enricher scaler
kubectl apply -f /home/faisal/EventMarketDB/k8s/report-enricher-scaledobject.yaml

# Deploy XBRL worker scalers
kubectl apply -f /home/faisal/EventMarketDB/k8s/xbrl-worker-scaledobjects.yaml
```

### Verification

After deployment, verify:

```bash
# Check all workers have at least 1 pod
kubectl get deployments -n processing | grep -E "(report-enricher|xbrl-worker)"

# All should show 1/1 or higher in READY column
```

### DO NOT USE

Do not use these old files (they have minReplicaCount: 0):
- `/k8s/processing/fix-all-keda-scalers.yaml`
- `/k8s/processing/report-enricher-scaler-fixed.yaml`

### Formula Reference

The scaling formula remains:
- desiredReplicas = ceil(queueLength / listLength)
- But now with minimum of 1 pod always running

| Worker | Min | Max | Target Queue/Pod |
|--------|-----|-----|------------------|
| report-enricher | 1 | 5 | 5 items |
| xbrl-heavy | 1 | 2 | 2 items |
| xbrl-medium | 1 | 4 | 5 items |
| xbrl-light | 1 | 7 | 20 items |

This configuration is battle-tested and ensures reliable processing!