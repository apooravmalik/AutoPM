from graph.state import AgentState
from services.task_service import _create_task_service

async def create_task_tool(state: AgentState) -> dict:
    """
    Tool node that validates parameters from the AI and calls the create_task service.
    """
    print("--- 🛠️ Running Create Task Tool ---")
    params = state.get("params", {})
    
    # 1. Validation: Check for the required task name
    task_name = params.get("name")
    if not task_name:
        response = "The task name was missing from the prompt. Please add it and try again."
        return {"response": response}

    # 2. Call the shared service function with data from the agent's state
    success, message = _create_task_service(
        telegram_user_id=state.get("telegram_user_id"),
        group_id=state.get("chat_id"),
        title=task_name,
        description=params.get("description"),
        project_name=params.get("project_name"),
        deadline=params.get("deadline"),
    )

    # 3. Return the final message to the agent's state
    return {"response": message}