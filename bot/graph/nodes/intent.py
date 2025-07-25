import json
import datetime
import re
from graph.state import AgentState
from utils.ai_client import get_ai_client

# ---- SYSTEM PROMPT TEMPLATE ----
SYSTEM_PROMPT_TEMPLATE = """
You are the central router and entity extractor for a project management bot. Your primary task is to analyze a user's request and convert it into a structured JSON object.

The JSON object MUST have two keys: "action" and "params".

1.  **"action"**: This value MUST be one of the following strings:
    - 'create_task', 'assign_task', 'working_task', 'completed_task', 'list_tasks', 'history', 'delete_task', 'task_details', 'create_project', 'delete_project', 'project_details', 'project_files', 'get_files', 'link', 'general_chat'.

2.  **"params"**: This is a dictionary of parameters for the action. The allowed keys for each action are defined in the "Parameter Schemas" section below. If a parameter is not found, its value MUST be `null`.

3.  **Date Handling**: The current date is **{current_date}**. All extracted dates must be resolved to the `YYYY-MM-DD` format.

4.  **Parameter Schemas**:
    - For 'create_task': `params` can include `name`, `description`, `project_name`, `assignee`, `deadline`.
    - For 'create_project': `params` can include `name`, `description`, `raw_input`.
    - For 'assign_task': `params` must include `task_name`, `assignee`.
    - For 'delete_task': `params` must include `task_id`.
    - For 'project_details', 'project_files', 'get_files': `params` must include `project_name`.
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
**Example 3: Project Details (by Name)**
User Request: "tell me about the 'Website Redesign' project"
Your JSON Output:
{{"action": "project_details", "params": {{"project_name": "Website Redesign"}}}}

---
**Example 4: No Parameters**
User Request: "show me my tasks"
Your JSON Output:
{{"action": "list_tasks", "params": {{}}}}

---
**Example 5: General Chat**
User Request: "hello bot how are you"
Your JSON Output:
{{"action": "general_chat", "params": {{}}}}
"""


# ---- JSON EXTRACTION HELPER ----
def extract_json_from_content(content: str) -> dict:
    """
    Robustly extract JSON from AI response content.
    """
    # (Copy your full extract_json_from_content() function here)
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
    Analyzes the user's input to determine their intent and extract parameters.
    """
    # (Copy your full user_intent_node() function here)
    print("--- 🧠 Running Intent Node ---")
    try:
        client = get_ai_client()
        today = datetime.date.today()
        formatted_date = today.strftime('%A, %B %d, %Y')
        final_system_prompt = SYSTEM_PROMPT_TEMPLATE.format(current_date=formatted_date)
        response = await client.chat.completions.create(
            model="mistralai/mistral-7b-instruct",
            messages=[
                {"role": "system", "content": final_system_prompt},
                {"role": "user", "content": state['input']}
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        print(f"--- AI Raw Content: {content!r} ---")
        result_json = extract_json_from_content(content)
        if not isinstance(result_json, dict):
            raise TypeError(f"AI response is not a dictionary: {type(result_json)}")
        if "action" not in result_json or "params" not in result_json:
            raise ValueError(f"AI response missing required keys. Got: {list(result_json.keys())}")
        print(f"--- Intent Found: {result_json} ---")
        return {
            "action": result_json.get("action"),
            "params": result_json.get("params", {}),
            "response": f"Action: `{result_json.get('action')}`\nParameters: `{result_json.get('params', {})}`"
        }
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        print(f"--- ⚠️ Error parsing AI response: {e} ---")
        return { "action": "general_chat", "params": {}, "response": "Sorry, I had trouble understanding the response from the AI. Please try rephrasing."}
    except Exception as e:
        print(f"--- 💥 An unexpected error occurred in intent node: {e} ---")
        return { "action": "general_chat", "params": {}, "response": "An unexpected error occurred."}