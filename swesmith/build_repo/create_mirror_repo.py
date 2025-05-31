import argparse
import os
import subprocess
import shutil

from dotenv import load_dotenv
from ghapi.all import GhApi
from swesmith.constants import ORG_NAME
from swesmith.utils import (
    repo_exists,
    get_repo_name,
)

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
api = GhApi(token=GITHUB_TOKEN)


def get_latest_commit(repo: str) -> str:
    """
    Get the latest commit hash of a repository.
    """
    try:
        org, repo_name = repo.split("/", 1)
        commits = api.repos.list_commits(org, repo_name, per_page=1, page=1)
        if commits:
            return commits[0].sha
        else:
            raise ValueError(f"No commits found for repository {repo}")
    except Exception as e:
        raise RuntimeError(f"Failed to get latest commit for {repo}: {e}")


def create_mirror_repo(repo: str, commit: str = "latest", org: str = ORG_NAME) -> None:
    """
    Create a mirror of the repository at the given commit.
    """
    if commit == "latest":
        commit = get_latest_commit(repo)
    repo_name = get_repo_name(repo, commit)
    if repo_exists(repo_name):
        return
    if repo_name in os.listdir():
        shutil.rmtree(repo_name)
    print(f"[{repo}][{commit[:8]}] Creating Mirror")
    api.repos.create_in_org(org, repo_name)
    for cmd in [
        f"git clone git@github.com:{repo}.git {repo_name}",
        (
            f"cd {repo_name}; "
            f"git checkout {commit}; "
            "rm -rf .git; "
            "git init; "
            'git config user.name "swesmith"; '
            'git config user.email "swesmith@anon.com"; '
            "rm -rf .github/workflows; "  # Remove workflows
            "git add .; "
            "git commit -m 'Initial commit'; "
            "git branch -M main; "
            f"git remote add origin git@github.com:{org}/{repo_name}.git; "
            "git push -u origin main",
        ),
        f"rm -rf {repo_name}",
    ]:
        subprocess.run(
            cmd,
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    print(f"[{repo}][{commit[:8]}] Mirror created successfully")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a mirror repository at a specific commit."
    )
    parser.add_argument("repo", type=str, help="Repository to mirror.")
    parser.add_argument(
        "--commit", type=str, default="latest", help="Commit hash to mirror."
    )
    parser.add_argument(
        "--org",
        type=str,
        default=ORG_NAME,
        help="GitHub organization to create repo for (default: 'swesmith')",
    )
    args = parser.parse_args()

    create_mirror_repo(**vars(args))
