"""Google Analytics OAuth service for GA4 connection."""

from typing import Optional, Dict, Any, Tuple
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.ga_connection import GAConnection
from app.services.encryption import get_encryption_service

settings = get_settings()


class GAOAuthService:
    """Service for Google Analytics OAuth connection."""
    
    @staticmethod
    def get_authorization_url(workspace_id: str, state: Optional[str] = None, next_url: Optional[str] = None) -> str:
        """
        Generate Google Analytics OAuth authorization URL.
        
        Args:
            workspace_id: Workspace ID to associate with this connection
            state: Optional state parameter (will include workspace_id if not provided)
            next_url: Optional URL to redirect to after successful connection
            
        Returns:
            Authorization URL
        """
        # Scopes for Google Analytics read-only access
        # Include userinfo.email to identify which Google account is being used for GA
        # (This can be different from the account used to log into the app)
        # Include openid as Google automatically adds it
        scopes = [
            "openid",  # Google automatically adds this, so include it explicitly
            "https://www.googleapis.com/auth/analytics.readonly",
            "https://www.googleapis.com/auth/userinfo.email",  # Minimal scope to identify the GA account
        ]
        
        # Build state: workspace_id:csrf_token:next_url (base64 encoded if next_url exists)
        import secrets
        csrf_token = secrets.token_urlsafe(16) if state is None else state.split(':')[1] if ':' in state else state
        
        # If next_url provided, encode it in state using base64 JSON
        if next_url:
            import json
            import base64
            state_data = {
                "workspace_id": workspace_id,
                "csrf": csrf_token,
                "next": next_url
            }
            state_json = json.dumps(state_data)
            state = base64.urlsafe_b64encode(state_json.encode()).decode()
        else:
            # Simple format: workspace_id:csrf_token
            state = f"{workspace_id}:{csrf_token}"
        
        # Use GA-specific redirect URI (different from user auth)
        ga_redirect_uri = f"{settings.APP_BASE_URL}/ga/callback"
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [ga_redirect_uri],
                }
            },
            scopes=scopes,
        )
        flow.redirect_uri = ga_redirect_uri
        
        authorization_url, _ = flow.authorization_url(
            access_type="offline",  # Required to get refresh token
            include_granted_scopes="false",  # Don't include user auth scopes
            state=state,
            prompt="consent",  # Force consent to get refresh token
        )
        
        return authorization_url
    
    @staticmethod
    def exchange_code_for_credentials(code: str) -> Optional[Credentials]:
        """
        Exchange authorization code for OAuth credentials.
        
        Args:
            code: Authorization code from Google
            
        Returns:
            Credentials object with refresh token, or None if exchange fails
        """
        scopes = [
            "openid",  # Google automatically adds this, so include it explicitly to match
            "https://www.googleapis.com/auth/analytics.readonly",
            "https://www.googleapis.com/auth/userinfo.email",  # Minimal scope to identify the GA account
        ]
        
        # Use GA-specific redirect URI (different from user auth)
        ga_redirect_uri = f"{settings.APP_BASE_URL}/ga/callback"
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [ga_redirect_uri],
                }
            },
            scopes=scopes,
        )
        flow.redirect_uri = ga_redirect_uri
        
        try:
            flow.fetch_token(code=code)
            if not flow.credentials:
                print("ERROR: No credentials returned from token exchange")
                return None
            if not flow.credentials.refresh_token:
                print("WARNING: No refresh token in credentials")
                # This is OK if user already authorized before
            print(f"DEBUG: Successfully exchanged code for credentials")
            print(f"DEBUG: Received scopes: {flow.credentials.scopes}")
            return flow.credentials
        except Warning as w:
            # Handle scope warnings - if credentials were still obtained, use them
            print(f"WARNING in exchange_code_for_credentials: {str(w)}")
            if flow.credentials:
                print("DEBUG: Credentials obtained despite scope warning, continuing...")
                return flow.credentials
            return None
        except Exception as e:
            print(f"ERROR in exchange_code_for_credentials: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def get_user_email_from_credentials(credentials: Credentials) -> Optional[str]:
        """
        Get user email from OAuth credentials.
        
        Args:
            credentials: OAuth credentials
            
        Returns:
            User email address, or None if unavailable
        """
        try:
            from googleapiclient.discovery import build
            print(f"DEBUG: Fetching user email from credentials...")
            service = build("oauth2", "v2", credentials=credentials)
            user_info = service.userinfo().get().execute()
            email = user_info.get("email")
            print(f"DEBUG: Got email from credentials: {email}")
            return email
        except Exception as e:
            print(f"DEBUG: Failed to get email from credentials: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def create_or_update_connection(
        db: Session,
        workspace_id: str,
        google_account_email: str,
        property_id: str,
        property_name: str,
        credentials: Credentials,
    ) -> GAConnection:
        """
        Create or update GA4 connection with encrypted refresh token.
        
        Args:
            db: Database session
            workspace_id: Workspace ID
            google_account_email: Google account email
            property_id: GA4 property ID
            property_name: GA4 property name
            credentials: OAuth credentials with refresh token
            
        Returns:
            GAConnection object
        """
        encryption_service = get_encryption_service()
        
        # Encrypt refresh token
        if not credentials.refresh_token:
            raise ValueError("No refresh token available in credentials")
        
        encrypted_refresh_token = encryption_service.encrypt(credentials.refresh_token)
        
        # Check if connection already exists for this workspace and property
        existing_connection = db.query(GAConnection).filter(
            GAConnection.workspace_id == workspace_id,
            GAConnection.property_id == property_id,
        ).first()
        
        if existing_connection:
            # Update existing connection
            from datetime import datetime
            existing_connection.google_account_email = google_account_email
            existing_connection.property_name = property_name
            existing_connection.refresh_token_encrypted = encrypted_refresh_token
            existing_connection.updated_at = datetime.utcnow()  # Update timestamp
            db.commit()
            db.refresh(existing_connection)
            return existing_connection
        
        # Create new connection
        connection = GAConnection(
            workspace_id=workspace_id,
            google_account_email=google_account_email,
            property_id=property_id,
            property_name=property_name,
            refresh_token_encrypted=encrypted_refresh_token,
        )
        
        db.add(connection)
        db.commit()
        db.refresh(connection)
        
        return connection
    
    @staticmethod
    def refresh_access_token(refresh_token_encrypted: str) -> Optional[Credentials]:
        """
        Refresh access token using encrypted refresh token.
        
        Args:
            refresh_token_encrypted: Encrypted refresh token
            
        Returns:
            New Credentials object, or None if refresh fails
        """
        encryption_service = get_encryption_service()
        
        try:
            # Decrypt refresh token
            refresh_token = encryption_service.decrypt(refresh_token_encrypted)
            
            # Create credentials and refresh
            creds = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
            )
            
            creds.refresh(Request())
            return creds
        except Exception:
            return None
    
    @staticmethod
    def parse_state(state: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Parse state parameter to extract workspace_id, CSRF token, and next URL.
        
        Args:
            state: State parameter from OAuth callback
            
        Returns:
            Tuple of (workspace_id, csrf_token, next_url)
        """
        if not state:
            return None, None, None
        
        # Try base64 JSON format first (if next_url was included)
        try:
            import base64
            import json
            state_json = base64.urlsafe_b64decode(state.encode()).decode()
            state_data = json.loads(state_json)
            workspace_id = state_data.get("workspace_id")
            csrf_token = state_data.get("csrf")
            next_url = state_data.get("next")
            return workspace_id, csrf_token, next_url
        except (ValueError, json.JSONDecodeError, Exception):
            # Fallback to simple format: workspace_id:csrf_token
            pass
        
        # Simple format: workspace_id:csrf_token
        if ":" in state:
            parts = state.split(":", 1)
            workspace_id = parts[0]
            csrf_token = parts[1] if len(parts) > 1 else None
            return workspace_id, csrf_token, None
        # If no colon, treat entire string as workspace_id
        return state, None, None

