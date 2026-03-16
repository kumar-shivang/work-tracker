import json
import os
import time
import logging
import httpx
from typing import Optional, List, Dict
from app.config import Config
from app.services.db_service import db_service

logger = logging.getLogger(__name__)

# Use Config for keys
OPENROUTER_API_KEY = Config.OPENAI_API_KEY
MODEL = Config.MODEL
FAST_MODEL = Config.FAST_MODEL
referer = os.getenv("REFERER", "Personal Assistant")
x_title = os.getenv("X_TITLE", "Personal Assistant")
max_tokens = int(os.getenv("MAX_TOKENS", "8096"))

async def send_request(
    messages: List[Dict[str, str]], 
    schema: Optional[Dict[str, str]] = None,
    function_name: str = "unknown",
    model: str = None
) -> str:
    if not OPENROUTER_API_KEY:
        return "Error: OPENROUTER_API_KEY not set."

    target_model = model or MODEL

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": referer,
        "X-Title": x_title,
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": target_model,
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
                model=target_model,
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
    COMMIT_SUMMARY_SCHEMA, DAILY_REPORT_SCHEMA, CONSOLIDATED_DAILY_SUMMARY_SCHEMA,
    INTENT_CLASSIFICATION_SCHEMA, REMINDER_SCHEMA, EXPENSE_SCHEMA, 
    HABIT_SCHEMA, JOURNAL_SCHEMA, STATUS_UPDATE_SCHEMA, OTHER_SCHEMA,
    CONVERSATIONAL_RESPONSE_SCHEMA, QUERY_SCHEMA, LOG_CLASSIFICATION_SCHEMA,
    RECALL_ANSWER_SCHEMA
)

async def classify_log_intent(text: str) -> dict:
    """
    Classify a log entry as 'work', 'personal', or 'ambiguous'.
    """
    prompt = f"""
    Classify the following log entry into one of these categories:
    - work: Professional tasks, coding, meetings, debugging, deployment.
    - personal: Hobbies, health, family, leisure, chores.
    - ambiguous: Not clearly work or personal, or contains elements of both.

    Log Entry: "{text}"

    Output valid JSON matching the schema.
    """
    messages = [
        {"role": "system", "content": "You are a helpful personal assistant. Output valid JSON."},
        {"role": "user", "content": prompt}
    ]

    # Use FAST_MODEL for quick classification
    response_str = await send_request(
        messages, 
        schema=LOG_CLASSIFICATION_SCHEMA, 
        function_name="classify_log_intent",
        model=FAST_MODEL
    )

    try:
        if response_str.startswith("```json"):
            response_str = response_str.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(response_str)
        return parsed
    except (json.JSONDecodeError, AttributeError):
        return {
            "category": "ambiguous",
            "confidence": 0.0,
            "reasoning": "Failed to parse LLM response"
        }

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
    
    # Use FAST_MODEL for quick classification
    response_1 = await send_request(
        messages_1, 
        schema=INTENT_CLASSIFICATION_SCHEMA, 
        function_name="classify_intent",
        model=FAST_MODEL
    )
    
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

Current Time (ISO 8601): {current_time}
User Message: "{message}"

IMPORTANT FORMATTING REQUIREMENTS:

1. All numeric values (amount, quantity, etc.) must be plain numbers:
   CORRECT: "amount": 72
   WRONG: "amount": {{"value": 72}}

2. Datetime values MUST be ISO 8601 format (YYYY-MM-DDTHH:MM:SS+HH:MM):
   CORRECT: "datetime": "2026-03-16T14:30:00+05:30"
   WRONG: "datetime": "tomorrow at 2pm" or null or empty string
   
   When parsing relative times (in 5 minutes, tomorrow at 3pm):
   - Calculate the absolute datetime from the current time: {current_time}
   - Always include timezone offset (+05:30 for IST)
   - Ensure the result is a valid ISO 8601 string

3. All required fields must be non-null and non-empty strings or numbers.

