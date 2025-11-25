# Complete User Flow Verification

## ✅ Correct Flow (As You Described)

### Step 1: User Prompts Custom GPT (First Time)
- **Location:** ChatGPT interface
- **Action:** User types: *"What were my sessions yesterday?"*
- **What Happens:** ChatGPT initiates OAuth authorization

### Step 2: ChatGPT Redirects to Authorization
- **URL:** `https://ga.connector.get-to-rev.com/authorize-gpt?redirect_uri=https://chat.openai.com/oauth/callback&state=random`
- **Status:** User NOT authenticated
- **Action:** Redirect to login

### Step 3: Redirect to Google Login
- **URL:** `https://ga.connector.get-to-rev.com/auth/google/login?next=/authorize-gpt?...`
- **UI:** Google "Sign in with Google" screen
- **Action:** User signs in with Google account

### Step 4: Account Creation/Authentication
- **URL:** `https://ga.connector.get-to-rev.com/auth/google/callback?code=...`
- **What Happens:**
  - Account created (if first time) OR user logged in
  - Default workspace created (if new user)
  - JWT token generated
- **Redirect To:** Continue flow (see Step 5)

### Step 5: Redirect to GA Connection (If Not Connected)
- **URL:** `https://ga.connector.get-to-rev.com/ga/connect?token=JWT_TOKEN`
- **UI:** Google Analytics OAuth consent screen
- **What Happens:**
  - User authorizes app to read GA4 data
  - User's GA4 properties are fetched

### Step 6: GA OAuth Callback
- **URL:** `https://ga.connector.get-to-rev.com/ga/callback?code=...`
- **What Happens:**
  - GA credentials stored (encrypted)
  - User redirected to property selection

### Step 7: Select GA Property
- **URL:** `https://ga.connector.get-to-rev.com/ga/select-property?token=JWT_TOKEN`
- **UI:** Property selection page
- **Action:** User selects GA4 property
- **Redirect To:** Back to `/authorize-gpt` (Step 8)

### Step 8: Authorization Confirmation Page
- **URL:** `https://ga.connector.get-to-rev.com/authorize-gpt?redirect_uri=...&token=JWT_TOKEN`
- **UI:** Authorization confirmation page
- **Content:**
  - "Authorize ChatGPT to access your GA4 data?"
  - Shows workspace and GA property info
  - "Authorize" button

### Step 9: User Clicks "Authorize"
- **Action:** User clicks "Authorize" button
- **What Happens:**
  - Authorization code generated
  - Redirects to ChatGPT callback with code

### Step 10: ChatGPT Exchanges Code
- **URL:** `https://ga.connector.get-to-rev.com/oauth/token`
- **Request:** `grant_type=authorization_code&code=...&redirect_uri=...`
- **Response:** `{access_token, refresh_token, expires_in, ...}`

### Step 11: ChatGPT Makes API Call
- **URL:** `https://ga.connector.get-to-rev.com/ga/run-report`
- **Headers:** `Authorization: Bearer {access_token}`
- **Body:** GA query parameters
- **Response:** GA4 data

### Step 12: ChatGPT Responds
- **UI:** ChatGPT interface
- **Response:** Natural language answer with GA data

---

## 🔧 Implementation Status

### ✅ Already Implemented:
- `/authorize-gpt` endpoint (needs modification)
- OAuth token exchange (`/oauth/token`)
- GA connection flow
- GA query endpoint
- Authorization confirmation page HTML

### ❌ Needs Fixing:

#### 1. `/authorize-gpt` Authentication
**Current:** Requires user authentication upfront  
**Should:** Handle unauthenticated users → redirect to login

#### 2. Token Passing Through Redirects
**Issue:** Need to pass JWT token through redirect chain  
**Solution Options:**
- Use session cookies (best)
- Pass token in URL query params (simpler, less secure)
- Store in temporary session storage

#### 3. Flow State Management
**Issue:** Need to preserve `redirect_uri` and `state` through redirects  
**Solution:** Store in session or pass as URL parameters

#### 4. Google Login Callback Redirect
**Current:** Always redirects to `/auth/google/success`  
**Should:** Check for `next` parameter and redirect accordingly

#### 5. GA Connection Completion Redirect
**Current:** Redirects to success page  
**Should:** Check if came from `/authorize-gpt` flow and redirect back

---

## 🔨 Required Code Changes

### Change 1: Update `/authorize-gpt` to Handle Unauthenticated Users
```python
# Current: Requires get_current_user (fails if not authenticated)
# Should: Check authentication, redirect to login if needed
```

### Change 2: Update Google Login to Accept `next` Parameter
```python
# Accept 'next' URL parameter
# Store it temporarily
# Redirect there after successful login
```

### Change 3: Update Google Login Callback
```python
# Check for stored 'next' URL
# Redirect to that URL with token instead of success page
```

### Change 4: Update GA Connection Flow
```python
# Accept 'next' parameter
# After property selection, redirect to 'next' URL
```

---

## 📝 Current Issue

The `/authorize-gpt` endpoint currently requires `get_current_user` dependency which will fail if user isn't authenticated. This breaks the flow because ChatGPT redirects there before the user has logged in.

**Fix Required:** Make authentication optional, redirect to login if not authenticated, then continue flow.


