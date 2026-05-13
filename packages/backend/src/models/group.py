"""
models/group.py – Device group with an associated API token.

The token is stored encrypted using IOTTA_SECRET_KEY.
It is returned in plaintext only via the API (GET /groups/{id}/token).
"""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.database import Base


class Group(Base):
    __tablename__ = "groups"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name       = Column(String, nullable=False)
    token      = Column(String, nullable=False)  # encrypted
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    devices = relationship("Device", back_populates="group")