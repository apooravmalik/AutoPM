# utils/auth_helper.py
from .supabaseClient import supabase
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

def get_user_from_telegram(telegram_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve user information from Supabase using Telegram ID.
    
    Args:
        telegram_id (int): The Telegram user ID
        
    Returns:
        Optional[Dict[str, Any]]: User data if found, None otherwise
    """
    try:
        # Query the telegram_users table for the telegram_id
        response = supabase.table('telegram_users').select('*').eq('telegram_id', telegram_id).execute()
        
        if response.data and len(response.data) > 0:
            user = response.data[0]
            logger.info(f"User found for telegram_id {telegram_id}: {user.get('telegram_username', 'N/A')}")
            return user
        else:
            logger.warning(f"No user found for telegram_id {telegram_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error retrieving user for telegram_id {telegram_id}: {str(e)}")
        return None

def check_admin_permission(user_id: str, group_id: int) -> bool:
    """
    Check if a user has admin permissions for a specific group.
    Checks both:
    1. Global admin/developer role in roles table
    2. Group-specific admin in groups table
    
    Args:
        user_id (str): The user ID from the users table
        group_id (int): The Telegram group ID
        
    Returns:
        bool: True if user is admin or developer, False otherwise
    """
    try:
        # Check if user has global admin or developer role in roles table
        response = supabase.table('roles').select('role').eq('user_id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            roles = [role_data.get('role') for role_data in response.data]
            is_global_admin = 'admin' in roles or 'developer' in roles
            
            if is_global_admin:
                logger.info(f"Global admin access granted for user_id {user_id} with roles: {roles}")
                return True
        
        # Check if user is admin of the specific group
        group_response = supabase.table('groups').select('admin_id').eq('group_id', group_id).execute()
        
        if group_response.data and len(group_response.data) > 0:
            group_admin_id = group_response.data[0].get('admin_id')
            
            if group_admin_id == user_id:
                logger.info(f"Group admin access granted for user_id {user_id} in group {group_id}")
                return True
        
        logger.info(f"Admin access denied for user_id {user_id} in group {group_id}")
        return False
            
    except Exception as e:
        logger.error(f"Error checking admin permission for user_id {user_id} in group {group_id}: {str(e)}")
        return False