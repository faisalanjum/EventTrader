# CLAUDE.md - EventMarketDB Kubernetes Cluster Reference

## 4. Kubernetes Cluster Info (🔒 Reference Only)

### Node Details

#### Physical Nodes
- **minisforum** (Control Plane)
  - IP: `192.168.40.73`
  - Role: control-plane
  - CPU: 16 cores (Intel-based)
  - RAM: ~62 GB (60.3 GB allocatable)
  - Storage: ~960 GB SSD
  - Taints: `dedicated=graph:NoSchedule`, `node-role.kubernetes.io/control-plane:NoSchedule`
  - Purpose: Kubernetes control plane and graph workloads only

- **minisforum2** (Primary Worker)
  - IP: `192.168.40.72`
  - Role: worker
  - CPU: 16 cores (Intel-based)
  - RAM: ~62 GB (63.4 GB allocatable)
  - Storage: ~960 GB SSD
  - Taints: None
  - Purpose: Main worker node for application pods

- **minisforum3** (Database Node)
  - IP: `192.168.40.74`
  - Role: database
  - CPU: 16 cores (Intel-based)
  - RAM: ~126 GB (129.5 GB allocatable)
  - Storage: ~1.9 TB SSD
  - Taints: `database=neo4j:NoSchedule`
  - Purpose: Dedicated Neo4j database node

#### OS and Runtime
- **Operating System**: Ubuntu 22.04.5 LTS
- **Kernel**: 5.15.0-xxx-generic (varies by node)
- **Container Runtime**: containerd v1.7.27
- **Kubernetes Version**: v1.30.12
- **Network Plugin**: Flannel
- **Additional Services**: 
  - Tailscale (for secure remote access)
  - UFW disabled (Kubernetes manages iptables)
  - Swap disabled on all nodes
  - ulimits configured for high file descriptors

### Pod Information

#### Processing Namespace (Main Application Pods)

- **event-trader**
  - Purpose: Main event trading application that fetches SEC filings and market data
  - Image: `faisalanjum/event-trader:latest`
  - Resources: Requests: 500m CPU, 8Gi memory | Limits: 2 CPU, 16Gi memory
  - Runs on: minisforum2 (nodeSelector enforced)
  - Logging: 
    - Uses centralized `log_config.py`
    - Writes to `/app/logs` (mounted to host `/home/faisal/EventMarketDB/logs`)
    - Daily rotation with format: `eventtrader_YYYYMMDD_minisforum2.log`
  - Scaling: Currently manual (replicas: 0-1)

- **xbrl-worker-heavy**
  - Purpose: Processes large XBRL documents (10-K forms)
  - Image: `faisalanjum/xbrl-worker:latest`
  - Resources: Requests: 2 CPU, 6Gi memory | Limits: 3 CPU, 8Gi memory
  - Runs on: minisforum2 or minisforum (NOT minisforum3)
  - Logging: Daily files like `xbrl-heavy_YYYYMMDD_minisforum2.log`
  - Scaling: KEDA autoscaler (0-4 replicas) based on Redis queue `reports:queues:xbrl:heavy`
  - Scale trigger: Queue length ≥ 1, target length 2

- **xbrl-worker-medium**
  - Purpose: Processes medium XBRL documents (10-Q forms)
  - Image: `faisalanjum/xbrl-worker:latest`
  - Resources: Requests: 1.5 CPU, 3Gi memory | Limits: 2 CPU, 4Gi memory
  - Runs on: minisforum2 or minisforum (NOT minisforum3)
  - Logging: Daily files like `xbrl-medium_YYYYMMDD_minisforum2.log`
  - Scaling: KEDA autoscaler (0-6 replicas) based on Redis queue `reports:queues:xbrl:medium`
  - Scale trigger: Queue length ≥ 1, target length 5

