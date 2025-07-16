import os
from dotenv import load_dotenv
from telegram import Update, ChatMemberUpdated
from telegram.ext import Application, MessageHandler, CommandHandler, ChatMemberHandler, ContextTypes, filters
from services.link_handler import link
from services.group_handler import group_handler
from services.task_handler import (
    create_task,
    assign_task,
    working_task,
    completed_task,
    list_tasks,
    task_history,
    delete_task_by_id,
    task_details
)
from services.project_handler import (
    delete_project, 
    create_project,
    project_details,
    project_files,
    handle_document_upload,
    get_files
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Create bot application
app = Application.builder().token(BOT_TOKEN).build()

# Handler to respond to greetings
async def handle_hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text.lower()
    if message_text in ["hello", "hi", "hey"]:
        telegram_username = update.effective_user.username or "there"
        await update.message.reply_text(
            f"👋 Hello @{telegram_username}!\n\n"
            "Welcome to AutoPM Bot.\n\n"
            "➡️ First, login on the web app and go to Settings → Generate One-Time Code (OTC).\n"
            "🔗 [Login here](http://localhost:5173/)\n\n"
            "Then use:\n"
            "`/link <Your OTC>` to connect your Telegram.",
            parse_mode="Markdown"
        )

# Register handlers
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hello))
app.add_handler(CommandHandler("link", link))
app.add_handler(ChatMemberHandler(group_handler, ChatMemberHandler.MY_CHAT_MEMBER))

# Register task handlers
app.add_handler(CommandHandler("create_task", create_task))
app.add_handler(CommandHandler("assign", assign_task))
app.add_handler(CommandHandler("working", working_task))
app.add_handler(CommandHandler("completed", completed_task))
app.add_handler(CommandHandler("tasks", list_tasks))
app.add_handler(CommandHandler("history", task_history))
app.add_handler(CommandHandler("delete_task", delete_task_by_id))
app.add_handler(CommandHandler("task_details", task_details))



#Register project handlers
app.add_handler(CommandHandler("create_project", create_project))
app.add_handler(CommandHandler("delete_project", delete_project))
app.add_handler(CommandHandler("project_details", project_details))
app.add_handler(CommandHandler("project_files", project_files))
app.add_handler(MessageHandler(filters.Document.ALL, handle_document_upload))
app.add_handler(CommandHandler("get_files", get_files))


# Run bot
if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run_polling())