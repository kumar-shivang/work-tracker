import json
import os
import time
import httpx
from typing import Optional, List, Dict
from app.config import Config
from app.services.db_service import db_service

# Use Config for keys
OPENROUTER_API_KEY = Config.OPENAI_API_KEY
MODEL = Config.MODEL
referer = os.getenv("REFERER", "Personal Assistant")
x_title = os.getenv("X_TITLE", "Personal Assistant")
max_tokens = int(os.getenv("MAX_TOKENS", "8096"))

async def send_request(
    messages: List[Dict[str, str]], 
    schema: Optional[Dict[str, str]] = None,
    function_name: str = "unknown"
) -> str:
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

    start_time = time.time()
    response_text = ""
    error_msg = None
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0
            )
            
            if response.status_code != 200:
                error_msg = f"Error calling LLM: {response.text}"
                return error_msg

            output = response.json()
            if "choices" in output and len(output["choices"]) > 0:
                response_text = output["choices"][0]["message"]["content"]
            else:
                response_text = "No content returned from LLM."
                
            return response_text
            
    except Exception as e:
        error_msg = f"Exception calling LLM: {e}"
        return error_msg
        
    finally:
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Log to Database
        # Try-except to ensure logging failure doesn't crash the app
        try:
            # Parse output as JSON if schema was provided, else keep None
            output_parsed = None
            if schema and response_text and not error_msg:
                try:
                    clean_text = response_text
                    if clean_text.startswith("```json"):
                        clean_text = clean_text.replace("```json", "").replace("```", "").strip()
                    output_parsed = json.loads(clean_text)
                except:
                    pass

            await db_service.log_llm_call(
                function_name=function_name,
                model=MODEL,
                input_messages=messages,
                input_schema=schema,
                output_raw=response_text if not error_msg else None,
                output_parsed=output_parsed,
                duration_ms=duration_ms,
                error=error_msg
            )
        except Exception as log_err:
            print(f"Failed to log LLM call to DB: {log_err}")


from app.services.schemas import (
    COMMIT_SUMMARY_SCHEMA, DAILY_REPORT_SCHEMA, 
    INTENT_CLASSIFICATION_SCHEMA, REMINDER_SCHEMA, EXPENSE_SCHEMA, 
    HABIT_SCHEMA, JOURNAL_SCHEMA, STATUS_UPDATE_SCHEMA, OTHER_SCHEMA,
    CONVERSATIONAL_RESPONSE_SCHEMA, QUERY_SCHEMA
)

async def parse_user_intent(message: str, current_time: str) -> dict:
    """
    Parses the user's message to determine intent using a two-step process:
    1. Classify the intent type (Reminder, Expense, etc.)
    2. Extract details using the specific strict schema for that intent.
    """
    
    # Step 1: Classify
    classification_prompt = f"""
Classify the following message into one of these categories:
- reminder (setting a reminder or alarm)
- expense (logging money spent)
- habit (logging a habit like exercise, reading, etc.)
- journal (personal reflection or diary entry)
- status_update (work status or progress update)
- question (asking about past data, activities, or summaries)
- chat (casual conversation, greetings, or general talk)
- other (doesn't fit any category)

Message: "{message}"

Output a JSON object with 'intent_type'.
"""
    messages_1 = [
        {"role": "system", "content": "You are a helpful personal assistant. Output valid JSON."},
        {"role": "user", "content": classification_prompt}
    ]
    
    response_1 = await send_request(messages_1, schema=INTENT_CLASSIFICATION_SCHEMA, function_name="classify_intent")
    
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
        "question": QUERY_SCHEMA,
        "chat": OTHER_SCHEMA,
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
    
    response_2 = await send_request(messages_2, schema=selected_schema, function_name=f"extract_{intent_type}")
    
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


async def summarize_diff(diff_text: str) -> dict:
    """
    Summarizes a git diff into a structured dictionary.
    """
    prompt = f"""
Summarize this git diff into a structured JSON object.
Summarize this git diff into a structured JSON object.
Focus on WHAT changed and WHY.
Provide a short, descriptive TITLE for the commit (e.g. "Fix login bug", "Update user profile schema").

Diff:
{diff_text[:50000]} 
""" 
    
    messages = [
        {"role": "system", "content": "You are a helpful coding assistant. Output valid JSON."},
        {"role": "user", "content": prompt}
    ]
    
    response_str = await send_request(messages, schema=COMMIT_SUMMARY_SCHEMA, function_name="summarize_diff")
    
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

async def summarize_daily_report(report_content: str) -> dict:
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
    
    response_str = await send_request(messages, schema=DAILY_REPORT_SCHEMA, function_name="summarize_daily_report")
    
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

async def generate_daily_summary_text(activities_text: str) -> str:
    """
    Generate a concise daily summary from activities.
    Returns a plain text summary (not structured JSON).
    """
    prompt = f"""
You are a personal productivity assistant. Based on the following activities from today, 
create a concise, meaningful summary of the day's work and experiences. 
Focus on accomplishments, patterns, and insights. Be encouraging and constructive.

Today's Activities:
{activities_text}

Write a brief 2-3 paragraph summary.
"""
    
    messages = [
        {"role": "system", "content": "You are a personal assistant helping to summarize daily activities."},
        {"role": "user", "content": prompt}
    ]
    
    response_str = await send_request(messages, schema=None, function_name="generate_daily_summary")
    return response_str.strip()


async def generate_conversational_response(context_messages: list) -> dict:
    """
    Generate a conversational response using enriched context (history + memories).
    Returns a dict with 'response_text' and optional 'action'.
    """
    response_str = await send_request(
        context_messages, 
        schema=CONVERSATIONAL_RESPONSE_SCHEMA, 
        function_name="conversational_response"
    )
    
    try:
        if response_str.startswith("```json"):
            response_str = response_str.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(response_str)
        return parsed
    except (json.JSONDecodeError, AttributeError):
        return {
            "response_text": response_str if isinstance(response_str, str) else "I'm having trouble understanding. Could you rephrase?",
            "action": None
        }
