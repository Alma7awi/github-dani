import os
import asyncio
from github import Github, Auth
from azure.ai.openai.aio import OpenAIClient
from azure.core.credentials import AzureKeyCredential

# -------------------------------
# Environment variables
# -------------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
PR_NUMBER = int(os.getenv("PR_NUMBER", "0"))
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")

if not all([GITHUB_TOKEN, GITHUB_REPOSITORY, PR_NUMBER, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY]):
    raise ValueError("Missing one or more required environment variables")

# -------------------------------
# Async PR review function
# -------------------------------
async def run_review():
    # Initialize GitHub client
    gh = Github(auth=Auth.Token(GITHUB_TOKEN))
    repo = gh.get_repo(GITHUB_REPOSITORY)
    pr = repo.get_pull(PR_NUMBER)

    # Read diff file
    try:
        with open("diff.txt", "r") as f:
            diff_text = f.read()
    except FileNotFoundError:
        diff_text = ""
    
    if not diff_text.strip():
        print("No changes detected in PR.")
        return

    # Initialize Azure OpenAI client
    client = OpenAIClient(
        AZURE_OPENAI_ENDPOINT,
        credential=AzureKeyCredential(AZURE_OPENAI_KEY)
    )

    # Prepare a simple prompt for code review
    prompt = f"Please review the following code changes:\n\n{diff_text}"

    # Call Azure OpenAI asynchronously
    response = await client.chat_completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    review_comment = response.choices[0].message.content

    # -------------------------------
    # Post comments to PR
    # -------------------------------
    try:
        for line_number, line in enumerate(diff_text.splitlines(), start=1):
            # Post review comment on PR using correct 'commit' argument
            pr.create_review_comment(
                body=line,  # or review_comment if posting full review
                path=".github/workflows/main.yml",  # replace dynamically if needed
                position=line_number,
                commit=pr.head.sha
            )
        print("Comments posted successfully.")
    except Exception as e:
        print(f"❌ Failed to post comment: {e}")
        # Fallback: save to file
        with open("review_comment.txt", "w") as f:
            f.write(review_comment)
        print("Review saved to review_comment.txt")

# -------------------------------
# Run async main
# -------------------------------
if __name__ == "__main__":
    asyncio.run(run_review())

