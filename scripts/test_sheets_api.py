import sys
import os
sys.path.append(os.getcwd())

from app.services.google_sheets import google_sheet_client

def test_connection():
    if not google_sheet_client.service:
        print("Failed to initialize service.")
        return

    spreadsheet_id = google_sheet_client.spreadsheet_id
    print(f"Testing Spreadsheet ID: {spreadsheet_id}")

    try:
        spreadsheet = google_sheet_client.service.spreadsheets().get(
            spreadsheetId=spreadsheet_id).execute()
        
        sheets = spreadsheet.get('sheets', [])
        print("\nAvailable Sheets:")
        for sheet in sheets:
            title = sheet.get("properties", {}).get("title", "Unknown")
            print(f"- {title}")
            
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    test_connection()
