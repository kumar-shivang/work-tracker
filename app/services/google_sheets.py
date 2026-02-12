import os
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from app.config import Config

logger = logging.getLogger(__name__)

class GoogleSheetClient:
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/spreadsheets']
        self.service_account_file = Config.SERVICE_ACCOUNT_FILE
        self.spreadsheet_id = Config.GOOGLE_SHEET_ID
        self.creds = None
        self.service = None
        self._authenticate()

    def _authenticate(self):
        try:
            if os.path.exists(self.service_account_file):
                self.creds = service_account.Credentials.from_service_account_file(
                    self.service_account_file, scopes=self.scopes)
                self.service = build('sheets', 'v4', credentials=self.creds)
                logger.info("Authenticated with Google Sheets API.")
            else:
                logger.error(f"Service account file not found: {self.service_account_file}")
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Sheets: {e}")

    def append_row(self, sheet_name: str, values: list):
        """
        Appends a row of values to the specified sheet.
        """
        if not self.service or not self.spreadsheet_id:
            logger.error("Google Sheets service not initialized.")
            return

        range_name = f"{sheet_name}!A1"
        body = {
            'values': [values]
        }

        try:
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            logger.info(f"Appended {result.get('updates').get('updatedCells')} cells to {sheet_name}.")
        except Exception as e:
            logger.error(f"Failed to append to Google Sheet '{sheet_name}': {e}")
            # Optional: Attempt to create sheet if it doesn't exist? 
            # For now, let's assume the user (or I) will create the sheets.

# Singleton
google_sheet_client = GoogleSheetClient()
