#!/usr/bin/env python3
"""
Initialize Google Workspace Manager
- Registers the Work Tracker Doc
- Registers the Personal Life Sheet
- Creates missing sheets (Expenses, Habits, Journal)
"""
import sys
import os
sys.path.append(os.getcwd())

from app.services.google_workspace import workspace_manager
from app.config import Config

def main():
    print("Initializing Google Workspace Manager...")
    
    # Register Work Tracker Doc
    if Config.GOOGLE_DOC_ID:
        print(f"Registering Work Tracker Doc: {Config.GOOGLE_DOC_ID}")
        workspace_manager.register_doc("WorkTracker", Config.GOOGLE_DOC_ID)
    else:
        print("⚠️  GOOGLE_DOC_ID not set, skipping Doc registration")
    
    # Register Personal Life Sheet
    if Config.GOOGLE_SHEET_ID:
        print(f"Registering Personal Life Sheet: {Config.GOOGLE_SHEET_ID}")
        workspace_manager.register_spreadsheet("PersonalLife", Config.GOOGLE_SHEET_ID)
        
        # Ensure required sheets exist
        required_sheets = ["Expenses", "Habits", "Journal"]
        for sheet_name in required_sheets:
            print(f"Ensuring sheet '{sheet_name}' exists...")
            workspace_manager.ensure_sheet_exists("PersonalLife", sheet_name)
    else:
        print("⚠️  GOOGLE_SHEET_ID not set, skipping Sheet registration")
    
    print("\n✅ Initialization complete!")
    print(f"State file: {workspace_manager.state_file}")

if __name__ == "__main__":
    main()
