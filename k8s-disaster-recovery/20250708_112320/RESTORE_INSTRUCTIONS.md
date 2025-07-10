# EventMarketDB Kubernetes Disaster Recovery

**CRITICAL**: This guide allows COMPLETE cluster restoration in under 5 minutes, even with ZERO prior knowledge.

## Prerequisites
- 3 Ubuntu 22.04 nodes with these EXACT IPs:
  - `192.168.40.73` (hostname: minisforum) - Control plane node
  - `192.168.40.72` (hostname: minisforum2) - Worker node  
  - `192.168.40.74` (hostname: minisforum3) - Database node
- K3s installed on all nodes (or any Kubernetes distribution)
- kubectl configured to access the cluster
- This backup folder extracted and accessible

## Quick Recovery (Under 5 Minutes)

### Option A: Automated Recovery (Recommended)
```bash
# Run this single command:
./quick-restore.sh

# Monitor progress:
watch kubectl get pods -A
```

### Option B: Manual Recovery Steps

#### 1. Apply Node Labels and Taints (30 seconds)
```bash
# CRITICAL: Apply node labels first
kubectl label node minisforum node-role.kubernetes.io/control-plane=true --overwrite
kubectl label node minisforum3 node-role.kubernetes.io/database=true --overwrite

# CRITICAL: Apply taints - DO NOT SKIP THIS!
kubectl taint nodes minisforum3 database=neo4j:NoSchedule --overwrite

# Note: No taints on minisforum or minisforum2 currently
```

#### 2. Create Namespaces (10 seconds)
```bash
kubectl create namespace processing
kubectl create namespace infrastructure
kubectl create namespace neo4j
kubectl create namespace monitoring
kubectl create namespace keda
kubectl create namespace mcp-services
```

#### 3. Restore Resources in Correct Order (3 minutes)

**IMPORTANT**: Order matters! Follow exactly:

```bash
# Step 1: Storage classes and persistent volumes
kubectl apply -f storage-classes.yaml
kubectl apply -f persistent-volumes.yaml

# Step 2: KEDA (must be before processing namespace)
kubectl apply -f keda/ --recursive

# Step 3: Core infrastructure
kubectl apply -f infrastructure/ --recursive

# Step 4: Neo4j database
kubectl apply -f neo4j/ --recursive

# Step 5: Wait for critical services (IMPORTANT!)
echo "Waiting for Redis..."
kubectl wait --for=condition=ready pod -l app=redis -n infrastructure --timeout=120s

echo "Waiting for Neo4j (this takes 2-3 minutes)..."
kubectl wait --for=condition=ready pod neo4j-0 -n neo4j --timeout=300s

# Step 6: Processing workloads
kubectl apply -f processing/ --recursive

# Step 7: Other services
kubectl apply -f mcp-services/ --recursive
kubectl apply -f monitoring/ --recursive
```

#### 4. Post-Restore Configuration (1 minute)

```bash
# Apply current XBRL worker restrictions (temporary for historical processing)
kubectl patch deployment xbrl-worker-heavy -n processing --type='json' -p='[{"op": "add", "path": "/spec/template/spec/affinity", "value": {"nodeAffinity": {"requiredDuringSchedulingIgnoredDuringExecution": {"nodeSelectorTerms": [{"matchExpressions": [{"key": "kubernetes.io/hostname", "operator": "NotIn", "values": ["minisforum"]}]}]}}}}]'

kubectl patch deployment xbrl-worker-medium -n processing --type='json' -p='[{"op": "add", "path": "/spec/template/spec/affinity", "value": {"nodeAffinity": {"requiredDuringSchedulingIgnoredDuringExecution": {"nodeSelectorTerms": [{"matchExpressions": [{"key": "kubernetes.io/hostname", "operator": "NotIn", "values": ["minisforum"]}]}]}}}}]'

kubectl patch deployment xbrl-worker-light -n processing --type='json' -p='[{"op": "add", "path": "/spec/template/spec/affinity", "value": {"nodeAffinity": {"requiredDuringSchedulingIgnoredDuringExecution": {"nodeSelectorTerms": [{"matchExpressions": [{"key": "kubernetes.io/hostname", "operator": "NotIn", "values": ["minisforum"]}]}]}}}}]'
```

