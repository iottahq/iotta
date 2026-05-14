"""
routers/auth.py – Authentication endpoints for iotta.

Endpoints:
  GET  /auth/setup/status  → { configured: bool }  (no auth required)
  POST /auth/setup         → creates the first admin user (no auth required)
  POST /auth/login         → returns a JWT access token
  GET  /auth/me            → returns the current user (JWT required)
"""

import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

_bearer = HTTPBearer()

# ── Crypto ─────────────────────────────────────────────────────────────────────

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def _secret_key() -> str:
    key = os.getenv("IOTTA_SECRET_KEY", "")
    if not key:
        raise RuntimeError("IOTTA_SECRET_KEY is not set")
    return key


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _create_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        _secret_key(),
        algorithm=JWT_ALGORITHM,
    )


def decode_token(token: str) -> str | None:
    """Decode a JWT and return the user id (sub), or None if invalid."""
    try:
        payload = jwt.decode(token, _secret_key(), algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


# ── Helpers ────────────────────────────────────────────────────────────────────


def _admin_exists(db: Session) -> bool:
    return db.query(User).first() is not None


# ── Schemas ────────────────────────────────────────────────────────────────────


class SetupRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: str
    is_admin: bool

    class Config:
        from_attributes = True


class SetupStatus(BaseModel):
    configured: bool


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.get("/setup/status", response_model=SetupStatus)
def setup_status(db: Session = Depends(get_db)):
    """Returns whether an admin user has already been created. No auth required."""
    return SetupStatus(configured=_admin_exists(db))


@router.post("/setup", response_model=TokenResponse, status_code=201)
def setup(body: SetupRequest, db: Session = Depends(get_db)):
    """
    Create the initial admin user.
    Fails with 409 if any user already exists.
    No auth required.
    """
    if _admin_exists(db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Setup has already been completed.",
        )

    if len(body.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters.",
        )

    user = User(
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email.lower(),
        hashed_password=_hash_password(body.password),
        is_admin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(access_token=_create_token(str(user.id)))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email + password, returns a JWT."""
    user = db.query(User).filter(User.email == body.email.lower()).first()

    if not user or not _verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    return TokenResponse(access_token=_create_token(str(user.id)))


@router.get("/me", response_model=UserRead)
def me(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
    db: Session = Depends(get_db),
):
    """Returns the currently authenticated user. Requires a valid JWT."""
    user_id = decode_token(credentials.credentials)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
