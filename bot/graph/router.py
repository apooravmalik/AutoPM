from graph.state import AgentState

def route_actions(state: AgentState) -> str:
    """
    Determines the next node to execute based on the 'action' in the state.
    """
    action = state.get("action")
    print(f"--- 🚦 Routing action: {action} ---")

    if action == "create_task":
        return "create_task_tool"
    
    # For any other action, or if the action is missing, end the conversation.
    return "__end__"