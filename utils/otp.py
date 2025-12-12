"""
OTP (One-Time Password) utility functions
"""
import random
import string
from datetime import datetime, timedelta
from flask import session, current_app
from flask_mail import Message
from extensions import mail

# OTP expiration time (10 minutes)
OTP_EXPIRY_MINUTES = 10


def generate_otp(length=6):
    """Generate a random numeric OTP"""
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])


def send_otp_email(email, otp):
    """
    Send OTP to user's email
    Returns True if sent successfully, False otherwise
    """
    try:
        # Check if email is configured
        if not current_app.config.get('MAIL_USERNAME') or not current_app.config.get('MAIL_PASSWORD'):
            current_app.logger.error("Email configuration missing: MAIL_USERNAME or MAIL_PASSWORD not set")
            return False
        
        subject = "Your Chef & Bartender Registration OTP"
        body = f"""
Hello,

Thank you for registering with Chef & Bartender!

Your OTP (One-Time Password) for email verification is:

    {otp}

This OTP is valid for {OTP_EXPIRY_MINUTES} minutes.

If you did not request this registration, please ignore this email.

Best regards,
Chef & Bartender Team
"""
        
        msg = Message(
            subject=subject,
            recipients=[email],
            body=body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME')
        )
        
        mail.send(msg)
        current_app.logger.info(f"OTP email sent successfully to {email}")
        return True
    except Exception as e:
        # Log the error properly
        error_msg = f"Error sending OTP email to {email}: {str(e)}"
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
