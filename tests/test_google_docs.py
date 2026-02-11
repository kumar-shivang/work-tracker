from app.services.google_docs import google_doc_client
import datetime

def test_google_docs():
    print("Testing Google Docs integration...")
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    message = f"Test entry from verification script at {timestamp}"
    
    print(f"Appending: '{message}'")
    google_doc_client.append_entry(message)
    print("Done. Please check the document.")

    print("Reading back content (first 500 chars)...")
    content = google_doc_client.read_day_content()
    print(f"Content length: {len(content)}")
    print(f"Snippet: {content[:500]}")

if __name__ == "__main__":
    test_google_docs()
