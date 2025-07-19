# bot/services/ai_handler.py

from telegram import Update
from telegram.ext import ContextTypes
from graph.agent import app # 👈 1. Import your compiled LangGraph app

async def route_to_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    This function is the bridge between Telegram and the LangGraph agent.
    It takes the user's message and passes it to the agent to handle.
    """
    if not (update.message and update.message.text):
        return

    command_text = update.message.text.replace(f"@{context.bot.username}", "").strip()
    if not command_text:
        await update.message.reply_text("Please provide a command after mentioning me.")
        return

    try:
        # 2. This is where you call your agent.
        # The input dictionary MUST match the structure of your AgentState.
        final_state = await app.ainvoke({"input": command_text})
        
        # 3. Get the final response from the agent's state
        response_message = final_state.get("response", "Sorry, something went wrong.")
        
        # 4. Send the agent's response back to the user
        await update.message.reply_text(response_message, parse_mode="Markdown")

    except Exception as e:
        print(f"An error occurred in the agent: {e}")
        await update.message.reply_text("❌ An error occurred while processing your request.")