- **xbrl-worker-light**
  - Purpose: Processes small XBRL documents (8-K, other forms)
  - Image: `faisalanjum/xbrl-worker:latest`
  - Resources: Requests: 1 CPU, 1.5Gi memory | Limits: 1.5 CPU, 2Gi memory
  - Runs on: minisforum2 or minisforum (NOT minisforum3)
  - Logging: Daily files like `xbrl-light_YYYYMMDD_minisforum2.log`
  - Scaling: KEDA autoscaler (0-10 replicas) based on Redis queue `reports:queues:xbrl:light`
  - Scale trigger: Queue length ≥ 1, target length 20

- **report-enricher**
  - Purpose: Enriches SEC reports with sections, exhibits, and metadata
  - Image: `faisalanjum/report-enricher:latest`
  - Resources: Requests: 500m CPU, 2Gi memory | Limits: 2 CPU, 8Gi memory
  - Runs on: Any node (preferably spread across nodes)
  - Logging: Daily files like `enricher_YYYYMMDD_minisforum2.log`
  - Scaling: KEDA autoscaler (0-15 replicas) based on Redis queue `reports:queues:enrich`
  - Scale trigger: Queue length ≥ 1, target length 5

#### Infrastructure Namespace

- **redis**
  - Purpose: Message queuing and caching
  - NodePort: 31379 (external access)
  - Storage: 40Gi PVC
  - Runs on: minisforum2

- **nats-0**
  - Purpose: Message streaming (for MCP services)
  - Runs on: minisforum2

#### Neo4j Namespace

- **neo4j-0**
  - Purpose: Graph database for financial data
  - Resources: Large allocation (uses most of minisforum3)
  - Storage: 
    - Data: 1.5TB PVC
    - Logs: 50GB PVC
  - NodePort Services:
    - Bolt: 30687 (database connections)
    - HTTP: 30474 (browser interface)
  - Runs on: minisforum3 ONLY (local-path-minisforum3 storage class)

#### Monitoring Namespace

- **prometheus** stack (operator, server, alertmanager)
- **grafana** (NodePort 32000 for web UI)
- **loki** (log aggregation, 50Gi storage)
- **node-exporter** (runs on all nodes)

#### KEDA Namespace

- **keda-operator**: Manages autoscaling
- **keda-metrics-apiserver**: Provides metrics
- **keda-admission-webhooks**: Validates configurations

### Networking

#### Services and External Access
- **Redis**: NodePort 31379 → Internal 6379
- **Neo4j Bolt**: NodePort 30687 → Internal 7687
- **Neo4j Browser**: NodePort 30474 → Internal 7474
- **Grafana**: NodePort 32000 → Internal 80
- **All other services**: ClusterIP (internal only)

#### Pod Network
- Flannel CNI with pod CIDR 10.244.0.0/16
- No fixed pod IPs (uses Kubernetes DNS)
- Service discovery via DNS (e.g., `redis.infrastructure.svc.cluster.local`)

### Lifecycle Behavior

#### Autoscaling Rules (KEDA)
All autoscaling uses Redis list length as the trigger:

- **report-enricher**: 
  - Queue: `reports:queues:enrich`
  - Formula: `desiredReplicas = ceil(queueLength / targetLength)` where targetLength=5
  - Example: 25 items in queue = 5 pods, 31 items = 7 pods
  - Min: 0, Max: 15, Cooldown: 60s
  - Activation: Scales from 0→1 when queue length ≥ 1
  - ScaledObject: `report-enricher-scaler`

- **xbrl-worker-heavy**: 
  - Queue: `reports:queues:xbrl:heavy`
  - Formula: `desiredReplicas = ceil(queueLength / 2)`
  - Example: 5 items = 3 pods, 8 items = 4 pods (max)
  - Min: 0, Max: 4, Cooldown: 300s (5 min)
  - Activation: Scales from 0→1 when queue length ≥ 1
  - ScaledObject: `xbrl-worker-heavy-scaler`
  - Memory intensive: Each pod can handle ~8GB documents

