"""FastAPI application entry point."""

from typing import Optional
from fastapi import FastAPI, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.security import OAuth2PasswordBearer
from pathlib import Path
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.errors import ConnectorError, error_to_http_exception
from app.database import get_db

settings = get_settings()

# OAuth2 scheme for API documentation
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Create FastAPI app
app = FastAPI(
    title="GA Analytics Connector",
    description="GA4 to Custom GPT connector - Secure multi-tenant analytics connector",
    version="1.0.0",
)

# Configure CORS
# In production, allow the app base URL and common OAuth callback origins
if settings.ENVIRONMENT == "development":
    allowed_origins = ["*"]
else:
    # Production: allow APP_BASE_URL and common OAuth origins
    allowed_origins = [
        settings.APP_BASE_URL,
        "https://chatgpt.com",
        "https://chat.openai.com",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Error handler for ConnectorError
@app.exception_handler(ConnectorError)
async def connector_error_handler(request, exc: ConnectorError):
    """Handle ConnectorError exceptions."""
    http_exc = error_to_http_exception(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail,
    )


# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "status": "healthy",
        "service": "GA Analytics Connector",
        "version": "1.0.1",  # Updated after Railway outage - ensure fresh deployment
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/privacy-policy", response_class=HTMLResponse)
async def privacy_policy():
    """Privacy policy page."""
    template_path = Path(__file__).parent / "templates" / "privacy_policy.html"
    if template_path.exists():
        return HTMLResponse(content=template_path.read_text())
    return HTMLResponse(
        content="<h1>Privacy Policy</h1><p>Privacy policy page is being updated.</p>",
        status_code=404
    )


@app.get("/openapi.json", response_class=JSONResponse)
async def get_openapi_spec():
    """Serve the OpenAPI specification for Custom GPT Actions."""
    import json
    openapi_path = Path(__file__).parent.parent / "openapi.json"
    if openapi_path.exists():
        with open(openapi_path, "r") as f:
            return json.load(f)
    return JSONResponse(
        content={"error": "OpenAPI specification not found"},
        status_code=404
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def user_dashboard(
    token: Optional[str] = Query(None, description="JWT token for authentication"),
    db: Session = Depends(get_db),
):
    """
    User dashboard page - central hub for managing connections.
    
    Shows current GA and ChatGPT connection status and provides
    links to manage everything.
    """
    from app.models.ga_connection import GAConnection
    from app.models.gpt_token import GPTToken
    from app.models.user import User
    from app.models.workspace import Workspace
    from sqlalchemy import and_
    import logging
    
    app_settings = get_settings()
    
    # Get user if authenticated, otherwise redirect to login
    user = None
    workspace = None
    
    try:
        if token:
            from app.core.security import verify_token
            import uuid
            payload = verify_token(token)
            if payload:
                user_id = payload.get("sub")
                if user_id:
                    user_id_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
                    user = db.query(User).filter(User.id == user_id_uuid).first()
                    if user:
                        workspace = db.query(Workspace).filter(Workspace.user_id == user.id).first()
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.debug(f"Error authenticating user for dashboard: {e}")
        user = None
        workspace = None
    
    # If not authenticated, redirect to login with return URL
    if not user or not workspace:
        from urllib.parse import quote
        from fastapi.responses import RedirectResponse
        app_settings = get_settings()
        login_url = f"{app_settings.APP_BASE_URL}/auth/google/login?next={quote(app_settings.APP_BASE_URL + '/dashboard')}"
        return RedirectResponse(url=login_url, status_code=302)
    
    app_settings = get_settings()
    
    # Get current connections
    ga_connection = db.query(GAConnection).filter(
        GAConnection.workspace_id == workspace.id
    ).first()
    
    active_gpt_tokens = db.query(GPTToken).filter(
        and_(
            GPTToken.workspace_id == workspace.id,
            GPTToken.revoked == False,
        )
    ).count()
    
    has_ga_connection = ga_connection is not None
    has_chatgpt_connection = active_gpt_tokens > 0
    
    # Build dashboard HTML
    from urllib.parse import urlencode
    token_param = f"?token={token}" if token else ""
    
    # Build change property URL with workspace_id and next parameter to redirect back to dashboard
    from urllib.parse import quote
    change_property_params = {"workspace_id": str(workspace.id)}
    if token:
        change_property_params["token"] = token
    # Add next parameter to redirect back to dashboard after property selection
    dashboard_url = f"{app_settings.APP_BASE_URL}/dashboard"
    if token:
        dashboard_url += f"?token={token}"
    change_property_params["next"] = dashboard_url
    change_property_url = f"{app_settings.APP_BASE_URL}/ga/select-property?{urlencode(change_property_params)}"
    
    ga_status_html = ""
    if has_ga_connection:
        ga_status_html = f"""
        <div class="status-card connected">
            <h3>✓ Google Analytics Connected</h3>
            <p><strong>Property:</strong> {ga_connection.property_name}</p>
            <p><strong>Property ID:</strong> {ga_connection.property_id}</p>
            <p><strong>Account:</strong> {ga_connection.google_account_email}</p>
            <div class="actions">
                <a href="{change_property_url}" class="button">Change Property</a>
                <a href="{app_settings.APP_BASE_URL}/ga/connect{token_param}" class="button button-secondary">Reconnect GA</a>
            </div>
        </div>
        """
    else:
        ga_status_html = f"""
        <div class="status-card disconnected">
            <h3>✗ Google Analytics Not Connected</h3>
            <p>Connect your GA4 account to start querying analytics data.</p>
            <div class="actions">
                <a href="{app_settings.APP_BASE_URL}/ga/connect{token_param}" class="button">Connect GA4 Account</a>
            </div>
        </div>
        """
    
    chatgpt_status_html = ""
    if has_chatgpt_connection:
        chatgpt_status_html = f"""
        <div class="status-card connected">
            <h3>✓ ChatGPT Authorized</h3>
            <p>Your Custom GPT is connected and can query your GA4 data.</p>
            <div class="actions">
                <a href="{app_settings.APP_BASE_URL}/revoke-chatgpt{token_param}" class="button button-warning">Revoke Connection</a>
                <a href="{app_settings.APP_BASE_URL}/authorize-gpt{token_param}" class="button button-secondary">Re-authorize</a>
            </div>
        </div>
        """
    else:
        chatgpt_status_html = f"""
        <div class="status-card disconnected">
            <h3>✗ ChatGPT Not Authorized</h3>
            <p>Authorize your Custom GPT to access your GA4 data.</p>
            <div class="actions">
                <a href="{app_settings.APP_BASE_URL}/authorize-gpt{token_param}" class="button">Authorize ChatGPT</a>
            </div>
        </div>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard - Ask My Analytics</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; 
                background: #f5f7fa;
                color: #333;
            }}
            .container {{
                max-width: 900px;
                margin: 0 auto;
                padding: 20px;
            }}
            header {{
                background: white;
                padding: 20px 30px;
                border-radius: 8px;
                margin-bottom: 30px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            header h1 {{
                color: #1a73e8;
                margin-bottom: 5px;
            }}
            header p {{
                color: #666;
                font-size: 14px;
            }}
            .user-info {{
                text-align: right;
                margin-top: 10px;
                color: #666;
                font-size: 14px;
            }}
            .status-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .status-card {{
                background: white;
                padding: 25px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .status-card.connected {{
                border-left: 4px solid #28a745;
            }}
            .status-card.disconnected {{
                border-left: 4px solid #dc3545;
            }}
            .status-card h3 {{
                margin-bottom: 15px;
                font-size: 20px;
            }}
            .status-card p {{
                margin: 8px 0;
                color: #666;
                line-height: 1.6;
            }}
            .status-card strong {{
                color: #333;
            }}
            .actions {{
                margin-top: 20px;
                padding-top: 20px;
                border-top: 1px solid #eee;
            }}
            .button {{
                display: inline-block;
                padding: 10px 20px;
                background: #1a73e8;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin-right: 10px;
                margin-top: 5px;
                font-size: 14px;
                transition: background 0.2s;
            }}
            .button:hover {{
                background: #1557b0;
            }}
            .button-secondary {{
                background: #6c757d;
            }}
            .button-secondary:hover {{
                background: #5a6268;
            }}
            .button-warning {{
                background: #dc3545;
            }}
            .button-warning:hover {{
                background: #c82333;
            }}
            .info-box {{
                background: #e7f3ff;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 30px;
                border-left: 4px solid #1a73e8;
            }}
            .info-box h2 {{
                margin-bottom: 10px;
                color: #1a73e8;
            }}
            .info-box ul {{
                margin-left: 20px;
                margin-top: 10px;
            }}
            .info-box li {{
                margin: 5px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Ask My Analytics Dashboard</h1>
                <p>Manage your Google Analytics connections and ChatGPT authorization</p>
                <div class="user-info">
                    Logged in as: <strong>{user.email}</strong>
                </div>
            </header>
            
            <div class="info-box">
                <h2>Quick Actions</h2>
                <ul>
                    <li><strong>Change GA Property:</strong> Select a different GA4 property to query</li>
                    <li><strong>Revoke ChatGPT:</strong> Disconnect ChatGPT and re-authorize to change property</li>
                    <li><strong>Reconnect GA:</strong> Update your GA connection or connect a different account</li>
                </ul>
            </div>
            
            <div class="status-grid">
                {ga_status_html}
                {chatgpt_status_html}
            </div>
            
            <div class="info-box">
                <h2>How to Reset and Choose a Different Property</h2>
                <p><strong>Option 1: Change Property (Recommended)</strong></p>
                <ol>
                    <li>Click "Change Property" above (if GA is connected)</li>
                    <li>Select your desired GA4 property</li>
                    <li>The new property will be used for all future queries</li>
                </ol>
                
                <p style="margin-top: 15px;"><strong>Option 2: Revoke and Re-authorize</strong></p>
                <ol>
                    <li>Click "Revoke Connection" above (if ChatGPT is authorized)</li>
                    <li>Go back to ChatGPT and use the Custom GPT</li>
                    <li>You'll be asked to authorize again</li>
                    <li>During re-authorization, you can select a different property</li>
                </ol>
            </div>
        </div>
    </body>
    </html>
    """
    
    from typing import Optional
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)


# Import and register routers
from app.api import auth, google_auth, ga_oauth, gpt_oauth, ga_report

app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(google_auth.router, prefix="/auth", tags=["google-oauth"])
app.include_router(ga_oauth.router, tags=["ga-oauth"])
app.include_router(gpt_oauth.router, tags=["gpt-oauth"])
app.include_router(ga_report.router, tags=["ga-report"])

