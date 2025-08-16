from graph.state import AgentState
from utils.supabaseClient import supabase
from services.task_service import _create_task_service, _assign_task_service
from services.project_service import _create_project_service, _project_details_service, _answer_project_question_service
from services.report_service import _summary_service

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

async def create_project_tool(state: AgentState) -> dict:
    """
    Tool node that validates parameters from the AI and calls the create_project service.
    """
    print("--- 🛠️ Running Create Project Tool ---")
    params = state.get("params", {})

    # 1. Validation: Check for the required project name
    project_name = params.get("name")
    if not project_name:
        response = "The project name was missing from the prompt. Please add it and try again."
        return {"response": response}

    # 2. Call the shared service function with data from the agent's state
    success, message = _create_project_service(
        telegram_user_id=state.get("telegram_user_id"),
        group_id=state.get("chat_id"),
        name=project_name,
        description=params.get("description"),
        raw_input=params.get("raw_input"),
    )

    # 3. Return the final message to the agent's state
    return {"response": message}

async def project_details_tool(state: AgentState) -> dict:
    """
    Tool node that validates parameters from the AI and calls the project_details service.
    """
    print("--- 🛠️ Running Project Details Tool ---")
    params = state.get("params", {})

    # 1. Validation: Check for the required project name
    project_name = params.get("project_name")
    if not project_name:
        response = "The project name was missing from the prompt. Please add it and try again."
        return {"response": response}

    # 2. Call the shared service function with data from the agent's state
    success, message = _project_details_service(
        telegram_user_id=state.get("telegram_user_id"),
        group_id=state.get("chat_id"),
        project_name=project_name,
    )

    # 3. Return the final message to the agent's state
    return {"response": message}

async def answer_project_question_tool(state: AgentState) -> dict:
    """
    Tool to answer a user's question about a project using RAG.
    """
    print("--- 🛠️ Running Answer Project Question Tool ---")
    params = state.get("params", {})
    
    project_name = params.get("project_name")
    question = params.get("question")

    if not project_name or not question:
        return {"response": "Please specify which project you are asking about and what your question is."}

    success, message = await _answer_project_question_service(
        project_name=project_name,
        question=question,
        group_id=state.get("chat_id")
    )
    return {"response": message}

async def summary_tool(state: AgentState) -> dict:
    """
    Tool to generate a summary of tasks.
    """
    print("--- 🛠️ Running Summary Tool ---")
    try:
        params = state.get("params", {})
        project_name = params.get("project_name")
        days = params.get("days", 7)

        print(f" tools.py ----- Generating summary for project '{project_name}' in group {state.get('chat_id')} for the last {days} days")
        if not project_name or project_name.lower() == "all projects":
            # Get all projects
            projects_res = supabase.from_("projects").select("name").eq("group_id", state.get("chat_id")).execute()
            if not projects_res.data:
                return {"response": "No projects found to summarize."}
            
            messages = []
            for project in projects_res.data:
                success, message = _summary_service(
                    telegram_user_id=state.get("telegram_user_id"),
                    group_id=state.get("chat_id"),
                    project_name=project['name'],
                    days=days
                )
                messages.append(message)
            return {"response": "\n\n---\n\n".join(messages)}
        else:
            success, message = _summary_service(
                telegram_user_id=state.get("telegram_user_id"),
                group_id=state.get("chat_id"),
                project_name=project_name,
                days=days
            )
            return {"response": message}
    except Exception as e:
        print(f"Error in summary_tool: {e}")
        return {"response": "An error occurred while generating the summary."}