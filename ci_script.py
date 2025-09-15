import os
import sys
import asyncio
from openai import AsyncAzureOpenAI
from github import Github, Auth

# Env vars
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
PR_NUMBER = os.environ.get("PR_NUMBER")
REPO_NAME = os.environ.get("GITHUB_REPOSITORY")
AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY")
DIFF_FILE = "diff.txt"

if not GITHUB_TOKEN or not AZURE_OPENAI_KEY:
    print("❌ ERROR: Required environment variables are not set.")
    sys.exit(1)

# Read diff
diff_content = "No changes detected."
if os.path.exists(DIFF_FILE):
    with open(DIFF_FILE, "r") as f:
        diff_content = f.read().strip() or diff_content

# OpenAI call
async def get_openai_review(diff_text: str) -> str:
    try:
        client = AsyncAzureOpenAI(
            azure_endpoint="https://alpheya-oai.qwlth.dev",
            api_version="2024-09-01-preview",
            api_key=AZURE_OPENAI_KEY
        )

        resp = await client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": "You are a senior software engineer reviewing code changes."},
                {"role": "user", "content": f"Please review this git diff and provide concise PR comments:\n\n{diff_text}"}
            ],
            temperature=0.7,
            max_tokens=700,
        )

        return resp.choices[0].message.content.strip() or "⚠️ OpenAI returned an empty review."

    except Exception as e:
        print("⚠️ OpenAI request failed:", e)
        return f"⚠️ OpenAI could not generate review. Diff as fallback:\n\n{diff_text}"

# Main
async def main():
    review_comment = await get_openai_review(diff_content)
    try:
        g = Github(auth=Auth.Token(GITHUB_TOKEN))
        repo = g.get_repo(REPO_NAME)
        pr = repo.get_pull(int(PR_NUMBER))
        pr.create_issue_comment(review_comment)
        print(f"✅ Comment posted to PR #{PR_NUMBER}")
    except Exception as e:
        print(f"❌ Failed to post comment: {e}")
        with open("review_comment.txt", "w") as f:
            f.write(review_comment)
        print("💾 Saved review_comment.txt instead")

if __name__ == "__main__":
    asyncio.run(main())

