from langgraph.graph import StateGraph, END
from drivers.drivers_graph.state import AttributionState
from drivers.drivers_graph.nodes import filter_events, analyze_attribution, format_output

def create_graph():
    g = StateGraph(AttributionState)
    # Async nodes work seamlessly in LangGraph
    g.add_node("filter", filter_events)
    g.add_node("analyze", analyze_attribution)
    g.add_node("format", format_output)
    g.set_entry_point("filter")
    g.add_edge("filter", "analyze")
    g.add_edge("analyze", "format")
    g.add_edge("format", END)
    return g.compile()

# Export the compiled graph for LangGraph Studio
graph = create_graph()