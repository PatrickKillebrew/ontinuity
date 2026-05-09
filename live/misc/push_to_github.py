"""
ONTINUITY GITHUB SYNC
=====================
Pushes files to the PatrickKillebrew/ontinuity GitHub repo.

Called two ways:
1. By NppEventExec on every Ctrl+S in Notepad++ (for .py files)
2. By run_ods.bat after each session ends (for session logs)

Usage: python push_to_github.py "C:\path\to\file"

Setup:
1. pip install PyGithub
2. Set GITHUB_TOKEN below (your existing token with repo scope)
3. Confirm REPO_NAME matches your repo exactly
"""

import sys
import os
from github import Github, GithubException

# -----------------------------------------
# CONFIGURATION — set your token before first run
# -----------------------------------------

GITHUB_TOKEN = "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"
REPO_NAME    = "PatrickKillebrew/ontinuity"

# -----------------------------------------
# ROUTING LOGIC
# Determines where in the repo the file lands
# based on what type of file it is
# -----------------------------------------

def get_github_path(local_path):
    """
    Returns the destination path in the GitHub repo.

    .py files   → live/filename.py
    .txt files  → live/sessions/filename.txt
    .png/.jpg   → live/screenshots/filename.ext
    anything else → live/misc/filename.ext
    """
    filename = os.path.basename(local_path)
    ext      = os.path.splitext(filename)[1].lower()

    if ext == ".py":
        return f"live/{filename}"

    elif ext == ".txt":
        return f"live/sessions/{filename}"

    elif ext in [".png", ".jpg", ".jpeg"]:
        return f"live/screenshots/{filename}"

    else:
        return f"live/misc/{filename}"


# -----------------------------------------
# SYNC LOGIC
# -----------------------------------------

def push_file(local_path):
    if not os.path.exists(local_path):
        print(f"[SYNC] File not found: {local_path}")
        return

    filename    = os.path.basename(local_path)
    github_path = get_github_path(local_path)

    # Read file content
    try:
        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        # Try binary for images
        with open(local_path, "rb") as f:
            content = f.read()

    try:
        g    = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)

        try:
            # File exists — update it
            existing = repo.get_contents(github_path)
            repo.update_file(
                path    = github_path,
                message = f"[sync] {filename}",
                content = content,
                sha     = existing.sha
            )
            print(f"[SYNC] Updated {github_path}")

        except GithubException as e:
            if e.status == 404:
                # File doesn't exist yet — create it
                repo.create_file(
                    path    = github_path,
                    message = f"[sync] {filename} (first upload)",
                    content = content
                )
                print(f"[SYNC] Created {github_path}")
            else:
                raise

    except Exception as e:
        print(f"[SYNC] Error: {e}")
        print(f"[SYNC] Check your GitHub token and repo name in push_to_github.py")


# -----------------------------------------
# ENTRY POINT
# -----------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("[SYNC] No file path provided")
        print("[SYNC] Usage: python push_to_github.py <filepath>")
        sys.exit(1)

    local_path = sys.argv[1]
    print(f"[SYNC] Syncing: {os.path.basename(local_path)}")
    push_file(local_path)
