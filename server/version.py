"""Which code is running: the deployed git commit, read once when the server starts.

Order: GIT_COMMIT or RENDER_GIT_COMMIT (set by a deploy) -> the checkout's own .git (the AWS VM runs from a git clone
and restarts after each `git pull`, so start-up time is deploy time) -> None. Read straight from the .git files: no
subprocess, nothing else about the server is exposed.
"""
from __future__ import annotations

import os
from pathlib import Path


def _from_git(root: Path) -> str | None:
    git = root / ".git"
    try:
        head = (git / "HEAD").read_text().strip()
    except OSError:
        return None
    if not head.startswith("ref:"):
        return head or None                                   # a detached HEAD holds the sha itself
    ref = head.split(":", 1)[1].strip()
    try:
        return (git / ref).read_text().strip() or None
    except OSError:
        pass
    try:                                                      # after `git gc` the ref may only be in packed-refs
        for line in (git / "packed-refs").read_text().splitlines():
            if line.endswith(" " + ref):
                return line.split(" ", 1)[0]
    except OSError:
        pass
    return None


def deployed(root: Path) -> dict:
    """{"commit": short sha or None, "commit_source": "env" | "git" | None}."""
    env = os.getenv("GIT_COMMIT") or os.getenv("RENDER_GIT_COMMIT")
    if env:
        return {"commit": env.strip()[:8], "commit_source": "env"}
    sha = _from_git(root)
    return {"commit": sha[:8], "commit_source": "git"} if sha else {"commit": None, "commit_source": None}
