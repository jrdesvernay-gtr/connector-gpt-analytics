#!/bin/bash

# Complete token generation flow from start to finish
# This script walks you through the entire OAuth flow

BASE_URL="http://localhost:8000"
WORKSPACE_ID="3f8f6972-6e6b-4eb2-ab3a-51a70e58c767"  # Your workspace ID

echo "🚀 Complete Token Generation Flow"
echo "=================================="
echo ""

echo "Step 1: Get Your JWT Token (User Authentication)"
echo "-------------------------------------------------"
echo ""
echo "Visit this URL in your browser to log in:"
echo "$BASE_URL/auth/google/login"
echo ""
echo "After logging in, you'll get a JWT token on the success page."
echo ""
read -p "Paste your JWT token here: " JWT_TOKEN

if [ -z "$JWT_TOKEN" ]; then
    echo "❌ Error: JWT token is required"
    exit 1
fi

echo ""
echo "✅ JWT Token received"
echo ""

echo "Step 2: Get Authorization Code"
echo "-------------------------------"
echo ""
echo "Requesting authorization code..."
echo ""

AUTH_URL="$BASE_URL/authorize-gpt?workspace_id=$WORKSPACE_ID&redirect_uri=$BASE_URL/authorize-gpt/callback&token=$JWT_TOKEN&state=test123"

# Get authorization code
AUTH_RESPONSE=$(curl -s -i -X GET "$AUTH_URL")

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
    echo "⚠️  Could not extract authorization code from redirect URL"
    echo "Please visit this URL manually and copy the code:"
    echo "$AUTH_URL"
    echo ""
    read -p "Paste the authorization code here: " AUTH_CODE
fi

if [ -z "$AUTH_CODE" ]; then
    echo "❌ Error: Authorization code is required"
    exit 1
fi

echo "✅ Authorization Code: $AUTH_CODE"
echo ""

echo "Step 3: Exchange Authorization Code for Tokens"
echo "------------------------------------------------"
echo ""

TOKEN_RESPONSE=$(curl -s -X POST "$BASE_URL/oauth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=$AUTH_CODE" \
  -d "redirect_uri=$BASE_URL/authorize-gpt/callback")

echo "Token Exchange Response:"
echo "$TOKEN_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$TOKEN_RESPONSE"
echo ""

# Extract tokens
ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | grep -oP '"access_token":\s*"\K[^"]*' || echo "")
REFRESH_TOKEN=$(echo "$TOKEN_RESPONSE" | grep -oP '"refresh_token":\s*"\K[^"]*' || echo "")

if [ -z "$ACCESS_TOKEN" ] || [ -z "$REFRESH_TOKEN" ]; then
    echo "❌ Error: Failed to extract tokens from response"
    exit 1
fi

echo "✅ Token Exchange Successful!"
echo ""
echo "📋 Your Tokens:"
echo "==============="
echo ""
echo "Access Token:"
echo "$ACCESS_TOKEN"
echo ""
echo "Refresh Token:"
echo "$REFRESH_TOKEN"
echo ""
echo "⏰ Access Token expires in: 3600 seconds (1 hour)"
echo "💾 Refresh Token expires in: 90 days"
echo ""

# Save tokens to file
TOKEN_FILE=".tokens_$(date +%Y%m%d_%H%M%S).txt"
cat > "$TOKEN_FILE" << EOF
# Tokens generated on $(date)
ACCESS_TOKEN=$ACCESS_TOKEN
REFRESH_TOKEN=$REFRESH_TOKEN
WORKSPACE_ID=$WORKSPACE_ID
EOF

echo "💾 Tokens saved to: $TOKEN_FILE"
echo ""

echo "Step 4: Test GA Query Endpoint (Optional)"
echo "------------------------------------------"
echo ""
read -p "Do you want to test the GA query endpoint now? (y/n): " TEST_QUERY

if [ "$TEST_QUERY" = "y" ] || [ "$TEST_QUERY" = "Y" ]; then
    echo ""
    echo "Testing GA query endpoint..."
    echo ""
    
    # Calculate date range (last 7 days)
    END_DATE=$(date +%Y-%m-%d)
    START_DATE=$(date -v-7d +%Y-%m-%d 2>/dev/null || date -d "7 days ago" +%Y-%m-%d 2>/dev/null || echo "2024-01-01")
    
    QUERY_RESPONSE=$(curl -s -X POST "$BASE_URL/ga/run-report" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"metrics\": [\"sessions\", \"totalUsers\"],
        \"dimensions\": [\"date\"],
        \"date_ranges\": [{
          \"startDate\": \"$START_DATE\",
          \"endDate\": \"$END_DATE\"
        }]
      }")
    
    echo "GA Query Response:"
    echo "$QUERY_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$QUERY_RESPONSE"
    echo ""
    
    if echo "$QUERY_RESPONSE" | grep -q "rows"; then
        echo "✅ GA Query successful!"
    else
        echo "⚠️  GA Query may have failed. Check the response above."
    fi
fi

echo ""
echo "🎉 Token generation complete!"
echo ""
echo "Next steps:"
echo "  - Use the access_token to call /ga/run-report"
echo "  - When access_token expires, use refresh_token to get a new one"
echo "  - Tokens are saved in: $TOKEN_FILE"

