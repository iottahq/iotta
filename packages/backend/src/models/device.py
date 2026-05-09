from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.database import Base
from datetime import datetime, timezone
import uuid


class Device(Base):
    __tablename__ = "devices"
 
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name          = Column(String, nullable=False)
    plugin_id     = Column(String, nullable=False)  # e.g. "bambu-lab-a1"
    credential_id = Column(UUID(as_uuid=True), ForeignKey("credentials.id"), nullable=False)
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
 
    credential = relationship("Credential", back_populates="devices")
