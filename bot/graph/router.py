from graph.state import AgentState

def route_actions(state: AgentState) -> str:
    """
    Determines the next node to execute based on the 'action' in the state.
    """
    action = state.get("action")
    print(f"--- 🚦 Routing action: {action} ---")

    if action == "create_task":
        return "create_task_tool"
    if action == "assign_task":
        return "assign_task_tool"
    
    return "__end__"