- **xbrl-worker-medium**: 
  - Queue: `reports:queues:xbrl:medium`
  - Formula: `desiredReplicas = ceil(queueLength / 5)`
  - Example: 10 items = 2 pods, 25 items = 5 pods
  - Min: 0, Max: 6, Cooldown: 180s (3 min)
  - Activation: Scales from 0→1 when queue length ≥ 1
  - ScaledObject: `xbrl-worker-medium-scaler`
  - Memory moderate: Each pod can handle ~4GB documents

- **xbrl-worker-light**: 
  - Queue: `reports:queues:xbrl:light`
  - Formula: `desiredReplicas = ceil(queueLength / 20)`
  - Example: 30 items = 2 pods, 100 items = 5 pods
  - Min: 0, Max: 10, Cooldown: 120s (2 min)
  - Activation: Scales from 0→1 when queue length ≥ 1
  - ScaledObject: `xbrl-worker-light-scaler`
  - Memory light: Each pod can handle ~2GB documents

#### Startup Dependencies
1. Infrastructure (Redis, NATS) must be running first
2. Neo4j should be ready before processing pods
3. KEDA operator must be running for autoscaling
4. No strict ordering between worker types

### Volumes and Persistence

#### Persistent Volume Claims
- **Neo4j Data**: 1.5TB on minisforum3 (`/var/lib/rancher/k3s/storage/` host path)
- **Neo4j Logs**: 50GB on minisforum3
- **Redis**: 40GB on minisforum2
- **Prometheus**: 100GB for metrics
- **Loki**: 50GB for logs

#### Host Path Mounts
- **Application Logs**: `/home/faisal/EventMarketDB/logs` (mounted to `/app/logs` in pods)
  - Used by all processing pods
  - Daily rotation with logrotate
  - Uses `copytruncate` to handle open file handles

### Logging Architecture

#### Centralized Logging System (`utils/log_config.py`)
The entire EventMarketDB system uses a centralized logging configuration that ensures consistent log handling across all components.

**Key Features**:
- **Process-safe file locking**: Uses `fcntl` for coordination between multiple processes
- **Daily rotation**: Automatic daily log files with format `{prefix}_YYYYMMDD_{hostname}.log`
- **Node-aware naming**: Uses `NODE_NAME` environment variable (Kubernetes) or `os.uname().nodename` (local)
- **Forced path support**: Allows specific log paths for chunked historical processing
- **Lock file mechanism**: `/home/faisal/EventMarketDB/logs/.logging_lock` coordinates log file selection
- **Fallback handling**: Creates unique fallback logs if lock contention occurs

**Log Level Configuration**:
- Controlled by `config.feature_flags.GLOBAL_LOG_LEVEL` (default: "INFO")
- Options: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"

#### Component-Specific Logging

##### 1. Historical Processing (Chunked - Local)
- **Execution**: Runs locally on minisforum (control node) via `./scripts/et chunked-historical`
- **Log Structure**:
  ```
  /home/faisal/EventMarketDB/logs/ChunkHist_{FROM}_to_{TO}_{TIMESTAMP}/
  ├── combined_{FROM}_to_{TO}.log      # Main combined log
  ├── chunk_{date1}_to_{date2}.log     # Individual chunk logs
  ├── chunk_{date3}_to_{date4}.log
  └── summary.txt                       # Processing summary
  ```
- **Implementation**:
  - Shell script creates folder structure
  - Passes specific log path via `--log-file` parameter
  - Python uses `force_path` in `setup_logging()` to write to exact location
  - Both shell logs and Python logs go to same file

##### 2. Live Processing (event-trader pod)
- **Execution**: Kubernetes pod on minisforum2 (nodeSelector enforced)
- **Log Files**: 
  - Primary: `event_trader_YYYYMMDD_minisforum2.log`
  - Alternative: `eventtrader_YYYYMMDD_minisforum2.log` (without underscore)
