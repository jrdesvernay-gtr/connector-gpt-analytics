"""GPT OAuth provider endpoints for Custom GPT authentication.latest version 2.0.0"""

import logging
from typing import Optional
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query, Form
from fastapi.responses import RedirectResponse, JSONResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.dependencies import get_current_user, get_user_default_workspace
from app.models.user import User
from app.models.workspace import Workspace
from app.services.gpt_oauth_service import GPTOAuthService
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

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
    request: Request,
    redirect_uri: Optional[str] = Query(None, description="OAuth redirect URI from Custom GPT"),
    state: Optional[str] = Query(None, description="State parameter for CSRF protection"),
    workspace_id: Optional[str] = Query(None, description="Workspace ID (optional, will use default if not provided)"),
    client_id: Optional[str] = Query(None, description="OAuth client ID"),
    scope: Optional[str] = Query("read", description="Requested scope"),
    token: Optional[str] = Query(None, description="JWT token (for authenticated requests)"),
    db: Session = Depends(get_db),
):
    """
    OAuth2 authorization endpoint for Custom GPT.
    
    This endpoint initiates the OAuth flow. If user is not authenticated,
    redirects to login, then continues flow after authentication.
    
    Flow:
    1. Check if user is authenticated
    2. If not → redirect to login with return URL
    3. After login → check if GA is connected
    4. If not → redirect to GA connection
    5. After GA connection → return here to show authorization page
    6. User authorizes → generate code and redirect to ChatGPT
    
    Args:
        redirect_uri: Where to redirect after authorization (from Custom GPT)
        state: Optional state parameter for CSRF protection
        workspace_id: Optional workspace ID (uses default if not provided)
        client_id: Optional OAuth client ID
        scope: Requested scope (default: "read")
        token: Optional JWT token for authentication
        request: FastAPI Request object
        db: Database session
        
    Returns:
        Either redirect to login, GA connection, authorization page, or ChatGPT callback
    """
    from app.api.dependencies import get_current_user_optional
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from urllib.parse import urlencode
    
    # Get settings at function level to avoid scoping issues
    app_settings = get_settings()
    
    logger.info(f"GPT authorization requested: redirect_uri={redirect_uri}, workspace_id={workspace_id}, state={state}, client_id={client_id}")
    
    # If no redirect_uri, show helpful message (coming from dashboard, not OAuth flow)
    if not redirect_uri or not redirect_uri.strip():
        try:
            # Check if user is authenticated
            user = None
            if token:
                try:
                    from app.core.security import verify_token
                    import uuid
                    payload = verify_token(token)
                    if payload:
                        user_id = payload.get("sub")
                        if user_id:
                            user_id_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
                            user = db.query(User).filter(User.id == user_id_uuid).first()
                except Exception as e:
                    logger.debug(f"Error verifying token: {e}")
                    pass
            
            if user:
                # User is authenticated - check if already authorized
                workspace = None
                if workspace_id:
                    import uuid
                    try:
                        workspace_id_uuid = uuid.UUID(workspace_id) if isinstance(workspace_id, str) else workspace_id
                        workspace = db.query(Workspace).filter(
                            Workspace.id == workspace_id_uuid,
                            Workspace.user_id == user.id
                        ).first()
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Error parsing workspace_id: {e}")
                        pass
                
                if not workspace:
                    # Get default workspace for user (manually, not using dependency)
                    workspace = db.query(Workspace).filter(Workspace.user_id == user.id).first()
                    if not workspace:
                        # Create default workspace if none exists
                        workspace = Workspace(
                            user_id=user.id,
                            name="My Workspace"
                        )
                        db.add(workspace)
                        db.commit()
                        db.refresh(workspace)
                
                # Check if already authorized
                from app.models.gpt_token import GPTToken
                from sqlalchemy import and_
                has_tokens = db.query(GPTToken).filter(
                    and_(
                        GPTToken.workspace_id == workspace.id,
                        GPTToken.revoked == False,
                    )
                ).count() > 0
                
                if has_tokens:
                    # Already authorized - show message
                    html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>ChatGPT Already Authorized - Ask My Analytics</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; background: #f5f5f5; }}
                            .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                            .success {{ background: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #28a745; color: #155724; }}
                            .button {{ display: inline-block; padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 10px 5px 10px 0; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>✓ ChatGPT Already Authorized</h1>
                            <div class="success">
                                <p><strong>Good news!</strong> Your ChatGPT is already connected and authorized.</p>
                                <p>You can go back to ChatGPT and start querying your GA4 data. The connection is active and working.</p>
                            </div>
                            <p><a href="{app_settings.APP_BASE_URL}/dashboard{'?token=' + token if token else ''}" class="button">← Back to Dashboard</a></p>
                        </div>
                    </body>
                    </html>
                    """
                    from fastapi.responses import HTMLResponse
                    return HTMLResponse(content=html)
                else:
                    # Not authorized - explain they need to authorize from ChatGPT
                    html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Authorize ChatGPT - Ask My Analytics</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; background: #f5f5f5; }}
                            .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                            .info {{ background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #007bff; }}
                            .button {{ display: inline-block; padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 10px 5px 10px 0; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>Authorize ChatGPT</h1>
                            <div class="info">
                                <p><strong>How to authorize ChatGPT:</strong></p>
                                <ol>
                                    <li>Go to ChatGPT and open your Custom GPT</li>
                                    <li>Ask a question like "What were my sessions yesterday?"</li>
                                    <li>ChatGPT will automatically prompt you to authorize</li>
                                    <li>Click "Authorize" and complete the OAuth flow</li>
                                </ol>
                                <p><strong>Note:</strong> Authorization must be initiated from ChatGPT, not from this dashboard.</p>
                            </div>
                            <p><a href="{app_settings.APP_BASE_URL}/dashboard{'?token=' + token if token else ''}" class="button">← Back to Dashboard</a></p>
                        </div>
                    </body>
                    </html>
                    """
                    from fastapi.responses import HTMLResponse
                    return HTMLResponse(content=html)
            
            # Not authenticated and no redirect_uri - invalid request
            logger.error(f"Invalid request: no redirect_uri and not authenticated")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing redirect_uri parameter. Authorization must be initiated from ChatGPT."
            )
        except Exception as e:
            # Catch any errors and show friendly error page
            logger.error(f"Error in authorize-gpt endpoint: {str(e)}", exc_info=True)
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error - Ask My Analytics</title>
                <style>
                    body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; background: #f5f5f5; }}
                    .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                    .error {{ background: #f8d7da; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #dc3545; color: #721c24; }}
                    .button {{ display: inline-block; padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 10px 5px 10px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Error</h1>
                    <div class="error">
                        <p><strong>An error occurred:</strong></p>
                        <p>Please try going back to the dashboard and try again, or authorize ChatGPT directly from ChatGPT.</p>
                    </div>
                    <p><a href="{app_settings.APP_BASE_URL}/dashboard{'?token=' + token if token else ''}" class="button">← Back to Dashboard</a></p>
                </div>
            </body>
            </html>
            """
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=error_html, status_code=500)
    
    # Try to get current user (optional - don't fail if not authenticated)
    # Check both token query parameter and Authorization header
    user = None
    
    # First, try token from query parameter
    if token:
        try:
            from app.core.security import verify_token
            import uuid
            payload = verify_token(token)
            if payload:
                user_id = payload.get("sub")
                if user_id:
                    # Convert string UUID to UUID object if needed
                    try:
                        user_id_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
                        user = db.query(User).filter(User.id == user_id_uuid).first()
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Invalid user ID format: {e}")
        except Exception as e:
            logger.debug(f"Failed to verify token from query param: {e}")
            pass
    
    # If not found, try Authorization header
    if not user:
        try:
            credentials: Optional[HTTPAuthorizationCredentials] = None
            security = HTTPBearer(auto_error=False)
            # Get credentials from request header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token_value = auth_header.replace("Bearer ", "")
                from app.core.security import verify_token
                import uuid
                payload = verify_token(token_value)
                if payload:
                    user_id = payload.get("sub")
                    if user_id:
                        # Convert string UUID to UUID object if needed
                        try:
                            user_id_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
                            user = db.query(User).filter(User.id == user_id_uuid).first()
                        except (ValueError, TypeError) as e:
                            logger.debug(f"Invalid user ID format: {e}")
        except Exception as e:
            logger.debug(f"Failed to verify token from Authorization header: {e}")
            pass
    
    # If not authenticated, redirect to login with return URL
    if not user:
        # Get settings at function level to avoid scoping issues
        app_settings = get_settings()
        try:
            # Build return URL to come back to authorize-gpt after login
            return_params = {
                "redirect_uri": redirect_uri,
            }
            if state:
                return_params["state"] = state
            if workspace_id:
                return_params["workspace_id"] = workspace_id
            if client_id:
                return_params["client_id"] = client_id
            if scope:
                return_params["scope"] = scope
                
            next_url = f"{app_settings.APP_BASE_URL}/authorize-gpt?{urlencode(return_params)}"
            
            # URL-encode the next_url properly for passing as query parameter
            from urllib.parse import quote
            login_url = f"{app_settings.APP_BASE_URL}/auth/google/login?next={quote(next_url)}"
            
            logger.info(f"User not authenticated, redirecting to login: {login_url}")
            logger.info(f"Next URL: {next_url}")
            return RedirectResponse(url=login_url, status_code=302)
        except Exception as e:
            logger.error(f"Error building redirect URL: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error initiating OAuth flow: {str(e)}"
            )
    
    # User is authenticated - get or determine workspace
    if workspace_id:
        # Use provided workspace_id
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
    else:
        # Use user's default workspace
        workspace = (
            db.query(Workspace)
            .filter(Workspace.user_id == user.id)
            .first()
        )
        if not workspace:
            # Create default workspace if none exists
            workspace = Workspace(user_id=user.id, name="My Workspace")
            db.add(workspace)
            db.commit()
            db.refresh(workspace)

    # Check if workspace has a GA connection
    from app.models.ga_connection import GAConnection

    ga_connection = (
        db.query(GAConnection)
        .filter(GAConnection.workspace_id == workspace.id)
        .first()
    )

    if not ga_connection:
        # No GA connection - redirect to GA connection flow
        # Store OAuth flow state to return here after GA connection
        
        # Build return URL to come back to authorize-gpt after GA connection
        return_params = {
            "redirect_uri": redirect_uri,
        }
        if state:
            return_params["state"] = state
        return_params["workspace_id"] = str(workspace.id)
        
        next_url = f"{app_settings.APP_BASE_URL}/authorize-gpt?{urlencode(return_params)}"
        
        # URL-encode the next_url properly for passing as query parameter
        from urllib.parse import quote
        ga_connect_url = f"{app_settings.APP_BASE_URL}/ga/connect?token={token}&next={quote(next_url)}"
        
        logger.debug(f"No GA connection found, redirecting to GA connection: {ga_connect_url}")
        return RedirectResponse(url=ga_connect_url, status_code=302)

    # Build current query params for redirect
    current_params = {}
    if request:
        for key, value in request.query_params.items():
            # FastAPI query params are MultiDict, get first value
            if isinstance(value, list):
                current_params[key] = value[0]
            else:
                current_params[key] = value
    
    # Check if this is an authorization confirmation request
    # If user clicked "Authorize" button, auto_authorize parameter will be present
    auto_authorize = current_params.get("auto_authorize") if current_params else None
    
    # If not auto-authorizing, show authorization confirmation page
    if auto_authorize != "true":
        # Show authorization page HTML
        authorization_page_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authorize ChatGPT</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }}
                .container {{
                    background: white;
                    border-radius: 12px;
                    padding: 40px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    max-width: 500px;
                    width: 90%;
                }}
                h1 {{
                    margin: 0 0 10px 0;
                    color: #333;
                }}
                .subtitle {{
                    color: #666;
                    margin-bottom: 30px;
                }}
                .info-box {{
                    background: #f5f7fa;
                    border-left: 4px solid #667eea;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .info-box strong {{
                    color: #333;
                }}
                .authorize-btn {{
                    background: #667eea;
                    color: white;
                    border: none;
                    padding: 15px 30px;
                    font-size: 16px;
                    border-radius: 6px;
                    cursor: pointer;
                    width: 100%;
                    margin-top: 20px;
                    font-weight: 600;
                    transition: background 0.3s;
                }}
                .authorize-btn:hover {{
                    background: #5568d3;
                }}
                .cancel-btn {{
                    background: transparent;
                    color: #666;
                    border: 1px solid #ddd;
                    padding: 15px 30px;
                    font-size: 16px;
                    border-radius: 6px;
                    cursor: pointer;
                    width: 100%;
                    margin-top: 10px;
                }}
                .cancel-btn:hover {{
                    background: #f5f7fa;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Authorize ChatGPT</h1>
                <p class="subtitle">Allow ChatGPT to access your Google Analytics data</p>
                
                <div class="info-box">
                    <strong>Workspace:</strong> {workspace.name}<br>
                    <strong>GA Property:</strong> {ga_connection.property_name}
                </div>
                
                <p>ChatGPT will be able to:</p>
                <ul>
                    <li>Query your GA4 analytics data</li>
                    <li>Read metrics and dimensions</li>
                    <li>Access data for this workspace only</li>
                </ul>
                
                <p><small>You can revoke access at any time.</small></p>
                
                <a href="{app_settings.APP_BASE_URL}/authorize-gpt?{urlencode({**current_params, 'auto_authorize': 'true'})}" 
                   class="authorize-btn" style="text-decoration: none; display: block; text-align: center;">
                    Authorize ChatGPT
                </a>
            </div>
        </body>
        </html>
        """
        return Response(content=authorization_page_html, media_type="text/html")

    # User authorized - generate authorization code and redirect
    authorization_code = GPTOAuthService.create_authorization_code(
        str(workspace.id)
    )

    logger.debug(
        f"Generated authorization code for workspace {workspace.id}, code length: {len(authorization_code)}"
    )

    # Build redirect URL with authorization code using proper URL encoding
    parsed_uri = urlparse(redirect_uri)
    query_params = parse_qs(parsed_uri.query)
    
    # Add our parameters (URL encode the code properly)
    query_params['code'] = [authorization_code]
    if state:
        query_params['state'] = [state]
    
    # Validate redirect_uri before building redirect URL
    if not redirect_uri or not parsed_uri.scheme or not parsed_uri.netloc:
        logger.error(f"Invalid redirect_uri format: {redirect_uri}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid redirect_uri format. Must be a valid URL."
        )
    
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
        f"Generated authorization code for workspace {workspace.id}, redirecting to ChatGPT: {redirect_uri}"
    )
    logger.debug(f"Full redirect URL: {redirect_url[:200]}...")
    logger.debug(f"Authorization code (first 20 chars): {authorization_code[:20]}...")

    try:
        return RedirectResponse(url=redirect_url, status_code=302)
    except Exception as e:
        logger.error(f"Error creating redirect response: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error redirecting to callback URL: {str(e)}"
        )


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


@router.get("/revoke-chatgpt")
async def revoke_chatgpt_page(
    token: Optional[str] = Query(None, description="JWT token for authentication"),
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_user_default_workspace),
    db: Session = Depends(get_db),
):
    """
    User-facing page to revoke ChatGPT authorization for this workspace.
    
    This allows users to reset their ChatGPT connection so they can re-authorize
    and select a different GA property if needed.
    """
    from app.config import get_settings
    from app.models.gpt_token import GPTToken
    from sqlalchemy import and_
    
    app_settings = get_settings()
    
    # Check if there are any active ChatGPT authorizations
    active_tokens = db.query(GPTToken).filter(
        and_(
            GPTToken.workspace_id == workspace.id,
            GPTToken.revoked == False,
        )
    ).count()
    
    has_active_connection = active_tokens > 0
    
    # Build conditional HTML parts to avoid backslash issues in f-strings
    status_class = 'active' if has_active_connection else 'inactive'
    status_text = 'Active ChatGPT connection' if has_active_connection else 'No active ChatGPT connection'
    
    if has_active_connection:
        warning_html = '<div class="warning"><strong>⚠️ Warning:</strong> Revoking will disconnect ChatGPT from your GA data. You will need to re-authorize in ChatGPT to use it again.</div>'
        confirm_msg = "Are you sure you want to revoke your ChatGPT connection? You will need to re-authorize in ChatGPT."
        token_input_html = f'<input type="hidden" name="token" value="{token or ""}">' if token else ''
        form_html = f'<form method="POST" action="/revoke-chatgpt">{token_input_html}<button type="submit" class="button" onclick="return confirm(\'{confirm_msg}\');">Revoke ChatGPT Connection</button></form>'
    else:
        warning_html = '<div class="info">You do not have any active ChatGPT connections to revoke.</div>'
        form_html = ''
    
    token_param = f'?token={token}' if token else ''
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Revoke ChatGPT Connection - Ask My Analytics</title>
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                max-width: 600px; 
                margin: 50px auto; 
                padding: 20px; 
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            h1 {{ color: #333; margin-top: 0; }}
            .info {{ 
                background: #e7f3ff; 
                padding: 15px; 
                border-radius: 5px; 
                margin: 20px 0;
                border-left: 4px solid #007bff;
            }}
            .warning {{ 
                background: #fff3cd; 
                padding: 15px; 
                border-radius: 5px; 
                margin: 20px 0;
                border-left: 4px solid #ffc107;
            }}
            .button {{
                display: inline-block;
                padding: 12px 24px;
                background: #dc3545;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 10px 5px 10px 0;
                border: none;
                cursor: pointer;
                font-size: 16px;
            }}
            .button:hover {{
                background: #c82333;
            }}
            .button-secondary {{
                background: #6c757d;
            }}
            .button-secondary:hover {{
                background: #5a6268;
            }}
            .status {{
                padding: 10px;
                margin: 10px 0;
                border-radius: 5px;
            }}
            .status.active {{
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}
            .status.inactive {{
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Revoke ChatGPT Connection</h1>
            
            <div class="info">
                <strong>What this does:</strong>
                <ul style="margin: 10px 0;">
                    <li>Revokes your current ChatGPT authorization</li>
                    <li>Next time you use the Custom GPT, you'll need to re-authorize</li>
                    <li>You'll be able to select a different GA property during re-authorization</li>
                </ul>
            </div>
            
            <div class="status {status_class}">
                <strong>Current Status:</strong> {status_text}
            </div>
            
            {warning_html}
            
            {form_html}
            
            <p style="margin-top: 30px;">
                <a href="{app_settings.APP_BASE_URL}/ga/connect{token_param}" class="button button-secondary">Connect/Change GA Property</a>
                <a href="{app_settings.APP_BASE_URL}/authorize-gpt{token_param}" class="button button-secondary">Re-authorize ChatGPT</a>
            </p>
        </div>
    </body>
    </html>
    """
    
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)


@router.post("/revoke-chatgpt")
async def revoke_chatgpt_action(
    token: Optional[str] = Form(None, description="JWT token for authentication"),
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_user_default_workspace),
    db: Session = Depends(get_db),
):
    """
    Revoke all ChatGPT authorizations for the user's workspace.
    
    This will force the user to re-authorize in ChatGPT next time they use it,
    allowing them to go through the full flow again and select a different GA property.
    """
    from app.config import get_settings
    from app.models.gpt_token import GPTToken
    from sqlalchemy import and_
    
    app_settings = get_settings()
    
    # Revoke all active tokens for this workspace
    revoked_count = GPTOAuthService.revoke_all_workspace_tokens(db, str(workspace.id))
    
    success_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ChatGPT Connection Revoked - Ask My Analytics</title>
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                max-width: 600px; 
                margin: 50px auto; 
                padding: 20px; 
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            h1 {{ color: #28a745; margin-top: 0; }}
            .success {{
                background: #d4edda;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
                border-left: 4px solid #28a745;
                color: #155724;
            }}
            .button {{
                display: inline-block;
                padding: 12px 24px;
                background: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 10px 5px 10px 0;
                font-size: 16px;
            }}
            .button:hover {{
                background: #0056b3;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>✓ ChatGPT Connection Revoked</h1>
            
            <div class="success">
                <strong>Success!</strong> Your ChatGPT connection has been revoked.
                {f'Revoked {revoked_count} authorization(s).' if revoked_count > 0 else ''}
            </div>
            
            <p><strong>What's next?</strong></p>
            <ol>
                <li>Go back to ChatGPT and try to use the Custom GPT</li>
                <li>ChatGPT will ask you to authorize again</li>
                <li>During re-authorization, you'll be able to select a different GA property</li>
            </ol>
            
            <p style="margin-top: 30px;">
                <a href="{app_settings.APP_BASE_URL}/ga/connect{'?token=' + token if token else ''}" class="button">Connect/Change GA Property</a>
                <a href="{app_settings.APP_BASE_URL}/authorize-gpt{'?token=' + token if token else ''}" class="button">Re-authorize ChatGPT Now</a>
            </p>
        </div>
    </body>
    </html>
    """
    
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=success_html)

