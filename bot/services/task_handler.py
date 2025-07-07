from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timezone
from utils.supabaseClient import supabase
from utils.auth_helper import get_user_from_telegram, check_admin_permission

async def create_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Create a standalone task (not part of a project)
    Usage: /create_task Task Title -- Task Description -- YYYY-MM-DD
    """
    try:
        # Check if user is admin
        user_data = get_user_from_telegram(update.effective_user.id)
        if not user_data:
            await update.message.reply_text("❌ Please link your Telegram account first using /link")
            return

        # Check admin permission for group
        if update.message.chat.type in ["group", "supergroup"]:
            group_id = update.message.chat.id
            if not check_admin_permission(user_data["id"], group_id):
                await update.message.reply_text("❌ Only admins can create tasks.")
                return
        else:
            await update.message.reply_text("❌ Tasks can only be created in groups.")
            return

        # Parse command arguments
        if not context.args:
            await update.message.reply_text(
                "❗ Usage: `/create_task <title> -- <description> -- <deadline>`\n"
                "Example: `/create_task Fix login bug -- The login form is not validating email properly -- 2024-12-31`\n"
                "Note: Deadline is optional and should be in YYYY-MM-DD format",
                parse_mode="Markdown"
            )
            return

        # Join all arguments and split by --
        full_text = " ".join(context.args)
        parts = full_text.split("--")
        
        # Extract title (required)
        title = parts[0].strip() if len(parts) > 0 else ""
        
        # Extract description (optional)
        description = parts[1].strip() if len(parts) > 1 else None
        
        # Extract deadline (optional)
        deadline = None
        if len(parts) > 2:
            deadline_str = parts[2].strip()
            if deadline_str:
                try:
                    # Parse deadline string to validate format
                    deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d")
                    deadline = deadline_str
                    
                    # Check if deadline is in the past
                    if deadline_date.date() < datetime.now().date():
                        await update.message.reply_text("❌ Deadline cannot be in the past.")
                        return
                        
                except ValueError:
                    await update.message.reply_text(
                        "❌ Invalid deadline format. Please use YYYY-MM-DD format.\n"
                        "Example: 2024-12-31"
                    )
                    return

        if not title:
            await update.message.reply_text("❌ Task title cannot be empty.")
            return

        # Insert task into database
        task_data = {
            "title": title,
            "description": description,
            "status": "Pending",
            "group_id": group_id,
            "project_id": None,  # Standalone task
            "parent_task_id": None,  # Top-level task
            "deadline": deadline
        }

        result = supabase.from_("tasks").insert(task_data).execute()
        
        if result.data:
            task_id = result.data[0]["id"]
            
            # Log task creation
            supabase.from_("status_logs").insert({
                "task_id": task_id,
                "employee_id": user_data["id"],
                "status": "created",
                "group_id": group_id,
                "deadline": deadline,
                "notes": f"Task created: {title}"
            }).execute()
            
            deadline_text = f"📅 **Deadline:** {deadline}" if deadline else "📅 **Deadline:** Not set"
            
            await update.message.reply_text(
                f"✅ **Task Created!**\n"
                f"📋 **Title:** {title}\n"
                f"📝 **Description:** {description or 'None'}\n"
                f"{deadline_text}\n"
                f"🆔 **ID:** `{task_id}`\n\n"
                f"Use `/assign @username {title}` to assign it to someone.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Failed to create task. Please try again.")

    except Exception as e:
        print(f"Error in create_task: {e}")
        await update.message.reply_text("❗ Something went wrong while creating the task.")

async def assign_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Assign a task to a user
    Usage: /assign @username task_name
    """
    try:
        # Check if user is admin
        user_data = get_user_from_telegram(update.effective_user.id)
        if not user_data:
            await update.message.reply_text("❌ Please link your Telegram account first using /link")
            return

        if update.message.chat.type in ["group", "supergroup"]:
            group_id = update.message.chat.id
            if not check_admin_permission(user_data["id"], group_id):
                await update.message.reply_text("❌ Only admins can assign tasks.")
                return
        else:
            await update.message.reply_text("❌ Tasks can only be assigned in groups.")
            return

        if len(context.args) < 2:
            await update.message.reply_text(
                "❗ Usage: `/assign @username <task_name>`\n"
                "Example: `/assign @john Fix login bug`",
                parse_mode="Markdown"
            )
            return

        # Parse username and task name
        username = context.args[0].replace("@", "")
        task_name = " ".join(context.args[1:])

        # Find the user by telegram username
        telegram_user = supabase.from_("telegram_users").select("id").eq("telegram_username", username).single().execute()
        
        if not telegram_user.data:
            await update.message.reply_text(f"❌ User @{username} not found or not linked.")
            return

        assignee_id = telegram_user.data["id"]

        # Find the task by name in this group
        task_result = supabase.from_("tasks").select("*").eq("group_id", group_id).ilike("title", f"%{task_name}%").execute()
        
        if not task_result.data:
            await update.message.reply_text(f"❌ Task '{task_name}' not found in this group.")
            return

        if len(task_result.data) > 1:
            task_list = "\n".join([f"• {task['title']}" for task in task_result.data[:5]])
            await update.message.reply_text(
                f"❌ Multiple tasks found matching '{task_name}':\n{task_list}\n\n"
                "Please be more specific."
            )
            return

        task = task_result.data[0]
        
        # Update task assignment
        update_result = supabase.from_("tasks").update({
            "assigned_to": assignee_id,
            "status": "Assigned"
        }).eq("id", task["id"]).execute()

        if update_result.data:
            # Log task assignment
            supabase.from_("status_logs").insert({
                "task_id": task["id"],
                "employee_id": assignee_id,
                "status": "assigned",
                "group_id": group_id,
                "deadline": task["deadline"],
                "notes": f"Task assigned to @{username} by admin"
            }).execute()
            
            deadline_text = f"📅 **Deadline:** {task['deadline']}" if task['deadline'] else "📅 **Deadline:** Not set"
            
            await update.message.reply_text(
                f"✅ **Task Assigned!**\n"
                f"📋 **Task:** {task['title']}\n"
                f"👤 **Assigned to:** @{username}\n"
                f"📊 **Status:** Assigned\n"
                f"{deadline_text}",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Failed to assign task. Please try again.")

    except Exception as e:
        print(f"Error in assign_task: {e}")
        await update.message.reply_text("❗ Something went wrong while assigning the task.")

async def working_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Mark a task as working
    Usage: /working task_name
    """
    try:
        user_data = get_user_from_telegram(update.effective_user.id)
        if not user_data:
            await update.message.reply_text("❌ Please link your Telegram account first using /link")
            return

        if not context.args:
            await update.message.reply_text(
                "❗ Usage: `/working <task_name>`\n"
                "Example: `/working Fix login bug`",
                parse_mode="Markdown"
            )
            return

        task_name = " ".join(context.args)
        group_id = update.message.chat.id if update.message.chat.type in ["group", "supergroup"] else None

        # Find tasks assigned to this user
        query = supabase.from_("tasks").select("*").eq("assigned_to", user_data["id"]).ilike("title", f"%{task_name}%")
        
        if group_id:
            query = query.eq("group_id", group_id)
        
        task_result = query.execute()

        if not task_result.data:
            await update.message.reply_text(f"❌ No task '{task_name}' assigned to you.")
            return

        if len(task_result.data) > 1:
            task_list = "\n".join([f"• {task['title']}" for task in task_result.data[:5]])
            await update.message.reply_text(
                f"❌ Multiple tasks found:\n{task_list}\n\n"
                "Please be more specific."
            )
            return

        task = task_result.data[0]

        # Update task status
        update_result = supabase.from_("tasks").update({
            "status": "In Progress"
        }).eq("id", task["id"]).execute()

        # Log the status change
        supabase.from_("status_logs").insert({
            "task_id": task["id"],
            "employee_id": user_data["id"],
            "status": "working",
            "group_id": group_id,
            "deadline": task["deadline"],
            "notes": f"Task started by user"
        }).execute()

        if update_result.data:
            deadline_text = f"📅 **Deadline:** {task['deadline']}" if task['deadline'] else ""
            
            await update.message.reply_text(
                f"🚀 **Task Started!**\n"
                f"📋 **Task:** {task['title']}\n"
                f"📊 **Status:** In Progress\n"
                f"⏰ **Started:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"{deadline_text}",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Failed to update task status.")

    except Exception as e:
        print(f"Error in working_task: {e}")
        await update.message.reply_text("❗ Something went wrong while updating the task.")

async def completed_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Mark a task as completed
    Usage: /completed task_name
    """
    try:
        user_data = get_user_from_telegram(update.effective_user.id)
        if not user_data:
            await update.message.reply_text("❌ Please link your Telegram account first using /link")
            return

        if not context.args:
            await update.message.reply_text(
                "❗ Usage: `/completed <task_name>`\n"
                "Example: `/completed Fix login bug`",
                parse_mode="Markdown"
            )
            return

        task_name = " ".join(context.args)
        group_id = update.message.chat.id if update.message.chat.type in ["group", "supergroup"] else None

        # Find tasks assigned to this user
        query = supabase.from_("tasks").select("*").eq("assigned_to", user_data["id"]).ilike("title", f"%{task_name}%")
        
        if group_id:
            query = query.eq("group_id", group_id)
        
        task_result = query.execute()

        if not task_result.data:
            await update.message.reply_text(f"❌ No task '{task_name}' assigned to you.")
            return

        if len(task_result.data) > 1:
            task_list = "\n".join([f"• {task['title']}" for task in task_result.data[:5]])
            await update.message.reply_text(
                f"❌ Multiple tasks found:\n{task_list}\n\n"
                "Please be more specific."
            )
            return

        task = task_result.data[0]

        # Check if task was completed on time
        completion_note = "Task completed by user"
        if task["deadline"]:
            deadline_date = datetime.strptime(task["deadline"], "%Y-%m-%d").date()
            today = datetime.now().date()
            if today > deadline_date:
                completion_note += " (completed after deadline)"
            elif today == deadline_date:
                completion_note += " (completed on deadline)"
            else:
                completion_note += " (completed before deadline)"

        # Update task status
        update_result = supabase.from_("tasks").update({
            "status": "Completed"
        }).eq("id", task["id"]).execute()

        # Log the status change
        supabase.from_("status_logs").insert({
            "task_id": task["id"],
            "employee_id": user_data["id"],
            "status": "completed",
            "group_id": group_id,
            "deadline": task["deadline"],
            "notes": completion_note
        }).execute()

        if update_result.data:
            deadline_text = f"📅 **Deadline:** {task['deadline']}" if task['deadline'] else ""
            
            await update.message.reply_text(
                f"✅ **Task Completed!**\n"
                f"📋 **Task:** {task['title']}\n"
                f"📊 **Status:** Completed\n"
                f"🎉 **Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"{deadline_text}\n\n"
                f"Great job! 🎊",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Failed to update task status.")

    except Exception as e:
        print(f"Error in completed_task: {e}")
        await update.message.reply_text("❗ Something went wrong while updating the task.")

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    List tasks for the current user
    Usage: /tasks
    """
    try:
        user_data = get_user_from_telegram(update.effective_user.id)
        if not user_data:
            await update.message.reply_text("❌ Please link your Telegram account first using /link")
            return

        group_id = update.message.chat.id if update.message.chat.type in ["group", "supergroup"] else None

        # Get tasks assigned to this user
        query = supabase.from_("tasks").select("*").eq("assigned_to", user_data["id"])
        
        if group_id:
            query = query.eq("group_id", group_id)
        
        tasks_result = query.order("created_at", desc=True).execute()

        if not tasks_result.data:
            await update.message.reply_text("📋 You have no tasks assigned.")
            return

        # Group tasks by status
        tasks_by_status = {}
        for task in tasks_result.data:
            status = task["status"]
            if status not in tasks_by_status:
                tasks_by_status[status] = []
            tasks_by_status[status].append(task)

        # Build message
        message = "📋 **Your Tasks:**\n\n"
        
        status_emojis = {
            "Pending": "⏳",
            "Assigned": "📋",
            "In Progress": "🚀",
            "Completed": "✅"
        }

        for status, tasks in tasks_by_status.items():
            emoji = status_emojis.get(status, "📌")
            message += f"{emoji} **{status}** ({len(tasks)})\n"
            for task in tasks[:3]:  # Show max 3 tasks per status
                deadline = f" (Due: {task['deadline']})" if task['deadline'] else ""
                
                # Add deadline urgency indicator
                if task['deadline'] and status != "Completed":
                    deadline_date = datetime.strptime(task['deadline'], "%Y-%m-%d").date()
                    today = datetime.now().date()
                    days_left = (deadline_date - today).days
                    
                    if days_left < 0:
                        deadline += " ⚠️"  # Overdue
                    elif days_left == 0:
                        deadline += " 🔥"  # Due today
                    elif days_left <= 2:
                        deadline += " ⏰"  # Due soon
                
                message += f"  • {task['title']}{deadline}\n"
            
            if len(tasks) > 3:
                message += f"  ... and {len(tasks) - 3} more\n"
            message += "\n"

        await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        print(f"Error in list_tasks: {e}")
        await update.message.reply_text("❗ Something went wrong while fetching tasks.")

async def task_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show task history/logs
    Usage: /history task_name
    """
    try:
        user_data = get_user_from_telegram(update.effective_user.id)
        if not user_data:
            await update.message.reply_text("❌ Please link your Telegram account first using /link")
            return

        if not context.args:
            await update.message.reply_text(
                "❗ Usage: `/history <task_name>`\n"
                "Example: `/history Fix login bug`",
                parse_mode="Markdown"
            )
            return

        task_name = " ".join(context.args)
        group_id = update.message.chat.id if update.message.chat.type in ["group", "supergroup"] else None

        # Find the task
        query = supabase.from_("tasks").select("*").ilike("title", f"%{task_name}%")
        
        if group_id:
            query = query.eq("group_id", group_id)
        
        task_result = query.execute()

        if not task_result.data:
            await update.message.reply_text(f"❌ Task '{task_name}' not found.")
            return

        if len(task_result.data) > 1:
            task_list = "\n".join([f"• {task['title']}" for task in task_result.data[:5]])
            await update.message.reply_text(
                f"❌ Multiple tasks found:\n{task_list}\n\n"
                "Please be more specific."
            )
            return

        task = task_result.data[0]

        # Get task history
        logs_result = supabase.from_("status_logs").select("*").eq("task_id", task["id"]).order("timestamp", desc=False).execute()

        if not logs_result.data:
            await update.message.reply_text(f"❌ No history found for task '{task['title']}'.")
            return

        # Build history message
        message = f"📋 **Task History: {task['title']}**\n\n"
        
        for log in logs_result.data:
            timestamp = log["timestamp"]
            if timestamp:
                # Parse timestamp and format it
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%Y-%m-%d %H:%M')
            else:
                time_str = "Unknown time"
            
            status_emoji = {
                "created": "🆕",
                "assigned": "👤",
                "working": "🚀",
                "completed": "✅"
            }.get(log["status"], "📌")
            
            message += f"{status_emoji} **{log['status'].title()}** - {time_str}\n"
            if log["notes"]:
                message += f"   {log['notes']}\n"
            message += "\n"

        await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        print(f"Error in task_history: {e}")
        await update.message.reply_text("❗ Something went wrong while fetching task history.")