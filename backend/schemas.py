"""
Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ----- User -----
class UserBase(BaseModel):
    github_username: str
    avatar_url: Optional[str] = None
    wallet_address: Optional[str] = None


class UserCreate(UserBase):
    github_id: str


class UserResponse(UserBase):
    id: int
    github_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserWalletLink(BaseModel):
    wallet_address: str


# ----- Project -----
class ProjectCreate(BaseModel):
    name: str
    repo_url: Optional[str] = None
    weight_code: float = Field(ge=0, le=1, description="Weight for code contribution")
    weight_time: float = Field(ge=0, le=1, description="Weight for time consistency")
    weight_vote: float = Field(ge=0, le=1, description="Weight for peer voting")
    deadline_contribution: datetime
    deadline_voting: datetime
    member_wallet_addresses: List[str] = Field(default_factory=list)


class ProjectMemberResponse(BaseModel):
    id: int
    user_id: int
    github_username: str
    wallet_address: Optional[str] = None
    role: str

    class Config:
        from_attributes = True


class ProjectResponse(BaseModel):
    id: int
    name: str
    repo_url: Optional[str] = None
    weight_code: float
    weight_time: float
    weight_vote: float
    deadline_contribution: datetime
    deadline_voting: datetime
    status: str
    contract_app_id: Optional[int] = None
    contract_address: Optional[str] = None
    created_at: datetime
    members: List[ProjectMemberResponse] = []

    class Config:
        from_attributes = True


# ----- Git / Scoring -----
class GitUserMetrics(BaseModel):
    commits: int
    lines_added: int
    lines_removed: int
    files_modified: int
    active_days: int
    total_days: int
    last_day_commits: int
    code_score_raw: Optional[float] = None
    time_score_raw: Optional[float] = None


class AnalyzeResponse(BaseModel):
    project_id: int
    metrics: dict  # github_username -> GitUserMetrics
    last_analyzed_at: Optional[datetime] = None


# ----- Voting -----
class VoteSubmit(BaseModel):
    member_id: int  # project_members.id
    score: int = Field(ge=1, le=5)
    wallet_signature: Optional[str] = None  # For on-chain verification


class VoteResponse(BaseModel):
    id: int
    project_id: int
    voter_id: int
    member_id: int
    score: int
    created_at: datetime

    class Config:
        from_attributes = True


# ----- Final scores -----
class FinalScoreResponse(BaseModel):
    member_id: int
    github_username: str
    wallet_address: Optional[str] = None
    code_score: float
    time_score: float
    peer_score: float
    final_score: float
    score_hash: Optional[str] = None
    reputation_minted: Optional[int] = None


# ----- Dashboard -----
class LeaderboardEntry(BaseModel):
    rank: int
    member_id: int
    github_username: str
    wallet_address: Optional[str] = None
    final_score: float
    code_score: float
    time_score: float
    peer_score: float


class DashboardResponse(BaseModel):
    project: ProjectResponse
    leaderboard: List[LeaderboardEntry]
    timeline_data: Optional[dict] = None  # For Chart.js
    my_reputation: Optional[int] = None
