# EventMarketDB Drivers Documentation

This directory contains all Neo4j database query tools, patterns, and agent implementations for the EventMarketDB financial graph database.

## 📚 Documentation Files

### Query Patterns & Schema
- **[docs/NEO4J_SCHEMA.md](docs/NEO4J_SCHEMA.md)** - Complete database schema + query guide (single reference)
- **[docs/XBRL_PATTERNS.md](docs/XBRL_PATTERNS.md)** - Structured financial data queries (10-K/10-Q only)
- **[docs/NON_XBRL_PATTERNS.md](docs/NON_XBRL_PATTERNS.md)** - Text search patterns with fulltext indexes

### Implementation Guides
- **[docs/MCP_AGENT_IMPLEMENTATION.md](docs/MCP_AGENT_IMPLEMENTATION.md)** - Production MCP query agent
- **[docs/LANGGRAPH_STUDIO_SETUP.md](docs/LANGGRAPH_STUDIO_SETUP.md)** - Visual debugging with LangGraph

## 🚀 Quick Navigation

| Need | Use This File |
|------|---------------|
| Write Neo4j queries | [docs/NEO4J_SCHEMA.md](docs/NEO4J_SCHEMA.md) |
| Understand schema | [docs/NEO4J_SCHEMA.md](docs/NEO4J_SCHEMA.md) |
| Query financial metrics | [docs/XBRL_PATTERNS.md](docs/XBRL_PATTERNS.md) |
| Search text content | [docs/NON_XBRL_PATTERNS.md](docs/NON_XBRL_PATTERNS.md) |
| Use the query agent | [docs/MCP_AGENT_IMPLEMENTATION.md](docs/MCP_AGENT_IMPLEMENTATION.md) |
| Debug with visuals | [docs/LANGGRAPH_STUDIO_SETUP.md](docs/LANGGRAPH_STUDIO_SETUP.md) |

## 🔑 Key Concepts

### XBRL vs Non-XBRL Data
- **XBRL**: Structured financial facts (10-K/10-Q ONLY)
  - Revenue, EPS, Assets, etc.
  - ~7.69M tagged facts
- **Non-XBRL**: Narrative text (ALL report types)
  - Management discussion, risk factors, 8-K events
  - Uses fulltext search for performance

### Critical Rules
1. **8-K reports NEVER have XBRL** - use text search
2. **Fact.is_numeric = '1'** - string not boolean
3. **No direct Fact→Report** relationship - must go through XBRLNode
4. **Reports don't influence Companies** - they influence Industry/Sector/Market

## 🛠️ Production Components

### MCP Agent (`drivers_graph/`)
- **mcp_agent_react_v4.py** - Latest production implementation
- Tiered LLM escalation (GPT-4o-mini → Claude)
- Redis pattern learning at `admin:neo4j_patterns`
- Handles complex multi-step queries

### Query Tools (`agenticDrivers/`)
- Jupyter notebooks for testing
- Example implementations
- Performance benchmarks

## 📊 Database at a Glance

- **31,618** Reports (19% have XBRL)
- **7.69M** XBRL Facts
- **177K** News articles
- **14.7K** Earnings transcripts
- **796** Companies
- **145K** Extracted text sections

## ⚡ Performance Tips

1. **Use fulltext indexes** - 10-100x faster than CONTAINS
2. **Filter by metadata first** - formType, section_name, dates
3. **Add LIMIT early** - prevent overwhelming results
4. **Check report type** - 8-K? Skip XBRL entirely

## 🔗 External Access

- **Neo4j Browser**: http://localhost:30474
- **Redis**: localhost:31379
- **MCP HTTP**: http://localhost:31380/mcp

---

For detailed information, start with [docs/NEO4J_SCHEMA.md](docs/NEO4J_SCHEMA.md).


# LangGraph Studio Demo

Minimal example with LangGraph Studio visualization and automatic LangSmith tracing.

## Quick Start

```bash
# 1. Start Studio
cd /home/faisal/EventMarketDB/drivers/drivers_graph
./studio.sh

# 2. Copy the RED URL to browser
# 3. Run the example
python example_usage.py
```

## LangSmith Observability (Always On!)

**ANY code** that imports `from eventtrader import keys` gets automatic tracing:

```python
from eventtrader import keys  # This enables tracing
from langgraph.graph import StateGraph
# Your code is now traced!
```

View traces at: https://smith.langchain.com → Projects → EventMarketDB

## Architecture

- `graph.py`: Defines workflow (filter → analyze → format)
- `nodes.py`: Async functions with MCP HTTP client
- `state.py`: TypedDict for data flow
- `config.py`: Loads env vars from parent .env
- `studio.sh`: Starts LangGraph with tunnel (shows URL in red)

## Technical Details

- **Graph**: StateGraph with AttributionState
- **MCP**: Connects to http://192.168.40.72:31380
- **Tunnel**: Bypasses CORS for remote access
- **Tracing**: Automatic via environment variables

## For Bots

```python
from eventtrader import keys  # Enables tracing
from drivers.drivers_graph.graph import create_graph

graph = create_graph()
result = await graph.ainvoke({"company_ticker": "AAPL", "target_date": "2025-01-26"})
```

