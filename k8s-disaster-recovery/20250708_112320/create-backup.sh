#!/bin/bash
# EventMarketDB Kubernetes Disaster Recovery Backup Script
# Creates a complete backup of all Kubernetes resources

echo "Starting EventMarketDB Kubernetes backup..."

# Get all namespaces we care about
NAMESPACES="processing infrastructure neo4j monitoring keda mcp-services"

# Export namespace resources
for ns in $NAMESPACES; do
    echo "Backing up namespace: $ns"
    mkdir -p $ns
    
    # Check if namespace exists
    if kubectl get namespace $ns &>/dev/null; then
        # Export all resources in namespace
        kubectl get all,cm,secret,pvc,pv,sa,role,rolebinding,scaledobject,ingress,networkpolicy -n $ns -o yaml > $ns/all-resources.yaml 2>/dev/null || true
        
        # Export individual resource types for easier recovery
        kubectl get deployments -n $ns -o yaml > $ns/deployments.yaml 2>/dev/null || echo "# No deployments in $ns" > $ns/deployments.yaml
        kubectl get statefulsets -n $ns -o yaml > $ns/statefulsets.yaml 2>/dev/null || echo "# No statefulsets in $ns" > $ns/statefulsets.yaml
        kubectl get services -n $ns -o yaml > $ns/services.yaml 2>/dev/null || echo "# No services in $ns" > $ns/services.yaml
        kubectl get configmaps -n $ns -o yaml > $ns/configmaps.yaml 2>/dev/null || echo "# No configmaps in $ns" > $ns/configmaps.yaml
        kubectl get secrets -n $ns -o yaml > $ns/secrets.yaml 2>/dev/null || echo "# No secrets in $ns" > $ns/secrets.yaml
        kubectl get pvc -n $ns -o yaml > $ns/pvc.yaml 2>/dev/null || echo "# No PVCs in $ns" > $ns/pvc.yaml
        kubectl get scaledobjects -n $ns -o yaml > $ns/scaledobjects.yaml 2>/dev/null || echo "# No scaledobjects in $ns" > $ns/scaledobjects.yaml
    else
        echo "Namespace $ns not found, skipping..."
    fi
done

# Export cluster-wide resources
echo "Backing up cluster-wide resources..."
kubectl get nodes -o yaml > nodes.yaml
kubectl get pv -o yaml > persistent-volumes.yaml
kubectl get sc -o yaml > storage-classes.yaml
kubectl get priorityclasses -o yaml > priority-classes.yaml 2>/dev/null || echo "# No priority classes found" > priority-classes.yaml
kubectl get namespaces -o yaml > namespaces.yaml

# Export CRDs if any
kubectl get crd -o yaml > crds.yaml 2>/dev/null || echo "# No CRDs found" > crds.yaml

# Get current node labels and taints
echo "Capturing node configuration..."
for node in minisforum minisforum2 minisforum3; do
    echo "=== Node: $node ===" >> node-config.txt
    kubectl describe node $node | grep -E "(Taints:|Labels:)" -A 5 >> node-config.txt
    echo "" >> node-config.txt
done

# Capture current resource usage for reference
echo "Capturing current state..."
kubectl get pods -A -o wide > current-pods-state.txt
kubectl top nodes > current-node-usage.txt 2>/dev/null || true
kubectl get scaledobjects -A -o wide > current-scalers.txt 2>/dev/null || true

echo "Backup complete!"