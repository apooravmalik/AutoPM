from telegram import Update, Document, InputFile
from telegram.ext import ContextTypes
from datetime import datetime
from utils.supabaseClient import supabase
from utils.auth_helper import get_user_from_telegram, check_admin_permission
import os
from uuid import uuid4
import tempfile
from services.project_service import _create_project_service, _project_details_service, _project_files_service, _get_files_service

async def create_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command handler for /create_project.
    Parses arguments and calls the shared service function.
    """
    # 1. Telegram-specific checks
    if update.message.chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❗ This command must be used inside a group.")
        return

    # 2. Parse arguments
    if not context.args:
        await update.message.reply_text("❗ Usage: /create_project <name> | <description> | <raw_input>")
        return

    full_text = " ".join(context.args)
    parts = [p.strip() for p in full_text.split("|")]
    name = parts[0]
    
    if not name:
        await update.message.reply_text("❗ Project name is required.")
        return

    # 3. Call the shared service function
    success, message = _create_project_service(
        telegram_user_id=update.effective_user.id,
        group_id=update.effective_chat.id,
        name=name,
        description=parts[1] if len(parts) > 1 else None,
        raw_input=parts[2] if len(parts) > 2 else None
    )

    # 4. Reply to the user
    await update.message.reply_text(message, parse_mode="Markdown")

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
    """
    Command handler for /project_details.
    Parses arguments and calls the shared service function.
    """
    # 1. Telegram-specific checks
    if update.message.chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❗ This command must be used inside a group.")
        return

    # 2. Parse arguments
    if not context.args:
        await update.message.reply_text("❗ Usage: /project_details <project_name>")
        return
        
    # The project name is the entire text after the command
    project_name = " ".join(context.args)

    # 3. Call the shared service function
    success, message = _project_details_service(
        telegram_user_id=update.effective_user.id,
        group_id=update.effective_chat.id,
        project_name=project_name
    )

    # 4. Reply to the user
    await update.message.reply_text(message, parse_mode="Markdown")
        
        
# This dictionary holds the state for pending file uploads
AWAITING_FILE_UPLOAD = {}

async def project_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command handler for /project_files.
    Calls the service to validate the project, then sets the state to await a file.
    """
    # 1. Parse arguments
    if not context.args:
        await update.message.reply_text("❗ Usage: /project_files <Project_name>")
        return

    project_name = " ".join(context.args)

    # 2. Call the service function to get project details
    success, result_data = _project_files_service(
        telegram_user_id=update.effective_user.id,
        group_id=update.effective_chat.id,
        project_name=project_name
    )

    # 3. Handle the result
    if success:
        # If successful, set the state in the global dictionary
        AWAITING_FILE_UPLOAD[update.effective_user.id] = {
            "project_id": result_data["project_id"],
            "user_id": result_data["user_id"]
        }
        # Prompt the user for the file
        await update.message.reply_text("📎 Please upload the file you want to attach to this project.")
    else:
        # If it failed, send the error message from the service
        await update.message.reply_text(result_data["error_message"], parse_mode="Markdown")


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
    Command handler for /get_files.
    Calls the service to get file info, then downloads and sends each file.
    """
    if not context.args:
        await update.message.reply_text("❗ Usage: /get_files <ProjectName>")
        return

    project_name = " ".join(context.args)

    # Call the service to get the list of file information
    success, files_info, actual_project_name = _get_files_service(
        telegram_user_id=update.effective_user.id,
        group_id=update.effective_chat.id,
        project_name=project_name
    )

    if not success:
        # If the service failed, the third item in the tuple is the error message
        await update.message.reply_text(actual_project_name, parse_mode="Markdown")
        return
    
    if not files_info:
        # If there are no files, the third item is the "no files" message
        await update.message.reply_text(actual_project_name)
        return

    await update.message.reply_text(f"📂 Sending {len(files_info)} file(s) for project **{actual_project_name}**...", parse_mode="Markdown")

    for file_data in files_info:
        try:
            storage_path = f"project-files/{file_data['custom_name']}"
            
            # Download file from Supabase storage
            file_bytes = supabase.storage.from_("project-file-storage").download(storage_path)

            # Manually fetch the uploader's username
            uploader = "an unknown user"
            uploader_id = file_data.get("uploaded_by")
            if uploader_id:
                user_res = supabase.from_("telegram_users").select("telegram_username").eq("id", uploader_id).single().execute()
                if user_res.data and user_res.data.get("telegram_username"):
                    uploader = user_res.data["telegram_username"]

            # Send the document directly from memory
            await update.message.reply_document(
                document=file_bytes,
                filename=file_data["filename"],
                caption=f"{file_data['filename']} (uploaded by @{uploader})"
            )
        except Exception as e:
            print(f"Error sending file {file_data.get('filename')}: {e}")
            await update.message.reply_text(f"⚠️ Could not send file: {file_data.get('filename')}")
