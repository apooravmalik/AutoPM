from graph.state import AgentState
from services.task_service import _create_task_service, _assign_task_service

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


async def assign_task_tool(state: AgentState) -> dict:
    """
    Tool to assign a task. It prioritizes using a task ID from a reply,
    but falls back to searching by name.
    """
    print("--- 🛠️ Running Assign Task Tool ---")
    params = state.get("params", {})
    
    # 1. Validation: Check for the required assignee
    assignee = params.get("assignee")
    if not assignee:
        return {"response": "An assignee (@username) was missing from the prompt. Please add it and try again."}

    # 2. Get task identifier (ID from reply takes precedence)
    task_id = state.get("task_id_from_reply")
    task_name = params.get("task_name")

    if not task_id and not task_name:
        return {"response": "The task name was missing. Please specify which task to assign or reply to a task message."}

    # 3. Call the shared service function
    # Note: We will need to update _assign_task_service to accept task_id
    success, message = _assign_task_service(
        admin_telegram_user_id=state.get("telegram_user_id"),
        group_id=state.get("chat_id"),
        assignee_username=assignee,
        task_name=task_name,
        task_id=task_id # Pass the ID to the service
    )
    return {"response": message}