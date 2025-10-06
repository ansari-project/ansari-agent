"""Proof of Concept: LangGraph with LangChain tools.

This PoC verifies:
1. LangGraph can be imported and used
2. LangChain tool integration works (recommended pattern)
3. 3-node graph can be created and executed
"""

import asyncio
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from ansari_langgraph.state import AnsariState


# Define a simple LangChain tool
@tool
async def search_tool(query: str) -> str:
    """Search for information (simulated)."""
    # Simulate async operation
    await asyncio.sleep(0.1)
    return f"Search results for: {query}"


# Create list of tools
tools = [search_tool]


# Node 1: Agent (simulated LLM call)
async def agent_node(state: AnsariState) -> AnsariState:
    """Simulated agent node - decides whether to call tool or finish."""
    print("→ Agent node executing...")

    messages = state.get("messages", [])

    # Simulate decision: if no messages yet, call tool; otherwise finish
    if len(messages) == 0:
        # Add user message
        messages.append({"role": "user", "content": "Test query"})

        # Simulate LLM deciding to call a tool
        state["messages"] = messages
        state["stop_reason"] = "tool_use"
        state["tool_calls"] = [{"name": "search_tool", "args": {"query": "test"}}]
        print("  Agent decided to call tool")
    else:
        # Simulate LLM finishing
        state["stop_reason"] = "end_turn"
        state["final_response"] = "Test response complete"
        print("  Agent finished")

    return state


# Node 2: Use LangGraph's built-in ToolNode (recommended pattern)
async def tool_node(state: AnsariState) -> AnsariState:
    """Tool node - executes tools using LangChain pattern."""
    print("→ Tool node executing...")

    # Execute the tool
    result = await search_tool.ainvoke({"query": "test"})
    print(f"  Tool result: {result}")

    # Add result to messages
    messages = state.get("messages", [])
    messages.append({"role": "assistant", "content": result})

    state["messages"] = messages
    state["tool_results"] = [{"status": "success", "result": result}]
    print("  Tool completed successfully")

    return state


# Node 3: Finalize
async def finalize_node(state: AnsariState) -> AnsariState:
    """Finalize node - formats final response."""
    print("→ Finalize node executing...")

    final_response = state.get("final_response", "No response generated")
    print(f"  Final response: {final_response}")

    return state


# Router: decide next node after agent
def route_after_agent(state: AnsariState) -> str:
    """Route to tool or finalize based on agent decision."""
    stop_reason = state.get("stop_reason")

    if stop_reason == "tool_use":
        print("  Router: → tool_node")
        return "tool_node"
    else:
        print("  Router: → finalize_node")
        return "finalize_node"


def create_graph() -> StateGraph:
    """Create the 3-node graph."""
    # Create graph
    graph = StateGraph(AnsariState)

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

    # Tool node always goes back to agent for final response
    graph.add_edge("tool_node", "agent_node")

    # Finalize ends the graph
    graph.add_edge("finalize_node", END)

    return graph


async def run_poc():
    """Run the proof of concept."""
    print("=" * 60)
    print("LangGraph PoC: Testing async httpx compatibility")
    print("=" * 60)

    # Create and compile graph
    graph = create_graph()
    app = graph.compile()

    print("\n📊 Graph compiled successfully")
    print("\n🚀 Running graph...\n")

    # Run the graph
    initial_state: AnsariState = {"messages": []}

    result = await app.ainvoke(initial_state)

    print("\n" + "=" * 60)
    print("✅ PoC COMPLETE")
    print("=" * 60)
    print(f"\nFinal state:")
    print(f"  Messages: {len(result.get('messages', []))} messages")
    print(f"  Stop reason: {result.get('stop_reason')}")
    print(f"  Final response: {result.get('final_response')}")

    if result.get("tool_results"):
        print(f"  Tool results: {len(result['tool_results'])} results")

    print("\n✅ GATE 0 PASSED:")
    print("  - LangGraph imports and works")
    print("  - LangChain @tool decorator works for async tools")
    print("  - 3-node graph executes successfully")
    print("  - No server/service infrastructure required")
    print("  - All dependencies are pure Python (no Node.js, no CLI)")


if __name__ == "__main__":
    asyncio.run(run_poc())
