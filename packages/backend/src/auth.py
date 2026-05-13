"""
auth.py – Bearer token authentication for the iotta API.

Two token types:

1. Admin token (IOTTA_ADMIN_TOKEN in .env)  → full access to everything
2. Group token (stored encrypted in groups)  → access only to devices in that group

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

security = HTTPBearer()

_ADMIN_TOKEN = os.getenv("IOTTA_ADMIN_TOKEN", "")


def check_auth_configured() -> None:
    if not _ADMIN_TOKEN or _ADMIN_TOKEN == "changeme":
        raise RuntimeError(
            "IOTTA_ADMIN_TOKEN is not set or still 'changeme'. "
            "Copy .env.example to .env and generate a token with: openssl rand -hex 32"
        )


def require_auth(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db),
) -> Group | None:
    """
    Validates the Bearer token.
    Returns None for admin, or the matching Group for group tokens.
    Raises 401 if no match.
    """
    token = credentials.credentials

    # 1. Admin token → full access
    if _ADMIN_TOKEN and secrets.compare_digest(token.encode(), _ADMIN_TOKEN.encode()):
        return None

    # 2. Group token → scoped access
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
