#!/usr/bin/env python3
import os
import asyncio
from github import Github, Auth
from openai import AsyncOpenAI

# -----------------------------
# Config
# -----------------------------
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY")
PR_NUMBER = int(os.environ.get("PR_NUMBER", 1))
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")

if not all([GITHUB_TOKEN, GITHUB_REPOSITORY, OPENAI_KEY]):
    raise EnvironmentError("Please set GITHUB_TOKEN, GITHUB_REPOSITORY, and OPENAI_API_KEY")

# -----------------------------
# GitHub setup
# -----------------------------
gh = Github(auth=Auth.Token(GITHUB_TOKEN))
repo = gh.get_repo(GITHUB_REPOSITORY)
pr = repo.get_pull(PR_NUMBER)

# -----------------------------
# OpenAI setup
# -----------------------------
client = AsyncOpenAI(api_key=OPENAI_KEY)

# -----------------------------
# Helper: generate review comment per line
# -----------------------------
async def generate_line_comment(line_text: str) -> str:
    SYSTEM_PROMPT = """
You are a senior software engineer reviewing code changes.
Focus on readability, bugs, best practices, security, and improvements.
Provide a concise comment for this single line of code.
"""
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Review this line:\n{line_text}"}
        ],
        temperature=0.7
    )
    return resp.choices[0].message.content.strip()

# -----------------------------
# Helper: extract lines to comment from diff
# -----------------------------
def parse_diff(diff_text: str):
    """
    Parses a Git diff and returns a list of (file_path, diff_position, line_text)
    suitable for GitHub inline comments.
    """
    comments = []
    current_file = None
    diff_position = 0

    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            current_file = None
            diff_position = 0
        elif line.startswith("+++ b/"):
            current_file = line[6:]  # filepath after "+++ b/"
            diff_position = 0
        elif current_file and (line.startswith("+") and not line.startswith("+++")):
            diff_position += 1
            comments.append((current_file, diff_position, line[1:].strip()))
        elif current_file and (not line.startswith("-")):
            diff_position += 1

    return comments

# -----------------------------
# Main async function
# -----------------------------
async def main():
    # Make sure diff.txt exists
    if not os.path.exists("diff.txt") or os.path.getsize("diff.txt") == 0:
        print("⚠️ diff.txt not found or empty. Skipping review.")
        return

    with open("diff.txt") as f:
        diff_text = f.read()

    lines_to_comment = parse_diff(diff_text)

    for file_path, diff_position, line_text in lines_to_comment:
        comment_text = await generate_line_comment(line_text)
        try:
            pr.create_review_comment(
                body=comment_text,
                commit_id=pr.head.sha,
                path=file_path,
                position=diff_position
            )
            print(f"✅ Comment posted on {file_path} at position {diff_position}")
        except Exception as e:
            print(f"❌ Failed to post comment on {file_path} at position {diff_position}: {e}")
            with open("review_comment.txt", "a") as f:
                f.write(f"{file_path} [{diff_position}]: {comment_text}\n")

# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    asyncio.run(main())

