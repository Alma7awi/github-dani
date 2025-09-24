import os
import asyncio
import openai
from github import Github
from github.GithubException import GithubException

# -----------------------------
# Environment variable setup
# -----------------------------
# These are passed from GitHub Actions via the env: section
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")           # GitHub token for authentication
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY")       # Repository name in "owner/repo" format
PR_NUMBER = os.getenv("PR_NUMBER")                 # Pull Request number as string
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")  # Azure OpenAI endpoint URL
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")            # Azure OpenAI key

# Convert PR_NUMBER to integer safely
try:
    PR_NUMBER = int(PR_NUMBER)
except (TypeError, ValueError):
    PR_NUMBER = 0

# Check if all required environment variables are present
if not all([GITHUB_TOKEN, GITHUB_REPO, PR_NUMBER, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY]):
    print("❌ Missing required environment variables.")
    print(f"GITHUB_TOKEN: {'set' if GITHUB_TOKEN else 'missing'}")
    print(f"GITHUB_REPO: {'set' if GITHUB_REPO else 'missing'}")
    print(f"PR_NUMBER: {PR_NUMBER}")
    print(f"AZURE_OPENAI_ENDPOINT: {'set' if AZURE_OPENAI_ENDPOINT else 'missing'}")
    print(f"AZURE_OPENAI_KEY: {'set' if AZURE_OPENAI_KEY else 'missing'}")
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
    """
    1. Sends the diff to Azure OpenAI asynchronously.
    2. Posts the returned review comment to the GitHub PR.
    3. If posting fails, saves the comment locally.
    """
    # Configure OpenAI SDK for Azure
    openai.api_key = AZURE_OPENAI_KEY
    openai.api_base = AZURE_OPENAI_ENDPOINT
    openai.api_type = "azure"
    openai.api_version = "2023-07-01-preview"

    review_comment = ""
    try:
        # Send the diff to GPT-4 for review asynchronously
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[{"role": "user", "content": f"Please review this PR diff and provide comments:\n{diff_text}"}]
        )
        # Extract content from the response
        review_comment = response.choices[0].message.content
        print("✅ Review generated successfully.")
    except Exception as e:
        review_comment = f"❌ Failed to generate review: {e}"
        print(review_comment)

    # -----------------------------
    # Post the comment to GitHub PR
    # -----------------------------
    try:
        gh = Github(GITHUB_TOKEN)       # Authenticate with GitHub token
        repo = gh.get_repo(GITHUB_REPO) # Get repository
        pr = repo.get_pull(PR_NUMBER)   # Get pull request

        # Use create_review instead of create_review_comment to avoid commit_id issues
        pr.create_review(
            body=review_comment,
            event="COMMENT"  # Only comment, don't approve/request changes
        )
        print("✅ Comment posted to PR successfully.")
    except GithubException as ge:
        print(f"❌ Failed to post comment: {ge}")
        # Fallback: save review comment locally
        with open("review_comment.txt", "w") as f:
            f.write(review_comment)
        print("💾 Saved review comment to review_comment.txt")

# -----------------------------
# Run the async function
# -----------------------------
if __name__ == "__main__":
    asyncio.run(run_review())

