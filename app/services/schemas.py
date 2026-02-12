from typing import List, TypedDict

# Define standard dictionary structures for type hinting (optional but good for dev)
# The actual schema passed to LLM is a dict.

COMMIT_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "files_modified": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of files that were modified, added, or deleted."
        },
        "key_changes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Bulleted list of the most important changes."
        },
        "purpose": {
            "type": "string",
            "description": "A concise explanation of why these changes were made."
        }
    },
    "required": ["files_modified", "key_changes", "purpose"],
    "additionalProperties": False
}

DAILY_REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "major_accomplishments": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of significant completed tasks or milestones."
        },
        "critical_issues": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of blockers, bugs, or problems encountered."
        },
        "next_steps": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of planned tasks for the next day."
        }
    },
    "required": ["major_accomplishments", "critical_issues", "next_steps"],
    "additionalProperties": False
}

REMINDER_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["reminder", "status_update", "other"],
            "description": "The type of request. 'reminder' if the user wants to be reminded of something. 'status_update' if the user is providing a work update. 'other' for anything else."
        },
        "content": {
            "type": "string",
            "description": "The content of the reminder or status update. If it's a reminder, extract what needs to be reminded."
        },
        "datetime": {
            "type": "string",
            "description": "ISO 8601 datetime string for when the reminder should be set. Calculate based on the user's relative time ('in 10 minutes', 'tomorrow at 5pm') and the current time provided in the prompt. Only applicable if type is 'reminder'."
        }
    },
    "required": ["type", "content"],
    "additionalProperties": False
}
