"""Query Log model."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class QueryLog(Base):
    """Query log model for tracking GA queries."""

    __tablename__ = "query_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    gpt_token_id = Column(UUID(as_uuid=True), ForeignKey("gpt_tokens.id"), nullable=True, index=True)
    query_params = Column(JSONB, nullable=False)  # GA query parameters
    response_summary = Column(JSONB, nullable=True)  # Summary of response (rows count, etc.)
    error = Column(Text, nullable=True)  # Error message if query failed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    workspace = relationship("Workspace", back_populates="query_logs")
    gpt_token = relationship("GPTToken", back_populates="query_logs")

