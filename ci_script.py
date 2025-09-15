import os
import sys
import asyncio
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI
from github import Github, Auth

# -----------------------------
# Environment variables
# -----------------------------
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
PR_NUMBER = os.environ.get("PR_NUMBER")
REPO_NAME = os.environ.get("GITHUB_REPOSITORY")  # e.g., owner/repo
DIFF_FILE = "diff.txt"

if not GITHUB_TOKEN:
    print("ERROR: GITHUB_TOKEN not set.")
    sys.exit(1)

# -----------------------------
# Read the diff
# -----------------------------
if not os.path.exists(DIFF_FILE):
    print(f"⚠️ {DIFF_FILE} not found. Skipping OpenAI review.")
    diff_content = ""
else:
    with open(DIFF_FILE, "r") as f:
        diff_content = f.read()

if not diff_content.strip():
    diff_content = "No changes detected."

# -----------------------------
# Azure OpenAI call
# -----------------------------
async def get_openai_review(diff_text: str) -> str:
    try:
        # Get AAD token provider
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default"
        )

        # Create Azure OpenAI client
        client = AsyncAzureOpenAI(
            azure_endpoint="https://alpheya-oai.qwlth.dev",
            api_version="2024-09-01-preview",
            azure_ad_token_provider=token_provider,
        )

        # Call the model
        resp = await client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": "You are a senior software engineer reviewing code changes."},
                {"role": "user", "content": f"Please review this git diff and provide concise PR comments:\n\n{diff_text}"}
            ],
            temperature=0.7,
            max_tokens=700,
        )

        comment_text = resp.choices[0].message.content.strip()
        return comment_text or "⚠️ OpenAI returned an empty review."

    except Exception as e:
        print("⚠️ OpenAI request failed:", e)
        return f"⚠️ OpenAI could not generate review. Diff as fallback:\n\n{diff_text}"

# -----------------------------
# Main async function
# -----------------------------
async def main():
    review_comment = await get_openai_review(diff_content)

    # Write comment to file (debugging/fallback)
    with open("review_comment.txt", "w") as f:
        f.write(review_comment)
    print("✅ review_comment.txt written successfully")

    # Post comment to PR
    if not PR_NUMBER or not REPO_NAME:
        print("INFO: PR number or repo not set. Skipping PR comment (likely a forked PR).")
        return

    try:
        g = Github(auth=Auth.Token(GITHUB_TOKEN))
        repo = g.get_repo(REPO_NAME)
        pr = repo.get_pull(int(PR_NUMBER))
        pr.create_issue_comment(review_comment)
        print(f"✅ Comment posted to PR #{PR_NUMBER}")
    except Exception as e:
        print(f"⚠️ Failed to post comment to GitHub PR: {e}")

if __name__ == "__main__":
    asyncio.run(main())

