from langgraph.graph import StateGraph, END
from graph.state import AgentState
from graph.nodes.intent import user_intent_node
from graph.router import route_actions

# Define the workflow
workflow = StateGraph(AgentState)

# Add the nodes
workflow.add_node("intent", user_intent_node)

# Set the entry point
workflow.set_entry_point("intent")

# Add the conditional router
# After the "intent" node, it will call "route_actions" to decide where to go.
workflow.add_conditional_edges(
    "intent",
    route_actions,
    {
        # For now, all paths lead to the end.
        # Later, we'll add paths like: "create_project_tool": "create_project_tool"
        "__end__": END
    }
)

# Compile the graph into our final app
app = workflow.compile()