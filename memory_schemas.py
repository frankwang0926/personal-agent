"""Model-facing descriptions for the local personal memory tools."""

REMEMBER_TOOL = {
    "type": "function",
    "name": "remember",
    "description": (
        "Store or update a personal fact only when the user explicitly asks you "
        "to remember it. Use a stable, descriptive key. The value replaces any "
        "existing value for that key. A successful write returns null."
    ),
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Exact fact key, e.g. project_name."},
            "value": {"type": "string", "description": "The fact to store as text."},
        },
        "required": ["key", "value"],
        "additionalProperties": False,
    },
}

RECALL_TOOL = {
    "type": "function",
    "name": "recall",
    "description": (
        "Retrieve a previously stored personal fact using its exact key. "
        "A missing fact produces an error; do not invent a remembered value."
    ),
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Exact fact key, e.g. project_name."},
        },
        "required": ["key"],
        "additionalProperties": False,
    },
}
