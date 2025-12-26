"""
OTP (One-Time Password) utility functions
Note: Email sending functionality has been disabled
"""
import random
import string
from datetime import datetime, timedelta
from flask import session, current_app

# OTP expiration time (10 minutes)
OTP_EXPIRY_MINUTES = 10


def generate_otp(length=6):
    """Generate a random numeric OTP"""
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])


def _send_email_via_resend(app, email, otp, from_email, api_key):
    """Send email using Resend API (HTTP-based, works on Railway, no phone verification)"""
    try:
        import resend  # type: ignore
        
        resend.api_key = api_key
        
        # Resend requires domain verification for custom domains (e.g., gmail.com)
        # Use onboarding@resend.dev for testing (no verification needed)
        # Format: "From Name <email@domain.com>"
        
        # If using a custom domain that might not be verified, suggest using test domain
        if from_email and '@gmail.com' in from_email.lower():
            # Gmail domain requires verification - use test domain instead
            from_address = "Chef & Bartender <onboarding@resend.dev>"
            app.logger.warning(
                f"Using Resend test domain because {from_email} requires domain verification. "
                f"For production, verify your domain at https://resend.com/domains or use onboarding@resend.dev"
            )
        elif '<' not in from_email and '@' in from_email:
            from_address = f"Chef & Bartender <{from_email}>"
        else:
            from_address = from_email
        
        params = {
            "from": from_address,
            "to": [email],
            "subject": "Your Chef & Bartender Registration OTP",
            "text": f"""
Hello,

Thank you for registering with Chef & Bartender!

Your OTP (One-Time Password) for email verification is:

    {otp}

This OTP is valid for {OTP_EXPIRY_MINUTES} minutes.

If you did not request this registration, please ignore this email.

Best regards,
Chef & Bartender Team
"""
        }
        
        email_response = resend.Emails.send(params)
        
        # Log detailed response
        app.logger.info(f"Resend API response: {email_response}")
        
        # Check if response has 'id' (success) or 'error' (failure)
        if 'id' in email_response:
            app.logger.info(f"OTP email sent successfully to {email} via Resend (id: {email_response.get('id')})")
            return True
        elif 'error' in email_response:
            error_msg = email_response.get('error', 'Unknown error')
            app.logger.error(f"Resend API error: {error_msg}")
            return False
        else:
            # Assume success if we got a response without error
            app.logger.info(f"OTP email sent to {email} via Resend (response: {email_response})")
            return True
    except Exception as e:
        error_detail = str(e)
        
        # Check for specific Resend test domain limitation error
        if "only send testing emails to your own email address" in error_detail.lower():
            app.logger.error(
                f"Resend test domain limitation: Cannot send to {email} using test domain. "
                f"Resend test domain (onboarding@resend.dev) can only send to your account email. "
                f"To send to any email address, please verify a domain at https://resend.com/domains"
            )
        else:
            app.logger.error(f"Error sending email via Resend to {email}: {error_detail}", exc_info=True)
        
        # Log more details about the exception
        if hasattr(e, 'response'):
            app.logger.error(f"Resend API response: {e.response}")
        return False


def _send_email_via_sendgrid(app, email, otp, from_email, api_key):
    """Send email using SendGrid API (HTTP-based, works on Railway)"""
    try:
        from sendgrid import SendGridAPIClient  # type: ignore
        from sendgrid.helpers.mail import Mail  # type: ignore
        
        message = Mail(
            from_email=from_email,
            to_emails=email,
            subject="Your Chef & Bartender Registration OTP",
            plain_text_content=f"""
Hello,

Thank you for registering with Chef & Bartender!

Your OTP (One-Time Password) for email verification is:

    {otp}

This OTP is valid for {OTP_EXPIRY_MINUTES} minutes.

If you did not request this registration, please ignore this email.

Best regards,
Chef & Bartender Team
"""
        )
        
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        
        if response.status_code in [200, 202]:
            app.logger.info(f"OTP email sent successfully to {email} via SendGrid (status: {response.status_code})")
            return True
        else:
            app.logger.error(f"SendGrid returned status {response.status_code}: {response.body}")
            return False
    except Exception as e:
        app.logger.error(f"Error sending email via SendGrid to {email}: {str(e)}", exc_info=True)
        return False


