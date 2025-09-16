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
REPO_NAME = os.environ.get("GITHUB_REPOSITORY")
DIFF_FILE = "diff.txt"

# Check required env vars
missing_vars = [v for v in ["GITHUB_TOKEN", "PR_NUMBER", "GITHUB_REPOSITORY"] if not os.environ.get(v)]
if missing_vars:
    print(f"❌ ERROR: Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

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

