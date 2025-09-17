import os
import asyncio
from github import Github
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.ai.openai.aio import AsyncAzureOpenAI

# -----------------------------
# GitHub setup
# -----------------------------
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY")  # e.g., 'username/repo'
PR_NUMBER = int(os.environ.get("PR_NUMBER", 1))    # default PR number = 1

if not GITHUB_TOKEN:
    raise EnvironmentError("GITHUB_TOKEN not set")

gh = Github(GITHUB_TOKEN)
repo = gh.get_repo(GITHUB_REPO)
pr = repo.get_pull(PR_NUMBER)

# -----------------------------
# Azure OpenAI setup
# -----------------------------
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default"
)

client = AsyncAzureOpenAI(
    azure_endpoint="https://alpheya-oai.qwlth.dev",
    api_version="2024-09-01-preview",
    azure_ad_token_provider=token_provider,
)

# -----------------------------
# Read diff
# -----------------------------
if not os.path.exists("diff.txt") or os.path.getsize("diff.txt") == 0:
    print("⚠️ diff.txt not found or empty. Skipping OpenAI review.")
    review_comment = "No diff found."
else:
    with open("diff.txt", "r") as f:
        diff = f.read()

# -----------------------------
# Generate review using Azure OpenAI
# -----------------------------
async def get_review():
    if os.path.exists("diff.txt") and os.path.getsize("diff.txt") > 0:
        res = await client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                 {"role": "system", "content": "You are a helpful, friendly software engineer providing detailed and constructive code review comments."},
                 {"role": "user", "content": f"Please review this git diff and provide concise PR comments:\n\n{diff}"}
                ]

            ],
            temperature=0.7
        )
        return res.choices[0].message.content.strip()
    return "No diff to review."

# -----------------------------
# Post comment to GitHub PR
# -----------------------------
async def main():
    review_comment = await get_review()
    try:
        pr.create_issue_comment(review_comment)
        print("✅ Comment posted successfully")
    except Exception as e:
        print("❌ Failed to post comment:", e)
        with open("review_comment.txt", "w") as f:
            f.write(review_comment)
        print("💾 Saved review_comment.txt instead")

if __name__ == "__main__":
    asyncio.run(main())


