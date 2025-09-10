#!/usr/bin/env python3
"""
ci_script.py
- Prints hello
- Verifies OPENAI_API_KEY exists (won't print the key)
- Gets git diff
- Calls OpenAI Chat Completion API
- Saves response or quota warning into review_comment.txt
"""

import os
import sys
import subprocess
from openai import OpenAI


def get_git_diff():
    try:
        # Try normal diff (last commit vs previous commit)
        return subprocess.check_output(["git", "diff", "HEAD~1..HEAD"], text=True)
    except subprocess.CalledProcessError:
        # Fallback for very first commit
        return subprocess.check_output(["git", "show", "HEAD"], text=True)




def main():
    print("Hello from ci_script.py — Dani CI test")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in environment. Exiting with failure.")
        sys.exit(1)
    else:
        print("OPENAI_API_KEY found in environment (will NOT print it).")

    diff = get_git_diff()
    client = OpenAI(api_key=api_key)

    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turo",
            messages=[
                {"role": "system", "content": "You are an engineer. Review the provided git diff and suggest improvements."},
                {"role": "user", "content": f"Here is the git diff:\n\n{diff}"}
            ],
            max_tokens=500,
        )

        assistant_text = resp.choices[0].message.content.strip()
        print("OpenAI response:")
        print(assistant_text)

    except Exception as e:
        msg = str(e)
        if "insufficient_quota" in msg:
            assistant_text = "⚠️ OpenAI quota exceeded — cannot generate review right now."
            print(assistant_text)
        else:
            print("OpenAI API request failed:", e)
            sys.exit(1)

    # Always save something to review_comment.txt
    with open("review_comment.txt", "w") as f:
        f.write(assistant_text)


if __name__ == "__main__":
    main()
