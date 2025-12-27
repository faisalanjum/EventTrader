# MCP HTTP Service Setup (Added July 25, 2025)

## Purpose
Enables MCP (Model Context Protocol) tools to be used with LangGraph/LangChain via HTTP transport, making them work exactly like any other LangChain tool.

## Deployment Files
- **Main deployment**: `mcp-neo4j-cypher-http-deployment.yaml`
- **Deployment script**: `/home/faisal/EventMarketDB/scripts/deploy-mcp-http.sh`
- **Example notebook**: `/home/faisal/EventMarketDB/drivers/agenticDrivers/neo4j_mcp_simple_tools.ipynb`

## Key Configuration
- **NodePort**: 31380 (follows pattern: Redis=31379, MCP=31380)
- **Namespace**: mcp-services
- **Image**: python:3.11-slim (installs FastMCP at runtime)
- **Node**: minisforum (control plane)

## Integration with Existing Scripts
1. **build_push.sh**: Added `mcp-http` case (no build needed)
2. **rollout.sh**: Added `mcp-http` case for restart

## Usage Example
```python
from langchain_mcp_adapters.client import MultiServerMCPClient

# No port-forward needed on minisforum
client = MultiServerMCPClient({
    "neo4j": {
        "url": "http://localhost:31380/mcp",
        "transport": "streamable_http",
    }
})

# Get tools (async required)
tools = await client.get_tools()

# Use with LangGraph exactly like any other tool
from langgraph.prebuilt import create_react_agent
agent = create_react_agent("openai:gpt-4", tools)
```

## Important Notes
- **Does NOT affect Claude Desktop** - original pods unchanged
- **Requires async** - MCP tools use `ainvoke()` not `invoke()`
- **Auto-restarts on reboot** - standard K8s deployment
- **No rebuild needed** - code changes just need pod restart

## To Deploy
```bash
kubectl apply -f mcp-neo4j-cypher-http-deployment.yaml
# OR
./scripts/deploy-mcp-http.sh
```

## To Remove
```bash
kubectl delete deployment mcp-neo4j-cypher-http -n mcp-services
kubectl delete service mcp-neo4j-cypher-http -n mcp-services
```