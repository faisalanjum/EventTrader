# Historical Processing Safety Configuration Applied

## Status: ✅ READY FOR HISTORICAL PROCESSING

### Applied Changes (July 8, 2025)

1. **KEDA Max Replicas Reduced:**
   - XBRL Medium: 4 → 3 pods
   - XBRL Light: 7 → 5 pods
   - Total pods reduced: 3 (saving 12GB RAM)

2. **Current KEDA Configuration:**
   | Worker | Min | Max | Memory per Pod | Max Memory |
   |--------|-----|-----|----------------|------------|
   | Report Enricher | 1 | 5 | 2GB | 10GB |
   | XBRL Heavy | 1 | 2 | 6GB | 12GB |
   | XBRL Medium | 1 | 3 | 3GB | 9GB |
   | XBRL Light | 1 | 5 | 1.5GB | 7.5GB |

3. **Memory Safety Margins:**
   - **minisforum**: 57.51GB total, ~55.3GB max usage = 2.2GB buffer
   - **minisforum2**: 60.51GB total, ~49.5GB max usage = 11GB buffer

### To Start Historical Processing:

```bash
# Historical processing can now be started safely
./scripts/et chunked-historical <start_date> <end_date>
```

### During Historical Processing:

Monitor memory usage:
```bash
watch -n 30 'kubectl top nodes; echo "---"; kubectl get pods -n processing | grep -E "(report-enricher|xbrl)" | wc -l'
```

If memory pressure occurs on minisforum2 (>55GB used):
```bash
# Manually reduce light workers if needed
kubectl scale deployment xbrl-worker-light --replicas=3 -n processing
```

### After Historical Processing Completes:

1. **Restore full KEDA scaling:**
```bash
kubectl apply -f /home/faisal/EventMarketDB/k8s/xbrl-worker-scaledobjects.yaml
```

2. **Remove nodeAffinity to allow multi-node distribution:**
```bash
kubectl patch deployment xbrl-worker-heavy -n processing --type='json' -p='[{"op": "remove", "path": "/spec/template/spec/affinity"}]'
kubectl patch deployment xbrl-worker-medium -n processing --type='json' -p='[{"op": "remove", "path": "/spec/template/spec/affinity"}]'
kubectl patch deployment xbrl-worker-light -n processing --type='json' -p='[{"op": "remove", "path": "/spec/template/spec/affinity"}]'
```

3. **Verify pods redistribute:**
```bash
kubectl get pods -n processing -o wide | grep xbrl
```

### Safety Features:

1. **Report-enricher podAntiAffinity** - Automatically distributes across nodes
2. **Reduced max replicas** - Prevents memory exhaustion
3. **11GB buffer on minisforum2** - Room for unexpected spikes
4. **minReplicaCount=1** - Ensures instant processing without cold starts

The cluster is now optimally configured for safe historical processing!