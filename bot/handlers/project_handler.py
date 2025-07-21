from telegram import Update, Document, InputFile
from telegram.ext import ContextTypes
from datetime import datetime
from utils.supabaseClient import supabase
from utils.auth_helper import get_user_from_telegram, check_admin_permission
import os
from uuid import uuid4
import tempfile

async def create_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("❗ Usage: /create_project <name> | <description> | <raw_input>")
            return

        full_text = " ".join(context.args)
        parts = [p.strip() for p in full_text.split("|")]

        if len(parts) < 1:
            await update.message.reply_text("❗ Project name is required.\n\nFormat:\n/create_project <name> | <description> | <raw_input>")
            return

        name = parts[0]
        description = parts[1] if len(parts) > 1 else None
        raw_input = parts[2] if len(parts) > 2 else None

        telegram_id = update.effective_user.id
        group_id = update.effective_chat.id if update.effective_chat.type in ["group", "supergroup"] else None

        user_res = get_user_from_telegram(telegram_id)
        if not user_res:
            await update.message.reply_text("❗ You are not linked yet. Use /link to link your Telegram account.")
            return

        owner_id = user_res["id"]

        if not group_id:
            await update.message.reply_text("❗ This command must be used inside a group.")
            return

        group_res = supabase.from_("groups").select("group_id").eq("group_id", group_id).single().execute()
        if not group_res.data:
            await update.message.reply_text("❗ Group is not registered. Use /link in this group first.")
            return

        if not check_admin_permission(owner_id, group_id):
            await update.message.reply_text("❌ Only admins can create projects.")
            return

        existing = supabase.from_("projects").select("id").eq("group_id", group_id).eq("name", name).execute()
        if existing.data and len(existing.data) > 0:
            await update.message.reply_text(f"⚠️ A project with the name *{name}* already exists in this group.", parse_mode="Markdown")
            return

        insert_data = {
            "name": name,
            "description": description,
            "owner_id": owner_id,
            "group_id": group_id,
            "raw_input": raw_input
        }

        supabase.from_("projects").insert(insert_data).execute()
        print(f"✅ Project *{name}* created successfully!")
        await update.message.reply_text(f"✅ Project *{name}* created successfully!", parse_mode="Markdown")

    except Exception as e:
        print(f"Error in /create_project: {e}")
        await update.message.reply_text("❗ Failed to create project. Please try again.")


async def delete_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Delete a project by its ID along with its tasks.
    Usage: /delete_project | <project_id>
    """
    try:
        user_data = get_user_from_telegram(update.effective_user.id)
        if not user_data:
            await update.message.reply_text("❌ Please link your Telegram account first using /link")
            return

        if not context.args:
            await update.message.reply_text(
                "❗ Usage: `/delete_project | <project_id>`",
                parse_mode="Markdown"
            )
            return

        full_text = " ".join(context.args)
        parts = [p.strip() for p in full_text.split("|")]
        project_id = parts[0] if parts else None

        if not project_id:
            await update.message.reply_text("❗ Please provide a valid project ID.")
            return

        group_id = update.message.chat.id if update.message.chat.type in ["group", "supergroup"] else None

        query = supabase.from_("projects").select("*").eq("id", project_id)
        if group_id:
            query = query.eq("group_id", group_id)

        project_result = query.execute()

        if not project_result.data:
            await update.message.reply_text("❌ No project found with that ID.")
            return

        project = project_result.data[0]

        supabase.from_("tasks").delete().eq("project_id", project_id).execute()
        delete_result = supabase.from_("projects").delete().eq("id", project_id).execute()

        if delete_result.data:
            await update.message.reply_text(
                f"🗑️ Project **{project['name']}** and its tasks deleted successfully.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Failed to delete the project.")

    except Exception as e:
        print(f"Error in delete_project: {e}")
        await update.message.reply_text("❗ Something went wrong while deleting the project.")


async def project_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("❗ Usage: /project_details | <project_name>")
            return

        full_text = " ".join(context.args)
        parts = [p.strip() for p in full_text.split("|")]
        project_name = parts[0] if parts else None

        if not project_name:
            await update.message.reply_text("❗ Please provide a valid project name.")
            return

        telegram_id = update.effective_user.id
        user_data = get_user_from_telegram(telegram_id)
        if not user_data:
            await update.message.reply_text("❌ Please link your Telegram account first using /link")
            return

        group_id = update.effective_chat.id if update.effective_chat.type in ["group", "supergroup"] else None
        if not group_id:
            await update.message.reply_text("❗ This command must be used inside a group.")
            return

        response = supabase.from_("projects").select("*")\
            .eq("name", project_name).eq("group_id", group_id).single().execute()

        if not response.data:
            await update.message.reply_text(f"❌ No project named *{project_name}* found in this group.", parse_mode="Markdown")
            return

        project = response.data
        text = (
            f"📋 *Project Details*\n\n"
            f"🆔 ID: `{project['id']}`\n"
            f"📛 Name: *{project['name']}*\n"
            f"🧾 Description: {project.get('description', '—')}\n"
            f"🧠 Raw Input: {project.get('raw_input', '—')}\n"
            f"👤 Owner ID: `{project['owner_id']}`\n"
            f"🕒 Created At: {project.get('created_at', '—')}"
        )

        await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        print(f"Error in project_details: {e}")
        await update.message.reply_text("❗ Something went wrong while fetching project details.")
        
        
AWAITING_FILE_UPLOAD = {}

async def project_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command: /project_files | <Project_name>
    Prompts user to upload a file and links it to the project.
    """
    try:
        user = get_user_from_telegram(update.effective_user.id)
        if not user:
            await update.message.reply_text("❗ Please link your Telegram account using /link.")
            return

        if not context.args:
            await update.message.reply_text("❗ Usage: /project_files | <Project_name>")
            return
        
        print(f"Context args: {context.args}")

        full_text = " ".join(context.args)
        parts = [p.strip() for p in full_text.split("|") if p.strip()]

        project_name = parts[0] if parts else None
        
        print(f"Project name: {project_name}")

        if not project_name:
            await update.message.reply_text("❗ Project name is required.")
            return

        group_id = update.effective_chat.id
        project_res = supabase.from_("projects").select("id").eq("name", project_name).eq("group_id", group_id).execute()

        if not project_res.data:
            await update.message.reply_text(f"❌ No project found with name: *{project_name}*", parse_mode="Markdown")
            return

        project_id = project_res.data[0]["id"]
        AWAITING_FILE_UPLOAD[update.effective_user.id] = {
            "project_id": project_id,
            "user_id": user["id"]
        }

        await update.message.reply_text("📎 Please upload the file you want to attach to this project.")

    except Exception as e:
        print(f"Error in handle_project_files: {e}")
        await update.message.reply_text("❗ Something went wrong. Please try again.")

