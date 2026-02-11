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
