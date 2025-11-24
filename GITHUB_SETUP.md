# GitHub Setup Guide

## Step 1: Configure Git (if not already done)

Set your git user name and email (replace with your GitHub credentials):

```bash
git config --global user.name "jrdesvernay-gtr"
git config --global user.email "jrdesvernay@get-to-rev.com"
```

Or set it just for this repository:

```bash
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

## Step 2: Create GitHub Repository

1. Go to [GitHub.com](https://github.com) and sign in
2. Click the "+" icon in the top right → "New repository"
3. Repository name: `connector-gpt-analytics` (or your preferred name)
4. Description: "GA4 to Custom GPT connector - Secure multi-tenant analytics connector"
5. Choose: **Private** (recommended for production code) or **Public**
6. **DO NOT** initialize with README, .gitignore, or license (we already have these)
7. Click "Create repository"

## Step 3: Connect Local Repository to GitHub

After creating the repository, GitHub will show you commands. Use these:

```bash
# Add the remote repository (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/jrdesvernay-gtr/connector-gpt-analytics.git

# Or if you prefer SSH (requires SSH key setup):
# git remote add origin git@github.com:YOUR_USERNAME/connector-gpt-analytics.git

# Rename branch to 'main' (if needed)
git branch -M main

# Push your code to GitHub
git push -u origin main
```

## Step 4: Verify

1. Go to your GitHub repository page
2. You should see all your files there
3. Check that `.env` files are NOT visible (they should be in .gitignore)

## Step 5: Deploy to Hosting Platform

Now you can connect your GitHub repository to:
- **Railway**: New Project → Deploy from GitHub repo
- **Render**: New Web Service → Connect GitHub repository
- **Fly.io**: Use `fly launch` and connect to GitHub

## Security Checklist

Before pushing, make sure:
- ✅ `.env` is in `.gitignore` (it is)
- ✅ No secrets are hardcoded in files
- ✅ `.env.production.example` doesn't contain real secrets
- ✅ Database credentials are not committed

## Troubleshooting

### "Permission denied" error
- Make sure you're authenticated with GitHub
- Use HTTPS with a Personal Access Token, or set up SSH keys

### "Repository not found"
- Check the repository name and your GitHub username
- Make sure the repository exists on GitHub

### Want to keep it private?
- GitHub allows free private repositories
- Perfect for production code with secrets

