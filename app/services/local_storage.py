import os
import datetime
import logging
from app.config import Config

logger = logging.getLogger(__name__)

class LocalStorage:
    def __init__(self, base_dir: str = "daily_reports"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def append_daily_entry(self, title: str, summary: dict, commit_data: dict):
        """
        Appends a commit summary to the daily markdown file.
        """
        ist_offset = datetime.timedelta(hours=5, minutes=30)
        ist_tz = datetime.timezone(ist_offset)
        now = datetime.datetime.now(ist_tz)
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")
        
        filename = os.path.join(self.base_dir, f"{date_str}.md")
        
        # Create file with user-friendly heading if it doesn't exist
        if not os.path.exists(filename):
            with open(filename, "w") as f:
                f.write(f"# Daily Report - {now.strftime('%d %B %Y')}\n\n")
        
        # Format the entry
        files = ", ".join(summary.get("files_modified", []))
        changes = "\n".join([f"- {change}" for change in summary.get("key_changes", [])])
        purpose = summary.get("purpose", "No purpose provided.")
        
        entry = f"""## {time_str} - {title}

**Commit**: `{commit_data['id'][:7]}` by {commit_data['author']['name']}
**Repo**: {commit_data['repository']['full_name']}
**Branch**: {commit_data['ref'].replace('refs/heads/', '')}

**Purpose**: {purpose}

**Key Changes**:
{changes}

**Files**: `{files}`

---
"""
        
        try:
            with open(filename, "a") as f:
                f.write(entry)
            logger.info(f"Appended entry to local file: {filename}")
        except Exception as e:
            logger.error(f"Failed to append to local file {filename}: {e}")

# Singleton instance
local_storage = LocalStorage()
