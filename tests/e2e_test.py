import asyncio
import os
import time
from datetime import datetime

# 1. Setup Environment for "Speed Run" BEFORE importing app modules
os.environ["CHECKIN_DAYS"] = "*"  # Every day
os.environ["CHECKIN_START_HOUR"] = "0"
os.environ["CHECKIN_END_HOUR"] = "23" 
# We want check-ins to happen, but waiting for cron is slow (1 min minimum).
# We will trigger functions DIRECTLY for the speed test.

from app.services.telegram import bot
from app.services.google_docs import google_doc_client
from app.tasks.evening_summary import generate_and_send_summary
from app.services.github import handle_github_webhook

async def run_e2e_speed_test():
    print("🚀 Starting End-to-End Speed Run...")
    
    # --- Step 1: Simulate Morning Check-In ---
    print("\n[1/4] Simulating Morning Check-In...")
    # Directly call the logging logic as if the bot received a message
    # We can't easily simulate the USER replying to the bot without a real Telegram client.
    # So we will simulate the BOT receiving an update or just directly calling log_checkin.
    
    bot.log_checkin("Starting E2E Speed Test - Planning")
    print("✅ Logged Check-In: 'Starting E2E Speed Test - Planning'")

    # --- Step 2: Simulate GitHub Push ---
    print("\n[2/4] Simulating GitHub Push...")
    dummy_payload = {
        "ref": "refs/heads/feature/speed-test",
        "repository": {
            "name": "n8n-assistant",
            "full_name": "shivang/n8n-assistant",
            "owner": {"name": "shivang"}
        },
        "commits": [
            {
                "id": "e2e_speed_test_commit_hash",
                "message": "Optimization: Added configurable timings",
                "author": {"name": "Shivang"},
                "url": "http://github.com/fake/commit"
            }
        ],
        "head_commit": {
            "id": "e2e_speed_test_commit_hash",
            "message": "Optimization: Added configurable timings",
            "author": {"name": "Shivang"},
            "url": "http://github.com/fake/commit"
        }
    }
    # Note: handle_github_webhook usually expects a Request object if called via FastAPI route,
    # but the logic inside might be separable? 
    # github_handler.py -> handle_github_webhook takes `payload: dict`? 
    # Let's check github_handler.py signature. It takes `request: Request`. 
    # We might need to mock the request or call the internal logic.
    # Looking at previous file views, `handle_github_webhook` takes `request: Request`.
    # But `fetch_diff` and `append_to_report` are internal.
    # Let's verify `github_handler.py` again. 
    # Actually, we can just call `append_to_report` directly to simulate the RESULT of a webhook
    # because `fetch_diff` requires a real GitHub commit SHA (which 'e2e_speed_test' is not).
    
    from app.services.github import append_to_report
    summary = {
        "files_modified": ["config.py", "scheduler.py"],
        "key_changes": ["Added timing variables", "Updated scheduler to use config"],
        "purpose": "To allow configurable run times for testing."
    }
    
    commit_data = {
        "id": "e2e1234",
        "author": {"name": "SpeedTester"},
        "repository": {"full_name": "shivang/n8n-assistant"},
        "ref": "refs/heads/test",
        "message": "Speed run commit"
    }
    
    append_to_report(commit_data, summary)
    print("✅ Logged Commit: 'Speed run commit'")

    # --- Step 3: Simulate Afternoon Check-In ---
    print("\n[3/4] Simulating Afternoon Check-In...")
    bot.log_checkin("E2E Test - Implementation Complete")
    print("✅ Logged Check-In: 'E2E Test - Implementation Complete'")

    # --- Step 4: Simulate Evening Summary ---
    print("\n[4/4] Generating Evening Summary (Email)...")
    await generate_and_send_summary()
    print("✅ Evening Summary Sent")

    print("\n🎉 Speed Run Complete! Please check your Google Doc and Email.")

if __name__ == "__main__":
    asyncio.run(run_e2e_speed_test())
