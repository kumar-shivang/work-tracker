import sys
import os
sys.path.append(os.getcwd())

from app.services.google_sheets import google_sheet_client

def create_sheets():
    if not google_sheet_client.service:
        print("Failed to initialize service.")
        return

    spreadsheet_id = google_sheet_client.spreadsheet_id
    required_sheets = ["Expenses", "Habits", "Journal"]
    
    # Get existing sheets
    try:
        spreadsheet = google_sheet_client.service.spreadsheets().get(
            spreadsheetId=spreadsheet_id).execute()
        existing_sheets = [s.get("properties", {}).get("title") for s in spreadsheet.get('sheets', [])]
    except Exception as e:
        print(f"Error fetching sheets: {e}")
        return

    requests = []
    for sheet_name in required_sheets:
        if sheet_name not in existing_sheets:
            print(f"Preparing to create sheet: {sheet_name}")
            requests.append({
                'addSheet': {
                    'properties': {
                        'title': sheet_name
                    }
                }
            })
            
            # Optional: Add header row
            # This is complex in a single batchUpdate with addSheet, usually we Create then Append.
            # For simplicity, let's just create the sheets first.
    
    if not requests:
        print("All required sheets already exist.")
        return

    body = {
        'requests': requests
    }

    try:
        response = google_sheet_client.service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        print("Successfully created sheets!")
        
        # Add Headers
        for sheet_name in required_sheets:
            if sheet_name == "Expenses" and sheet_name not in existing_sheets:
                 google_sheet_client.append_row(sheet_name, ["Date", "Time", "Amount", "Currency", "Category", "Description"])
            elif sheet_name == "Habits" and sheet_name not in existing_sheets:
                 google_sheet_client.append_row(sheet_name, ["Date", "Time", "Habit", "Status"])
            elif sheet_name == "Journal" and sheet_name not in existing_sheets:
                 google_sheet_client.append_row(sheet_name, ["Date", "Time", "Sentiment", "Entry"])
                 
        print("Headers added.")

    except Exception as e:
        print(f"Error creating sheets: {e}")

if __name__ == "__main__":
    create_sheets()
