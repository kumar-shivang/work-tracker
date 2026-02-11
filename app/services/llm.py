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
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": schema
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

from app.services.schemas import COMMIT_SUMMARY_SCHEMA, DAILY_REPORT_SCHEMA

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