async def handle_document_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles file uploads after the /project_files command.
    """
    try:
        user_id = update.effective_user.id
        file_data = AWAITING_FILE_UPLOAD.get(user_id)
        if not file_data:
            return  # Not waiting for this user’s upload

        file: Document = update.message.document
        if not file:
            await update.message.reply_text("❗ Please send a valid file (PDF/TXT).")
            return

        project_id = file_data["project_id"]
        uploaded_by = file_data["user_id"]

        # Download file from Telegram
        file_name = file.file_name
        file_ext = os.path.splitext(file_name)[1].lower()
        file_unique_name = f"{project_id}_{file_name}"

        # Download to temp
        telegram_file = await context.bot.get_file(file.file_id)
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, file_unique_name)
        await telegram_file.download_to_drive(temp_path)

        # Upload to Supabase bucket
        with open(temp_path, "rb") as f:
            supabase.storage.from_("project-file-storage").upload(
                path=f"project-files/{file_unique_name}",
                file=f,
                file_options={"content-type": file.mime_type}
            )

        # Insert metadata into DB
        supabase.from_("project_files").insert({
            "id": str(uuid4()),
            "project_id": project_id,
            "filename": file_name,
            "custom_name": file_unique_name,
            "type": file_ext,
            "uploaded_by": uploaded_by
        }).execute()

        del AWAITING_FILE_UPLOAD[user_id]
        await update.message.reply_text(f"✅ File *{file_name}* uploaded and tagged to project!", parse_mode="Markdown")

        # Clean temp file
        os.remove(temp_path)

    except Exception as e:
        print(f"Error in handle_document_upload: {e}")
        await update.message.reply_text("❗ Failed to upload file.")


async def get_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Usage: /get_files | ProjectName
    """
    try:
        full_text = " ".join(context.args)
        parts = [p.strip() for p in full_text.split("|") if p.strip()]
        project_name = parts[0] if parts else None

        if not project_name:
            await update.message.reply_text("❗ Please provide a project name.\nFormat: `/get_files | ProjectName`", parse_mode="Markdown")
            return

        # Get project ID
        project_resp = supabase.from_("projects").select("id").eq("name", project_name).execute()
        if not project_resp.data or len(project_resp.data) == 0:
            await update.message.reply_text(f"❗ No project found with name *{project_name}*", parse_mode="Markdown")
            return

        project_id = project_resp.data[0]["id"]

        # Get file metadata
        files_resp = supabase.from_("project_files").select("*").eq("project_id", project_id).execute()
        files = files_resp.data

        if not files:
            await update.message.reply_text("📭 No files attached to this project.")
            return

        await update.message.reply_text(f"📂 Sending {len(files)} file(s) for project *{project_name}*...", parse_mode="Markdown")

        for file in files:
            storage_path = f"project-files/{file['custom_name']}"

            # Create a temp path
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_path = tmp_file.name

            # Download file from Supabase
            res = supabase.storage.from_("project-file-storage").download(storage_path)
            with open(tmp_path, "wb") as f:
                f.write(res)
                
            #get user name from user_id
            user_name = supabase.from_("telegram_users").select("telegram_username").eq("id", file['uploaded_by']).execute().data[0]["telegram_username"]

            # Send to Telegram
            await update.message.reply_document(
                document=InputFile(tmp_path, filename=file["filename"]),
                caption=f"{file['filename']} (uploaded by user: {user_name})"
            )

            # Clean temp
            os.remove(tmp_path)

    except Exception as e:
        print(f"Error in handle_get_files: {e}")
        await update.message.reply_text("❗ Failed to retrieve files.")