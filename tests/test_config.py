import os
from app.config import Config

class TestConfig(Config):
    """
    Configuration for End-to-End Speed Run.
    Overrides timing settings to ensure jobs run immediately or frequently.
    """
    # Check-in every minute
    CHECKIN_DAYS = "*" # Every day
    CHECKIN_START_HOUR = "*" # Every hour
    CHECKIN_END_HOUR = "*" # Every hour
    # Actually, cron doesn't support "every hour" in the range field nicely if we used start-end
    # But our config uses f"{START}-{END}" in scheduler.py
    # If we pass specific values here, we might need to patch scheduler or use mock env vars.
    # A cleaner way is to set env vars before importing main/scheduler.
    pass

# We will set environment variables in e2e_test.py instead of using this class directly,
# because the application imports Config from config.py
