"""Google Analytics service for fetching properties and running reports."""

from typing import List, Optional, Dict, Any
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric

from app.services.ga_oauth_service import GAOAuthService
from app.models.ga_connection import GAConnection
from app.core.errors import GAPropertyNotFoundError, OAuthTokenRevokedError

# Try to import Analytics Admin API (might need google-analytics-admin package)
try:
    from google.analytics.admin import AnalyticsAdminServiceClient
    ADMIN_API_AVAILABLE = True
except ImportError:
    try:
        from google.analytics.admin_v1beta import AnalyticsAdminServiceClient
        ADMIN_API_AVAILABLE = True
    except ImportError:
        ADMIN_API_AVAILABLE = False


class GAService:
    """Service for Google Analytics operations."""
    
    @staticmethod
    def get_properties(credentials: Credentials) -> List[Dict[str, str]]:
        """
        Fetch list of GA4 properties accessible with given credentials.
        
        Args:
            credentials: OAuth credentials with analytics access
            
        Returns:
            List of property dicts with property_id and property_name
            
        Raises:
            OAuthTokenRevokedError: If credentials are invalid
        """
        if not ADMIN_API_AVAILABLE:
            # Fallback: Use OAuth2 API to get account info and try alternative approach
            # For now, raise an error asking to install google-analytics-admin
            raise ImportError(
                "Analytics Admin API not available. Please install: pip install google-analytics-admin"
            )
        
        try:
            print(f"DEBUG: Creating AnalyticsAdminServiceClient...")
            client = AnalyticsAdminServiceClient(credentials=credentials)
            
            # List all accounts first
            print(f"DEBUG: Listing accounts...")
            accounts = client.list_accounts()
            accounts_list = list(accounts)
            print(f"DEBUG: Found {len(accounts_list)} account(s)")
            properties = []
            
            # Use account_summaries - it includes properties and is the recommended approach
            print(f"DEBUG: Using account_summaries to get properties...")
            try:
                account_summaries = client.list_account_summaries()
                account_summaries_list = list(account_summaries)
                print(f"DEBUG: Found {len(account_summaries_list)} account summary(ies)")
                
                # Create account name map from accounts list
                account_name_map = {acc.name: acc.display_name for acc in accounts_list}
                
                # Create account name map from accounts list
                account_name_map = {acc.name: acc.display_name for acc in accounts_list}
                print(f"DEBUG: Account name map: {account_name_map}")
                
                for summary in account_summaries_list:
                    # Debug: Print all fields in summary
                    print(f"DEBUG: AccountSummary fields: {dir(summary)}")
                    
                    # Get account path
                    account_path = getattr(summary, 'account', None)
                    print(f"DEBUG: Account path from summary: {account_path}")
                    
                    # Get account name from the account name map
                    account_name = "Unknown Account"
                    if account_path:
                        account_name = account_name_map.get(account_path, account_path.split("/")[-1] if "/" in account_path else account_path)
                    
                    # Try to get display name if available (might be on summary itself)
                    display_name = getattr(summary, 'display_name', None)
                    if display_name:
                        account_name = display_name
                    
                    print(f"DEBUG: Processing account summary: {account_name} (account path: {account_path})")
                    
                    # Get property summaries from the account summary
                    property_summaries = getattr(summary, 'property_summaries', None)
                    if property_summaries is None:
                        property_summaries = []
                    else:
                        property_summaries = list(property_summaries) if hasattr(property_summaries, '__iter__') else []
                    
                    print(f"DEBUG: Found {len(property_summaries)} property(ies) in account summary")
                    
                    for prop_summary in property_summaries:
                        # Debug: Print property summary fields
                        print(f"DEBUG: PropertySummary fields: {dir(prop_summary)}")
                        
                        # Extract property ID from path like "properties/123456789"
                        prop_path = getattr(prop_summary, 'property', None)
                        print(f"DEBUG: Property path: {prop_path}")
                        
                        if not prop_path:
                            continue
                        prop_id = prop_path.split("/")[-1] if "/" in prop_path else prop_path
                        prop_name = getattr(prop_summary, 'display_name', None) or prop_id
                        
                        print(f"DEBUG: Adding property: {prop_name} (ID: {prop_id})")
                        properties.append({
                            "property_id": prop_id,
                            "property_name": prop_name,
                            "account_name": account_name,
                        })
            except Exception as e:
                print(f"DEBUG: Error with account_summaries: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                # Fallback: Try listing all properties without filtering
                print(f"DEBUG: Fallback: listing all properties...")
                try:
                    property_list = client.list_properties()
                    for prop in property_list:
                        prop_id = prop.name.split("/")[-1] if "/" in prop.name else prop.name
                        properties.append({
                            "property_id": prop_id,
                            "property_name": prop.display_name,
                            "account_name": "Unknown Account",
                        })
                except Exception as e2:
                    print(f"DEBUG: Fallback also failed: {type(e2).__name__}: {str(e2)}")
                    import traceback
                    traceback.print_exc()
            
            print(f"DEBUG: Total properties found: {len(properties)}")
            return properties
        except Exception as e:
            if "invalid_grant" in str(e).lower() or "invalid_token" in str(e).lower():
                raise OAuthTokenRevokedError()
            raise
    
    @staticmethod
    def refresh_and_get_properties(connection: GAConnection) -> List[Dict[str, str]]:
        """
        Refresh credentials and fetch properties.
        
        Args:
            connection: GAConnection object with encrypted refresh token
            
        Returns:
            List of property dicts
            
        Raises:
            OAuthTokenRevokedError: If refresh token is invalid
        """
        # Refresh access token
        credentials = GAOAuthService.refresh_access_token(
            connection.refresh_token_encrypted
        )
        
        if not credentials:
            raise OAuthTokenRevokedError()
        
        return GAService.get_properties(credentials)
    
    @staticmethod
    def run_report(
        connection: GAConnection,
        metrics: List[str],
        dimensions: Optional[List[str]] = None,
        date_ranges: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Run a GA4 report using the connection.
        
        Args:
            connection: GAConnection object
            metrics: List of metric names (e.g., ['sessions', 'totalUsers'])
            dimensions: Optional list of dimension names (e.g., ['date', 'country'])
            date_ranges: Optional list of date ranges [{"startDate": "2024-01-01", "endDate": "2024-01-31"}]
            
        Returns:
            Report data with rows and totals
        """
        # Refresh access token
        credentials = GAOAuthService.refresh_access_token(
            connection.refresh_token_encrypted
        )
        
        if not credentials:
            raise OAuthTokenRevokedError()
        
        # Default date range: last 30 days
        if not date_ranges:
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            date_ranges = [{"startDate": start_date, "endDate": end_date}]
        
        # Create client
        client = BetaAnalyticsDataClient(credentials=credentials)
        
        # Build request
        request = RunReportRequest(
            property=f"properties/{connection.property_id}",
            metrics=[Metric(name=m) for m in metrics],
            dimensions=[Dimension(name=d) for d in dimensions] if dimensions else [],
            date_ranges=[
                DateRange(start_date=dr["startDate"], end_date=dr["endDate"])
                for dr in date_ranges
            ],
        )
        
        # Run report
        response = client.run_report(request=request)
        
        # Format response
        rows = []
        for row in response.rows:
            row_dict = {}
            # Add dimension values
            for i, dim_value in enumerate(row.dimension_values):
                dim_name = dimensions[i] if dimensions else f"dimension_{i}"
                row_dict[dim_name] = dim_value.value
            # Add metric values
            for i, metric_value in enumerate(row.metric_values):
                metric_name = metrics[i]
                row_dict[metric_name] = float(metric_value.value) if metric_value.value else 0
            rows.append(row_dict)
        
        # Extract totals
        totals = {}
        if response.totals:
            for i, total in enumerate(response.totals[0].metric_values):
                metric_name = metrics[i]
                totals[metric_name] = float(total.value) if total.value else 0
        
        return {
            "rows": rows,
            "totals": totals,
            "row_count": len(rows),
        }

