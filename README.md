AutoPM Bot Commands Reference
=====================================

AUTHENTICATION COMMANDS
========================

/link <OTC>
- Description: Link your Telegram account to the web app
- Required: OTC (One-Time Code from web app)
- Usage: /link ABC123XYZ
- Notes: Must first generate OTC from web app Settings. Can be used in groups or private chat.

TASK MANAGEMENT COMMANDS
=========================

/create_task <title> | <description> | <project_name> | <deadline>
- Description: Create a new task (Admin only)
- Required: title
- Optional: description, project_name, deadline (YYYY-MM-DD format)
- Usage Examples:
  - /create_task Fix login bug
  - /create_task Fix login bug | Login form validation issue
  - /create_task Fix login bug | Login form validation issue | Dashboard Project
  - /create_task Fix login bug | Login form validation issue | Dashboard Project | 2024-12-31
- Notes: Must be used in groups. Only admins can create tasks.

/assign @username | <task_name>
- Description: Assign a task to a user (Admin only)
- Required: username (with @), task_name
- Usage: /assign @john | Fix login bug
- Notes: Must be used in groups. Only admins can assign tasks.

/working <task_name>
- Description: Mark your assigned task as "In Progress"
- Required: task_name
- Usage: /working Fix login bug
- Notes: Only works for tasks assigned to you.

/completed <task_name>
- Description: Mark your task as completed
- Required: task_name
- Usage: /completed Fix login bug
- Notes: Only works for tasks assigned to you and currently "In Progress".

/tasks
- Description: List all your assigned tasks grouped by status
- Required: None
- Usage: /tasks
- Notes: Shows tasks with deadline urgency indicators.

/history <task_name>
- Description: View task history and status changes
- Required: task_name
- Usage: /history Fix login bug
- Notes: Shows chronological log of task events.

/delete_task <task_id>
- Description: Delete a task by its ID
- Required: task_id
- Usage: /delete_task 123
- Notes: Must be used in groups. Deletes task and all associated logs.

/task_details <task_name>
- Description: Get detailed information about a task
- Required: task_name
- Usage: /task_details Fix login bug
- Notes: Shows tasks with "Assigned" or "Pending" status only.

PROJECT MANAGEMENT COMMANDS
============================

/create_project <name> | <description> | <raw_input>
- Description: Create a new project (Admin only)
- Required: name
- Optional: description, raw_input
- Usage Examples:
  - /create_project Dashboard
  - /create_project Dashboard | User management system
  - /create_project Dashboard | User management system | Initial requirements document
- Notes: Must be used in groups. Only admins can create projects.

/delete_project | <project_id>
- Description: Delete a project and all its associated tasks
- Required: project_id
- Usage: /delete_project | 456
- Notes: Permanently deletes project and all linked tasks.

/project_details | <project_name>
- Description: Get detailed information about a project
- Required: project_name
- Usage: /project_details | Dashboard
- Notes: Must be used in groups.

/project_files | <project_name>
- Description: Initiate file upload process for a project
- Required: project_name
- Usage: /project_files | Dashboard
- Notes: After running this command, upload a document file to attach it to the project.

/get_files | <project_name>
- Description: Download all files attached to a project
- Required: project_name
- Usage: /get_files | Dashboard
- Notes: Bot will send all files associated with the project.

GENERAL COMMANDS
================

hello / hi / hey
- Description: Get welcome message and setup instructions
- Required: None
- Usage: Simply type "hello", "hi", or "hey"
- Notes: Provides login instructions and web app link.

COMMAND SYNTAX NOTES
=====================

Pipe Symbol (|): Used to separate parameters in multi-parameter commands
- Example: /create_task Title | Description | Project | 2024-12-31

Required vs Optional Parameters:
- <parameter> = Required
- [parameter] = Optional (shown in examples above)

Date Format: 
- Always use YYYY-MM-DD format for deadlines
- Example: 2024-12-31

Username Format:
- Always include @ symbol when mentioning users
- Example: @username

PERMISSION REQUIREMENTS
=======================

Admin Only Commands:
- /create_task
- /assign
- /create_project
- /delete_project

User Commands (for assigned tasks):
- /working
- /completed
- /tasks
- /history

General Commands (all users):
- /link
- /task_details
- /project_details
- /project_files
- /get_files
- /delete_task

IMPORTANT NOTES
===============

1. Most commands must be used in groups (not private chat)
2. You must link your account with /link before using other commands
3. Generate OTC from web app (http://localhost:5173/) Settings page
4. Task names in commands support partial matching (case-insensitive)
5. File uploads are supported for projects (PDF/TXT files)
6. Deadline warnings appear for overdue/urgent tasks
7. All task operations are logged in the database
8. Groups are automatically registered when bot is added
