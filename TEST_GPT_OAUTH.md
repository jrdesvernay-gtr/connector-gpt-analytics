# Testing GPT OAuth Flow

This guide walks through testing the GPT OAuth endpoints step by step.

## Prerequisites

1. ✅ You must be logged in and have a JWT token
2. ⚠️ **REQUIRED**: You must have connected Google Analytics (see Step 0 below)
3. You must have a workspace with a GA connection

## Step 0: Connect Google Analytics (REQUIRED FIRST!)

**Before you can test GPT OAuth or query GA data, you must connect your Google Analytics account!**

1. Get your JWT token first (from user login below)
2. Visit this URL to connect GA (replace `YOUR_JWT_TOKEN`):
```
http://localhost:8000/ga/connect?token=YOUR_JWT_TOKEN
```

3. You'll be redirected to Google to authorize Analytics access
4. After authorization, select your GA4 property
5. Once you see the success message, proceed with the GPT OAuth flow below

**Important**: If you skip this step, the GA query endpoint will return `{"detail":"No GA connection found for this workspace"}`!

## Step 1: Get Your User Token

First, log in to get a JWT token (if you don't already have one):

```bash
# Visit in browser:
http://localhost:8000/auth/google/login

# After successful login, you'll get a JWT token in the success page
# Or use the token from your previous test
```

Save your JWT token. Example: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

## Step 2: Get Your Workspace ID

You need your workspace ID. From your previous tests, it was: `ae11b4fe-3fd6-48b2-8a48-99ef96dfc163`

You can also check your workspace by visiting:
```
http://localhost:8000/auth/me?token=YOUR_JWT_TOKEN
```

## Step 3: Test Authorization Endpoint

Visit the authorization endpoint in your browser (replace `YOUR_JWT_TOKEN` and `YOUR_WORKSPACE_ID`):

**For testing, use our local callback URL:**
```
http://localhost:8000/authorize-gpt?workspace_id=YOUR_WORKSPACE_ID&redirect_uri=http://localhost:8000/authorize-gpt/callback&token=YOUR_JWT_TOKEN&state=test123
```

**Expected Result:**
- You should be redirected to `http://localhost:8000/authorize-gpt/callback?code=AUTHORIZATION_CODE&state=test123`
- The callback page will display a JSON response with the authorization code
- Copy the `authorization_code` from the response

**Note:** 
- If you get "Not authenticated", make sure you're passing the token as a query parameter.
- For production, use your actual Custom GPT callback URL as the `redirect_uri`.
- For testing, we use `http://localhost:8000/authorize-gpt/callback` to see the code.

## Step 4: Test Token Exchange

Once you have the authorization code from Step 3, exchange it for tokens:

```bash
curl -X POST http://localhost:8000/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  
  -d "code=AUTHORIZATION_CODE_FROM_STEP_3" \
  -d "redirect_uri=http://localhost:8000/authorize-gpt/callback"
```

**Note:** Use the same `redirect_uri` that you used in Step 3.

**Expected Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "random_refresh_token_string",
  "scope": "read"
}
```

## Step 5: Test Token Refresh

Use the refresh token from Step 4 to get a new access token:

```bash
curl -X POST http://localhost:8000/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=REFRESH_TOKEN_FROM_STEP_4"
```

**Expected Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "scope": "read"
}
```

## Step 6: Test GA Query Endpoint

**⚠️ Make sure you've completed Step 0 (Connect GA) first!**

Use the `access_token` from Step 4 to query GA4 data. **Important**: Use ONLY the `access_token` value, not the entire JSON response!

```bash
curl -X POST http://localhost:8000/ga/run-report \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "metrics": ["sessions", "totalUsers"],
    "dimensions": ["date"],
    "date_ranges": [{
      "startDate": "2024-01-01",
      "endDate": "2024-01-31"
    }]
  }'
```

**Example** (replace with your actual access_token):
```bash
curl -X POST http://localhost:8000/ga/run-report \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "metrics": ["sessions", "totalUsers"],
    "dimensions": ["date"],
    "date_ranges": [{
      "startDate": "2024-01-01",
      "endDate": "2024-01-31"
    }]
  }'
```

**⚠️ Common Mistake**: Don't paste the entire JSON response like this:
```bash
# ❌ WRONG - Don't do this!
-H "Authorization: Bearer {\"access_token\":\"...\",\"scope\":\"read\"}"
```

**✅ Correct** - Extract just the access_token value:
```bash
# ✅ CORRECT - Use only the access_token string
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Expected Response:**
```json
{
  "row_count": 31,
  "rows": [...],
  "totals": {...}
}
```

## Common Issues

### "Not authenticated" error
- Make sure you're passing the JWT token as a query parameter: `?token=YOUR_TOKEN`
- Check that your token hasn't expired

### "Workspace not found or access denied"
- Verify the workspace_id belongs to your user account
- Check that you're authenticated with the correct user

### "No GA connection found for this workspace"
- **You must complete Step 0 first!** Connect Google Analytics via `/ga/connect?token=YOUR_JWT_TOKEN`
- Verify that a GA connection exists by checking the success message after connecting

### "Invalid or expired GPT token"
- Make sure you're using the `access_token` value only, not the entire JSON response
- Check that the token hasn't expired (they expire in 1 hour)
- Verify you're using the token from Step 4 (token exchange), not the JWT from Step 1
- Make sure the server has been restarted after code changes

### "Invalid or expired authorization code"
- Authorization codes expire after 10 minutes
- Make sure you're using the code immediately after generating it

## Next Steps

Once OAuth is working, we'll implement the `/ga/run-report` endpoint that uses these tokens.

