"""Pydantic schemas for GPT OAuth related models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import uuid


class WorkspaceBase(BaseModel):
    """Base workspace schema."""
    name: str


class WorkspaceCreate(WorkspaceBase):
    """Schema for creating a workspace."""
    pass


class WorkspaceResponse(WorkspaceBase):
    """Schema for workspace response."""
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class GPTTokenCreate(BaseModel):
    """Schema for creating a GPT token."""
    workspace_id: uuid.UUID
    scope: str = "read"


class GPTTokenResponse(BaseModel):
    """Schema for GPT token response."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: str
    scope: str

    class Config:
        from_attributes = True


class OAuthTokenRequest(BaseModel):
    """Schema for OAuth token request (refresh grant)."""
    grant_type: str
    refresh_token: str
    client_id: Optional[str] = None


class OAuthAuthorizeRequest(BaseModel):
    """Schema for OAuth authorization request."""
    response_type: str = "code"
    client_id: str
    redirect_uri: str
    scope: str
    state: Optional[str] = None

