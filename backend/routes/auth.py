"""
Authentication routes: GitHub OAuth, wallet link, JWT.
"""
from datetime import datetime, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Header
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
from models import User
from schemas import UserResponse, UserWalletLink
from firebase_service import firebase_service

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def _get_bearer_token(authorization: Optional[str] = Header(None)) -> Optional[str]:
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


def get_current_user_id(
    token: Optional[str] = Depends(_get_bearer_token),
    db: Session = Depends(get_db),
) -> Optional[int]:
    """Decode JWT and return user id; returns None if invalid/missing."""
    if not token:
        return None
    try:
        settings = get_settings()
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        uid = payload.get("sub")
        return int(uid) if uid else None
    except JWTError:
        return None


def require_user_id(
    token: Optional[str] = Depends(_get_bearer_token),
    db: Session = Depends(get_db),
) -> int:
    """Require valid JWT; raise 401 if missing/invalid."""
    uid = get_current_user_id(token, db)
    if uid is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return uid


def optional_user_id(
    token: Optional[str] = Depends(_get_bearer_token),
    db: Session = Depends(get_db),
) -> Optional[int]:
    """Return user id if valid JWT present, else None."""
    return get_current_user_id(token, db)


class GitHubCallbackQuery(BaseModel):
    code: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


@router.get("/github")
async def github_login_redirect():
    """Redirect URL for GitHub OAuth. Frontend redirects here or uses link."""
    settings = get_settings()
    return {
        "url": f"https://github.com/login/oauth/authorize?client_id={settings.GITHUB_CLIENT_ID}&redirect_uri={settings.GITHUB_CALLBACK_URL}&scope=read:user"
    }


@router.get("/github/callback")
async def github_callback(code: str, db: Session = Depends(get_db)):
    """Exchange code for token, fetch user, create/update DB user, return JWT."""
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
    data = r.json()
    access_token_github = data.get("access_token")
    if not access_token_github:
        raise HTTPException(status_code=400, detail="GitHub OAuth failed")

    async with httpx.AsyncClient() as client:
        r2 = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token_github}"},
        )
    gh_user = r2.json()
    github_id = str(gh_user.get("id"))
    github_username = gh_user.get("login", "unknown")
    avatar_url = gh_user.get("avatar_url")

    user = db.query(User).filter(User.github_id == github_id).first()
    if not user:
        user = User(
            github_id=github_id,
            github_username=github_username,
            avatar_url=avatar_url,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.github_username = github_username
        user.avatar_url = avatar_url
        db.commit()
        db.refresh(user)

    # Sync user data to Firebase
    user_data_for_firebase = {
        "id": user.id,
        "github_id": user.github_id,
        "github_username": user.github_username,
        "avatar_url": user.avatar_url or "",
        "wallet_address": user.wallet_address or None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "synced_at": datetime.utcnow().isoformat(),
    }
    firebase_service.create_user_in_firestore(user.id, user_data_for_firebase)

    jwt_token = create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=jwt_token,
        user=UserResponse(
            id=user.id,
            github_id=user.github_id,
            github_username=user.github_username,
            avatar_url=user.avatar_url,
            wallet_address=user.wallet_address,
            created_at=user.created_at,
        ),
    )


@router.post("/wallet", response_model=UserResponse)
def link_wallet(
    body: UserWalletLink,
    db: Session = Depends(get_db),
    user_id: int = Depends(require_user_id),
):
    """Link Algorand wallet address to current user. Validates format."""
    from algosdk import encoding
    if not encoding.is_valid_address(body.wallet_address):
        raise HTTPException(status_code=400, detail="Invalid Algorand address")
    existing = db.query(User).filter(User.wallet_address == body.wallet_address).first()
    if existing and existing.id != user_id:
        raise HTTPException(status_code=400, detail="Wallet already linked to another account")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.wallet_address = body.wallet_address
    db.commit()
    db.refresh(user)
    return UserResponse(
        id=user.id,
        github_id=user.github_id,
        github_username=user.github_username,
        avatar_url=user.avatar_url,
        wallet_address=user.wallet_address,
        created_at=user.created_at,
    )


@router.get("/me", response_model=UserResponse)
def me(db: Session = Depends(get_db), user_id: int = Depends(require_user_id)):
    """Current user info."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user.id,
        github_id=user.github_id,
        github_username=user.github_username,
        avatar_url=user.avatar_url,
        wallet_address=user.wallet_address,
        created_at=user.created_at,
    )
