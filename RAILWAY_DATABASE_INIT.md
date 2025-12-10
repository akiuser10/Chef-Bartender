# Railway Database Initialization Guide

## Automatic Initialization (Recommended)

The database should initialize automatically when your app starts. The fixes ensure that:
- All tables are created on startup
- Schema updates run automatically
- Works with both SQLite (local) and PostgreSQL (Railway)

**Just wait for Railway to redeploy your app** (usually 2-5 minutes after pushing to GitHub).

## Manual Initialization (If Needed)

If tables still don't appear after deployment, you can manually initialize:

### Option A: Using Railway Web Interface

1. Go to your Railway dashboard
2. Click on your **Web Service**
3. Go to **"Deployments"** tab
4. Click on the latest deployment
5. Click **"View Logs"** to see if there are any errors
6. If you see database errors, the app should retry on the next request

### Option B: Install Railway CLI (If Manual Init Needed)

**Note:** The database should initialize automatically. Only use this if automatic initialization fails.

1. **Install Railway CLI:**
   ```bash
   # macOS
   brew install railway
   
   # Or using npm
   npm i -g @railway/cli
   ```

2. **Login to Railway:**
   ```bash
   railway login
   ```

3. **Link to your project:**
   ```bash
   railway link
   ```

4. **Run the initialization script:**
   ```bash
   # Make sure you're in the project root directory
   railway run python init_db.py
   
   # Or if that doesn't work, try:
   railway run python3 init_db.py
   ```
   
   **If you get "No such file or directory":**
   - Wait for Railway to finish deploying the latest code (check Deployments tab)
   - The file should be in the root directory after deployment
   - You can also just wait - automatic initialization should work!

### Option C: Use Railway Shell

1. In Railway dashboard → Your Web Service → **"Settings"**
2. Look for **"Shell"** or **"Console"** option
3. Run:
   ```bash
   python init_db.py
   ```

## Verify Database is Working

After initialization, you should be able to:

1. **Register a new user** at `/register`
2. **Login** at `/login`
3. **Stay logged in** between page visits
4. **See your data persist** (products, recipes, etc.)

## Troubleshooting

### If tables still don't exist:

1. **Check Railway logs:**
   - Dashboard → Web Service → Deployments → View Logs
   - Look for "Database tables created successfully" message
   - Check for any PostgreSQL connection errors

2. **Verify DATABASE_URL:**
   - Dashboard → PostgreSQL Service → Variables
   - Make sure `DATABASE_URL` is set correctly
   - It should start with `postgresql://`

3. **Check database connection:**
   - The app should connect automatically
   - If connection fails, check Railway PostgreSQL service status

### Common Issues:

- **"No tables" error:** Wait for app to fully deploy, then refresh
- **Connection errors:** Verify `DATABASE_URL` environment variable
- **Permission errors:** Railway handles permissions automatically

## Next Steps

Once the database is initialized:

1. Register your first admin account
2. Set your organization in the profile page
3. Start adding products, recipes, and ingredients!
