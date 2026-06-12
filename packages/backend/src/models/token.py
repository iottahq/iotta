"""
models/token.py – Scoped API token for device access.

A token belongs to a group and grants fine-grained access to specific devices
and actions. Token values are never stored — only their SHA-256 hash.

Token format: iotta_sk_<64 hex chars>
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.database import Base

TOKEN_PREFIX = "iotta_sk_"


def generate_raw_token() -> str:
    """Generate a new raw token. Only returned to the user on create/rotate — never stored."""
    return TOKEN_PREFIX + secrets.token_hex(32)


def hash_token(raw: str) -> str:
    """SHA-256 hash of the raw token, used for DB lookup."""
    return hashlib.sha256(raw.encode()).hexdigest()


class Token(Base):
    __tablename__ = "tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    group_id = Column(
        UUID(as_uuid=True),
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    group = relationship("Group", back_populates="tokens")
    devices = relationship("TokenDevice", back_populates="token", cascade="all, delete-orphan")


class TokenDevice(Base):
    """Per-device permission entry for a token."""

    __tablename__ = "token_devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tokens.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    # ["*"] = all actions, or an explicit list of action names e.g. ["print", "status"]
    allowed_actions = Column(JSON, nullable=False)

    token = relationship("Token", back_populates="devices")

    __table_args__ = (
        UniqueConstraint("token_id", "device_id", name="uq_token_device"),
    )
