"""Authentication service - business logic for user authentication."""

from typing import Optional
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.workspace import Workspace
from app.core.security import get_password_hash, verify_password
from app.schemas.user import UserCreate


class AuthService:
    """Service for authentication operations."""
    
    @staticmethod
    def create_user(db: Session, user_create: UserCreate) -> User:
        """
        Create a new user account.
        
        Args:
            db: Database session
            user_create: User creation data
            
        Returns:
            Created user object
            
        Raises:
            ValueError: If email already exists
        """
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_create.email).first()
        if existing_user:
            raise ValueError(f"User with email {user_create.email} already exists")
        
        # Create new user
        hashed_password = get_password_hash(user_create.password)
        user = User(
            email=user_create.email,
            password_hash=hashed_password,
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Create default workspace for the user
        workspace = Workspace(
            user_id=user.id,
            name="My Workspace",
        )
        db.add(workspace)
        db.commit()
        
        return user
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user by email and password.
        
        Args:
            db: Database session
            email: User email
            password: Plain text password
            
        Returns:
            User object if authentication succeeds, None otherwise
        """
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            return None
        
        # Check if user is Google-only user (no password)
        if user.is_google_user and not user.password_hash:
            return None  # Google users can't login with password
        
        if not user.password_hash or not verify_password(password, user.password_hash):
            return None
        
        return user
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email."""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()

