# EventMarketDB Critical Information

## Cluster Access

### Node IPs (MUST MATCH EXACTLY)
- **minisforum** (Control Plane): 192.168.40.73
- **minisforum2** (Worker): 192.168.40.72  
- **minisforum3** (Database): 192.168.40.74

### Critical Passwords
- **Neo4j Database**: 
  - Username: `neo4j`
  - Password: `Next2020#`
- **Redis**: No authentication
- **Grafana**: Check monitoring/configmaps.yaml for credentials

## External Service Ports

These NodePorts are hardcoded in the services and MUST remain the same:

| Service | NodePort | Internal Port | Usage |
|---------|----------|---------------|--------|
| Neo4j Bolt | 30687 | 7687 | Database connections |
| Neo4j HTTP | 30474 | 7474 | Web browser interface |
| Redis | 31379 | 6379 | Queue/cache |
| Grafana | 32000 | 80 | Monitoring dashboard |

## Storage Paths

Local storage paths on each node:
- **Primary**: `/var/lib/rancher/k3s/storage/`
- **Logs**: `/home/faisal/EventMarketDB/logs/`

## Current Resource Allocation

### Node Capacity
- **minisforum**: 16 CPU, 57GB RAM
- **minisforum2**: 16 CPU, 60GB RAM  
- **minisforum3**: 16 CPU, 126GB RAM

### Major Resource Consumers
- **Neo4j**: 90GB memory limit (typically uses ~35GB)
- **XBRL Heavy Workers**: 6GB request, 8GB limit each
- **XBRL Medium Workers**: 3GB request, 4GB limit each
- **XBRL Light Workers**: 1.5GB request, 2GB limit each
- **Report Enricher**: 2GB request, 8GB limit each

## KEDA Autoscaling Limits

Current max replicas (as of backup):
- **xbrl-worker-heavy**: 2 pods
- **xbrl-worker-medium**: 4 pods
- **xbrl-worker-light**: 7 pods
- **report-enricher**: 5 pods

## Queue Names (Redis)

Critical Redis queue keys:
- `reports:queues:xbrl:heavy` - 10-K forms
- `reports:queues:xbrl:medium` - 10-Q forms
- `reports:queues:xbrl:light` - 8-K and other forms
- `reports:queues:enrich` - Report enrichment

## Special Configurations

### Node Affinity (Temporary)
XBRL workers are currently restricted FROM minisforum to reserve memory for historical processing. After historical completes, remove these restrictions:

```bash
# Remove restrictions after historical processing
kubectl patch deployment xbrl-worker-heavy -n processing --type='json' -p='[{"op": "remove", "path": "/spec/template/spec/affinity"}]'
kubectl patch deployment xbrl-worker-medium -n processing --type='json' -p='[{"op": "remove", "path": "/spec/template/spec/affinity"}]'
kubectl patch deployment xbrl-worker-light -n processing --type='json' -p='[{"op": "remove", "path": "/spec/template/spec/affinity"}]'
```

### Critical Taints
- **minisforum3**: `database=neo4j:NoSchedule` (NEVER REMOVE - keeps Neo4j isolated)

## Recovery Priorities

1. **Neo4j** - All processing depends on database
2. **Redis** - Queue system for all workers
3. **KEDA** - Autoscaling controller
4. **XBRL Workers** - Document processing
5. **Report Enricher** - Post-processing
6. **Monitoring** - Optional but helpful

## Data Not Included

This backup includes configuration but NOT:
- Neo4j database contents (698,437+ nodes)
- Redis queue contents
- Prometheus metrics history
- Application logs

These must be restored from separate data backups.

## Contact for Issues

If restoration fails, check:
1. Node IPs match exactly
2. Kubernetes cluster is healthy (`kubectl get nodes`)
3. Storage paths exist on nodes
4. No conflicting resources from previous installation

## Backup Metadata

- **Created**: $(date)
- **Created By**: Disaster Recovery Script
- **Cluster Version**: K3s v1.30.12
- **Total Namespaces**: 6
- **Total Pods**: ~25-30 when fully scaled