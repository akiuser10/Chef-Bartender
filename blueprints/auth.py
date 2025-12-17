"""
Authentication blueprint - handles login, register, logout
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db, mail
from models import User
from utils.currency import COUNTRIES, CURRENCIES, get_country_currency
from flask_mail import Message
import re
import secrets
import hashlib

auth_bp = Blueprint('auth', __name__)

# Email validation regex pattern
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def validate_email(email):
    """
    Validate email format on the server side.
    Returns True if valid, False otherwise.
    """
    if not email or len(email) > 254:  # RFC 5321 limit
        return False
    return bool(EMAIL_REGEX.match(email))


def generate_verification_token():
    """Generate a secure random token for email verification"""
    return secrets.token_urlsafe(32)


def send_verification_email(user, token):
    """
    Send email verification link to user.
    Returns True if sent successfully, False otherwise.
    """
    try:
        verification_url = url_for('auth.verify_email', token=token, _external=True)
        
        msg = Message(
            subject='Verify Your Email - Chef & Bartender',
            recipients=[user.email],
            html=f'''
            <html>
            <body>
                <h2>Welcome to Chef & Bartender!</h2>
                <p>Thank you for registering. Please verify your email address by clicking the link below:</p>
                <p><a href="{verification_url}" style="background-color: #4a9d2f; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Verify Email Address</a></p>
                <p>Or copy and paste this link into your browser:</p>
                <p>{verification_url}</p>
                <p>If you did not create an account, please ignore this email.</p>
            </body>
            </html>
            ''',
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@chef-bartender.com')
        )
        
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f'Error sending verification email: {str(e)}', exc_info=True)
        return False


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        password_confirm = request.form.get('password_confirm', '').strip()
        organisation = request.form.get('organisation', '').strip()
        user_role = request.form.get('user_role', '').strip()
        
        # Validate required fields
        if not username or not email or not password or not password_confirm:
            flash('Please fill in all required fields.', 'error')
            return render_template('register.html')
        
        # Server-side email format validation (security: prevent malformed emails)
        if not validate_email(email):
            flash('Please enter a valid email address.', 'error')
            return render_template('register.html')
        
        # Validate password length (security: enforce minimum password strength)
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('register.html')
        
        # Validate password confirmation
        if password != password_confirm:
            flash('Passwords do not match. Please try again.', 'error')
            return render_template('register.html')
        
        # Validate username format (security: prevent injection and ensure valid format)
        if len(username) < 3 or len(username) > 80:
            flash('Username must be between 3 and 80 characters long.', 'error')
            return render_template('register.html')
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            flash('Username can only contain letters, numbers, underscores, and hyphens.', 'error')
            return render_template('register.html')
        
        # Check if email is already registered
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please log in.', 'error')
            return redirect(url_for('auth.login'))
        
        # Check if username is already taken
        if User.query.filter_by(username=username).first():
            flash('Username already taken. Please choose another.', 'error')
            return render_template('register.html')
        
        # Create the user with email verification token
        password_hash = generate_password_hash(password)
        verification_token = generate_verification_token()
        
        user = User(
            username=username,
            email=email,
            password=password_hash,
            organisation=organisation if organisation else None,
            user_role=user_role if user_role else None,
            email_verified=False,
            email_verification_token=verification_token
        )
        db.session.add(user)
        db.session.commit()
        
        # Send verification email (gracefully handle if email is not configured)
        email_sent = send_verification_email(user, verification_token)
        
        if email_sent:
            flash('Account created successfully! Please check your email to verify your account before logging in.', 'success')
        else:
            # If email sending fails, still allow registration but warn user
            current_app.logger.warning(f'Could not send verification email to {email}, but user was created')
            flash('Account created successfully! However, we could not send a verification email. Please contact support if you need to verify your email.', 'warning')
        
        return redirect(url_for('auth.login'))
    
    # GET request - show registration form
    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password, request.form['password']):
            # For existing users without email_verified field, set it to True (backward compatibility)
            # Handle case where column might not exist yet (will be added by schema update)
            try:
                if not hasattr(user, 'email_verified') or user.email_verified is None:
                    # Set default for existing users
                    if hasattr(user, 'email_verified'):
                        user.email_verified = True
                        db.session.commit()
            except Exception:
                # If column doesn't exist yet, schema update will handle it
                pass
            
            login_user(user)
            
            # Show verification reminder if email not verified (only if field exists)
            try:
                if hasattr(user, 'email_verified') and not user.email_verified:
                    flash('Welcome back! Please verify your email address to ensure account security.', 'warning')
                else:
                    flash('Welcome back!')
            except Exception:
                flash('Welcome back!')
            
            return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password.')
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        try:
            user = current_user
            
            # Update username if changed and not already taken
            new_username = request.form.get('username', '').strip()
            if new_username and new_username != user.username:
                existing_user = User.query.filter_by(username=new_username).first()
                if existing_user and existing_user.id != user.id:
                    flash('Username already taken. Please choose another.', 'error')
                    return redirect(url_for('auth.profile'))
                user.username = new_username
            
            # Update email if changed and not already taken
            new_email = request.form.get('email', '').strip()
            if new_email and new_email != user.email:
                # Server-side email format validation (security)
                if not validate_email(new_email):
                    flash('Please enter a valid email address.', 'error')
                    return redirect(url_for('auth.profile'))
                
                existing_user = User.query.filter_by(email=new_email).first()
                if existing_user and existing_user.id != user.id:
                    flash('Email already taken. Please choose another.', 'error')
                    return redirect(url_for('auth.profile'))
                user.email = new_email
            
            # Update first name, last name, and user role
            user.first_name = request.form.get('first_name', '').strip() or None
            user.last_name = request.form.get('last_name', '').strip() or None
            user.user_role = request.form.get('user_role', '').strip() or None
            # Normalize organization name (trim whitespace) for consistent matching
            org_value = request.form.get('organisation', '').strip()
            user.organisation = org_value if org_value else None
            user.restaurant_bar_name = request.form.get('restaurant_bar_name', '').strip() or None
            user.company_address = request.form.get('company_address', '').strip() or None
            user.contact_number = request.form.get('contact_number', '').strip() or None
            
            # Update country and currency
            country = request.form.get('country', '').strip() or None
            currency = request.form.get('currency', '').strip() or 'AED'
            
            # If country is selected but currency is not, set currency based on country
            if country and not currency:
                currency = get_country_currency(country)
            
            user.country = country
            user.currency = currency
            
            # Update password if provided
            new_password = request.form.get('password', '').strip()
            if new_password:
                user.password = generate_password_hash(new_password)
            
            db.session.commit()
            flash('Profile updated successfully! Your organization sharing will be updated immediately.', 'success')
            return redirect(url_for('main.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while updating your profile: {str(e)}', 'error')
            return redirect(url_for('auth.profile'))
    
    return render_template('profile.html', user=current_user, countries=COUNTRIES, currencies=CURRENCIES)


@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    """Verify user email using the verification token"""
    try:
        user = User.query.filter_by(email_verification_token=token).first()
        
        if not user:
            flash('Invalid or expired verification link.', 'error')
            return redirect(url_for('auth.login'))
        
        if user.email_verified:
            flash('Email already verified. You can log in.', 'info')
            return redirect(url_for('auth.login'))
        
        # Verify the email
        user.email_verified = True
        user.email_verification_token = None  # Clear token after verification
        db.session.commit()
        
        flash('Email verified successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error verifying email: {str(e)}', exc_info=True)
        flash('An error occurred while verifying your email. Please try again or contact support.', 'error')
        return redirect(url_for('auth.login'))


@auth_bp.route('/resend-verification', methods=['GET', 'POST'])
@login_required
def resend_verification():
    """Resend verification email to logged-in user"""
    if current_user.email_verified:
        flash('Your email is already verified.', 'info')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # Generate new token
        verification_token = generate_verification_token()
        current_user.email_verification_token = verification_token
        db.session.commit()
        
        # Send verification email
        email_sent = send_verification_email(current_user, verification_token)
        
        if email_sent:
            flash('Verification email sent! Please check your inbox.', 'success')
        else:
            flash('Could not send verification email. Please contact support.', 'error')
        
        return redirect(url_for('main.index'))
    
    return render_template('resend_verification.html')

