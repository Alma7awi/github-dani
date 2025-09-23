import os
import requests
import subprocess
import json
from openai import OpenAI

# --- Setup ---
token = os.getenv("GITHUB_TOKEN")
repo = os.getenv("GITHUB_REPOSITORY")
pr_number = os.getenv("PR_NUMBER")
commit_id = os.getenv("GITHUB_SHA")

headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github+json"
}

# --- Step 1: Get PR diff ---
diff = subprocess.check_output(
    ["git", "diff", "origin/main...HEAD"], text=True
)

# --- Step 2: Ask OpenAI to generate inline review comments ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

prompt = f"""
You are a code reviewer. Review the following diff and suggest inline comments. 
Output ONLY valid JSON in the following format:

[
  {{"file": "filename", "line": line_number, "comment": "Your review text"}},
  ...
]

Diff:
{diff}
"""

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
    temperature=0
)

raw_output = response.choices[0].message.content.strip()

# --- Step 3: Parse JSON ---
try:
    comments = json.loads(raw_output)
except json.JSONDecodeError:
    print("⚠️ OpenAI did not return valid JSON. Output was:\n", raw_output)
    comments = []

# --- Step 4: Post inline comments to GitHub ---
url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/comments"

for c in comments:
    payload = {
        "body": c["comment"],
        "commit_id": commit_id,
        "path": c["file"],
        "line": c["line"],
        "side": "RIGHT"
    }
    r = requests.post(url, headers=headers, json=payload)

    if r.status_code == 201:
        print(f"✅ Comment posted on {c['file']}:{c['line']}")
    else:
        print(f"❌ Failed to post comment: {r.status_code}, {r.text}")

