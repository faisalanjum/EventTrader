# CLAUDE.md - EventMarketDB Kubernetes Cluster Reference

## 4. Kubernetes Cluster Infrastructure

### Physical Nodes
| Node | IP | Role | CPU | RAM | Storage | Taints | Purpose |
|------|-----|------|-----|-----|---------|--------|---------|
| **minisforum** | 192.168.40.73 | control-plane | 16 cores | 62GB (60.3GB alloc) | 960GB SSD | `dedicated=graph:NoSchedule`<br>`node-role.kubernetes.io/control-plane:NoSchedule` | K8s control plane, graph workloads |
| **minisforum2** | 192.168.40.72 | worker | 16 cores | 62GB (63.4GB alloc) | 960GB SSD | None | Main worker for app pods |
| **minisforum3** | 192.168.40.74 | database | 16 cores | 126GB (129.5GB alloc) | 1.9TB SSD | `database=neo4j:NoSchedule` | Dedicated Neo4j only |

**Platform**: Ubuntu 22.04.5 LTS, containerd v1.7.27, Kubernetes v1.30.12, Flannel CNI

### Pods by Namespace

#### Processing Namespace
| Pod | Purpose | Resources (Req/Limit) | Runs On | Scaling | Log Pattern |
|-----|---------|----------------------|---------|---------|-------------|
| **event-trader** | Fetches SEC filings & market data | 500m/2 CPU, 8Gi/16Gi RAM | minisforum2 | Manual: 0-1 | `event_trader_YYYYMMDD_{node}.log` |

| **xbrl-worker-heavy** | 10-K forms (8GB docs) | 2/3 CPU, 6Gi/8Gi RAM | minisforum/2 | KEDA: 1-2, queue/2 | `xbrl-heavy_YYYYMMDD_{node}.log` |
| **xbrl-worker-medium** | 10-Q forms (4GB docs) | 1.5/2 CPU, 3Gi/4Gi RAM | minisforum/2 | KEDA: 1-3, queue/5 | `xbrl-medium_YYYYMMDD_{node}.log` |
| **xbrl-worker-light** | 8-K forms (2GB docs) | 1/1.5 CPU, 1.5Gi/2Gi RAM | minisforum/2 | KEDA: 1-4, queue/20 | `xbrl-light_YYYYMMDD_{node}.log` |

| **report-enricher** | Enriches reports metadata | 500m/2 CPU, 2Gi/8Gi RAM | Any node | KEDA: 0-15, queue/5 | `enricher_YYYYMMDD_{node}.log` |
| **edge-writer** | Single-writer for Neo4j relationships<br>9-10k relationships/sec | 500m/1 CPU, 1Gi/2Gi RAM | Any node | Fixed: 1 (singleton) | `edge_writer_YYYYMMDD_{node}.log` |

**Note**: All processing pods use `faisalanjum/{name}:latest` images. XBRL workers NEVER run on minisforum3.

#### Infrastructure Namespace
| Service | Purpose | Access | Storage | Node |
|---------|---------|--------|---------|------|
| **redis** | Message queuing & caching | NodePort 31379 | 40Gi PVC | minisforum2 |
| **nats-0** | Message streaming | Internal only | - | minisforum3 |

#### Neo4j Namespace
**neo4j-0** (StatefulSet) - Graph database for financial data
- **Resources**: 90Gi RAM (req/limit), 8/16 CPU (req/limit)
- **Memory Config**: Heap 24G, Page Cache 56G, Transaction 4G/tx max
- **Storage**: 1.5TB data PVC, 50GB logs PVC  
- **Access**: Bolt NodePort 30687, HTTP NodePort 30474
- **Node**: minisforum3 ONLY (local-path-minisforum3)
- **Planned Memory Increase**: 90→100Gi pod, 24→26G heap, 56→68G cache
  - Patch file: `/home/faisal/EventMarketDB/k8s/neo4j-memory-increase-patch.yaml`

#### Other Namespaces
- **Monitoring**: Prometheus stack, Grafana (NodePort 32000), Loki (50Gi), node-exporter
- **KEDA**: Operator, metrics API server, admission webhooks

