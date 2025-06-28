from telegram import Update
from telegram.ext import ContextTypes
from supabase import create_client, Client
import os
from datetime import datetime

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE")  # Use service role key for secure lookup
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) != 1:
            await update.message.reply_text("❗ Usage: /link your@email.com")
            return

        email = context.args[0].strip()
        telegram_id = update.effective_user.id
        telegram_username = update.effective_user.username or "unknown"

        # 1. Get Supabase Auth user by email
        user_res = supabase.table("users").select("id").eq("email", email).execute()
        if not user_res.data:
            await update.message.reply_text("❌ User not found. Make sure you're signed in on the website first.")
            return

        user_id = user_res.data[0]['id']

        # 2. Upsert into telegram_users table
        result = supabase.table("telegram_users").upsert({
            "id": user_id,
            "telegram_id": telegram_id,
            "telegram_username": telegram_username,
            "last_seen_at": datetime.utcnow().isoformat(),
            "valid": True
        }).execute()

        await update.message.reply_text("✅ Telegram account successfully linked!")

    except Exception as e:
        print(f"Error in /link command: {e}")
        await update.message.reply_text("❗ Something went wrong while linking.")
