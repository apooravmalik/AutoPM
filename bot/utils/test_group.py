from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Command to test group context
async def test_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        chat = message.chat

        print("📥 Raw update.message.chat:", chat)

        if not chat:
            await message.reply_text("❌ No chat object found.")
            return

        chat_type = chat.type
        chat_id = chat.id
        chat_title = chat.title

        await message.reply_text(
            f"✅ Group Info:\n"
            f"- Chat Type: {chat_type}\n"
            f"- Chat ID: {chat_id}\n"
            f"- Chat Title: {chat_title or 'N/A'}"
        )

        print(f"✅ Group Info:\nChat Type: {chat_type}, Chat ID: {chat_id}, Chat Title: {chat_title}")

    except Exception as e:
        print("❌ Error reading group info:", e)

# Run the bot
if __name__ == "__main__":

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("testgroup", test_group))

    print("🤖 Bot is running. Use /testgroup inside a group chat.")
    app.run_polling()