#### MCP Services Namespace
| Pod | Purpose | Resources | Access | Known Issue |
|-----|---------|-----------|--------|-------------|
| **mcp-neo4j-cypher** | Claude Desktop Cypher queries | 100m/250m CPU, 256Mi/512Mi RAM | Internal | DNS fails on restart |
| **mcp-neo4j-memory** | Claude Desktop memory ops (async) | 100m/250m CPU, 512Mi/1Gi RAM | Internal | DNS fails on restart |
| **mcp-neo4j-cypher-http** | LangGraph/LangChain HTTP API | 100m/250m CPU, 256Mi/512Mi RAM | NodePort 31380 | DNS fails on restart |

**Note**: All use `python:3.11-slim`, install packages at runtime, run on minisforum only

### Networking

#### External Access (NodePorts)
| Service | External Port | Internal Port | Purpose |
|---------|--------------|---------------|----------|
| Redis | 31379 | 6379 | Queue/cache access |
| MCP HTTP | 31380 | 8000 | LangGraph/LangChain API |
| Neo4j Bolt | 30687 | 7687 | Database connections |
| Neo4j Browser | 30474 | 7474 | Web UI |
| Grafana | 32000 | 80 | Monitoring UI |

**Internal**: Flannel CNI (10.244.0.0/16), DNS-based service discovery

### KEDA Autoscaling

| Deployment | Queue | Formula | Min-Max | Cooldown | Notes |
|------------|-------|---------|---------|----------|-------|
| report-enricher | `reports:queues:enrich` | ceil(queue/5) | 0-15 | 60s | Scales from 0 |
| xbrl-worker-heavy | `reports:queues:xbrl:heavy` | ceil(queue/2) | 1-2 | 300s | 8GB docs |
| xbrl-worker-medium | `reports:queues:xbrl:medium` | ceil(queue/5) | 1-3 | 180s | 4GB docs |
| xbrl-worker-light | `reports:queues:xbrl:light` | ceil(queue/20) | 1-4 | 120s | 2GB docs |

**Startup Order**: Infrastructure → Neo4j → KEDA → Processing pods

### Storage

#### Persistent Volumes
| Service | Size | Node | Path |
|---------|------|------|------|
| Neo4j Data | 1.5TB | minisforum3 | `/var/lib/rancher/k3s/storage/` |
| Neo4j Logs | 50GB | minisforum3 | - |
| Redis | 40GB | minisforum2 | - |
| Prometheus | 100GB | - | - |
| Loki | 50GB | - | - |

**Host Mount**: `/home/faisal/EventMarketDB/logs` → `/app/logs` (all processing pods)

### Logging System

**Centralized via `utils/log_config.py`**:
- Process-safe file locking with `fcntl`
- Daily rotation: `{prefix}_YYYYMMDD_{node}.log`
- Lock file: `/home/faisal/EventMarketDB/logs/.logging_lock`
- Log level: `config.feature_flags.GLOBAL_LOG_LEVEL` (default: INFO)

#### Log Files by Component
| Component | Pattern | Location | Notes |
|-----------|---------|----------|-------|
| Historical | `ChunkHist_{FROM}_to_{TO}_{TIMESTAMP}/` | `/home/faisal/EventMarketDB/logs/` | Local on minisforum |
| Live | `event_trader_YYYYMMDD_{node}.log` | `/home/faisal/EventMarketDB/logs/` | Pod on minisforum2 |
| XBRL Workers | `xbrl-{type}_YYYYMMDD_{node}.log` | `/home/faisal/EventMarketDB/logs/` | Pods on minisforum/2 |
| Report Enricher | `enricher_YYYYMMDD_{node}.log` | `/home/faisal/EventMarketDB/logs/` | Pods on any node |
| MCP Services | stdout/stderr only | kubectl logs | minisforum pods |

**Logrotate**: Daily, 7 days retention, copytruncate, configured by `scripts/setup-logging.sh`

### Processing Modes

| Mode | Command/Deployment | Runs On | Memory | Redis Prefix | Notes |
|------|-------------------|---------|---------|--------------|-------|
| **Historical** | `./scripts/et chunked-historical start end` | minisforum local | 48GB | `reports:hist:` | 5-day chunks, sequential |
| **Live** | `event-trader` pod with `-live` flag | minisforum2 pod | 16GB limit | `reports:live:` | Continuous polling |

