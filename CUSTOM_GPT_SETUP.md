# Custom GPT Configuration Guide

## Step 11: OpenAPI Spec ✅

The OpenAPI specification has been generated: `openapi.json`

This spec includes:
- OAuth2 authorization flow configuration
- `/ga/run-report` endpoint documentation
- Request/response schemas
- Example queries
- Common metrics and dimensions reference

## Step 12: Configure Custom GPT in ChatGPT

### Prerequisites
- [x] Production API deployed and working
- [x] OpenAPI spec generated (`openapi.json`)
- [x] OAuth endpoints working

### Setup Steps

1. **Open ChatGPT Custom GPT Builder**
   - Go to [chat.openai.com](https://chat.openai.com)
   - Click your profile → "My GPTs" or go to: https://chat.openai.com/gpts
   - Click "Create a GPT" or "+ Create"

2. **Configure Basic Information**
   - **Name**: "GA4 Analytics Assistant" (or your preferred name)
   - **Description**: "Query your Google Analytics 4 data with natural language. Get insights on sessions, users, traffic sources, page performance, and more."
   - **Instructions**: See system prompt below

3. **Add Actions (API Integration)**
   - Click "Add Action" or go to "Configure" tab
   - Click "Import from URL" or "Upload file"
   - Either:
     - **Upload file**: Upload the `openapi.json` file
     - **Paste URL**: `https://ga.connector.get-to-rev.com/openapi.json` (if available)
   
4. **Configure OAuth Settings**
   After uploading the OpenAPI spec, configure OAuth:
   
   - **Client Authentication**: OAuth
   - **Authorization URL**: `https://ga.connector.get-to-rev.com/authorize-gpt`
   - **Token URL**: `https://ga.connector.get-to-rev.com/oauth/token`
   - **Client ID**: Leave empty (not required for our implementation)
   - **Client Secret**: Leave empty (not required)
   - **Scope**: `read`
   - **Token Exchange Method**: POST
   - **Auth Type**: OAuth

5. **Save and Test**
   - Click "Save" or "Update"
   - Test the GPT by asking: "What were my sessions yesterday?"
   - On first use, you'll be prompted to authorize via OAuth

### System Prompt (Instructions)

```
You are a Google Analytics 4 (GA4) analytics assistant. Your role is to help users query and understand their GA4 data through natural language.

**Your Capabilities:**
- Query GA4 data including sessions, users, page views, traffic sources, and more
- Analyze trends over time
- Compare metrics across dimensions (country, device, channel, etc.)
- Provide insights and recommendations based on the data

**How to Use the API:**
- When a user asks about analytics data, use the `/ga/run-report` endpoint
- Extract the relevant metrics and dimensions from the user's question
- Use appropriate date ranges (default to last 30 days if not specified)
- Always format dates as YYYY-MM-DD
- Use clear, natural language to explain the results

**Common Metrics:**
- sessions, totalUsers, activeUsers
- screenPageViews, eventCount
- conversions, totalRevenue
- engagementRate, averageSessionDuration

**Common Dimensions:**
- date, country, city
- deviceCategory, sessionDefaultChannelGroup
- pageTitle, landingPage

**Example Queries:**
- "What were my sessions last week?" → Query sessions by date for last 7 days
- "Show me users by country" → Query totalUsers dimensioned by country
- "What are my top pages?" → Query screenPageViews dimensioned by pageTitle

Always be helpful and provide context for the numbers you return.
```

### Alternative: Manual OAuth Setup

If the OpenAPI spec's OAuth configuration doesn't work automatically:

1. In Custom GPT Actions configuration
2. Set **Privacy Policy URL**: `https://ga.connector.get-to-rev.com/privacy-policy`
3. In the OAuth section:
   - **Authorization URL**: `https://ga.connector.get-to-rev.com/authorize-gpt`
   - **Token URL**: `https://ga.connector.get-to-rev.com/oauth/token`
   - **Client ID**: (leave empty)
   - **Client Secret**: (leave empty)
   - **Scope**: `read`

## Step 13: End-to-End Testing

After configuring the Custom GPT:

1. **Authorize the Connection**
   - Ask the GPT a question like: "What were my sessions yesterday?"
   - You'll be redirected to authorize
   - Complete the OAuth flow

2. **Test Basic Queries**
   - "Show me my sessions for the last 7 days"
   - "What are my top traffic sources?"
   - "How many users visited my site last month?"

3. **Test Complex Queries**
   - "Compare sessions by device type"
   - "Show me users by country for the last 30 days"
   - "What are my top 10 pages by page views?"

4. **Verify Error Handling**
   - Test with invalid date ranges
   - Test when disconnected

## Troubleshooting

### OAuth Authorization Fails
- Check that the authorization URL is correct
- Verify the workspace has a GA connection
- Check Railway logs for errors

### "No GA connection found"
- User needs to connect GA first via: `https://ga.connector.get-to-rev.com/ga/connect`
- Verify the workspace has connected properties

### Token Expired
- The GPT should automatically refresh tokens
- If not, user needs to re-authorize

### API Not Responding
- Check Railway deployment status
- Verify the production URL is correct
- Check CORS settings

## Next Steps

- Monitor query logs in your database
- Set up error alerts
- Consider rate limiting
- Add more endpoints as needed

