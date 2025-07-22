from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timezone
from utils.supabaseClient import supabase
from utils.auth_helper import get_user_from_telegram, check_admin_permission
from typing import Tuple
from services.task_service import _create_task_service, _assign_task_service, _working_task_service, _completed_task_service, _list_tasks_service, _task_history_service, _task_details_service

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
    Command handler for /completed. Parses the task name and calls the service.
    """
    if not context.args:
        await update.message.reply_text("❗ Usage: `/completed <task_name>`")
        return

    task_name = " ".join(context.args)
    group_id = update.message.chat.id if update.message.chat.type in ["group", "supergroup"] else None

    # Call the shared service function
    success, message = _completed_task_service(
        telegram_user_id=update.effective_user.id,
        task_name=task_name,
        group_id=group_id
    )
    
    # Reply with the result from the service
    await update.message.reply_text(message, parse_mode="Markdown")

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command handler for /tasks. Calls the list_tasks service.
    """
    group_id = update.message.chat.id if update.message.chat.type in ["group", "supergroup"] else None

    # Call the shared service function
    success, message = _list_tasks_service(
        telegram_user_id=update.effective_user.id,
        group_id=group_id
    )
    
    # Reply with the result from the service
    await update.message.reply_text(message, parse_mode="Markdown")
    
async def task_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command handler for /history <task_name>. Parses the task name and calls the service.
    """
    if not context.args:
        await update.message.reply_text("❗ Usage: `/history <task_name>`")
        return

    task_name = " ".join(context.args)
    group_id = update.message.chat.id if update.message.chat.type in ["group", "supergroup"] else None

    # Call the shared service function
    success, message = _task_history_service(
        telegram_user_id=update.effective_user.id,
        task_name=task_name,
        group_id=group_id
    )
    
    # Reply with the result from the service
    await update.message.reply_text(message, parse_mode="Markdown")
        
        
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
    """
    Command handler for /task_details. Calls the details service.
    """
    if not context.args:
        await update.message.reply_text("❗ Usage: `/task_details <task_name>`")
        return

    task_name = " ".join(context.args)
    group_id = update.message.chat.id

    # Call the shared service function
    success, messages = _task_details_service(
        task_name=task_name,
        group_id=group_id
    )
    
    # Loop through the list of messages from the service and send each one
    for msg in messages:
        await update.message.reply_text(msg, parse_mode="Markdown")