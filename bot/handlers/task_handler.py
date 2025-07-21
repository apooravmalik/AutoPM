from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timezone
from utils.supabaseClient import supabase
from utils.auth_helper import get_user_from_telegram, check_admin_permission
from typing import Tuple
from services.task_service import _create_task_service, _assign_task_service, _working_task_service

async def create_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command handler for /create_task.
    It now acts as a simple "adapter" that parses command arguments
    and calls the shared service function.
    """
    # 1. Perform Telegram-specific checks
    if update.message.chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ This command can only be used in groups.")
        return

    # 2. Parse arguments from the command context
    if not context.args:
        # Provide usage instructions if no arguments are given
        await update.message.reply_text(
            "❗ Usage: `/create_task <title> | <description> | <project name> | <deadline>`",
            parse_mode="Markdown"
        )
        return

    full_text = " ".join(context.args)
    parts = [p.strip() for p in full_text.split("|")]
    
    title = parts[0] if len(parts) > 0 else ""
    if not title:
        await update.message.reply_text("❌ Task title cannot be empty.")
        return

    # 3. Call the shared service function with the parsed data
    success, message = _create_task_service(
        telegram_user_id=update.effective_user.id,
        group_id=update.message.chat.id,
        title=title,
        description=parts[1] if len(parts) > 1 else None,
        project_name=parts[2] if len(parts) > 2 else None,
        deadline=parts[3] if len(parts) > 3 else None,
    )

    # 4. Reply to the user with the result from the service
    await update.message.reply_text(message, parse_mode="Markdown")

async def assign_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command handler for /assign.
    It now acts as a simple "adapter" that parses command arguments
    and calls the shared service function.
    """
    # 2. Perform Telegram-specific checks
    if update.message.chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ This command can only be used in groups.")
        return

    # 3. Parse arguments from the command context
    if not context.args:
        await update.message.reply_text(
            "❗ Usage: `/assign @username | <task_name>`",
            parse_mode="Markdown"
        )
        return

    full_text = " ".join(context.args)
    parts = [p.strip() for p in full_text.split("|")]

    if len(parts) < 2:
        await update.message.reply_text("❗ Both a @username and task name are required.")
        return

    assignee_username = parts[0]
    task_name = parts[1]

    if not assignee_username.startswith('@') or not task_name:
        await update.message.reply_text("❗ Invalid format. Usage: `/assign @username | <task_name>`")
        return

    # 4. Call the shared service function with the parsed data
    success, message = _assign_task_service(
        admin_telegram_user_id=update.effective_user.id,
        group_id=update.message.chat.id,
        assignee_username=assignee_username,
        task_name=task_name
    )

    # 5. Reply to the user with the result from the service
    await update.message.reply_text(message, parse_mode="Markdown")
    
            
async def working_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command handler for /working. Parses the task name and calls the service.
    """
    if not context.args:
        await update.message.reply_text("❗ Usage: `/working <task_name>`")
        return

    task_name = " ".join(context.args)
    group_id = update.message.chat.id if update.message.chat.type in ["group", "supergroup"] else None

    # Call the shared service function
    success, message = _working_task_service(
        telegram_user_id=update.effective_user.id,
        task_name=task_name,
        group_id=group_id
    )
    
    # Reply with the result from the service
    await update.message.reply_text(message, parse_mode="Markdown")

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

        # Only fetch tasks assigned to this user AND currently in 'In Progess' status (assigned to someone and they accepted)
        query = (
            supabase
            .from_("tasks")
            .select("*")
            .eq("assigned_to", user_data["id"])
            .ilike("title", f"%{task_name}%")
            .eq("status", "In Progress")
        )

        if group_id:
            query = query.eq("group_id", group_id)

        task_result = query.execute()

        if not task_result.data:
            await update.message.reply_text(f"✅ The task '{task_name}' is already completed or not assigned.")
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
        
        
        
async def delete_task_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("❗ Usage: /delete_task <task_id>")
            return

        task_id = context.args[0]
        user_data = get_user_from_telegram(update.effective_user.id)
        if not user_data:
            await update.message.reply_text("❌ Please link your Telegram account first using /link")
            return

        group_id = update.message.chat.id

        # Fetch the task to confirm it exists
        task_res = (
            supabase
            .from_("tasks")
            .select("*")
            .eq("id", task_id)
            .eq("group_id", group_id)
            .single()
            .execute()
        )

        task = task_res.data
        if not task:
            await update.message.reply_text("❌ Task not found or doesn't belong to this group.")
            return

        # Delete all status_logs referencing this task
        supabase.from_("status_logs").delete().eq("task_id", task_id).execute()

        # Delete the task
        supabase.from_("tasks").delete().eq("id", task_id).execute()

        await update.message.reply_text(f"🗑️ Task *{task['title']}* (ID: `{task_id}`) deleted successfully.", parse_mode="Markdown")

    except Exception as e:
        print(f"Error in delete_task_by_id: {e}")
        await update.message.reply_text("❗ Failed to delete the task. Please try again.")


async def task_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("❗ Usage: /get_task_details <task_name>")
            return

        task_name = " ".join(context.args)
        group_id = update.message.chat.id

        # Fetch matching tasks (case-insensitive) with Assigned or Pending status
        task_result = (
            supabase
            .from_("tasks")
            .select("*")
            .eq("group_id", group_id)
            .ilike("title", f"%{task_name}%")
            .in_("status", ["Assigned", "Pending"])
            .execute()
        )

        tasks = task_result.data

        if not tasks:
            await update.message.reply_text("❌ No matching tasks found with that name and status Assigned or Pending.")
            return

        # Send task details for each match
        for task in tasks:
            project_name = "Solo Task"
            if task.get("project_id"):
                project_fetch = (
                    supabase
                    .from_("projects")
                    .select("name")
                    .eq("id", task["project_id"])
                    .single()
                    .execute()
                )
                if project_fetch.data:
                    project_name = project_fetch.data["name"]

            assignee = task.get("assigned_to") or "Unassigned"
            due_date = task.get("due_date") or "Not set"

            await update.message.reply_text(
                f"📝 *Task Details:*\n"
                f"*ID:* `{task['id']}`\n"
                f"*Title:* {task['title']}\n"
                f"*Status:* {task['status']}\n"
                f"*Due Date:* {due_date}\n"
                f"*Assigned To:* {assignee}\n"
                f"*Project:* {project_name}",
                parse_mode="Markdown"
            )

    except Exception as e:
        print(f"Error in get_task_details: {e}")
        await update.message.reply_text("❗ Failed to fetch task details.")
