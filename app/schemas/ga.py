"""Pydantic schemas for GA4 related models."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import uuid


class GAConnectionBase(BaseModel):
    """Base GA connection schema."""
    google_account_email: str
    property_id: str
    property_name: str


class GAConnectionCreate(GAConnectionBase):
    """Schema for creating a GA connection."""
    refresh_token: str  # Will be encrypted before storage


class GAConnectionResponse(GAConnectionBase):
    """Schema for GA connection response."""
    id: uuid.UUID
    workspace_id: uuid.UUID
    last_synced_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class Property(BaseModel):
    """Schema for GA4 property."""
    property_id: str
    property_name: str
    account_name: Optional[str] = None


class PropertyList(BaseModel):
    """Schema for list of properties."""
    properties: List[Property]


class GAReportRequest(BaseModel):
    """Schema for GA report request."""
    date_ranges: List[Dict[str, str]]
    metrics: List[str]
    dimensions: Optional[List[str]] = None
    property_id: Optional[str] = None  # If not provided, use workspace default


class GAReportResponse(BaseModel):
    """Schema for GA report response."""
    rows: List[Dict[str, Any]]
    totals: Optional[Dict[str, Any]] = None
    row_count: int

