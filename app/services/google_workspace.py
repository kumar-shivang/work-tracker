import json
import os
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from app.config import Config

logger = logging.getLogger(__name__)

class GWorkspaceManager:
    """
    Unified manager for Google Docs and Sheets with persistent state tracking.
    Stores IDs and current indices in a local JSON file to simplify API interactions.
    """
    
    def __init__(self, state_file='gworkspace_state.json'):
        self.scopes = [
            'https://www.googleapis.com/auth/documents',
            'https://www.googleapis.com/auth/spreadsheets'
        ]
        self.service_account_file = Config.SERVICE_ACCOUNT_FILE
        self.state_file = state_file
        self.creds = None
        self.docs_service = None
        self.sheets_service = None
        self.state = self._load_state()
        self._authenticate()

    def _authenticate(self):
        try:
            if os.path.exists(self.service_account_file):
                self.creds = service_account.Credentials.from_service_account_file(
                    self.service_account_file, scopes=self.scopes)
                self.docs_service = build('docs', 'v1', credentials=self.creds)
                self.sheets_service = build('sheets', 'v4', credentials=self.creds)
                logger.info("Authenticated with Google Workspace.")
            else:
                logger.error(f"Service account file not found: {self.service_account_file}")
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Workspace: {e}")

    def _load_state(self):
        """Load tracking data from JSON or initialize a new one."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning("State file corrupted, starting fresh.")
        return {"docs": {}, "sheets": {}}

    def _save_state(self):
        """Persist current IDs and indices to the JSON file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    # --- GOOGLE DOCS METHODS ---

    def register_doc(self, friendly_name: str, doc_id: str):
        """Track an existing Google Doc."""
        if not self.docs_service: return
        
        try:
            # We fetch the doc to get the current end index (length)
            doc = self.docs_service.documents().get(documentId=doc_id).execute()
            # The content length is the end index of the last element
            content = doc.get('body').get('content', [])
            end_index = content[-1].get('endIndex', 1) if content else 1
            
            self.state['docs'][friendly_name] = {
                "id": doc_id,
                "cursor": end_index
            }
            self._save_state()
            logger.info(f"Registered doc '{friendly_name}' with length {end_index}")
        except Exception as e:
            logger.error(f"Failed to register doc '{friendly_name}': {e}")

    def append_to_doc(self, friendly_name: str, text: str):
        """
        Appends text to a tracked doc and updates the index.
        Simple append for now to match interface properly.
        """
        if friendly_name not in self.state['docs']:
             # Attempt auto-register if ID is known (e.g. from Config)
             if friendly_name == "WorkTracker" and Config.GOOGLE_DOC_ID:
                 self.register_doc("WorkTracker", Config.GOOGLE_DOC_ID)
             else:
                logger.error(f"Doc '{friendly_name}' is not registered.")
                return

        doc_info = self.state['docs'][friendly_name]
        doc_id = doc_info['id']
        start_index = doc_info['cursor']
        # Google Docs index excludes the final newline, verify we are appending correctly
        # Usually it's safer to just insert at end index - 1 if we want to stay inside
        # But 'endIndex' of document usually means the very end.
        # Let's trust the state for now, but valid index is essential.
        
        # If cursor is 0 or 1, might be empty doc.
        if start_index < 1: start_index = 1

        requests = [{
            'insertText': {
                'location': {'index': start_index - 1}, # Append before the final EOF marker
                'text': text + "\n"
            }
        }]

        try:
            self.docs_service.documents().batchUpdate(
                documentId=doc_id, body={'requests': requests}
            ).execute()

            # Update state roughly (API doesn't return new index directly in response for batch)
            # We should probably re-fetch or calc carefully. 
            # For robustness, let's re-fetch to stay synced.
            self.register_doc(friendly_name, doc_id) 
            
            logger.info(f"Appended to '{friendly_name}'")
        except Exception as e:
            logger.error(f"Failed to append to doc '{friendly_name}': {e}")
            # Try to re-sync state on failure
            self.register_doc(friendly_name, doc_id)

    # --- GOOGLE SHEETS METHODS ---

    def register_spreadsheet(self, friendly_name: str, spreadsheet_id: str):
        """Track an existing spreadsheet and its sheet tabs."""
        if not self.sheets_service: return

        try:
            ss = self.sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            
            sheet_data = {}
            for s in ss.get('sheets', []):
                title = s['properties']['title']
                sheet_data[title] = {
                    "id": s['properties']['sheetId'],
                    "rows": s['properties']['gridProperties'].get('rowCount', 0) 
                    # Note: rowCount is total rows, not used rows. 
                    # We usually want to append, so we might not need to track 'rows' if we use 'append' API.
                    # But the requirement was to use the Manager's unified approach.
                    # The user's snippet uses 'insertDimension' and 'updateCells' which requires knowing where to insert.
                    # Standard 'append' is easier. Let's stick to standard append for now for reliability?
                    # "Google Sheets API Append" is robust. The user's "Manager" code does manual insertion.
                    # Using manual insertion allows inserting at top (log style).
                    # Let's support both or stick to the user's snippet logic if requested.
                    # The user said "use it and enhance it".
                }

            self.state['sheets'][friendly_name] = {
                "id": spreadsheet_id,
                "tabs": sheet_data
            }
            self._save_state()
            logger.info(f"Registered spreadsheet '{friendly_name}'")
        except Exception as e:
            logger.error(f"Failed to register spreadsheet '{friendly_name}': {e}")

    def ensure_sheet_exists(self, friendly_name: str, sheet_title: str):
        """Creates a sheet tab if it doesn't exist."""
        ss_info = self.state['sheets'].get(friendly_name)
        if not ss_info: return

        if sheet_title in ss_info['tabs']:
            return

        spreadsheet_id = ss_info['id']
        try:
            req = {
                'requests': [{
                    'addSheet': {
                        'properties': {'title': sheet_title}
                    }
                }]
            }
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body=req).execute()
            
            # Re-register to update state with new sheet ID
            self.register_spreadsheet(friendly_name, spreadsheet_id)
            
            # Add headers
            self._add_header(friendly_name, sheet_title)
            
            logger.info(f"Created sheet '{sheet_title}' in '{friendly_name}'")
        except Exception as e:
            logger.error(f"Failed to create sheet '{sheet_title}': {e}")

    def _add_header(self, friendly_name, sheet_title):
        headers = {
            "Expenses": ["Date", "Time", "Amount", "Currency", "Category", "Description"],
            "Habits": ["Date", "Time", "Habit", "Status"],
            "Journal": ["Date", "Time", "Sentiment", "Entry"]
        }
        if sheet_title in headers:
            # We can use the simple append here for headers
            self.append_row(friendly_name, sheet_title, headers[sheet_title])

    def append_row(self, friendly_name: str, tab_name: str, values: list):
        """
        Appends to end of sheet using standard API (robust).
        """
        ss_info = self.state['sheets'].get(friendly_name)
        if not ss_info: 
             if friendly_name == "PersonalLife" and Config.GOOGLE_SHEET_ID:
                 self.register_spreadsheet("PersonalLife", Config.GOOGLE_SHEET_ID)
                 ss_info = self.state['sheets'].get(friendly_name)
             
             if not ss_info:
                logger.error(f"Spreadsheet '{friendly_name}' not registered.")
                return

        # Ensure tab exists
        if tab_name not in ss_info.get('tabs', {}):
            self.ensure_sheet_exists(friendly_name, tab_name)

        spreadsheet_id = ss_info['id']
        range_name = f"{tab_name}!A1"
        body = {'values': [values]}

        try:
            self.sheets_service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            logger.info(f"Appended row to '{tab_name}'")
        except Exception as e:
            logger.error(f"Failed to append to '{tab_name}': {e}")

# Singleton
workspace_manager = GWorkspaceManager()
