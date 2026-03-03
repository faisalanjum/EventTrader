---
description: "Check Kubernetes cluster health: pod status, restarts, resource usage, and recent events"
tools:
  - Bash
  - Read
---

Check the Kubernetes cluster health for EventMarketDB workloads.

## Steps

1. **Pod status** — `kubectl get pods -o wide` across relevant namespaces (default, eventtrader)
2. **Recent restarts** — Flag any pods with restart count > 0: `kubectl get pods -o jsonpath='{range .items[?(@.status.containerStatuses[0].restartCount>0)]}{.metadata.name}{"\t"}{.status.containerStatuses[0].restartCount}{"\n"}{end}'`
3. **Resource usage** — `kubectl top pods` (if metrics-server available)
4. **Recent events** — `kubectl get events --sort-by=.lastTimestamp` (last 10 warnings)
5. **Key deployments** — Check status of: neo4j, event-trader, edge-writer, report-enricher, chromadb-server
6. **PVC status** — `kubectl get pvc` to check persistent volume claims (especially neo4j data)

## Output Format

Return a concise health summary:

```
Cluster Health: OK / DEGRADED / DOWN
Pods: X/Y running
Restarts: [list any with restarts > 0]
Warnings: [recent warning events]
Storage: [PVC status]
```

Flag anything that needs attention.
