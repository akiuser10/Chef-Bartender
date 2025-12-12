# Namecheap DNS Setup for Resend Domain Verification

This guide is specifically for adding Resend DNS records in **Namecheap**.

## Step 1: Get DNS Records from Resend

1. **Go to Resend Dashboard:**
   - Visit [resend.com](https://resend.com) and log in
   - Click on **"Domains"** in the left sidebar
   - Click **"Add Domain"**
   - Enter: `chef-bartender.online`
   - Click **"Add"**

2. **Copy the DNS Records:**
   - Resend will show you the DNS records you need to add
   - You'll typically see:
     - **1 SPF Record** (TXT type)
     - **2-3 DKIM Records** (CNAME type)
     - **1 DMARC Record** (TXT type - optional but recommended)
   - **Keep this page open** - you'll need to copy each record

## Step 2: Access Namecheap DNS Settings

1. **Log into Namecheap:**
   - Go to [namecheap.com](https://www.namecheap.com)
   - Click **"Sign In"** (top right)
   - Enter your credentials

2. **Go to Domain List:**
   - Click **"Domain List"** from the top menu
   - Find `chef-bartender.online` in your list
   - Click **"Manage"** button next to your domain

3. **Access Advanced DNS:**
   - Scroll down to the **"Advanced DNS"** section
   - Click on the **"Advanced DNS"** tab
   - You'll see a table with existing DNS records

## Step 3: Add DNS Records in Namecheap

### Adding TXT Records (SPF and DMARC)

For each **TXT record** from Resend:

1. **Click "Add New Record"** button
2. **Select Record Type:**
   - Click the dropdown and select **"TXT Record"**

3. **Fill in the fields:**
   - **Host**: 
     - For SPF (root domain): Enter `@` (this means the root domain)
     - For DMARC: Enter `_dmarc` (exactly as shown in Resend)
   - **Value**: 
     - Copy the **entire value** from Resend (including all text)
     - Paste it exactly as shown
   - **TTL**: 
     - Leave as **"Automatic"** or set to **300** (5 minutes) for faster updates

4. **Click the green checkmark (✓)** to save

### Adding CNAME Records (DKIM)

For each **CNAME record** from Resend:

1. **Click "Add New Record"** button
2. **Select Record Type:**
   - Click the dropdown and select **"CNAME Record"**

3. **Fill in the fields:**
   - **Host**: 
     - Copy the **exact host name** from Resend
     - Example: `resend._domainkey` or similar
     - **Important**: Do NOT include the domain name, just the subdomain part
   - **Value**: 
     - Copy the **entire value** from Resend
     - Example: `resend.com` or a longer value
   - **TTL**: 
     - Leave as **"Automatic"** or set to **300**

4. **Click the green checkmark (✓)** to save

## Step 4: Example Records (Your values will be different!)

Here's what the records might look like in Namecheap:

### SPF Record (TXT):
```
Type: TXT Record
Host: @
Value: v=spf1 include:resend.com ~all
TTL: Automatic
```

### DKIM Record 1 (CNAME):
```
Type: CNAME Record
Host: resend._domainkey
Value: resend.com
TTL: Automatic
```

### DKIM Record 2 (CNAME):
```
Type: CNAME Record
Host: resend2._domainkey
Value: resend.com
TTL: Automatic
```

### DMARC Record (TXT):
```
Type: TXT Record
Host: _dmarc
Value: v=DMARC1; p=none;
TTL: Automatic
```

## Step 5: Verify Records Are Added

After adding all records:

1. **Check your records list:**
   - You should see all the records you just added in the Advanced DNS table
   - Make sure they match what Resend showed you

2. **Double-check:**
   - **Host names** match exactly (case-sensitive)
   - **Values** are complete and match Resend
   - **Record types** are correct (TXT vs CNAME)

## Step 6: Wait for DNS Propagation

- DNS changes can take **15 minutes to 48 hours**
- Usually takes **15-30 minutes** with Namecheap
- You can check propagation at [whatsmydns.net](https://www.whatsmydns.net)
  - Enter your domain and check TXT/CNAME records

## Step 7: Verify Domain in Resend

1. **Go back to Resend Dashboard:**
   - Click on **"Domains"** → `chef-bartender.online`

2. **Click "Verify"** or wait for automatic verification

3. **Check Status:**
   - You'll see which records are verified ✅
   - Any missing/incorrect records will be shown ❌
   - Fix any issues and verify again

4. **Once all records show ✅:**
   - Your domain is verified!
   - You can now send emails to any address

## Step 8: Update Railway Configuration

Once verified in Resend:

1. **Go to Railway Dashboard:**
   - Your Project → Web Service → **Variables** tab

2. **Update Environment Variable:**
   - Find `MAIL_DEFAULT_SENDER`
   - Update to: `noreply@chef-bartender.online`
   - Or: `Chef & Bartender <noreply@chef-bartender.online>`
   - Click **"Save"**

3. **Railway will automatically redeploy** (2-3 minutes)

## Troubleshooting Namecheap-Specific Issues

### Can't find Advanced DNS?
- Make sure you're in the **"Advanced DNS"** tab, not "Basic DNS"
- If you see "Namecheap BasicDNS" or "Namecheap Web Hosting DNS", you're in the wrong place
- Look for the tab that says **"Advanced DNS"**

### Host field confusion?
- For root domain records (SPF): Use `@` not `chef-bartender.online`
- For subdomain records (DKIM): Use only the subdomain part (e.g., `resend._domainkey`)
- Namecheap automatically appends your domain name

### Records not showing up?
- Click **"Refresh"** in Namecheap
- Wait a few minutes and check again
- Make sure you clicked the green checkmark (✓) to save

### Still not verified in Resend?
- Double-check each record matches exactly what Resend shows
- Wait longer (up to 48 hours for full propagation)
- Use [whatsmydns.net](https://www.whatsmydns.net) to verify records are visible globally
- Check Resend dashboard for specific error messages

## Quick Checklist

- [ ] Logged into Namecheap
- [ ] Found domain in Domain List
- [ ] Opened Advanced DNS tab
- [ ] Added all TXT records (SPF, DMARC)
- [ ] Added all CNAME records (DKIM)
- [ ] Verified all records match Resend exactly
- [ ] Waited 15-30 minutes for propagation
- [ ] Verified domain in Resend dashboard
- [ ] Updated `MAIL_DEFAULT_SENDER` in Railway
- [ ] Tested email sending

## Need Help?

If you're stuck:
1. **Screenshot your Namecheap DNS records** (hide sensitive info)
2. **Screenshot Resend's required records**
3. Compare them side-by-side to find discrepancies

---

**Once verified, your app will be able to send OTP emails to any email address!** 🎉
