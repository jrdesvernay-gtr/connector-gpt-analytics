"""Workspace model."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Workspace(Base):
    """Workspace model - represents a user's workspace."""

    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, default="My Workspace")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="workspaces")
    ga_connections = relationship("GAConnection", back_populates="workspace", cascade="all, delete-orphan")
    gpt_tokens = relationship("GPTToken", back_populates="workspace", cascade="all, delete-orphan")
    query_logs = relationship("QueryLog", back_populates="workspace", cascade="all, delete-orphan")

