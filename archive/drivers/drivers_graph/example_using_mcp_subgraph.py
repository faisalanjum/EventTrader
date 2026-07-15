"""Example of using MCP agent as a subgraph in a larger workflow"""
from langgraph.graph import StateGraph, END
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from drivers.drivers_graph.mcp_agent_minimal import mcp_minimal_graph

class WorkflowState(TypedDict):
    messages: Annotated[list, add_messages]
    analysis_needed: bool
    mcp_result: str

def create_workflow_with_mcp():
    workflow = StateGraph(WorkflowState)
    
    # Regular nodes
    async def analyze_request(state):
        """Determine if we need database analysis"""
        last_msg = state["messages"][-1]
        needs_db = "database" in last_msg.content.lower() or "find" in last_msg.content.lower()
        return {"analysis_needed": needs_db}
    
    async def process_other(state):
        """Handle non-database requests"""
        return {"mcp_result": "Handled without database query"}
    
    # Add nodes
    workflow.add_node("analyze", analyze_request)
    workflow.add_node("mcp_agent", mcp_minimal_graph)  # Use as subgraph!
    workflow.add_node("other", process_other)
    
    # Routing
    def route_request(state):
        if state.get("analysis_needed"):
            return "mcp_agent"
        return "other"
    
    # Build flow
    workflow.set_entry_point("analyze")
    workflow.add_conditional_edges("analyze", route_request)
    workflow.add_edge("mcp_agent", END)
    workflow.add_edge("other", END)
    
    return workflow.compile()

# Usage
async def main():
    workflow = create_workflow_with_mcp()
    result = await workflow.ainvoke({
        "messages": [{"role": "user", "content": "Find the highest daily stock return"}]
    })