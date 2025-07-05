from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timezone
from utils.supabseClient import supabase

async def link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) != 1:
            await update.message.reply_text("❗ Usage: /link <Your One-Time Code>")
            return

        otc_code = context.args[0].strip().upper()
        telegram_id = update.effective_user.id
        telegram_username = update.effective_user.username or "unknown"

        # 1. Verify OTC
        otc_res = supabase.from_("otc_codes").select("user_id, expires_at, used").eq("code", otc_code).single().execute()
        if not otc_res.data:
            await update.message.reply_text("❌ Invalid or expired OTC. Please generate a new one from the web app.")
            return

        otc_data = otc_res.data
        if otc_data["used"]:
            await update.message.reply_text("⚠️ This OTC has already been used.")
            return

        if datetime.fromisoformat(otc_data["expires_at"]).replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            await update.message.reply_text("⌛ This OTC has expired. Please generate a new one.")
            return

        user_id = otc_data["user_id"]
        print("✅ OTC verified!")

        # 2. Upsert into telegram_users
        supabase.from_("telegram_users").upsert({
            "id": user_id,
            "telegram_id": telegram_id,
            "telegram_username": telegram_username,
            "last_seen_at": datetime.utcnow().isoformat(),
            "valid": True
        }).execute()
        print("✅ Telegram user linked!")

        assigned_role = "developer"

        # 3. Handle group-specific logic
        if update.message.chat.type in ["group", "supergroup"]:
            group_id = update.message.chat.id
            group_name = update.message.chat.title or "Unnamed Group"

            # Check if group exists
            group_check = supabase.from_("groups").select("*").eq("group_id", group_id).single().execute()

            if not group_check.data:
                # No group entry – insert group and set user as admin
                supabase.from_("groups").insert({
                    "group_id": group_id,
                    "group_name": group_name,
                    "admin_id": user_id
                }).execute()
                assigned_role = "admin"
                print(f"👑 New group. {user_id} set as admin.")
            else:
                # Update group admin if missing
                if not group_check.data.get("admin_id"):
                    supabase.from_("groups").update({
                        "admin_id": user_id
                    }).eq("group_id", group_id).execute()
                    assigned_role = "admin"
                    print(f"👑 Admin added to existing group.")
                else:
                    # Check if roles table already has an admin for this group
                    roles_check = supabase.from_("roles").select("role").eq("group_id", group_id).eq("role", "admin").execute()
                    if not roles_check.data:
                        assigned_role = "admin"
                        print("👑 No admin in roles table, assigning admin role.")

            # Insert role
            supabase.from_("roles").insert({
                "user_id": user_id,
                "group_id": group_id,
                "role": assigned_role
            }).execute()

            await update.message.reply_text(f"✅ Telegram linked and {assigned_role} role assigned!", parse_mode="Markdown")

        else:
            # If in private chat, just assign developer role (no group_id)
            supabase.from_("roles").insert({
                "user_id": user_id,
                "role": "developer"
            }).execute()

            await update.message.reply_text(
                "✅ Telegram linked!\n\n"
                "Now send `/link <your_code>` *in the group* to join it.",
                parse_mode="Markdown"
            )

        # 4. Mark OTC as used
        supabase.from_("otc_codes").update({"used": True}).eq("code", otc_code).execute()

    except Exception as e:
        print(f"Error in /link command: {e}")
        await update.message.reply_text("❗ Something went wrong while linking your account.")
