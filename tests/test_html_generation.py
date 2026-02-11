from app.services.llm import summarize_daily_report
from app.services.google_docs import google_doc_client

def test_summary_gen():
    print("Fetching today's content from Google Docs...")
    content = google_doc_client.read_day_content()
    
    if not content:
        print("No content found properly. Using dummy content.")
        content = """
        Commit: 12345 by Me at 10:00 - Implemented login
        Status: 11:00 - Working on backend
        Commit: 67890 by Me at 14:00 - Fixed bug in login
        Status: 17:00 - Deployment testing
        """
    
    print("\nGenerating HTML Summary...")
    html = summarize_daily_report(content)
    
    print("\n--- Generated HTML ---")
    print(html)
    print("----------------------")
    
    if "<h3>" in html and "<ul>" in html:
        print("\n✅ Verification Passed: Output contains expected HTML tags.")
    else:
        print("\n❌ Verification Failed: Output does not look like HTML.")

if __name__ == "__main__":
    test_summary_gen()
