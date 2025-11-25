# Railway Deployment Checklist

## ✅ Completed Steps
- [x] Step 1: Sign up/Login to Railway
- [x] Step 2: Create New Project
- [x] Step 3: Deploy from GitHub repo
- [x] Step 4: Railway auto-detected Dockerfile
- [x] Step 5: Add PostgreSQL Database

## 🔧 Next Steps: Configure Environment Variables

### Step 6: Get Database URL from Railway

1. In Railway dashboard, click on your **PostgreSQL** service
2. Go to the **Variables** tab
3. Find `DATABASE_URL` - **Copy this value** (it's already set automatically)
4. You'll need this for your app service

### Step 7: Set Environment Variables for Your App Service

1. In Railway, click on your **Web Service** (the app, not the database)
2. Go to the **Variables** tab
3. Click **+ New Variable** for each variable below

#### Required Variables:

```
DATABASE_URL=<paste from PostgreSQL service Variables tab>
```

```
SECRET_KEY=e0Dd5Wyh-xIn0fHPjSe5wD8YTGYsfvVZUHIJIEWBpMU
```

```
ENCRYPTION_KEY=V3FqWns9PbRVUChhJDUsWQyPGphtGjSBwlrT_m17yDs=
```

```
GOOGLE_CLIENT_ID=<your Google OAuth Client ID>
```

```
GOOGLE_CLIENT_SECRET=<your Google OAuth Client Secret>
```

```
GOOGLE_REDIRECT_URI=https://ga-connector-api-production.up.railway.app/auth/google/callback
```
Note: Use your actual Railway domain. Later, update this to `https://connector.get-to-rev.com/auth/google/callback` after adding custom domain.

```
APP_BASE_URL=https://ga-connector-api-production.up.railway.app
```
Note: Use your actual Railway domain (check `RAILWAY_PUBLIC_DOMAIN` variable that Railway provides automatically). Later, update this to `https://connector.get-to-rev.com` after adding custom domain.

```
ENVIRONMENT=production
```

### Step 8: Generate Production Keys

Run these commands locally to generate secure keys:

```bash
# Generate SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate ENCRYPTION_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**⚠️ Important**: Save these keys securely - you won't be able to see them again in Railway!

### Step 9: Get Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to "APIs & Services" → "Credentials"
3. Find your OAuth 2.0 Client ID
4. Copy:
   - **Client ID** → `GOOGLE_CLIENT_ID`
   - **Client Secret** → `GOOGLE_CLIENT_SECRET`

### Step 10: Verify Deployment

After setting all variables:
1. Railway will automatically redeploy
2. Check the **Deployments** tab for build status
3. Once deployed, click on your service → **Settings** → **Generate Domain**
4. Test the health endpoint: `https://your-app.up.railway.app/health`

### Step 11: Run Database Migrations

The Dockerfile should run migrations automatically, but you can verify:

1. In Railway, go to your app service
2. Click **Deployments** tab
3. Check the logs - you should see: `alembic upgrade head`
4. If migrations didn't run, you can run them manually:
   - Click on your service → **Settings** → **Deploy**
   - Or use Railway CLI: `railway run alembic upgrade head`

## 🎯 After Environment Variables Are Set

Once all variables are configured:
- Railway will automatically redeploy
- Your app will be live at the Railway domain
- Next: Add custom domain (connector.get-to-rev.com)

