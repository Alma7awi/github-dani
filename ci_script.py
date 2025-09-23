import os
import sys
import json
import asyncio
import aiohttp
from azure.identity.aio import DefaultAzureCredential
from openai import AsyncAzureOpenAI

# -------------------------------
# Config & Environment Variables
# -------------------------------
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
PR_NUMBER = os.getenv("PR_NUMBER")
COMMIT_ID = os.getenv("GITHUB_SHA")
DIFF_FILE = "diff.patch"  # saved diff file in workflow

if not all([GITHUB_REPOSITORY, GITHUB_TOKEN, PR_NUMBER, COMMIT_ID]):
    print("❌ Missing required GitHub environment variables")
    sys.exit(1)

# -------------------------------
# Azure OpenAI Setup
# -------------------------------
client = AsyncAzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2024-02-15-preview",
    credential=DefaultAzureCredential()
)

MODEL = "gpt-4o-mini"

# -------------------------------
# Helper: Call OpenAI for review
# -------------------------------
async def get_review(diff_text: str):
    system_prompt = "You are a senior code reviewer."
    
    # 1. General PR Summary
    summary_prompt = f"""
Review the following pull request diff and provide a structured summary
with strengths, risks, and improvements. Be concise and constructive.

Diff:
{diff_text}
"""
    summary_resp = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": summary_prompt},
        ],
        max_tokens=800,
    )
    summary = summary_resp.choices[0].message.content.strip()

    # 2. Inline Comments (JSON format)
    inline_prompt = f"""
Review the following diff and suggest inline comments.
Output ONLY valid JSON in the format:

[
  {{ "file": "path/to/file", "line": line_number, "comment": "feedback here" }}
]

Diff:
{diff_text}
"""
    inline_resp = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a precise code reviewer."},
            {"role": "user", "content": inline_prompt},
        ],
        max_tokens=1200,
    )
    inline_text = inline_resp.choices[0].message.content.strip()

    try:
        inline_comments = json.loads(inline_text)
    except Exception:
        inline_comments = []
        print("⚠️ Failed to parse inline JSON, raw output:", inline_text)

    return summary, inline_comments

# -------------------------------
# Helper: Post comment to GitHub
# -------------------------------
async def post_summary_comment(session, summary: str):
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/issues/{PR_NUMBER}/comments"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    payload = {"body": summary}
    async with session.post(url, headers=headers, json=payload) as resp:
        if resp.status != 201:
            print("❌ Failed to post summary:", await resp.text())

async def post_inline_comment(session, comment: dict):
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/pulls/{PR_NUMBER}/comments"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    payload = {
        "body": comment["comment"],
        "commit_id": COMMIT_ID,
        "path": comment["file"],
        "line": comment["line"],
        "side": "RIGHT"
    }
    async with session.post(url, headers=headers, json=payload) as resp:
        if resp.status not in [201, 200]:
            print("❌ Failed inline comment:", await resp.text())

# -------------------------------
# Main Runner
# -------------------------------
async def main():
    if not os.path.exists(DIFF_FILE):
        print(f"❌ Diff file {DIFF_FILE} not found")
        sys.exit(1)

    with open(DIFF_FILE, "r") as f:
        diff_text = f.read()

    summary, inline_comments = await get_review(diff_text)

    async with aiohttp.ClientSession() as session:
        # Post summary comment
        await post_summary_comment(session, f"## 🤖 PR Review Bot\n\n{summary}")

        # Post inline comments
        for comment in inline_comments:
            await post_inline_comment(session, comment)

    print("✅ Review completed: summary + inline comments posted")

if __name__ == "__main__":
    asyncio.run(main())
