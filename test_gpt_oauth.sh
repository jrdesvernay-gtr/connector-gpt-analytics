#!/bin/bash

# Test script for GPT OAuth flow
# Usage: ./test_gpt_oauth.sh YOUR_JWT_TOKEN YOUR_WORKSPACE_ID

BASE_URL="http://localhost:8000"
JWT_TOKEN=${1:-""}
WORKSPACE_ID=${2:-"3f8f6972-6e6b-4eb2-ab3a-51a70e58c767"}  # Default from previous test
REDIRECT_URI="https://chatgpt.com/callback"
STATE="test123"

if [ -z "$JWT_TOKEN" ]; then
    echo "❌ Error: JWT token required"
    echo "Usage: ./test_gpt_oauth.sh YOUR_JWT_TOKEN [WORKSPACE_ID]"
    echo ""
    echo "Get your JWT token by visiting: $BASE_URL/auth/google/login"
    exit 1
fi

echo "🧪 Testing GPT OAuth Flow"
echo "=========================="
echo ""
echo "Step 1: Testing Authorization Endpoint"
echo "--------------------------------------"
echo "GET $BASE_URL/authorize-gpt?workspace_id=$WORKSPACE_ID&redirect_uri=$REDIRECT_URI&token=$JWT_TOKEN&state=$STATE"
echo ""

# Test authorization endpoint
AUTH_RESPONSE=$(curl -s -i -X GET "$BASE_URL/authorize-gpt?workspace_id=$WORKSPACE_ID&redirect_uri=$REDIRECT_URI&token=$JWT_TOKEN&state=$STATE")

# Extract the Location header (redirect URL)
REDIRECT_LOCATION=$(echo "$AUTH_RESPONSE" | grep -i "Location:" | cut -d' ' -f2 | tr -d '\r')

if [ -z "$REDIRECT_LOCATION" ]; then
    echo "❌ Error: No redirect location found"
    echo "Response:"
    echo "$AUTH_RESPONSE"
    exit 1
fi

echo "✅ Authorization successful!"
echo "Redirect URL: $REDIRECT_LOCATION"
echo ""

# Extract authorization code from redirect URL
AUTH_CODE=$(echo "$REDIRECT_LOCATION" | grep -oP 'code=\K[^&]*' || echo "")

if [ -z "$AUTH_CODE" ]; then
    echo "⚠️  Warning: Could not extract authorization code from redirect URL"
    echo "Please extract it manually and run Step 2 with:"
    echo "curl -X POST $BASE_URL/oauth/token -d 'grant_type=authorization_code' -d 'code=YOUR_CODE' -d 'redirect_uri=$REDIRECT_URI'"
    exit 0
fi

echo "Authorization Code: $AUTH_CODE"
echo ""

echo "Step 2: Testing Token Exchange"
echo "-------------------------------"
echo "POST $BASE_URL/oauth/token"
echo ""

# Exchange code for tokens
TOKEN_RESPONSE=$(curl -s -X POST "$BASE_URL/oauth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=$AUTH_CODE" \
  -d "redirect_uri=$REDIRECT_URI")

echo "Response:"
echo "$TOKEN_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$TOKEN_RESPONSE"
echo ""

# Extract refresh token if available
REFRESH_TOKEN=$(echo "$TOKEN_RESPONSE" | grep -oP '"refresh_token":\s*"\K[^"]*' || echo "")

if [ -z "$REFRESH_TOKEN" ]; then
    echo "⚠️  Warning: Could not extract refresh token"
    echo "Token exchange may have failed. Check the response above."
    exit 1
fi

echo "✅ Token exchange successful!"
echo "Refresh Token: $REFRESH_TOKEN"
echo ""

echo "Step 3: Testing Token Refresh"
echo "------------------------------"
echo "POST $BASE_URL/oauth/token (refresh)"
echo ""

# Refresh the token
REFRESH_RESPONSE=$(curl -s -X POST "$BASE_URL/oauth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=$REFRESH_TOKEN")

echo "Response:"
echo "$REFRESH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$REFRESH_RESPONSE"
echo ""

ACCESS_TOKEN=$(echo "$REFRESH_RESPONSE" | grep -oP '"access_token":\s*"\K[^"]*' || echo "")

if [ -z "$ACCESS_TOKEN" ]; then
    echo "⚠️  Warning: Could not extract access token from refresh response"
    exit 1
fi

echo "✅ Token refresh successful!"
echo "New Access Token: $ACCESS_TOKEN"
echo ""
echo "🎉 All tests passed!"
echo ""
echo "You can now use the access token to call protected endpoints."
echo "Next: Implement /ga/run-report endpoint to test with GA queries."

