# Complete User Flow - First-Time Custom GPT Usage (VERIFIED)

This document describes the **complete flow** from when a user first prompts the Custom GPT, verified by reviewing all redirects and token passing.

---

## 🎯 Complete Flow Overview

### Phase 1: User Prompts Custom GPT (First Time)
**Location:** ChatGPT interface  
**User Action:** Types question like *"What were my sessions yesterday?"*

**What Happens:**
1. ChatGPT sees it needs to call `/ga/run-report`
2. No access token exists yet
3. ChatGPT initiates OAuth authorization flow
4. ChatGPT redirects user to authorization URL

---

## 📋 Step-by-Step Flow (Detailed)

### **Step 1: ChatGPT Initiates OAuth Authorization**

**URL:** `https://ga.connector.get-to-rev.com/authorize-gpt?redirect_uri=https://chat.openai.com/oauth/callback&state=random_state_string`

**What Happens:**
- `/authorize-gpt` endpoint receives request
- Checks if user is authenticated (looks for `token` query parameter)
- **User not authenticated** → Proceeds to Step 2

**Code Location:** `app/api/gpt_oauth.py:45-119`

---

### **Step 2: Redirect to Google Login**

**Redirect To:** `https://ga.connector.get-to-rev.com/auth/google/login?next=ENCODED_AUTHORIZE_GPT_URL`

**URL Details:**
- `next` parameter contains: `/authorize-gpt?redirect_uri=...&state=...&workspace_id=...`
- `next` URL is URL-encoded using `quote()`

**What Happens:**
- `/auth/google/login` receives request
- Extracts `next` parameter (URL-encoded)
- Encodes `next` in OAuth state: `base64(json({csrf: "...", next: "..."}))`
- Redirects to Google OAuth authorization URL

**Code Location:** `app/api/google_auth.py:21-51`

---

### **Step 3: Google OAuth Consent Screen**

**URL:** Google OAuth authorization page  
**UI:** Google "Sign in with Google" consent screen

**User Action:** 
- Selects Google account
- Clicks "Continue" or "Allow"

**What Happens:**
- User authorizes app to access their Google profile
- Google redirects back to callback with authorization code

**Redirect To:** `/auth/google/callback?code=GOOGLE_CODE&state=BASE64_STATE`

---

### **Step 4: Google OAuth Callback - Account Creation/Login**

**URL:** `https://ga.connector.get-to-rev.com/auth/google/callback?code=4/0Ab32j...&state=eyJjc3Jm...`

**What Happens:**
1. `/auth/google/callback` receives callback
2. Exchanges authorization code for user info
3. **Creates user account** (if first time) OR logs in existing user
4. Creates default workspace (if new user)
5. Generates JWT token: `create_access_token({sub: user_id})`
6. Extracts `next` URL from state: `base64.decode(state).json()["next"]`
7. URL-decodes `next` URL if needed
8. Appends JWT token to `next` URL: `?token=JWT_TOKEN`
9. Redirects to: `/authorize-gpt?redirect_uri=...&state=...&token=JWT_TOKEN`

**Token Passed:** JWT token in URL query parameter (`?token=...`)

**Code Location:** `app/api/google_auth.py:54-169`

---

### **Step 5: Return to Authorization Endpoint (Now Authenticated)**

**URL:** `https://ga.connector.get-to-rev.com/authorize-gpt?redirect_uri=...&state=...&token=JWT_TOKEN`

**What Happens:**
1. `/authorize-gpt` receives request with token
2. Validates JWT token
3. Extracts user from token
4. Gets or determines workspace
5. Checks if workspace has GA connection
6. **No GA connection found** → Proceeds to Step 6

**Code Location:** `app/api/gpt_oauth.py:45-181`

---

### **Step 6: Redirect to GA Connection**

**Redirect To:** `https://ga.connector.get-to-rev.com/ga/connect?token=JWT_TOKEN&next=ENCODED_AUTHORIZE_GPT_URL`

**URL Details:**
- `token`: JWT token for authentication
- `next`: URL-encoded `/authorize-gpt?redirect_uri=...&state=...&workspace_id=...`

