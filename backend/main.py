"""
TrustChain Backend - FastAPI application.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import engine, Base
from models import User, Project, ProjectMember, GitMetrics, Vote, FinalScore  # noqa: F401 - register models
from routes import auth, projects

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TrustChain API",
    description="Trustless Group Contribution Evaluation Platform",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(projects.router)


@app.get("/")
def root():
    return {"app": "TrustChain", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
