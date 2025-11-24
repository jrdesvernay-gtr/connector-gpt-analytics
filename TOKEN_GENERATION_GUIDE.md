# Complete Token Generation Guide

This guide walks you through generating tokens from scratch.

## Quick Start Script

Run the automated script:

```bash
./generate_tokens_from_start.sh
```

The script will:
1. Prompt you to log in and get a JWT token
2. Generate an authorization code
3. Exchange it for access and refresh tokens
4. Optionally test the GA query endpoint
5. Save tokens to a file

## Complete Flow (In Order)

The correct order is:
1. **Login** (get JWT token)
2. **Connect GA** (authorize Google Analytics access) ⚠️ **THIS IS REQUIRED FIRST!**
3. **Authorize GPT** (get authorization code)
4. **Exchange for tokens** (get access_token)
5. **Query GA** (use access_token to get data)

## Manual Steps

### Step 0: Connect Google Analytics (REQUIRED - Do This First!)

⚠️ **IMPORTANT**: You must connect your Google Analytics account before you can query GA data!

1. Get your JWT token first (see Step 1 below)
2. Visit this URL to connect GA (replace `YOUR_JWT_TOKEN`):
```
http://localhost:8000/ga/connect?token=YOUR_JWT_TOKEN
```

3. You'll be redirected to Google to authorize Analytics access
4. After authorization, you'll be redirected back and can select your GA property
5. Once connected, proceed with the GPT OAuth flow below

### Step 1: Get JWT Token (User Login)

Visit in your browser:
```
http://localhost:8000/auth/google/login
```

After logging in, you'll see a success page with a JWT token. Copy it.

### Step 2: Get Authorization Code

Visit this URL (replace `YOUR_JWT_TOKEN` with the token from Step 1):
```
http://localhost:8000/authorize-gpt?workspace_id=3f8f6972-6e6b-4eb2-ab3a-51a70e58c767&redirect_uri=http://localhost:8000/authorize-gpt/callback&token=YOUR_JWT_TOKEN&state=test123
```

You'll be redirected to a page showing the authorization code in JSON. Copy the `authorization_code` value.

### Step 3: Exchange Code for Tokens

Run this command (replace `AUTHORIZATION_CODE` with the code from Step 2):
```bash
curl -X POST http://localhost:8000/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=AUTHORIZATION_CODE" \
  -d "redirect_uri=http://localhost:8000/authorize-gpt/callback"
```

You'll get back:
- `access_token` - Use this to call protected endpoints (expires in 1 hour)
- `refresh_token` - Use this to get new access tokens (expires in 90 days)

### Step 4: Test GA Query

⚠️ **IMPORTANT**: Make sure you've connected Google Analytics (Step 0) before testing!

Use ONLY the `access_token` value (not the entire JSON response) to query GA4 data:

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

**Note**: Replace `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` with your actual `access_token` value from Step 3 (just the token string, not the JSON).

**Common Error**: If you get `{"detail":"No GA connection found for this workspace"}`, you need to complete Step 0 first!

## Refresh Access Token

When your access token expires, refresh it:
```bash
curl -X POST http://localhost:8000/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=YOUR_REFRESH_TOKEN"
```

## Token Lifetimes

- **Access Token**: 1 hour (3600 seconds)
- **Refresh Token**: 90 days
- **Authorization Code**: 10 minutes

## Troubleshooting

### "Not authenticated" error
- Make sure you're using a valid JWT token
- Check that the token hasn't expired

### "Invalid or expired authorization code"
- Authorization codes expire after 10 minutes
- Generate a new one if it's been too long

### "No GA connection found"
- Make sure you've connected Google Analytics first via `/ga/connect`
- Verify your workspace has a GA connection

### Access token expired
- Use the refresh token to get a new access token
- Or generate new tokens from scratch

