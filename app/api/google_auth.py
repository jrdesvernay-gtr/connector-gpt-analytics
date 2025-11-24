"""Google OAuth authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
import secrets

from app.database import get_db
from app.schemas.user import Token
from app.services.google_oauth_service import GoogleOAuthService
from app.core.security import create_access_token
from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/google/login")
async def google_login(request: Request):
    """
    Initiate Google OAuth login flow.
    Redirects user to Google for authentication.
    
    Visit this endpoint to start the Google OAuth login process.
    """
    # Generate state for CSRF protection (store in session in production)
    state = secrets.token_urlsafe(32)
    
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
    
    # In production, redirect to frontend with token
    # For now, redirect to success endpoint with token
    redirect_url = f"{settings.APP_BASE_URL}/auth/google/success?token={access_token}"
    
    return RedirectResponse(url=redirect_url)


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

