---
description: "Check Kubernetes cluster health for EventMarketDB: pod status, restarts, resource usage, KEDA autoscalers, recent events, and PVCs."
tools:
  - Bash
  - Read
---

Check the Kubernetes cluster health for EventMarketDB workloads.

## Cluster topology (verified 2026-04-24)

**3 nodes**, K8s v1.30.12, containerd runtime:
- `minisforum` — control-plane (192.168.40.73)
- `minisforum2` — worker (192.168.40.72)
- `minisforum3` — `database` role label, hosts Neo4j PVCs (192.168.40.74)

**Active app namespaces:** `processing`, `neo4j`, `mcp-services`, `infrastructure`, `monitoring`, `keda`.
The `default` namespace is empty. There is **no** `eventtrader` namespace and **no** `chromadb-server` deployment.

## Steps

### 1. Pod status across app namespaces
```
kubectl get pods -A -o wide \
  --field-selector=metadata.namespace!=kube-system,metadata.namespace!=kube-flannel,metadata.namespace!=local-path-storage
```
Or per-namespace if a deeper look is needed:
```
kubectl get pods -n processing -o wide
kubectl get pods -n neo4j -o wide
kubectl get pods -n mcp-services -o wide
kubectl get pods -n infrastructure -o wide
kubectl get pods -n monitoring -o wide
```

### 2. Restart counts (across all namespaces)
```
kubectl get pods -A -o jsonpath='{range .items[?(@.status.containerStatuses[0].restartCount>0)]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.status.containerStatuses[0].restartCount}{"\n"}{end}' | sort -k3 -n -r | head -20
```
**Baseline:** Many control-plane and infra pods carry historical restart counts from past node reboots (etcd, kube-controller-manager, KEDA, flannel etc. — typical "X (85d ago)" or "(13d ago)"). Only flag restarts whose `Last State` shows recent termination (`kubectl describe pod <name>`).

### 3. Resource usage
```
kubectl top nodes
kubectl top pods -A --sort-by=memory | head -20
kubectl top pods -A --sort-by=cpu    | head -20
```

### 4. Recent warning events (cluster-wide)
```
kubectl get events -A --field-selector type=Warning --sort-by=.lastTimestamp 2>&1 | tail -15
```

### 5. Key workloads to verify

**`processing` namespace (EventMarketDB pipeline):**

| Workload | Kind | Expected replicas | Notes |
|---|---|---|---|
| `edge-writer` | Deployment | 1/1 | Always-on Neo4j writer |
| `report-enricher` | Deployment | 1–5 (KEDA) | `report-enricher-scaler`, redis trigger |
| `xbrl-worker-heavy` | Deployment | 3 (KEDA, fixed) | `xbrl-worker-heavy-scaler`, redis trigger. **Temp bumped 2→3 until queues drain (see MEMORY.md)** |
| `xbrl-worker-medium` | Deployment | 2–4 (KEDA) | `xbrl-worker-medium-scaler`, redis trigger. **Temp max 3→4** |
| `extraction-worker` | Deployment | 0–7 (KEDA) | `extraction-worker-scaler`, scales from zero on `extract:pipeline` Redis list |
| `event-trader` | Deployment | **0/0 by design** | Replicas held at 0; invoked out-of-band — not an outage |
| `guidance-trigger` | Deployment | **0/0 by design** | KEDA-scaled trigger pod; 0 when idle is normal |
| `trade-ready-morning/midday/close/evening` | CronJob | n/a | `0 7,12,16:30,21 * * 0-5` America/New_York. Check for recent `Completed` job pods |

```
kubectl get deploy -n processing
kubectl get scaledobjects -n processing
kubectl get cronjobs -n processing
kubectl get pods -n processing --field-selector=status.phase!=Running,status.phase!=Succeeded
```

**`neo4j` namespace:**
```
kubectl get statefulset -n neo4j        # neo4j 1/1
kubectl get pod neo4j-0 -n neo4j -o wide
```
Neo4j is a **StatefulSet** (not Deployment), single pod `neo4j-0`, pinned to `minisforum3`. Disk check:
```
kubectl exec -n neo4j neo4j-0 -- df -h /data
```

