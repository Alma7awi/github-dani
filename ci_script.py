import os
import asyncio
import openai
from github import Github
from github.GithubException import GithubException

# -----------------------------
# Environment variable setup
# -----------------------------
# GitHub-related variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY")
PR_NUMBER = int(os.getenv("PR_NUMBER", 0))

# OpenAI Proxy credentials (safe from GitHub secrets)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

# Validate required environment variables
if not all([GITHUB_TOKEN, GITHUB_REPO, PR_NUMBER, OPENAI_API_KEY]):
    print("❌ Missing required environment variables.")
    print(f"GITHUB_TOKEN: {'set' if GITHUB_TOKEN else 'missing'}")
    print(f"GITHUB_REPO: {GITHUB_REPO or 'missing'}")
    print(f"PR_NUMBER: {PR_NUMBER or 'missing'}")
    print(f"OPENAI_API_KEY: {'set' if OPENAI_API_KEY else 'missing'}")
    print(f"OPENAI_API_BASE: {OPENAI_API_BASE}")
    exit(1)

# Configure OpenAI client
openai.api_key = OPENAI_API_KEY
openai.api_base = OPENAI_API_BASE

# -----------------------------
# Read the diff file
# -----------------------------
try:
    with open("diff.txt", "r") as f:
        diff_text = f.read()
except FileNotFoundError:
    print("⚠️ diff.txt not found, skipping review.")
    diff_text = ""

if not diff_text.strip():
    print("⚠️ diff.txt is empty, nothing to review.")
    exit(0)

# -----------------------------
# Async function for AI review
# -----------------------------
async def run_review():
    review_comment = ""
    try:
        # Ask the AI to review the diff
        response = await openai.chat.completions.acreate(
            model="gpt-4o-mini",  # lightweight & cost-efficient model
            messages=[
                {"role": "system", "content": "You are a code review assistant."},
                {"role": "user", "content": f"Review this Git diff and suggest improvements:\n{diff_text}"}
            ],
            temperature=0.3,
            max_tokens=500
        )
        review_comment = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ OpenAI request failed: {e}")
        review_comment = f"❌ Failed to generate AI review: {e}"

    # -----------------------------
    # Post comment to GitHub PR
    # -----------------------------
    try:
        gh = Github(auth=None, login_or_token=GITHUB_TOKEN)  # GitHub client
        repo = gh.get_repo(GITHUB_REPO)
        pr = repo.get_pull(PR_NUMBER)

        # Post as a PR review comment
        pr.create_review(
            body=review_comment,
            event="COMMENT"  # Just a neutral comment
        )
        print(f"✅ Comment posted to PR #{PR_NUMBER} successfully.")
    except GithubException as ge:
        print(f"❌ Failed to post comment: {ge}")
        # Fallback: save locally
        with open("review_comment.txt", "w") as f:
            f.write(review_comment)
        print("💾 Saved review_comment.txt instead.")

# -----------------------------
# Run async function
# -----------------------------
if __name__ == "__main__":
    asyncio.run(run_review())


