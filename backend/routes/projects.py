"""
Project routes: create, get, analyze, vote, finalize.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from config import get_settings
from database import get_db
from models import User, Project, ProjectMember, GitMetrics, Vote, FinalScore
from routes.auth import require_user_id, optional_user_id
from schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectMemberResponse,
    AnalyzeResponse,
    VoteSubmit,
    VoteResponse,
    FinalScoreResponse,
    LeaderboardEntry,
    DashboardResponse,
)
from git_analyzer import analyze_repo
from scoring_engine import (
    compute_code_score,
    compute_time_consistency_score,
    compute_peer_vote_score,
    compute_final_score,
    score_tier_to_reputation,
)
from blockchain_service import (
    create_project_contract,
    finalize_project,
    submit_score_hash_txn,
    hash_score,
    read_app_global_state,
)
import os

router = APIRouter(prefix="/projects", tags=["projects"])
settings = get_settings()


def _member_response(m: ProjectMember) -> ProjectMemberResponse:
    return ProjectMemberResponse(
        id=m.id,
        user_id=m.user_id,
        github_username=m.user.github_username,
        wallet_address=m.user.wallet_address,
        role=m.role,
    )


@router.post("/create", response_model=ProjectResponse)
def create_project(
    body: ProjectCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(require_user_id),
):
    """Create project, add members by wallet, deploy contract."""
    # Validate weights sum to 1
    w = body.weight_code + body.weight_time + body.weight_vote
    if abs(w - 1.0) > 0.01:
        raise HTTPException(status_code=400, detail="Weights must sum to 1.0")

    creator = db.query(User).filter(User.id == user_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="User not found")

    project = Project(
        name=body.name,
        repo_url=body.repo_url,
        creator_id=user_id,
        weight_code=body.weight_code,
        weight_time=body.weight_time,
        weight_vote=body.weight_vote,
        deadline_contribution=body.deadline_contribution,
        deadline_voting=body.deadline_voting,
        status="draft",
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Add creator as owner
    db.add(
        ProjectMember(project_id=project.id, user_id=user_id, role="owner")
    )
    # Add members by wallet: find users with those wallets
    for addr in body.member_wallet_addresses or []:
        if not addr or addr == (creator.wallet_address or ""):
            continue
        u = db.query(User).filter(User.wallet_address == addr).first()
        if u:
            pm = ProjectMember(project_id=project.id, user_id=u.id, role="member")
            db.add(pm)
    db.commit()

    # Deploy contract if we have creator mnemonic and rep ASA
    if settings.CREATOR_MNEMONIC and settings.REPUTATION_ASA_ID:
        try:
            approval_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "contracts", "teal", "contribution_approval.teal"
            )
            clear_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "contracts", "teal", "contribution_clear.teal"
            )
            if os.path.isfile(approval_path) and os.path.isfile(clear_path):
                with open(approval_path) as f:
                    approval_teal = f.read()
                with open(clear_path) as f:
                    clear_teal = f.read()
                wc = int(round(body.weight_code * 100))
                wt = int(round(body.weight_time * 100))
                wv = int(round(body.weight_vote * 100))
                app_id, app_addr = create_project_contract(
                    settings.CREATOR_MNEMONIC,
                    project.id,
                    int(body.deadline_contribution.timestamp()),
                    int(body.deadline_voting.timestamp()),
                    wc, wt, wv,
                    settings.REPUTATION_ASA_ID,
                    approval_teal,
                    clear_teal,
                )
                project.contract_app_id = app_id
                project.contract_address = app_addr
                project.status = "active"
                db.commit()
                db.refresh(project)
        except Exception as e:
            # Leave project in draft; contract can be deployed later
            pass

    members = db.query(ProjectMember).filter(ProjectMember.project_id == project.id).all()
    return ProjectResponse(
        id=project.id,
        name=project.name,
        repo_url=project.repo_url,
        weight_code=project.weight_code,
        weight_time=project.weight_time,
        weight_vote=project.weight_vote,
        deadline_contribution=project.deadline_contribution,
        deadline_voting=project.deadline_voting,
        status=project.status,
        contract_app_id=project.contract_app_id,
        contract_address=project.contract_address,
        created_at=project.created_at,
        members=[_member_response(m) for m in members],
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    user_id: Optional[int] = Depends(optional_user_id),
):
    project = db.query(Project).options(joinedload(Project.members).joinedload(ProjectMember.user)).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(
        id=project.id,
        name=project.name,
        repo_url=project.repo_url,
        weight_code=project.weight_code,
        weight_time=project.weight_time,
        weight_vote=project.weight_vote,
        deadline_contribution=project.deadline_contribution,
        deadline_voting=project.deadline_voting,
        status=project.status,
        contract_app_id=project.contract_app_id,
        contract_address=project.contract_address,
        created_at=project.created_at,
        members=[_member_response(m) for m in project.members],
    )


@router.post("/{project_id}/analyze", response_model=AnalyzeResponse)
def analyze_project(
    project_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(require_user_id),
):
    """Clone repo, run git analysis, store metrics, return per-user metrics."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.repo_url:
        raise HTTPException(status_code=400, detail="No repo URL set")
    clone_dir = settings.GIT_CLONE_DIR
    since = None
    until = project.deadline_contribution
    raw = analyze_repo(project.repo_url, clone_dir, since=since, until=until)
    # Map author email to github_username via project members
    member_emails = {}
    for m in project.members:
        # We don't have email in User; use github_username as key for metrics
        member_emails[m.user.github_username.lower()] = m.user.github_username
    metrics_json = {}
    all_metrics_list = list(raw.values())
    for author_key, data in raw.items():
        author_lower = author_key.lower().split("@")[0] if "@" in author_key else author_key.lower()
        # Try to match to member
        username = member_emails.get(author_lower) or author_key
        code_s = compute_code_score(
            data.get("commits", 0),
            data.get("lines_added", 0),
            data.get("lines_removed", 0),
            data.get("files_modified", 0),
            all_metrics_list,
        )
        time_s = compute_time_consistency_score(
            data.get("active_days", 0),
            data.get("total_days", 1),
            data.get("last_day_commits", 0),
            data.get("commits", 0),
        )
        metrics_json[username] = {
            **data,
            "code_score_raw": code_s,
            "time_score_raw": time_s,
        }
    gm = db.query(GitMetrics).filter(GitMetrics.project_id == project_id).first()
    if gm:
        gm.metrics_json = metrics_json
        gm.last_analyzed_at = datetime.utcnow()
        db.commit()
    else:
        gm = GitMetrics(project_id=project_id, metrics_json=metrics_json, last_analyzed_at=datetime.utcnow())
        db.add(gm)
        db.commit()
    return AnalyzeResponse(project_id=project_id, metrics=metrics_json, last_analyzed_at=gm.last_analyzed_at)