- **Implementation**:
  - Calls `setup_logging(name="event_trader")`
  - Mounts host path: `/home/faisal/EventMarketDB/logs` → `/app/logs`
  - Uses injected `NODE_NAME` for actual node identification

##### 3. XBRL Workers (3 types)
- **Execution**: Kubernetes pods on minisforum2 or minisforum (NOT minisforum3)
- **Log Files**:
  - Heavy: `xbrl-heavy_YYYYMMDD_{node}.log` (for 10-K forms)
  - Medium: `xbrl-medium_YYYYMMDD_{node}.log` (for 10-Q forms)
  - Light: `xbrl-light_YYYYMMDD_{node}.log` (for 8-K, other forms)
- **Implementation**:
  - Queue type from `XBRL_QUEUE` environment variable determines log prefix
  - Entry point: `neograph/xbrl_worker_loop.py`
  - Dynamic log prefix selection based on queue name

##### 4. Report Enricher
- **Execution**: Kubernetes pods on any node (spreads via podAntiAffinity)
- **Log Files**: `enricher_YYYYMMDD_{node}.log`
- **Implementation**:
  - Entry point: `redisDB/report_enricher_pod.py` → `redisDB/report_enricher.py`
  - Calls `setup_logging(name="enricher")`
  - Logger includes process name suffix

#### Volume Mounting and Permissions
All Kubernetes pods use identical volume mounting:
```yaml
volumeMounts:
- name: logs
  mountPath: /app/logs
volumes:
- name: logs
  hostPath:
    path: /home/faisal/EventMarketDB/logs
    type: DirectoryOrCreate
```

#### Log Rotation Configuration
Managed by logrotate on all nodes (`/etc/logrotate.d/eventmarketdb`):
```
/home/faisal/EventMarketDB/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    copytruncate
    create 0644 faisal faisal
}
```
- **copytruncate**: Critical for handling open file handles
- **Setup script**: `scripts/setup-logging.sh` configures on all nodes

#### Environment Variables for Logging
- **NODE_NAME**: Injected via Kubernetes downward API
  ```yaml
  env:
  - name: NODE_NAME
    valueFrom:
      fieldRef:
        fieldPath: spec.nodeName
  ```
- **XBRL_QUEUE**: Determines log prefix for XBRL workers
- **PYTHONUNBUFFERED=1**: Ensures immediate log output (report-enricher)

#### Log File Location Summary
| Component | Location | File Pattern | Node(s) |
|-----------|----------|--------------|---------|
| Historical (chunked) | `/home/faisal/EventMarketDB/logs/ChunkHist_*` | Multiple files per chunk | minisforum (local) |
| Live (event-trader) | `/home/faisal/EventMarketDB/logs/` | `event_trader_YYYYMMDD_{node}.log` | minisforum2 |
| XBRL Heavy | `/home/faisal/EventMarketDB/logs/` | `xbrl-heavy_YYYYMMDD_{node}.log` | minisforum2, minisforum |
| XBRL Medium | `/home/faisal/EventMarketDB/logs/` | `xbrl-medium_YYYYMMDD_{node}.log` | minisforum2, minisforum |
| XBRL Light | `/home/faisal/EventMarketDB/logs/` | `xbrl-light_YYYYMMDD_{node}.log` | minisforum2, minisforum |
| Report Enricher | `/home/faisal/EventMarketDB/logs/` | `enricher_YYYYMMDD_{node}.log` | Any node |

#### Critical Implementation Notes
1. **File Locking**: The centralized `log_config.py` uses file locking to ensure multiple processes can safely write to the same log file
2. **Node Identification**: Always uses actual node name (not pod name) for log file naming
3. **Force Path**: Historical processing bypasses normal log file discovery and uses explicit paths
4. **Daily Files**: New log file created each day at midnight based on system time
5. **Process Safety**: Lock file prevents race conditions during simultaneous process starts

### Processing Modes: Historical vs Live

