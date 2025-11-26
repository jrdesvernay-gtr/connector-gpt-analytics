"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.security import OAuth2PasswordBearer
from pathlib import Path

from app.config import get_settings
from app.core.errors import ConnectorError, error_to_http_exception

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


# Import and register routers
from app.api import auth, google_auth, ga_oauth, gpt_oauth, ga_report

app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(google_auth.router, prefix="/auth", tags=["google-oauth"])
app.include_router(ga_oauth.router, tags=["ga-oauth"])
app.include_router(gpt_oauth.router, tags=["gpt-oauth"])
app.include_router(ga_report.router, tags=["ga-report"])

