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

INTENT_CLASSIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "intent_type": {
            "type": "string",
            "enum": ["reminder", "expense", "habit", "journal", "status_update", "other"],
            "description": "The type of request."
        }
    },
    "required": ["intent_type"],
    "additionalProperties": False
}

REMINDER_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"const": "reminder"},
        "content": {"type": "string", "description": "What to remind about"},
        "datetime": {"type": "string", "description": "ISO 8601 datetime"}
    },
    "required": ["type", "content", "datetime"],
    "additionalProperties": False
}

EXPENSE_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"const": "expense"},
        "content": {"type": "string", "description": "Description of expense"},
        "amount": {"type": "number"},
        "currency": {"type": "string"},
        "category": {"type": "string"}
    },
    "required": ["type", "content", "amount", "currency", "category"],
    "additionalProperties": False
}

HABIT_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"const": "habit"},
        "content": {"type": "string", "description": "Name of habit"}
    },
    "required": ["type", "content"],
    "additionalProperties": False
}

JOURNAL_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"const": "journal"},
        "content": {"type": "string", "description": "Journal entry"},
        "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]}
    },
    "required": ["type", "content", "sentiment"],
    "additionalProperties": False
}

STATUS_UPDATE_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"const": "status_update"},
        "content": {"type": "string", "description": "Status update text"}
    },
    "required": ["type", "content"],
    "additionalProperties": False
}

OTHER_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"const": "other"},
        "content": {"type": "string"}
    },
    "required": ["type", "content"],
    "additionalProperties": False
}
