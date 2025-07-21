from graph.state import AgentState

def route_actions(state: AgentState) -> str:
    """
    A placeholder router. For now, it just prints the action and ends the graph.
    """
    action = state.get("action")
    print(f"--- 🚦 Routing action: {action} ---")

    # In the future, this will return the name of a tool node.
    # For now, we simply end the graph for all actions.
    return "__end__"