**Shared Infrastructure**: Both modes use same XBRL worker and enricher pods. Workers preserve metadata to maintain data separation.

### Migration History

**Pre-Kubernetes**: Python multiprocessing, ThreadPoolExecutor, single host limitations  
**Post-Kubernetes** (Jan 2025): Redis queues + KEDA autoscaling, distributed across nodes, horizontal scaling

### XBRL Processing

**Status Flow**: NULL → QUEUED → PROCESSING → COMPLETED/FAILED

**Queue Routing**:
- 10-K → `reports:queues:xbrl:heavy` (8GB docs)
- 10-Q → `reports:queues:xbrl:medium` (4GB docs)
- 8-K → `reports:queues:xbrl:light` (2GB docs)

**Neo4j Structure**: `(Report)-[:HAS_XBRL]->(XBRLNode)-[:HAS_FACT]->(Fact)`

**Key Files**:
- Entry: `neograph/mixins/report.py:474`
- Worker: `neograph/xbrl_worker_loop.py`
- Edge writer: Handles high-contention relationships (9-10k/sec)

**Feature Flags**: 
- `PRESERVE_XBRL_FAILED_STATUS=True`
- `ENABLE_KUBERNETES_XBRL=True`

### Common Operations

#### Pod Management
```bash
kubectl get pods -n processing                        # View all pods
kubectl top pods -n processing                        # Resource usage
kubectl scale deployment xbrl-worker-heavy -n processing --replicas=2  # Manual scale
```

#### Queue Monitoring
```bash
kubectl exec -it redis-* -n infrastructure -- redis-cli
> LLEN reports:queues:xbrl:heavy    # Check queue lengths
```

#### Resource Capacity (minisforum2)
- **Total**: 16 CPU, 63GB RAM
- **At max scale**: 16.5 CPU (103%), 52Gi RAM (82%)
- **Reduced 2025-01-13**: Heavy max 2, Medium max 3 pods

### Deployment & Naming

**Scripts**:
```bash
./scripts/deploy.sh {component}        # Single component
./scripts/deploy-all.sh                # All components
./scripts/deploy-mcp-http.sh           # MCP HTTP service
kubectl rollout restart deployment/{name} -n {namespace}  # Restart
```

**Conventions**:
- Images: `faisalanjum/{name}:latest` (except MCP uses `python:3.11-slim`)
- Pods: `{deployment}-{hash}-{random}`
- Service DNS: `{service}.{namespace}.svc.cluster.local`
- Auto-injected: `XBRL_QUEUE`, `NODE_NAME`, `NEO4J_*`, `REDIS_*`

---

## 5. Claude Operating Guidelines

These rules define how Claude must behave when performing any task in this repository. They are non-negotiable and must be followed precisely.

### ✅ 1. Clean Up After Yourself  
Always delete all intermediate, temporary, or generated files (e.g., test logs, debug outputs, temp YAMLs) after verifying task success. Leave the environment clean and uncluttered.

### 🔁 2. Ensure Idempotency  
All commands and scripts must be safe to re-run multiple times without causing unintended effects. This includes:
- No duplication of deployments, config, or data
- No accidental resets or state changes  
- No resource exhaustion or scaling errors

Before executing, always:
- Understand the full **business and code logic**
- Confirm system-wide safety and impact
- Avoid breaking any downstream process

### 🧪 3. Test Thoroughly  
Never assume a change works. Always:
- Run it end-to-end
- Check logs, system health, pod status, and outputs
- Validate functionality in production (no staging available)
- Be prepared to roll back safely

### 📝 4. Document All New Behavior  
If a change introduces new logic, structure, or runtime behavior:
- Update this `CLAUDE.md` if infrastructure or behavior guidance changes
- Update related documentation (`README.md`, `HowTo/*.md`, etc.)
- Nothing should be added silently

### ⛔ 5. Do Not Modify Critical Components Without Explicit Permission  
Never touch the following unless specifically instructed:
- Secrets or encrypted configs
- Persistent volume mounts (e.g., Redis, Neo4j data)
- kube-system resources or core networking
- Production ingress/egress rules
- Business-critical workloads

