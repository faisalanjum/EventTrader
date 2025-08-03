"""Example of using MCP agent as a tool in a larger workflow"""
from langchain.tools import Tool
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from drivers.drivers_graph.mcp_neo4j_agent import neo4j_mcp_agent
import asyncio

class WorkflowState(TypedDict):
    messages: Annotated[list, add_messages]
    analysis_result: str

# Wrap the MCP agent as a tool
async def query_neo4j(query: str) -> str:
    """
    Query the Neo4j database using the MCP agent.
    This tool handles complex database queries with full schema awareness.
    """
    result = await neo4j_mcp_agent.ainvoke({
        "messages": [{"role": "user", "content": query}]
    })
    
    # Extract the final response from the agent
    last_message = result["messages"][-1]
    return last_message.content

# Create the tool
neo4j_tool = Tool(
    name="neo4j_query",
    description="Query the Neo4j EventMarketDB database. Use this for any database-related questions.",
    func=lambda x: asyncio.run(query_neo4j(x))  # Sync wrapper for async function
)

def create_workflow_with_tool():
    """Create a workflow that uses MCP agent as a tool"""
    workflow = StateGraph(WorkflowState)
    
    # Agent node that can use the Neo4j tool
    async def agent_with_tools(state):
        """Agent that decides when to use the Neo4j tool"""
        # Create model with the tool
        model = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            temperature=0
        ).bind_tools([neo4j_tool])
        
        # Invoke with user message
        response = await model.ainvoke(state["messages"])
        
        # If tool was called, execute it
        if hasattr(response, 'tool_calls') and response.tool_calls:
            tool_results = []
            for tool_call in response.tool_calls:
                if tool_call['name'] == 'neo4j_query':
                    result = await query_neo4j(tool_call['args']['query'])
                    tool_results.append(result)
            
            # Return tool results
            return {
                "messages": [response],
                "analysis_result": "\n".join(tool_results)
            }
        
        return {"messages": [response]}
    
    # Add nodes
    workflow.add_node("agent", agent_with_tools)
    
    # Set flow
    workflow.set_entry_point("agent")
    workflow.add_edge("agent", END)
    
    return workflow.compile()

# Alternative: Direct function usage
async def use_mcp_directly(query: str):
    """
    Directly use the MCP agent graph without wrapping as tool.
    This is the simplest approach for programmatic usage.
    """
    result = await neo4j_mcp_agent.ainvoke({
        "messages": [{"role": "user", "content": query}]
    })
    return result["messages"][-1].content

# Example usage patterns
async def main():
    # Pattern 1: As a tool in a larger agent
    workflow = create_workflow_with_tool()
    result = await workflow.ainvoke({
        "messages": [{"role": "user", "content": "Query the database to find companies with highest returns"}]
    })
    
    # Pattern 2: Direct invocation
    direct_result = await use_mcp_directly("Find News that influenced AAPL")
    
    # Pattern 3: In existing code
    # You can import and use mcp_minimal_graph.ainvoke() anywhere in your codebase