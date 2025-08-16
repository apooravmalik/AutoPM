# bot/handlers/report_handler.py
from telegram import Update
from telegram.ext import ContextTypes
from services.report_service import _summary_service
from utils.supabaseClient import supabase

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command handler for /summary.
    Usage: /summary
           /summary | <project_name> | <days>
    """
    if update.message.chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ This command can only be used in groups.")
        return

    group_id = update.message.chat.id
    telegram_user_id = update.effective_user.id

    if not context.args:
        # Case: /summary for all projects, default 7 days
        days = 7
        print(f"Generating summary for all projects in group {group_id} for the last {days} days")

        # Fetch all projects for the current group
        projects_res = supabase.from_("projects").select("name").eq("group_id", group_id).execute()
        if not projects_res.data:
            await update.message.reply_text("No projects found in this group to summarize.")
            return

        await update.message.reply_text(f"📊 Generating summaries for {len(projects_res.data)} project(s)...")

        # Loop through each project and send a separate summary
        for project in projects_res.data:
            project_name = project['name']
            success, message = _summary_service(
                telegram_user_id=telegram_user_id,
                group_id=group_id,
                project_name=project_name,
                days=days
            )
            await update.message.reply_text(message, parse_mode="Markdown")

    else:
        # Case: /summary with specific arguments
        project_name = None
        days = 7  # Default to 7 days

        full_text = " ".join(context.args)
        parts = [p.strip() for p in full_text.split("|")]
        parts = [p for p in parts if p]
        
        if len(parts) > 0:
            project_name = parts[0]
        if len(parts) > 1 and parts[1].isdigit():
            days = int(parts[1])
        
        if not project_name:
            await update.message.reply_text("Please specify a project name after the `|`.")
            return

        print(f"Generating summary for project '{project_name}' in group {group_id} for the last {days} days")
        success, message = _summary_service(
            telegram_user_id=telegram_user_id,
            group_id=group_id,
            project_name=project_name,
            days=days
        )

        await update.message.reply_text(message, parse_mode="Markdown")