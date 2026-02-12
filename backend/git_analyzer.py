"""
Git repository analysis using GitPython.
Clones repo (or uses existing path), parses git log, extracts per-author metrics.
"""
import os
import tempfile
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
import git
from git import Repo


def _ensure_clone(repo_url: str, base_dir: str) -> str:
    """Clone repo into base_dir and return path. Uses shallow clone for speed."""
    name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    path = os.path.join(base_dir, name)
    if os.path.isdir(path):
        try:
            r = Repo(path)
            r.remotes.origin.pull()
        except Exception:
            subprocess.run(["git", "clone", "--depth", "500", repo_url, path], check=True)
    else:
        os.makedirs(base_dir, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "500", repo_url, path], check=True)
    return path


def _is_whitespace_only_commit(commit: git.Commit) -> bool:
    """Heuristic: treat as whitespace-only if no insertions/deletions in commit stats."""
    try:
        total = commit.stats.total
        ins = total.get("insertions", 0)
        outs = total.get("deletions", 0)
        return ins == 0 and outs == 0
    except Exception:
        return True


def analyze_repo(
    repo_url: str,
    clone_dir: str,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Analyze git log and return per-author metrics.
    Returns dict: author_email -> { commits, lines_added, lines_removed, files_modified, active_days, ... }
    """
    path = _ensure_clone(repo_url, clone_dir)
    repo = Repo(path)

    # Default: last 90 days if no range
    if not until:
        until = datetime.utcnow()
    if not since:
        since = until - timedelta(days=90)

    since_str = since.strftime("%Y-%m-%d")
    until_str = until.strftime("%Y-%m-%d")

    # Per-author aggregates
    by_author: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "commits": 0,
            "lines_added": 0,
            "lines_removed": 0,
            "files_modified": set(),
            "commit_dates": [],
            "last_day_commits": 0,
        }
    )

    try:
        commits = list(
            repo.iter_commits(
                since=since_str,
                until=until_str,
                no_merges=True,
            )
        )
    except Exception:
        commits = []

    total_days = max(1, (until - since).days)
    last_day = (until - timedelta(days=1)).date() if total_days >= 1 else until.date()

    for commit in commits:
        try:
            author = commit.author.email or commit.author.name or "unknown"
        except Exception:
            author = "unknown"

        # Skip merge commits (already no_merges, but double-check)
        if len(commit.parents) > 1:
            continue

        # Filter whitespace-only
        if _is_whitespace_only_commit(commit):
            continue

        by_author[author]["commits"] += 1
        try:
            stats = commit.stats.total
            by_author[author]["lines_added"] += stats.get("insertions", 0)
            by_author[author]["lines_removed"] += stats.get("deletions", 0)
        except Exception:
            pass
        try:
            for f in commit.stats.files:
                by_author[author]["files_modified"].add(f)
        except Exception:
            pass
        try:
            ts = datetime.fromtimestamp(commit.committed_date)
            by_author[author]["commit_dates"].append(ts.date())
        except Exception:
            pass

    # Last-day commits (for penalty)
    for author, data in by_author.items():
        data["files_modified"] = len(data["files_modified"])
        dates = data["commit_dates"]
        data["active_days"] = len(set(dates))
        data["total_days"] = total_days
        data["last_day_commits"] = sum(1 for d in dates if d == last_day)
        del data["commit_dates"]

    return {k: dict(v) for k, v in by_author.items()}
