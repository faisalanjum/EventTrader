#!/bin/bash
# Verify all changes persist after restart

echo "=== EventMarketDB Persistence Verification ==="
echo "Date: $(date)"
echo ""

# 1. Node Taints
echo "1. Checking Node Taints..."
TAINT=$(kubectl describe node minisforum | grep "Taints:" | awk '{print $2}')
if [ "$TAINT" == "<none>" ]; then
    echo "✅ minisforum taint removed (as expected)"
else
    echo "❌ WARNING: minisforum has taint: $TAINT"
fi

# 2. KEDA Configurations
echo -e "\n2. Checking KEDA MaxReplicas..."
HEAVY=$(kubectl get scaledobject xbrl-worker-heavy-scaler -n processing -o jsonpath='{.spec.maxReplicaCount}')
MEDIUM=$(kubectl get scaledobject xbrl-worker-medium-scaler -n processing -o jsonpath='{.spec.maxReplicaCount}')
LIGHT=$(kubectl get scaledobject xbrl-worker-light-scaler -n processing -o jsonpath='{.spec.maxReplicaCount}')

[ "$HEAVY" == "2" ] && echo "✅ Heavy: $HEAVY (correct)" || echo "❌ Heavy: $HEAVY (expected 2)"
[ "$MEDIUM" == "3" ] && echo "✅ Medium: $MEDIUM (correct)" || echo "❌ Medium: $MEDIUM (expected 3)"
[ "$LIGHT" == "5" ] && echo "✅ Light: $LIGHT (correct)" || echo "❌ Light: $LIGHT (expected 5)"

# 3. Node Affinity
echo -e "\n3. Checking Node Affinity..."
AFFINITY_COUNT=$(kubectl get deploy -n processing -o json | jq '[.items[] | select(.metadata.name | contains("xbrl-worker")) | select(.spec.template.spec.affinity != null)] | length')
if [ "$AFFINITY_COUNT" == "3" ]; then
    echo "✅ All 3 XBRL workers have affinity rules"
else
    echo "❌ Only $AFFINITY_COUNT workers have affinity (expected 3)"
fi

# 4. Neo4j Memory
echo -e "\n4. Checking Neo4j Memory..."
NEO4J_MEM=$(kubectl get sts neo4j -n neo4j -o jsonpath='{.spec.template.spec.containers[0].resources.limits.memory}')
if [ "$NEO4J_MEM" == "90Gi" ]; then
    echo "✅ Neo4j memory: $NEO4J_MEM (correct)"
else
    echo "❌ Neo4j memory: $NEO4J_MEM (expected 90Gi)"
fi

# 5. Benzinga WebSocket Fix
echo -e "\n5. Checking Benzinga WebSocket Fix..."
ONCLOSE=$(grep "def _on_close" /home/faisal/EventMarketDB/benzinga/bz_websocket.py | grep -c "self, close_status_code, close_msg")
if [ "$ONCLOSE" == "1" ]; then
    echo "✅ WebSocket _on_close signature fixed"
else
    echo "❌ WebSocket _on_close signature NOT fixed"
fi

# 6. Current Pod Status
echo -e "\n6. Current Pod Status..."
echo "Processing namespace:"
kubectl get pods -n processing -o wide | grep -E "NAME|xbrl-worker|report-enricher|event-trader"

echo -e "\nMCP Services:"
kubectl get pods -n mcp-services

echo -e "\nNeo4j:"
kubectl get pods -n neo4j

# 7. Queue Status
echo -e "\n7. Redis Queue Status..."
REDIS_POD=$(kubectl get pod -n infrastructure -l app=redis -o jsonpath='{.items[0].metadata.name}')
if [ -n "$REDIS_POD" ]; then
    kubectl exec -n infrastructure $REDIS_POD -- redis-cli LLEN reports:queues:xbrl:heavy | xargs echo "Heavy queue:"
    kubectl exec -n infrastructure $REDIS_POD -- redis-cli LLEN reports:queues:xbrl:medium | xargs echo "Medium queue:"
    kubectl exec -n infrastructure $REDIS_POD -- redis-cli LLEN reports:queues:xbrl:light | xargs echo "Light queue:"
fi

echo -e "\n=== Verification Complete ==="
echo "If all items show ✅, your changes have persisted correctly."
echo "Note: Pod distribution may vary after restart - this is normal."