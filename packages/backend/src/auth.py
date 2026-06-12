"""
auth.py – Bearer token authentication for the iotta management API.

Three token types (in order of precedence):

1. JWT (issued by POST /auth/login or POST /auth/setup)
   → full admin access
2. Admin token (IOTTA_ADMIN_TOKEN in .env)
   → full access, API-client fallback
3. Scoped token (iotta_sk_*)
   → rejected here; only valid on device sub-apps (see device_manager.py)

Every management request must include:
    Authorization: Bearer <token>
"""

import os
import secrets

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.token import TOKEN_PREFIX
from src.models.user import User

security = HTTPBearer()

_ADMIN_TOKEN = os.getenv("IOTTA_ADMIN_TOKEN", "")


def _decode_jwt(token: str, db: Session) -> User | None:
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
) -> None:
    """
    Validates the Bearer token for management endpoints.

    Accepts JWT or static admin token → returns None (admin access).
    Scoped tokens (iotta_sk_*) are explicitly rejected here — they are
    only valid on device sub-apps.

    Raises 401/403 if no valid token is found.
    """
    token = credentials.credentials

    user = _decode_jwt(token, db)
    if user:
        return None

    if _ADMIN_TOKEN and secrets.compare_digest(token.encode(), _ADMIN_TOKEN.encode()):
        return None

    if token.startswith(TOKEN_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Scoped tokens cannot access management endpoints. Use a JWT.",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    user = _decode_jwt(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
