#!/bin/bash

# Test script for GA query endpoint
# Usage: ./test_ga_query.sh YOUR_ACCESS_TOKEN

BASE_URL="http://localhost:8000"
ACCESS_TOKEN=${1:-""}

if [ -z "$ACCESS_TOKEN" ]; then
    echo "❌ Error: Access token required"
    echo "Usage: ./test_ga_query.sh YOUR_ACCESS_TOKEN"
    echo ""
    echo "Get your access token by:"
    echo "1. Visit: $BASE_URL/authorize-gpt?workspace_id=YOUR_WORKSPACE_ID&redirect_uri=$BASE_URL/authorize-gpt/callback&token=YOUR_JWT_TOKEN"
    echo "2. Copy the authorization_code from the response"
    echo "3. Exchange it: ./test_token_exchange.sh YOUR_AUTHORIZATION_CODE"
    exit 1
fi

echo "📊 Testing GA Query Endpoint"
echo "============================"
echo ""

# Calculate date range (last 30 days)
END_DATE=$(date +%Y-%m-%d)
START_DATE=$(date -v-30d +%Y-%m-%d 2>/dev/null || date -d "30 days ago" +%Y-%m-%d 2>/dev/null || echo "2024-01-01")

# Test query: Get sessions and users by date for last 30 days
echo "Query: Sessions and Total Users by Date ($START_DATE to $END_DATE)"
echo ""

RESPONSE=$(curl -s -X POST "$BASE_URL/ga/run-report" \
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

echo "Response:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# Check if we got data
if echo "$RESPONSE" | grep -q "rows"; then
    ROW_COUNT=$(echo "$RESPONSE" | grep -oP '"row_count":\s*\K\d+' || echo "0")
    if [ "$ROW_COUNT" -gt 0 ]; then
        echo "✅ Query successful! Returned $ROW_COUNT row(s)"
        echo ""
        echo "Try other queries:"
        echo "  - Sessions by channel: {\"metrics\": [\"sessions\"], \"dimensions\": [\"sessionDefaultChannelGroup\"]}"
        echo "  - Users by country: {\"metrics\": [\"totalUsers\"], \"dimensions\": [\"country\"]}"
        echo "  - Engagement rate: {\"metrics\": [\"engagementRate\", \"activeUsers\"], \"dimensions\": [\"date\"]}"
    else
        echo "⚠️  Query returned 0 rows. Check your date ranges and property connection."
    fi
else
    echo "❌ Query failed. Check the error message above."
    echo ""
    echo "Common issues:"
    echo "  - Access token expired (get a new one)"
    echo "  - No GA connection for workspace"
    echo "  - Invalid property ID"
fi

