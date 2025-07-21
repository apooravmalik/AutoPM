from utils.supabaseClient import supabase
from utils.auth_helper import get_user_from_telegram, check_admin_permission
from typing import Tuple


def _create_task_service(
    telegram_user_id: int, 
    group_id: int,
    title: str, 
    description: str = None, 
    project_name: str = None, # project_name is optional
    deadline: str = None
) -> Tuple[bool, str]:
    """
    - Description: Create a new task (Admin only)
    - Required: title
    - Optional: description, project_name, deadline (YYYY-MM-DD format)
    Returns a tuple: (success, message).
    """
    try:
        # 1. Permission checks (always run for group tasks)
        user_data = get_user_from_telegram(telegram_user_id)
        if not user_data:
            return (False, "❌ User not linked. Please use /link first.")
            
        if not check_admin_permission(user_data["id"], group_id):
            return (False, "❌ Sorry, only admins can create tasks in groups.")

        # 2. Handle the optional project name
        project_id = None
        if project_name:
            project_res = supabase.from_("projects").select("id").eq("name", project_name).eq("group_id", group_id).execute()
            if project_res.data:
                project_id = project_res.data[0]["id"]
            # Note: If project_name is given but not found, we don't fail.
            # The project_id simply remains None.

        # 3. Insert task into Supabase
        task_data = {
            "title": title,
            "description": description,
            "status": "Pending",
            "group_id": group_id,
            "project_id": project_id, # Will be null if project not found
            "parent_task_id": None,
            "deadline": deadline
        }
        
        result = supabase.from_("tasks").insert(task_data).execute()

        if not result.data:
            return (False, "❌ Failed to create task in the database.")
            
        task_id = result.data[0]["id"]

        # 4. Format a dynamic success message
        project_text = ""
        if project_id and project_name:
             project_text = f"\n🏷️ **Project:** {project_name}"
        elif project_name and not project_id:
             # Inform the user that the specified project was not found
             project_text = f"\n⚠️ **Note:** Project '{project_name}' was not found, so this task is standalone."

        success_message = f"✅ **Task Created!**\n📋 **Title:** {title}\n **📝 Description:** {description}\n **📅 Deadline:** {deadline}\n 🆔 **ID:** `{task_id}`{project_text}"
        return (True, success_message)

    except Exception as e:
        print(f"Error in _create_task_service: {e}")
        return (False, "❗ A server error occurred while creating the task.")
    
def _assign_task_service(
    admin_telegram_user_id: int,
    group_id: int,
    assignee_username: str,
    task_name: str
) -> Tuple[bool, str]:
    """
    Core logic to assign a task, using a manual filter to bypass the .ilike() error.
    """
    try:
        # 1. Permission & User checks (remain the same)
        admin_user_data = get_user_from_telegram(admin_telegram_user_id)
        if not admin_user_data or not check_admin_permission(admin_user_data["id"], group_id):
            return (False, "❌ Sorry, only admins can assign tasks.")

        clean_username = assignee_username.replace("@", "")
        assignee_user = supabase.from_("telegram_users").select("id").eq("telegram_username", clean_username).single().execute()
        if not assignee_user.data:
            return (False, f"❌ User @{clean_username} not found or not linked.")
        assignee_id = assignee_user.data["id"]

        # 2. WORKAROUND: Fetch all pending tasks and filter in Python
        all_pending_tasks_res = supabase.from_("tasks").select("*").eq("group_id", group_id).eq("status", "Pending").execute()
        
        matching_tasks = []
        if all_pending_tasks_res.data:
            for task in all_pending_tasks_res.data:
                if task_name.lower() in task['title'].lower():
                    matching_tasks.append(task)

        # 3. Handle results (remain the same)
        if not matching_tasks:
            return (False, f"❌ No pending task found matching '{task_name}'.")
        if len(matching_tasks) > 1:
            task_list = "\n".join([f"• {task['title']}" for task in matching_tasks[:5]])
            return (False, f"❌ Multiple tasks found:\n{task_list}\n\nPlease be more specific.")
        
        task = matching_tasks[0]
        
        # 4. Update and Log (remain the same)
        update_result = supabase.from_("tasks").update({"assigned_to": assignee_id, "status": "Assigned"}).eq("id", task["id"]).execute()
        if not update_result.data:
            return (False, "❌ Failed to update the task in the database.")
        
        supabase.from_("status_logs").insert({"task_id": task["id"], "employee_id": assignee_id, "status": "assigned", "group_id": group_id, "notes": f"Task assigned to @{clean_username} by admin"}).execute()

        success_message = f"✅ **Task Assigned!**\n📋 **Task:** {task['title']}\n👤 **To:** @{clean_username}"
        return (True, success_message)

    except Exception as e:
        print(f"Error in _assign_task_service: {e}")
        return (False, "❗ A server error occurred while assigning the task.")

def _working_task_service(
    telegram_user_id: int,
    task_name: str,
    group_id: int = None
) -> Tuple[bool, str]:
    """
    Core logic to find a user's assigned task and mark it as "In Progress".
    Returns a tuple: (success, message).
    """
    try:
        # 1. Get user data
        user_data = get_user_from_telegram(telegram_user_id)
        if not user_data:
            return (False, "❌ Please link your Telegram account first using /link")

        # 2. Find the task assigned to this user
        query = supabase.from_("tasks").select("*").eq("assigned_to", user_data["id"]).ilike("title", f"%{task_name}%")
        
        # Filter by group if the command was used in one
        if group_id:
            query = query.eq("group_id", group_id)
        
        task_result = query.execute()

        # 3. Handle query results
        if not task_result.data:
            return (False, f"❌ No task '{task_name}' assigned to you was found.")

        if len(task_result.data) > 1:
            task_list = "\n".join([f"• {task['title']}" for task in task_result.data[:5]])
            return (False, f"❌ Multiple tasks found matching that name:\n{task_list}\n\nPlease be more specific.")

        task = task_result.data[0]
        
        # 4. Update task status
        update_result = supabase.from_("tasks").update({"status": "In Progress"}).eq("id", task["id"]).execute()

        if not update_result.data:
            return (False, "❌ Failed to update task status in the database.")
            
        # 5. Log the status change
        supabase.from_("status_logs").insert({
            "task_id": task["id"],
            "employee_id": user_data["id"],
            "status": "working",
            "group_id": group_id,
            "notes": "Task status changed to In Progress"
        }).execute()

        # 6. Format and return success message
        success_message = f"🚀 **Task Started!**\n📋 **Task:** {task['title']}\n📊 **Status:** In Progress"
        return (True, success_message)

    except Exception as e:
        print(f"Error in _working_task_service: {e}")
        return (False, "❗ An unexpected error occurred.")