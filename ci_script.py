import os
import asyncio
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.ai.openai.aio import AsyncAzureOpenAI
from github import Github

async def main():
    # -----------------------------
    # Read git diff
    # -----------------------------
    diff_file = "diff.txt"
    if not os.path.exists(diff_file):
        print("⚠️ diff.txt not found. Skipping OpenAI review.")
        return

    with open(diff_file, "r") as f:
        diff = f.read()

    # -----------------------------
    # Setup Azure OpenAI client
    # -----------------------------
    try:
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default"
        )

        client = AsyncAzureOpenAI(
            azure_endpoint="https://alpheya-oai.qwlth.dev",
            api_version="2024-09-01-preview",
            azure_ad_token_provider=token_provider,
        )
    except Exception as e:
        print(f"❌ Failed to initialize Azure OpenAI client: {e}")
        return

    # -----------------------------
    # Call OpenAI API
    # -----------------------------
    review_comment = ""
    try:
        res = await client.chat_completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": "You are a senior software engineer reviewing code changes."},
                {"role": "user", "content": f"Please review this git diff and provide concise PR comments:\n\n{diff}"}
            ],
            temperature=0.7,
        )
        review_comment = res.choices[0].message.content.strip()
        print("OpenAI response:\n", review_comment)
    except Exception as e:
        print(f"❌ OpenAI request failed: {e}")

    # -----------------------------
    # Post to GitHub if token exists
    # -----------------------------
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        try:
            repo_name = os.getenv("GITHUB_REPOSITORY", "Alma7awi/github-dani")
            pr_number = int(os.getenv("PR_NUMBER", "0"))
            if pr_number:
                g = Github(github_token)
                repo = g.get_repo(repo_name)
                pr = repo.get_pull(pr_number)
                pr.create_issue_comment(review_comment)
                print("✅ Comment posted to PR")
            else:
                print("⚠️ PR_NUMBER not set, skipping posting to GitHub")
        except Exception as e:
            print(f"❌ Failed to post comment: {e}")
    else:
        print("⚠️ GITHUB_TOKEN not set, skipping posting to GitHub")

    # -----------------------------
    # Always save locally
    # -----------------------------
    with open("review_comment.txt", "w") as f:
        f.write(review_comment)
    print("💾 Saved review_comment.txt")


if __name__ == "__main__":
    asyncio.run(main())


