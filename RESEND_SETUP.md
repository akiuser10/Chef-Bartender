# Resend Setup for OTP Emails (Easier Alternative)

Since Railway blocks SMTP and SendGrid requires phone verification, we're using **Resend** - a simpler email API service.

## Why Resend?

- ✅ **No phone verification required** - Just email verification
- ✅ **Works on Railway** - Uses HTTP API, not SMTP
- ✅ **Free Tier** - 3,000 emails/month, 100 emails/day
- ✅ **Simple setup** - Just API key, no domain verification needed
- ✅ **Fast & Reliable** - Built for modern applications

## Setup Steps

### 1. Create Resend Account

1. Go to [resend.com](https://resend.com/signup)
2. Sign up with your email (no phone number needed!)
3. Verify your email address

### 2. Get API Key

1. In Resend dashboard, go to **API Keys** (in sidebar)
2. Click **"Create API Key"**
3. Name it (e.g., "Chef & Bartender Production")
4. Click **"Add"**
5. **Copy the API key** (starts with `re_`)

### 3. Verify Sender Email (Important!)

1. In Resend dashboard, go to **Domains** (in sidebar)
2. Click **"Add Domain"** OR **"Verify Email"** (if available)
3. For quick testing, you can use Resend's default domain first
4. **Better option**: Add and verify your sender email address
   - Go to **Settings** → **Sender Emails**
   - Add `akiuser10@gmail.com`
   - Verify it by clicking the verification link sent to your email

### 4. Add API Key to Railway

1. Go to Railway Dashboard → Your Service → **Variables** tab
2. Add new variable:
   - **Key**: `RESEND_API_KEY`
   - **Value**: `re_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx` (your API key)
3. Keep `MAIL_DEFAULT_SENDER=akiuser10@gmail.com`

### 5. Important: Sender Verification

Resend requires the sender email to be verified. If emails aren't being delivered:
- Check Resend dashboard → **Logs** to see delivery status
- Verify your sender email in Resend dashboard
- Or use Resend's default domain for testing

### 5. Test

After Railway redeploys:
1. Visit: `https://your-app.up.railway.app/test-email-config`
2. Check that `email_provider` shows `"Resend API"`
3. Try registering a new user
4. Check your email for the OTP

## Required Variables in Railway

Minimum required:
```
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
MAIL_DEFAULT_SENDER=akiuser10@gmail.com
```

## Resend Free Tier

- **3,000 emails/month**
- **100 emails/day**
- Full API access
- Perfect for development and small production use

## Comparison with SendGrid

| Feature | Resend | SendGrid |
|---------|--------|----------|
| Phone Verification | ❌ Not Required | ✅ Required |
| Email Verification | ✅ Required | ✅ Required |
| Free Tier | 3,000/month | 100/day |
| Setup Time | ~2 minutes | ~10 minutes |
| Domain Required | ❌ No | ✅ Optional |

## Troubleshooting

- **"Email provider: SMTP"** - RESEND_API_KEY not set correctly
- **Resend error 401** - Invalid API key
- **No emails received** - Check Resend dashboard → Logs

Resend is the recommended option for quick setup without phone verification!