**`mcp-services` namespace:**
```
kubectl get deploy -n mcp-services
```
Expected (all 1/1): `ibkr`, `ibkr-ib-gateway`, `ibkr-paper`, `ibkr-paper-gateway`, `mcp-neo4j-cypher-http`, `mcp-yahoo-finance`.

**`infrastructure` namespace:**
```
kubectl get pods -n infrastructure
```
Expected: `nats-0` (StatefulSet, 2/2), `nats-box-*` (1/1), `redis-*` (1/1).

**`monitoring` namespace:**
```
kubectl get pods -n monitoring
```
Expected always-on: `prometheus-grafana` (3/3), `prometheus-kube-prometheus-operator`, `prometheus-kube-state-metrics`, `alertmanager-prometheus-kube-prometheus-alertmanager-0` (2/2), `loki-0`, `prometheus-prometheus-kube-prometheus-prometheus-0` (2/2), `loki-promtail-*` (DaemonSet, 1 replica on minisforum2 only), `prometheus-prometheus-node-exporter-*` (DaemonSet, 3 replicas).

### 6. KEDA autoscaler health
```
kubectl get scaledobjects -A
```
Expected entries (all in `processing`):
- `extraction-worker-scaler` — 0..7, redis (`extract:pipeline`)
- `report-enricher-scaler` — 1..5, redis
- `xbrl-worker-heavy-scaler` — 3..3, redis (`reports:queues:xbrl:heavy`)
- `xbrl-worker-medium-scaler` — 2..4, redis (`reports:queues:xbrl:medium`)

`READY=True` and `FALLBACK=False` are healthy. `ACTIVE=Unknown` is acceptable for zero-scaled deployments idle.

### 7. PVC status
```
kubectl get pvc -A
```
Expected `Bound` PVCs:
| Namespace | PVC | Size | StorageClass |
|---|---|---|---|
| `neo4j` | `data-neo4j-0` | 1536Gi | `local-path-minisforum3` |
| `neo4j` | `logs-neo4j-0` | 50Gi | `local-path-minisforum3` |
| `infrastructure` | `redis-pvc` | 40Gi | `local-path` |
| `monitoring` | `prometheus-...-prometheus-0` | 100Gi | `local-path` |
| `monitoring` | `storage-loki-0` | 50Gi | `local-path` |
| `mcp-services` | `ibkr-live-jts-home` | 1Gi | `local-path` |

Any `Pending` PVC is a problem.

### 8. NodePort exposure (sanity)
| Service | Port | Purpose |
|---|---|---|
| `monitoring/prometheus-grafana` | 32000 | Grafana UI |
| `neo4j/neo4j-bolt` | 30687 | Bolt protocol |
| `neo4j/neo4j-http` | 30474 | Neo4j Browser |
| `infrastructure/redis` | 31379 | Redis (queues) |
| `mcp-services/ibkr` | 31100 | IBKR live MCP |
| `mcp-services/ibkr-paper` | 31101 | IBKR paper MCP |

```
kubectl get svc -A | grep NodePort
```

## Output Format

```
Cluster Health: OK / DEGRADED / DOWN
Nodes: 3/3 Ready (minisforum, minisforum2, minisforum3)
Pods: <running>/<total> across app namespaces
Processing pipeline:
  edge-writer        : 1/1
  report-enricher    : <n>/<max> (KEDA)
  xbrl-heavy         : 3/3
  xbrl-medium        : <n>/4 (KEDA)
  extraction-worker  : <n>/7 (KEDA, 0 = idle, OK)
  event-trader       : 0/0 (intentional, OK)
  guidance-trigger   : 0/0 (intentional, OK)
Neo4j           : neo4j-0 Running on minisforum3, disk <used>/<total>
MCP services    : 6/6 deployments healthy
Infrastructure  : redis OK, nats OK
KEDA scalers    : 4/4 Ready
Recent restarts (non-baseline): [list]
Warning events  : [count + summaries]
PVCs            : 6/6 Bound
NodePorts       : reachable / unreachable
```

Flag anything outside expected baseline. Do **not** flag:
- `event-trader 0/0` or `guidance-trigger 0/0` (intentional)
- `extraction-worker 0` (KEDA idle)
- Long-running historical restart counts dated `(85d ago)` / `(13d ago)` (past node reboots)
- `Completed` CronJob pods from `trade-ready-*`
