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
    diff = ""
else:
    with open("diff.txt", "r") as f:
        diff = f.read()

# -----------------------------
# System prompt
# -----------------------------
SYSTEM_PROMPT = """
You are a senior software engineer reviewing code changes in a pull request.
Focus on:
1. Code readability and style
2. Possible bugs or errors
3. Best practices
4. Security considerations
5. Suggestions for improvement

Provide concise, actionable comments in bullet points.
"""

# -----------------------------
# Generate review using Azure OpenAI
# -----------------------------
async def get_review():
    if not diff:
        return "No diff to review."

    resp = await client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Please review this git diff and provide concise PR comments:\n\n{diff}"}
        ],
        temperature=0.7
    )

    # Get the response text
    return resp.choices[0].message["content"].strip()

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



