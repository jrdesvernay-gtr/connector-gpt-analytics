"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import UserCreate, UserResponse, Token
from app.services.auth_service import AuthService
from app.core.security import create_access_token
from app.api.dependencies import get_current_user, get_user_default_workspace
from app.models.user import User
from app.models.workspace import Workspace

router = APIRouter()


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    user_create: UserCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new user account.
    
    - **email**: User email address (must be unique)
    - **password**: User password (will be hashed)
    """
    try:
        user = AuthService.create_user(db, user_create)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Login endpoint - returns JWT access token.
    
    Uses OAuth2PasswordRequestForm for compatibility with OpenAPI.
    The form should have:
    - **username**: User email address
    - **password**: User password
    """
    user = AuthService.authenticate_user(
        db, 
        email=form_data.username,  # OAuth2PasswordRequestForm uses 'username' field
        password=form_data.password,
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return Token(access_token=access_token, token_type="bearer")


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Alternative login endpoint that returns JWT token.
    Same as /login but with a different route name for flexibility.
    OAuth2 standard endpoint name.
    """
    user = AuthService.authenticate_user(
        db, 
        email=form_data.username,  # OAuth2PasswordRequestForm uses 'username' field
        password=form_data.password,
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current authenticated user information including workspace ID.
    
    Requires valid JWT token in Authorization header or query parameter:
    - Authorization: Bearer <token>
    - ?token=<token>
    
    Returns:
    - User information (id, email, created_at)
    - Default workspace ID (the workspace to use for this user)
    - All workspaces for this user (if multiple exist)
    """
    user_data = UserResponse.model_validate(current_user).model_dump()
    
    # Get default workspace
    default_workspace = None
    try:
        default_workspace = await get_user_default_workspace(
            current_user=current_user,
            db=db
        )
    except Exception as e:
        # If no workspace exists, we'll return None
        pass
    
    # Get all workspaces for this user
    all_workspaces = (
        db.query(Workspace)
        .filter(Workspace.user_id == current_user.id)
        .order_by(Workspace.created_at.desc())
        .all()
    )
    
    return {
        **user_data,
        "default_workspace_id": str(default_workspace.id) if default_workspace else None,
        "workspaces": [
            {
                "id": str(w.id),
                "created_at": w.created_at.isoformat(),
            }
            for w in all_workspaces
        ],
    }

