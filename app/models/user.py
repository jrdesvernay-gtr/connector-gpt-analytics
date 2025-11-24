"""User model."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Made nullable for Google OAuth users
    google_id = Column(String(255), unique=True, nullable=True, index=True)  # Google user ID
    is_google_user = Column(Boolean, default=False, nullable=False)  # Track auth method
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    workspaces = relationship("Workspace", back_populates="user", cascade="all, delete-orphan")

