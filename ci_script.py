import os
import asyncio
import openai
from github import Github, Auth
from github.GithubException import GithubException

# -----------------------------
# Environment variable setup
# -----------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")           # GitHub token
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY")       # e.g., "owner/repo"
PR_NUMBER = os.getenv("PR_NUMBER")                 # PR number
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")       # OpenAI API key

# Convert PR_NUMBER to integer
try:
    PR_NUMBER = int(PR_NUMBER)
except (TypeError, ValueError):
    PR_NUMBER = 0

# Check required environment variables
if not all([GITHUB_TOKEN, GITHUB_REPO, PR_NUMBER, OPENAI_API_KEY]):
    print("❌ Missing required environment variables.")
    exit(1)

# -----------------------------
# Read diff.txt
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
# Function to get AI review (sync inside async)
# -----------------------------
async def get_ai_review(diff_text: str) -> str:
    """
    Sends the diff to OpenAI synchronously in a separate thread to avoid blocking.
    Returns the AI review text.
    """
    openai.api_key = OPENAI_API_KEY
    try:
        response = await asyncio.to_thread(
            openai.ChatCompletion.create,  # sync method
            model="gpt-4",
            messages=[
                {
                    "role": "user",
                    "content": f"Review this PR diff and suggest inline comments in this format:\n<file_path>:<line_number>:<comment>\n{diff_text}"
                }
            ]
        )
        review_text = response.choices[0].message.content
        print("✅ AI review generated successfully.")
        return review_text
    except Exception as e:
        print(f"❌ Failed to generate AI review: {e}")
        return ""

# -----------------------------
# Async function to post PR comments
# -----------------------------
async def run_review():
    ai_comments = []

    # Get AI review text
    review_text = await get_ai_review(diff_text)

    # Parse AI response into (file_path, line_number, comment)
    for line in review_text.splitlines():
        if line.strip() and line.count(":") >= 2:
            parts = line.split(":", 2)
            file_path = parts[0].strip()
            try:
                line_number = int(parts[1].strip())
                comment = parts[2].strip()
                ai_comments.append((file_path, line_number, comment))
            except ValueError:
                continue  # Skip invalid lines

    # Post comments to GitHub PR
    try:
        gh = Github(auth=Auth.Token(GITHUB_TOKEN))  # Correct auth
        repo = gh.get_repo(GITHUB_REPO)
        pr = repo.get_pull(PR_NUMBER)

        for file_path, line_number, comment in ai_comments:
            # Post inline comment on PR diff
            pr.create_review_comment(
                body=comment,
                commit_id=pr.head.sha,
                path=file_path,
                line=line_number,
                side="RIGHT"  # Comment on the changed line
            )

        print("✅ Inline comments posted to PR successfully.")

    except GithubException as ge:
        print(f"❌ Failed to post PR comments: {ge}")
        # Fallback: save comments locally
        with open("review_comment.txt", "w") as f:
            for file_path, line_number, comment in ai_comments:
                f.write(f"{file_path}:{line_number}:{comment}\n")
        print("💾 Saved comments locally to review_comment.txt")

# -----------------------------
# Run async review
# -----------------------------
if __name__ == "__main__":
    asyncio.run(run_review())
