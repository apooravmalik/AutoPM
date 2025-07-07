from telegram import Update
from telegram.ext import ContextTypes
from utils.supabaseClient import supabase

async def group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # For ChatMemberHandler, we need to access my_chat_member, not chat_member
        chat_member_update = update.my_chat_member
        
        if not chat_member_update:
            print("⚠️ my_chat_member is None. Ignoring.")
            return

        # Get chat information from the chat_member_update
        chat = chat_member_update.chat
        new_chat_member = chat_member_update.new_chat_member
        old_chat_member = chat_member_update.old_chat_member

        if not chat:
            print("⚠️ chat is None. Ignoring.")
            return

        # Only process group and supergroup chats
        if chat.type not in ["group", "supergroup"]:
            print(f"ℹ️ Ignoring chat type: {chat.type}")
            return

        # Check if bot was added to the group
        bot_user_id = context.bot.id
        
        if (new_chat_member.user.id != bot_user_id):
            print("ℹ️ Chat member update is not about the bot. Ignoring.")
            return

        # Check if bot was actually added (not removed or restricted)
        if new_chat_member.status not in ["member", "administrator"]:
            print(f"ℹ️ Bot status is '{new_chat_member.status}', not added to group.")
            return

        group_id = chat.id
        group_name = chat.title or "Unnamed Group"

        print(f"👥 Bot added to group: {group_name} ({group_id})")

        # Check if group already exists
        existing = supabase.from_("groups").select("group_id").eq("group_id", group_id).execute()

        if existing.data and len(existing.data) > 0:
            print("ℹ️ Group already registered.")
            return  # Already exists

        # Insert new group
        result = supabase.from_("groups").insert({
            "group_id": group_id,
            "group_name": group_name
        }).execute()

        if result.data:
            print(f"✅ Group {group_name} ({group_id}) registered in DB.")
        else:
            print(f"❌ Failed to register group in DB: {result}")

    except Exception as e:
        print(f"❌ Error in group_handler: {e}")
        import traceback
        traceback.print_exc()