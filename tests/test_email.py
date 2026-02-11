from app.services.email import send_email
from app.config import Config

def test_email():
    print(f"Sending test email to {Config.EMAIL_RECIPIENTS}...")
    subject = "Test Email from Personal Assistant"
    body = "<h1>It Works!</h1><p>This is a test email to verify SMTP configuration.</p>"
    
    success = send_email(subject, body)
    if success:
        print("SUCCESS: Email sent.")
    else:
        print("FAILURE: Email not sent. Check logs.")

if __name__ == "__main__":
    test_email()
