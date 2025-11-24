"""Pydantic schemas for User model."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
import uuid


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr


class UserCreate(UserBase):
    """Schema for creating a user."""
    password: str


class UserResponse(UserBase):
    """Schema for user response."""
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """Schema for access token response."""
    access_token: str
    token_type: str = "bearer"

