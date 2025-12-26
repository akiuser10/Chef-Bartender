# Railway Quick Start Checklist

## ✅ Pre-Deployment Checklist

- [x] Code is committed and pushed to GitHub
- [x] Dockerfile is configured
- [x] railway.json is configured
- [x] Environment variables are documented
- [x] Database configuration supports PostgreSQL

## 🚀 Deployment Steps

### 1. Create Railway Project
- [ ] Sign up/login at [railway.app](https://railway.app)
- [ ] Click "New Project" → "Deploy from GitHub repo"
- [ ] Select your repository
- [ ] Wait for initial build

### 2. Add PostgreSQL Database
- [ ] Click "+ New" → "Database" → "Add PostgreSQL"
- [ ] Verify `DATABASE_URL` is automatically set

### 3. Set Environment Variables
- [ ] Go to your service → "Variables" tab
- [ ] Add `SECRET_KEY` (generate with: `python -c "import secrets; print(secrets.token_hex(32))"`)
- [ ] (Optional) Add email API keys if needed

### 4. Deploy
- [ ] Railway will auto-deploy on push
- [ ] Check "Deployments" tab for status
- [ ] View "Logs" to verify startup
- [ ] Visit your app URL

### 5. Verify
- [ ] Visit `/health` endpoint - should return `{"status": "ok"}`
- [ ] Register a new user account
- [ ] Test login functionality
- [ ] Test file uploads (if configured)

## 📝 Environment Variables Needed

**Required:**
- `SECRET_KEY` - Flask secret key

**Auto-set by Railway:**
- `DATABASE_URL` - PostgreSQL connection
- `PORT` - Server port

**Optional (for emails):**
- `RESEND_API_KEY` - Recommended for Railway
- OR `SENDGRID_API_KEY`
- OR SMTP settings (`MAIL_SERVER`, `MAIL_PORT`, etc.)

## 🔗 Quick Links

- Railway Dashboard: https://railway.app
- Your App URL: (shown in Railway dashboard)
- Health Check: `https://your-app.railway.app/health`

## 📚 Full Documentation

See `RAILWAY_DEPLOY.md` for detailed instructions.

