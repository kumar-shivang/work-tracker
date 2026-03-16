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
        "detailed_summary": {
            "type": "string",
            "description": "A detailed paragraph (2-3 sentences) explaining what was changed and why. Should be substantive enough for an email summary."
        },
        "files_modified": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of files that were modified, added, or deleted."
        },
        "key_changes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Bulleted list (3-5 items) of the most important changes made."
        },
        "purpose": {
            "type": "string",
            "description": "A concise explanation of why these changes were made and their business/technical rationale."
        }
    },
    "required": ["title", "detailed_summary", "files_modified", "key_changes", "purpose"],
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

CONSOLIDATED_DAILY_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "executive_summary": {
            "type": "string",
            "description": "A concise 2-3 sentence overview of the day's work highlights."
        },
        "major_accomplishments": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of 5-7 significant completed tasks or milestones achieved today."
        },
        "technical_details": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Key technical changes, refactors, or architectural decisions made (3-5 items)."
        }
    },
    "required": ["executive_summary", "major_accomplishments", "technical_details"],
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
            "description": "Natural language response to send to the user. If a tool call is made, this should introduce the tool or be empty."
        },
        "action": {
            "type": ["object", "null"],
            "description": "Optional structured action detected in the message (e.g. creating a new reminder). Null if no action.",
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
        },
        "tool_call": {
            "type": ["object", "null"],
            "description": "Optional tool call to retrieve information. Null if no tool needed.",
            "properties": {
                "function_name": {
                    "type": "string",
                    "enum": ["view_expenses", "view_reminders", "view_habits", "view_stats", "view_calendar", "create_event"],
                    "description": "Name of the function to call."
                },
                "arguments": {
                    "type": "object",
                    "description": "Arguments for the function call.",
                    "additionalProperties": True
                }
            },
            "required": ["function_name", "arguments"]
        }
    },
    "required": ["response_text", "action", "tool_call"],
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

# ─── Tool Output Schemas ────────────────────────────────────

TOOL_OUTPUT_SCHEMAS = {
    "view_expenses": {
        "type": "object",
        "properties": {
            "expenses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "amount": {"type": "number"},
                        "currency": {"type": "string"},
                        "category": {"type": "string"},
                        "description": {"type": "string"}
                    }
                }
            },
            "total_count": {"type": "integer"}
        }
    },
    "view_reminders": {
        "type": "object",
        "properties": {
            "reminders": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "time": {"type": "string"},
                        "content": {"type": "string"},
                        "is_fired": {"type": "boolean"}
                    }
                }
            },
            "total_count": {"type": "integer"}
        }
    },
    "view_habits": {
        "type": "object",
        "properties": {
            "habits": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "time": {"type": "string"}
                    }
                }
            },
            "date": {"type": "string"}
        }
    },
    "view_calendar": {
        "type": "object",
        "properties": {
            "events": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "start": {"type": "string"},
                        "link": {"type": "string"}
                    }
                }
            }
        }
    },
    "create_event": {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["success", "error"]},
            "link": {"type": "string"},
            "message": {"type": "string"}
        },
        "required": ["status"]
    }
}

LOG_CLASSIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": ["work", "personal", "ambiguous"],
            "description": "Classify the log entry. Use 'ambiguous' if it's unclear or could be both."
        },
        "confidence": {
            "type": "number",
            "description": "Confidence score between 0.0 and 1.0"
        },
        "reasoning": {
            "type": "string",
            "description": "Brief explanation for the classification"
        }
    },
    "required": ["category", "confidence", "reasoning"],
    "additionalProperties": False
}

RECALL_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "description": "A concise answer to the user's question based on their memories"
        },
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"],
            "description": "How confident you are in the answer based on available memories"
        },
        "memory_count": {
            "type": "integer",
            "description": "Number of relevant memories used to answer"
        }
    },
    "required": ["answer", "confidence", "memory_count"],
    "additionalProperties": False
}
