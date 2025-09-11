import os
import sys
import asyncio
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI

# -----------------------------
# Environment variables
# -----------------------------
pr_number = os.environ.get("PR_NUMBER")
repo_name = os.environ.get("GITHUB_REPOSITORY")  # e.g., owner/repo

# Read diff
diff_file = "diff.txt"
if not os.path.exists(diff_file):
    print(f"ERROR: {diff_file} not found.")
    sys.exit(1)

with open(diff_file, "r") as f:
    diff_content = f.read()

if not diff_content.strip():
    review_comment = "No changes detected in diff."
else:
    # -----------------------------
    # Azure OpenAI token provider
    # -----------------------------
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), 
        "https://cognitiveservices.azure.com/.default"
    )

    client = AsyncAzureOpenAI(
        azure_endpoint="https://alpheya-oai.qwlth.dev",
        api_version="2024-09-01-preview",
        azure_ad_token_provider=token_provider
    )

    async def get_review():
        resp = await client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": "You are a senior software engineer reviewing code changes."},
                {"role": "user", "content": f"Please review this git diff and provide concise PR comments:\n\n{diff_content}"}
            ],
            temperature=0,
        )
        return resp.choices[0].message.content.strip()

    review_comment = asyncio.run(get_review())

# -----------------------------
# Save to file for GitHub Action
# -----------------------------
with open("review_comment.txt", "w") as f:
    f.write(review_comment)

print("✅ review_comment.txt written successfully")
print(review_comment)

