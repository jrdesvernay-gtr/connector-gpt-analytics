"""Google OAuth authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from typing import Optional
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
import secrets

from app.database import get_db
from app.schemas.user import Token
from app.services.google_oauth_service import GoogleOAuthService
from app.core.security import create_access_token
from app.config import get_settings
import logging

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)


@router.get("/google/login")
async def google_login(request: Request, next: Optional[str] = Query(None, alias="next")):
    """
    Initiate Google OAuth login flow.
    Redirects user to Google for authentication.
    
    Args:
        next: Optional URL to redirect to after successful login (URL-encoded)
    
    Visit this endpoint to start the Google OAuth login process.
    """
    from urllib.parse import urlencode, parse_qs
    import base64
    import json
    
    # Generate state for CSRF protection
    csrf_token = secrets.token_urlsafe(32)
    
    # If next URL provided, encode it in the state so we can retrieve it after callback
    # Format: base64(json({csrf: "...", next: "..."}))
    state_data = {"csrf": csrf_token}
    if next:
        state_data["next"] = next
    
    # Encode state as base64 JSON
    state_json = json.dumps(state_data)
    state = base64.urlsafe_b64encode(state_json.encode()).decode()
    
    authorization_url = GoogleOAuthService.get_authorization_url(state=state)
    
    return RedirectResponse(url=authorization_url)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None,
    db: Session = Depends(get_db),
):
    """
    Handle Google OAuth callback.
    Exchanges authorization code for user info and creates/logs in user.
    
    Returns redirect with JWT token.
    In production, you'd redirect to your frontend with the token.
    """
    print(f"DEBUG: User auth callback received")
    print(f"DEBUG: Full callback URL: {request.url}")
    print(f"DEBUG: Query params: code={'Yes' if code else 'No'}, state={state}, error={error}")
    print(f"DEBUG: Expected redirect URI: {settings.GOOGLE_REDIRECT_URI}")
    
    # Check if Google returned an error
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth error: {error}",
        )
    
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code",
        )
    
    print(f"DEBUG: Exchanging code for user info...")
    # Exchange code for user info
    try:
        google_user_info = GoogleOAuthService.exchange_code_for_token(code)
    except Exception as e:
        import traceback
        error_detail = f"Error exchanging code for token: {str(e)}"
        print(f"User Auth Callback Error: {error_detail}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail,
        )
    
    if not google_user_info:
        print("ERROR: google_user_info is None after exchange")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code or invalid token. Check server logs for details.",
        )
    
    print(f"DEBUG: Got user info successfully: {google_user_info.get('email')}")
    
    # Get or create user
    try:
        user = GoogleOAuthService.get_or_create_user_from_google(db, google_user_info)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    # Create JWT token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    # Extract 'next' URL from state if present
    next_url = None
    if state:
        try:
            import base64
            import json
            # Decode state to get next URL
            # State format: base64(json({csrf: "...", next: "..."}))
            state_json = base64.urlsafe_b64decode(state.encode()).decode()
            state_data = json.loads(state_json)
            next_url = state_data.get("next")
            logger.debug(f"Extracted next_url from state: {next_url}")
        except (ValueError, json.JSONDecodeError, Exception) as e:
            logger.debug(f"Could not decode state (this is OK if no next URL was provided): {e}")
            # If state decode fails, it might be a simple state token without next URL
            # This is OK - we'll just redirect to default success page
            pass
    
    # If we have a next URL, redirect there with token
    if next_url:
        # URL-decode next_url if it was URL-encoded
        from urllib.parse import unquote
        try:
            next_url = unquote(next_url)
        except Exception:
            pass  # If unquote fails, use as-is
        
        # Append token to next URL
        from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
        parsed = urlparse(next_url)
        query_params = parse_qs(parsed.query)
        query_params['token'] = [access_token]
        new_query = urlencode(query_params, doseq=True)
        redirect_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
        logger.info(f"Redirecting to next URL with token: {redirect_url[:100]}...")
        return RedirectResponse(url=redirect_url, status_code=302)
    
    # Default: redirect to success page
    logger.debug("No next URL found, redirecting to success page")
    redirect_url = f"{settings.APP_BASE_URL}/auth/google/success?token={access_token}"
    return RedirectResponse(url=redirect_url, status_code=302)


@router.get("/google/success")
async def google_success(token: str):
    """
    Success page after Google OAuth.
    Returns JSON with token for API use.
    In production, this would be a frontend page that handles the token.
    """
    return JSONResponse(
        content={
            "message": "Google login successful",
            "access_token": token,
            "token_type": "bearer",
            "instructions": "Use this token in the Authorization header: Bearer <token>",
        }
    )

