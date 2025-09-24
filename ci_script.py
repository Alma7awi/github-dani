import os
import asyncio
from github import Github
from github.GithubException import GithubException
from azure.identity.aio import DefaultAzureCredential  # Async Azure credential
from azure.ai.openai.aio import OpenAIClient             # Async Azure OpenAI client

# -----------------------------
# Environment variable setup
# -----------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # GitHub token for authentication
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY")  # Repository name "owner/repo"
PR_NUMBER = int(os.getenv("PR_NUMBER", 0))  # Pull Request number

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")  # Azure OpenAI endpoint
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")  # Azure OpenAI key

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
    # Use DefaultAzureCredential for async auth
    credential = DefaultAzureCredential()
    client = OpenAIClient(endpoint=AZURE_OPENAI_ENDPOINT, credential=credential)

    review_comment = ""
    try:
        # Send the diff to Azure OpenAI asynchronously
        response = await client.chat_completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": f"Please review this PR diff and provide comments:\n{diff_text}"}]
        )
        # Extract review comment from response
        review_comment = response.choices[0].message.content
        print("✅ Review generated successfully.")
    except Exception as e:
        review_comment = f"❌ Failed to generate review: {e}"
        print(review_comment)
    finally:
        # Close Azure credential session
        await credential.close()

    # -----------------------------
    # Post comment to GitHub PR
    # -----------------------------
    try:
        gh = Github(GITHUB_TOKEN)  # Authenticate to GitHub
        repo = gh.get_repo(GITHUB_REPO)
        pr = repo.get_pull(PR_NUMBER)

        # Use create_review (not create_review_comment) to avoid commit_id errors
        pr.create_review(
            body=review_comment,
            event="COMMENT"  # Only comment, do not approve/request changes
        )
        print("✅ Comment posted to PR successfully.")
    except GithubException as ge:
        print(f"❌ Failed to post comment: {ge}")
        # Fallback: save review locally
        fallback_file = "review_comment.txt"
        with open(fallback_file, "w") as f:
            f.write(review_comment)
        print(f"💾 Saved review comment to {fallback_file}")

# -----------------------------
# Run async function
# -----------------------------
if __name__ == "__main__":
    asyncio.run(run_review())

