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


def _send_email_sync(app, email, otp, mail_config, sendgrid_api_key=None):
    """
    Send email synchronously (called from background thread)
    Uses SendGrid API if available, otherwise falls back to SMTP
    """
    with app.app_context():
        # Prefer SendGrid if API key is available (works on Railway)
        if sendgrid_api_key:
            from_email = mail_config.get('MAIL_DEFAULT_SENDER') or mail_config.get('MAIL_USERNAME') or 'noreply@chefandbartender.com'
            return _send_email_via_sendgrid(app, email, otp, from_email, sendgrid_api_key)
        else:
            return _send_email_via_smtp(app, email, otp, mail_config)


def send_otp_email(email, otp):
    """
    Send OTP to user's email asynchronously (non-blocking)
    Returns True immediately if configuration is valid, False otherwise
    The actual email is sent in a background thread
    Uses SendGrid API if available (recommended for Railway), otherwise SMTP
    """
    try:
        # Check for SendGrid API key first (preferred for Railway)
        sendgrid_api_key = current_app.config.get('SENDGRID_API_KEY')
        
        if sendgrid_api_key:
            # Use SendGrid API (works on Railway)
            app = current_app._get_current_object()
            from_email = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME') or 'noreply@chefandbartender.com'
            
            mail_config = {
                'MAIL_DEFAULT_SENDER': from_email,
                'MAIL_USERNAME': current_app.config.get('MAIL_USERNAME'),
            }
            
            # Send email in background thread (non-blocking)
            thread = threading.Thread(
                target=_send_email_sync,
                args=(app, email, otp, mail_config, sendgrid_api_key),
                daemon=True
            )
            thread.start()
            
            current_app.logger.info(f"OTP email sending started for {email} via SendGrid (async)")
            return True
        
        # Fallback to SMTP configuration
        mail_username = current_app.config.get('MAIL_USERNAME')
        mail_password = current_app.config.get('MAIL_PASSWORD')
        
        if not mail_username or not mail_password:
            current_app.logger.error(
                f"Email configuration missing: SENDGRID_API_KEY={bool(sendgrid_api_key)}, "
                f"MAIL_USERNAME={bool(mail_username)}, "
                f"MAIL_PASSWORD={bool(mail_password)}"
            )
            return False
        
        # Prepare mail config to pass to thread
        app = current_app._get_current_object()
        
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
            args=(app, email, otp, mail_config, None),
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
