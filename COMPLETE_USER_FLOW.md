# Complete User Flow: First-Time Custom GPT Usage

This document describes the **entire flow** from when a user first prompts the Custom GPT, including all UI interactions and OAuth steps.

---

## 🎯 CORRECTED USER FLOW (Account Creation as Part of Flow)

### Step 1: User Prompts Custom GPT (First Time)
- **UI Location:** ChatGPT interface
- **User Action:** Types question like *"What were my sessions yesterday?"*
- **What Happens:**
  - ChatGPT sees it needs to call `/ga/run-report`
  - No access token exists yet
  - ChatGPT initiates OAuth authorization flow

### Step 2: ChatGPT Redirects to Authorization Endpoint
- **URL:** `https://ga.connector.get-to-rev.com/authorize-gpt?redirect_uri=https://chat.openai.com/oauth/callback&state=random_state`
- **What Happens:**
  - Our server receives the authorization request
  - Checks if user has active session → **No session (first time)**
  - **Action:** Redirect user to login/account creation

### Step 3: Redirect to Login/Account Creation
- **Redirect To:** `https://ga.connector.get-to-rev.com/auth/google/login?next=/authorize-gpt?...` 
- **UI Location:** Our web app (Google OAuth consent screen)
- **What Happens:**
  - User sees Google "Sign in with Google" screen
  - User selects Google account
  - Google redirects back to our callback

### Step 4: Account Creation/Authentication
- **URL:** `https://ga.connector.get-to-rev.com/auth/google/callback?code=...`
- **What Happens:**
  - Our server exchanges code for user info
  - **Creates user account** (if first time) OR logs in existing user
  - Creates default workspace (if new user)
  - Generates JWT token
  - Stores session/cookie
- **Redirect To:** Continue to next step (GA connection)

### Step 5: Redirect to GA Connection (If Not Connected)
- **URL:** `https://ga.connector.get-to-rev.com/ga/connect?token=JWT_TOKEN`
- **UI Location:** Our web app (Google Analytics OAuth consent)
- **What Happens:**
  - User is authenticated (has JWT token)
  - Check if workspace has GA connection → **No connection (first time)**
  - Redirects to Google Analytics OAuth consent screen
  - User authorizes our app to read GA4 data

### Step 6: GA OAuth Callback
- **URL:** `https://ga.connector.get-to-rev.com/ga/callback?code=...`
- **What Happens:**
  - Server exchanges code for GA credentials
  - Stores encrypted refresh token
  - Fetches user's GA4 properties
  - Redirects to property selection

### Step 7: Select GA Property
- **URL:** `https://ga.connector.get-to-rev.com/ga/select-property?token=JWT_TOKEN`
- **UI Location:** Our web app (property selection page)
- **What Happens:**
  - Shows list of available GA4 properties
  - User selects property
  - Creates GA connection record
  - **Redirects back to:** `/authorize-gpt` page (original request)

### Step 8: Authorization Page (Now Authenticated)
- **URL:** `https://ga.connector.get-to-rev.com/authorize-gpt?workspace_id=...&redirect_uri=...&state=...`
- **UI Location:** Our web app (authorization confirmation page)
- **What Happens:**
  - User is now authenticated (has session/JWT)
  - Server verifies workspace ownership
  - Shows authorization page:
    - *"Authorize ChatGPT to access your GA4 data?"*
    - Shows workspace name
    - Shows which GA property will be accessed
  - **Button:** "Authorize"

### Step 9: User Clicks "Authorize"
- **User Action:** Clicks "Authorize" button
- **What Happens:**
  - Server generates authorization code
  - Stores code temporarily (or in JWT)
  - Redirects back to ChatGPT callback URL:
    ```
    https://chat.openai.com/oauth/callback?code=AUTHORIZATION_CODE&state=STATE
    ```

### Step 10: ChatGPT Exchanges Code for Token
- **URL:** `https://ga.connector.get-to-rev.com/oauth/token`
- **Method:** POST
- **Request:**
  ```json
  {
    "grant_type": "authorization_code",
    "code": "AUTHORIZATION_CODE",
    "redirect_uri": "https://chat.openai.com/oauth/callback"
  }
  ```