**What Happens:**
1. `/ga/connect` receives request
2. Validates JWT token (via `get_current_user` dependency)
3. Gets workspace
4. Passes `next` URL to GA OAuth service
5. Encodes `next` URL in OAuth state: `base64(json({workspace_id: "...", csrf: "...", next: "..."}))`
6. Redirects to Google Analytics OAuth authorization URL

**Code Location:** `app/api/ga_oauth.py:21-75`  
**State Management:** `app/services/ga_oauth_service.py:19-72`

---

### **Step 7: Google Analytics OAuth Consent Screen**

**URL:** Google OAuth authorization page  
**UI:** Google Analytics OAuth consent screen

**User Action:**
- Selects Google account (can be different from login account)
- Grants permission to read GA4 data
- Clicks "Continue" or "Allow"

**What Happens:**
- User authorizes app to access their Google Analytics data
- Google redirects back to callback with authorization code

**Redirect To:** `/ga/callback?code=GA_CODE&state=BASE64_STATE_WITH_NEXT`

---

### **Step 8: GA OAuth Callback - Connection Setup**

**URL:** `https://ga.connector.get-to-rev.com/ga/callback?code=4/0Ab32j...&state=eyJ3b3Jrc3BhY2VfaWQ...`

**What Happens:**
1. `/ga/callback` receives callback
2. Parses state: `parse_state(state)` → `(workspace_id, csrf_token, next_url)`
3. Exchanges authorization code for GA credentials
4. Stores encrypted refresh token in database
5. Fetches user's GA4 properties
6. Gets Google account email (can differ from login email)

**Decision Point:**
- **If multiple properties** → Proceeds to Step 9 (Property Selection)
- **If single property** → Proceeds to Step 11 (Auto-Select)

**Code Location:** `app/api/ga_oauth.py:77-289`  
**State Parsing:** `app/services/ga_oauth_service.py:263-299`

---

### **Step 9A: Multiple Properties - Redirect to Property Selection**

**Redirect To:** `https://ga.connector.get-to-rev.com/ga/select-property?workspace_id=...&token=JWT_TOKEN&next=ENCODED_AUTHORIZE_GPT_URL`

**What Happens:**
1. Creates temporary GA connection with first property (stores credentials)
2. Generates new JWT token
3. Redirects to property selection page with:
   - `workspace_id`: Workspace ID
   - `token`: JWT token for authentication
   - `next`: URL-encoded `/authorize-gpt?redirect_uri=...&state=...&workspace_id=...`

**Code Location:** `app/api/ga_oauth.py:200-236`

---

### **Step 10: Property Selection Page**

**URL:** `https://ga.connector.get-to-rev.com/ga/select-property?workspace_id=...&token=JWT_TOKEN&next=ENCODED_URL`

**UI:** Property selection page showing:
- List of available GA4 properties
- "Select" button for each property
- "Continue with current selection" link

**User Action:**
- Clicks "Select" on a property OR
- Clicks "Continue with current selection"

**What Happens:**
- Property selection links include `token` and `next` parameters
- "Continue" link includes `next` parameter

**Code Location:** `app/api/ga_oauth.py:492-635`

---

### **Step 11: Property Selection Complete**

**URL:** `https://ga.connector.get-to-rev.com/ga/properties/{property_id}/select?token=JWT_TOKEN&next=ENCODED_AUTHORIZE_GPT_URL`

**What Happens (GET request):**
1. `/ga/properties/{id}/select` receives request
2. Validates JWT token
3. Updates GA connection with selected property
4. If `next` URL provided:
   - URL-decodes `next` URL
   - Generates fresh JWT token
   - Appends token to `next` URL: `?token=JWT_TOKEN`
   - Redirects to: `/authorize-gpt?redirect_uri=...&state=...&workspace_id=...&token=JWT_TOKEN`

**Redirect To:** `/authorize-gpt?redirect_uri=...&state=...&workspace_id=...&token=JWT_TOKEN`

**Code Location:** `app/api/ga_oauth.py:338-460`

---

