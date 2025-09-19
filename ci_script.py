import os
import asyncio
from github import Github
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncOpenAI

# -----------------------------
# GitHub setup
# -----------------------------
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY")  # e.g., 'username/repo'
PR_NUMBER = int(os.environ.get("PR_NUMBER", 1))

if not GITHUB_TOKEN:
    raise EnvironmentError("⚠️ GITHUB_TOKEN not set")

gh = Github(GITHUB_TOKEN)
repo = gh.get_repo(GITHUB_REPO)
pr = repo.get_pull(PR_NUMBER)

# -----------------------------
# Azure OpenAI setup
# -----------------------------
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default"
)

client = AsyncOpenAI(
    api_version="2024-09-01-preview",
    azure_endpoint="https://alpheya-oai.qwlth.dev",
    azure_ad_token_provider=token_provider,
)

# -----------------------------
# Read diff
# -----------------------------
diff = ""
if os.path.exists("diff.txt") and os.path.getsize("diff.txt") > 0:
    with open("diff.txt", "r") as f:
        diff = f.read()
else:
    print("⚠️ diff.txt not found or empty. Skipping OpenAI review.")

# -----------------------------
# Helper: map code lines
# -----------------------------
def get_diff_positions(file_diff, search_terms):
    """Return list of (line_text, position) tuples for lines that match search_terms."""
    positions = []
    lines = file_diff.split("\n")
    for i, line in enumerate(lines, start=1):
        for term in search_terms:
            if term in line:
                positions.append((line.strip(), i))
    return positions

# -----------------------------
# Generate review comments using OpenAI
# -----------------------------
async def generate_line_comments():
    if not diff:
        return []

    search_terms = ["netFlow[0]", "startBalance"]  # Example triggers
    lines_to_comment = get_diff_positions(diff, search_terms)

    comments = []
    for line_text, diff_pos in lines_to_comment:
        SYSTEM_PROMPT = """
You are a senior software engineer reviewing code changes in a pull request.
Focus on:
1. Code readability and style
2. Possible bugs or errors
3. Best practices
4. Security considerations
5. Suggestions for improvement
Provide concise comments for this line only.
"""
        resp = await client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Review this code line and suggest improvements:\n{line_text}"}
            ],
            temperature=0.7,
        )
        comment_text = resp.choices[0].message.content.strip()
        comments.append((diff_pos, comment_text))
    return comments

# -----------------------------
# Post comments inline in PR
# -----------------------------
async def main():
    comments = await generate_line_comments()
    if not comments:
        print("No line-level comments generated.")
        return

    files = pr.get_files()
    target_file = None
    if files.totalCount > 0:
        target_file = files[0].filename  # just pick first changed file
    else:
        print("⚠️ No changed files found in PR.")
        return

    for diff_pos, comment_text in comments:
        try:
            pr.create_review_comment(
                body=comment_text,
                commit_id=pr.head.sha,
                path=target_file,
                position=diff_pos,   # must be relative position in diff
            )
            print(f"✅ Comment posted at {target_file}:{diff_pos}")
        except Exception as e:
            print(f"❌ Inline failed at {diff_pos}: {e}")
            # Fallback: post a general PR comment instead
            pr.create_issue_comment(f"[Line {diff_pos}] {comment_text}")
            print("💬 Posted as general PR comment")

if __name__ == "__main__":
    asyncio.run(main())


