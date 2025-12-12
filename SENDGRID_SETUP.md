# SendGrid Setup for OTP Emails

Since Railway blocks SMTP connections, we're using SendGrid API (HTTP-based) which works reliably on Railway.

## Why SendGrid?

- ✅ **Works on Railway** - Uses HTTP API, not SMTP
- ✅ **Free Tier** - 100 emails/day forever
- ✅ **Reliable** - Built for cloud platforms
- ✅ **Fast** - No connection delays

## Setup Steps

### 1. Create SendGrid Account

1. Go to [sendgrid.com](https://signup.sendgrid.com/)
2. Sign up for a free account (no credit card required)
3. Verify your email address

### 2. Create API Key

1. In SendGrid dashboard, go to **Settings** → **API Keys**
2. Click **"Create API Key"**
3. Name it (e.g., "Chef & Bartender Production")
4. Select **"Full Access"** or **"Mail Send"** permissions
5. Click **"Create & View"**
6. **Copy the API key immediately** (you won't be able to see it again!)

### 3. Verify Sender Email

1. Go to **Settings** → **Sender Authentication**
2. Click **"Verify a Single Sender"**
3. Fill in the form:
   - **From Email Address**: `akiuser10@gmail.com`
   - **From Name**: `Chef & Bartender`
   - Complete the verification process

### 4. Add API Key to Railway

1. Go to Railway Dashboard → Your Service → **Variables** tab
2. Add a new variable:
   - **Key**: `SENDGRID_API_KEY`
   - **Value**: `SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxx` (your API key from step 2)
3. Click **"Add"**

### 5. Remove or Keep SMTP Variables (Optional)

You can now **remove** these SMTP variables from Railway (they won't be used):
- `MAIL_SERVER`
- `MAIL_PORT`
- `MAIL_USE_TLS`
- `MAIL_USE_SSL`
- `MAIL_USERNAME`
- `MAIL_PASSWORD`

**OR** keep them as fallback for local development.

### 6. Required Variables

Minimum required in Railway:
```
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
MAIL_DEFAULT_SENDER=akiuser10@gmail.com
```

### 7. Test

After Railway redeploys:
1. Visit: `https://your-app.up.railway.app/test-email-config`
2. Check that `email_provider` shows `"SendGrid API"`
3. Try registering a new user
4. Check your email for the OTP

## Troubleshooting

- **"Email provider: SMTP"** - SendGrid API key not set correctly
- **SendGrid error 403** - API key doesn't have correct permissions
- **SendGrid error 400** - Sender email not verified
- **No emails received** - Check SendGrid Activity Feed in dashboard

## SendGrid Free Tier Limits

- 100 emails/day
- Unlimited contacts
- Full API access
- Perfect for development and small production use

If you need more, SendGrid offers paid plans starting at $19.95/month for 50,000 emails.
