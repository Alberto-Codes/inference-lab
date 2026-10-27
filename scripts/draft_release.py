"""Create an experiment draft at a validated commit without publishing its tag."""

import argparse
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

REPO = "Alberto-Codes/inference-lab"


def api(path: str, payload: dict | None = None):
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={
            "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404 and payload is None:
            return None
        raise


def create_draft(tag: str, commit: str) -> dict:
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag) or not re.fullmatch(
        r"[0-9a-f]{40}", commit
    ):
        raise ValueError("Use a vMAJOR.MINOR.PATCH tag and full lowercase commit SHA")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if head != commit:
        raise ValueError("Check out the exact release commit before creating the draft")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "origin/main"], check=True
    )
    runs = api(
        f"actions/workflows/ci.yml/runs?head_sha={commit}&branch=main&status=success"
    )
    if not runs or not any(
        r["head_sha"] == commit and r["conclusion"] == "success"
        for r in runs["workflow_runs"]
    ):
        raise ValueError("Successful CI at the release SHA is required")
    if api(f"git/ref/tags/{tag}") is not None:
        raise ValueError("Tag already exists; experiment tags are immutable")
    page = 1
    while True:
        releases = api(f"releases?per_page=100&page={page}")
        if releases is None:
            raise RuntimeError("Cannot read repository releases")
        if any(r["tag_name"] == tag for r in releases):
            raise ValueError(
                "Release already exists; inspect it instead of overwriting"
            )
        if len(releases) < 100:
            break
        page += 1
    notes = Path(f"docs/releases/{tag}.md").read_text()
    notes = notes.replace("(../", f"(https://github.com/{REPO}/blob/{commit}/docs/")
    notes += (
        f"\n\nExperiment commit: [{commit}](https://github.com/{REPO}/tree/{commit}).\n"
    )
    release = api(
        "releases",
        {
            "tag_name": tag,
            "target_commitish": commit,
            "name": f"{tag}: Nemotron Parse receipt pilot",
            "body": notes,
            "draft": True,
            "prerelease": True,
        },
    )
    verified = api(f"releases/{release['id']}")
    if not verified or not verified["draft"] or verified["target_commitish"] != commit:
        raise RuntimeError("Draft target verification failed; inspect the release")
    if api(f"git/ref/tags/{tag}") is not None:
        raise RuntimeError("Unexpected tag after draft creation; inspect the release")
    return verified


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    release = create_draft(args.tag, args.commit)
    print(
        f"status: draft\nurl: {release['html_url']}\ntarget: {release['target_commitish']}\ntag_exists: false"
    )


if __name__ == "__main__":
    main()
