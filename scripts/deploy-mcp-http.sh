#!/usr/bin/env bash
# Deploy MCP HTTP service
# Usage: ./scripts/deploy-mcp-http.sh
set -e
cd "$(dirname "$0")/.."    # repo root

echo "▶︎ Deploying MCP Neo4j Cypher HTTP service..."
kubectl apply -f k8s/mcp-services/mcp-neo4j-cypher-http-deployment.yaml

echo "▶︎ Waiting for deployment..."
kubectl rollout status deployment/mcp-neo4j-cypher-http -n mcp-services --timeout=120s

echo "✔︎ MCP HTTP service deployed"
echo ""
echo "Service endpoint: http://mcp-neo4j-cypher-http.mcp-services:8000/mcp"