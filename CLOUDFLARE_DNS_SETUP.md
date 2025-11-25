# Cloudflare DNS Setup for ga.connector.get-to-rev.com

## Step-by-Step Instructions

### 1. Log into Cloudflare

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Select your domain: `get-to-rev.com`

### 2. Add CNAME Record

1. Click on **DNS** in the left sidebar
2. Click **"Add record"** button
3. Fill in the fields:
   - **Type**: Select `CNAME`
   - **Name**: Enter `ga.connector` (this creates `ga.connector.get-to-rev.com`)
   - **Target**: Enter `ga-connector-api-production.up.railway.app`
   - **Proxy status**: Toggle to **DNS only** (gray cloud) or **Proxied** (orange cloud)
     - **Recommended for Railway**: Use **DNS only** (gray cloud) initially
     - Railway handles HTTPS, so proxying through Cloudflare can cause issues
   - **TTL**: Select `Auto` or `3600`
4. Click **"Save"**

### 3. Verify the Record

After saving, you should see:
```
Type    Name         Target                                          Proxy
CNAME   ga.connector ga-connector-api-production.up.railway.app     DNS only
```

### 4. Wait for DNS Propagation

- DNS changes in Cloudflare usually propagate within **5-15 minutes**
- You can check propagation status at: https://www.whatsmydns.net/#CNAME/ga.connector.get-to-rev.com

### 5. Important: Proxy Settings

⚠️ **For Railway deployments, it's recommended to use "DNS only" (gray cloud)**:

- **Gray cloud (DNS only)**: Direct connection to Railway, Railway handles SSL
- **Orange cloud (Proxied)**: Traffic goes through Cloudflare, which can interfere with Railway's SSL certificates

If you use the orange cloud (proxied):
- You may need to configure Cloudflare SSL settings
- Railway's automatic SSL may not work correctly
- More complex setup required

**Recommendation**: Start with gray cloud (DNS only), then switch to proxied later if needed.

### 6. Verify in Railway

1. After DNS propagates, go back to Railway
2. Check your service → Settings → Networking → Custom Domain
3. Railway should show the domain as "Active" once DNS resolves
4. Railway will automatically provision an SSL certificate

### 7. Test the Domain

Once Railway shows the domain as active:
- Test: `https://ga.connector.get-to-rev.com/health`
- Should return: `{"status":"healthy"}`

## Troubleshooting

### Domain not resolving
- Wait a few more minutes for DNS propagation
- Verify the CNAME record is correct in Cloudflare
- Check that the record shows "Active" in Cloudflare

### SSL/HTTPS errors
- Make sure you're using "DNS only" (gray cloud) in Cloudflare
- Wait for Railway to provision the SSL certificate (can take a few minutes)
- Check Railway's Custom Domain status

### Still having issues?
- Double-check the CNAME target matches Railway's domain exactly
- Verify the record type is CNAME (not A or AAAA)
- Clear your browser cache and try again

