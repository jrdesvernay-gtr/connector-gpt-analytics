"""GA Connection model."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class GAConnection(Base):
    """Google Analytics connection model."""

    __tablename__ = "ga_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    google_account_email = Column(String(255), nullable=False)
    property_id = Column(String(255), nullable=False, index=True)
    property_name = Column(String(255), nullable=False)
    refresh_token_encrypted = Column(String(2048), nullable=False)  # Encrypted Google refresh token
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)  # Track when connection was last modified

    # Relationships
    workspace = relationship("Workspace", back_populates="ga_connections")

