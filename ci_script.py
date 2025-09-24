import os
import asyncio
import openai
from github import Github
from github.GithubException import GithubException

# -----------------------------
# Environment variables
# -----------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY")
PR_NUMBER = int(os.getenv("PR_NUMBER", 0))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Exit if missing variables
if not all([GITHUB_TOKEN, GITHUB_REPO, PR_NUMBER, OPENAI_API_KEY]):
    print("❌ Missing required environment variables.")
    exit(1)

# -----------------------------
# Read diff file
# -----------------------------
try:
    with open("diff.txt", "r") as f:
        diff_text = f.read()
except FileNotFoundError:
    print("⚠️ diff.txt not found")
    diff_text = ""

if not diff_text.strip():
    print("⚠️ diff.txt empty")
    exit(0)

# -----------------------------
# Async function to get AI comments
# -----------------------------
async def run_review():
    openai.api_key = OPENAI_API_KEY
    comments = []

    try:
        # Ask AI to suggest inline comments
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[{
                "role": "user",
                "content": f"Review this PR diff and suggest inline comments in this format:\n<line_number>: <comment>\n{diff_text}"
            }]
        )
        # Parse AI response (assuming it gives: line_number: comment)
        review_text = response.choices[0].message.content
        for line in review_text.splitlines():
            if ":" in line:
                line_number, comment = line.split(":", 1)
                comments.append((int(line_number.strip()), comment.strip()))
        print("✅ AI comments generated")
    except Exception as e:
        print(f"❌ Failed to generate AI review: {e}")

    # -----------------------------
    # Post inline comments to PR
    # -----------------------------
    try:
        gh = Github(GITHUB_TOKEN)
        repo = gh.get_repo(GITHUB_REPO)
        pr = repo.get_pull(PR_NUMBER)
        for line_number, comment in comments:
            # Create comment on specific line of the PR diff
            # Note: You might need the actual commit_id and path for full inline comments
            pr.create_review_comment(
                body=comment,
                commit_id=pr.head.sha,
                path="path/to/file",  # You may need to extract file paths from diff
                line=line_number,
                side="RIGHT"
            )
        print("✅ Inline comments posted to PR")
    except GithubException as ge:
        print(f"❌ Failed to post PR comments: {ge}")
        # fallback
        with open("review_comment.txt", "w") as f:
            f.write(str(comments))
        print("💾 Saved comments locally")

if __name__ == "__main__":
    asyncio.run(run_review())
