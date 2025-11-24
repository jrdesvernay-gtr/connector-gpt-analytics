"""Google OAuth service for user authentication."""

from typing import Optional, Dict, Any
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import google.auth.exceptions
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.user import User
from app.models.workspace import Workspace

settings = get_settings()


class GoogleOAuthService:
    """Service for Google OAuth authentication."""
    
    @staticmethod
    def get_authorization_url(state: Optional[str] = None) -> str:
        """
        Generate Google OAuth authorization URL.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL
        """
        from google_auth_oauthlib.flow import Flow
        
        # Scopes for user profile (signup/login)
        scopes = [
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "openid",
        ]
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                }
            },
            scopes=scopes,
        )
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="false",  # Don't include previously granted scopes
            state=state,
            prompt="select_account consent",  # Select account AND force fresh consent (user auth only)
        )
        
        return authorization_url
    
    @staticmethod
    def verify_google_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify Google ID token and extract user info.
        
        Args:
            token: Google ID token
            
        Returns:
            User info dict with email, name, google_id, or None if invalid
        """
        try:
            # Verify the token
            idinfo = id_token.verify_oauth2_token(
                token,
                Request(),
                settings.GOOGLE_CLIENT_ID,
            )
            
            # Check issuer
            if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
                return None
            
            return {
                "email": idinfo.get("email"),
                "name": idinfo.get("name"),
                "google_id": idinfo.get("sub"),
                "picture": idinfo.get("picture"),
            }
        except (ValueError, google.auth.exceptions.GoogleAuthError):
            return None
    
    @staticmethod
    def exchange_code_for_token(code: str) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for user info.
        
        Args:
            code: Authorization code from Google
            
        Returns:
            User info dict or None if exchange fails
        """
        from google_auth_oauthlib.flow import Flow
        
        scopes = [
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "openid",
        ]
        
        # Ensure redirect URI matches exactly
        redirect_uri = settings.GOOGLE_REDIRECT_URI
        print(f"DEBUG (user auth exchange): Using redirect_uri: {redirect_uri}")
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri],
                }
            },
            scopes=scopes,
        )
        flow.redirect_uri = redirect_uri
        
        try:
            print(f"DEBUG (user auth exchange): Attempting to exchange code")
            print(f"DEBUG (user auth exchange): redirect_uri on flow: {flow.redirect_uri}")
            print(f"DEBUG (user auth exchange): redirect_uri from settings: {redirect_uri}")
            print(f"DEBUG (user auth exchange): client_id: {settings.GOOGLE_CLIENT_ID[:20]}...")
            print(f"DEBUG (user auth exchange): code length: {len(code)}")
            
            # Ensure redirect_uri is set on flow
            flow.redirect_uri = redirect_uri
            
            # Fetch token - don't pass redirect_uri again, use the one set on flow
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            if not credentials:
                print("ERROR: No credentials returned from token exchange")
                return None
            
            print(f"DEBUG: Got credentials, id_token: {'Yes' if credentials.id_token else 'No'}")
            
            # Get user info using access token
            if credentials.id_token:
                # Verify ID token
                user_info = GoogleOAuthService.verify_google_token(credentials.id_token)
                if user_info:
                    print(f"DEBUG: Got user info from ID token: {user_info.get('email')}")
                    return user_info
            
            # If no ID token or verification failed, use userinfo endpoint
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            
            creds = Credentials(
                token=credentials.token,
                refresh_token=credentials.refresh_token if hasattr(credentials, 'refresh_token') else None,
                token_uri=credentials.token_uri,
                client_id=credentials.client_id,
                client_secret=credentials.client_secret,
                scopes=credentials.scopes,
            )
            
            print("DEBUG: Fetching user info from userinfo endpoint...")
            service = build("oauth2", "v2", credentials=creds)
            user_info = service.userinfo().get().execute()
            
            result = {
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "google_id": user_info.get("id"),
                "picture": user_info.get("picture"),
            }
            print(f"DEBUG: Got user info from userinfo endpoint: {result.get('email')}")
            return result
        except Exception as e:
            error_msg = f"ERROR in exchange_code_for_token (user auth): {type(e).__name__}: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            # Re-raise the exception so the caller can see the actual error
            raise Exception(f"Failed to exchange code for token: {str(e)}") from e
    
    @staticmethod
    def get_or_create_user_from_google(
        db: Session,
        google_user_info: Dict[str, Any],
    ) -> User:
        """
        Get existing user or create new user from Google OAuth info.
        
        Args:
            db: Database session
            google_user_info: User info from Google (email, google_id, name, picture)
            
        Returns:
            User object
        """
        email = google_user_info.get("email")
        google_id = google_user_info.get("google_id")
        
        if not email or not google_id:
            raise ValueError("Missing required Google user information")
        
        # Try to find user by Google ID first
        user = db.query(User).filter(User.google_id == google_id).first()
        
        if user:
            # Update email if it changed
            if user.email != email:
                user.email = email
                db.commit()
                db.refresh(user)
            return user
        
        # Try to find user by email (might be existing user linking Google account)
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            # Link Google account to existing user
            user.google_id = google_id
            user.is_google_user = True
            db.commit()
            db.refresh(user)
            return user
        
        # Create new user
        user = User(
            email=email,
            google_id=google_id,
            is_google_user=True,
            password_hash=None,  # No password for Google users
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Create default workspace
        workspace = Workspace(
            user_id=user.id,
            name="My Workspace",
        )
        db.add(workspace)
        db.commit()
        
        return user

