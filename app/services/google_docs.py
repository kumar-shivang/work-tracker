import os
import datetime
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from app.config import Config

logger = logging.getLogger(__name__)

class GoogleDocClient:
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
        self.service_account_file = Config.SERVICE_ACCOUNT_FILE
        self.document_id = Config.GOOGLE_DOC_ID
        self.creds = None
        self.service = None
        self._authenticate()

    def _authenticate(self):
        try:
            if os.path.exists(self.service_account_file):
                self.creds = service_account.Credentials.from_service_account_file(
                    self.service_account_file, scopes=self.scopes)
                self.service = build('docs', 'v1', credentials=self.creds)
                logger.info("Authenticated with Google Docs API.")
            else:
                logger.error(f"Service account file not found: {self.service_account_file}")
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Docs: {e}")

    def append_entry(self, text: str):
        """
        Appends text to the document, ensuring a daily heading exists.
        """
        if not self.service or not self.document_id:
            logger.error("Google Docs service not initialized.")
            return

        ist_offset = datetime.timedelta(hours=5, minutes=30)
        ist_tz = datetime.timezone(ist_offset)
        today_heading = datetime.datetime.now(ist_tz).strftime("%d %B %Y")
        
        try:
            # 1. Get current document content to check for heading
            doc = self.service.documents().get(documentId=self.document_id).execute()
            content = doc.get('body').get('content')
            
            heading_exists = False
            end_index = content[-1]['endIndex'] - 1 # Insert at end

            for element in content:
                if 'paragraph' in element:
                    for run in element['paragraph']['elements']:
                        if 'textRun' in run and today_heading in run['textRun']['content']:
                            heading_exists = True
                            break
            
            requests = []
            
            # 2. Add heading if missing
            if not heading_exists:
                requests.append({
                    'insertText': {
                        'location': {'index': end_index},
                        'text': f"\n{today_heading}\n"
                    }
                })
                # Add heading style (Heading 1)
                # Note: Setting style requires knowing the range, which shifts. 
                # For simplicity, we just insert text. Advanced styling can be added if needed.
                # Let's just make it bold / large via text style or just plain text header for now.
                
                # Update index for next insertion
                end_index += len(today_heading) + 2

            # 3. Append the new entry
            requests.append({
                'insertText': {
                    'location': {'index': end_index}, # Append to end
                    'text': f"{text}\n"
                }
            })

            self.service.documents().batchUpdate(
                documentId=self.document_id, body={'requests': requests}).execute()
            
            logger.info("Appended entry to Google Doc.")
            
        except Exception as e:
            logger.error(f"Failed to append to Google Doc: {e}")

    def read_day_content(self) -> str:
        """
        Reads content for the current day (simple implementation: reads whole doc or last chunk).
        For evening summary, we might want to just parse the doc.
        
        Simplification: Return the full text for now, LLM handles extraction or 
        we rely on the local markdown files for the SUMMARY generation 
        but use Google Docs for the permanent log.
        
        Wait, if we use Google Docs *instead* of markdown, we must read from it for the summary.
        """
        if not self.service or not self.document_id:
            return ""

        try:
            doc = self.service.documents().get(documentId=self.document_id).execute()
            full_text = ""
            for element in doc.get('body').get('content'):
                if 'paragraph' in element:
                    for run in element['paragraph']['elements']:
                        if 'textRun' in run:
                            full_text += run['textRun']['content']
            return full_text
        except Exception as e:
            logger.error(f"Failed to read Google Doc: {e}")
            return ""

# Singleton
google_doc_client = GoogleDocClient()
