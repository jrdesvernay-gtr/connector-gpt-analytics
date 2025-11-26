# User Flow Guide - Managing Your Analytics Connector

This guide explains how users can manage their GA4 connections and ChatGPT authorization from a user perspective.

## 🏠 Main Dashboard

**URL:** `https://ga.connector.get-to-rev.com/dashboard`

The dashboard is your central hub for managing everything. If you're not logged in, you'll be automatically redirected to Google login.

### What You'll See:

1. **Google Analytics Connection Status**
   - ✓ Connected: Shows your current property name, ID, and account email
   - ✗ Not Connected: Prompt to connect your GA4 account

2. **ChatGPT Authorization Status**
   - ✓ Authorized: Your Custom GPT can query your GA data
   - ✗ Not Authorized: Need to authorize ChatGPT

### Quick Actions Available:

- **Change Property** - Select a different GA4 property
- **Revoke Connection** - Disconnect ChatGPT (requires re-authorization)
- **Reconnect GA** - Update your GA connection
- **Authorize ChatGPT** - Connect your Custom GPT

---

## 🔄 How to Change Your GA Property

You have **two options**:

### Option 1: Change Property Directly (Recommended)

1. Go to: `https://ga.connector.get-to-rev.com/dashboard`
2. If GA is connected, click **"Change Property"**
3. Select your desired GA4 property from the list
4. Done! Future queries will use the new property

**When to use:** You want to switch to a different property while keeping ChatGPT authorized.

### Option 2: Revoke and Re-authorize

1. Go to: `https://ga.connector.get-to-rev.com/dashboard`
2. Click **"Revoke Connection"** (if ChatGPT is authorized)
3. Go back to ChatGPT and use your Custom GPT
4. You'll be asked to authorize again
5. During re-authorization, you can select a different property

**When to use:** You want a complete reset of the connection.

---

## 🔌 How to Revoke ChatGPT Connection

### Using the Dashboard:

1. Visit: `https://ga.connector.get-to-rev.com/dashboard`
2. In the ChatGPT status card, click **"Revoke Connection"**
3. Confirm the revocation
4. Done! Next time you use ChatGPT, you'll need to authorize again

### Direct URL:

1. Visit: `https://ga.connector.get-to-rev.com/revoke-chatgpt`
2. If not logged in, you'll be redirected to login first
3. Click the "Revoke ChatGPT Connection" button
4. Confirm the action

**What happens:**
- All active ChatGPT tokens are revoked
- Next time you use the Custom GPT, it will ask for re-authorization
- During re-authorization, you can select a different GA property

---

## 🔐 Login/Authentication

If you're not logged in, you'll be automatically redirected to Google login. After login, you'll be redirected back to where you were trying to go.

**Login URL:** `https://ga.connector.get-to-rev.com/auth/google/login`

---

## 📋 Complete User Journey

### First Time Setup:

1. **Login** → `https://ga.connector.get-to-rev.com/auth/google/login`
2. **Connect GA4** → Dashboard → "Connect GA4 Account"
3. **Select Property** → Choose your GA4 property
4. **Authorize ChatGPT** → Dashboard → "Authorize ChatGPT"
5. **Use in ChatGPT** → Start asking questions in your Custom GPT!

### Changing Property Later:

**Quick Method:**
1. Dashboard → "Change Property" → Select new property

**Full Reset Method:**
1. Dashboard → "Revoke Connection"
2. Use Custom GPT in ChatGPT → Re-authorize → Select new property

### Troubleshooting:

**Issue: "ChatGPT can't access my data"**
- Check dashboard → Ensure both GA and ChatGPT are connected
- If ChatGPT shows as disconnected, click "Authorize ChatGPT"

**Issue: "Wrong property being queried"**
- Dashboard → "Change Property" → Select correct property

**Issue: "Need to connect a different Google account"**
- Dashboard → "Reconnect GA" → You can authorize with a different Google account

---

## 🔗 Quick Reference Links

- **Dashboard:** `https://ga.connector.get-to-rev.com/dashboard`
- **Revoke ChatGPT:** `https://ga.connector.get-to-rev.com/revoke-chatgpt`
- **Change Property:** `https://ga.connector.get-to-rev.com/ga/select-property`
- **Privacy Policy:** `https://ga.connector.get-to-rev.com/privacy-policy`

---

## 💡 Tips

- **Bookmark the dashboard** for easy access to manage your connections
- The dashboard shows real-time status - refresh to see updates
- You can have multiple GA accounts, but one property per workspace
- Revoking ChatGPT doesn't affect your GA connection - you can re-authorize anytime

