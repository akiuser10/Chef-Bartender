# Railway Database URL Setup Guide

## How to Check and Link DATABASE_URL in Railway

### Step 1: Verify PostgreSQL Service is Running

1. Go to your Railway project: https://railway.com/project/beaeed50-5406-45cf-852f-9eba4bf94733
2. Find your **PostgreSQL** service
3. Check that it shows **"Active"** or **"Running"** status (green indicator)

### Step 2: Check DATABASE_URL in Web Service

1. Go to your **"Chef-Bartender"** web service (not PostgreSQL)
2. Click on the **"Variables"** tab
3. Look for `DATABASE_URL` in the list

**If DATABASE_URL is present:**
- ✅ It should be automatically linked
- The value should start with `postgresql://` or `postgres://`
- Railway automatically sets this when services are in the same project

**If DATABASE_URL is missing:**
- ❌ You need to link it manually (see Step 3)

### Step 3: Link DATABASE_URL Manually (If Missing)

1. In your **"Chef-Bartender"** web service → **"Variables"** tab
2. Click **"+ New Variable"** or **"Add Variable"**
3. Click **"Add Reference"** or **"Link Variable"**
4. Select your **PostgreSQL** service
5. Select **`DATABASE_URL`** from the dropdown
6. Click **"Add"** or **"Save"**

Railway will automatically:
- Link the variable
- Update it if the database connection changes
- Keep it in sync

### Step 4: Verify the Link

After linking, you should see:
- `DATABASE_URL` in your web service variables
- It should show as a "reference" (not a direct value)
- The value should be masked (for security)

### Step 5: Redeploy (If Needed)

1. After adding/linking `DATABASE_URL`, Railway may auto-redeploy
2. If not, go to your web service → **"Deployments"** tab
3. Click **"Redeploy"** or **"Deploy Latest"**

### Step 6: Test the Connection

1. Visit: https://chef-bartender.up.railway.app/
2. Check Railway logs for:
   - "Database connection successful"
   - "Database initialized successfully"

## Troubleshooting

### Issue: DATABASE_URL shows but connection still fails

**Check the format:**
- Should be: `postgresql://user:password@host:port/database`
- Railway should provide this automatically

**Check Railway logs:**
- Look for connection error messages
- Verify PostgreSQL service is actually running

### Issue: Services are in different projects

**Solution:**
- Move both services to the same Railway project
- Railway only auto-links services in the same project

### Issue: PostgreSQL service not running

**Solution:**
1. Go to PostgreSQL service
2. Check status - should be "Active"
3. If stopped, start it
4. Wait for it to be fully running before testing

## Quick Verification Checklist

- [ ] PostgreSQL service is "Active" or "Running"
- [ ] PostgreSQL and web service are in the same Railway project
- [ ] `DATABASE_URL` exists in web service Variables tab
- [ ] `DATABASE_URL` is linked/referenced (not a hardcoded value)
- [ ] Web service has been redeployed after linking
- [ ] Check logs for "Database connection successful"

## Expected DATABASE_URL Format

Railway provides `DATABASE_URL` in this format:
```
postgresql://postgres:password@postgres.railway.internal:5432/railway
```

Or for public connections:
```
postgresql://postgres:password@host.railway.app:5432/railway
```

The app automatically converts `postgres://` to `postgresql://` if needed.