Output ONLY valid JSON. No markdown code blocks.
"""
    messages_2 = [
        {"role": "system", "content": "You are a helpful personal assistant. Output ONLY valid JSON, nothing else."},
        {"role": "user", "content": extraction_prompt}
    ]
    
    # Use FAST_MODEL for quick extraction with retry logic
    max_retries = 2
    for attempt in range(max_retries):
        response_2 = await send_request(
            messages_2, 
            schema=selected_schema, 
            function_name=f"extract_{intent_type}",
            model=FAST_MODEL
        )
        
        try:
            if response_2.startswith("```json"):
                response_2 = response_2.replace("```json", "").replace("```", "").strip()
            parsed_2 = json.loads(response_2)
            
            # Validate datetime field for reminders
            if intent_type == "reminder":
                datetime_str = parsed_2.get("datetime", "")
                if not datetime_str or not isinstance(datetime_str, str):
                    if attempt < max_retries - 1:
                        # Retry with more explicit instructions
                        messages_2.append({"role": "assistant", "content": response_2})
                        messages_2.append({
                            "role": "user",
                            "content": f"The datetime field is invalid: {datetime_str}. Please provide a valid ISO 8601 datetime string like '2026-03-16T14:30:00+05:30'."
                        })
                        continue
                    else:
                        raise ValueError(f"Invalid datetime after retries: {datetime_str}")
            
            # Clean extracted values - handle LLM providers that wrap values in objects
            parsed_2 = _clean_extracted_values(parsed_2)
            
            return parsed_2
        
        except (json.JSONDecodeError, ValueError) as e:
            if attempt < max_retries - 1:
                logger.warning(f"Extraction attempt {attempt + 1} failed: {e}. Retrying...")
                # Retry with simplified prompt
                messages_2.append({"role": "assistant", "content": response_2})
                messages_2.append({
                    "role": "user",
                    "content": "Invalid JSON or missing required fields. Please output ONLY valid JSON matching the required schema."
                })
                continue
            else:
                logger.error(f"Failed to extract intent after {max_retries} attempts: {e}")
                return {
                    "type": "status_update",
                    "content": message
                }


def _clean_extracted_values(data: dict) -> dict:
    """
    Clean extracted values from LLM responses.
    Some LLM providers wrap values in objects like {"value": 72, "type": "Number"}.
    This function extracts the actual values.
    """
    if not isinstance(data, dict):
        return data
    
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            # Check if this is a wrapped value (has 'value' key)
            if "value" in value:
                result[key] = value["value"]
            else:
                # Recursively clean nested objects
                result[key] = _clean_extracted_values(value)
        elif isinstance(value, list):
            # Clean list items
            result[key] = [
                _clean_extracted_values(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    
    return result


def _split_diff_by_files(diff_text: str) -> List[str]:
    """
    Split a diff into chunks by file boundaries.
    Each chunk starts with 'diff --git a/...' marker.
    """
    chunks = []
    current_chunk = []
    
    for line in diff_text.split('\n'):
        if line.startswith('diff --git') and current_chunk:
            # Start of a new file diff - save current chunk and start new one
            chunks.append('\n'.join(current_chunk))
            current_chunk = [line]
        else:
            current_chunk.append(line)
    
    # Add the last chunk
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    return chunks


def _batch_diff_chunks(chunks: List[str], max_chars_per_batch: int = 30000) -> List[str]:
    """
    Combine file chunks into larger batches while respecting max_chars_per_batch.
    This ensures we don't send too large prompts to the LLM.
    """
    batches = []
    current_batch = []
    current_size = 0
    
    for chunk in chunks:
        chunk_size = len(chunk)
        
        if current_size + chunk_size > max_chars_per_batch and current_batch:
            # Current batch is full, save it
            batches.append('\n'.join(current_batch))
            current_batch = [chunk]
            current_size = chunk_size
        else:
            # Add to current batch
            current_batch.append(chunk)
            current_size += chunk_size
    
    # Add the last batch
    if current_batch:
        batches.append('\n'.join(current_batch))
    
    return batches


async def _summarize_diff_batch(diff_text: str) -> dict:
    """
    Summarize a single batch of diff text.
    """
    prompt = f"""
Summarize this git diff into a structured JSON object.
Focus on WHAT changed and WHY.

Required fields:
- title: A short, descriptive title (under 50 chars)
- detailed_summary: A detailed paragraph (2-3 sentences) explaining what was changed and why. This will be included in an email summary, so make it substantive.
- files_modified: List of files changed
- key_changes: 3-5 bullet points of the most important changes
- purpose: The business/technical rationale for these changes

