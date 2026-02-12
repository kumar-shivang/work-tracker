import requests
import json
import os
from typing import Optional, List, Dict
from app.config import Config

# Use Config for keys
OPENROUTER_API_KEY = Config.OPENAI_API_KEY
MODEL = Config.MODEL
referer = os.getenv("REFERER", "Personal Assistant")
x_title = os.getenv("X_TITLE", "Personal Assistant")
max_tokens = int(os.getenv("MAX_TOKENS", "8096"))

def send_request(messages:List[Dict[str,str]], schema:Optional[Dict[str,str]]=None) -> str:
    if not OPENROUTER_API_KEY:
        return "Error: OPENROUTER_API_KEY not set."

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": referer,
        "X-Title": x_title,
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "provider": {
            "sort": "price"
        }
    }
    
    if schema:
        # Strict structured output format
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "user_intent",
                "strict": True,
                "schema": schema
            }
        }

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=json.dumps(payload),
        )
        
        if response.status_code != 200:
            return f"Error calling LLM: {response.text}"

        output = response.json()
        if "choices" in output and len(output["choices"]) > 0:
            return output["choices"][0]["message"]["content"]
        return "No content returned from LLM."
    except Exception as e:
        return f"Exception calling LLM: {e}"

from app.services.schemas import (
    COMMIT_SUMMARY_SCHEMA, DAILY_REPORT_SCHEMA, 
    INTENT_CLASSIFICATION_SCHEMA, REMINDER_SCHEMA, EXPENSE_SCHEMA, 
    HABIT_SCHEMA, JOURNAL_SCHEMA, STATUS_UPDATE_SCHEMA, OTHER_SCHEMA
)

def parse_user_intent(message: str, current_time: str) -> dict:
    """
    Parses the user's message to determine intent using a two-step process:
    1. Classify the intent type (Reminder, Expense, etc.)
    2. Extract details using the specific strict schema for that intent.
    """
    
    # Step 1: Classify
    classification_prompt = f"""
Classify the following message into one of these categories:
- reminder
- expense
- habit
- journal
- status_update
- other

Message: "{message}"

Output a JSON object with 'intent_type'.
"""
    messages_1 = [
        {"role": "system", "content": "You are a helpful personal assistant. Output valid JSON."},
        {"role": "user", "content": classification_prompt}
    ]
    
    response_1 = send_request(messages_1, schema=INTENT_CLASSIFICATION_SCHEMA)
    
    intent_type = "status_update" # Default
    try:
        if response_1.startswith("```json"):
            response_1 = response_1.replace("```json", "").replace("```", "").strip()
        parsed_1 = json.loads(response_1)
        intent_type = parsed_1.get("intent_type", "status_update")
    except Exception as e:
        print(f"Error classifying intent: {e}")
        # Proceed with default
        
    # Step 2: Extract Details
    schema_map = {
        "reminder": REMINDER_SCHEMA,
        "expense": EXPENSE_SCHEMA,
        "habit": HABIT_SCHEMA,
        "journal": JOURNAL_SCHEMA,
        "status_update": STATUS_UPDATE_SCHEMA,
        "other": OTHER_SCHEMA
    }
    
    selected_schema = schema_map.get(intent_type, STATUS_UPDATE_SCHEMA)
    
    extraction_prompt = f"""
Extract details for the intent: {intent_type.upper()}

Current Time: {current_time}
Message: "{message}"

Output valid JSON matching the schema.
"""
    messages_2 = [
        {"role": "system", "content": "You are a helpful personal assistant. Output valid JSON."},
        {"role": "user", "content": extraction_prompt}
    ]
    
    response_2 = send_request(messages_2, schema=selected_schema)
    
    try:
        if response_2.startswith("```json"):
            response_2 = response_2.replace("```json", "").replace("```", "").strip()
        parsed_2 = json.loads(response_2)
        return parsed_2
        
    except json.JSONDecodeError:
        return {
            "type": "status_update",
            "content": message
        }


def summarize_diff(diff_text: str) -> dict:
    """
    Summarizes a git diff into a structured dictionary.
    """
    prompt = f"""
Summarize this git diff into a structured JSON object.
Focus on WHAT changed and WHY.

Diff:
{diff_text[:50000]} 
""" 
    
    messages = [
        {"role": "system", "content": "You are a helpful coding assistant. Output valid JSON."},
        {"role": "user", "content": prompt}
    ]
    
    response_str = send_request(messages, schema=COMMIT_SUMMARY_SCHEMA)
    
    try:
        # OpenRouter/LLM might return the JSON directly or inside markdown
        # send_request returns the content string.
        # We need to parse it. 
        if response_str.startswith("```json"):
            response_str = response_str.replace("```json", "").replace("```", "").strip()
        
        return json.loads(response_str)
    except json.JSONDecodeError:
        return {
            "files_modified": [],
            "key_changes": ["Error parsing LLM response"],
            "purpose": response_str
        }

def summarize_daily_report(report_content: str) -> dict:
    """
    Summarizes the full day's report into a structured dictionary.
    """
    prompt = f"""
Synthesize this daily development report into a structured JSON object.

Report Content:
{report_content[:50000]}
"""
    messages = [
        {"role": "system", "content": "You are a personal assistant. Output valid JSON."},
        {"role": "user", "content": prompt}
    ]
    
    response_str = send_request(messages, schema=DAILY_REPORT_SCHEMA)
    
    try:
        if response_str.startswith("```json"):
            response_str = response_str.replace("```json", "").replace("```", "").strip()
        return json.loads(response_str)
    except json.JSONDecodeError:
        return {
            "major_accomplishments": ["Error parsing JSON"],
            "critical_issues": [],
            "next_steps": []
        }
