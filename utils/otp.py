"""
OTP (One-Time Password) utility functions
"""
import random
import string
from datetime import datetime, timedelta
from flask import session, current_app
from extensions import mail
from flask_mail import Message  # type: ignore
import threading
import smtplib

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
    Priority: Resend > SendGrid > SMTP
    Falls back to next method if previous one fails
    """
    with app.app_context():
        from_email = mail_config.get('MAIL_DEFAULT_SENDER') or mail_config.get('MAIL_USERNAME') or 'noreply@chefandbartender.com'
        
        # Try Resend first (easiest, no phone verification)
        if resend_api_key:
            if _send_email_via_resend(app, email, otp, from_email, resend_api_key):
                return True
            app.logger.warning(f"Resend failed for {email}, falling back to alternative method")
        
        # Fallback to SendGrid if Resend failed or not available
        if sendgrid_api_key:
            if _send_email_via_sendgrid(app, email, otp, from_email, sendgrid_api_key):
                return True
            app.logger.warning(f"SendGrid failed for {email}, falling back to SMTP")
        
        # Last resort: SMTP (may not work on Railway)
        return _send_email_via_smtp(app, email, otp, mail_config)


def send_otp_email(email, otp):
    """
    Send OTP to user's email asynchronously (non-blocking)
    Returns True immediately if configuration is valid, False otherwise
    The actual email is sent in a background thread
    Priority: Resend API > SendGrid API > SMTP
    """
    try:
        app = current_app._get_current_object()
        from_email = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME') or 'noreply@chefandbartender.com'
        
        # Check for Resend API key first (easiest, no phone verification)
        resend_api_key = current_app.config.get('RESEND_API_KEY')
        sendgrid_api_key = current_app.config.get('SENDGRID_API_KEY')
        
        # Prepare mail config with all SMTP settings for fallback
        mail_config = {
            'MAIL_DEFAULT_SENDER': from_email,
            'MAIL_USERNAME': current_app.config.get('MAIL_USERNAME'),
            'MAIL_SERVER': current_app.config.get('MAIL_SERVER'),
            'MAIL_PORT': current_app.config.get('MAIL_PORT'),
            'MAIL_USE_TLS': current_app.config.get('MAIL_USE_TLS'),
            'MAIL_PASSWORD': current_app.config.get('MAIL_PASSWORD'),
        }
        
        if resend_api_key or sendgrid_api_key:
            # Use API-based email service (works on Railway) with SMTP fallback
            # Send email in background thread (non-blocking)
            thread = threading.Thread(
                target=_send_email_sync,
                args=(app, email, otp, mail_config, resend_api_key, sendgrid_api_key),
                daemon=True
            )
            thread.start()
            
            provider = 'Resend' if resend_api_key else 'SendGrid'
            current_app.logger.info(f"OTP email sending started for {email} via {provider} (with fallback) (async)")
            return True
        
        # Fallback to SMTP configuration (may not work on Railway)
        mail_username = current_app.config.get('MAIL_USERNAME')
        mail_password = current_app.config.get('MAIL_PASSWORD')
        
        if not mail_username or not mail_password:
            current_app.logger.error(
                f"Email configuration missing: RESEND_API_KEY={bool(resend_api_key)}, "
                f"SENDGRID_API_KEY={bool(sendgrid_api_key)}, "
                f"MAIL_USERNAME={bool(mail_username)}, "
                f"MAIL_PASSWORD={bool(mail_password)}"
            )
            return False
        
        # Prepare mail config to pass to thread
        mail_config = {
            'MAIL_DEFAULT_SENDER': current_app.config.get('MAIL_DEFAULT_SENDER'),
            'MAIL_USERNAME': mail_username,
            'MAIL_SERVER': current_app.config.get('MAIL_SERVER'),
            'MAIL_PORT': current_app.config.get('MAIL_PORT'),
            'MAIL_USE_TLS': current_app.config.get('MAIL_USE_TLS'),
        }
        
        # Send email in background thread (non-blocking)
        thread = threading.Thread(
            target=_send_email_sync,
            args=(app, email, otp, mail_config, None, None),
            daemon=True
        )
        thread.start()
        
        current_app.logger.info(f"OTP email sending started for {email} via SMTP (async)")
        return True
    except Exception as e:
        error_msg = f"Error initiating OTP email send to {email}: {str(e)}"
        try:
            current_app.logger.error(error_msg, exc_info=True)
        except:
            print(error_msg)
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
