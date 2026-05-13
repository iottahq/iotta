"""
models/device.py – Registered device.
"""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.database import Base


class Device(Base):
    __tablename__ = "devices"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name          = Column(String, nullable=False)
    plugin_id     = Column(String, nullable=False)
    credential_id = Column(UUID(as_uuid=True), ForeignKey("credentials.id"), nullable=False)
    group_id      = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=True)
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    credential = relationship("Credential", back_populates="devices")
    group      = relationship("Group", back_populates="devices")