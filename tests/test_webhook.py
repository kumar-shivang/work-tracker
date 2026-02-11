import requests
import json
import time

def test_webhook():
    url = "http://localhost:3001/webhook/github"
    payload = {
        "ref": "refs/heads/main",
        "repository": {
            "name": "n8n",
            "full_name": "kumar-shivang/n8n",
            "owner": {
                "name": "kumar-shivang"
            }
        },
        "commits": [
            {
                "id": "test_sha_123",
                "message": "Test commit for webhook verification",
                "author": {
                    "name": "Shivang"
                }
            }
        ]
    }
    
    print(f"Sending payload to {url}...")
    try:
        response = requests.post(url, json=payload)
        print(f"Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    # Wait a bit for server to start if run immediately after
    time.sleep(2)
    test_webhook()
