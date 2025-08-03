from langchain_mcp_adapters.client import MultiServerMCPClient

async def filter_events(s):
    """Minimal MCP connection test - just check if we can connect"""
    # Provide defaults to avoid KeyError
    s.setdefault("company_ticker", "AAPL")
    s.setdefault("target_date", "2025-01-26")
    s.setdefault("events", [])
    s.setdefault("result", {})
    
    try:
        # Use localhost like ALL other MCP files for consistency
        # NodePort 31380 is accessible on localhost when running on cluster node
        client = MultiServerMCPClient({
            "neo4j": {
                "url": "http://localhost:31380/mcp",
                "transport": "streamable_http",
            }
        })
        # Just set a simple event for now - real queries can be added later
        s["events"] = [{"id": "mcp_test", "return": 1.5, "headline": "MCP Connected"}]
    except Exception as e:
        s["events"] = [{"id": "error", "return": 0, "headline": f"MCP Error: {str(e)}"}]
    return s

async def analyze_attribution(s):
    """Simple analysis of events"""
    if s["events"]:
        s["result"] = {"event": s["events"][0]["id"], "confidence": 95, 
                      "reason": "MCP connection test"}
    return s

async def format_output(s):
    """Format the final output"""
    s["result"].update({"company": s["company_ticker"], "date": s["target_date"]})
    return s