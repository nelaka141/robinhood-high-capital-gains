"""Step 7's "unalterable paper trail": branch, commit, push, then PR + merge into main.
Uses plain `git` via subprocess (run inside a clone of the repo) and the GitHub REST API for
the PR (requires GITHUB_TOKEN in the environment with repo write access)."""
from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List

import requests

GITHUB_API = "https://api.github.com"


def _run(*args: str, cwd: str | Path = ".") -> str:
    result = subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def commit_and_push_cycle(
    repo_dir: str | Path,
    changed_paths: List[str],
    commit_message: str,
    branch_prefix: str = "auto/rebalance",
) -> str:
    """Creates a fresh branch off origin/main, commits `changed_paths`, pushes it. Returns the
    branch name. Assumes `repo_dir` is already a clone with `origin` configured."""
    branch = f"{branch_prefix}-{datetime.utcnow():%Y%m%d-%H%M%S}"
    _run("git", "fetch", "origin", "main", cwd=repo_dir)
    _run("git", "checkout", "-B", branch, "origin/main", cwd=repo_dir)
    _run("git", "add", *changed_paths, cwd=repo_dir)
    _run("git", "commit", "-m", commit_message, cwd=repo_dir)
    _run("git", "push", "-u", "origin", branch, cwd=repo_dir)
    return branch


def open_and_merge_pr(owner: str, repo: str, branch: str, title: str, body: str) -> dict:
    """Opens a PR from `branch` into main and merges it immediately — this bot's own automated
    commits are pre-authorized to merge without human review, per CLAUDE.md's standing
    instruction. Requires GITHUB_TOKEN in the environment."""
    token = os.environ["GITHUB_TOKEN"]
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    pr = requests.post(
        f"{GITHUB_API}/repos/{owner}/{repo}/pulls",
        headers=headers,
        json={"title": title, "head": branch, "base": "main", "body": body},
        timeout=30,
    )
    pr.raise_for_status()
    pr_number = pr.json()["number"]

    merge = requests.put(
        f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/merge",
        headers=headers,
        json={"merge_method": "merge"},
        timeout=30,
    )
    merge.raise_for_status()
    return {"pr_number": pr_number, "pr_url": pr.json()["html_url"], "merge": merge.json()}
