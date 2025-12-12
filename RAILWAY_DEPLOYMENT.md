# Railway Deployment Guide - Chef & Bartender

## 🚂 Deploy to Railway (Step-by-Step)

Railway is one of the easiest platforms to deploy Flask applications. Follow these steps:

---

## Step 1: Prepare Your Code

### 1.1 Initialize Git (if not already done)

```bash
cd "/Volumes/Akhil SSD/Chef & Bartender"
git init
git add .
git commit -m "Ready for Railway deployment"
```

### 1.2 Push to GitHub

1. **Create a new repository on GitHub:**
   - Go to [github.com](https://github.com)
   - Click "New repository"
   - Name it (e.g., `chef-bartender`)
   - Don't initialize with README
   - Click "Create repository"

2. **Push your code:**
   ```bash
   git remote add origin https://github.com/akiuser10/Chef-Bartender.git
   git branch -M main
   git push -u origin main
   ```
   
   **Note:** If you already have a remote set, update it with:
   ```bash
   git remote set-url origin https://github.com/akiuser10/Chef-Bartender.git
   git push -u origin main
   ```

---

## Step 2: Deploy on Railway

### 2.1 Sign Up / Login

1. Go to [railway.app](https://railway.app)
2. Click "Start a New Project"
3. Sign up with GitHub (recommended) or email

### 2.2 Create New Project

1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Authorize Railway to access your GitHub (if needed)
4. Select your repository (`chef-bartender` or your repo name)
5. Railway will automatically detect it's a Python/Flask app

### 2.3 Add PostgreSQL Database

1. In your Railway project dashboard, click **"+ New"**
2. Select **"Database"** → **"Add PostgreSQL"**
3. Railway will create a PostgreSQL database
4. The `DATABASE_URL` environment variable will be automatically set

### 2.4 Configure Environment Variables

1. Click on your **Web Service** (the one with your app name)
2. Go to the **"Variables"** tab
3. Add the following environment variable:

   **SECRET_KEY:**
   - Click **"+ New Variable"**
   - Key: `SECRET_KEY`
   - Value: Generate one using:
     ```bash
     python3 -c "import secrets; print(secrets.token_hex(32))"
     ```
   - Or use this one (for reference): `5ceb4a7bb084c6fdd6a210917463879ea8fcb19d02906049ffbe4d26f581732d`
   - Click **"Add"**

   **Note:** `DATABASE_URL` is automatically set when you add PostgreSQL, so you don't need to add it manually.

3. **Configure Email Settings (for OTP verification):**
   - Click **"+ New Variable"** and add each of these:
   
   ```
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USE_TLS=true
   MAIL_USE_SSL=false
   MAIL_USERNAME=akiuser10@gmail.com
   MAIL_PASSWORD=<your-gmail-app-password>
   MAIL_DEFAULT_SENDER=akiuser10@gmail.com
   ```
   
   **Note:** 
   - Replace `<your-gmail-app-password>` with your actual Gmail App Password
   - Remove spaces from the app password when entering (e.g., `vahw jfyq bpix vtjc` becomes `vahwjfyqbpixvtjc`)
   - See `EMAIL_CONFIGURATION.md` for more details

### 2.5 Configure Build Settings (Optional)

Railway should auto-detect your Flask app, but you can verify:

1. Go to your **Web Service** → **"Settings"** tab
2. **Build Command:** (leave empty or set to `pip install -r requirements.txt`)
3. **Start Command:** `gunicorn app:app` (should be auto-detected)

### 2.6 Deploy

1. Railway will automatically start deploying when you:
   - Push code to your GitHub repo, OR
   - Click **"Deploy"** in the Railway dashboard
2. Wait 2-5 minutes for the first deployment
3. Your app will be live at: `https://your-app-name.up.railway.app`

---

## Step 3: Get Your App URL

1. In Railway dashboard, click on your **Web Service**
2. Go to **"Settings"** tab
3. Scroll to **"Domains"** section
4. Your app URL will be shown (e.g., `https://chef-bartender-production.up.railway.app`)
5. You can also add a custom domain if you have one

---

## Step 4: Initial Setup

1. **Visit your app URL**
2. **Register the first user** (this will be your admin account)
3. **Set your organization** in the profile page
4. **Start adding products, recipes, and ingredients!**

---

## 📋 Pre-Deployment Checklist

✅ **Files Ready:**
- [x] `requirements.txt` includes `gunicorn` and `psycopg2-binary`
- [x] `Procfile` exists with `web: gunicorn app:app`
- [x] `railway.json` created for Railway-specific config
- [x] `config.py` supports `DATABASE_URL` environment variable
- [x] `.gitignore` excludes sensitive files

✅ **Code Ready:**
- [x] App uses `create_app()` factory pattern
- [x] Database migrations run automatically
- [x] File uploads directory is created automatically

✅ **Security:**
- [ ] Generate a secure `SECRET_KEY` (use the command above)
- [ ] Never commit `.env` files or database files
- [ ] Use environment variables for sensitive data

---

## 🔄 Updating Your App

After making changes to your code:

1. **Commit and push to GitHub:**
   ```bash
   git add .
   git commit -m "Your update message"
   git push
   ```

2. **Railway will automatically redeploy** your app (usually takes 2-3 minutes)

---

## 🐛 Troubleshooting

### App won't start
- **Check logs:** In Railway dashboard → Your Web Service → "Deployments" → Click on latest deployment → View logs
- **Verify environment variables:** Make sure `SECRET_KEY` is set
- **Check build logs:** Look for errors during `pip install`

### Database errors
- **Verify PostgreSQL is running:** Check your PostgreSQL service in Railway dashboard
- **Check DATABASE_URL:** It should be automatically set, but verify in Variables tab
- **Database format:** Railway uses `postgresql://` format (your config.py handles this)

### File uploads not working
- **Railway uses ephemeral filesystem:** Uploaded files may be lost on redeploy
- **Solution:** For production, use cloud storage (AWS S3, Cloudinary, etc.)

### Static files not loading
- **Verify static files are committed:** Check that CSS/JS files are in your Git repo
- **Check file paths:** Ensure templates use `url_for('static', ...)`

### Build fails
- **Check Python version:** Railway auto-detects, but you can specify in `runtime.txt`
- **Check requirements.txt:** Ensure all dependencies are listed
- **View build logs:** Railway shows detailed build output

---

## 💰 Railway Pricing

- **Free Tier:** $5 credit/month (usually enough for small apps)
- **Hobby Plan:** $5/month (more resources)
- **Pro Plan:** $20/month (production-ready)

**Note:** Free tier may have limitations on:
- Build minutes
- Data transfer
- Database size

---

## 🔐 Security Best Practices

1. **Never commit secrets:**
   - Keep `SECRET_KEY` in Railway environment variables only
   - Don't commit `.env` files

2. **Use strong SECRET_KEY:**
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

3. **Enable HTTPS:** Railway provides HTTPS automatically

4. **Database security:** Railway manages database security, but ensure your app uses connection pooling

---

## 📝 Important Notes

1. **Database Migration:**
   - Your local SQLite data won't automatically transfer
   - You'll need to re-enter data manually, or
   - Export/import data using a migration script

2. **File Storage:**
   - Uploaded images are stored in `static/uploads/`
   - On Railway, these may be lost on redeploy
   - For production, use cloud storage (AWS S3, Cloudinary, etc.)

3. **Environment Variables:**
   - Railway automatically provides `DATABASE_URL` when you add PostgreSQL
   - You only need to set `SECRET_KEY` manually

4. **Auto-Deploy:**
   - Railway automatically deploys when you push to GitHub
   - You can disable this in Settings if needed

---

## 🎉 You're Ready!

Once deployed, share your app URL with your team members. They can:
- Register accounts
- Set the same organization name
- Start collaborating on shared Master Lists, Recipes, and Secondary Ingredients!

---

## 📞 Need Help?

- **Railway Docs:** [docs.railway.app](https://docs.railway.app)
- **Railway Discord:** [discord.gg/railway](https://discord.gg/railway)
- **Check logs:** Railway dashboard → Your service → Deployments → View logs
