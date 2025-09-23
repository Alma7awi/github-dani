import os
import re
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
# Parse unified diff -> [(file_path, line_no, line_text)]
# -----------------------------
def parse_diff(diff):
    comments = []
    current_file = None
    new_line_num = None

    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_file = line.replace("+++ b/", "").strip()
        elif line.startswith("@@"):
            # Example: @@ -12,8 +12,8 @@
            match = re.search(r"\+(\d+)", line)
            if match:
                new_line_num = int(match.group(1)) - 1  # reset offset
        elif line.startswith("+") and not line.startswith("+++"):
            new_line_num += 1
            comments.append((current_file, new_line_num, line[1:].strip()))
        elif line.startswith("-") and not line.startswith("---"):
            # removed line, skip since no anchor in PR
            continue
        else:
            if new_line_num is not None:
                new_line_num += 1
    return comments

diff_lines = parse_diff(diff_text)

# -----------------------------
# Generate GPT review for each line
# -----------------------------
async def generate_line_comment(line_text):
    SYSTEM_PROMPT = """
You are a senior software engineer reviewing code changes.
Focus on readability, bugs, best practices, security, and improvements.
Provide a concise review comment for this single line of code.
"""
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Review this line of code:\n{line_text}"}
        ],
        temperature=0.7
    )
    return resp.choices[0].message.content.strip()

# -----------------------------
# Post inline comments
# -----------------------------
async def main():
    for file_path, line_num, line_text in diff_lines:
        try:
            comment_text = await generate_line_comment(line_text)
            pr.create_review_comment(
                body=comment_text,
                commit_id=pr.head.sha,
                path=file_path,
                line=line_num,
                side="RIGHT"
            )
            print(f"✅ Comment posted on {file_path}:{line_num}")
        except Exception as e:
            print(f"❌ Failed on {file_path}:{line_num}: {e}")
            with open("review_comment.txt", "a") as f:
                f.write(f"{file_path}:{line_num} - {line_text}\n{comment_text}\n\n")

if __name__ == "__main__":
    asyncio.run(main())

