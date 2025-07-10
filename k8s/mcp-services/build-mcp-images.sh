#!/bin/bash
# Build MCP Docker images with pre-installed packages

set -e

echo "Building MCP Docker images..."

# Build cypher image
echo "Building mcp-neo4j-cypher image..."
docker build \
  -f /home/faisal/EventMarketDB/k8s/mcp-services/Dockerfile.cypher \
  -t faisalanjum/mcp-neo4j-cypher:latest \
  /home/faisal/neo4j-mcp-server/servers/mcp-neo4j-cypher/

# Build memory image  
echo "Building mcp-neo4j-memory image..."
docker build \
  -f /home/faisal/EventMarketDB/k8s/mcp-services/Dockerfile.memory \
  -t faisalanjum/mcp-neo4j-memory:latest \
  /home/faisal/neo4j-mcp-server/servers/mcp-neo4j-memory/

echo "Docker images built successfully!"
echo ""
echo "To push to Docker Hub:"
echo "  docker push faisalanjum/mcp-neo4j-cypher:latest"
echo "  docker push faisalanjum/mcp-neo4j-memory:latest"
echo ""
echo "To update deployments:"
echo "  kubectl set image deployment/mcp-neo4j-cypher mcp-neo4j-cypher=faisalanjum/mcp-neo4j-cypher:latest -n mcp-services"
echo "  kubectl set image deployment/mcp-neo4j-memory mcp-neo4j-memory=faisalanjum/mcp-neo4j-memory:latest -n mcp-services"