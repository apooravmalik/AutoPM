from langgraph.graph import StateGraph, END
from graph.state import AgentState
from graph.nodes.intent import user_intent_node
from graph.nodes.tools import create_task_tool, assign_task_tool, create_project_tool, project_details_tool, answer_project_question_tool
from graph.router import route_actions

workflow = StateGraph(AgentState)

# Add the nodes
workflow.add_node("intent", user_intent_node) #Node for Intent
workflow.add_node("create_task_tool", create_task_tool) #Node for Create Task tool
workflow.add_node("assign_task_tool", assign_task_tool) # Node for Assign Tool
workflow.add_node("create_project_tool", create_project_tool) # Node for Create Project tool
workflow.add_node("project_details_tool", project_details_tool) # Node for Project Details tool
workflow.add_node("answer_project_question_tool", answer_project_question_tool) # Node for Answer Project Question tool

workflow.set_entry_point("intent")

# Add the conditional router
workflow.add_conditional_edges(
    "intent",
    route_actions,
    {
        "create_task_tool": "create_task_tool", # Route to Create Task tool
        "assign_task_tool": "assign_task_tool", # Route to Assign Task tool
        "create_project_tool": "create_project_tool", # Route to Create Project tool
        "project_details_tool": "project_details_tool", # Route to Project Details tool
        "answer_project_question_tool": "answer_project_question_tool", # Route to Answer Project Question tool
        # If no action matches, end the workflow
        "__end__": END
    }
)

# Add edges from all tools back to the end
workflow.add_edge("create_task_tool", END)
workflow.add_edge("assign_task_tool", END)
workflow.add_edge("create_project_tool", END)
workflow.add_edge("project_details_tool", END)
workflow.add_edge("answer_project_question_tool", END)

app = workflow.compile()
