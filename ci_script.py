import os
import asyncio
from github import Github
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.ai.openai.aio import AsyncAzureOpenAI

# -----------------------------
# GitHub setup
# -----------------------------
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY")  # e.g., 'username/repo'
PR_NUMBER = int(os.environ.get("PR_NUMBER", 1))    # default PR number = 1

if not GITHUB_TOKEN:
    raise EnvironmentError("GITHUB_TOKEN not set")

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

client = AsyncAzureOpenAI(
    azure_endpoint="https://alpheya-oai.qwlth.dev",
    api_version="2024-09-01-preview",
    azure_ad_token_provider=token_provider,
)

# -----------------------------
# Read diff
# -----------------------------
if not os.path.exists("diff.txt") or os.path.getsize("diff.txt") == 0:
    print("⚠️ diff.txt not found or empty. Skipping OpenAI review.")
    review_comment = "No diff found."
else:
    with open("diff.txt", "r") as f:
        diff = f.read()

# -----------------------------
# Helper to map code lines to diff positions
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
# Generate review comments using Azure OpenAI
# -----------------------------
async def generate_line_comments():
    if not diff:
        return []

    # For example, we can search for risky patterns (you can use OpenAI too)
    search_terms = ["netFlow[0]", "startBalance"]
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

    for diff_pos, comment_text in comments:
        try:
            pr.create_review_comment(
                body=comment_text,
                commit_id=pr.head.sha,
                path="api/src/use-case/queries/get-insights/mwrr/helpers/calculate-mwrr-from-transactions.ts",
                line=diff_pos,
                side="RIGHT"
            )
            print(f"✅ Comment posted at diff line {diff_pos}")
        except Exception as e:
            print("❌ Failed to post comment:", e)
            with open("review_comment.txt", "w") as f:
                f.write(comment_text)
            print("💾 Saved review_comment.txt instead")

if __name__ == "__main__":
    asyncio.run(main())



