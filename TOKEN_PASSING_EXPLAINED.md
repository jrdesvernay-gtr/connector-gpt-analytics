# Token Passing Mechanism Explained

This document explains how different types of tokens are passed through the OAuth flow.

---

## Types of Tokens

1. **JWT Access Tokens** (User Authentication)
   - Used to authenticate users in our web app
   - Format: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (JSON Web Token)
   - Contains: `{sub: user_id, exp: expiration, type: "access"}`

2. **Authorization Codes** (GPT OAuth Flow)
   - Temporary codes used in OAuth2 authorization code flow
   - Format: JWT token with `type: "authorization_code"`
   - Short-lived (typically 10 minutes)

3. **GPT Access Tokens** (Custom GPT API Access)
   - Used by ChatGPT to call our API
   - Format: JWT token with `type: "gpt_access"`
   - Contains: `{workspace_id: "...", exp: expiration, type: "gpt_access"}`

4. **Refresh Tokens** (Long-lived tokens)
   - Opaque strings stored in database
   - Used to get new access tokens without re-authorization
   - Never passed in URLs (stored securely)

---

## How Tokens Are Passed

### 1. JWT Tokens (User Authentication) - **URL Query Parameters**

**Where:** Passed as `?token=JWT_TOKEN` in URLs during web redirects

**Why:** This allows browser-based authentication flow without requiring cookies or sessions.

**Example Flow:**
```
1. User logs in → JWT token generated
2. Redirect to: /ga/connect?token=eyJhbGci...
3. Token validated in endpoint
4. Redirect to: /ga/select-property?token=eyJhbGci...
5. Token validated again
```

**Code Example:**
```python
# After Google login
access_token = create_access_token(data={"sub": str(user.id)})
redirect_url = f"{settings.APP_BASE_URL}/ga/connect?token={access_token}"

# In endpoint
@router.get("/ga/connect")
async def ga_connect(
    token: str = Query(None),  # Extract from URL
    current_user: User = Depends(get_current_user),  # Validates token
):
    ...
```

**Security Note:** 
- ✅ Works for browser-based flows
- ✅ Token is visible in browser history (but short-lived)
- ⚠️ Not ideal for mobile apps (better to use Authorization header)
- ✅ In production, consider adding token expiration and rate limiting

---

### 2. Authorization Codes (GPT OAuth) - **URL Query Parameters in OAuth Redirect**

**Where:** Passed in the OAuth callback URL as `?code=AUTHORIZATION_CODE`

**Why:** Standard OAuth2 authorization code flow requires this format.

**Example Flow:**
```
1. User clicks "Authorize" in /authorize-gpt
2. Authorization code generated (JWT with type="authorization_code")
3. Redirect to: https://chat.openai.com/oauth/callback?code=eyJhbGci...&state=...
4. ChatGPT receives code
5. ChatGPT exchanges code for tokens via POST /oauth/token
```

**Code Example:**
```python
# Generate authorization code
authorization_code = GPTOAuthService.create_authorization_code(str(workspace.id))
# Code is a JWT: {"workspace_id": "...", "type": "authorization_code", "exp": ...}

# Build redirect URL
parsed_uri = urlparse(redirect_uri)  # redirect_uri from ChatGPT
query_params = parse_qs(parsed_uri.query)
query_params['code'] = [authorization_code]  # Add code to URL
query_params['state'] = [state]  # Preserve state

# Redirect to ChatGPT
redirect_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, ..., new_query, ...))
return RedirectResponse(url=redirect_url, status_code=302)
```

**Security Note:**
- ✅ Standard OAuth2 pattern
- ✅ Code is short-lived (10 minutes typically)
- ✅ Code can only be exchanged once
- ✅ ChatGPT receives it over HTTPS

---

### 3. GPT Access Tokens - **HTTP Authorization Header**

**Where:** Passed in `Authorization: Bearer ACCESS_TOKEN` header for API calls

