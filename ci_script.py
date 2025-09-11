import os
import sys
import asyncio
from github import Github, Auth
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
PR_NUMBER = os.environ.get("PR_NUMBER")
REPO_NAME = os.environ.get("GITHUB_REPOSITORY")
DIFF_FILE = "diff.txt"

# Read diff
if os.path.exists(DIFF_FILE):
    with open(DIFF_FILE, "r") as f:
        diff_content = f.read()
else:
    diff_content = ""

if not diff_content.strip():
    review_comment = "No changes detected in diff."
else:
    review_comment = ""  # will be overwritten by OpenAI

async def get_openai_review(diff_text: str) -> str:
    try:
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default"
        )

        client = AsyncAzureOpenAI(
            azure_endpoint="https://alpheya-oai.qwlth.dev",
            api_version="2024-09-01-preview",
            azure_ad_token_provider=token_provider
        )

        resp = await client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": "You are a senior software engineer reviewing code changes."},
                {"role": "user", "content": f"Please review this git diff:\n\n{diff_text}"}
            ],
            temperature=0.7,
            max_tokens=700
        )

        comment_text = resp.choices[0].message.content.strip()
        if not comment_text:
            comment_text = "⚠️ OpenAI returned empty review. Diff as fallback:\n\n" + diff_text
        return comment_text

    except Exception as e:
        print("⚠️ OpenAI request failed:", e)
        return "⚠️ OpenAI could not generate review. Diff as fallback:\n\n" + diff_text

async def main():
    global review_comment
    if diff_content.strip():
        review_comment = await get_openai_review(diff_content)

    # Always write review_comment.txt
    with open("review_comment.txt", "w") as f:
        f.write(review_comment)
    print("✅ review_comment.txt written successfully")

    # Post comment to GitHub
    if PR_NUMBER and REPO_NAME:
        try:
            g = Github(auth=Auth.Token(GITHUB_TOKEN))
            repo = g.get_repo(REPO_NAME)
            pr = repo.get_pull(int(PR_NUMBER))
            pr.create_issue_comment(review_comment)
            print(f"✅ Comment posted to PR #{PR_NUMBER}")
        except Exception as e:
            print(f"⚠️ Failed to post comment: {e}")

if __name__ == "__main__":
    asyncio.run(main())
