#!/bin/bash

# Get the pod name
POD=$(kubectl get pods -n mcp-services -l app=mcp-neo4j-memory -o name 2>/dev/null | head -n 1 | cut -d/ -f2)
if [ -z "$POD" ]; then
  echo "Error: No mcp-neo4j-memory pod found" >&2
  exit 1
fi

# Run the MCP server directly
exec kubectl exec -i -n mcp-services $POD -- python -c "
import sys
sys.path.append('/app')
from mcp_servers.neo4j_memory_server import main
import asyncio
asyncio.run(main())
" 2>/dev/null