**Why:** This is the standard way to pass access tokens to APIs (not in URLs).

**Example Flow:**
```
1. ChatGPT exchanges authorization code → gets access_token
2. ChatGPT makes API call:
   POST /ga/run-report
   Authorization: Bearer eyJhbGci...
   Content-Type: application/json
   {"metrics": ["sessions"], ...}
3. Our server validates token in header
```

**Code Example:**
```python
# ChatGPT side (example)
import requests
response = requests.post(
    "https://ga.connector.get-to-rev.com/ga/run-report",
    headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    },
    json={
        "metrics": ["sessions"],
        "dimensions": ["date"],
        ...
    }
)

# Our server side
from fastapi.security import HTTPBearer

async def get_valid_gpt_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer()),
    db: Session = Depends(get_db),
):
    token = credentials.credentials  # Extract from "Bearer TOKEN"
    gpt_token = GPTOAuthService.validate_access_token(db, token)
    return {"gpt_token": gpt_token, "workspace": workspace}
```

**Security Note:**
- ✅ Standard OAuth2 bearer token pattern
- ✅ Token not visible in URLs
- ✅ Works well for API calls
- ✅ Can be stored securely by ChatGPT

---

### 4. Refresh Tokens - **Never Passed in URLs**

**Where:** Stored securely in database, passed only in POST request body to `/oauth/token`

**Why:** Refresh tokens are long-lived credentials and must be kept secret.

**Example Flow:**
```
1. Initial token exchange returns refresh_token
2. Refresh token stored in database (hashed)
3. When access token expires, ChatGPT calls:
   POST /oauth/token
   grant_type=refresh_token
   refresh_token=ZA_8JUa0afygfXlx...
4. Server validates, returns new access_token
```

**Code Example:**
```python
# Token exchange response
{
    "access_token": "eyJhbGci...",
    "refresh_token": "ZA_8JUa0afygfXlx...",  # Opaque string
    "expires_in": 3600,
    "token_type": "bearer"
}

# Refresh token stored in database (hashed)
gpt_token = GPTToken(
    workspace_id=workspace.id,
    access_token_hash=hash_access_token(access_token),
    refresh_token="ZA_8JUa0afygfXlx...",  # Stored as-is (opaque)
    expires_at=datetime.utcnow() + timedelta(hours=1)
)

# When refreshing
POST /oauth/token
Content-Type: application/x-www-form-urlencoded
grant_type=refresh_token&refresh_token=ZA_8JUa0afygfXlx...
```

**Security Note:**
- ✅ Never exposed in URLs
- ✅ Only sent in POST body over HTTPS
- ✅ Can be revoked at any time
- ✅ Long-lived but can be rotated

---

## Complete Flow with Token Passing

### Flow 1: User Login (JWT Token via URL)

```
1. User visits: /auth/google/login?next=/authorize-gpt?redirect_uri=...
   ↓
2. Google OAuth → /auth/google/callback?code=GOOGLE_CODE
   ↓
3. Server generates JWT: create_access_token({sub: user_id})
   ↓
4. Redirect: /authorize-gpt?redirect_uri=...&token=JWT_TOKEN
   ↑ Token passed in URL query parameter
```

### Flow 2: GA Connection (JWT Token via URL)

```
1. /authorize-gpt detects no GA connection
   ↓
2. Redirect: /ga/connect?token=JWT_TOKEN&next=/authorize-gpt?...
   ↑ Token passed in URL query parameter
   ↓
3. GA OAuth → /ga/callback?code=GA_CODE&state=workspace_id:csrf
   ↓
4. Server generates new JWT: create_access_token({sub: user_id})
   ↓
5. Redirect: /ga/select-property?workspace_id=...&token=JWT_TOKEN&next=/authorize-gpt?...
   ↑ Token passed in URL query parameter
```

### Flow 3: GPT Authorization (Authorization Code via URL)

