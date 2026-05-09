from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.database import Base
from datetime import datetime, timezone
import uuid
 
 
class Credential(Base):
    __tablename__ = "credentials"
 
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name       = Column(String, nullable=False)
    data       = Column(JSON, nullable=False)  # { "ip": "...", "access_code": "..." }
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
 
    devices = relationship("Device", back_populates="credential")