#### Historical Processing (Local)
- **Command**: `./scripts/et chunked-historical start_date end_date`
- **Runs on**: minisforum (control node) locally, NOT in Kubernetes
- **Purpose**: Backfill historical SEC filings for specific date ranges
- **Process**: 
  - Splits date range into 5-day chunks
  - Runs each chunk sequentially
  - Creates dedicated log folders: `/home/faisal/EventMarketDB/logs/ChunkHist_<dates>_<timestamp>/`
  - Uses Redis prefix `reports:hist:` for data separation
- **Helper Pods Used**: 
  - SAME xbrl-worker pods (heavy/medium/light)
  - SAME report-enricher pods
  - Workers don't know if processing historical or live data
  - Queue items contain metadata to preserve data separation

#### Live Processing (Pod)
- **Deployment**: `event-trader` pod in Kubernetes
- **Command**: Runs with `-live` flag
- **Purpose**: Real-time processing of new SEC filings
- **Process**:
  - Continuously polls SEC EDGAR for new filings
  - Uses Redis prefix `reports:live:` for data separation
  - Logs to mounted volume: `eventtrader_YYYYMMDD_minisforum2.log`
- **Helper Pods Used**: Same workers as historical (shared queues)

#### Key Differences
1. **Execution Environment**:
   - Historical: Local Python process on control node
   - Live: Containerized pod on minisforum2

2. **Data Separation**:
   - Different Redis key prefixes (`hist:` vs `live:`)
   - Metadata preserved through processing pipeline
   - Final data in Neo4j maintains separation

3. **Resource Usage**:
   - Historical: Can use full control node resources
   - Live: Limited by pod resource constraints

4. **Scaling**:
   - Historical: Single process, no scaling
   - Live: Could scale to multiple replicas (currently 0-1)

### Transition History

#### Before Kubernetes (Python Multiprocessing)
- **Report Enricher**: Used `multiprocessing.Pool` with 15 workers locally
- **XBRL Processing**: ThreadPoolExecutor with semaphore limiting
- **Issues**: 
  - Memory pressure on single host
  - Difficult to scale
  - Resource contention between historical and live
  - Complex process management
  - Workers competed for same system resources

#### After Migration to Kubernetes
- **Report Enricher**: Migrated to Redis queue + KEDA pods (Jan 2025)
- **XBRL Workers**: Migrated to 3-tier queue system + KEDA (Jan 2025)
- **Benefits**:
  - Dynamic scaling based on workload
  - Better resource isolation
  - Distributed across nodes
  - Automatic recovery from failures
  - Clear resource limits prevent OOM
  - Horizontal scaling instead of vertical
  - Historical and live processing share worker infrastructure
  - No resource competition between processing modes

### Operational Commands for Bots

#### Checking Pod Status
```bash
# View all processing pods
kubectl get pods -n processing

# Check specific worker type
kubectl get pods -n processing -l app=xbrl-worker-heavy

# View pod resource usage
kubectl top pods -n processing
```

#### Scaling Operations
```bash
# Manual scaling (overrides KEDA temporarily)
kubectl scale deployment xbrl-worker-heavy -n processing --replicas=2

# Check KEDA scalers
kubectl get scaledobjects -n processing

# View scaling events
kubectl describe scaledobject xbrl-worker-heavy-scaler -n processing
```

#### Queue Monitoring
```bash
# Check queue lengths (from any pod with redis-cli)
kubectl exec -it redis-77f84c44fd-4h4w4 -n infrastructure -- redis-cli
> LLEN reports:queues:xbrl:heavy
> LLEN reports:queues:xbrl:medium
> LLEN reports:queues:xbrl:light
> LLEN reports:queues:enrich
```

