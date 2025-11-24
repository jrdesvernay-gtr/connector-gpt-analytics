"""Configuration management using pydantic-settings."""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = Field(
        ..., description="PostgreSQL database connection URL"
    )

    # Security
    SECRET_KEY: str = Field(
        ..., description="Secret key for JWT token signing"
    )
    ENCRYPTION_KEY: str = Field(
        ..., description="Fernet encryption key for GA refresh tokens"
    )

    # Google OAuth
    GOOGLE_CLIENT_ID: str = Field(
        ..., description="Google OAuth client ID"
    )
    GOOGLE_CLIENT_SECRET: str = Field(
        ..., description="Google OAuth client secret"
    )
    GOOGLE_REDIRECT_URI: str = Field(
        ..., description="Google OAuth redirect URI"
    )

    # Application
    APP_BASE_URL: str = Field(
        default="http://localhost:8000",
        description="Base URL of the application"
    )
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment (development, staging, production)"
    )

    # JWT settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60,
        description="Access token expiration time in minutes"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=90,
        description="Refresh token expiration time in days"
    )
    
    # Server settings
    PORT: int = Field(
        default=8000,
        description="Server port (defaults to 8000, can be overridden by PORT env var)"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

