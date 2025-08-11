import json
import datetime
import re
import litellm
from graph.state import AgentState
from utils.ai_client import get_model_name

# ---- SYSTEM PROMPT TEMPLATE ----
SYSTEM_PROMPT_TEMPLATE = """
You are the central router and entity extractor for a project management bot. Your primary task is to analyze a user's request and convert it into a structured JSON object.

The JSON object MUST have two keys: "action" and "params".

1.  **"action"**: This value MUST be one of the following strings:
    - 'create_task', 'assign_task', 'working_task', 'completed_task', 'list_tasks', 'history', 'delete_task', 'task_details', 'create_project', 'delete_project', 'project_details', 'project_files', 'get_files', 'link', 'answer_project_question'.

2.  **"params"**: This is a dictionary of parameters for the action. The allowed keys for each action are defined in the "Parameter Schemas" section below. If a required parameter (like a project or task name) is not found in the user's request, its value MUST be `null`. Do not invent or assume values.

3.  **Date Handling**: The current date is **{current_date}**. All extracted dates must be resolved to the `YYYY-MM-DD` format.

4.  **Parameter Schemas**:
    - For 'create_task': `params` can include `name`, `description`, `project_name`, `assignee`, `deadline`.
    - For 'create_project': `params` must include `name`. `description` and `raw_input` are optional.
    - For 'assign_task': `params` must include `task_name`, `assignee`.
    - For 'delete_task': `params` must include `task_id`.
    - For 'project_details', 'project_files', 'get_files': `params` must include `project_name`. This is for when a user wants "details" or "information".
    - For 'answer_project_question': `params` must include `project_name` and `question`.
    - For all other actions, extract relevant entities as seen in the user's request.

Your final output MUST ONLY be the valid JSON object. Do not add explanations or markdown.
---
**Example 1: Create Project**
User Request: "let's start a new project called 'Q3 Marketing Campaign'. The main goal is to promote the new feature launch."
Your JSON Output:
{{"action": "create_project", "params": {{"name": "Q3 Marketing Campaign", "description": "The main goal is to promote the new feature launch", "raw_input": null}}}}
---
**Example 2: Create Task**
User Request: "Create a task 'Fix Bug' in project 'Test' for @Apoorav Malik due tomorrow"
Your JSON Output:
{{"action": "create_task", "params": {{"name": "Fix Bug", "description": null, "project_name": "Test", "assignee": "@Apoorav Malik", "deadline": "2025-07-20"}}}}
---
**Example 3: Assign Task (With Context)**
User Request: "assign this to @jane"
Context Task ID: `a1b2-c3d4`
Your JSON Output:
{{"action": "assign_task", "params": {{"task_name": null, "assignee": "@jane"}}}}
---
**Example 4: Create Project (Error)**
User Request: "create a project with the description 'A new project'"
Your JSON Output:
{{"action": "create_project", "params": {{"name": null, "description": "A new project", "raw_input": null}}}}
---
**Example 5: Create Project (Error)**
User Request: "create a project"
Your JSON Output:
{{"action": "create_project", "params": {{"name": null, "description": null, "raw_input": null}}}}
---
**Example 6: Project Details**
User Request: "show me the details for the 'Q3 Marketing Campaign' project"
Your JSON Output:
{{"action": "project_details", "params": {{"project_name": "Q3 Marketing Campaign"}}}}
---
**Example 7: Project Details**
User Request: "give me information on the 'Mobile App Refactor' project"
Your JSON Output:
{{"action": "project_details", "params": {{"project_name": "Mobile App Refactor"}}}}
---
**Example 8: Ask Question about Project**
User Request: "What is the basic plan for the 'Mobile App Refactor' project?"
Your JSON Output:
{{"action": "answer_project_question", "params": {{"project_name": "Mobile App Refactor", "question": "What is the basic plan for the project?"}}}}
---
**Example 9: Ask Question about Project (RAG)**
User Request: "Can you tell me about the files in the 'Mobile App Refactor' project?"
Your JSON Output:
{{"action": "answer_project_question", "params": {{"project_name": "Mobile App Refactor", "question": "What are the files in the project?"}}}}
---
**Example 10: Ask a specific question about a project**
User Request: "Can you tell for which position is the JD for in the 'Mobile App Refactor' project?"
Your JSON Output:
{{"action": "answer_project_question", "params": {{"project_name": "Mobile App Refactor", "question": "for which position is the JD for in the project?"}}}}
---
**Example 11: Another specific question**
User Request: "in the project 'New Website', what is the deadline for the design phase?"
Your JSON Output:
{{"action": "answer_project_question", "params": {{"project_name": "New Website", "question": "what is the deadline for the design phase"}}}}
"""


# ---- JSON EXTRACTION HELPER ----
def extract_json_from_content(content: str) -> dict:
    content = re.sub(r'^```(?:json)?\s*', '', content, flags=re.MULTILINE)
    content = re.sub(r'```\s*$', '', content, flags=re.MULTILINE)
    content = content.strip()
    json_pattern = r'\{.*\}'
    match = re.search(json_pattern, content, re.DOTALL)
    if match:
        json_str = match.group(0)
    else:
        json_str = content
    try:
        parsed_data = json.loads(json_str)
        while isinstance(parsed_data, str):
            parsed_data = json.loads(parsed_data)
        return parsed_data
    except json.JSONDecodeError as e:
        print(f"--- JSON Decode Error: {e} ---")
        print(f"--- Problematic JSON String: {json_str!r} ---")
        raise


# ---- INTENT NODE ----
async def user_intent_node(state: AgentState) -> dict:
    """
    Analyzes the user's input using LiteLLM with Groq.
    """
    print("--- 🧠 Running Intent Node (Groq via LiteLLM) ---")
    
    try:
        today = datetime.date.today()
        formatted_date = today.strftime('%A, %B %d, %Y')
        final_system_prompt = SYSTEM_PROMPT_TEMPLATE.format(current_date=formatted_date)


        # Build a more detailed prompt for the AI, including context if it exists.
        user_input = state['input']
        context_text = ""
        if state.get("task_id_from_reply"):
            print(f"--- 📝 Task ID found ---")
            context_text = f"\nContext Task ID: {state['task_id_from_reply']}"
        
        full_user_prompt = user_input + context_text
        
        response = await litellm.acompletion(
            model=get_model_name(),
            messages=[
                {"role": "system", "content": final_system_prompt},
                {"role": "user", "content": full_user_prompt} # Use the new, context-aware prompt
            ],
            response_format={"type": "json_object"},
        )
        
        content = response.choices[0].message.content
        result_json = extract_json_from_content(content)

        print(f"--- Intent Found: {result_json} ---")

        # Return only the new information to merge with the existing state
        return {
            "action": result_json.get("action"),
            "params": result_json.get("params", {})
        }
    except Exception as e:
        print(f"--- 💥 An unexpected error occurred in intent node: {e} ---")
        # If the AI fails, we set a response message directly.
        # This will be sent back to the user by the ai_handler.
        return {
            "response": "An unexpected error occurred while processing your request with the AI."
        }
