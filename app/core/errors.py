"""Structured error handling for the application."""

from fastapi import HTTPException
from typing import Optional, Dict, Any


class ConnectorError(Exception):
    """Base exception for connector errors."""

    def __init__(
        self,
        error_code: str,
        message: str,
        user_action: Optional[str] = None,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.error_code = error_code
        self.message = message
        self.user_action = user_action
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class GAPropertyNotFoundError(ConnectorError):
    """Error when GA property is not found."""

    def __init__(self, property_id: Optional[str] = None):
        super().__init__(
            error_code="ga_property_not_found",
            message="Google Analytics property not found or unreachable",
            user_action="Reconnect Google Analytics",
            status_code=404,
            details={"property_id": property_id} if property_id else {},
        )


class OAuthTokenRevokedError(ConnectorError):
    """Error when OAuth token is revoked."""

    def __init__(self, token_type: str = "oauth"):
        super().__init__(
            error_code="oauth_token_revoked",
            message=f"{token_type.title()} token has been revoked",
            user_action="Reconnect your account",
            status_code=401,
            details={"token_type": token_type},
        )


class RateLimitExceededError(ConnectorError):
    """Error when rate limit is exceeded."""

    def __init__(self, retry_after: Optional[int] = None):
        super().__init__(
            error_code="rate_limit_exceeded",
            message="API rate limit exceeded",
            user_action="Wait and retry",
            status_code=429,
            details={"retry_after": retry_after} if retry_after else {},
        )


class NoGAConnectionError(ConnectorError):
    """Error when no GA connection exists."""

    def __init__(self):
        super().__init__(
            error_code="no_ga_connection",
            message="No Google Analytics property connected",
            user_action="Connect a Google Analytics property",
            status_code=404,
        )


class InvalidTokenError(ConnectorError):
    """Error when token is invalid or expired."""

    def __init__(self, token_type: str = "access"):
        super().__init__(
            error_code="invalid_token",
            message=f"{token_type.title()} token is expired or invalid",
            user_action="Re-authorize the application",
            status_code=401,
            details={"token_type": token_type},
        )


class ConcurrentRequestError(ConnectorError):
    """Error when duplicate request is detected."""

    def __init__(self):
        super().__init__(
            error_code="concurrent_request",
            message="Duplicate request detected",
            user_action="Wait for the current request to complete",
            status_code=409,
        )


def error_to_http_exception(error: ConnectorError) -> HTTPException:
    """Convert ConnectorError to HTTPException."""
    return HTTPException(
        status_code=error.status_code,
        detail={
            "error_code": error.error_code,
            "message": error.message,
            "user_action": error.user_action,
            "details": error.details,
        },
    )

