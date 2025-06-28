import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Create the bot application
app = Application.builder().token(BOT_TOKEN).build()

# Handler to respond to "hello"
async def handle_hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "hello":
        print("message recieved")
        await update.message.reply_text("👋 Hello! Bot is working fine.")

# Add handler
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hello))

# Run the bot using polling
if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run_polling())
