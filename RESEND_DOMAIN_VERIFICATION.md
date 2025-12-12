# Resend Domain Verification Guide for chef-bartender.online

This guide will help you verify your domain `chef-bartender.online` in Resend so you can send emails to any recipient.

## Step 1: Add Domain in Resend

1. **Go to Resend Dashboard:**
   - Visit [resend.com](https://resend.com) and log in
   - Click on **"Domains"** in the left sidebar

2. **Add Your Domain:**
   - Click the **"Add Domain"** button
   - Enter your domain: `chef-bartender.online`
   - Click **"Add"**

3. **Get DNS Records:**
   - Resend will show you DNS records that need to be added
   - You'll typically see 3-4 records like:
     - **SPF Record** (TXT record)
     - **DKIM Records** (CNAME records - usually 2-3)
     - **DMARC Record** (TXT record - optional but recommended)

## Step 2: Add DNS Records to Your Domain

You need to add these DNS records where you registered `chef-bartender.online`. Common registrars include:
- Namecheap
- GoDaddy
- Cloudflare
- Google Domains
- Name.com
- etc.

### How to Add DNS Records (General Steps):

1. **Log into your domain registrar** (where you bought `chef-bartender.online`)

2. **Find DNS Management:**
   - Look for "DNS Management", "DNS Settings", "DNS Records", or "Advanced DNS"
   - This is usually in your domain settings

3. **Add Each Record:**
   
   **For TXT Records (SPF/DMARC):**
   - Click "Add Record" or "+"
   - Select **Type**: `TXT`
   - **Name/Host**: (Resend will tell you - might be `@` or blank for root domain, or `_dmarc` for DMARC)
   - **Value**: Copy the exact value from Resend
   - **TTL**: Leave default (usually 3600 or Auto)
   - Click "Save" or "Add"

   **For CNAME Records (DKIM):**
   - Click "Add Record" or "+"
   - Select **Type**: `CNAME`
   - **Name/Host**: Copy from Resend (usually something like `resend._domainkey` or similar)
   - **Value/Target**: Copy the exact value from Resend
   - **TTL**: Leave default
   - Click "Save" or "Add"

### Example DNS Records (Your actual values will be different):

```
Type: TXT
Name: @
Value: v=spf1 include:resend.com ~all

Type: CNAME
Name: resend._domainkey
Value: resend.com

Type: TXT
Name: _dmarc
Value: v=DMARC1; p=none;
```

## Step 3: Wait for DNS Propagation

- DNS changes can take **5 minutes to 48 hours** to propagate
- Usually takes **15-30 minutes** in most cases
- You can check propagation status at [whatsmydns.net](https://www.whatsmydns.net)

## Step 4: Verify Domain in Resend

1. **Go back to Resend Dashboard** → **Domains**
2. **Click on your domain** (`chef-bartender.online`)
3. **Click "Verify"** or wait for automatic verification
4. Resend will check if the DNS records are correctly set
5. Once verified, you'll see a green checkmark ✅

## Step 5: Update Railway Configuration

Once your domain is verified in Resend:

1. **Go to Railway Dashboard:**
   - Open your project → Your Web Service → **Variables** tab

2. **Update Environment Variables:**
   - Update `MAIL_DEFAULT_SENDER` to use your verified domain:
     ```
     MAIL_DEFAULT_SENDER=noreply@chef-bartender.online
     ```
   - Or you can use:
     ```
     MAIL_DEFAULT_SENDER=Chef & Bartender <noreply@chef-bartender.online>
     ```

3. **Keep your Resend API Key:**
   - Make sure `RESEND_API_KEY` is still set (starts with `re_`)

## Step 6: Test

1. **Railway will automatically redeploy** when you update environment variables
2. **Wait for deployment to complete** (2-3 minutes)
3. **Test registration:**
   - Go to `https://chef-bartender.up.railway.app/register`
   - Register with any email address
   - Check if OTP email is received

## Troubleshooting

### DNS Records Not Working?

1. **Check DNS Propagation:**
   - Use [whatsmydns.net](https://www.whatsmydns.net) to check if records are visible globally
   - Enter your domain and check TXT/CNAME records

2. **Common Issues:**
   - **Wrong record type**: Make sure TXT records are TXT, CNAME records are CNAME
   - **Wrong name/host**: Double-check the exact name from Resend (case-sensitive)
   - **Wrong value**: Copy the entire value exactly, including spaces
   - **TTL too high**: If you made a mistake, lower TTL to 300 (5 minutes) temporarily

3. **Verify in Resend:**
   - Go to Resend → Domains → Your domain
   - Check the status - it will show which records are missing/incorrect

### Domain Still Not Verified?

- Wait longer (up to 48 hours for some DNS providers)
- Double-check all DNS records match exactly what Resend shows
- Some registrars require you to remove the domain name from the host field (e.g., use `@` instead of `chef-bartender.online`)

### Emails Still Not Sending?

1. **Check Resend Logs:**
   - Go to Resend Dashboard → **Logs**
   - See if emails are being sent and any error messages

2. **Verify Sender Address:**
   - Make sure `MAIL_DEFAULT_SENDER` uses your verified domain
   - Format: `noreply@chef-bartender.online` or `Chef & Bartender <noreply@chef-bartender.online>`

3. **Check Railway Logs:**
   - Railway Dashboard → Your Service → Deployments → View Logs
   - Look for email sending errors

## Quick Reference

**Required Railway Environment Variables:**
```
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
MAIL_DEFAULT_SENDER=noreply@chef-bartender.online
```

**Domain Status Check:**
- Resend Dashboard → Domains → chef-bartender.online
- Should show ✅ Verified

**Test Email Configuration:**
- Visit: `https://chef-bartender.up.railway.app/test-email-config`
- Should show `email_provider: "Resend API"`

---

Once verified, you'll be able to send emails to **any email address**, not just your own!
