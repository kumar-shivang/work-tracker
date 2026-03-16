import os
import logging
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from app.config import Config

logger = logging.getLogger(__name__)

class GoogleCalendarClient:
    """
    Client for interacting with Google Calendar using a Service Account.
    """
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/calendar']
        self.service_account_file = Config.SERVICE_ACCOUNT_FILE
        # Service accounts refer to calendars by the owner's email address
        self.calendar_id = getattr(Config, 'GOOGLE_CALENDAR_ID', 'primary')
        self.creds = None
        self.service = None
        self._authenticate()

    def _authenticate(self):
        try:
            if os.path.exists(self.service_account_file):
                self.creds = service_account.Credentials.from_service_account_file(
                    self.service_account_file, scopes=self.scopes)
                self.service = build('calendar', 'v3', credentials=self.creds)
                logger.info("Authenticated with Google Calendar API.")
            else:
                logger.error(f"Service account file not found: {self.service_account_file}")
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Calendar: {e}")

    def create_event(self, summary: str, description: str, start_time: datetime.datetime, duration_minutes: int = 30):
        """
        Creates a new event on the calendar.
        """
        if not self.service:
            logger.error("Calendar service not initialized.")
            return

        end_time = start_time + datetime.timedelta(minutes=duration_minutes)

        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC', # Adjust as per your config
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            },
        }

        try:
            event = self.service.events().insert(calendarId=self.calendar_id, body=event).execute()
            logger.info(f"Event created: {event.get('htmlLink')}")
            return event
        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
            return None

    def list_upcoming_events(self, max_results: int = 10):
        """
        Lists the next 'max_results' events from the calendar.
        """
        if not self.service: return []

        now = datetime.datetime.utcnow().isoformat() + 'Z'
        try:
            events_result = self.service.events().list(
                calendarId=self.calendar_id, timeMin=now,
                maxResults=max_results, singleEvents=True,
                orderBy='startTime'
            ).execute()
            return events_result.get('items', [])
        except Exception as e:
            logger.error(f"Failed to list events: {e}")
            return []

    def update_event(self, event_id: str, updates: dict):
        """
        Updates an existing event using patch (partial update).
        """
        if not self.service: return None
        try:
            updated_event = self.service.events().patch(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=updates
            ).execute()
            logger.info(f"Event {event_id} updated.")
            return updated_event
        except Exception as e:
            logger.error(f"Failed to update event {event_id}: {e}")
            return None

# Singleton
google_calendar_client = GoogleCalendarClient()
