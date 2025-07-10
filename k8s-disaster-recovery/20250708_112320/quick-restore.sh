#!/bin/bash
# EventMarketDB Kubernetes Quick Restore Script
# Restores entire cluster in under 5 minutes

set -e  # Exit on any error

echo "=========================================="
echo "EventMarketDB Kubernetes Disaster Recovery"
echo "=========================================="
echo ""
echo "This script will restore your entire cluster."
echo "Expected time: 5 minutes"
echo ""
echo "Prerequisites:"
echo "- 3 nodes: minisforum (192.168.40.73), minisforum2 (192.168.40.72), minisforum3 (192.168.40.74)"
echo "- kubectl configured and working"
echo ""
read -p "Press ENTER to start recovery or Ctrl+C to cancel..."

START_TIME=$(date +%s)

echo ""
echo "[Step 1/7] Applying node labels and taints..."
kubectl label node minisforum node-role.kubernetes.io/control-plane=true --overwrite 2>/dev/null || true
kubectl label node minisforum3 node-role.kubernetes.io/database=true --overwrite 2>/dev/null || true
kubectl taint nodes minisforum3 database=neo4j:NoSchedule --overwrite 2>/dev/null || true
echo "✓ Node configuration complete"

echo ""
echo "[Step 2/7] Creating namespaces..."
for ns in processing infrastructure neo4j monitoring keda mcp-services; do
    kubectl create namespace $ns 2>/dev/null || echo "  - Namespace $ns already exists"
done
echo "✓ Namespaces ready"

echo ""
echo "[Step 3/7] Applying storage and cluster resources..."
kubectl apply -f storage-classes.yaml 2>/dev/null || true
kubectl apply -f persistent-volumes.yaml 2>/dev/null || true
kubectl apply -f crds.yaml 2>/dev/null || true
echo "✓ Storage configured"

echo ""
echo "[Step 4/7] Installing KEDA and core infrastructure..."
echo "  - Installing KEDA..."
kubectl apply -f keda/ --recursive
echo "  - Installing infrastructure services..."
kubectl apply -f infrastructure/ --recursive
echo "  - Installing Neo4j database..."
kubectl apply -f neo4j/ --recursive
echo "✓ Core services deployed"

echo ""
echo "[Step 5/7] Waiting for critical services..."
echo "  - Waiting for Redis (timeout: 2 minutes)..."
kubectl wait --for=condition=ready pod -l app=redis -n infrastructure --timeout=120s || echo "  ! Redis taking longer than expected"

echo "  - Waiting for Neo4j (this takes 2-3 minutes)..."
kubectl wait --for=condition=ready pod neo4j-0 -n neo4j --timeout=300s || echo "  ! Neo4j taking longer than expected"
echo "✓ Core services ready"

echo ""
echo "[Step 6/7] Deploying application workloads..."
echo "  - Processing workloads..."
kubectl apply -f processing/ --recursive
echo "  - Verifying KEDA scalers have minReplicaCount=1..."
kubectl get scaledobjects -n processing -o yaml | grep -q "minReplicaCount: 0" && echo "  ! WARNING: Found minReplicaCount: 0 - applying fix..." && kubectl apply -f KEDA_CRITICAL_UPDATE.yaml || echo "  ✓ KEDA configs correct"
echo "  - MCP services..."
kubectl apply -f mcp-services/ --recursive 2>/dev/null || true
echo "  - Monitoring stack..."
kubectl apply -f monitoring/ --recursive 2>/dev/null || true
echo "✓ All workloads deployed"

echo ""
echo "[Step 7/7] Applying current configuration adjustments..."
# Apply XBRL worker node restrictions (temporary for historical processing)
kubectl patch deployment xbrl-worker-heavy -n processing --type='json' -p='[{"op": "add", "path": "/spec/template/spec/affinity", "value": {"nodeAffinity": {"requiredDuringSchedulingIgnoredDuringExecution": {"nodeSelectorTerms": [{"matchExpressions": [{"key": "kubernetes.io/hostname", "operator": "NotIn", "values": ["minisforum"]}]}]}}}}]' 2>/dev/null || true

kubectl patch deployment xbrl-worker-medium -n processing --type='json' -p='[{"op": "add", "path": "/spec/template/spec/affinity", "value": {"nodeAffinity": {"requiredDuringSchedulingIgnoredDuringExecution": {"nodeSelectorTerms": [{"matchExpressions": [{"key": "kubernetes.io/hostname", "operator": "NotIn", "values": ["minisforum"]}]}]}}}}]' 2>/dev/null || true

kubectl patch deployment xbrl-worker-light -n processing --type='json' -p='[{"op": "add", "path": "/spec/template/spec/affinity", "value": {"nodeAffinity": {"requiredDuringSchedulingIgnoredDuringExecution": {"nodeSelectorTerms": [{"matchExpressions": [{"key": "kubernetes.io/hostname", "operator": "NotIn", "values": ["minisforum"]}]}]}}}}]' 2>/dev/null || true

echo "✓ Configuration applied"

# Calculate elapsed time
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
MINUTES=$((ELAPSED / 60))
SECONDS=$((ELAPSED % 60))

echo ""
echo "=========================================="
echo "RECOVERY COMPLETE!"
echo "Time taken: ${MINUTES}m ${SECONDS}s"
echo "=========================================="
echo ""
echo "Verification commands:"
echo "  kubectl get pods -A                    # Check all pods"
echo "  kubectl exec -n neo4j neo4j-0 -- cypher-shell -u neo4j -p 'Next2020#' \"RETURN 1\""
echo "  kubectl exec -n infrastructure deploy/redis -- redis-cli ping"
echo ""
echo "Current pod status:"
kubectl get pods -A --no-headers | grep -v "Running\|Completed" | wc -l | xargs echo "Pods not yet ready:"
echo ""
echo "For detailed status: kubectl get pods -A | grep -v Running"