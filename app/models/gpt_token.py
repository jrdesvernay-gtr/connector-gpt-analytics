"""GPT Token model."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class GPTToken(Base):
    """GPT OAuth token model."""

    __tablename__ = "gpt_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    access_token_hash = Column(String(255), nullable=False, index=True)  # Hashed access token
    expires_at = Column(DateTime, nullable=False, index=True)
    scope = Column(String(255), nullable=False, default="read")
    refresh_token = Column(String(255), nullable=False, unique=True, index=True)  # Opaque refresh token
    revoked = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="gpt_tokens")
    query_logs = relationship("QueryLog", back_populates="gpt_token")

