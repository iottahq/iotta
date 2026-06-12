"""
models/group.py – Device group.

Groups bundle devices together. Access is controlled via scoped tokens
(see models/token.py), not a single group-level token.
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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    devices = relationship("Device", back_populates="group")
    tokens  = relationship("Token", back_populates="group", cascade="all, delete-orphan")
