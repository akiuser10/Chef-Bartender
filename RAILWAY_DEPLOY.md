# Railway Deployment Guide

Quick guide to deploy your Bar & Bartender application to Railway.

## Prerequisites

1. **GitHub Account** - Your code should be in a GitHub repository
2. **Railway Account** - Sign up at [railway.app](https://railway.app)

## Step-by-Step Deployment

### 1. Prepare Your Repository

Ensure your code is committed and pushed to GitHub:

```bash
git add .
git commit -m "Ready for Railway deployment"
git push origin main
```

### 2. Create Railway Project

1. Go to [railway.app](https://railway.app) and sign in
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your repository
5. Railway will automatically detect the Dockerfile and start building

### 3. Add PostgreSQL Database

1. In your Railway project dashboard, click **"+ New"**
2. Select **"Database"** → **"Add PostgreSQL"**
3. Railway will automatically:
   - Create the database
   - Set the `DATABASE_URL` environment variable
   - Link it to your web service

### 4. Configure Environment Variables

Go to your web service → **Variables** tab and add:

#### Required Variables:

- **`SECRET_KEY`** - Generate a secure key:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

#### Optional Variables (for email functionality):

- **`MAIL_SERVER`** - SMTP server (e.g., `smtp.gmail.com`)
- **`MAIL_PORT`** - SMTP port (e.g., `465` for SSL)
- **`MAIL_USE_SSL`** - Set to `true` for port 465
- **`MAIL_USERNAME`** - Your email address
- **`MAIL_PASSWORD`** - Your email app password
- **`MAIL_DEFAULT_SENDER`** - Sender email address

**OR** use email APIs (recommended for Railway):

- **`RESEND_API_KEY`** - Get from [resend.com](https://resend.com) (recommended)
- **`SENDGRID_API_KEY`** - Get from [sendgrid.com](https://sendgrid.com)

### 5. Configure Persistent Storage (Optional)

For file uploads to persist across deployments:

1. In your web service, go to **"Settings"** → **"Volumes"**
2. Click **"Add Volume"**
3. Mount path: `/data`
4. Update the volume to persist uploads

The app will automatically detect `/data` and use `/data/uploads` for file storage.

### 6. Deploy

Railway will automatically:
- Build your Docker image
- Deploy your application
- Set up the database connection
- Start your app

### 7. Verify Deployment

1. Check the **"Deployments"** tab for build status
2. View **"Logs"** to ensure the app started successfully
3. Click on your service to get the public URL
4. Visit `/health` endpoint to verify it's running

## Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `SECRET_KEY` | ✅ Yes | Flask secret key | `your-secret-key-here` |
| `DATABASE_URL` | ✅ Auto | PostgreSQL connection (set automatically) | `postgresql://...` |
| `PORT` | ✅ Auto | Server port (set automatically) | `8080` |
| `RESEND_API_KEY` | ⚠️ Optional | Resend API key for emails | `re_...` |
| `SENDGRID_API_KEY` | ⚠️ Optional | SendGrid API key for emails | `SG....` |
| `MAIL_SERVER` | ⚠️ Optional | SMTP server | `smtp.gmail.com` |
| `MAIL_PORT` | ⚠️ Optional | SMTP port | `465` |
| `MAIL_USE_SSL` | ⚠️ Optional | Use SSL | `true` |
| `MAIL_USERNAME` | ⚠️ Optional | SMTP username | `your@email.com` |
| `MAIL_PASSWORD` | ⚠️ Optional | SMTP password | `your-app-password` |

## Troubleshooting

### Build Fails

- Check the build logs in Railway dashboard
- Ensure `requirements.txt` is up to date
- Verify Dockerfile syntax

### Database Connection Errors

- Ensure PostgreSQL service is running (green status)
- Check that `DATABASE_URL` is set (Railway sets this automatically)
- Verify services are in the same project (they auto-link)

### App Won't Start

- Check logs for errors
- Verify `SECRET_KEY` is set
- Ensure port binding is correct (Railway sets `PORT` automatically)

### File Uploads Not Persisting

- Add a persistent volume at `/data`
- Or use Railway's object storage service

### Email Not Working

- Railway may block SMTP ports (587, 25)
- **Recommended:** Use Resend API instead
- Set `RESEND_API_KEY` environment variable

## Post-Deployment

1. **Initialize Database:**
   - The app automatically creates tables on first startup
   - Check logs for "Database initialization completed successfully"

2. **Create Admin User:**
   - Visit your app URL
   - Register a new account (first user becomes admin)
   - Or use Railway CLI to run commands

3. **Test Features:**
   - Login/Registration
   - File uploads
   - Database operations
   - Email functionality (if configured)

## Custom Domain (Optional)

1. Go to your service → **Settings** → **Domains**
2. Click **"Generate Domain"** for a Railway subdomain
3. Or add your custom domain

## Monitoring

- **Logs:** View real-time logs in Railway dashboard
- **Metrics:** Check CPU, memory usage in the Metrics tab
- **Deployments:** Track deployment history

## Updating Your App

Simply push to your GitHub repository's main branch:

```bash
git add .
git commit -m "Update app"
git push origin main
```

Railway will automatically detect the change and redeploy.

## Cost

- **Free Tier:** $5/month credit (usually enough for small apps)
- **PostgreSQL:** Included in free tier
- **Bandwidth:** Generous free tier

## Support

- Railway Docs: [docs.railway.app](https://docs.railway.app)
- Railway Discord: [discord.gg/railway](https://discord.gg/railway)