Diff:
{diff_text}
"""
    
    messages = [
        {"role": "system", "content": "You are a helpful coding assistant. Output valid JSON."},
        {"role": "user", "content": prompt}
    ]
    
    # Use default smart MODEL for heavy reasoning
    response_str = await send_request(messages, schema=COMMIT_SUMMARY_SCHEMA, function_name="summarize_diff")
    
    try:
        # Parse LLM response
        if response_str.startswith("```json"):
            response_str = response_str.replace("```json", "").replace("```", "").strip()
        
        return json.loads(response_str)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse diff summary: {e}")
        return {
            "title": "Unknown",
            "detailed_summary": response_str[:200] if response_str else "Error parsing response",
            "files_modified": [],
            "key_changes": [response_str[:100] if response_str else "Error parsing response"],
            "purpose": "Unable to parse LLM response"
        }


async def _combine_summaries(summaries: List[dict]) -> dict:
    """
    Combine multiple diff batch summaries into a single summary.
    """
    if not summaries:
        return {
            "title": "No changes",
            "detailed_summary": "No changes detected.",
            "files_modified": [],
            "key_changes": [],
            "purpose": "Empty diff"
        }
    
    if len(summaries) == 1:
        return summaries[0]
    
    # Combine multiple batch summaries
    all_files = []
    all_changes = []
    all_purposes = []
    all_detailed = []
    
    for summary in summaries:
        if isinstance(summary.get("files_modified"), list):
            all_files.extend(summary["files_modified"])
        if isinstance(summary.get("key_changes"), list):
            all_changes.extend(summary["key_changes"])
        if summary.get("purpose"):
            all_purposes.append(summary["purpose"])
        if summary.get("detailed_summary"):
            all_detailed.append(summary["detailed_summary"])
    
    # Remove duplicates while preserving order
    all_files = list(dict.fromkeys(all_files))
    all_changes = list(dict.fromkeys(all_changes))
    
    # Create final summary with all information
    combined_purpose = " ".join(set(all_purposes)) if all_purposes else "Multiple changes across multiple files"
    combined_detailed = " ".join(all_detailed) if all_detailed else "Multiple batches of changes were made."
    
    # Use first summary's title or create one from combined info
    title = summaries[0].get("title", "Multiple changes")
    
    return {
        "title": title,
        "detailed_summary": combined_detailed[:500],  # Limit to reasonable length
        "files_modified": all_files,
        "key_changes": all_changes[:10],  # Limit to 10 most important changes
        "purpose": combined_purpose[:500]  # Limit purpose to reasonable length
    }


async def summarize_diff(diff_text: str) -> dict:
    """
    Summarizes a git diff into a structured dictionary.
    Handles large diffs by splitting them into chunks and summarizing each chunk,
    then combining the results.
    """
    if not diff_text or not diff_text.strip():
        return {
            "title": "No changes",
            "files_modified": [],
            "key_changes": ["No diff content provided"],
            "purpose": "Empty commit or no changes detected"
        }
    
    logger.info(f"Summarizing diff of size: {len(diff_text)} bytes")
    
    # Try to summarize directly if diff is small
    if len(diff_text) < 15000:
        logger.info("Diff is small enough to summarize directly")
        return await _summarize_diff_batch(diff_text)
    
    # For large diffs, split by files and batch them
    logger.info("Diff is large, splitting into chunks...")
    file_chunks = _split_diff_by_files(diff_text)
    logger.info(f"Split diff into {len(file_chunks)} file chunks")
    
    # Batch file chunks to avoid token limits
    batches = _batch_diff_chunks(file_chunks, max_chars_per_batch=30000)
    logger.info(f"Created {len(batches)} batches for processing")
    
    # Summarize each batch
    summaries = []
    for i, batch in enumerate(batches):
        logger.info(f"Summarizing batch {i+1}/{len(batches)}...")
        try:
            batch_summary = await _summarize_diff_batch(batch)
            summaries.append(batch_summary)
        except Exception as e:
            logger.error(f"Error summarizing batch {i+1}: {e}")
            # Continue with other batches
            continue
    
    if not summaries:
        return {
            "title": "Unable to process",
            "files_modified": [],
            "key_changes": ["All batch summaries failed"],
            "purpose": "Error occurred while processing diff chunks"
        }
    
    # Combine all batch summaries into one
    final_summary = await _combine_summaries(summaries)
    logger.info(f"Combined {len(summaries)} batch summaries into final result")
    
    return final_summary

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
    
    # Use default smart MODEL for summarization
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


async def consolidate_commit_summaries(commit_summaries: List[dict]) -> dict:
    """
    Takes a list of individual commit summaries and consolidates them into a 
    comprehensive daily summary suitable for email/report distribution.
    
    Only includes actual accomplishments from commits - no speculation on challenges or future priorities.
    
    Args:
        commit_summaries: List of dicts with keys: title, detailed_summary, files_modified, key_changes, purpose
    
    Returns:
        Dict with consolidated daily summary including executive summary and organized accomplishments
    """
    if not commit_summaries:
        return {
            "executive_summary": "No commits or work activity recorded today.",
            "major_accomplishments": [],
            "technical_details": []
        }
    
    # Prepare the consolidated information from all commits
    consolidated_text = "Daily Commit Summary:\n\n"
    detailed_summaries = []
    all_files = set()
    all_purposes = []
    
    for i, summary in enumerate(commit_summaries, 1):
        title = summary.get("title", f"Commit {i}")
        detailed = summary.get("detailed_summary", "")
        files = summary.get("files_modified", [])
        purpose = summary.get("purpose", "")
        
        consolidated_text += f"{i}. {title}\n"
        if detailed:
            consolidated_text += f"   {detailed}\n"
        if purpose:
            consolidated_text += f"   Purpose: {purpose}\n"
        consolidated_text += "\n"
        
        if detailed:
            detailed_summaries.append(detailed)
        all_files.update(files)
        if purpose:
            all_purposes.append(purpose)
    
    # Add file information
    consolidated_text += f"\nTotal Files Modified: {len(all_files)}\n"
    consolidated_text += f"Key Areas: {', '.join(list(all_files)[:10])}\n"
    if len(all_files) > 10:
        consolidated_text += f"...and {len(all_files) - 10} more files\n"
    
    # Generate consolidated summary using LLM
    prompt = f"""
