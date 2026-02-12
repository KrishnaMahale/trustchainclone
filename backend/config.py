"""
TrustChain backend configuration.
Uses environment variables for all secrets and URLs.
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment."""

    # App
    APP_NAME: str = "TrustChain"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://trustchain:trustchain@localhost:5432/trustchain"

    # JWT
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # GitHub OAuth
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_CALLBACK_URL: str = "http://localhost:3000/auth/callback"

    # Algorand TestNet
    ALGOD_URL: str = "https://testnet-api.algonode.cloud"
    ALGOD_TOKEN: str = ""
    INDEXER_URL: str = "https://testnet-idx.algonode.cloud"
    CREATOR_MNEMONIC: str = ""  # For deployment; never expose in frontend

    # Reputation ASA
    REPUTATION_ASA_ID: int = 0  # Set after creation

    # Git clone temp dir
    GIT_CLONE_DIR: str = "/tmp/trustchain_repos"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
