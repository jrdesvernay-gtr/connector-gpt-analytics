#!/bin/bash

# Test script for token exchange
# Usage: ./test_token_exchange.sh AUTHORIZATION_CODE

BASE_URL="http://localhost:8000"
AUTH_CODE=${1:-""}
REDIRECT_URI="http://localhost:8000/authorize-gpt/callback"

if [ -z "$AUTH_CODE" ]; then
    echo "❌ Error: Authorization code required"
    echo "Usage: ./test_token_exchange.sh YOUR_AUTHORIZATION_CODE"
    echo ""
    echo "Get your authorization code by visiting:"
    echo "http://localhost:8000/authorize-gpt?workspace_id=YOUR_WORKSPACE_ID&redirect_uri=$REDIRECT_URI&token=YOUR_JWT_TOKEN&state=test123"
    exit 1
fi

echo "🔄 Exchanging authorization code for tokens..."
echo ""

# Exchange code for tokens
RESPONSE=$(curl -s -X POST "$BASE_URL/oauth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=$AUTH_CODE" \
  -d "redirect_uri=$REDIRECT_URI")

echo "Response:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# Check if we got tokens
if echo "$RESPONSE" | grep -q "access_token"; then
    echo "✅ Token exchange successful!"
    echo ""
    
    # Extract tokens
    ACCESS_TOKEN=$(echo "$RESPONSE" | grep -oP '"access_token":\s*"\K[^"]*' || echo "")
    REFRESH_TOKEN=$(echo "$RESPONSE" | grep -oP '"refresh_token":\s*"\K[^"]*' || echo "")
    
    if [ ! -z "$ACCESS_TOKEN" ]; then
        echo "Access Token: $ACCESS_TOKEN"
        echo ""
    fi
    
    if [ ! -z "$REFRESH_TOKEN" ]; then
        echo "Refresh Token: $REFRESH_TOKEN"
        echo ""
        echo "💡 Save these tokens! You can use the access_token to call protected endpoints."
        echo "💡 Use the refresh_token to get a new access_token when it expires."
    fi
else
    echo "❌ Token exchange failed. Check the error message above."
fi

