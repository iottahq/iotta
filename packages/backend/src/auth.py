"""
auth.py – Bearer token auth for the iotta API.

Reads the token from the environment variable IOTTA_API_TOKEN.
Set it in your .env file (see .env.example).

Every request must include:
    Authorization: Bearer <token>
"""

import os
import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer()

_TOKEN = os.getenv("IOTTA_API_TOKEN", "")


def check_token_configured() -> None:
    if not _TOKEN or _TOKEN == "changeme":
        raise RuntimeError(
            "IOTTA_API_TOKEN is not set or still 'changeme'. "
            "Copy .env.example to .env and set a secure token. "
            "Generate one with: openssl rand -hex 32"
        )


def require_auth(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> None:
    if not secrets.compare_digest(
        credentials.credentials.encode("utf-8"),
        _TOKEN.encode("utf-8"),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
