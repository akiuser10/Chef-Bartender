"""
Authentication blueprint - handles login, register, logout
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from models import User
from utils.currency import COUNTRIES, CURRENCIES, get_country_currency

auth_bp = Blueprint('auth', __name__)


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
        
        # Validate password confirmation
        if password != password_confirm:
            flash('Passwords do not match. Please try again.', 'error')
            return render_template('register.html')
        
        # Check if email is already registered
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please log in.', 'error')
            return redirect(url_for('auth.login'))
        
        # Check if username is already taken
        if User.query.filter_by(username=username).first():
            flash('Username already taken. Please choose another.', 'error')
            return render_template('register.html')
        
        # Create the user
        password_hash = generate_password_hash(password)
        user = User(
            username=username,
            email=email,
            password=password_hash,
            organisation=organisation if organisation else None,
            user_role=user_role if user_role else None
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    # GET request - show registration form
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