## Verification Steps (1 minute)

```bash
# 1. Check all pods are running
kubectl get pods -A | grep -v "Running\|Completed" | grep -v "NAME"
# Should return nothing or only pods in "ContainerCreating" state

# 2. Verify Neo4j database
kubectl exec -n neo4j neo4j-0 -- cypher-shell -u neo4j -p 'Next2020#' "MATCH (n) RETURN count(n) LIMIT 1"
# Should return a count number

# 3. Check Redis
kubectl exec -n infrastructure deploy/redis -- redis-cli ping
# Should return: PONG

# 4. Verify KEDA autoscaling
kubectl get scaledobjects -A
# Should show 4 scalers in processing namespace

# 5. Check node resources
kubectl top nodes
# All nodes should show metrics
```

## Current Configuration as of Backup

- **Backup Created**: $(date)
- **Cluster Version**: K3s v1.30.12
- **Node Configuration**:
  - minisforum: Control plane, 16 CPU, 57GB RAM (no taints currently)
  - minisforum2: Worker, 16 CPU, 60GB RAM (no taints)
  - minisforum3: Database, 16 CPU, 126GB RAM (taint: database=neo4j:NoSchedule)

- **Resource Limits**:
  - Neo4j: 90GB memory limit (using ~35GB)
  - XBRL Workers: Heavy(2), Medium(4), Light(7) max pods via KEDA
  - Report Enricher: 5 max pods via KEDA

- **Current State Notes**:
  - All XBRL workers temporarily forced to minisforum2 for historical processing
  - minisforum reserved for historical data fetch (needs 48GB RAM)
  - After historical completes, remove nodeAffinity to restore multi-node distribution

## Critical Passwords and Endpoints

- **Neo4j Database**: 
  - Username: `neo4j`
  - Password: `Next2020#`
  - Bolt: `bolt://localhost:30687` (external)
  - Browser: `http://localhost:30474` (external)

- **Redis**: 
  - No authentication (internal only)
  - External: `localhost:31379`

- **Grafana Monitoring**:
  - URL: `http://minisforum:32000`
  - Default login: admin/admin (check configmap for actual)

## Troubleshooting

### If pods are stuck in Pending:
```bash
kubectl describe pod <pod-name> -n <namespace>
# Check Events section for scheduling issues
```

### If Neo4j won't start:
```bash
# Check if PVC exists and is bound
kubectl get pvc -n neo4j
# Should show neo4j-data and neo4j-logs as Bound

# Check logs
kubectl logs neo4j-0 -n neo4j
```

### If XBRL workers aren't scaling:
```bash
# Check KEDA is running
kubectl get pods -n keda

# Check Redis connectivity
kubectl exec -n infrastructure deploy/redis -- redis-cli LLEN reports:queues:xbrl:heavy
```

## Recovery Time Breakdown

- Create namespaces: 10 seconds
- Apply resources: 2 minutes  
- Neo4j startup: 2-3 minutes
- Verification: 1 minute
- **Total: ~5 minutes**

## IMPORTANT NOTES

1. **Data Persistence**: This backup includes PVC definitions but NOT the actual data. Neo4j data must be restored separately from database backups.

2. **Secrets**: All secrets are included in encrypted form. Handle with care.

3. **IP Addresses**: The cluster expects specific node IPs. If IPs change, update service definitions.

4. **Storage**: Uses local-path storage. Ensure /var/lib/rancher/k3s/storage exists on nodes.

5. **Post-Recovery**: After historical processing completes, remove nodeAffinity from XBRL workers to restore optimal multi-node distribution.