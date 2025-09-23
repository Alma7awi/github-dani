#!/usr/bin/env python3
import os
import asyncio
from github import Github, GithubException
from pathlib import Path

# Optional: Azure OpenAI client
# from azure.identity import DefaultAzureCredential
# from azure.ai.openai import AsyncOpenAIClient

# -----------------------------
# Environment Variables
# -----------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
PR_NUMBER = int(os.getenv("PR_NUMBER", 0))
DIFF_FILE = "diff.txt"

if not GITHUB_TOKEN:
    print("❌ ERROR: GITHUB_TOKEN not set.")
    exit(1)
if not GITHUB_REPOSITORY:
    print("❌ ERROR: GITHUB_REPOSITORY not set.")
    exit(1)
if PR_NUMBER == 0:
    print("❌ ERROR: PR_NUMBER not set.")
    exit(1)
if not Path(DIFF_FILE).exists():
    print(f"❌ ERROR: {DIFF_FILE} not found.")
    exit(1)

# -----------------------------
# GitHub Client
# -----------------------------
gh = Github(GITHUB_TOKEN)
repo = gh.get_repo(GITHUB_REPOSITORY)
pr = repo.get_pull(PR_NUMBER)

# -----------------------------
# Load diff
# -----------------------------
with open(DIFF_FILE, "r") as f:
    diff_lines = f.readlines()

# -----------------------------
# Mock/Placeholder for AI Review
# -----------------------------
# Replace this with your async Azure OpenAI call
async def analyze_line(line):
    # Here you can call AsyncAzureOpenAI or any AI client
    # For now, we just flag lines containing 'TODO' as example
    if "TODO" in line:
        return "Found TODO, please resolve."
    return None

# -----------------------------
# Post inline comments
# -----------------------------
async def post_comments():
    comments_posted = 0
    for i, line in enumerate(diff_lines):
        review_comment = await analyze_line(line)
        if review_comment:
            try:
                # line + 1 because GitHub API uses 1-based indexing for positions
                pr.create_review_comment(
                    body=review_comment,
                    commit_id=pr.head.sha,
                    path=PR_NUMBER,  # or you can parse actual file path from diff
                    position=i + 1
                )
                comments_posted += 1
            except GithubException as e:
                print(f"⚠️ Warning: Failed to post comment for line {i+1}: {e}")

    if comments_posted == 0:
        print("ℹ️ No inline comments generated.")
    else:
        print(f"✅ {comments_posted} inline comments posted.")

# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    asyncio.run(post_comments())

