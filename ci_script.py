#!/usr/bin/env python3
import os
import asyncio
from github import Github

# ---------------- Environment Variables ----------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
PR_NUMBER = int(os.getenv("PR_NUMBER"))

if not GITHUB_TOKEN:
    print("❌ ERROR: GITHUB_TOKEN not set.")
    exit(1)
if not GITHUB_REPOSITORY:
    print("❌ ERROR: GITHUB_REPOSITORY not set.")
    exit(1)
if not PR_NUMBER:
    print("❌ ERROR: PR_NUMBER not set.")
    exit(1)

# ---------------- Connect to GitHub ----------------
gh = Github(GITHUB_TOKEN)
repo = gh.get_repo(GITHUB_REPOSITORY)
pr = repo.get_pull(PR_NUMBER)
commit_id = pr.head.sha

# ---------------- Parse diff file ----------------
def parse_diff(file_path="diff.txt"):
    """
    Parse diff.txt into a list of changes with file paths and line numbers.
    Returns: list of tuples (file_path, line_in_diff, comment)
    """
    changes = []
    try:
        with open(file_path, "r") as f:
            current_file = None
            for line in f:
                if line.startswith("+++ b/"):
                    current_file = line.strip()[6:]
                elif line.startswith("+") and not line.startswith("+++"):
                    # For demo, comment on added lines
                    changes.append((current_file, line))
    except FileNotFoundError:
        print("⚠️ diff.txt not found. Skipping inline comments.")
    return changes

# ---------------- Create inline comments ----------------
async def post_inline_comments():
    changes = parse_diff()
    if not changes:
        print("No changes to comment on.")
        return

    for file_path, line_content in changes:
        try:
            # Note: GitHub requires 'position' in the diff, here using 1 as placeholder
            pr.create_review_comment(
                body=f"Review suggestion: {line_content.strip()}",
                commit_id=commit_id,
                path=file_path,
                position=1  # TODO: calculate correct line position in diff
            )
            print(f"✅ Comment posted to {file_path}")
        except Exception as e:
            print(f"❌ Failed to post comment on {file_path}: {e}")
            # Fallback to file
            with open("review_comment.txt", "a") as f:
                f.write(f"{file_path}: {line_content}\n")

# ---------------- Run async ----------------
if __name__ == "__main__":
    asyncio.run(post_inline_comments())

