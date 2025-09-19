import os
import asyncio
from github import Github, Auth
from openai import AsyncOpenAI

# -----------------------------
# Config
# -----------------------------
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY")
PR_NUMBER = int(os.environ.get("PR_NUMBER", 1))
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")

if not all([GITHUB_TOKEN, GITHUB_REPO, OPENAI_KEY]):
    raise EnvironmentError("Please set GITHUB_TOKEN, GITHUB_REPOSITORY, and OPENAI_API_KEY")

# -----------------------------
# GitHub setup
# -----------------------------
gh = Github(auth=Auth.Token(GITHUB_TOKEN))
repo = gh.get_repo(GITHUB_REPO)
pr = repo.get_pull(PR_NUMBER)

# -----------------------------
# OpenAI setup
# -----------------------------
client = AsyncOpenAI(api_key=OPENAI_KEY)

# -----------------------------
# Read diff
# -----------------------------
if not os.path.exists("diff.txt") or os.path.getsize("diff.txt") == 0:
    print("⚠️ diff.txt not found or empty. Skipping review.")
    exit()

with open("diff.txt") as f:
    diff_text = f.read()

# -----------------------------
# Helper: find lines to comment
# -----------------------------
def find_lines_to_comment(diff, search_terms=None):
    """Return a list of (line_number, line_text) for lines to comment."""
    lines = diff.split("\n")
    result = []
    for i, line in enumerate(lines, start=1):
        if search_terms:
            if any(term in line for term in search_terms):
                result.append((i, line.strip()))
        else:
            result.append((i, line.strip()))
    return result

# Example: risky patterns to flag
search_terms = ["netFlow[0]", "startBalance"]

lines_to_comment = find_lines_to_comment(diff_text, search_terms)

# -----------------------------
# Generate GPT review for each line
# -----------------------------
async def generate_line_comment(line_text):
    SYSTEM_PROMPT = """
You are a senior software engineer reviewing code changes.
Focus on readability, bugs, best practices, security, and improvements.
Provide a concise comment for this single line of code.
"""
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Review this line:\n{line_text}"}
        ],
        temperature=0.7
    )
    return resp.choices[0].message.content.strip()

# -----------------------------
# Post comments to PR
# -----------------------------
async def main():
    for diff_line_number, line_text in lines_to_comment:
        comment_text = await generate_line_comment(line_text)
        try:
            pr.create_review_comment(
                body=comment_text,
                commit_id=pr.head.sha,
                path="api/src/use-case/queries/get-insights/mwrr/helpers/calculate-mwrr-from-transactions.ts",
                line=diff_line_number,
                side="RIGHT"
            )
            print(f"✅ Comment posted at diff line {diff_line_number}")
        except Exception as e:
            print(f"❌ Failed to post comment at line {diff_line_number}: {e}")
            with open("review_comment.txt", "a") as f:
                f.write(f"Line {diff_line_number}: {comment_text}\n")

if __name__ == "__main__":
    asyncio.run(main())

