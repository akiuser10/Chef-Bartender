"""
Authentication blueprint - handles login, register, logout
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from models import User
from utils.currency import COUNTRIES, CURRENCIES, get_country_currency
from utils.otp import (
    generate_otp, send_otp_email, store_otp_in_session,
    verify_otp_from_session, clear_otp_session, get_pending_registration_data
)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Check if this is OTP verification step
        if 'verify_otp' in request.form:
            email = session.get('otp_email')
            user_otp = request.form.get('otp', '').strip()
            
            if not email or not user_otp:
                flash('Please enter the OTP sent to your email.', 'error')
                return render_template('register.html', step='verify_otp', email=email)
            
            if verify_otp_from_session(email, user_otp):
                # OTP verified, create the account
                pending_data = get_pending_registration_data()
                username = pending_data.get('username')
                email = pending_data.get('email')
                password_hash = pending_data.get('password_hash')
                
                if not username or not email or not password_hash:
                    flash('Session expired. Please register again.', 'error')
                    clear_otp_session()
                    return redirect(url_for('auth.register'))
                
                # Double-check email is not already registered
                if User.query.filter_by(email=email).first():
                    flash('Email already registered. Please log in.', 'error')
                    clear_otp_session()
                    return redirect(url_for('auth.login'))
                
                # Create the user
                user = User(username=username, email=email, password=password_hash)
                db.session.add(user)
                db.session.commit()
                
                # Clear OTP session
                clear_otp_session()
                
                flash('Account created successfully! Please log in.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('Invalid or expired OTP. Please check your email and try again.', 'error')
                return render_template('register.html', step='verify_otp', email=email)
        
        # Initial registration step - collect email, username, password and send OTP
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not email or not password:
            flash('Please fill in all fields.', 'error')
            return render_template('register.html')
        
        # Check if email is already registered
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please log in.', 'error')
            return redirect(url_for('auth.login'))
        
        # Check if username is already taken
        if User.query.filter_by(username=username).first():
            flash('Username already taken. Please choose another.', 'error')
            return render_template('register.html')
        
        # Generate and send OTP
        otp = generate_otp()
        password_hash = generate_password_hash(password)
        
        # Store OTP and registration data in session
        store_otp_in_session(email, otp, username, password_hash)
        
        # Send OTP email
        try:
            if send_otp_email(email, otp):
                flash(f'OTP has been sent to {email}. Please check your email and enter the 6-digit code.', 'info')
                return render_template('register.html', step='verify_otp', email=email)
            else:
                # Get more detailed error info for debugging
                from flask import current_app
                error_details = (
                    f"Email config check failed. Check Railway logs for details. "
                    f"Variables set: MAIL_USERNAME={bool(current_app.config.get('MAIL_USERNAME'))}, "
                    f"MAIL_PASSWORD={bool(current_app.config.get('MAIL_PASSWORD'))}"
                )
                current_app.logger.error(error_details)
                flash('Failed to send OTP email. Please check your email configuration in Railway and try again later.', 'error')
                clear_otp_session()
                return render_template('register.html')
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f'Error in registration OTP sending: {str(e)}', exc_info=True)
            flash(f'An error occurred while sending OTP. Please try again later. Error: {str(e)}', 'error')
            clear_otp_session()
            return render_template('register.html')
    
    # GET request - show registration form
    # Clear any existing OTP session if user navigates back
    if 'otp_email' not in request.args.get('step', ''):
        clear_otp_session()
    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
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