def _send_email_via_smtp(app, email, otp, mail_config):
    """
    Send email via SMTP (for development or when SendGrid is not available)
    """
    try:
        msg = Message(
            subject="Your Chef & Bartender Registration OTP",
            recipients=[email],
            body=f"""
Hello,

Thank you for registering with Chef & Bartender!

Your OTP (One-Time Password) for email verification is:

    {otp}

This OTP is valid for {OTP_EXPIRY_MINUTES} minutes.

If you did not request this registration, please ignore this email.

Best regards,
Chef & Bartender Team
""",
            sender=mail_config.get('MAIL_DEFAULT_SENDER') or mail_config.get('MAIL_USERNAME')
        )
        
        # Set timeout for SMTP operations
        import socket
        socket.setdefaulttimeout(10)  # 10 second timeout
        
        mail.send(msg)
        app.logger.info(f"OTP email sent successfully to {email} via SMTP")
        return True
    except Exception as e:
        error_msg = (
            f"Error sending OTP email to {email}: {str(e)}\n"
            f"MAIL_SERVER: {mail_config.get('MAIL_SERVER')}\n"
            f"MAIL_PORT: {mail_config.get('MAIL_PORT')}\n"
            f"MAIL_USE_TLS: {mail_config.get('MAIL_USE_TLS')}\n"
            f"MAIL_USERNAME: {mail_config.get('MAIL_USERNAME', 'NOT SET')}"
        )
        try:
            app.logger.error(error_msg, exc_info=True)
        except:
            print(error_msg)
        return False


def _send_email_sync(app, email, otp, mail_config, resend_api_key=None, sendgrid_api_key=None):
    """
    Send email synchronously (called from background thread)
    Priority: Resend > SMTP
    Falls back to SMTP if Resend fails
    """
    with app.app_context():
        from_email = mail_config.get('MAIL_DEFAULT_SENDER') or mail_config.get('MAIL_USERNAME') or 'noreply@chefandbartender.com'
        
        # Try Resend first (primary email service)
        if resend_api_key:
            result = _send_email_via_resend(app, email, otp, from_email, resend_api_key)
            if result:
                return True
            app.logger.warning(f"Resend failed for {email}, falling back to SMTP")
        
        # Fallback to SMTP if Resend failed or not available
        # Check if SMTP is configured
        if mail_config.get('MAIL_SERVER') and mail_config.get('MAIL_PASSWORD'):
            return _send_email_via_smtp(app, email, otp, mail_config)
        else:
            app.logger.error(
                f"Email sending failed: Resend unavailable and SMTP not configured. "
                f"Please verify your domain in Resend at https://resend.com/domains "
                f"or configure SMTP settings."
            )
            return False


def send_otp_email(email, otp):
    """
    Email sending is disabled.
    Returns False to indicate email was not sent.
    """
    try:
        current_app.logger.warning(f"Email sending is disabled. OTP {otp} was requested for {email} but not sent.")
    except:
        pass
    return False


def store_otp_in_session(email, otp, username=None, password_hash=None):
    """Store OTP and registration data in session"""
    session['otp_email'] = email
    session['otp_code'] = otp
    session['otp_timestamp'] = datetime.now().isoformat()
    if username:
        session['pending_username'] = username
    if password_hash:
        session['pending_password'] = password_hash


def verify_otp_from_session(email, user_otp):
    """
    Verify OTP from session
    Returns True if valid, False otherwise
    """
    stored_email = session.get('otp_email')
    stored_otp = session.get('otp_code')
    stored_timestamp = session.get('otp_timestamp')
    
    # Check if email matches
    if not stored_email or stored_email != email:
        return False
    
    # Check if OTP matches
    if not stored_otp or stored_otp != user_otp:
        return False
    
    # Check if OTP has expired
    if stored_timestamp:
        try:
            otp_time = datetime.fromisoformat(stored_timestamp)
            expiry_time = otp_time + timedelta(minutes=OTP_EXPIRY_MINUTES)
            if datetime.now() > expiry_time:
                return False
        except (ValueError, TypeError):
            return False
    
    return True


def clear_otp_session():
    """Clear OTP data from session"""
    session.pop('otp_email', None)
    session.pop('otp_code', None)
    session.pop('otp_timestamp', None)
    session.pop('pending_username', None)
    session.pop('pending_password', None)


def get_pending_registration_data():
    """Get pending registration data from session"""
    return {
        'username': session.get('pending_username'),
        'email': session.get('otp_email'),
        'password_hash': session.get('pending_password')
    }
