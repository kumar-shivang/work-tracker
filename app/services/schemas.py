from typing import List, TypedDict

# Define standard dictionary structures for type hinting (optional but good for dev)
# The actual schema passed to LLM is a dict.

COMMIT_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "A short, descriptive title for the commit (under 50 chars)."
        },
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
    "required": ["title", "files_modified", "key_changes", "purpose"],
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
            "enum": ["reminder", "expense", "habit", "journal", "status_update", "question", "chat", "other"],
            "description": "The type of request. Use 'question' when the user asks about their past data/activities. Use 'chat' for casual conversation."
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

CONVERSATIONAL_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "response_text": {
            "type": "string",
            "description": "Natural language response to send to the user."
        },
        "action": {
            "type": ["object", "null"],
            "description": "Optional structured action detected in the message. Null if no action.",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["reminder", "expense", "habit", "journal", "status_update", "none"]
                },
                "content": {"type": "string"},
                "amount": {"type": ["number", "null"]},
                "currency": {"type": ["string", "null"]},
                "category": {"type": ["string", "null"]},
                "datetime": {"type": ["string", "null"]},
                "sentiment": {"type": ["string", "null"]}
            },
            "required": ["type", "content"]
        }
    },
    "required": ["response_text", "action"],
    "additionalProperties": False
}

QUERY_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"const": "question"},
        "content": {"type": "string", "description": "The user's question rephrased for clarity"},
        "search_query": {"type": "string", "description": "Optimized query for semantic memory search"},
        "data_type": {
            "type": ["string", "null"],
            "enum": ["expense", "habit", "journal", "commit", "reminder", "status_update", "daily_summary", None],
            "description": "Specific data type to filter by, or null for general search"
        }
    },
    "required": ["type", "content", "search_query", "data_type"],
    "additionalProperties": False
}
