import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    # Handle optional split for empty string
    _tracked = os.getenv("TRACKED_REPOS", "")
    TRACKED_REPOS = _tracked.split(",") if _tracked else []
    
    # Prefer OPENROUTER_API_KEY from .env, fallback to OPENAI_API_KEY
    OPENAI_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "x-ai/grok-4.1-fast") # Default per .env
    
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    MY_TELEGRAM_CHAT_ID = os.getenv("MY_TELEGRAM_CHAT_ID")
    
    GMAIL_USER = os.getenv("GMAIL_USER")
    GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
    
    _recipients = os.getenv("EMAIL_RECIPIENTS", "")
    EMAIL_RECIPIENTS = _recipients.split(",") if _recipients else []
    
    SENDER_EMAIL = os.getenv("SENDER_EMAIL", GMAIL_USER)
    
    # Strip any potential comments or whitespace
    _port = os.getenv("API_PORT", "3001").split("#")[0].strip()
    API_PORT = int(_port) if _port.isdigit() else 3001
    
    TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")
    REPORT_DIR = "reports"

    # Alias for llm.py
    MODEL = os.getenv("MODEL", OPENAI_MODEL)
    
    # Google Docs
    GOOGLE_DOC_ID = os.getenv("GOOGLE_DOC_ID")
    SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE", "service-account-key.json")

    # Scheduler Timings
    # Check-ins
    CHECKIN_DAYS = os.getenv("CHECKIN_DAYS", "mon-fri")
    CHECKIN_START_HOUR = int(os.getenv("CHECKIN_START_HOUR", "9"))
    CHECKIN_END_HOUR = int(os.getenv("CHECKIN_END_HOUR", "18"))
    
    # Evening Summary
    SUMMARY_DAYS = os.getenv("SUMMARY_DAYS", "mon-fri")
    SUMMARY_HOUR = int(os.getenv("SUMMARY_HOUR", "18"))
    SUMMARY_MINUTE = int(os.getenv("SUMMARY_MINUTE", "30"))
