#!/bin/bash
# EventMarketDB Restore Verification Script

echo "======================================"
echo "EventMarketDB Restore Verification"
echo "======================================"
echo ""

ERRORS=0

echo "1. Checking nodes..."
if kubectl get nodes | grep -q "Ready"; then
    echo "✓ Nodes are ready"
    kubectl get nodes
else
    echo "✗ Nodes not ready!"
    ERRORS=$((ERRORS + 1))
fi
echo ""

echo "2. Checking namespaces..."
for ns in processing infrastructure neo4j monitoring keda mcp-services; do
    if kubectl get namespace $ns &>/dev/null; then
        echo "✓ Namespace $ns exists"
    else
        echo "✗ Namespace $ns missing!"
        ERRORS=$((ERRORS + 1))
    fi
done
echo ""

echo "3. Checking critical services..."
# Redis
if kubectl exec -n infrastructure deploy/redis -- redis-cli ping 2>/dev/null | grep -q "PONG"; then
    echo "✓ Redis is responding"
else
    echo "✗ Redis not responding!"
    ERRORS=$((ERRORS + 1))
fi

# Neo4j
if kubectl exec -n neo4j neo4j-0 -- cypher-shell -u neo4j -p 'Next2020#' "RETURN 1" 2>/dev/null | grep -q "1"; then
    echo "✓ Neo4j is responding"
else
    echo "✗ Neo4j not responding!"
    ERRORS=$((ERRORS + 1))
fi
echo ""

echo "4. Checking KEDA autoscaling..."
SCALER_COUNT=$(kubectl get scaledobjects -A --no-headers 2>/dev/null | wc -l)
if [ $SCALER_COUNT -ge 4 ]; then
    echo "✓ KEDA scalers active ($SCALER_COUNT found)"
else
    echo "✗ KEDA scalers missing (only $SCALER_COUNT found, expected 4+)"
    ERRORS=$((ERRORS + 1))
fi
echo ""

echo "5. Checking pod status..."
NOT_READY=$(kubectl get pods -A --no-headers | grep -v "Running\|Completed" | wc -l)
if [ $NOT_READY -eq 0 ]; then
    echo "✓ All pods are ready"
else
    echo "⚠ $NOT_READY pods not ready yet:"
    kubectl get pods -A | grep -v "Running\|Completed" | grep -v "NAME"
fi
echo ""

echo "6. Resource summary:"
kubectl top nodes 2>/dev/null || echo "  (metrics-server may need time to collect data)"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo "======================================"
    echo "✓ VERIFICATION PASSED!"
    echo "======================================"
    echo ""
    echo "Your EventMarketDB cluster is fully restored."
    echo ""
    echo "Important endpoints:"
    echo "  Neo4j Browser: http://localhost:30474"
    echo "  Neo4j Bolt:    bolt://localhost:30687"
    echo "  Redis:         localhost:31379"
    echo "  Grafana:       http://minisforum:32000"
else
    echo "======================================"
    echo "✗ VERIFICATION FAILED!"
    echo "======================================"
    echo ""
    echo "Found $ERRORS errors. Check the output above."
    echo "Run 'kubectl get pods -A' for more details."
fi