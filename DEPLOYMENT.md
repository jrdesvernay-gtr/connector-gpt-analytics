# Deployment Guide

This guide walks you through deploying the GA Analytics Connector to production.

## Step 9: Deploy to Production

### Prerequisites

1. ✅ Complete local development and testing (Steps 1-8)
2. Account on a managed hosting platform (Railway, Render, or Fly.io recommended)
3. Domain access for `connector.get-to-rev.com`
4. Google Cloud Console access for updating OAuth settings

---

## Option A: Deploy to Railway (Recommended)

Railway is a great choice because:
- Easy PostgreSQL database setup
- Simple custom domain configuration
- Automatic HTTPS
- Built-in Docker support

### 9.1 Deploy to Railway

1. **Sign up/Login to Railway**:
   - Go to [railway.app](https://railway.app)
   - Sign up or log in with GitHub

2. **Create a New Project**:
   - Click "New Project"
   - Select "Deploy from GitHub repo" (recommended) or "Empty Project"

3. **Add PostgreSQL Database**:
   - In your project, click "+ New"
   - Select "Database" → "PostgreSQL"
   - Railway will automatically create a PostgreSQL database
   - Note the connection string (you'll need it for `DATABASE_URL`)

4. **Deploy the Application**:
   - If using GitHub: Connect your repo and select it
   - Railway will automatically detect the Dockerfile
   - Or click "+ New" → "GitHub Repo" and select your repository

5. **Set Environment Variables**:
   In Railway, go to your service → Variables tab and add:

   ```
   DATABASE_URL=<Railway PostgreSQL connection string>
   SECRET_KEY=<generate a strong random string>
   ENCRYPTION_KEY=<generate using: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
   GOOGLE_CLIENT_ID=<your Google OAuth Client ID>
   GOOGLE_CLIENT_SECRET=<your Google OAuth Client Secret>
   GOOGLE_REDIRECT_URI=https://connector.get-to-rev.com/auth/google/callback
   APP_BASE_URL=https://connector.get-to-rev.com
   ENVIRONMENT=production
   PORT=8000
   ```

   **Generate keys**:
   ```bash
   # SECRET_KEY (32+ character random string)
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   
   # ENCRYPTION_KEY
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

6. **Run Database Migrations**:
   Railway can run migrations automatically, or you can run them manually:
   - Go to your service → Settings → Deploy
   - Add a build command (if needed): `alembic upgrade head`
   - Or use Railway's CLI:
     ```bash
     railway run alembic upgrade head
     ```

7. **Deploy**:
   - Railway will automatically deploy when you push to your main branch
   - Or trigger a manual deployment from the Dashboard

### 9.2 Add Custom Domain (Railway)

1. **In Railway Dashboard**:
   - Go to your service → Settings → Networking
   - Click "Custom Domain"
   - Enter: `connector.get-to-rev.com`
   - Railway will provide DNS records to configure

2. **Configure DNS** (Step 9.3 below)

### 9.3 Configure DNS

In your domain provider (where `get-to-rev.com` is managed):

1. **Add CNAME Record**:
   ```
   Type: CNAME
   Name: connector
   Value: <Railway-provided-domain> (e.g., your-app.up.railway.app)
   TTL: 3600 (or default)
   ```

2. **Wait for Propagation** (5-60 minutes)

3. **Verify in Railway**:
   - Railway will automatically provision SSL certificate once DNS is configured
   - Check the "Custom Domain" section for status

### 9.4 Ensure HTTPS

✅ Railway automatically provides HTTPS certificates via Let's Encrypt once DNS is configured.

---

## Option B: Deploy to Render

Render is another excellent option with similar features.

### 9.1 Deploy to Render

1. **Sign up/Login to Render**:
   - Go to [render.com](https://render.com)
   - Sign up or log in with GitHub

2. **Create PostgreSQL Database**:
   - Go to Dashboard → "New +" → "PostgreSQL"
   - Choose plan (Free tier available for testing)
   - Note the connection string

3. **Create Web Service**:
   - Go to Dashboard → "New +" → "Web Service"
   - Connect your GitHub repository
   - Render will auto-detect Python

4. **Configure Service**:
   - **Build Command**: `pip install -r requirements.txt && alembic upgrade head`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Environment**: `Python 3`

5. **Set Environment Variables** (same as Railway above)

6. **Deploy**: Render will automatically deploy

### 9.2-9.4 Custom Domain (Render)

1. Go to your service → Settings → Custom Domain
2. Add `connector.get-to-rev.com`
3. Configure DNS as per Render's instructions
4. HTTPS is automatic once DNS is configured

---

## Step 10: Update Google OAuth for Production

⚠️ **CRITICAL**: Update your Google Cloud Console OAuth settings for production.

### Update Authorized Redirect URIs

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to "APIs & Services" → "Credentials"
3. Click on your OAuth 2.0 Client ID
4. Under "Authorized redirect URIs", add:
   ```
   https://connector.get-to-rev.com/auth/google/callback
   https://connector.get-to-rev.com/ga/callback
   ```
5. Under "Authorized JavaScript origins", add:
   ```
   https://connector.get-to-rev.com
   ```
6. Click "Save"

### Update OAuth Consent Screen

1. Go to "APIs & Services" → "OAuth consent screen"
2. Add your production domain to "Authorized domains"
3. Update "Application homepage link" and "Privacy policy link" if needed

---

## Post-Deployment Checklist

- [ ] Verify app is running: `https://connector.get-to-rev.com/health`
- [ ] Test user login: `https://connector.get-to-rev.com/auth/google/login`
- [ ] Test GA connection: `https://connector.get-to-rev.com/ga/connect`
- [ ] Verify HTTPS is working (green lock icon)
- [ ] Check database migrations were applied
- [ ] Verify all environment variables are set correctly
- [ ] Test GPT OAuth flow with production URL
- [ ] Update API documentation URLs

---

## Troubleshooting

### Application won't start
- Check environment variables are all set
- Review logs in Railway/Render dashboard
- Ensure `DATABASE_URL` is correct

### Database connection errors
- Verify PostgreSQL is running
- Check `DATABASE_URL` format
- Ensure migrations have run: `alembic upgrade head`

### OAuth redirect errors
- Verify redirect URIs in Google Cloud Console match production URLs
- Check `APP_BASE_URL` and `GOOGLE_REDIRECT_URI` environment variables

### Custom domain not working
- Wait for DNS propagation (can take up to 48 hours)
- Verify CNAME record is correct
- Check domain status in hosting platform

---

## Next Steps

After successful deployment:

1. **Step 11**: Generate OpenAPI spec for Custom GPT Actions
2. **Step 12**: Configure the Custom GPT in ChatGPT
3. **Step 13**: End-to-end testing in production

---

## Security Notes

⚠️ **Production Security Checklist**:
- [ ] `SECRET_KEY` is a strong random string (not reused from development)
- [ ] `ENCRYPTION_KEY` is unique and securely generated
- [ ] Environment variables are not committed to git
- [ ] HTTPS is enforced
- [ ] CORS is properly configured for production domains only
- [ ] Database backups are enabled
- [ ] Monitoring/alerting is set up

