"""FastAPI dependencies for authentication and authorization."""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import verify_token
from app.models.user import User
from app.models.workspace import Workspace

security = HTTPBearer()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    token: Optional[str] = None,  # Allow token as query parameter for browser testing
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.
    
    Supports both Authorization header and token query parameter (for browser testing).
    
    Raises:
        HTTPException: If token is invalid or user not found.
    """
    # Get token from header or query parameter
    if token:
        # Token provided as query parameter (for browser testing)
        token_value = token
    elif credentials:
        # Token provided in Authorization header
        token_value = credentials.credentials
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = verify_token(token_value)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Convert string UUID to UUID object if needed
    try:
        import uuid
        user_id_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == user_id_uuid).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Dependency to get the current user if authenticated, otherwise None.
    Useful for endpoints that work with or without authentication.
    """
    if credentials is None:
        return None
    
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        return None
    
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        return None
    
    # Convert string UUID to UUID object if needed
    try:
        import uuid
        user_id_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        user = db.query(User).filter(User.id == user_id_uuid).first()
        return user
    except (ValueError, TypeError):
        return None


async def get_user_default_workspace(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Workspace:
    """
    Dependency to get the current user's default workspace.
    Creates a default workspace if one doesn't exist.
    """
    workspace = db.query(Workspace).filter(
        Workspace.user_id == current_user.id
    ).first()
    
    if workspace is None:
        # Create default workspace for user
        workspace = Workspace(
            user_id=current_user.id,
            name="My Workspace",
        )
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
    
    return workspace


async def get_valid_gpt_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db),
):
    """
    Dependency to validate GPT access token for Custom GPT requests.
    
    This validates that the request comes from an authenticated Custom GPT session.
    Returns the GPTToken record and associated Workspace.
    
    Raises:
        HTTPException: If token is invalid, expired, or revoked.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # Validate token using GPTOAuthService
    from app.services.gpt_oauth_service import GPTOAuthService
    from app.models.gpt_token import GPTToken
    from app.models.workspace import Workspace
    
    gpt_token = GPTOAuthService.validate_access_token(db, token)
    
    if not gpt_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired GPT token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get workspace
    workspace = db.query(Workspace).filter(Workspace.id == gpt_token.workspace_id).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    
    return {
        "gpt_token": gpt_token,
        "workspace": workspace,
    }

