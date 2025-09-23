import os
import asyncio
from github import Github
from github.GithubException import GithubException
from azure.identity.aio import DefaultAzureCredential  # Async Azure credential
from azure.ai.openai.aio import OpenAIClient            # Async Azure OpenAI client

# -----------------------------
# Environment variable setup
# -----------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # GitHub token to post PR comments
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY")  # e.g., "owner/repo"
PR_NUMBER = int(os.getenv("PR_NUMBER", 0))  # Pull Request number

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")  # Azure OpenAI endpoint
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")  # Azure OpenAI key

# Check required environment variables
if not all([GITHUB_TOKEN, GITHUB_REPO, PR_NUMBER, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY]):
    print("❌ Missing required environment variables.")
    exit(1)

# -----------------------------
# Read the diff
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
    # Create async OpenAI client
    client = OpenAIClient(endpoint=AZURE_OPENAI_ENDPOINT, credential=DefaultAzureCredential())
    
    try:
        # Example: sending diff to Azure OpenAI
        response = await client.chat_completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": f"Review this diff:\n{diff_text}"}]
        )
        review_comment = response.choices[0].message.content
    except Exception as e:
        review_comment = f"❌ Failed to generate review: {e}"

    # -----------------------------
    # Post comment to PR
    # -----------------------------
    try:
        gh = Github(GITHUB_TOKEN)  # Auth with token
        repo = gh.get_repo(GITHUB_REPO)
        pr = repo.get_pull(PR_NUMBER)

        # Use `create_review` instead of `create_review_comment` to fix commit_id error
        pr.create_review(
            body=review_comment,
            event="COMMENT"  # Just a comment, not approve/request changes
        )
        print("✅ Comment posted to PR successfully.")

    except GithubException as ge:
        print(f"❌ Failed to post comment: {ge}")
        # Fallback: save comment locally
        with open("review_comment.txt", "w") as f:
            f.write(review_comment)
        print("💾 Saved review comment to review_comment.txt")

# -----------------------------
# Run the async function
# -----------------------------
asyncio.run(run_review())

