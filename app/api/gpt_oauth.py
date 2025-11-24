"""GPT OAuth provider endpoints for Custom GPT authentication."""

import logging
from typing import Optional
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query, Form
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.workspace import Workspace
from app.services.gpt_oauth_service import GPTOAuthService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/authorize-gpt/callback")
async def authorize_gpt_callback(
    code: str = Query(..., description="Authorization code"),
    state: Optional[str] = Query(None, description="State parameter"),
):
    """
    Test callback endpoint to display authorization code.
    This is for testing only - in production, Custom GPT will handle the callback.
    """
    return JSONResponse({
        "message": "Authorization successful!",
        "authorization_code": code,
        "state": state,
        "instructions": {
            "step1": "Copy the authorization_code above",
            "step2": f"Exchange it for tokens using: POST /oauth/token",
            "step3": "Use the curl command below:",
            "curl_command": f'curl -X POST http://localhost:8000/oauth/token -H "Content-Type: application/x-www-form-urlencoded" -d "grant_type=authorization_code" -d "code={code}" -d "redirect_uri=http://localhost:8000/authorize-gpt/callback"'
        }
    })


@router.get("/authorize-gpt")
async def authorize_gpt(
    workspace_id: str = Query(..., description="Workspace ID"),
    redirect_uri: str = Query(..., description="OAuth redirect URI from Custom GPT"),
    state: Optional[str] = Query(None, description="State parameter for CSRF protection"),
    client_id: Optional[str] = Query(None, description="OAuth client ID"),
    scope: Optional[str] = Query("read", description="Requested scope"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    OAuth2 authorization endpoint for Custom GPT.
    
    This endpoint initiates the OAuth flow. The user must be authenticated,
    and we verify they own the workspace before generating an authorization code.
    
    Args:
        workspace_id: Workspace ID to authorize
        redirect_uri: Where to redirect after authorization (from Custom GPT)
        state: Optional state parameter for CSRF protection
        client_id: Optional OAuth client ID
        scope: Requested scope (default: "read")
        user: Authenticated user (from dependency)
        db: Database session
        
    Returns:
        Redirect to redirect_uri with authorization code
    """
    logger.debug(f"GPT authorization requested for workspace: {workspace_id}")

    # Verify workspace exists and belongs to user
    workspace = (
        db.query(Workspace)
        .filter(
            Workspace.id == workspace_id,
            Workspace.user_id == user.id,
        )
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or access denied",
        )

    # Check if workspace has a GA connection
    from app.models.ga_connection import GAConnection

    ga_connection = (
        db.query(GAConnection)
        .filter(GAConnection.workspace_id == workspace.id)
        .first()
    )

    if not ga_connection:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace has no GA connection. Please connect Google Analytics first.",
        )

    # Generate authorization code
    authorization_code = GPTOAuthService.create_authorization_code(
        str(workspace.id)
    )

    logger.debug(
        f"Generated authorization code for workspace {workspace.id}, code length: {len(authorization_code)}"
    )

    # Build redirect URL with authorization code using proper URL encoding
    # Parse the redirect_uri to ensure we don't break existing query params
    parsed_uri = urlparse(redirect_uri)
    query_params = parse_qs(parsed_uri.query)
    
    # Add our parameters (URL encode the code properly)
    query_params['code'] = [authorization_code]
    if state:
        query_params['state'] = [state]
    
    # Rebuild the URL with encoded parameters
    new_query = urlencode(query_params, doseq=True)
    redirect_url = urlunparse((
        parsed_uri.scheme,
        parsed_uri.netloc,
        parsed_uri.path,
        parsed_uri.params,
        new_query,
        parsed_uri.fragment
    ))

    logger.info(
        f"Generated authorization code for workspace {workspace.id}"
    )
    logger.debug(f"Redirect URL: {redirect_url}")
    logger.debug(f"Authorization code (first 20 chars): {authorization_code[:20]}...")

    return RedirectResponse(url=redirect_url, status_code=302)


@router.post("/oauth/token")
async def oauth_token(
    grant_type: str = Form(..., description="Grant type: authorization_code or refresh_token"),
    code: Optional[str] = Form(None, description="Authorization code"),
    refresh_token: Optional[str] = Form(None, description="Refresh token"),
    redirect_uri: Optional[str] = Form(None, description="Redirect URI"),
    client_id: Optional[str] = Form(None, description="Client ID"),
    client_secret: Optional[str] = Form(None, description="Client secret"),
    db: Session = Depends(get_db),
):
    """
    OAuth2 token endpoint for Custom GPT.
    
    This endpoint exchanges authorization codes for access tokens,
    or refreshes access tokens using refresh tokens.
    
    Supports:
    - authorization_code grant: Exchange code for tokens
    - refresh_token grant: Refresh an expired access token
    
    Args:
        grant_type: OAuth2 grant type
        code: Authorization code (for authorization_code grant)
        refresh_token: Refresh token (for refresh_token grant)
        redirect_uri: Redirect URI (optional, for validation)
        client_id: Client ID (optional, for validation)
        client_secret: Client secret (optional, for validation)
        db: Database session
        
    Returns:
        OAuth2 token response with access_token, refresh_token, etc.
    """
    logger.debug(f"Token request received: grant_type={grant_type}")

    if grant_type == "authorization_code":
        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing authorization code",
            )

        # Trim whitespace from code (in case it was copied with trailing newlines)
        code = code.strip()
        
        logger.debug(f"Exchanging authorization code (length: {len(code)}, first 20 chars: {code[:20]}...)")

        # Exchange code for tokens
        token_response = GPTOAuthService.exchange_code_for_tokens(db, code)

        if not token_response:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired authorization code",
            )

        logger.info("Successfully exchanged authorization code for tokens")
        return JSONResponse(content=token_response)

    elif grant_type == "refresh_token":
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing refresh token",
            )

        # Refresh access token
        token_response = GPTOAuthService.refresh_access_token(db, refresh_token)

        if not token_response:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired refresh token",
            )

        logger.info("Successfully refreshed access token")
        return JSONResponse(content=token_response)

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported grant_type: {grant_type}",
        )


@router.post("/debug/validate-token")
async def debug_validate_token(
    token: str = Form(..., description="Access token to validate"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Debug endpoint to validate a GPT token and see what's happening.
    This is for debugging only - remove in production.
    """
    import uuid
    from app.core.security import verify_token
    from app.services.gpt_oauth_service import GPTOAuthService
    from app.models.gpt_token import GPTToken
    from datetime import datetime
    
    result = {
        "token_preview": token[:50] + "..." if len(token) > 50 else token,
        "steps": []
    }
    
    # Step 1: Verify JWT
    payload = verify_token(token)
    if not payload:
        result["steps"].append({"step": "JWT verification", "status": "failed", "error": "Invalid JWT"})
        return JSONResponse(content=result)
    
    result["steps"].append({
        "step": "JWT verification",
        "status": "success",
        "payload": {
            "workspace_id": payload.get("workspace_id"),
            "type": payload.get("type"),
            "exp": payload.get("exp"),
            "exp_datetime": datetime.fromtimestamp(payload.get("exp")).isoformat() if payload.get("exp") else None,
        }
    })
    
    # Step 2: Check token type
    if payload.get("type") != "gpt_access":
        result["steps"].append({
            "step": "Token type check",
            "status": "failed",
            "error": f"Expected 'gpt_access', got '{payload.get('type')}'"
        })
        return JSONResponse(content=result)
    
    result["steps"].append({"step": "Token type check", "status": "success"})
    
    # Step 3: Convert workspace_id
    workspace_id_str = payload.get("workspace_id")
    try:
        workspace_id = uuid.UUID(workspace_id_str) if isinstance(workspace_id_str, str) else workspace_id_str
        result["steps"].append({
            "step": "Workspace ID conversion",
            "status": "success",
            "workspace_id": str(workspace_id)
        })
    except Exception as e:
        result["steps"].append({
            "step": "Workspace ID conversion",
            "status": "failed",
            "error": str(e)
        })
        return JSONResponse(content=result)
    
    # Step 4: Find tokens in database
    from sqlalchemy import and_
    tokens = (
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
    
    result["steps"].append({
        "step": "Database query",
        "status": "success" if tokens else "failed",
        "token_count": len(tokens),
        "tokens": []
    })
    
    if not tokens:
        result["error"] = "No tokens found in database for this workspace"
        return JSONResponse(content=result)
    
    # Step 5: Check each token
    from app.core.security import verify_token_hash
    for idx, token_record in enumerate(tokens):
        is_expired = datetime.utcnow() > token_record.expires_at
        hash_match = verify_token_hash(token, token_record.access_token_hash)
        
        token_info = {
            "id": str(token_record.id),
            "created_at": token_record.created_at.isoformat(),
            "expires_at": token_record.expires_at.isoformat(),
            "is_expired": is_expired,
            "hash_match": hash_match,
        }
        result["steps"][-1]["tokens"].append(token_info)
        
        if not is_expired and hash_match:
            result["steps"].append({
                "step": "Token validation",
                "status": "success",
                "matched_token_id": str(token_record.id)
            })
            return JSONResponse(content=result)
    
    result["error"] = "No valid token found - all tokens are expired or hash doesn't match"
    return JSONResponse(content=result)


@router.get("/debug/tokens")
async def debug_tokens(
    workspace_id: str = Query(..., description="Workspace ID"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Debug endpoint to check stored tokens for a workspace.
    This is for debugging only - remove in production.
    """
    import uuid
    from app.models.gpt_token import GPTToken
    from datetime import datetime
    
    try:
        workspace_uuid = uuid.UUID(workspace_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format",
        )
    
    # Verify workspace belongs to user
    workspace = (
        db.query(Workspace)
        .filter(
            Workspace.id == workspace_uuid,
            Workspace.user_id == user.id,
        )
        .first()
    )
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or access denied",
        )
    
    # Get all tokens for this workspace
    tokens = (
        db.query(GPTToken)
        .filter(GPTToken.workspace_id == workspace_uuid)
        .order_by(GPTToken.created_at.desc())
        .all()
    )
    
    result = {
        "workspace_id": str(workspace_uuid),
        "token_count": len(tokens),
        "tokens": []
    }
    
    for token in tokens:
        result["tokens"].append({
            "id": str(token.id),
            "created_at": token.created_at.isoformat(),
            "expires_at": token.expires_at.isoformat(),
            "is_expired": datetime.utcnow() > token.expires_at,
            "revoked": token.revoked,
            "scope": token.scope,
            "hash_preview": token.access_token_hash[:20] + "..." if token.access_token_hash else None,
        })
    
    return JSONResponse(content=result)


@router.post("/oauth/revoke")
async def oauth_revoke(
    token: str = Form(..., description="Token to revoke (access or refresh)"),
    token_type_hint: Optional[str] = Form(None, description="Hint: access_token or refresh_token"),
    db: Session = Depends(get_db),
):
    """
    OAuth2 token revocation endpoint.
    
    Revokes an access token or refresh token.
    
    Args:
        token: Token to revoke
        token_type_hint: Hint about token type (optional)
        db: Database session
        
    Returns:
        Success response
    """
    logger.debug(f"Token revocation requested: token_type_hint={token_type_hint}")

    revoked = GPTOAuthService.revoke_token(db, token)

    if not revoked:
        # According to OAuth2 spec, revocation should succeed even if token is invalid
        # But we can log it
        logger.warning("Token revocation attempted but token not found")
        return JSONResponse(content={"message": "Token revoked or not found"})

    logger.info("Token successfully revoked")
    return JSONResponse(content={"message": "Token revoked successfully"})

