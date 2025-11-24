"""Security utilities for password hashing and JWT tokens."""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets

from app.config import get_settings

settings = get_settings()

# Password hashing context using Argon2
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, token_type: str = "access") -> str:
    """
    Create a JWT token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta
        token_type: Type of token (default: "access")
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": token_type})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def create_refresh_token() -> str:
    """Create an opaque refresh token."""
    return secrets.token_urlsafe(32)


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        return None


def hash_token(token: str) -> str:
    """Hash a token for storage (one-way)."""
    return pwd_context.hash(token)


def verify_token_hash(token: str, hashed_token: str) -> bool:
    """Verify a token against a hash."""
    return pwd_context.verify(token, hashed_token)

