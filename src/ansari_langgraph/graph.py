"""Graph construction for Ansari LangGraph agent."""

from langgraph.graph import StateGraph, END
from ansari_langgraph.state import AnsariState
from ansari_langgraph.nodes import create_agent_node, tool_node, finalize_node


def route_after_agent(state: AnsariState) -> str:
    """Route to tool or finalize based on agent decision."""
    stop_reason = state.get("stop_reason")

    if stop_reason == "tool_use":
        return "tool_node"
    else:
        return "finalize_node"


def create_graph(model: str = "claude-sonnet-4-20250514"):
    """Create the Ansari agent graph.

    Args:
        model: Anthropic model name to use
    """
    # Create graph
    graph = StateGraph(AnsariState)

    # Create agent node with specified model
    agent_node = create_agent_node(model=model)

    # Add nodes
    graph.add_node("agent_node", agent_node)
    graph.add_node("tool_node", tool_node)
    graph.add_node("finalize_node", finalize_node)

    # Set entry point
    graph.set_entry_point("agent_node")

    # Add conditional routing from agent
    graph.add_conditional_edges(
        "agent_node",
        route_after_agent,
        {
            "tool_node": "tool_node",
            "finalize_node": "finalize_node",
        },
    )

    # Tool node goes back to agent for final response
    graph.add_edge("tool_node", "agent_node")

    # Finalize ends the graph
    graph.add_edge("finalize_node", END)

    return graph.compile()
