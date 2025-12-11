"""
Role-based permission utilities
"""
from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user

# Roles that can create and edit recipes and secondary ingredients
EDITOR_ROLES = ['Chef', 'Chef Manager', 'Bartender', 'Operation Manager']

# Roles that can only view recipes (read-only)
VIEWER_ROLES = ['Cost Controller']

# Roles that only have access to Master List
MASTER_LIST_ONLY_ROLES = ['Purchase Manager']


def has_role(user, role):
    """Check if user has a specific role"""
    if not user or not user.is_authenticated:
        return False
    return user.user_role == role


def has_any_role(user, roles):
    """Check if user has any of the specified roles"""
    if not user or not user.is_authenticated:
        return False
    return user.user_role in roles


def can_edit_recipes(user):
    """Check if user can create/edit recipes"""
    return has_any_role(user, EDITOR_ROLES)


def can_view_recipes(user):
    """Check if user can view recipes (read-only or edit)"""
    return has_any_role(user, EDITOR_ROLES + VIEWER_ROLES)


def can_access_recipes(user):
    """Check if user can access recipes section at all"""
    return can_view_recipes(user)


def can_access_secondary_ingredients(user):
    """Check if user can access secondary ingredients section"""
    return has_any_role(user, EDITOR_ROLES)


def can_access_master_list(user):
    """Check if user can access master list"""
    # All authenticated users can access master list
    return user and user.is_authenticated


def can_edit_secondary_ingredients(user):
    """Check if user can create/edit secondary ingredients"""
    return has_any_role(user, EDITOR_ROLES)


def role_required(allowed_roles):
    """Decorator to require specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('auth.login'))
            
            if current_user.user_role not in allowed_roles:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('main.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def editor_required(f):
    """Decorator to require editor role (can create/edit recipes and secondary ingredients)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        
        if not can_edit_recipes(current_user):
            flash('You do not have permission to create or edit recipes.', 'error')
            return redirect(url_for('main.index'))
        
        return f(*args, **kwargs)
    return decorated_function


def recipe_viewer_required(f):
    """Decorator to require recipe viewer role (can view recipes)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        
        if not can_access_recipes(current_user):
            flash('You do not have permission to access recipes.', 'error')
            return redirect(url_for('main.index'))
        
        return f(*args, **kwargs)
    return decorated_function