@router.post("/{project_id}/vote", response_model=VoteResponse)
def submit_vote(
    project_id: int,
    body: VoteSubmit,
    db: Session = Depends(get_db),
    user_id: int = Depends(require_user_id),
):
    """Submit peer vote (1-5). No self-vote, one vote per member. Valid during voting window."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    now = datetime.utcnow()
    if now < project.deadline_contribution:
        raise HTTPException(status_code=400, detail="Voting not open yet")
    if now > project.deadline_voting:
        raise HTTPException(status_code=400, detail="Voting deadline passed")
    voter_member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    ).first()
    if not voter_member:
        raise HTTPException(status_code=403, detail="Not a project member")
    target = db.query(ProjectMember).filter(
        ProjectMember.id == body.member_id,
        ProjectMember.project_id == project_id,
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")
    if target.user_id == user_id:
        raise HTTPException(status_code=400, detail="Self voting not allowed")
    existing = db.query(Vote).filter(
        Vote.project_id == project_id,
        Vote.voter_id == user_id,
        Vote.member_id == body.member_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already voted for this member")
    vote = Vote(
        project_id=project_id,
        voter_id=user_id,
        member_id=body.member_id,
        score=body.score,
    )
    db.add(vote)
    db.commit()
    db.refresh(vote)
    return VoteResponse(
        id=vote.id,
        project_id=vote.project_id,
        voter_id=vote.voter_id,
        member_id=vote.member_id,
        score=vote.score,
        created_at=vote.created_at,
    )


@router.post("/{project_id}/finalize")
def finalize_project_route(
    project_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(require_user_id),
):
    """Compute final scores, call contract finalize, store hashes. Creator only."""
    project = db.query(Project).options(
        joinedload(Project.members).joinedload(ProjectMember.user),
        joinedload(Project.git_metrics),
        joinedload(Project.votes),
    ).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    creator_member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
        ProjectMember.role == "owner",
    ).first()
    if not creator_member:
        raise HTTPException(status_code=403, detail="Only project creator can finalize")
    if datetime.utcnow() < project.deadline_voting:
        raise HTTPException(status_code=400, detail="Cannot finalize before voting deadline")
    if project.status == "finalized":
        return {"status": "already_finalized", "project_id": project_id}

    metrics_json = (project.git_metrics and project.git_metrics.metrics_json) or {}
    votes_by_member: dict[int, List[int]] = {}
    for v in project.votes:
        votes_by_member.setdefault(v.member_id, []).append(v.score)

    results = []
    for member in project.members:
        username = member.user.github_username
        m_metrics = metrics_json.get(username, {})
        code_score = float(m_metrics.get("code_score_raw") or 0)
        time_score = float(m_metrics.get("time_score_raw") or 0)
        peer_scores = votes_by_member.get(member.id) or []
        peer_score = compute_peer_vote_score(peer_scores)
        final_score = compute_final_score(
            code_score,
            time_score,
            peer_score,
            project.weight_code,
            project.weight_time,
            project.weight_vote,
        )
        score_hash_str = hash_score(code_score, time_score, peer_score, final_score)
        results.append({
            "member": member,
            "code_score": code_score,
            "time_score": time_score,
            "peer_score": peer_score,
            "final_score": final_score,
            "score_hash": score_hash_str,
        })

    if project.contract_app_id and settings.CREATOR_MNEMONIC:
        try:
            finalize_project(settings.CREATOR_MNEMONIC, project.contract_app_id)
        except Exception:
            pass
    for r in results:
        fs = FinalScore(
            project_id=project_id,
            member_id=r["member"].id,
            code_score=r["code_score"],
            time_score=r["time_score"],
            peer_score=r["peer_score"],
            final_score=r["final_score"],
            score_hash=r["score_hash"],
        )
        db.add(fs)
    project.status = "finalized"
    db.commit()
    return {"status": "finalized", "project_id": project_id, "scores": len(results)}


@router.get("/{project_id}/dashboard", response_model=DashboardResponse)
def dashboard(
    project_id: int,
    db: Session = Depends(get_db),
    user_id: Optional[int] = Depends(optional_user_id),
):
    """Leaderboard, breakdown, timeline data, on-chain proof link."""
    project = db.query(Project).options(
        joinedload(Project.members).joinedload(ProjectMember.user),
        joinedload(Project.final_scores),
    ).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    scores = {s.member_id: s for s in project.final_scores}
    leaderboard = []
    for i, m in enumerate(sorted(project.members, key=lambda x: (scores.get(x.id).final_score if scores.get(x.id) else 0), reverse=True)):
        s = scores.get(m.id)
        if not s:
            continue
        leaderboard.append(
            LeaderboardEntry(
                rank=i + 1,
                member_id=m.id,
                github_username=m.user.github_username,
                wallet_address=m.user.wallet_address,
                final_score=s.final_score,
                code_score=s.code_score,
                time_score=s.time_score,
                peer_score=s.peer_score,
            )
        )
    # Timeline: placeholder; could aggregate from git_metrics per-day
    timeline_data = None
    my_reputation = None
    return DashboardResponse(
        project=ProjectResponse(
            id=project.id,
            name=project.name,
            repo_url=project.repo_url,
            weight_code=project.weight_code,
            weight_time=project.weight_time,
            weight_vote=project.weight_vote,
            deadline_contribution=project.deadline_contribution,
            deadline_voting=project.deadline_voting,
            status=project.status,
            contract_app_id=project.contract_app_id,
            contract_address=project.contract_address,
            created_at=project.created_at,
            members=[_member_response(m) for m in project.members],
        ),
        leaderboard=leaderboard,
        timeline_data=timeline_data,
        my_reputation=my_reputation,
    )


@router.get("/{project_id}/scores", response_model=List[FinalScoreResponse])
def get_final_scores(
    project_id: int,
    db: Session = Depends(get_db),
):
    """Get final scores for a project (after finalization)."""
    project = db.query(Project).options(
        joinedload(Project.members).joinedload(ProjectMember.user),
        joinedload(Project.final_scores),
    ).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    out = []
    for s in project.final_scores:
        m = next((x for x in project.members if x.id == s.member_id), None)
        if not m:
            continue
        out.append(
            FinalScoreResponse(
                member_id=m.id,
                github_username=m.user.github_username,
                wallet_address=m.user.wallet_address,
                code_score=s.code_score,
                time_score=s.time_score,
                peer_score=s.peer_score,
                final_score=s.final_score,
                score_hash=s.score_hash,
                reputation_minted=s.reputation_minted,
            )
        )
    return out
