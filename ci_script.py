
ci_script.py
- Reads diff.txt
- Calls OpenAI for code review
- Posts comment to GitHub PR
- Handles quota issues, forked PRs, and deprecated 

import os
import sys
from openai import OpenAI
from github import Github, Auth

print("Hello from ci_script.py — Dani CI test")

# Example content (replace this with your OpenAI API call result)
review_text = "✅ Code Review:\nLooks good, but consider adding more comments."

# Save to file so GitHub Action can read it
with open("review_comment.txt", "w") as f:
    f.write(review_text)

print("review_comment.txt written successfully")

def main():
    print("Hello from ci_script.py — Dani CI test")

    # -----------------------------
    # Environment variables
    # -----------------------------
    openai_key = os.environ.get("OPENAI_API_KEY")
    github_token = os.environ.get("GITHUB_TOKEN")  # can be PAT
    pr_number = os.environ.get("PR_NUMBER")
    repo_name = os.environ.get("GITHUB_REPOSITORY")  # e.g., owner/repo

    if not openai_key:
        print("ERROR: OPENAI_API_KEY not set.")
        sys.exit(1)
    if not github_token:
        print("ERROR: GITHUB_TOKEN not set.")
        sys.exit(1)
    if not pr_number or not repo_name:
        print("INFO: PR number or repo not set. Skipping PR comment (likely a forked PR).")
        post_comment = False
    else:
        post_comment = True

    # -----------------------------
    # Read diff.txt
    # -----------------------------
    diff_file = "diff.txt"
    if not os.path.exists(diff_file):
        print(f"ERROR: {diff_file} not found.")
        sys.exit(1)

    with open(diff_file, "r") as f:
        diff = f.read()

    if not diff.strip():
        review_comment = "No changes detected in diff."
        print(review_comment)
    else:
        # -----------------------------
        # Call OpenAI API
        # -----------------------------
        client = OpenAI(api_key=openai_key)
        try:
            resp = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": "You are a senior software engineer reviewing code changes."},
                    {"role": "user", "content": f"Please review this git diff and provide concise PR comments:\n\n{diff}"}
                ],
                max_tokens=500,
            )
            review_comment = resp.choices[0].message.content.strip()
            print("OpenAI response:\n", review_comment)

        except Exception as e:
            msg = str(e)
            if "insufficient_quota" in msg or "429" in msg:
                review_comment = "⚠️ OpenAI quota exceeded — cannot generate review at this time."
                print(review_comment)
            else:
                review_comment = f"⚠️ OpenAI request failed: {msg}"
                print(review_comment)

    # -----------------------------
    # Post comment to GitHub PR
    # -----------------------------
    if post_comment:
        try:
            g = Github(auth=Auth.Token(github_token))  # new auth method
            repo = g.get_repo(repo_name)
            pr = repo.get_pull(int(pr_number))
            pr.create_issue_comment(review_comment)
            print(f"✅ Comment posted to PR #{pr_number}")
        except Exception as e:
            print(f"⚠️ Failed to post comment: {e}")
    else:
        print("PR comment skipped (forked PR or missing info).")

if __name__ == "__main__":
    main()
