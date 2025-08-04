from utils.supabaseClient import supabase
from utils.auth_helper import get_user_from_telegram, check_admin_permission
from typing import Tuple, List
from datetime import datetime


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
    task_name: str = None,
    task_id: str = None # Add task_id as an optional parameter
) -> Tuple[bool, str]:
    """
    Core logic to assign a task to a user, finding the task by ID or by name.
    Returns a tuple: (success, message).
    """
    try:
        # 1. Permission checks (same as before)
        admin_user_data = get_user_from_telegram(admin_telegram_user_id)
        if not admin_user_data or not check_admin_permission(admin_user_data["id"], group_id):
            return (False, "❌ Sorry, only admins can assign tasks.")

        # 2. Find the assignee by their username (same as before)
        clean_username = assignee_username.replace("@", "")
        assignee_user = supabase.from_("telegram_users").select("id").eq("telegram_username", clean_username).single().execute()
        
        if not assignee_user.data:
            return (False, f"❌ User @{clean_username} not found or not linked to the bot.")
            
        assignee_id = assignee_user.data["id"]

        # 3. Find the task (ID takes priority)
        task = None
        if task_id:
            # If an ID is provided (from a reply), find the task directly.
            task_res = supabase.from_("tasks").select("*").eq("id", task_id).eq("group_id", group_id).single().execute()
            if task_res.data:
                task = task_res.data
        elif task_name:
            # If no ID, fall back to searching by name (using our workaround)
            all_pending_tasks_res = supabase.from_("tasks").select("*").eq("group_id", group_id).eq("status", "Pending").execute()
            matching_tasks = []
            if all_pending_tasks_res.data:
                for t in all_pending_tasks_res.data:
                    if task_name.lower() in t['title'].lower():
                        matching_tasks.append(t)
            
            if len(matching_tasks) == 1:
                task = matching_tasks[0]
            elif len(matching_tasks) > 1:
                return (False, f"❌ Multiple pending tasks found matching '{task_name}'. Please be more specific.")

        if not task:
            return (False, f"❌ No pending task found for the given details.")
        
        # 4. Update the task with the assignee and new status
        update_result = supabase.from_("tasks").update({
            "assigned_to": assignee_id,
            "status": "Assigned"
        }).eq("id", task["id"]).execute()

        if not update_result.data:
            return (False, "❌ Failed to update the task in the database.")

        # 5. Log the assignment event (same as before)
        supabase.from_("status_logs").insert({
            "task_id": task["id"],
            "employee_id": assignee_id,
            "status": "assigned",
            "group_id": group_id,
            "notes": f"Task assigned to @{clean_username} by admin"
        }).execute()

        # 6. Return a success message (same as before)
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
    Core logic to find a user's assigned task and mark it as "In Progress",
    using a manual filter to bypass the .ilike() error.
    """
    try:
        # 1. Get user data
        user_data = get_user_from_telegram(telegram_user_id)
        if not user_data:
            return (False, "❌ Please link your Telegram account first using /link")

        # 2. WORKAROUND: Fetch all tasks assigned to the user without the ILIKE filter
        query = supabase.from_("tasks").select("*").eq("assigned_to", user_data["id"]).eq("status", "Assigned")
        
        if group_id:
            query = query.eq("group_id", group_id)
        
        all_assigned_tasks_res = query.execute()

        # 3. Filter the results manually in Python
        matching_tasks = []
        if all_assigned_tasks_res.data:
            for task in all_assigned_tasks_res.data:
                # Case-insensitive check of the title
                if task_name.lower() in task['title'].lower():
                    matching_tasks.append(task)
        
        # 4. Handle the filtered results
        if not matching_tasks:
            return (False, f"❌ No task '{task_name}' assigned to you was found.")

        if len(matching_tasks) > 1:
            task_list = "\n".join([f"• {task['title']}" for task in matching_tasks[:5]])
            return (False, f"❌ Multiple tasks found matching that name:\n{task_list}\n\nPlease be more specific.")

        task = matching_tasks[0]
        
        # 5. Update task status
        update_result = supabase.from_("tasks").update({"status": "In Progress"}).eq("id", task["id"]).execute()

        if not update_result.data:
            return (False, "❌ Failed to update task status in the database.")
            
        # 6. Log the status change
        supabase.from_("status_logs").insert({
            "task_id": task["id"],
            "employee_id": user_data["id"],
            "status": "working",
            "group_id": group_id,
            "notes": "Task status changed to In Progress"
        }).execute()

        # 7. Format and return success message
        success_message = f"🚀 **Task Started!**\n📋 **Task:** {task['title']}\n📊 **Status:** In Progress"
        return (True, success_message)

    except Exception as e:
        print(f"Error in _working_task_service: {e}")
        return (False, "❗ An unexpected error occurred.")
    
    
def _completed_task_service(
    telegram_user_id: int,
    task_name: str,
    group_id: int = None
) -> Tuple[bool, str]:
    """
    Core logic to find an "In Progress" task and mark it as "Completed".
    Uses a manual filter to bypass the .ilike() error.
    Returns a tuple: (success, message).
    """
    try:
        # 1. Get user data
        user_data = get_user_from_telegram(telegram_user_id)
        if not user_data:
            return (False, "❌ Please link your Telegram account first using /link")

        # 2. WORKAROUND: Fetch all "In Progress" tasks assigned to the user
        query = (
            supabase.from_("tasks")
            .select("*")
            .eq("assigned_to", user_data["id"])
            .eq("status", "In Progress")
        )
        if group_id:
            query = query.eq("group_id", group_id)
        
        all_inprogress_tasks_res = query.execute()

        # 3. Filter the results manually in Python
        matching_tasks = []
        if all_inprogress_tasks_res.data:
            for task in all_inprogress_tasks_res.data:
                if task_name.lower() in task['title'].lower():
                    matching_tasks.append(task)

        # 4. Handle filtered results
        if not matching_tasks:
            return (False, f"✅ No 'In Progress' task named '{task_name}' was found. It might be already completed or not yet started.")

        if len(matching_tasks) > 1:
            task_list = "\n".join([f"• {task['title']}" for task in matching_tasks[:5]])
            return (False, f"❌ Multiple 'In Progress' tasks found:\n{task_list}\n\nPlease be more specific.")

        task = matching_tasks[0]

        # 5. Check deadline for completion note
        completion_note = "Task completed by user"
        if task.get("deadline"):
            deadline_date = datetime.strptime(task["deadline"], "%Y-%m-%d").date()
            today = datetime.now().date()
            if today > deadline_date:
                completion_note += " (completed after deadline)"
            else:
                completion_note += " (completed on or before deadline)"
        
        # 6. Update task status
        update_result = supabase.from_("tasks").update({"status": "Completed"}).eq("id", task["id"]).execute()
        if not update_result.data:
            return (False, "❌ Failed to update task status in the database.")

        # 7. Log the status change
        supabase.from_("status_logs").insert({
            "task_id": task["id"],
            "employee_id": user_data["id"],
            "status": "completed",
            "group_id": group_id,
            "notes": completion_note
        }).execute()

        # 8. Format and return the final success message
        deadline_text = f"📅 **Deadline:** {task['deadline']}" if task.get('deadline') else ""
        success_message = (
            f"✅ **Task Completed!**\n"
            f"📋 **Task:** {task['title']}\n"
            f"📊 **Status:** Completed\n"
            f"🎉 **Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"{deadline_text}\n\n"
            f"Great job! 🎊"
        )
        return (True, success_message)

    except Exception as e:
        print(f"Error in _completed_task_service: {e}")
        return (False, "❗ An unexpected error occurred.")
    
    
def _list_tasks_service(
    telegram_user_id: int, 
    group_id: int = None
) -> Tuple[bool, str]:
    """
    Core logic to fetch and format a list of tasks for a user.
    Returns a tuple: (success, message).
    """
    try:
        # 1. Get user data
        user_data = get_user_from_telegram(telegram_user_id)
        if not user_data:
            return (False, "❌ Please link your Telegram account first using /link")

        # 2. Get tasks assigned to this user from the database
        query = supabase.from_("tasks").select("*").eq("assigned_to", user_data["id"])
        if group_id:
            query = query.eq("group_id", group_id)
        
        tasks_result = query.order("created_at", desc=True).execute()

        if not tasks_result.data:
            return (True, "📋 You have no tasks assigned.")

        # 3. Group tasks by status
        tasks_by_status = {}
        for task in tasks_result.data:
            status = task["status"]
            if status not in tasks_by_status:
                tasks_by_status[status] = []
            tasks_by_status[status].append(task)

        # 4. Build the formatted message (keeping the original format)
        message = "📋 **Your Tasks:**\n\n"
        status_emojis = {"Pending": "⏳", "Assigned": "📋", "In Progress": "🚀", "Completed": "✅"}

        for status, tasks in tasks_by_status.items():
            emoji = status_emojis.get(status, "📌")
            message += f"{emoji} **{status}** ({len(tasks)})\n"
            for task in tasks[:3]:
                deadline = f" (Due: {task['deadline']})" if task.get('deadline') else ""
                
                if task.get('deadline') and status != "Completed":
                    deadline_date = datetime.strptime(task['deadline'], "%Y-%m-%d").date()
                    today = datetime.now().date()
                    days_left = (deadline_date - today).days
                    
                    if days_left < 0:
                        deadline += " ⚠️" # Overdue
                    elif days_left == 0:
                        deadline += " 🔥" # Due today
                    elif days_left <= 2:
                        deadline += " ⏰" # Due soon
                
                message += f"   • {task['title']}{deadline}\n"
            
            if len(tasks) > 3:
                message += f"   ... and {len(tasks) - 3} more\n"
            message += "\n"

        return (True, message)

    except Exception as e:
        print(f"Error in _list_tasks_service: {e}")
        return (False, "❗ Something went wrong while fetching tasks.")
    
    
def _task_history_service(
    telegram_user_id: int,
    task_name: str,
    group_id: int = None
) -> Tuple[bool, str]:
    """
    Core logic to find a task and format its history.
    If multiple tasks match, it shows the history for the most recent one.
    """
    try:
        # 1. Get user data (same as before)
        user_data = get_user_from_telegram(telegram_user_id)
        if not user_data:
            return (False, "❌ Please link your Telegram account first using /link")

        # 2. WORKAROUND: Fetch all tasks and filter in Python (same as before)
        query = supabase.from_("tasks").select("*")
        if group_id:
            query = query.eq("group_id", group_id)
        all_tasks_res = query.execute()

        matching_tasks = []
        if all_tasks_res.data:
            for task in all_tasks_res.data:
                if task_name.lower() in task['title'].lower():
                    matching_tasks.append(task)
        
        # 3. Handle filtered results
        if not matching_tasks:
            return (False, f"❌ Task '{task_name}' not found.")
        
        # --- NEW LOGIC TO HANDLE MULTIPLE MATCHES ---
        task = None
        user_note = ""
        if len(matching_tasks) > 1:
            # Sort by creation date (newest first) and pick the top one
            matching_tasks.sort(key=lambda t: t['created_at'], reverse=True)
            task = matching_tasks[0]
            # Create a note to inform the user
            user_note = f"⚠️ Multiple tasks found. Showing history for the most recent one (ID: `{task['id']}`).\n\n"
        else:
            task = matching_tasks[0]
        # --- END OF NEW LOGIC ---

        # 4. Get task history logs (same as before)
        logs_result = supabase.from_("status_logs").select("*").eq("task_id", task["id"]).order("timestamp", desc=False).execute()

        if not logs_result.data:
            return (True, f"✔️ No history found for task '{task['title']}'.")

        # 5. Build the formatted history message (with the new note)
        message = user_note + f"📋 **Task History: {task['title']}**\n\n"
        status_emojis = {"created": "🆕", "assigned": "👤", "working": "🚀", "completed": "✅"}

        for log in logs_result.data:
            timestamp = log.get("timestamp")
            if timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%Y-%m-%d %H:%M')
            else:
                time_str = "Unknown time"
            
            status = log.get("status", "note")
            emoji = status_emojis.get(status, "📌")
            
            message += f"{emoji} **{status.title()}** - {time_str}\n"
            if log.get("notes"):
                message += f"   > {log['notes']}\n"
            message += "\n"

        return (True, message)

    except Exception as e:
        print(f"Error in _task_history_service: {e}")
        return (False, "❗ Something went wrong while fetching task history.")
    
    
def _task_details_service(
    task_name: str,
    group_id: int
) -> Tuple[bool, List[str]]:
    """
    Core logic to find tasks and format their details, using correct queries.
    """
    try:
        # 1. WORKAROUND: Fetch tasks and join projects (which has a valid FK)
        # We remove the incorrect telegram_users join from this query.
        all_tasks_res = (
            supabase.from_("tasks")
            .select("*, projects(name)") 
            .eq("group_id", group_id)
            .in_("status", ["Assigned", "Pending"])
            .execute()
        )

        matching_tasks = []
        if all_tasks_res.data:
            for task in all_tasks_res.data:
                if task_name.lower() in task['title'].lower():
                    matching_tasks.append(task)

        if not matching_tasks:
            return (True, ["❌ No matching tasks found with that name and status 'Assigned' or 'Pending'."])

        # 2. Build a formatted message for each matching task
        messages = []
        for task in matching_tasks:
            project_name = task.get("projects", {}).get("name") if task.get("projects") else "None"
            deadline = task.get("deadline") or "Not set"
            assignee_username = "Unassigned"

            # 3. Manually fetch the assignee's username if an ID exists
            assignee_id = task.get("assigned_to")
            if assignee_id:
                # This second query gets the username using the ID from the task
                # Assuming your 'telegram_users' table has an 'id' column that is a FK to 'auth.users.id'
                user_res = supabase.from_("telegram_users").select("telegram_username").eq("id", assignee_id).single().execute()
                if user_res.data:
                    assignee_username = f"@{user_res.data['telegram_username']}"

            # 4. Format the final message
            message = (
                f"📝 **Task Details:**\n"
                f"**ID:** `{task['id']}`\n"
                f"**Title:** {task['title']}\n"
                f"**Status:** {task['status']}\n"
                f"**Deadline:** {deadline}\n"
                f"**Assigned To:** {assignee_username}\n"
                f"**Project:** {project_name}"
            )
            messages.append(message)
        
        return (True, messages)

    except Exception as e:
        print(f"Error in _task_details_service: {e}")
        return (False, ["❗ An unexpected error occurred while fetching task details."])