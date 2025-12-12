# Email Configuration for OTP Verification

This guide explains how to configure email settings for OTP (One-Time Password) verification during user registration.

## Railway Environment Variables

Set the following environment variables in your Railway project settings:

1. Go to your Railway project dashboard
2. Select your service
3. Go to the "Variables" tab
4. Add the following environment variables:

```
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USE_SSL=false
MAIL_USERNAME=akiuser10@gmail.com
MAIL_PASSWORD=<your-gmail-app-password>
MAIL_DEFAULT_SENDER=akiuser10@gmail.com
```

**Note:** Replace `<your-gmail-app-password>` with your actual Gmail App Password (remove spaces if present).

## Important Notes

⚠️ **Security**: Never commit email credentials to git. Always use environment variables.

⚠️ **Gmail App Password**: The `MAIL_PASSWORD` should be your Gmail App Password (with spaces removed or kept - Gmail accepts both formats). This is NOT your regular Gmail password.

## How to Generate Gmail App Password

1. Go to your Google Account settings
2. Navigate to Security
3. Enable 2-Step Verification if not already enabled
4. Under "Signing in to Google", select "App passwords"
5. Generate a new app password for "Mail"
6. Use that 16-character password (remove spaces or keep them - both work)

## Testing

After setting the environment variables in Railway:
1. Redeploy your application (or Railway will auto-deploy)
2. Try registering a new user
3. Check the email inbox for the OTP code
4. Enter the OTP to complete registration

## Troubleshooting

- **Email not sending**: Check that all environment variables are set correctly in Railway
- **Authentication failed**: Verify the App Password is correct (not your regular password)
- **Connection timeout**: Ensure `MAIL_PORT=587` and `MAIL_USE_TLS=true` are set correctly

## Alternative Email Providers

If you want to use a different email provider, update the environment variables:

### Outlook/Office365
```
MAIL_SERVER=smtp-mail.outlook.com
MAIL_PORT=587
MAIL_USE_TLS=true
```

### SendGrid
```
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USERNAME=apikey
MAIL_PASSWORD=<your-sendgrid-api-key>
```

### Mailgun
```
MAIL_SERVER=smtp.mailgun.org
MAIL_PORT=587
MAIL_USE_TLS=true
```
