#!/usr/bin/env python3
"""
ci_script.py
- Reads diff.txt
- Verifies OPENAI_API_KEY exists
- Calls OpenAI Chat Completion API
- Posts the review comment directly to the GitHub PR
"""

import os
import sys
from openai import OpenAI
from github import Github

def main():
    print("Hello from ci_script.py — Dani CI test")

    # -----------------------------
    # Check OpenAI API Key
    # -----------------------------
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        print("ERROR: OPENAI_API_KEY not found in environment. Exiting.")
        sys.exit(1)

    # -----------------------------
    # Read diff.txt
    # -----------------------------
    diff_file = "diff.txt"
    if not os.path.exists(diff_file):
        print(f"ERROR: {diff_file} not found. Exiting.")
        sys.exit(1)

    with open(diff_file, "r") as f:
        diff = f.read()

    if not diff.strip():
        print("No changes detected in diff.txt. Exiting.")
        sys.exit(0)

    # -----------------------------
    # Call OpenAI API
    # -----------------------------
    client = OpenAI(api_key=openai_key)

    try:
        resp = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "You are a senior software engineer reviewing code changes."},
                {"role": "user", "content": f"Please review this git diff and provide concise PR comments:\n\n{diff}"}
            ],
            max_tokens=500,
        )
        review_comment = resp.choices[0].message.content.strip()
        print("OpenAI response:\n", review_comment)

    except Exception as e:
        review_comment = f"⚠️ OpenAI request failed: {e}"
        print(review_comment)

    # -----------------------------
    # Post comment to GitHub PR
    # -----------------------------
    github_token = os.environ.get("GITHUB_TOKEN")
    pr_number = os.environ.get("PR_NUMBER")
    repo_name = os.environ.get("GITHUB_REPOSITORY")  # e.g., "owner/repo"

    if not github_token or not pr_number or not repo_name:
        print("ERROR: Missing GitHub environment variables. Cannot post PR comment.")
        sys.exit(1)

    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(int(pr_number))
    pr.create_issue_comment(review_comment)
    print(f"✅ Comment posted to PR #{pr_number}")

if __name__ == "__main__":
    main()

