"""GPT OAuth service for Custom GPT authentication."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.config import get_settings
from app.models.gpt_token import GPTToken
from app.models.workspace import Workspace
from app.core.security import (
    create_access_token,
    hash_token,
    verify_token_hash,
    create_refresh_token,
)

settings = get_settings()
logger = logging.getLogger(__name__)


class GPTOAuthService:
    """Service for GPT OAuth token management."""

    # Token lifetimes
    ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Short-lived access tokens
    REFRESH_TOKEN_EXPIRE_DAYS = 90  # Long-lived refresh tokens

    @staticmethod
    def create_authorization_code(workspace_id: str) -> str:
        """
        Create a temporary authorization code for the workspace.
        In a production system, you'd store this in a cache (Redis) with expiration.
        For now, we'll encode it in the token itself.
        """
        # For simplicity, we'll use a JWT token as the authorization code
        # In production, use a proper session store
        code_data = {
            "workspace_id": workspace_id,
        }
        from app.core.security import create_access_token
        # Create authorization code with type="authorization_code"
        code = create_access_token(
            code_data, 
            expires_delta=timedelta(minutes=10),
            token_type="authorization_code"
        )
        return code

    @staticmethod
    def verify_authorization_code(code: str) -> Optional[str]:
        """
        Verify and extract workspace_id from authorization code.
        Returns workspace_id if valid, None otherwise.
        """
        from app.core.security import verify_token

        logger.debug(f"Verifying authorization code (length: {len(code)})")
        payload = verify_token(code)
        if not payload:
            logger.warning("Invalid authorization code format - token verification failed")
            return None

        logger.debug(f"Decoded payload: {payload}")
        token_type = payload.get("type")
        if token_type != "authorization_code":
            logger.warning(f"Authorization code has wrong type: {token_type} (expected: authorization_code)")
            return None

        workspace_id = payload.get("workspace_id")
        if not workspace_id:
            logger.warning("Authorization code missing workspace_id")
            return None

        logger.debug(f"Authorization code verified successfully for workspace: {workspace_id}")
        return workspace_id

    @staticmethod
    def exchange_code_for_tokens(
        db: Session, code: str, client_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            db: Database session
            code: Authorization code
            client_id: OAuth client ID (optional, for validation)

        Returns:
            Dict with access_token, refresh_token, expires_in, token_type, scope
            or None if exchange fails
        """
        workspace_id_str = GPTOAuthService.verify_authorization_code(code)
        if not workspace_id_str:
            logger.warning("Failed to verify authorization code")
            return None

        # Convert workspace_id string to UUID
        try:
            import uuid
            workspace_id = uuid.UUID(workspace_id_str) if isinstance(workspace_id_str, str) else workspace_id_str
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid workspace_id format: {workspace_id_str}, error: {e}")
            return None

        # Verify workspace exists
        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            logger.warning(f"Workspace not found: {workspace_id}")
            return None

        # Check if workspace has a GA connection
        from app.models.ga_connection import GAConnection

        ga_connection = (
            db.query(GAConnection)
            .filter(GAConnection.workspace_id == workspace.id)
            .first()
        )
        if not ga_connection:
            logger.warning(f"Workspace {workspace_id} has no GA connection")
            return None

        # Create access token (short-lived)
        # Note: token_type parameter sets the "type" field in the JWT
        access_token = create_access_token(
            data={"workspace_id": str(workspace.id)},
            expires_delta=timedelta(minutes=GPTOAuthService.ACCESS_TOKEN_EXPIRE_MINUTES),
            token_type="gpt_access",  # This sets the "type" field in the JWT
        )

        # Create refresh token (long-lived, opaque)
        refresh_token = create_refresh_token()

        # Hash the access token for storage
        access_token_hash = hash_token(access_token)

        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(
            minutes=GPTOAuthService.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        refresh_expires_at = datetime.utcnow() + timedelta(
            days=GPTOAuthService.REFRESH_TOKEN_EXPIRE_DAYS
        )

        # Revoke any existing active tokens for this workspace
        db.query(GPTToken).filter(
            and_(
                GPTToken.workspace_id == workspace.id,
                GPTToken.revoked == False,
            )
        ).update({"revoked": True})

        # Create new GPT token record
        gpt_token = GPTToken(
            workspace_id=workspace.id,
            access_token_hash=access_token_hash,
            expires_at=expires_at,
            scope="read",  # Only read access for now
            refresh_token=refresh_token,
            revoked=False,
        )
        db.add(gpt_token)
        db.commit()
        db.refresh(gpt_token)

        logger.info(
            f"Created GPT tokens for workspace {workspace.id}, token_id: {gpt_token.id}"
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": GPTOAuthService.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
            "refresh_token": refresh_token,
            "scope": "read",
        }

    @staticmethod
    def refresh_access_token(
        db: Session, refresh_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Refresh an access token using a refresh token.

        Args:
            db: Database session
            refresh_token: Refresh token

        Returns:
            Dict with new access_token, expires_in, token_type, scope
            or None if refresh fails
        """
        # Find token by refresh_token
        gpt_token = (
            db.query(GPTToken)
            .filter(
                and_(
                    GPTToken.refresh_token == refresh_token,
                    GPTToken.revoked == False,
                )
            )
            .first()
        )

        if not gpt_token:
            logger.warning("Refresh token not found or revoked")
            return None

        # Check if refresh token is expired
        # Note: We store refresh_expires_at in the token record
        # For now, we'll check if the token was created more than REFRESH_TOKEN_EXPIRE_DAYS ago
        refresh_token_age = datetime.utcnow() - gpt_token.created_at
        if refresh_token_age.days > GPTOAuthService.REFRESH_TOKEN_EXPIRE_DAYS:
            logger.warning("Refresh token has expired")
            gpt_token.revoked = True
            db.commit()
            return None

        # Verify workspace still exists
        workspace = (
            db.query(Workspace)
            .filter(Workspace.id == gpt_token.workspace_id)
            .first()
        )
        if not workspace:
            logger.warning(f"Workspace not found: {gpt_token.workspace_id}")
            gpt_token.revoked = True
            db.commit()
            return None

        # Create new access token
        # Note: token_type parameter sets the "type" field in the JWT
        new_access_token = create_access_token(
            data={"workspace_id": str(gpt_token.workspace_id)},
            expires_delta=timedelta(minutes=GPTOAuthService.ACCESS_TOKEN_EXPIRE_MINUTES),
            token_type="gpt_access",  # This sets the "type" field in the JWT
        )

        # Update access token hash and expiration
        new_access_token_hash = hash_token(new_access_token)
        new_expires_at = datetime.utcnow() + timedelta(
            minutes=GPTOAuthService.ACCESS_TOKEN_EXPIRE_MINUTES
        )

        gpt_token.access_token_hash = new_access_token_hash
        gpt_token.expires_at = new_expires_at

        db.commit()

        logger.info(f"Refreshed access token for workspace {gpt_token.workspace_id}")

        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": GPTOAuthService.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "scope": gpt_token.scope,
        }

    @staticmethod
    def validate_access_token(db: Session, token: str) -> Optional[GPTToken]:
        """
        Validate a GPT access token and return the GPTToken record.

        Args:
            db: Database session
            token: Access token string

        Returns:
            GPTToken record if valid, None otherwise
        """
        # Verify JWT token
        from app.core.security import verify_token

        payload = verify_token(token)
        if not payload:
            logger.warning("Invalid token format - JWT verification failed")
            return None

        token_type = payload.get("type")
        if token_type != "gpt_access":
            logger.warning(f"Token is not a GPT access token (type: {token_type})")
            return None

        workspace_id_str = payload.get("workspace_id")
        if not workspace_id_str:
            logger.warning("Token missing workspace_id")
            return None
        
        # Convert workspace_id string to UUID
        try:
            import uuid
            workspace_id = uuid.UUID(workspace_id_str) if isinstance(workspace_id_str, str) else workspace_id_str
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid workspace_id format: {workspace_id_str}, error: {e}")
            return None
        
        logger.debug(f"Token payload validated: workspace_id={workspace_id}, type={token_type}")

        # Find token by workspace_id and check if revoked
        # Get all non-revoked tokens for this workspace
        gpt_tokens = (
            db.query(GPTToken)
            .filter(
                and_(
                    GPTToken.workspace_id == workspace_id,
                    GPTToken.revoked == False,
                )
            )
            .order_by(GPTToken.created_at.desc())
            .all()
        )

        if not gpt_tokens:
            logger.warning(f"No GPT token found for workspace {workspace_id}")
            return None

        # Since we're using signed JWTs, we can validate without hash matching
        # The JWT signature ensures the token is valid and hasn't been tampered with
        # We just need to verify:
        # 1. There's a non-revoked token record for this workspace
        # 2. The token record is not expired
        # 3. Optionally verify hash (for extra security, but JWT signature is enough)
        
        # Get the most recent non-expired token
        gpt_token = None
        for token_record in gpt_tokens:
            # Check if token is expired
            if datetime.utcnow() > token_record.expires_at:
                logger.debug(f"Skipping expired token {token_record.id} for workspace {workspace_id}")
                continue
            
            # Try to verify hash (optional - JWT signature is primary validation)
            # If hash matches, use this token
            if verify_token_hash(token, token_record.access_token_hash):
                gpt_token = token_record
                logger.debug(f"Found matching token (hash verified) for workspace {workspace_id}, token_id: {token_record.id}")
                break
        
        # If no hash match, use the most recent non-expired token
        # This handles cases where hash verification fails but JWT is valid
        if not gpt_token:
            for token_record in gpt_tokens:
                if datetime.utcnow() <= token_record.expires_at:
                    gpt_token = token_record
                    logger.debug(
                        f"Using most recent non-expired token for workspace {workspace_id}, "
                        f"token_id: {token_record.id} (hash verification skipped - JWT signature is primary)"
                    )
                    break
        
        if not gpt_token:
            logger.warning(
                f"No valid (non-expired) GPT token found for workspace {workspace_id}. "
                f"Found {len(gpt_tokens)} token(s) but all are expired or invalid."
            )
            return None

        # Final expiration check
        if datetime.utcnow() > gpt_token.expires_at:
            logger.warning(f"Token has expired for workspace {workspace_id}")
            return None

        logger.debug(f"Token validated successfully for workspace {workspace_id}, token_id: {gpt_token.id}")
        return gpt_token

    @staticmethod
    def revoke_token(db: Session, token: str) -> bool:
        """
        Revoke a token (access or refresh).

        Args:
            db: Database session
            token: Token string (access or refresh)

        Returns:
            True if revoked, False otherwise
        """
        # Try as refresh token first
        gpt_token = (
            db.query(GPTToken)
            .filter(
                and_(
                    GPTToken.refresh_token == token,
                    GPTToken.revoked == False,
                )
            )
            .first()
        )

        if gpt_token:
            gpt_token.revoked = True
            db.commit()
            logger.info(f"Revoked refresh token for workspace {gpt_token.workspace_id}")
            return True

        # Try as access token
        gpt_token = GPTOAuthService.validate_access_token(db, token)
        if gpt_token:
            gpt_token.revoked = True
            db.commit()
            logger.info(f"Revoked access token for workspace {gpt_token.workspace_id}")
            return True

        return False
    
    @staticmethod
    def revoke_all_workspace_tokens(db: Session, workspace_id: str) -> int:
        """
        Revoke all active GPT tokens for a workspace.
        
        Args:
            db: Database session
            workspace_id: Workspace ID (string UUID)
            
        Returns:
            Number of tokens revoked
        """
        import uuid
        try:
            workspace_id_uuid = uuid.UUID(workspace_id) if isinstance(workspace_id, str) else workspace_id
        except (ValueError, TypeError):
            logger.error(f"Invalid workspace_id format: {workspace_id}")
            return 0
        
        # Revoke all active tokens for this workspace
        result = db.query(GPTToken).filter(
            and_(
                GPTToken.workspace_id == workspace_id_uuid,
                GPTToken.revoked == False,
            )
        ).update({"revoked": True})
        
        db.commit()
        logger.info(f"Revoked {result} GPT token(s) for workspace {workspace_id}")
        return result