### **Step 9B: Single Property - Auto-Select and Redirect**

**Redirect To:** `https://ga.connector.get-to-rev.com/authorize-gpt?redirect_uri=...&state=...&workspace_id=...&token=JWT_TOKEN`

**What Happens:**
1. Creates GA connection with single property
2. If `next_url` from state:
   - URL-decodes `next_url`
   - Generates JWT token
   - Appends token to `next_url`
   - Redirects to `/authorize-gpt` with token

**Code Location:** `app/api/ga_oauth.py:237-289`

---

### **Step 12: Return to Authorization Endpoint (GA Connected)**

**URL:** `https://ga.connector.get-to-rev.com/authorize-gpt?redirect_uri=...&state=...&workspace_id=...&token=JWT_TOKEN`

**What Happens:**
1. `/authorize-gpt` receives request with token
2. Validates JWT token
3. Gets user from token
4. Gets workspace
5. **GA connection exists** ✅
6. Checks for `auto_authorize` parameter
7. **Not present** → Shows authorization confirmation page

**Code Location:** `app/api/gpt_oauth.py:45-292`

---

### **Step 13: Authorization Confirmation Page**

**URL:** Same as Step 12  
**UI:** Beautiful authorization page showing:
- "Authorize ChatGPT" heading
- Workspace name and GA property name
- List of permissions ChatGPT will have
- "Authorize ChatGPT" button

**User Action:** Clicks "Authorize ChatGPT" button

**What Happens:**
- Button links to: `/authorize-gpt?...&auto_authorize=true`
- All query parameters (including `token`, `redirect_uri`, `state`) are preserved

**Code Location:** `app/api/gpt_oauth.py:187-292`

---

### **Step 14: User Clicks "Authorize" - Generate Authorization Code**

**URL:** `https://ga.connector.get-to-rev.com/authorize-gpt?redirect_uri=...&state=...&workspace_id=...&token=JWT_TOKEN&auto_authorize=true`

**What Happens:**
1. `/authorize-gpt` receives request with `auto_authorize=true`
2. Validates JWT token
3. Gets workspace
4. Verifies GA connection
5. Generates authorization code: `GPTOAuthService.create_authorization_code(workspace_id)`
   - Code is a JWT with: `{workspace_id: "...", type: "authorization_code", exp: ...}`
6. Builds redirect URL with code:
   - Parses `redirect_uri` from query params
   - Adds `code` parameter: `?code=AUTHORIZATION_CODE`
   - Preserves `state` parameter
7. Redirects to ChatGPT callback: `https://chat.openai.com/oauth/callback?code=AUTHORIZATION_CODE&state=...`

**Token Passed:** Authorization code in URL query parameter (`?code=...`)

**Code Location:** `app/api/gpt_oauth.py:294-329`  
**Code Generation:** `app/services/gpt_oauth_service.py:48-68`

---

### **Step 15: ChatGPT Receives Authorization Code**

**URL:** `https://chat.openai.com/oauth/callback?code=AUTHORIZATION_CODE&state=...`

**What Happens:**
- ChatGPT receives authorization code from redirect
- Stores code temporarily
- Proceeds to Step 16 (Token Exchange)

---

### **Step 16: ChatGPT Exchanges Code for Tokens**

**Request:**
```
POST https://ga.connector.get-to-rev.com/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code
&code=AUTHORIZATION_CODE
&redirect_uri=https://chat.openai.com/oauth/callback
```

**What Happens:**
1. `/oauth/token` receives token exchange request
2. Validates authorization code: `verify_authorization_code(code)`
3. Extracts `workspace_id` from code
4. Verifies workspace exists
5. Verifies workspace has GA connection
6. Generates GPT access token (JWT with `type: "gpt_access"`)
7. Generates refresh token (opaque string)
8. Stores tokens in database (access token hash + refresh token)
9. Returns token response:

```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "ZA_8JUa0afygfXlx...",
  "token_type": "bearer",
  "expires_in": 3600,
  "scope": "read"
}
```

**Token Passed:** Access token and refresh token in JSON response

