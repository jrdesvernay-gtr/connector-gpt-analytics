#!/usr/bin/env python3
"""
Generate OpenAPI specification for Custom GPT Actions.
This creates a Custom GPT-compatible OpenAPI 3.0 spec.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.config import get_settings

settings = get_settings()

# Get the base OpenAPI spec from FastAPI
openapi_schema = app.openapi()

# Customize for Custom GPT
openapi_schema["info"]["description"] = """
GA4 Analytics Connector - Query Google Analytics 4 data through natural language.

This API allows you to query GA4 data including:
- Sessions, users, engagement metrics
- Traffic sources and channels
- Page views and content performance
- E-commerce and conversion data
- Custom dimensions and metrics

All queries require OAuth2 authentication.
"""

# Add server URL (production)
openapi_schema["servers"] = [
    {
        "url": settings.APP_BASE_URL,
        "description": "Production server"
    }
]

# Customize OAuth2 security scheme for Custom GPT
# Custom GPT expects OAuth2 with authorization code flow
if "components" not in openapi_schema:
    openapi_schema["components"] = {}

if "securitySchemes" not in openapi_schema["components"]:
    openapi_schema["components"]["securitySchemes"] = {}

# Add OAuth2 security scheme for Custom GPT
openapi_schema["components"]["securitySchemes"]["oauth2"] = {
    "type": "oauth2",
    "flows": {
        "authorizationCode": {
            "authorizationUrl": f"{settings.APP_BASE_URL}/authorize-gpt",
            "tokenUrl": f"{settings.APP_BASE_URL}/oauth/token",
            "scopes": {
                "read": "Read access to GA4 analytics data"
            }
        }
    },
    "description": "OAuth2 authentication. Users must authorize the connector through the web interface first."
}

# Ensure the /ga/run-report endpoint has proper security and descriptions
if "paths" in openapi_schema and "/ga/run-report" in openapi_schema["paths"]:
    report_path = openapi_schema["paths"]["/ga/run-report"]
    
    if "post" in report_path:
        post_spec = report_path["post"]
        
        # Add security requirement
        post_spec["security"] = [{"oauth2": ["read"]}]
        
        # Enhance description
        post_spec["summary"] = "Query Google Analytics 4 Data"
        post_spec["description"] = """
Run a GA4 report query to retrieve analytics data.

**Common Metrics:**
- `sessions` - Number of sessions
- `totalUsers` - Total number of users
- `activeUsers` - Active users
- `screenPageViews` - Page views
- `eventCount` - Number of events
- `conversions` - Conversion count
- `totalRevenue` - Total revenue
- `engagementRate` - Engagement rate

**Common Dimensions:**
- `date` - Date dimension
- `country` - Country
- `city` - City
- `deviceCategory` - Device type (desktop/mobile/tablet)
- `sessionDefaultChannelGroup` - Traffic source channel
- `pageTitle` - Page title
- `landingPage` - Landing page

**Date Format:** YYYY-MM-DD (e.g., "2024-11-01")

**Example Queries:**
- Get daily sessions for last 30 days
- Get users by country
- Get top pages by page views
- Get conversion rate by channel
"""
        
        # Enhance request body schema with examples
        if "requestBody" in post_spec and "content" in post_spec["requestBody"]:
            content = post_spec["requestBody"]["content"]
            if "application/json" in content and "schema" in content["application/json"]:
                schema = content["application/json"]["schema"]
                
                # Add examples
                content["application/json"]["examples"] = {
                    "daily_sessions": {
                        "summary": "Daily sessions for last 30 days",
                        "value": {
                            "metrics": ["sessions", "totalUsers"],
                            "dimensions": ["date"],
                            "date_ranges": [
                                {
                                    "startDate": "2024-11-01",
                                    "endDate": "2024-11-30"
                                }
                            ]
                        }
                    },
                    "users_by_country": {
                        "summary": "Users by country",
                        "value": {
                            "metrics": ["totalUsers"],
                            "dimensions": ["country"],
                            "date_ranges": [
                                {
                                    "startDate": "2024-11-01",
                                    "endDate": "2024-11-30"
                                }
                            ]
                        }
                    },
                    "pages_by_views": {
                        "summary": "Top pages by page views",
                        "value": {
                            "metrics": ["screenPageViews"],
                            "dimensions": ["pageTitle"],
                            "date_ranges": [
                                {
                                    "startDate": "2024-11-01",
                                    "endDate": "2024-11-30"
                                }
                            ]
                        }
                    }
                }

# Remove endpoints that Custom GPT doesn't need (keep only the main query endpoint)
# But actually, let's keep them all but focus on the main one

# Output the spec
output_path = Path(__file__).parent.parent / "openapi.json"
with open(output_path, "w") as f:
    json.dump(openapi_schema, f, indent=2)

print(f"✅ OpenAPI specification generated: {output_path}")
print(f"📋 Server URL: {settings.APP_BASE_URL}")
print(f"🔐 OAuth2 Auth URL: {settings.APP_BASE_URL}/authorize-gpt")
print(f"🔑 OAuth2 Token URL: {settings.APP_BASE_URL}/oauth/token")
print("")
print("📤 This file can be uploaded to Custom GPT Actions configuration.")


