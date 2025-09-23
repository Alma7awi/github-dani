import os
import asyncio
from github import Github, Auth
from openai import AsyncOpenAI
from unidiff import PatchSet

# -----------------------------
# Config
# -----------------------------
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY")
PR_NUMBER = int(os.environ.get("PR_NUMBER", 0))
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")

if not all([GITHUB_TOKEN, GITHUB_REPO, OPENAI_KEY, PR_NUMBER]):
    raise EnvironmentError("Missing one of: GITHUB_TOKEN, GITHUB_REPOSITORY, OPENAI_API_KEY, PR_NUMBER")

gh = Github(auth=Auth.Token(GITHUB_TOKEN))
repo = gh.get_repo(GITHUB_REPO)
pr = repo.get_pull(PR_NUMBER)

client = AsyncOpenAI(api_key=OPENAI_KEY)

# -----------------------------
# Read and parse diff
# -----------------------------
with open("diff.txt") as f:
    patch = PatchSet(f)

# -----------------------------
# GPT comment generator
# -----------------------------
async def review_chunk(file_path, hunk_text):
    SYSTEM_PROMPT = """
You are a senior software engineer reviewing a Git diff.
Focus on readability, bugs, best practices, and correctness.
Write a concise review for this diff hunk.
"""
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Review this diff:\n{hunk_text}"}
        ],
        temperature=0.7
    )
    return resp.choices[0].message.content.strip()

# -----------------------------
# Main
# -----------------------------
async def main():
    for patched_file in patch:
        print(f"\n{patched_file.path}\nViewed\n")
        for hunk in patched_file:
            # Show raw diff chunk
            hunk_text = "".join(str(line) for line in hunk)
            print(hunk.section_header)
            print(hunk_text)

            # Ask GPT for review
            comment = await review_chunk(patched_file.path, hunk_text)
            print(f"\n💡 GPT Review:\n{comment}\n")

if __name__ == "__main__":
    asyncio.run(main())

