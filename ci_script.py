#!/usr/bin/env python3
import os
import asyncio
from github import Github, Auth
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.ai.openai.aio import AsyncAzureOpenAI

# -----------------------------
# Config / Environment
# -----------------------------
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY")
PR_NUMBER = int(os.environ.get("PR_NUMBER", 1))

if not all([GITHUB_TOKEN, GITHUB_REPO]):
    raise EnvironmentError("GITHUB_TOKEN and GITHUB_REPOSITORY must be set")

# -----------------------------
# GitHub Setup
# -----------------------------
gh = Github(auth=Auth.Token(GITHUB_TOKEN))
repo = gh.get_repo(GITHUB_REPO)
pr = repo.get_pull(PR_NUMBER)

# -----------------------------
# Azure OpenAI Setup
# -----------------------------
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default"
)

client = AsyncAzureOpenAI(
    azure_endpoint="https://your-azure-endpoint",
    api_version="2024-09-01-preview",
    azure_ad_token_provider=token_provider,
)

# -----------------------------
# Helper: Generate review comment for a line
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
# Main: Post inline comments
# -----------------------------
async def main():
    files = pr.get_files()
    for file in files:
        if not file.patch:
            continue

        lines = file.patch.split("\n")
        for idx, line in enumerate(lines):
            # Example: flag risky terms
            if any(term in line for term in ["netFlow[0]", "startBalance"]):
                comment_text = await generate_line_comment(line)
                try:
                    pr.create_review_comment(
                        body=comment_text,
                        commit_id=pr.head.sha,
                        path=file.filename,
                        position=idx + 1,  # GitHub diff position
                    )
                    print(f"✅ Comment posted: {file.filename} line {idx+1}")
                except Exception as e:
                    print(f"❌ Failed to post comment: {e}")
                    with open("review_comment.txt", "a") as f:
                        f.write(f"{file.filename} line {idx+1}: {comment_text}\n")

if __name__ == "__main__":
    asyncio.run(main())

