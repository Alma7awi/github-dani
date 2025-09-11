import os
import sys
from openai import OpenAI
from github import Github, Auth

print("Hello from ci_script.py — Dani CI test")

def main():
    # -----------------------------
    # Environment variables
    # -----------------------------
    openai_key = os.environ.get("OPENAI_API_KEY")
    github_token = os.environ.get("GITHUB_TOKEN")  # can be PAT
    pr_number = os.environ.get("PR_NUMBER")
    repo_name = os.environ.get("GITHUB_REPOSITORY")  # e.g., owner/repo

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
    else:
        review_comment = ""  # will fill below

        # -----------------------------
        # Call OpenAI API (if key exists)
        # -----------------------------
        if openai_key:
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
                # -----------------------------
                # Fallback: include diff if OpenAI fails
                # -----------------------------
                if "insufficient_quota" in msg or "429" in msg:
                    review_comment = f"⚠️ OpenAI quota exceeded — cannot generate review.\n\nHere is the diff as fallback:\n\n{diff}"
                    print("⚠️ OpenAI quota exceeded — posting diff as fallback.")
                else:
                    review_comment = f"⚠️ OpenAI request failed: {msg}\n\nHere is the diff:\n\n{diff}"
                    print(f"⚠️ OpenAI request failed: {msg}")

        else:
            # No API key: just post the diff
            review_comment = f"ℹ️ No OpenAI API key found — posting diff only:\n\n{diff}"
            print("No OpenAI API key, posting diff only.")

    # -----------------------------
    # Save comment to file
    # -----------------------------
    with open("review_comment.txt", "w") as f:
        f.write(review_comment)
    print("✅ review_comment.txt written successfully")

    # -----------------------------
    # Post comment to GitHub PR
    # -----------------------------
    if post_comment:
        try:
            g = Github(auth=Auth.Token(github_token))
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

