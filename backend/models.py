"""
TrustChain database models (SQLAlchemy ORM).
"""
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from database import Base


class User(Base):
    """User: GitHub identity + optional Algorand wallet mapping."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    github_id = Column(String(64), unique=True, index=True, nullable=False)
    github_username = Column(String(255), nullable=False)
    avatar_url = Column(String(512), nullable=True)
    wallet_address = Column(String(58), unique=True, index=True, nullable=True)  # Algorand addr
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project_memberships = relationship("ProjectMember", back_populates="user")
    votes_given = relationship("Vote", foreign_keys="Vote.voter_id", back_populates="voter")


class Project(Base):
    """Project with contribution rules and deadlines."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    repo_url = Column(String(512), nullable=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Weights (0–1), stored as decimals e.g. 0.4, 0.3, 0.3
    weight_code = Column(Float, default=0.4, nullable=False)
    weight_time = Column(Float, default=0.3, nullable=False)
    weight_vote = Column(Float, default=0.3, nullable=False)

    deadline_contribution = Column(DateTime, nullable=False)
    deadline_voting = Column(DateTime, nullable=False)

    # Blockchain
    contract_app_id = Column(Integer, nullable=True)
    contract_address = Column(String(58), nullable=True)
    status = Column(String(32), default="draft")  # draft | active | voting | finalized

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    git_metrics = relationship("GitMetrics", back_populates="project", uselist=False)
    votes = relationship("Vote", back_populates="project")
    final_scores = relationship("FinalScore", back_populates="project")


class ProjectMember(Base):
    """Project membership: user + optional contribution target."""

    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(32), default="member")  # owner | member

    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_user"),)

    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="project_memberships")
    votes_received = relationship("Vote", foreign_keys="Vote.member_id", back_populates="member")


class GitMetrics(Base):
    """Git-derived metrics per project (aggregate per user in JSONB)."""

    __tablename__ = "git_metrics"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, unique=True)
    # Per-user metrics: { "github_username": { "commits", "lines_added", ... } }
    metrics_json = Column(JSONB, nullable=False, default=dict)
    last_analyzed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="git_metrics")


class Vote(Base):
    """Peer vote: voter -> member, score 1–5."""

    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    voter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("project_members.id"), nullable=False)
    score = Column(Integer, nullable=False)  # 1-5
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("project_id", "voter_id", "member_id", name="uq_vote_per_pair"),
    )

    project = relationship("Project", back_populates="votes")
    voter = relationship("User", foreign_keys=[voter_id], back_populates="votes_given")
    member = relationship("ProjectMember", foreign_keys=[member_id], back_populates="votes_received")


class FinalScore(Base):
    """Final contribution score per member (after finalization)."""

    __tablename__ = "final_scores"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("project_members.id"), nullable=False)
    code_score = Column(Float, nullable=False)
    time_score = Column(Float, nullable=False)
    peer_score = Column(Float, nullable=False)
    final_score = Column(Float, nullable=False)
    score_hash = Column(String(64), nullable=True)  # SHA256 for on-chain verification
    reputation_minted = Column(Integer, nullable=True)  # ASA amount
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("project_id", "member_id", name="uq_final_score_member"),)

    project = relationship("Project", back_populates="final_scores")
