# bot/services/ai_handler.py
import re
from telegram import Update
from telegram.ext import ContextTypes
from graph.builder import app

def _parse_task_id_from_reply(text: str) -> str | None:
    """Helper to find a task ID in a message using regex."""
    if not text:
        return None
    
    # Look for the pattern "🆔 ID: uuid" (with emoji)
    match = re.search(r"🆔\s*ID:\s*([0-9a-fA-F-]+)", text)
    if match:
        return match.group(1)
    
    # Fallback: Look for the pattern "ID: `uuid`" (with backticks)
    match = re.search(r"ID:\s*`([0-9a-fA-F-]+)`", text)
    if match:
        return match.group(1)
    
    # Another fallback: Look for just "ID: uuid" (plain text)
    match = re.search(r"ID:\s*([0-9a-fA-F-]+)", text)
    if match:
        return match.group(1)
    
    return None


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
    
    # Check for a replied-to message and try to parse a task ID
    task_id_from_reply = None
    if update.message.reply_to_message and update.message.reply_to_message.text:
        replied_text = update.message.reply_to_message.text
        print(f"--- DEBUG: Replied-to message text: {replied_text!r} ---")
        
        task_id_from_reply = _parse_task_id_from_reply(replied_text)
        
    print(f"----task id received: {task_id_from_reply}----")

    try:
        print(f"--- 📝 User Command: {command_text} ---")
        #For the agent to work, we need to set up the initial state.
        # 1. Create the initial state with the user's input and Telegram metadata.
        initial_state = {
            "input": command_text,
            "telegram_user_id": update.effective_user.id,
            "chat_id": update.message.chat.id,
            "task_id_from_reply": task_id_from_reply
        }
        print(f"----task id received: {task_id_from_reply}----")
        print(f"--- 📝 Initial State: {initial_state} ---")
        print("--- 🧠 Starting the AI Agent ---")
        # 2. This is where you call your agent.
        # The input dictionary MUST match the structure of your AgentState.
        final_state = await app.ainvoke(initial_state)
        
        # 3. Get the final response from the agent's state
        response_message = final_state.get("response", "Sorry, something went wrong.")
        
        print(f"--- 📝 Final Response: {response_message} ---")
        # 4. Send the agent's response back to the user
        await update.message.reply_text(response_message, parse_mode="Markdown")

    except Exception as e:
        print(f"An error occurred in the agent: {e}")
        await update.message.reply_text("❌ An error occurred while processing your request.")