Based on the following work activity summaries from today, create a consolidated daily summary.
Focus ONLY on what was actually accomplished - do not invent or speculate about challenges or future priorities.

{consolidated_text}

Create a JSON response with:
- executive_summary: A 2-3 sentence overview of today's highlights based on actual work done
- major_accomplishments: Extract the actual completed tasks/commits from the list (these are real accomplishments)
- technical_details: Specific technical changes, implementations, or improvements made

Be factual and specific. Reference the actual work done in the commits.
"""
    
    messages = [
        {"role": "system", "content": "You are a technical summarizer. Create a comprehensive daily summary based only on actual commit data. Output valid JSON."},
        {"role": "user", "content": prompt}
    ]
    
    # Use default model for consolidation
    response_str = await send_request(
        messages, 
        schema=CONSOLIDATED_DAILY_SUMMARY_SCHEMA, 
        function_name="consolidate_commit_summaries"
    )
    
    try:
        if response_str.startswith("```json"):
            response_str = response_str.replace("```json", "").replace("```", "").strip()
        return json.loads(response_str)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to consolidate summaries: {e}")
        # Fallback to structured summary based on actual data
        return {
            "executive_summary": f"Completed {len(commit_summaries)} commits focused on: {', '.join(all_purposes[:3])}",
            "major_accomplishments": [s.get("title", "Work") for s in commit_summaries[:7]],
            "technical_details": detailed_summaries[:5]
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
    
    # Use default smart MODEL for creative summary
    response_str = await send_request(messages, schema=None, function_name="generate_daily_summary")
    return response_str.strip()


async def generate_conversational_response(context_messages: list) -> dict:
    """
    Generate a conversational response using enriched context (history + memories).
    Returns a dict with 'response_text' and optional 'action'.
    """
    # Use FAST_MODEL for quick chat replies
    response_str = await send_request(
        context_messages, 
        schema=CONVERSATIONAL_RESPONSE_SCHEMA, 
        function_name="conversational_response",
        model=FAST_MODEL
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


async def answer_recall_question(query: str, memory_text: str) -> dict:
    """
    Answer a user's recall question based on their stored memories.
    Returns a structured response with answer, confidence, and memory count.
    """
    messages = [
        {"role": "system", "content": "You are a personal assistant. Answer the user's question based on their stored memories. Be concise and helpful. Use emojis sparingly. Output valid JSON."},
        {"role": "user", "content": f"My question: {query}\n\nHere are relevant memories:\n{memory_text}\n\nAnswer my question based on these memories."}
    ]
    
    response_str = await send_request(
        messages, 
        schema=RECALL_ANSWER_SCHEMA, 
        function_name="recall_answer",
        model=FAST_MODEL
    )
    
    try:
        if response_str.startswith("```json"):
            response_str = response_str.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(response_str)
        return parsed
    except (json.JSONDecodeError, AttributeError):
        return {
            "answer": response_str if isinstance(response_str, str) else "I couldn't find relevant information.",
            "confidence": "low",
            "memory_count": 0
        }
