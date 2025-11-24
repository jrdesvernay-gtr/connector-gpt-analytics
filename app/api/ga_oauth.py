"""Google Analytics OAuth connection endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.ga import Property, PropertyList, GAConnectionResponse
from app.services.ga_oauth_service import GAOAuthService
from app.services.ga_service import GAService
from app.api.dependencies import get_current_user, get_user_default_workspace
from app.models.user import User
from app.models.workspace import Workspace
from app.models.ga_connection import GAConnection
from app.core.errors import ConnectorError, error_to_http_exception

router = APIRouter()


@router.get("/ga/connect")
async def ga_connect(
    workspace_id: str = None,
    token: str = None,  # Allow token as query parameter for browser testing
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_user_default_workspace),
    db: Session = Depends(get_db),
):
    """
    Initiate Google Analytics OAuth connection flow.
    Redirects user to Google for analytics authorization.
    
    Args:
        workspace_id: Optional workspace ID (defaults to user's default workspace)
    """
    print(f"DEBUG: GA connect endpoint called")
    print(f"DEBUG: User ID: {current_user.id}, Email: {current_user.email}")
    print(f"DEBUG: Workspace ID: {workspace.id if workspace else 'None'}")
    
    try:
        # Use provided workspace_id or default workspace
        if workspace_id:
            workspace = db.query(Workspace).filter(
                Workspace.id == workspace_id,
                Workspace.user_id == current_user.id,
            ).first()
            if not workspace:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workspace not found",
                )
        
        print(f"DEBUG: Generating authorization URL for workspace: {workspace.id}")
        authorization_url = GAOAuthService.get_authorization_url(
            workspace_id=str(workspace.id)
        )
        print(f"DEBUG: Authorization URL generated successfully")
        
        return RedirectResponse(url=authorization_url)
    except Exception as e:
        import traceback
        error_detail = f"Error in ga_connect: {type(e).__name__}: {str(e)}"
        print(f"ERROR in ga_connect: {error_detail}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail,
        )


@router.get("/ga/callback")
async def ga_callback(
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None,
    db: Session = Depends(get_db),
):
    """
    Handle Google Analytics OAuth callback.
    Exchanges authorization code for credentials and fetches properties.
    """
    print(f"DEBUG: GA callback received")
    print(f"DEBUG: Full callback URL: {request.url}")
    print(f"DEBUG: Query params: code={'Yes' if code else 'No'}, state={state}, error={error}")
    
    # Check if Google returned an error
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth error: {error}",
        )
    
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code",
        )
    
    # Parse workspace_id from state
    workspace_id, _ = GAOAuthService.parse_state(state or "")
    print(f"DEBUG: Parsed workspace_id from state: {workspace_id}")
    
    if not workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing workspace ID in state",
        )
    
    # Verify workspace exists and get the user
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    
    # Get user from workspace (we already know who they are from the JWT token used to initiate the flow)
    from app.models.user import User
    user = db.query(User).filter(User.id == workspace.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Exchange code for credentials FIRST
    print(f"DEBUG: Exchanging code for credentials...")
    try:
        credentials = GAOAuthService.exchange_code_for_credentials(code)
    except Exception as e:
        import traceback
        error_detail = f"Failed to exchange authorization code: {str(e)}"
        print(f"GA Callback Error: {error_detail}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail,
        )
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code. Check server logs for details.",
        )
    
    print(f"DEBUG: Successfully exchanged code for credentials")
    print(f"DEBUG: Has refresh_token: {bool(credentials.refresh_token)}")
    
    # Verify we got a refresh token
    if not credentials.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No refresh token received. Please try again and ensure you grant all permissions.",
        )
    
    # Get the email of the Google account that was used for GA OAuth
    # This can be DIFFERENT from the user's login email!
    # Example: User logs in with personal@gmail.com, but connects GA owned by company@gmail.com
    google_account_email = GAOAuthService.get_user_email_from_credentials(credentials)
    
    # Fallback: If we can't get email from credentials (shouldn't happen with userinfo.email scope),
    # use the logged-in user's email as a fallback
    if not google_account_email:
        print("WARNING: Could not get email from GA OAuth credentials, using logged-in user email")
        google_account_email = user.email
    
    # Fetch properties
    print(f"DEBUG: Fetching GA4 properties...")
    try:
        properties = GAService.get_properties(credentials)
        print(f"DEBUG: Got {len(properties) if properties else 0} properties")
    except ConnectorError as e:
        print(f"DEBUG: ConnectorError fetching properties: {str(e)}")
        raise error_to_http_exception(e)
    except Exception as e:
        error_detail = f"Failed to fetch properties: {type(e).__name__}: {str(e)}"
        print(f"DEBUG: Exception fetching properties: {error_detail}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail,
        )
    
    if not properties:
        print(f"DEBUG: No properties returned - returning 404")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No GA4 properties found for this account. Please ensure you have GA4 properties set up in Google Analytics.",
        )
    
    # If multiple properties, let user choose. Otherwise, auto-select the single property
    if len(properties) > 1:
        # Multiple properties: Create a temporary connection with first property to store credentials,
        # then redirect to property selection page
        first_property = properties[0]
        try:
            connection = GAOAuthService.create_or_update_connection(
                db=db,
                workspace_id=workspace_id,
                google_account_email=google_account_email,
                property_id=first_property["property_id"],
                property_name=first_property["property_name"],
                credentials=credentials,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        
        # Redirect to property selection page
        # Generate a token for the user so they can access the selection page
        from app.core.security import create_access_token
        from app.config import get_settings
        settings = get_settings()
        
        access_token = create_access_token(data={"sub": str(user.id)})
        redirect_url = f"{settings.APP_BASE_URL}/ga/select-property?workspace_id={workspace_id}&token={access_token}"
        return RedirectResponse(url=redirect_url)
    else:
        # Single property: auto-select and create connection
        first_property = properties[0]
        try:
            connection = GAOAuthService.create_or_update_connection(
                db=db,
                workspace_id=workspace_id,
                google_account_email=google_account_email,
                property_id=first_property["property_id"],
                property_name=first_property["property_name"],
                credentials=credentials,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        
        # Redirect to success page
        from app.config import get_settings
        settings = get_settings()
        redirect_url = f"{settings.APP_BASE_URL}/ga/success?workspace_id={workspace_id}&property_id={first_property['property_id']}"
        return RedirectResponse(url=redirect_url)


@router.get("/ga/properties", response_model=PropertyList)
async def get_ga_properties(
    workspace_id: str = None,
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_user_default_workspace),
    db: Session = Depends(get_db),
):
    """
    Get list of GA4 properties for the workspace's GA connection.
    Requires an active GA connection.
    """
    # Use provided workspace_id or default workspace
    if workspace_id:
        workspace = db.query(Workspace).filter(
            Workspace.id == workspace_id,
            Workspace.user_id == current_user.id,
        ).first()
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )
    
    # Get GA connection for workspace
    connection = db.query(GAConnection).filter(
        GAConnection.workspace_id == workspace.id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No GA connection found for this workspace. Please connect Google Analytics first.",
        )
    
    # Fetch properties
    try:
        properties_data = GAService.refresh_and_get_properties(connection)
    except ConnectorError as e:
        raise error_to_http_exception(e)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch properties: {str(e)}",
        )
    
    properties = [
        Property(
            property_id=prop["property_id"],
            property_name=prop["property_name"],
            account_name=prop.get("account_name"),
        )
        for prop in properties_data
    ]
    
    return PropertyList(properties=properties)


@router.post("/ga/properties/{property_id}/select", response_model=GAConnectionResponse)
@router.get("/ga/properties/{property_id}/select")  # Also support GET for browser clicks
async def select_property(
    request: Request,
    property_id: str,
    workspace_id: str = None,
    token: str = None,  # Allow token as query parameter for browser testing
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_user_default_workspace),
    db: Session = Depends(get_db),
):
    """
    Select/set a GA4 property as the default for a workspace.
    Updates the existing connection or creates a new one.
    
    Supports both POST (API) and GET (browser click) requests.
    """
    # Use provided workspace_id or default workspace
    if workspace_id:
        workspace = db.query(Workspace).filter(
            Workspace.id == workspace_id,
            Workspace.user_id == current_user.id,
        ).first()
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )
    
    # Get GA connection for workspace
    connection = db.query(GAConnection).filter(
        GAConnection.workspace_id == workspace.id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No GA connection found. Please connect Google Analytics first.",
        )
    
    # Fetch properties to verify the property exists
    try:
        properties_data = GAService.refresh_and_get_properties(connection)
    except ConnectorError as e:
        raise error_to_http_exception(e)
    
    # Find the property
    selected_property = None
    for prop in properties_data:
        if prop["property_id"] == property_id:
            selected_property = prop
            break
    
    if not selected_property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found or not accessible",
        )
    
    # Update connection if different property
    if connection.property_id != property_id:
        connection.property_id = property_id
        connection.property_name = selected_property["property_name"]
        db.commit()
        db.refresh(connection)
    
    # For GET requests (browser clicks), redirect back to selection page
    from app.config import get_settings
    settings = get_settings()
    
    # Check request method - if GET, redirect back to selection page
    if request.method == 'GET':
        redirect_url = f"{settings.APP_BASE_URL}/ga/select-property?workspace_id={workspace.id}{f'&token={token}' if token else ''}"
        return RedirectResponse(url=redirect_url)
    
    # For POST requests (API), return JSON
    return GAConnectionResponse.model_validate(connection)


@router.get("/ga/connections", response_model=List[GAConnectionResponse])
async def list_connections(
    workspace_id: str = None,
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_user_default_workspace),
    db: Session = Depends(get_db),
):
    """
    List all GA connections for a workspace.
    """
    # Use provided workspace_id or default workspace
    if workspace_id:
        workspace = db.query(Workspace).filter(
            Workspace.id == workspace_id,
            Workspace.user_id == current_user.id,
        ).first()
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )
    
    connections = db.query(GAConnection).filter(
        GAConnection.workspace_id == workspace.id
    ).all()
    
    return [GAConnectionResponse.model_validate(conn) for conn in connections]


@router.get("/ga/select-property")
async def select_property_page(
    workspace_id: str,
    token: str = None,  # Allow token as query parameter for browser testing
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_user_default_workspace),
    db: Session = Depends(get_db),
):
    """
    Property selection page - shows all available GA4 properties for user to choose.
    """
    # Use provided workspace_id or default workspace
    if workspace_id:
        workspace = db.query(Workspace).filter(
            Workspace.id == workspace_id,
            Workspace.user_id == current_user.id,
        ).first()
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )
    
    # Get GA connection (should exist after OAuth callback)
    connection = db.query(GAConnection).filter(
        GAConnection.workspace_id == workspace.id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No GA connection found. Please connect Google Analytics first.",
        )
    
    # Fetch all available properties
    try:
        properties_data = GAService.refresh_and_get_properties(connection)
    except ConnectorError as e:
        raise error_to_http_exception(e)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch properties: {str(e)}",
        )
    
    # Build property selection page
    from app.config import get_settings
    settings = get_settings()
    
    properties_html = ""
    for prop in properties_data:
        is_selected = "✓ SELECTED" if prop["property_id"] == connection.property_id else "Select"
        select_url = f"{settings.APP_BASE_URL}/ga/properties/{prop['property_id']}/select?token={token or ''}"
        
        properties_html += f"""
        <div style="padding: 15px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px;">
            <h3>{prop['property_name']}</h3>
            <p><strong>Property ID:</strong> {prop['property_id']}</p>
            {f"<p><strong>Account:</strong> {prop.get('account_name', 'N/A')}</p>" if prop.get('account_name') else ''}
            <p>
                {f'<span style="color: green;">{is_selected}</span>' if prop["property_id"] == connection.property_id else f'<a href="{select_url}" style="display: inline-block; padding: 8px 16px; background: #007bff; color: white; text-decoration: none; border-radius: 3px;">Select</a>'}
            </p>
        </div>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Select GA4 Property</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
            h1 {{ color: #333; }}
            .info {{ background: #e7f3ff; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <h1>Select a Google Analytics Property</h1>
        <div class="info">
            <p>Choose which GA4 property you want to query. You can change this later.</p>
        </div>
        {properties_html}
        <p style="margin-top: 30px;">
            <a href="{settings.APP_BASE_URL}/ga/success?workspace_id={workspace.id}&property_id={connection.property_id}{f'&token={token}' if token else ''}" style="color: #007bff;">Continue with current selection →</a>
        </p>
    </body>
    </html>
    """
    
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)


@router.get("/ga/success")
async def ga_success(
    workspace_id: str,
    property_id: str,
    db: Session = Depends(get_db),
):
    """
    Success page after GA connection.
    Shows connection details.
    """
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    
    connection = db.query(GAConnection).filter(
        GAConnection.workspace_id == workspace_id,
        GAConnection.property_id == property_id,
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )
    
    return JSONResponse(
        content={
            "message": "Google Analytics connected successfully",
            "connection": {
                "id": str(connection.id),
                "property_id": connection.property_id,
                "property_name": connection.property_name,
                "google_account_email": connection.google_account_email,
            },
            "instructions": "You can now query GA4 data using the /ga/report endpoint",
        }
    )

