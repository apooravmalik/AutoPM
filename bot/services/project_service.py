from typing import Tuple, Dict, Any, List
from utils.supabaseClient import supabase
from utils.auth_helper import get_user_from_telegram, check_admin_permission

def _create_project_service(
    telegram_user_id: int,
    group_id: int,
    name: str,
    description: str = None,
    raw_input: str = None
) -> Tuple[bool, str]:
    """
    Core logic to create a project.
    Returns a tuple: (success, message).
    """
    try:
        # 1. Permission checks
        user_data = get_user_from_telegram(telegram_user_id)
        if not user_data:
            return (False, "❗ You are not linked yet. Use /link first.")
        
        if not check_admin_permission(user_data["id"], group_id):
            return (False, "❌ Only admins can create projects.")

        # 2. Check if project with the same name already exists
        existing = supabase.from_("projects").select("id").eq("group_id", group_id).eq("name", name).execute()
        if existing.data:
            return (False, f"⚠️ A project with the name **{name}** already exists in this group.")

        # 3. Insert the new project
        insert_data = {
            "name": name,
            "description": description,
            "owner_id": user_data["id"],
            "group_id": group_id,
            "raw_input": raw_input
        }
        result = supabase.from_("projects").insert(insert_data).execute()

        if not result.data:
            return (False, "❗ Failed to create project in the database.")

        return (True, f"✅ Project **{name}** created successfully!")

    except Exception as e:
        print(f"Error in _create_project_service: {e}")
        return (False, "❗ An unexpected error occurred while creating the project.")


def _project_details_service(
    telegram_user_id: int,
    group_id: int,
    project_name: str
) -> Tuple[bool, str]:
    """
    Core logic to fetch and format details for a specific project.
    Returns a tuple: (success, message).
    """
    try:
        # 1. Permission check (user must be linked)
        if not get_user_from_telegram(telegram_user_id):
            return (False, "❗ You are not linked yet. Use /link first.")

        # 2. Fetch the project from the database
        response = supabase.from_("projects").select("*")\
            .eq("name", project_name).eq("group_id", group_id).single().execute()

        if not response.data:
            return (False, f"❌ No project named **{project_name}** found in this group.")

        project = response.data
        owner_id = project.get('owner_id')
        owner_username = f"`{owner_id}`" # Default to showing the ID

        # 3. Fetch the owner's username
        if owner_id:
            user_res = supabase.from_("telegram_users").select("telegram_username").eq("id", owner_id).single().execute()
            if user_res.data and user_res.data.get("telegram_username"):
                owner_username = f"@{user_res.data['telegram_username']}"

        # 4. Format the details into a message
        message = (
            f"📋 **Project Details**\n\n"
            f"🆔 ID: `{project['id']}`\n"
            f"📛 Name: **{project['name']}**\n"
            f"🧾 Description: {project.get('description', '—')}\n"
            f"🧠 Raw Input: {project.get('raw_input', '—')}\n"
            f"👤 Owner: {owner_username}\n"
            f"🕒 Created At: {project.get('created_at', '—')}"
        )
        return (True, message)

    except Exception as e:
        print(f"Error in _project_details_service: {e}")
        return (False, "❗ An unexpected error occurred while fetching project details.")

def _project_files_service(
    telegram_user_id: int,
    group_id: int,
    project_name: str
) -> Tuple[bool, Dict[str, Any]]:
    """
    Core logic to validate a project for file upload.
    Returns a tuple: (success, result_dictionary).
    On success, the dictionary contains project_id and user_id.
    On failure, it contains an error_message.
    """
    try:
        # 1. Check if the user is linked
        user_data = get_user_from_telegram(telegram_user_id)
        if not user_data:
            return (False, {"error_message": "❗ Please link your Telegram account using /link."})

        # 2. Find the specified project in the group
        project_res = supabase.from_("projects").select("id").eq("name", project_name).eq("group_id", group_id).single().execute()

        if not project_res.data:
            return (False, {"error_message": f"❌ No project found with name: **{project_name}**"})

        # 3. Return the necessary IDs for the handler to set the state
        result_data = {
            "project_id": project_res.data["id"],
            "user_id": user_data["id"]
        }
        return (True, result_data)

    except Exception as e:
        print(f"Error in _project_files_service: {e}")
        return (False, {"error_message": "❗ An unexpected error occurred."})
    
    
def _get_files_service(
    telegram_user_id: int,
    group_id: int,
    project_name: str
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """
    Core logic to fetch metadata for all files in a project.
    Returns a tuple: (success, list_of_file_info, project_name).
    The file_info dictionary contains everything needed to download and send a file.
    """
    try:
        # 1. Permission check (user must be linked)
        if not get_user_from_telegram(telegram_user_id):
            return (False, [], "User not linked.")

        # 2. Find the project
        project_resp = supabase.from_("projects").select("id, name").eq("name", project_name).eq("group_id", group_id).single().execute()
        if not project_resp.data:
            return (False, [], f"❗ No project found with name **{project_name}**")
        
        project_id = project_resp.data["id"]
        actual_project_name = project_resp.data["name"]

        # 3. Get file metadata.
        files_resp = (
            supabase.from_("project_files")
            .select("*")
            .eq("project_id", project_id)
            .execute()
        )
        
        if not files_resp.data:
            return (True, [], "📭 No files attached to this project.")

        return (True, files_resp.data, actual_project_name)

    except Exception as e:
        print(f"Error in _get_files_service: {e}")
        return (False, [], "❗ An unexpected error occurred.")