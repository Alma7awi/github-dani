import os
import asyncio
import openai
from github import Github
from github.GithubException import GithubException

# -----------------------------
# Environment variable setup
# -----------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY")
PR_NUMBER = int(os.getenv("PR_NUMBER", 0))
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")

# Check required environment variables
if not all([GITHUB_TOKEN, GITHUB_REPO, PR_NUMBER, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY]):
    print("❌ Missing required environment variables.")
    exit(1)

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
# Async function to call Azure OpenAI
# -----------------------------
async def run_review():
    # Configure OpenAI to use Azure endpoint
    openai.api_key = AZURE_OPENAI_KEY
    openai.api_base = AZURE_OPENAI_ENDPOINT
    openai.api_type = "azure"
    openai.api_version = "2023-07-01-preview"

    review_comment = ""
    try:
        # Send the diff to Azure OpenAI asynchronously
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[{"role": "user", "content": f"Please review this PR diff and provide comments:\n{diff_text}"}]
        )
        review_comment = response.choices[0].message.content
        print("✅ Review generated successfully.")
    except Exception as e:
        review_comment = f"❌ Failed to generate review: {e}"
        print(review_comment)

    # -----------------------------
    # Post comment to GitHub PR
    # -----------------------------
    try:
        gh = Github(GITHUB_TOKEN)
        repo = gh.get_repo(GITHUB_REPO)
        pr = repo.get_pull(PR_NUMBER)

        # Use create_review to avoid commit_id issues
        pr.create_review(
            body=review_comment,
            event="COMMENT"
        )
        print("✅ Comment posted to PR successfully.")
    except GithubException as ge:
        print(f"❌ Failed to post comment: {ge}")
        # Fallback: save review locally
        with open("review_comment.txt", "w") as f:
            f.write(review_comment)
        print("💾 Saved review comment to review_comment.txt")

# Run async function
if __name__ == "__main__":
    asyncio.run(run_review())

