#!/usr/bin/env python3  # Shebang to ensure the script runs with Python 3

import os  # For accessing environment variables
import asyncio  # To support asynchronous execution
from github import Github, GithubException  # GitHub API client
from pathlib import Path  # For file path checks

# Optional Azure OpenAI imports (used if you integrate Azure)
# from azure.identity import DefaultAzureCredential
# from azure.ai.openai import AsyncOpenAIClient

# -----------------------------
# Environment Variables
# -----------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Token to authenticate GitHub API requests
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")  # e.g., "owner/repo"
PR_NUMBER = int(os.getenv("PR_NUMBER", 0))  # Pull request number to comment on
DIFF_FILE = "diff.txt"  # Local diff file path

# -----------------------------
# Validate Environment Variables
# -----------------------------
if not GITHUB_TOKEN:
    print("❌ ERROR: GITHUB_TOKEN not set.")  # Inline comment: fail early if token missing
    exit(1)
if not GITHUB_REPOSITORY:
    print("❌ ERROR: GITHUB_REPOSITORY not set.")  # Fail if repo info missing
    exit(1)
if PR_NUMBER == 0:
    print("❌ ERROR: PR_NUMBER not set.")  # Fail if PR number not provided
    exit(1)
if not Path(DIFF_FILE).exists():
    print(f"❌ ERROR: {DIFF_FILE} not found.")  # Fail if diff file is missing
    exit(1)

# -----------------------------
# GitHub Client Setup
# -----------------------------
gh = Github(GITHUB_TOKEN)  # Inline comment: instantiate GitHub API client
repo = gh.get_repo(GITHUB_REPOSITORY)  # Get repository object
pr = repo.get_pull(PR_NUMBER)  # Get the PR object

# -----------------------------
# Load Diff
# -----------------------------
with open(DIFF_FILE, "r") as f:
    diff_lines = f.readlines()  # Read all lines from diff.txt for analysis

# -----------------------------
# Placeholder AI Review Function
# -----------------------------
async def analyze_line(line):
    """
    Async function to analyze a line from the diff.
    Replace this with your AsyncAzureOpenAI logic.
    """
    if "TODO" in line:  # Inline comment: Example rule
        return "Found TODO, please resolve."
    return None  # No comment needed

# -----------------------------
# Post Inline Comments
# -----------------------------
async def post_comments():
    comments_posted = 0  # Counter for posted comments
    for i, line in enumerate(diff_lines):  # Iterate over each line in the diff
        review_comment = await analyze_line(line)  # Get AI review for line
        if review_comment:
            try:
                pr.create_review_comment(
                    body=review_comment,
                    commit_id=pr.head.sha,  # Comment against latest commit
                    path=PR_NUMBER,  # TODO: Replace with actual file path from diff
                    position=i + 1  # Line position in diff
                )
                comments_posted += 1  # Increment counter
            except GithubException as e:
                print(f"⚠️ Warning: Failed to post comment for line {i+1}: {e}")  # Error fallback

    if comments_posted == 0:
        print("ℹ️ No inline comments generated.")  # No comments to post
    else:
        print(f"✅ {comments_posted} inline comments posted.")  # Summary output

# -----------------------------
# Run Main Async Function
# -----------------------------
if __name__ == "__main__":
    asyncio.run(post_comments())  # Run the async posting function

