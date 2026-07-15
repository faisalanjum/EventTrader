"""Ultra-minimal MCP React Agent with multi-model support"""
import json, asyncio, os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)

from eventtrader import keys
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition, create_react_agent
from langgraph.graph import StateGraph, START, END, MessagesState

# Setup API keys
os.environ["OPENAI_API_KEY"] = keys.OPENAI_API_KEY
if keys.ANTHROPIC_API_KEY: os.environ["ANTHROPIC_API_KEY"] = keys.ANTHROPIC_API_KEY
if keys.GEMINI_API_KEY: os.environ["GOOGLE_API_KEY"] = keys.GEMINI_API_KEY

mcp_client = MultiServerMCPClient({"neo4j": {"url": "http://localhost:31380/mcp", "transport": "streamable_http"}})

# Tools
async def get_tools():
    mcp_tools = await mcp_client.get_tools()
    @tool
    async def run_cypher_query(query: str) -> str:
        """Executes a Cypher query on the Neo4j MCP server."""
        tools = await mcp_client.get_tools()
        read_tool = next(t for t in tools if t.name == "read_neo4j_cypher")
        result = await read_tool.ainvoke({"query": query})
        return json.loads(result)
    return mcp_tools + [run_cypher_query]

# Model selection - uncomment the model you want to use
# MODEL = 'gpt-4'  # OpenAI GPT-4
# MODEL = 'gpt-4o'  # OpenAI GPT-4 Optimized
# MODEL = 'opus-4'  # Anthropic Claude Opus 4 ($15/$75 per M tokens)
# MODEL = 'sonnet-4'  # Anthropic Claude Sonnet 4 ($3/$15 per M tokens)
# MODEL = 'claude'  # Anthropic Claude 3.5 Sonnet
# MODEL = 'gemini'  # Google Gemini 2.5 Flash
# MODEL = 'gemini-2.0'  # Google Gemini 2.0 Flash
MODEL = 'gpt-4'  # Default

MODEL_MAP = {
    # OpenAI models
    'gpt-4': 'openai:gpt-4',
    'gpt-4o': 'openai:gpt-4o',
    # Anthropic Claude 4 models (latest)
    'opus-4': 'anthropic:claude-opus-4-20250514',
    'sonnet-4': 'anthropic:claude-sonnet-4-20250514',
    # Anthropic Claude 3.5 models
    'claude': 'anthropic:claude-3-5-sonnet-latest',
    'claude-sonnet': 'anthropic:claude-3-5-sonnet-latest',
    'claude-haiku': 'anthropic:claude-3-5-haiku-latest',
    # Google Gemini models
    'gemini': 'google_genai:gemini-2.5-flash',
    'gemini-2.5': 'google_genai:gemini-2.5-flash',
    'gemini-2.0': 'google_genai:gemini-2.0-flash'
}

# Build graph with schema and read tool nodes
all_tools = asyncio.new_event_loop().run_until_complete(get_tools())

# Filter to only schema and read tools
schema_tool = next(t for t in all_tools if t.name == "get_neo4j_schema")
read_tools = [t for t in all_tools if t.name in ["read_neo4j_cypher", "run_cypher_query"]]
tools = [schema_tool] + read_tools

# Create agent with custom routing
from langchain.chat_models import init_chat_model
llm = init_chat_model(MODEL_MAP[MODEL])
llm_with_tools = llm.bind_tools(tools)

# Agent node that works with custom tool nodes
async def agent(state):
    messages = state["messages"]
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}

# Custom routing that returns our node names
def route_tools(state):
    messages = state["messages"]
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        tool_name = last_message.tool_calls[0]["name"]
        if tool_name == "get_neo4j_schema":
            return "schema"
        else:
            return "read"
    return END

builder = StateGraph(MessagesState)
builder.add_node("agent", agent)
builder.add_node("schema", ToolNode([schema_tool]))
builder.add_node("read", ToolNode(read_tools))
builder.add_edge(START, "agent")
builder.add_conditional_edges(
    "agent",
    route_tools,
    {
        "schema": "schema",
        "read": "read",
        END: END
    }
)
builder.add_edge("schema", "agent")
builder.add_edge("read", "agent")
mcp_agent = builder.compile()