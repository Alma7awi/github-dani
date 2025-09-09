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
        # Try normal diff (last commit vs previous commit)
        return subprocess.check_output(["git", "diff", "HEAD~1..HEAD"], text=True)
    except subprocess.CalledProcessError:
        # Fallback for very first commit: just show the initial commit diff
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
        print("OpenAI API request failed:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()