### 🎯 6. EventMarketDB-Specific Guidelines

#### Resource Management
- **ALWAYS check node capacity** before scaling:
  ```bash
  kubectl top nodes
  kubectl describe node minisforum2  # Primary worker node
  ```
- **NEVER schedule pods on minisforum3** (Neo4j dedicated)
- **Monitor resource usage** - cluster runs at 216% CPU overcommit

#### Queue & State Consistency
- **Check queue depths** before any changes:
  ```bash
  redis-cli LLEN reports:queues:xbrl:heavy
  redis-cli LLEN reports:queues:xbrl:medium
  redis-cli LLEN reports:queues:xbrl:light
  redis-cli LLEN reports:queues:enrich
  ```
- **Preserve metadata** through entire pipeline
- **Never mix** live and historical data prefixes
- **Respect processing order**: raw → processed → with/without returns

#### Financial Data Processing
- **Memory requirements are critical**:
  - 10-K forms: 8GB RAM per document
  - 10-Q forms: 4GB RAM per document  
  - 8-K forms: 2GB RAM per document
- **Never skip enrichment** - adds critical metadata
- **Validate** all financial data before processing

#### Production Deployment
- **No staging** - all changes go to production
- **Always use deployment scripts**:
  ```bash
  ./scripts/deploy.sh {component}     # Single component
  ./scripts/deploy-all.sh            # All components
  ```
- **Verify immediately** after deployment:
  ```bash
  kubectl get pods -n processing
  kubectl logs {pod-name} -n processing --tail=50
  ```
- **Check logs** at `/home/faisal/EventMarketDB/logs/`

#### Error Recovery
1. **Check pod logs first**
2. **Verify Redis connectivity** 
3. **Ensure Neo4j accessibility**
4. **Let KEDA handle scaling** - don't panic about restarts
5. **Rollback only if necessary**:
   ```bash
   kubectl rollout undo deployment/{name} -n processing
   ```

Claude must act conservatively, verify obsessively, and operate cleanly.

---

### MCP Integration

#### Three MCP Setups

1. **Claude Desktop (K8s Pods)**
   - Purpose: GUI app integration
   - Flow: Desktop → SSH → proxy script → kubectl exec → pods
   - Config: `~/.config/claude/claude_desktop_config.json`
   - Connection: Internal `bolt://neo4j-bolt.neo4j:7687`

2. **Claude CLI (Local)**
   - Purpose: CLI tool integration
   - Flow: CLI → bash scripts → local Python
   - Config: `/home/faisal/EventMarketDB/.mcp.json`
   - Connection: NodePort `bolt://localhost:30687`

3. **MCP HTTP (LangGraph/LangChain)**
   - Purpose: Programmatic API access
   - Service: NodePort 31380
   - Usage: `MultiServerMCPClient` with async tools

#### Claude CLI Setup
1. Create wrapper scripts in `/home/faisal/EventMarketDB/mcp_servers/`
2. Scripts set `NEO4J_URI=bolt://localhost:30687` and activate venv
3. Create `.mcp.json` pointing to wrapper scripts
4. Requires: `pip install mcp`, Neo4j at port 30687


#### MCP Recovery
**Known Issue**: DNS fails on node restart. Pods auto-restart with `set -e` fix.

**Key Files**:
- YAML: `/home/faisal/EventMarketDB/k8s/mcp-services/mcp-neo4j-cypher-http-deployment.yaml`
- Deploy: `./scripts/deploy-mcp-http.sh`
- Example: `/home/faisal/EventMarketDB/drivers/agenticDrivers/neo4j_mcp_simple_tools.ipynb`

### Critical Don'ts ⚠️

**Neo4j**: No scaling (1 replica), no storage class changes, no node moves  
**Volumes**: No PVC deletion, no reclaim policy changes  
**Nodes**: No minisforum3 app pods, respect taints  
**Resources**: Keep limits, check capacity before scaling  
**Network**: No NodePort/service name changes  
**Logging**: No path changes, keep logrotate  
**KEDA**: No minReplicas>0, respect cooldowns