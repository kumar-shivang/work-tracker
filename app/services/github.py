import os
import requests
import datetime
import logging
from app.config import Config
from app.services.llm import summarize_diff

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_diff(owner: str, repo: str, sha: str) -> str:
    """
    Fetches the diff for a specific commit using the GitHub API.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
    headers = {
        "Authorization": f"token {Config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3.diff"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        logger.error(f"Failed to fetch diff for {sha}: {response.status_code} - {response.text}")
        return ""

from app.services.google_docs import google_doc_client

def append_to_report(commit_data: dict, summary: dict):
    """
    Appends the commit summary to the Google Doc.
    summary is now a dict with keys: files_modified, key_changes, purpose
    """
    timestamp = datetime.datetime.now().strftime("%H:%M")
    
    # Format the structured summary into a readable string
    files = ", ".join(summary.get("files_modified", []))
    changes = "\n".join([f"- {change}" for change in summary.get("key_changes", [])])
    purpose = summary.get("purpose", "No purpose provided.")
    
    formatted_summary = f"""
**Purpose**: {purpose}

**Key Changes**:
{changes}

**Files**: {files}
"""

    entry = f"""
Commit: {commit_data['id'][:7]} by {commit_data['author']['name']} at {timestamp}
Repository: {commit_data['repository']['full_name']}
Branch: {commit_data['ref'].replace('refs/heads/', '')}
Message: {commit_data['message']}

Summary:
{formatted_summary}

--------------------------------------------------
"""
    # Use Google Doc Client
    google_doc_client.append_entry(entry)
    logger.info(f"Appended commit {commit_data['id'][:7]} to Google Doc")

async def handle_github_webhook(payload: dict):
    """
    Process the GitHub push event payload.
    """
    ref = payload.get("ref", "")
    # Only track pushes to main/master usually, but let's track all for now or filter if needed
    
    repository = payload.get("repository", {})
    repo_full_name = repository.get("full_name")
    
    # Check if we should track this repo
    # if repo_full_name not in Config.TRACKED_REPOS and Config.TRACKED_REPOS != [""]:
    #     logger.info(f"Skipping repo {repo_full_name} (not in tracked list)")
    #     return {"status": "skipped", "reason": "untracted repo"}

    commits = payload.get("commits", [])
    if not commits:
        return {"status": "no_commits"}
        
    for commit in commits:
        commit_sha = commit.get("id")
        commit_msg = commit.get("message")
        author_name = commit.get("author", {}).get("name")
        
        logger.info(f"Processing commit {commit_sha} by {author_name}")
        
        # 1. Fetch Diff
        owner = repository.get("owner", {}).get("name")
        repo_name = repository.get("name")
        
        diff_text = fetch_diff(owner, repo_name, commit_sha)
        
        if not diff_text:
            logger.warning(f"No diff found for {commit_sha}")
            summary = {
                "files_modified": [],
                "key_changes": ["No diff available (possibly empty commit or API error)."],
                "purpose": "Unable to fetch or process diff."
            }
        else:
            # 2. Summarize via LLM
            summary = summarize_diff(diff_text)
            
        # 3. Append to Report
        commit_data = {
            "id": commit_sha,
            "author": {"name": author_name},
            "repository": {"full_name": repo_full_name},
            "ref": ref,
            "message": commit_msg
        }
        append_to_report(commit_data, summary)
        
    return {"status": "processed", "commits_count": len(commits)}
