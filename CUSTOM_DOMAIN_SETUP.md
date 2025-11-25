# Custom Domain Setup Guide

## Step 9.2: Add Custom Domain in Railway

1. **In Railway Dashboard**:
   - Go to your **Web Service** (not the database)
   - Click on **Settings** tab
   - Scroll down to **Networking** section
   - Click **"Custom Domain"** or **"Add Domain"**

2. **Enter Your Domain**:
   - Domain: `ga.connector.get-to-rev.com`
   - Click **"Add"** or **"Generate"**

3. **Railway will provide DNS records**:
   - Railway will show you DNS configuration instructions
   - Usually a **CNAME** record pointing to Railway's domain
   - Example: `connector` → `ga-connector-api-production.up.railway.app`

## Step 9.3: Configure DNS

In your domain provider (where `get-to-rev.com` is managed):

### Option A: CNAME Record (Recommended)

1. Go to your DNS provider (e.g., Cloudflare, GoDaddy, Namecheap, etc.)
2. Add a new DNS record:
   ```
   Type: CNAME
   Name: ga.connector
   Value: ga-connector-api-production.up.railway.app
   TTL: 3600 (or Auto)
   ```
   
   **Note**: Some DNS providers require you to enter the full subdomain path. If your DNS provider doesn't support nested subdomains, you may need to create a subdomain record for `connector` first, then add `ga` as a subdomain of that. Alternatively, use a simpler domain like `ga-connector.get-to-rev.com`.
3. Save the record

### Option B: A Record (If CNAME not supported)

If your DNS provider doesn't support CNAME for root domain, Railway will provide IP addresses. Use those instead.

## Step 9.4: Verify HTTPS (Automatic)

✅ **Railway automatically provisions SSL certificates** via Let's Encrypt once DNS is configured correctly.

**Wait for DNS propagation** (5-60 minutes, sometimes up to 48 hours):
- Check DNS propagation: https://www.whatsmydns.net/#CNAME/ga.connector.get-to-rev.com
- Railway will show domain status in the Settings → Custom Domain section

## Step 10: Update Environment Variables

After the custom domain is active and HTTPS is working:

1. **Update in Railway** (Service → Variables):
   - `APP_BASE_URL`: Change from Railway domain to `https://ga.connector.get-to-rev.com`
   - `GOOGLE_REDIRECT_URI`: Change to `https://ga.connector.get-to-rev.com/auth/google/callback`

2. **Update Google OAuth Settings**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to "APIs & Services" → "Credentials"
   - Click on your OAuth 2.0 Client ID
   - Under **"Authorized redirect URIs"**, add:
     ```
     https://ga.connector.get-to-rev.com/auth/google/callback
     https://ga.connector.get-to-rev.com/ga/callback
     ```
   - Under **"Authorized JavaScript origins"**, add:
     ```
     https://ga.connector.get-to-rev.com
     ```
   - Click **"Save"**

## Verification Checklist

- [ ] Custom domain added in Railway
- [ ] DNS CNAME record configured
- [ ] DNS propagated (check with whatsmydns.net)
- [ ] HTTPS certificate active (green lock in browser)
- [ ] `https://ga.connector.get-to-rev.com/health` works
- [ ] Environment variables updated to use custom domain
- [ ] Google OAuth redirect URIs updated
- [ ] Test user login: `https://ga.connector.get-to-rev.com/auth/google/login`

## Troubleshooting

### Domain not resolving
- Wait longer for DNS propagation (can take up to 48 hours)
- Verify CNAME record is correct
- Check DNS provider's status

### HTTPS not working
- Railway provisions SSL automatically - wait a few minutes after DNS resolves
- Check Railway's Custom Domain status page
- Verify DNS is pointing correctly

### OAuth redirect errors
- Make sure Google OAuth redirect URIs are updated
- Verify `APP_BASE_URL` and `GOOGLE_REDIRECT_URI` match in Railway
- Clear browser cache and try again

