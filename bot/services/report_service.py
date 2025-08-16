# bot/services/report_service.py

from utils.supabaseClient import supabase
from utils.auth_helper import get_user_from_telegram, check_admin_permission
from typing import Tuple
from datetime import datetime, timedelta

def _summary_service(
    telegram_user_id: int,
    group_id: int,
    project_name: str = None,
    days: int = 7
) -> Tuple[bool, str]:
    """
    Core logic to generate a summary of tasks.
    Returns a tuple: (success, message).
    """
    try:
        # 1. Permission checks
        user_data = get_user_from_telegram(telegram_user_id)
        if not user_data:
            return (False, "❌ User not linked. Please use /link first.")

        if not check_admin_permission(user_data["id"], group_id):
            return (False, "❌ Sorry, only admins can request a summary.")

        # 2. Fetch project ID if project_name is provided
        project_id = None
        if project_name:
            project_res = supabase.from_("projects").select("id").eq("name", project_name).eq("group_id", group_id).single().execute()
            if not project_res.data:
                return (False, f"❌ Project '{project_name}' not found.")
            project_id = project_res.data['id']

        # 3. Fetch tasks
        date_threshold = datetime.now() - timedelta(days=days)
        
        query = supabase.from_("tasks").select("*").eq("group_id", group_id).gte("created_at", date_threshold)
        
        if project_id:
            query = query.eq("project_id", project_id)

        tasks_res = query.execute()

        if not tasks_res.data:
            return (True, f"📊 No tasks found in the last {days} days for {project_name}.")

        tasks = tasks_res.data

        # 4. Fetch user details for assigned tasks
        user_id_map = {}
        for task in tasks:
            if task.get('assigned_to'):
                user_id = task['assigned_to']
                if user_id not in user_id_map:
                    user_res = supabase.from_("telegram_users").select("telegram_username").eq("id", user_id).single().execute()
                    if user_res.data:
                        user_id_map[user_id] = user_res.data.get('telegram_username', 'unknown')

        # 5. Categorize tasks
        in_progress_tasks = [task for task in tasks if task['status'] == 'In Progress']
        completed_tasks = [task for task in tasks if task['status'] == 'Completed']
        missed_deadlines = [task for task in tasks if task.get('deadline') and datetime.strptime(task['deadline'], "%Y-%m-%d").date() < datetime.now().date() and task['status'] != 'Completed']

        # 6. Sort completed tasks by completion date (newest first)
        completed_tasks.sort(key=lambda t: t.get('updated_at'), reverse=True)

        # 7. Helper function to format task lines
        def format_task_line(task):
            user_info = ""
            if task.get('assigned_to'):
                username = user_id_map.get(task['assigned_to'], 'unknown')
                user_info = f" (@{username})"
            
            deadline_info = ""
            if task.get('deadline'):
                deadline_info = f" (Due: {task['deadline']})"

            return f"   • {task['title']}{user_info}{deadline_info}\n"

        # 8. Build the summary message
        project_title = f"for Project '{project_name}'" if project_name else ""
        message = f"📊 **Project Summary {project_title} (Last {days} Days)**\n\n"

        # In Progress Tasks
        message += f"🚀 **In Progress ({len(in_progress_tasks)})**\n"
        if in_progress_tasks:
            for task in in_progress_tasks:
                message += format_task_line(task)
        else:
            message += "   No tasks in progress.\n"
        message += "\n"

        # Recently Completed Tasks
        message += f"✅ **Recently Completed ({len(completed_tasks)})**\n"
        if completed_tasks:
            for task in completed_tasks[:3]: # Show the latest 3
                message += format_task_line(task)
        else:
            message += "   No tasks completed recently.\n"
        message += "\n"
        
        # Missed Deadlines
        message += f"⚠️ **Missed Deadlines ({len(missed_deadlines)})**\n"
        if missed_deadlines:
            for task in missed_deadlines:
                message += format_task_line(task)
        else:
            message += "   No missed deadlines.\n"

        return (True, message)

    except Exception as e:
        print(f"Error in _summary_service: {e}")
        return (False, "❗ An unexpected error occurred while generating the summary.")