- **Response:**
  ```json
  {
    "access_token": "jwt_token_for_gpt",
    "refresh_token": "opaque_refresh_token",
    "expires_in": 3600,
    "token_type": "bearer",
    "scope": "read"
  }
  ```

### Step 11: ChatGPT Makes API Call
- **URL:** `https://ga.connector.get-to-rev.com/ga/run-report`
- **Method:** POST
- **Headers:** `Authorization: Bearer {access_token}`
- **Body:**
  ```json
  {
    "metrics": ["sessions"],
    "dimensions": ["date"],
    "date_ranges": [{
      "startDate": "2024-11-23",
      "endDate": "2024-11-23"
    }]
  }
  ```
- **Response:** GA4 data

### Step 12: ChatGPT Responds to User
- **UI Location:** ChatGPT interface
- **Response:** *"You had 732 sessions yesterday (November 23, 2024)."*

---

## 🔄 SUBSEQUENT USAGE FLOW (User Already Set Up)

### First Question of Session:
1. User prompts GPT
2. ChatGPT checks token → **May be expired**
3. If expired, uses refresh token to get new access token
4. Makes API call
5. Returns response

### If Refresh Token Expired:
1. User prompts GPT
2. ChatGPT's refresh token is expired
3. ChatGPT redirects to `/authorize-gpt`
4. User is already logged in (has session)
5. User clicks "Authorize" → New tokens issued
6. Flow continues

---

## 🔧 IMPLEMENTATION REQUIREMENTS

### 1. Modify `/authorize-gpt` Endpoint

**Current:** Requires authentication upfront  
**Should:** Handle unauthenticated users gracefully

```python
@router.get("/authorize-gpt")
async def authorize_gpt(
    redirect_uri: str = Query(...),
    state: Optional[str] = Query(None),
    workspace_id: Optional[str] = Query(None),  # Optional, can lookup
    request: Request,
    db: Session = Depends(get_db),
):
    # Check for session/authentication
    # If not authenticated → redirect to login with return URL
    # If authenticated → show authorization page
```

### 2. Add Session Management

- Store user session in secure HTTP-only cookies
- Link session to user account
- Persist across redirects

### 3. Add Authorization Confirmation Page

- Beautiful UI showing what will be authorized
- Workspace and GA property info
- "Authorize" button
- Clear messaging

### 4. Flow State Management

- Store original OAuth parameters (`redirect_uri`, `state`) in session
- After login/GA connection, redirect back to authorization
- Maintain flow context through redirects

### 5. Auto-Discover Workspace

- If user is logged in but no `workspace_id` provided
- Use user's default workspace
- Or show workspace selector if multiple

---

## 📋 FLOW DIAGRAM

```
User Prompts GPT
    ↓
ChatGPT → /authorize-gpt
    ↓
Not Authenticated? → /auth/google/login
    ↓
Google OAuth → Account Created/Logged In
    ↓
No GA Connection? → /ga/connect
    ↓
Google Analytics OAuth → GA Connected
    ↓
Select Property → Property Selected
    ↓
Back to /authorize-gpt (authenticated)
    ↓
Authorization Page → User Clicks "Authorize"
    ↓
Redirect to ChatGPT with code
    ↓
ChatGPT → /oauth/token (exchange code)
    ↓
ChatGPT → /ga/run-report (with token)
    ↓
Returns GA Data
    ↓
ChatGPT Responds to User
```

---

## ✅ CHECKLIST FOR IMPLEMENTATION

- [ ] Modify `/authorize-gpt` to handle unauthenticated users
- [ ] Add session management (cookies or database)
- [ ] Store flow state (`redirect_uri`, `state`) in session
- [ ] Create authorization confirmation page UI
- [ ] Auto-redirect after login to continue OAuth flow
- [ ] Auto-redirect after GA connection to authorization
- [ ] Handle workspace discovery (default or selector)
- [ ] Test complete flow end-to-end
