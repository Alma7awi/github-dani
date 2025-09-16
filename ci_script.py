import os
import sys
import asyncio
from github import Github, Auth
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI

# -----------------------------
# Environment variables
# -----------------------------
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
PR_NUMBER = os.environ.get("PR_NUMBER")
REPO_NAME = os.environ.get("GITHUB_REPOSITORY")
DIFF_FILE = "diff.txt"

# Check required env vars
missing_vars = [v for v in ["GITHUB_TOKEN", "PR_NUMBER", "GITHUB_REPOSITORY"] if not os.environ.get(v)]
if missing_vars:
    print(f"❌ ERROR: Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

# -----------------------------
# Read git diff
# -----------------------------
diff_content = "No changes detected."
if os.path.exists(DIFF_FILE):
    with open(DIFF_FILE, "r") as f:
        diff_content = f.read().strip() or diff_content

# -----------------------------
# Get Azure AD token provider
# -----------------------------
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default"
)

# -----------------------------
# Call Azure OpenAI
# -----------------------------
async def get_openai_review(diff_text: str) -> str:
    try:
        client = AsyncAzureOpenAI(
            azure_endpoint="https://alpheya-oai.qwlth.dev",
            api_version="2024-09-01-preview",
            azure_ad_token_provider=token_provider,
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

# -----------------------------
# Post review to PR
# -----------------------------
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

