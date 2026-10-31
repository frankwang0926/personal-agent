"""Model-facing descriptions for task capture and tracking."""

CREATE_TASK_TOOL = {
    "type": "function",
    "name": "create_task",
    "description": (
        "Create a task when the user asks to track something they need to do. "
        "Returns the saved task with its generated ID and open status. "
        "This does not schedule reminders or notifications."
    ),
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "A concise description of the task."},
        },
        "required": ["title"],
        "additionalProperties": False,
    },
}

LIST_TASKS_TOOL = {
    "type": "function",
    "name": "list_tasks",
    "description": (
        "Read the current saved tasks, including their IDs, titles, and open/done "
        "statuses. Use this source of truth to answer task questions and identify "
        "a task before updating it."
    ),
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
}

UPDATE_TASK_TOOL = {
    "type": "function",
    "name": "update_task",
    "description": (
        "Rename a task or change its status using an actual ID from the task store. "
        "Set an unchanged field to null; provide at least one change. Setting "
        "status to done completes the task. Returns the saved updated record. "
        "If the user's reference matches multiple tasks, ask which one first."
    ),
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "Exact persisted task ID; never invent one."},
            "title": {"type": ["string", "null"], "description": "New title, or null to preserve it."},
            "status": {
                "type": ["string", "null"],
                "enum": ["open", "done", None],
                "description": "New status, or null to preserve it.",
            },
        },
        "required": ["task_id", "title", "status"],
        "additionalProperties": False,
    },
}