```
1. User clicks "Authorize" in /authorize-gpt
   ↓
2. Server generates authorization code (JWT with type="authorization_code")
   ↓
3. Redirect: https://chat.openai.com/oauth/callback?code=AUTH_CODE&state=STATE
   ↑ Authorization code passed in URL (OAuth2 standard)
   ↓
4. ChatGPT receives code
   ↓
5. ChatGPT calls: POST /oauth/token
   Body: grant_type=authorization_code&code=AUTH_CODE
   ↑ Code passed in POST body
   ↓
6. Server returns:
   {
     "access_token": "eyJhbGci...",
     "refresh_token": "ZA_8JUa0afygfXlx..."
   }
   ↑ Tokens returned in JSON response
```

### Flow 4: API Calls (Access Token via Header)

```
1. ChatGPT stores access_token
   ↓
2. ChatGPT makes API call:
   POST /ga/run-report
   Authorization: Bearer eyJhbGci...
   ↑ Access token passed in Authorization header
   ↓
3. Server validates token and returns GA data
```

### Flow 5: Token Refresh (Refresh Token via POST Body)

```
1. Access token expires (1 hour)
   ↓
2. ChatGPT calls:
   POST /oauth/token
   grant_type=refresh_token
   refresh_token=ZA_8JUa0afygfXlx...
   ↑ Refresh token passed in POST body (never in URL)
   ↓
3. Server validates and returns new access_token
```

---

## Summary Table

| Token Type | Where Passed | Method | Visibility | Security Level |
|------------|--------------|--------|------------|----------------|
| **JWT (User Auth)** | URL Query (`?token=...`) | GET redirects | Visible in URL | Medium (short-lived) |
| **Authorization Code** | URL Query (`?code=...`) | OAuth redirect | Visible in URL | Medium (one-time use) |
| **GPT Access Token** | HTTP Header (`Authorization: Bearer ...`) | API calls | Not in URL | High (standard OAuth2) |
| **Refresh Token** | POST Body only | POST `/oauth/token` | Never in URL | High (long-lived) |

---

## Security Considerations

### ✅ What We're Doing Right:
1. **JWT tokens in URLs** - Acceptable for browser-based flows, tokens are short-lived
2. **Authorization codes in URLs** - Standard OAuth2 pattern, codes are one-time use
3. **Access tokens in headers** - Industry standard, not exposed in URLs
4. **Refresh tokens never in URLs** - Kept secure, only in POST body

### ⚠️ Potential Improvements:
1. **Session cookies** - Could use HTTP-only cookies instead of URL tokens for web flow
2. **PKCE** - Could add PKCE to authorization code flow for extra security
3. **Token rotation** - Could rotate refresh tokens on each use
4. **Rate limiting** - Should rate limit token exchange endpoints

---

## Why This Approach?

1. **Browser-based flow** - Users are redirected through OAuth, so tokens must be in URLs initially
2. **Stateless** - No session management required (tokens carry user identity)
3. **Standard OAuth2** - Follows OAuth2 best practices for each token type
4. **Simple** - Easy to debug and test (tokens visible in browser dev tools)

---

## Alternative: Session-Based (Future Improvement)

Instead of passing JWT in URLs, we could:

```python
# Set HTTP-only cookie after login
response.set_cookie(
    key="session_token",
    value=session_token,
    httponly=True,  # Not accessible via JavaScript
    secure=True,    # HTTPS only
    samesite="lax"
)

# Validate from cookie instead of query param
@router.get("/ga/connect")
async def ga_connect(
    request: Request,  # Read cookie from request
    ...
):
    session_token = request.cookies.get("session_token")
    # Validate session token
```

**Benefits:**
- ✅ Tokens not in URLs
- ✅ More secure (HTTP-only cookies)
- ✅ Better UX (no visible tokens)

**Trade-offs:**
- ❌ More complex (session management)
- ❌ CSRF protection needed
- ❌ Harder to debug

For MVP, URL-based token passing is acceptable and simpler to implement.