#### Resource Capacity Check
- **minisforum2 capacity**: 16 CPU, 63GB RAM
- **Current allocations when all max replicas**:
  - xbrl-heavy: 4 pods × 2 CPU = 8 CPU, 4 × 6Gi = 24Gi RAM
  - xbrl-medium: 6 pods × 1.5 CPU = 9 CPU, 6 × 3Gi = 18Gi RAM
  - xbrl-light: 10 pods × 1 CPU = 10 CPU, 10 × 1.5Gi = 15Gi RAM
  - report-enricher: 15 pods × 0.5 CPU = 7.5 CPU, 15 × 2Gi = 30Gi RAM
  - **Total at max**: 34.5 CPU (216% overcommit), 87Gi RAM (137% overcommit)
  - **Note**: Not all pods can run at max simultaneously

### Naming and Conventions

#### Deployment Operations
```bash
# Deploy single component
./scripts/deploy.sh xbrl-worker
./scripts/deploy.sh report-enricher
./scripts/deploy.sh event-trader

# Deploy all components
./scripts/deploy-all.sh

# Rollout restart (picks up new images)
kubectl rollout restart deployment/xbrl-worker-heavy -n processing
kubectl rollout restart deployment/xbrl-worker-medium -n processing
kubectl rollout restart deployment/xbrl-worker-light -n processing
```

#### Environment Variables (Auto-injected)
- `XBRL_QUEUE`: Queue name for XBRL workers (e.g., `reports:queues:xbrl:heavy`)
- `NODE_NAME`: Kubernetes node name (for logging)
- `NEO4J_URI`: `bolt://neo4j-bolt.neo4j:7687`
- `NEO4J_USERNAME`, `NEO4J_PASSWORD`: From eventtrader-secrets
- `REDIS_HOST`, `REDIS_PORT`: From eventtrader-secrets

#### Pod Naming
- Format: `{deployment-name}-{replicaset-hash}-{random}`
- Examples: 
  - `xbrl-worker-heavy-65875bd657-pwgmh`
  - `report-enricher-cd5b5b69d-cdsj4`

#### Image Naming
- Registry: Docker Hub (`faisalanjum/`)
- Tags: Always `latest` (rolling updates)
- Images:
  - `faisalanjum/event-trader:latest`
  - `faisalanjum/xbrl-worker:latest`
  - `faisalanjum/report-enricher:latest`

#### Labels and Annotations
- Standard labels: `app`, `worker-type`
- KEDA uses: `scaledobject.keda.sh/name`
- Node selectors: `kubernetes.io/hostname`

#### Service Discovery
- Pattern: `{service}.{namespace}.svc.cluster.local`
- Example: `redis.infrastructure.svc.cluster.local:6379`

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

### Critical Don'ts (⚠️ Do NOT Change Unless Explicitly Asked)

1. **Neo4j Configuration**
   - Do NOT modify StatefulSet scaling (must remain 1 replica)
   - Do NOT change storage class from `local-path-minisforum3`
   - Do NOT remove node affinity to minisforum3
   - Do NOT modify memory settings without careful planning

2. **Persistent Volumes**
   - Do NOT delete PVCs (data loss!)
   - Do NOT change reclaim policy on production PVs
   - Do NOT move Neo4j data to different node

3. **Node Taints**
   - Do NOT remove `database=neo4j:NoSchedule` from minisforum3
   - Do NOT schedule application pods on minisforum3

4. **Resource Limits**
   - Do NOT remove resource limits (can crash nodes)
   - Do NOT overcommit memory beyond node capacity
   - Do NOT increase max replicas without checking node capacity

5. **Networking**
   - Do NOT change NodePort numbers (external dependencies)
   - Do NOT modify service names (breaks DNS)
   - Do NOT expose internal services without security review

6. **Logging**
   - Do NOT change log directory paths
   - Do NOT disable logrotate
   - Do NOT modify `NODE_NAME` environment injection

7. **KEDA Autoscaling**
   - Do NOT set minReplicas > 0 for workers (wastes resources)
   - Do NOT remove activation thresholds
   - Do NOT set cooldown periods too low (causes flapping)