**Code Location:** `app/api/gpt_oauth.py:332-388`  
**Token Exchange:** `app/services/gpt_oauth_service.py:80-176`

---

### **Step 17: ChatGPT Makes API Call**

**Request:**
```
POST https://ga.connector.get-to-rev.com/ga/run-report
Authorization: Bearer eyJhbGci...
Content-Type: application/json

{
  "metrics": ["sessions"],
  "dimensions": ["date"],
  "date_ranges": [{
    "startDate": "2024-11-23",
    "endDate": "2024-11-23"
  }]
}
```

**What Happens:**
1. `/ga/run-report` receives request
2. Validates GPT access token (via `get_valid_gpt_token` dependency)
   - Extracts token from `Authorization: Bearer TOKEN` header
   - Verifies JWT signature and expiration
   - Checks token type is `"gpt_access"`
   - Finds active GPT token in database
3. Gets workspace from token
4. Gets GA connection for workspace
5. Calls GA4 API to fetch data
6. Returns GA4 data:

```json
{
  "rows": [
    {
      "dimensionValues": [{"value": "20241123"}],
      "metricValues": [{"value": "732"}]
    }
  ],
  "totals": [{"metricValues": [{"value": "732"}]}],
  "row_count": 1
}
```

**Token Passed:** Access token in HTTP Authorization header (`Authorization: Bearer ...`)

**Code Location:** `app/api/ga_report.py:22-143`  
**Token Validation:** `app/api/dependencies.py:140-188`

---

### **Step 18: ChatGPT Responds to User**

**Location:** ChatGPT interface  
**Response:** 
> "You had **732 sessions** yesterday (November 23, 2024)."

**What Happens:**
- ChatGPT formats GA4 data into natural language
- Displays response to user
- User sees their analytics data

---

## 🔄 Subsequent Usage Flow

### **First Query After Authorization**
1. User asks another question
2. ChatGPT uses existing access token
3. If token expired, uses refresh token to get new access token
4. Makes API call with new token

### **Token Refresh Flow**
If access token expires:

**Request:**
```
POST https://ga.connector.get-to-rev.com/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
&refresh_token=ZA_8JUa0afygfXlx...
```

