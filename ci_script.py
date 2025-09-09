#!/usr/bin/env python3
"""
ci_script.py
- Prints hello
- Verifies OPENAI_API_KEY exists (won't print the key)
- Calls OpenAI Chat Completion API with a system + user prompt
- Prints the assistant reply
"""

import os
import sys
import subprocess
from openai import OpenAI


def get_git_diff():
    try:
        # Check if HEAD~1 exists
        subprocess.check_output(["git", "rev-parse", "HEAD~1"], stderr=subprocess.DEVNULL)
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

    # Get git diff
    diff = get_git_diff()

    # Create client
    client = OpenAI(api_key=api_key)

    try:
        # Chat completions style: system + user
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an engineer. Review the provided git diff and suggest improvements."},
                {"role": "user", "content": f"Here is the git diff:\n\n{diff}"}
            ],
            max_tokens=500,
        )

        # Extract the assistant message
        assistant_text = resp.choices[0].message.content

        print("OpenAI response:")
        print(assistant_text.strip())

        # Save response to file (for workflow comment step)
        with open("review_comment.txt", "w") as f:
            f.write(assistant_text.strip())

        except Exception as e:
    msg = str(e)
    if "insufficient_quota" in msg:
        assistant_text = "⚠️ OpenAI quota exceeded — cannot generate review right now."
        print(assistant_text)
        with open("review_comment.txt", "w") as f:
            f.write(assistant_text)
        sys.exit(0)  # exit successfully so workflow continues
    else:
        print("OpenAI API request failed:", e)
        sys.exit(1)



if __name__ == "__main__":
    main()

