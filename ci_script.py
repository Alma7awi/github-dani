#!/usr/bin/env python3
"""
ci_script.py
Refactored script to:
- Generate diff for the PR
- Send diff to Azure OpenAI for review
- Post inline comments to the PR
- Fallback to review_comment.txt if posting fails
"""

import os
import asyncio
from github import Github, GithubException

try:
    from azure.identity.aio import DefaultAzureCredential
    from azure.ai.openai.aio import OpenAIClient
except ImportError:
    raise ImportError("Required packages missing. Run: pip install azure-identity azure-ai-openai PyGithub")

# ------------------ ENVIRONMENT VARIABLES ------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
PR_NUMBER = os.getenv("PR_NUMBER")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL", "gpt-4")
if not all([GITHUB_TOKEN, GITHUB_REPOSITORY, PR_NUMBER, AZURE_OPENAI_ENDPOINT]):
    raise SystemExit("❌ Missing one or more required environment variables.")

# ------------------ HELPER FUNCTIONS ------------------
async def get_openai_review(diff_text: str) -> str:
    """Send diff to Azure OpenAI and get review comments."""
    credential = DefaultAzureCredential()
    client = OpenAIClient(endpoint=AZURE_OPENAI_ENDPOINT, credential=credential)
    prompt = f"Review this PR diff and provide line-by-line feedback:\n{diff_text}"
    
    try:
        response = await client.chat_completions.create(
            deployment_id=AZURE_OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        review_text = response.choices[0].message.content
        return review_text
    except Exception as e:
        return f"❌ OpenAI review failed: {e}"
    finally:
        await client.close()
        await credential.close()

def parse_diff(diff_path="diff.txt"):
    """Read diff file and map lines for inline commenting."""
    if not os.path.exists(diff_path):
        print("⚠️ Diff file not found, creating an empty one.")
        return {}
    
    inline_map = {}  # {file_path: [(line_number, line_text), ...]}
    current_file = None
    line_number = 0
    
    with open(diff_path, "r") as f:
        for line in f:
            if line.startswith("+++ b/"):
                current_file = line.strip().split(" ")[1][2:]
                inline_map[current_file] = []
                line_number = 0
            elif current_file:
                if line.startswith("+") and not line.startswith("+++"):
                    line_number += 1
                    inline_map[current_file].append((line_number, line[1:]))
                elif not line.startswith("-"):
                    line_number += 1
    return inline_map

async def post_inline_comments(github_token, repo_name, pr_number, review_text, inline_map):
    """Post comments to GitHub PR inline if possible."""
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(int(pr_number))

    try:
        for file_path, lines in inline_map.items():
            for line_number, code_line in lines:
                comment_body = f"💡 Suggested review: {review_text[:200]}..."  # Truncate if needed
                pr.create_review_comment(
                    body=comment_body,
                    commit_id=pr.head.sha,
                    path=file_path,
                    position=line_number
                )
        print(f"✅ Inline comments posted to PR #{pr_number}")
    except GithubException as e:
        # Fallback to saving to file
        print(f"⚠️ Failed to post inline comments: {e}")
        with open("review_comment.txt", "w") as f:
            f.write(review_text)
        print("💾 Review saved to review_comment.txt")

# ------------------ MAIN ------------------
async def main():
    print("🔹 Reading diff...")
    inline_map = parse_diff()
    if not inline_map:
        print("⚠️ No diff content found.")
        return

    with open("diff.txt", "r") as f:
        diff_text = f.read()

    print("🔹 Sending diff to Azure OpenAI...")
    review_text = await get_openai_review(diff_text)

    print("🔹 Posting inline comments to PR...")
    await asyncio.to_thread(post_inline_comments, GITHUB_TOKEN, GITHUB_REPOSITORY, PR_NUMBER, review_text, inline_map)

if __name__ == "__main__":
    asyncio.run(main())


