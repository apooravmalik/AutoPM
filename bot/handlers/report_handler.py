# bot/handlers/report_handler.py
from telegram import Update
from telegram.ext import ContextTypes
from services.report_service import _summary_service

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command handler for /summary.
    Usage: /summary | <project_name> | <days>
    """
    if update.message.chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ This command can only be used in groups.")
        return

    project_name = None
    days = 7  # Default to 7 days

    if context.args:
        # Join all arguments into a single string
        full_text = " ".join(context.args)
        
        # Split the string by the pipe delimiter
        parts = [p.strip() for p in full_text.split("|")]
        
        # Filter out any empty strings that result from the split
        parts = [p for p in parts if p]
        
        if len(parts) > 0:
            project_name = parts[0]
        if len(parts) > 1 and parts[1].isdigit():
            days = int(parts[1])
            
    print(f"Generating summary for project '{project_name}' in group {update.message.chat.id} for the last {days} days")
    success, message = _summary_service(
        telegram_user_id=update.effective_user.id,
        group_id=update.message.chat.id,
        project_name=project_name,
        days=days
    )

    await update.message.reply_text(message, parse_mode="Markdown")