import asyncio
import json
import sys
from unittest.mock import MagicMock

# Mock google_docs before importing github
sys.path.insert(0, '/home/shivang/n8n')

# Create mock for google_doc_client
mock_doc_client = MagicMock()
mock_doc_client.append_entry = MagicMock()

# Inject mock into sys.modules
import app.services.google_docs
app.services.google_docs.google_doc_client = mock_doc_client

# Now import the webhook handler
from app.services.github import handle_github_webhook

async def test():
    with open("github-payload.json", "r") as f:
        payload = json.load(f)
    
    print("Testing webhook handler with real payload...")
    result = await handle_github_webhook(payload)
    print(f"\nResult: {result}")
    
    print(f"\nGoogle Doc append_entry called: {mock_doc_client.append_entry.called}")
    print(f"Call count: {mock_doc_client.append_entry.call_count}")
    
    if mock_doc_client.append_entry.called:
        print("\n=== Content appended to Google Doc ===")
        call_args = mock_doc_client.append_entry.call_args[0][0]
        print(call_args)

if __name__ == "__main__":
    asyncio.run(test())
