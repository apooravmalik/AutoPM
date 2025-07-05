import os
from dotenv import load_dotenv
from telegram import Update, ChatMemberUpdated
from telegram.ext import Application, MessageHandler, CommandHandler, ChatMemberHandler, ContextTypes, filters
from services.link_handler import link
from services.group_handler import group_handler

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

# Run bot
if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run_polling())
