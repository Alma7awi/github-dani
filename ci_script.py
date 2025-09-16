import os
from github import Github
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI
import asyncio

# GitHub environment variables
github_token = os.getenv("GITHUB_TOKEN")
repo_name = os.getenv("GITHUB_REPOSITORY")
pr_number = os.getenv("GITHUB_PR_NUMBER")

if not all([github_token, repo_name, pr_number]):
    raise ValueError("❌ Missing one or more required GitHub environment variables.")

# Read diff
with open("diff.txt", "r") as f:
    diff_content = f.read().strip()

if not diff_content:
    print("⚠️ No diff changes found, skipping.")
    exit(0)

# ---- Azure OpenAI client (using AAD token provider) ----
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), 
    "https://cognitiveservices.azure.com/.default"
)

client = AsyncAzureOpenAI(
    azure_endpoint="https://alpheya-oai.qwlth.dev",
    api_version="2024-09-01-preview",
    azure_ad_token_provider=token_provider,
)

async def main():
    # Call Azure OpenAI for review
    response = await client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": "You are a helpful code review assistant."},
            {"role": "user", "content": f"Please review this git diff:\n\n{diff_content}"}
        ],
        temperature=0.7,
    )

    comment_body = response.choices[0].message.content.strip()

    # Post to GitHub PR
    gh = Github(github_token)
    repo = gh.get_repo(repo_name)
    pr = repo.get_pull(int(pr_number))
    pr.create_issue_comment(comment_body)

    print("✅ Review comment posted on PR")

if __name__ == "__main__":
    asyncio.run(main())

