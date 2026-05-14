"""
auth.py – Bearer token authentication for the iotta API.

Three token types (in order of precedence):

1. JWT (issued by POST /auth/login or POST /auth/setup)
   → full admin access
2. Admin token (IOTTA_ADMIN_TOKEN in .env)
   → full access, legacy / API-client fallback
3. Group token (stored encrypted in groups)
   → access only to devices in that group

Every request must include:
    Authorization: Bearer <token>
"""

import os
import secrets

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.crypto import decrypt
from src.database import get_db
from src.models.group import Group
from src.models.user import User

security = HTTPBearer()

_ADMIN_TOKEN = os.getenv("IOTTA_ADMIN_TOKEN", "")


def check_auth_configured() -> None:
    # With user-based auth the static token is optional
    pass


def _decode_jwt(token: str, db: Session) -> User | None:
    """Try to decode a JWT and return the corresponding User, or None."""
    try:
        from src.routers.auth import decode_token
        user_id = decode_token(token)
        if not user_id:
            return None
        return db.query(User).filter(User.id == user_id).first()
    except Exception:
        return None


def require_auth(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db),
) -> Group | None:
    """
    Validates the Bearer token.

    Returns:
      - None          → admin access (JWT user or static admin token)
      - Group         → scoped group token access

    Raises 401 if no valid token is found.
    """
    token = credentials.credentials

    # 1. JWT → admin access
    user = _decode_jwt(token, db)
    if user:
        return None

    # 2. Static admin token → full access (legacy / API clients)
    if _ADMIN_TOKEN and secrets.compare_digest(token.encode(), _ADMIN_TOKEN.encode()):
        return None

    # 3. Group token → scoped access
    for group in db.query(Group).all():
        try:
            decrypted = decrypt(group.token)
        except Exception:
            continue
        if secrets.compare_digest(token.encode(), decrypted.encode()):
            return group

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency that requires a valid JWT and returns the User.
    Used by /auth/me and any future user-specific endpoints.
    """
    token = credentials.credentials
    user = _decode_jwt(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user