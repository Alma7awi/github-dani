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
from openai import OpenAI
import subprocess

diff = subprocess.check_output(["git", "diff", "HEAD~1..HEAD"], text=True)


def main():
    print("Hello from ci_script.py — Dani CI test")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in environment. Exiting with failure.")
        sys.exit(1)
    else:
        print("OPENAI_API_KEY found in environment (will NOT print it).")

    # Create client (we pass api_key explicitly for clarity; the library also reads the env var)
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

        # Extract the assistant message safely
        assistant_text = resp.choices[0].message.content
        try:
            # Many SDK responses store text at resp.choices[0].message.content
            choice = resp.choices[0]
            message_obj = getattr(choice, "message", None) or choice.get("message", None)
            if message_obj:
                assistant_text = getattr(message_obj, "content", None) or message_obj.get("content", None)
        except Exception:
            assistant_text = None

        if not assistant_text:
            # fallback: print whole response (safe for debugging)
            print("OpenAI response (raw):")
            print(resp)
        else:
            print("OpenAI response:")
            print(assistant_text.strip())

    except Exception as e:
        print("OpenAI API request failed:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
