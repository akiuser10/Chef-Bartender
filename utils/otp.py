"""
OTP (One-Time Password) utility functions
"""
import random
import string
from datetime import datetime, timedelta
from flask import session, current_app
from flask_mail import Message
from extensions import mail
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
        import resend
        
        resend.api_key = api_key
        
        params = {
            "from": from_email,
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
        
        app.logger.info(f"OTP email sent successfully to {email} via Resend (id: {email_response.get('id', 'unknown')})")
        return True
    except Exception as e:
        app.logger.error(f"Error sending email via Resend to {email}: {str(e)}", exc_info=True)
        return False


def _send_email_via_sendgrid(app, email, otp, from_email, api_key):
    """Send email using SendGrid API (HTTP-based, works on Railway)"""
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
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
        from flask_mail import Message
        from extensions import mail
        
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
    """
    with app.app_context():
        from_email = mail_config.get('MAIL_DEFAULT_SENDER') or mail_config.get('MAIL_USERNAME') or 'noreply@chefandbartender.com'
        
        # Prefer Resend (easiest, no phone verification)
        if resend_api_key:
            return _send_email_via_resend(app, email, otp, from_email, resend_api_key)
        # Fallback to SendGrid if Resend not available
        elif sendgrid_api_key:
            return _send_email_via_sendgrid(app, email, otp, from_email, sendgrid_api_key)
        # Last resort: SMTP (may not work on Railway)
        else:
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
        
        if resend_api_key or sendgrid_api_key:
            # Use API-based email service (works on Railway)
            mail_config = {
                'MAIL_DEFAULT_SENDER': from_email,
                'MAIL_USERNAME': current_app.config.get('MAIL_USERNAME'),
            }
            
            # Send email in background thread (non-blocking)
            thread = threading.Thread(
                target=_send_email_sync,
                args=(app, email, otp, mail_config, resend_api_key, sendgrid_api_key),
                daemon=True
            )
            thread.start()
            
            provider = 'Resend' if resend_api_key else 'SendGrid'
            current_app.logger.info(f"OTP email sending started for {email} via {provider} (async)")
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