**Response:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 3600,
  "scope": "read"
}
```

**Code Location:** `app/api/gpt_oauth.py:390-410`  
**Token Refresh:** `app/services/gpt_oauth_service.py:178-229`

---

## 📊 Token Flow Summary

| Step | Token Type | How Passed | Location |
|------|-----------|------------|----------|
| 1-2 | None | - | User not authenticated |
| 3 | None | OAuth state | Google OAuth flow |
| 4 | JWT (User Auth) | URL query (`?token=...`) | Google callback → `/authorize-gpt` |
| 6 | JWT (User Auth) | URL query (`?token=...`) | `/authorize-gpt` → `/ga/connect` |
| 7 | None | OAuth state | GA OAuth flow |
| 9-11 | JWT (User Auth) | URL query (`?token=...`) | GA callback → Property selection → `/authorize-gpt` |
| 12-14 | JWT (User Auth) | URL query (`?token=...`) | `/authorize-gpt` (authorization page) |
| 14 | Authorization Code | URL query (`?code=...`) | `/authorize-gpt` → ChatGPT callback |
| 16 | Access Token | JSON response | `/oauth/token` → ChatGPT |
| 16 | Refresh Token | JSON response | `/oauth/token` → ChatGPT |
| 17 | Access Token | HTTP header (`Authorization: Bearer ...`) | ChatGPT → `/ga/run-report` |

---

## ✅ Redirect Verification Checklist

### **Google Login Flow**
- ✅ `/authorize-gpt` → `/auth/google/login?next=ENCODED_URL` (when not authenticated)
- ✅ `/auth/google/login` encodes `next` in OAuth state
- ✅ `/auth/google/callback` extracts `next` from state
- ✅ `/auth/google/callback` → `/authorize-gpt?...&token=JWT` (with token)

### **GA Connection Flow**
- ✅ `/authorize-gpt` → `/ga/connect?token=JWT&next=ENCODED_URL` (when no GA connection)
- ✅ `/ga/connect` encodes `next` in OAuth state
- ✅ `/ga/callback` extracts `next` from state
- ✅ `/ga/callback` → Property selection OR `/authorize-gpt?...&token=JWT` (single property)

### **Property Selection Flow**
- ✅ `/ga/callback` → `/ga/select-property?workspace_id=...&token=JWT&next=ENCODED_URL` (multiple properties)
- ✅ Property selection page includes `next` in all links
- ✅ `/ga/properties/{id}/select` → `/authorize-gpt?...&token=JWT` (with `next` URL)

### **GPT Authorization Flow**
- ✅ `/authorize-gpt` shows authorization page (when authenticated + GA connected)
- ✅ Authorization page button → `/authorize-gpt?...&auto_authorize=true`
- ✅ `/authorize-gpt` with `auto_authorize=true` → ChatGPT callback with code

### **Token Exchange Flow**
- ✅ ChatGPT → `/oauth/token` (POST with code)
- ✅ `/oauth/token` → JSON response with access_token and refresh_token

### **API Call Flow**
- ✅ ChatGPT → `/ga/run-report` (POST with Bearer token)
- ✅ `/ga/run-report` validates token and returns GA data

---

## 🔍 Code Verification Summary

### **All Redirects Verified:**
1. ✅ User login redirect chain
2. ✅ GA connection redirect chain
3. ✅ Property selection redirect chain
4. ✅ Authorization code redirect
5. ✅ Token passing at each step

### **All Token Passing Verified:**
1. ✅ JWT tokens passed in URL query parameters (web flow)
2. ✅ Authorization codes passed in URL query parameters (OAuth callback)
3. ✅ Access tokens passed in HTTP Authorization header (API calls)
4. ✅ Refresh tokens passed in POST body (token refresh)
5. ✅ State management for `next` URLs (base64 JSON encoding)

### **All State Management Verified:**
1. ✅ Google login state includes `next` URL
2. ✅ GA OAuth state includes `next` URL
3. ✅ State parsing handles both base64 JSON and simple formats
4. ✅ URL encoding/decoding handled correctly

---

## 🎯 Complete Flow Diagram

```
User Prompts GPT (First Time)
    ↓
ChatGPT → /authorize-gpt (no token)
    ↓
Not Authenticated → /auth/google/login?next=ENCODED_URL
    ↓
Google OAuth → /auth/google/callback?code=...
    ↓
Account Created/Logged In → Generate JWT
    ↓
Extract next from state → /authorize-gpt?...&token=JWT
    ↓
No GA Connection → /ga/connect?token=JWT&next=ENCODED_URL
    ↓
GA OAuth → /ga/callback?code=...&state=...
    ↓
Parse state → Extract next_url
    ↓
Multiple Properties? → /ga/select-property?workspace_id=...&token=JWT&next=ENCODED_URL
    OR
Single Property → /authorize-gpt?...&token=JWT (direct redirect)
    ↓
User Selects Property → /ga/properties/{id}/select?token=JWT&next=ENCODED_URL
    ↓
Property Selected → /authorize-gpt?...&token=JWT
    ↓
GA Connected ✅ → Show Authorization Page
    ↓
User Clicks "Authorize" → /authorize-gpt?...&auto_authorize=true
    ↓
Generate Authorization Code → ChatGPT callback?code=CODE&state=...
    ↓
ChatGPT Receives Code → POST /oauth/token
    ↓
Token Exchange → {access_token, refresh_token}
    ↓
ChatGPT Stores Tokens → Makes API Call
    ↓
POST /ga/run-report (Bearer token) → GA Data
    ↓
ChatGPT Formats Response → User Sees Answer
```

---

## ✨ Summary

**All redirects are correctly set up:**
- ✅ Token passing through entire chain
- ✅ State management for `next` URLs
- ✅ URL encoding/decoding
- ✅ OAuth flows properly connected
- ✅ Property selection preserves flow
- ✅ Authorization page works correctly

**The complete flow is ready for testing!** 🚀


