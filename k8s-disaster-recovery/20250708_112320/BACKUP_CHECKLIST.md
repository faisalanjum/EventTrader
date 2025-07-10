# Backup Verification Checklist

## Pre-Restore Checklist
- [ ] All 3 nodes accessible (ping 192.168.40.73, .72, .74)
- [ ] kubectl configured and working
- [ ] At least 300GB free space on nodes for volumes
- [ ] Backup file extracted to accessible directory

## During Restore Checklist
- [ ] Node labels applied (control-plane, database)
- [ ] Node taints applied (database=neo4j on minisforum3)
- [ ] All 6 namespaces created
- [ ] Storage classes and PVs created
- [ ] KEDA installed and running
- [ ] Redis pod ready
- [ ] Neo4j pod ready (may take 3 minutes)
- [ ] XBRL workers deployed
- [ ] Report enricher deployed

## Post-Restore Checklist
- [ ] All pods in Running state (except Jobs)
- [ ] Neo4j responding to queries
- [ ] Redis responding to ping
- [ ] KEDA scalers active (4 minimum)
- [ ] Node resources visible (kubectl top nodes)
- [ ] External ports accessible:
  - [ ] Neo4j browser: http://localhost:30474
  - [ ] Neo4j bolt: localhost:30687
  - [ ] Redis: localhost:31379
  - [ ] Grafana: http://minisforum:32000

## Data Restore Checklist (Separate Process)
- [ ] Neo4j database backup restored
- [ ] Redis queues repopulated if needed
- [ ] Application logs directory mounted
- [ ] Prometheus data restored (optional)

## Final Verification
- [ ] Run ./verify-restore.sh - all checks pass
- [ ] Process a test document through the system
- [ ] Check Grafana dashboards loading
- [ ] Verify KEDA scaling with test queue items

## Rollback Plan
If restore fails:
1. Delete all namespaces: `kubectl delete ns processing infrastructure neo4j monitoring keda mcp-services`
2. Remove node taints: `kubectl taint nodes minisforum3 database=neo4j:NoSchedule-`
3. Start fresh with ./quick-restore.sh

## Important Reminders
- XBRL workers currently restricted to minisforum2 (temporary)
- After historical processing, remove nodeAffinity restrictions
- Neo4j password: Next2020#
- All services use NodePort for external access