## MCP Agent - Adaptive Neo4j Query Agent

A minimal (250-line) agent that learns from successful queries to handle ANY Neo4j query with 90% cost reduction.

### Features
- **Cost-efficient**: Uses GPT-4o-mini instead of Claude Sonnet 4 (99% cheaper)
- **Adaptive learning**: Learns from every successful query
- **Few-shot approach**: Shows examples instead of complex instructions
- **Handles quirks**: Automatically handles Neo4j type errors (e.g., INFLUENCES Infinity bug)

### Usage

```python
from drivers.drivers_graph.mcp_agent import mcp_agent

# In LangGraph Studio
result = await mcp_agent.ainvoke({
    "messages": [{"role": "human", "content": "Find News influencing Company with max returns"}]
})
```

### How it works
1. Finds similar past queries using embeddings
2. Builds minimal prompt with examples
3. Generates query with GPT-4o-mini
4. Executes via MCP HTTP
5. Learns from successful queries



# MCP Agent Implementation Guide

## Overview
The MCP Agent is a Neo4j Cypher query generator that uses natural language to create accurate database queries. It features tiered model escalation and Redis-based pattern learning.

## Key Files

### Production Implementation
- **`mcp_agent_final.py`** - The final production implementation with all features:
  - Tiered model escalation (GPT-4o-mini → Claude-3.5-Sonnet)
  - Redis pattern storage and retrieval
  - Result limiting to control costs
  - Enhanced error detection
  - Fixed seed patterns for complex queries

### Legacy Implementations (for reference)
- **`mcp_agent.py`** - Original implementation with property validation
- **`mcp_agent_react.py`** - ReAct pattern implementation using LangGraph
- **`mcp_agent_minimal_tiered.py`** - Earlier tiered implementation

## Key Features

### 1. Tiered Model Escalation
- Starts with cost-efficient GPT-4o-mini
- Automatically escalates to Claude-3.5-Sonnet after 5 failures
- Resets to cheaper model after success

### 2. Redis Integration
- Uses namespace: `admin:neo4j_patterns`
- Stores successful query patterns with embeddings
- Similarity threshold: 0.95 for duplicate detection
- Max patterns: 500 (FIFO)

### 3. Result Limiting
- Max rows: 50
- Max characters: 5000
- Automatic truncation with notifications

### 4. Enhanced Seed Patterns
- Basic queries (counts, averages)
- Date filtering and matching
- Complex multi-condition queries
- Fact retrieval with proper joins
- Fixed syntax for nested queries

## Usage

```python
from mcp_agent_final import query_neo4j

# Simple query
result = await query_neo4j("Count all companies")

# Complex query
result = await query_neo4j("""
    Find the 10 companies that filed a 10-Q in the last 60 days 
    where a same-day news item drove the company's daily_stock return 
    at least 4% below the SPY's daily_macro return
""")

# Result structure
{
    "query": "MATCH ...",        # Generated Cypher
    "result": "[...]",           # Query results (JSON)
    "success": True,             # Success status
    "attempts": 6,               # Number of attempts
    "model_used": "Claude-3.5-Sonnet",  # Model that succeeded
    "was_truncated": False       # Whether results were truncated
}
```

## Configuration

### Environment Variables (via .env)
- `OPENAI_API_KEY` - For GPT-4o-mini and embeddings
- `ANTHROPIC_API_KEY` - For Claude-3.5-Sonnet escalation

### Redis Connection
- Host: localhost
- Port: 31379 (Kubernetes NodePort)
- Namespace: `admin:neo4j_patterns`

### MCP HTTP Service
- URL: http://localhost:31380/mcp
- Transport: streamable_http

## Testing

The implementation has been thoroughly tested with:
- Simple queries (single-step)
- Complex queries (multi-join with date matching and fact retrieval)
- Model escalation scenarios
- Redis pattern storage and retrieval

## Key Improvements Over Original

1. **No Schema Validation** - Removed rigid property validation that blocked valid queries
2. **Better Error Detection** - Properly catches Neo4j syntax errors in results
3. **Fixed Seed Patterns** - Corrected syntax for complex queries (no nested MATCH-RETURN)
4. **Token Limits** - Increased to 2048 for complex queries
5. **Result Limiting** - Prevents token overflow and reduces costs

## Common Query Patterns

### Date Filtering
```cypher
datetime(r.created) > datetime() - duration('P60D')
```

### Date Matching
```cypher
date(datetime(n.created)) = date(datetime(r.created))
```

### NULL/NaN Checks
```cypher
WHERE r.property IS NOT NULL AND r.property <> 'NaN'
```

### Fact Traversal
```cypher
Report -[:HAS_XBRL]-> XBRLNode <-[:REPORTS]- Fact
```

## Troubleshooting

1. **Redis Connection Failed**: Falls back to in-memory pattern storage
2. **MCP Service Unavailable**: Check if pod is running in mcp-services namespace
3. **Recursion Limit**: Increase MAX_STEPS if needed (default: 50)
4. **Empty Results**: Check if LIMIT clause is appropriate for query

## Future Enhancements

1. Add more sophisticated query templates
2. Implement query result caching
3. Add query performance tracking
4. Enhanced error message parsing