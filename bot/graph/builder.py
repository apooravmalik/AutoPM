from langgraph.graph import StateGraph, END
from graph.state import AgentState
from graph.nodes.intent import user_intent_node
from graph.nodes.tools import create_task_tool
from graph.router import route_actions

# Define the workflow
workflow = StateGraph(AgentState)

# Add the nodes to the graph
workflow.add_node("intent", user_intent_node)
workflow.add_node("create_task_tool", create_task_tool)

# Set the entry point for the graph
workflow.set_entry_point("intent")

# Add the conditional router.
# After the 'intent' node, the 'route_actions' function will be called.
# Based on its return value, the graph will transition to the specified node.
workflow.add_conditional_edges(
    "intent",
    route_actions,
    {
        "create_task_tool": "create_task_tool",
        "__end__": END
    }
)

# After the tool is executed, the graph ends.
workflow.add_edge("create_task_tool", END)

# Compile the graph into our final, runnable app
app = workflow.compile()