# EventMarketDB Kubernetes Disaster Recovery Package

## 🚨 EMERGENCY RESTORE? Start Here!

If your cluster is down and you need to restore NOW:

1. Extract this backup to any directory
2. Run: `./quick-restore.sh`
3. Wait 5 minutes
4. Run: `./verify-restore.sh`

That's it! Your cluster will be restored.

## 📁 Package Contents

| File/Directory | Purpose |
|----------------|---------|
| `quick-restore.sh` | One-command cluster restoration |
| `verify-restore.sh` | Verify the restore worked |
| `RESTORE_INSTRUCTIONS.md` | Detailed manual restoration guide |
| `CRITICAL_INFO.md` | Passwords, ports, and critical config |
| `create-backup.sh` | Script that created this backup |
| `processing/` | Processing namespace resources |
| `infrastructure/` | Redis, NATS resources |
| `neo4j/` | Neo4j database configuration |
| `monitoring/` | Prometheus, Grafana, Loki |
| `keda/` | KEDA autoscaling system |
| `mcp-services/` | MCP Claude integration |
| `*.yaml` | Cluster-wide resources |

## 🎯 Quick Reference

### Cluster Nodes Required
- `192.168.40.73` - minisforum (control plane)
- `192.168.40.72` - minisforum2 (worker)
- `192.168.40.74` - minisforum3 (database)

### Critical Services
- **Neo4j**: bolt://localhost:30687 (user: neo4j, pass: Next2020#)
- **Redis**: localhost:31379
- **Grafana**: http://minisforum:32000

### Restore Options
1. **Automatic**: Run `./quick-restore.sh` (recommended)
2. **Manual**: Follow `RESTORE_INSTRUCTIONS.md`
3. **Verify**: Run `./verify-restore.sh` after restore

## ⏱️ Recovery Time

- Automated restore: ~5 minutes
- Manual restore: ~7 minutes
- Verification: ~1 minute

## 🔍 Troubleshooting

If restore fails:
1. Check all 3 nodes are accessible
2. Verify kubectl works: `kubectl get nodes`
3. Check detailed instructions in `RESTORE_INSTRUCTIONS.md`
4. Review errors in pod events: `kubectl get events -A --sort-by='.lastTimestamp'`

## 📊 What Gets Restored

✅ **Included**:
- All Kubernetes configurations
- Service definitions and ports
- Resource limits and requests
- Autoscaling rules
- Network policies
- Secrets (encrypted)

❌ **NOT Included**:
- Database data (restore from Neo4j backup)
- Redis queue contents
- Metrics history
- Log files

## 🛡️ Security Note

This backup contains encrypted secrets. Store securely and limit access.

## 📝 Backup Information

- **Created**: $(date)
- **Method**: Full cluster export
- **Namespaces**: 6 (processing, infrastructure, neo4j, monitoring, keda, mcp-services)
- **Restore tested**: Yes, designed for zero-knowledge restore

---

For detailed restoration steps, see `RESTORE_INSTRUCTIONS.md`
For critical passwords and configuration, see `CRITICAL_INFO.md`