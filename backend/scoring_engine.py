"""
Contribution scoring engine.
FinalScore = 0.4 * CodeScore + 0.3 * TimeConsistencyScore + 0.3 * PeerVoteScore
"""
import math
from typing import Dict, Any, List, Optional


def _normalize(value: float, min_val: float, max_val: float) -> float:
    """Clamp and normalize to 0-100."""
    if max_val <= min_val:
        return 100.0
    x = max(min_val, min(max_val, value))
    return 100.0 * (x - min_val) / (max_val - min_val)


def compute_code_score(
    commits: int,
    lines_added: int,
    lines_removed: int,
    files_modified: int,
    all_metrics: List[Dict[str, Any]],
    penalize_spam: bool = True,
) -> float:
    """
    Code score 0-100.
    - Weighted by commits and impact (lines, files).
    - Penalize commit spamming (many tiny commits).
    - Filter already applied for whitespace-only in git_analyzer.
    """
    if not all_metrics:
        return 0.0

    # Aggregate stats across all users for normalization
    total_commits = sum(m.get("commits", 0) for m in all_metrics)
    total_added = sum(m.get("lines_added", 0) for m in all_metrics)
    total_removed = sum(m.get("lines_removed", 0) for m in all_metrics)
    total_files = sum(m.get("files_modified", 0) for m in all_metrics)

    if total_commits == 0:
        return 0.0

    # Contribution share
    commit_share = commits / total_commits
    add_share = (lines_added / total_added) if total_added else 0
    rem_share = (lines_removed / total_removed) if total_removed else 0
    file_share = (files_modified / total_files) if total_files else 0

    # Weighted: 30% commits, 40% lines impact, 30% files
    raw = 0.3 * commit_share + 0.4 * (add_share + rem_share) / 2 + 0.3 * file_share
    raw = min(1.0, raw) * 100.0

    # Penalize spamming: many commits with very few lines each
    if penalize_spam and commits > 0:
        avg_lines = (lines_added + lines_removed) / commits
        if avg_lines < 5 and commits > 10:
            spam_penalty = 0.7  # 30% penalty
            raw *= spam_penalty

    return round(min(100.0, max(0.0, raw)), 2)


def compute_time_consistency_score(
    active_days: int,
    total_days: int,
    last_day_commits: int,
    total_commits: int,
) -> float:
    """
    Time consistency 0-100.
    - active_days / total_days as base.
    - Penalize last-day mass commits.
    """
    if total_days <= 0:
        return 0.0
    base = 100.0 * active_days / total_days
    # Penalty if >30% of commits on last day
    if total_commits > 0 and last_day_commits / total_commits > 0.3:
        base *= 0.7
    return round(min(100.0, max(0.0, base)), 2)


def compute_peer_vote_score(votes: List[int], scale_1_5: bool = True) -> float:
    """
    Average of peer votes, normalized to 0-100.
    votes: list of 1-5 ratings.
    """
    if not votes:
        return 0.0
    avg = sum(votes) / len(votes)
    if scale_1_5:
        # 1->0, 5->100
        normalized = 100.0 * (avg - 1) / 4.0
    else:
        normalized = avg
    return round(min(100.0, max(0.0, normalized)), 2)


def compute_final_score(
    code_score: float,
    time_score: float,
    peer_score: float,
    weight_code: float = 0.4,
    weight_time: float = 0.3,
    weight_vote: float = 0.3,
) -> float:
    """Weighted final score 0-100."""
    total_w = weight_code + weight_time + weight_vote
    if total_w <= 0:
        total_w = 1.0
    final = (
        (weight_code / total_w) * code_score
        + (weight_time / total_w) * time_score
        + (weight_vote / total_w) * peer_score
    )
    return round(min(100.0, max(0.0, final)), 2)


def score_tier_to_reputation(final_score: float) -> int:
    """
    Map final score to non-transferable reputation amount (ASA units).
    Tier-based for simplicity.
    """
    if final_score >= 90:
        return 100
    if final_score >= 80:
        return 80
    if final_score >= 70:
        return 60
    if final_score >= 60:
        return 40
    if final_score >= 50:
        return 20
    return 0
