#!/usr/bin/env python3
import os
import sys
import asyncio
from github import Github
from github.GithubException import GithubException
from openai import AsyncAzureOpenAI

# ------------------------
# Environment Variables
# ------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
PR_NUMBER = os.getenv("PR_NUMBER")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL", "gpt-4")

if not all([GITHUB_TOKEN, GITHUB_REPOSITORY, PR_NUMBER, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY]):
    print("❌ ERROR: Missing required environment variables.")
    sys.exit(1)

# ------------------------
# GitHub Initialization
# ------------------------
gh = Github(GITHUB_TOKEN)
repo = gh.get_repo(GITHUB_REPOSITORY)
pr = repo.get_pull(int(PR_NUMBER))
commit_sha = pr.head.sha

# ------------------------
# Load diff
# ------------------------
diff_file = "diff.txt"
if not os.path.exists(diff_file):
    print(f"❌ ERROR: {diff_file} not found. Generate it with `git diff origin/main...HEAD > diff.txt`")
    sys.exit(1)

with open(diff_file, "r") as f:
    diff_text = f.read()

# ------------------------
# Generate review content using Azure OpenAI
# ------------------------
async def get_review(diff):
    client = AsyncAzureOpenAI(
        endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        model=AZURE_OPENAI_MODEL
    )

    prompt = f"Review the following code changes and provide comments per line:\n\n{diff}"

    response = await client.chat(prompt)
    return response.strip()

# ------------------------
# Helper to post inline comments
# ------------------------
def post_inline_comments(review_comments):
    """
    review_comments: dict where keys are file paths and values are list of tuples
    (position_in_diff, comment_text)
    """
    for file_path, comments in review_comments.items():
        for position, body in comments:
            try:
                pr.create_review_comment(
                    body=body,
                    commit_id=commit_sha,
                    path=file_path,
                    position=position
                )
                print(f"✅ Comment posted on {file_path} at diff position {position}")
            except GithubException as e:
                print(f"❌ Failed to post comment on {file_path}: {e}")

# ------------------------
# Main
# ------------------------
async def main():
    # For simplicity, we assume Azure gives a dict: {"file_path": [(position, comment), ...]}
    # In practice, you can parse Azure's response to generate this mapping
    review_text = await get_review(diff_text)

    # Example: split by lines like: "file.py:10:Comment text"
    review_comments = {}
    for line in review_text.split("\n"):
        if ":" in line:
            parts = line.split(":", 2)
            if len(parts) == 3:
                file_path, position_str, comment = parts
                position = int(position_str)
                review_comments.setdefault(file_path.strip(), []).append((position, comment.strip()))

    post_inline_comments(review_comments)

    # Fallback: save review if GitHub fails
    with open("review_comment.txt", "w") as f:
        f.write(review_text)

if __name__ == "__main__":
    asyncio.run(main())

