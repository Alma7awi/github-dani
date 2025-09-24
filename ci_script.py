import os
import asyncio
from github import Github, Auth
from github.GithubException import GithubException
from openai import AsyncOpenAI

# -----------------------------
# Environment variable setup
# -----------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY")
PR_NUMBER = int(os.getenv("PR_NUMBER", 0))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

# Validate env vars
if not all([GITHUB_TOKEN, GITHUB_REPO, PR_NUMBER, OPENAI_API_KEY]):
    print("❌ Missing required environment variables.")
    exit(1)

# Create OpenAI async client
client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)

# -----------------------------
# Read diff file
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
# Async review function
# -----------------------------
async def run_review():
    review_comment = ""
    try:
        # Ask AI to review code diff
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
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
        gh = Github(auth=Auth.Token(GITHUB_TOKEN))  # modern way, no deprecation
        repo = gh.get_repo(GITHUB_REPO)
        pr = repo.get_pull(PR_NUMBER)

        pr.create_review(
            body=review_comment,
            event="COMMENT"
        )
        print(f"✅ Comment posted to PR #{PR_NUMBER} successfully.")
    except GithubException as ge:
        print(f"❌ Failed to post comment: {ge}")
        with open("review_comment.txt", "w") as f:
            f.write(review_comment)
        print("💾 Saved review_comment.txt instead.")

# -----------------------------
# Run async function
# -----------------------------
if __name__ == "__main__":
    asyncio.run(run_review())

