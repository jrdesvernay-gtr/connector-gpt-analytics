"""Session management utilities for web authentication."""

from typing import Optional
from fastapi import Request, Response
from datetime import datetime, timedelta
import secrets
import json
from urllib.parse import urlencode

from app.config import get_settings

settings = get_settings()

# Session cookie settings
SESSION_COOKIE_NAME = "ga_connector_session"
SESSION_MAX_AGE = 86400 * 30  # 30 days


def create_session_token() -> str:
    """Create a new session token."""
    return secrets.token_urlsafe(32)


def set_session_cookie(response: Response, session_token: str, user_id: str):
    """
    Set a session cookie in the response.
    
    Args:
        response: FastAPI Response object
        session_token: Session token to store
        user_id: User ID to associate with session
    """
    # In production, you'd store this in Redis or database
    # For now, we'll encode basic info in the cookie itself (not ideal for production)
    session_data = {
        "token": session_token,
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    # Set secure HTTP-only cookie
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=json.dumps(session_data),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=True,  # Only send over HTTPS
        samesite="lax",  # Allow cross-site requests from ChatGPT
        path="/",
    )


def get_session_from_request(request: Request) -> Optional[dict]:
    """
    Get session data from request cookie.
    
    Returns:
        Session data dict or None if no session
    """
    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_cookie:
        return None
    
    try:
        session_data = json.loads(session_cookie)
        return session_data
    except (json.JSONDecodeError, KeyError):
        return None


def clear_session(response: Response):
    """Clear the session cookie."""
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        samesite="lax",
    )


def store_oauth_state(response: Response, redirect_uri: str, state: Optional[str], workspace_id: Optional[str] = None):
    """
    Store OAuth flow state in session cookie.
    This allows us to resume the OAuth flow after login.
    """
    session_data = {
        "oauth_flow": {
            "redirect_uri": redirect_uri,
            "state": state,
            "workspace_id": workspace_id,
            "created_at": datetime.utcnow().isoformat(),
        }
    }
    
    # Append to existing session or create new
    # In production, store in database/Redis
    
    # For now, we'll store it in a separate cookie
    response.set_cookie(
        key="oauth_state",
        value=json.dumps(session_data),
        max_age=600,  # 10 minutes
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )


def get_oauth_state(request: Request) -> Optional[dict]:
    """Get stored OAuth flow state."""
    state_cookie = request.cookies.get("oauth_state")
    if not state_cookie:
        return None
    
    try:
        state_data = json.loads(state_cookie)
        return state_data.get("oauth_flow")
    except (json.JSONDecodeError, KeyError):
        return None


def build_authorize_url(redirect_uri: str, state: Optional[str] = None, workspace_id: Optional[str] = None) -> str:
    """Build the authorize-gpt URL with all parameters."""
    params = {
        "redirect_uri": redirect_uri,
    }
    if state:
        params["state"] = state
    if workspace_id:
        params["workspace_id"] = workspace_id
    
    return f"{settings.APP_BASE_URL}/authorize-gpt?{urlencode(params)}"


