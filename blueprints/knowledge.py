"""
Knowledge Hub Blueprint
Handles Bartender Library and Chef Library pages
"""
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from functools import wraps

knowledge_bp = Blueprint('knowledge', __name__, url_prefix='/knowledge')


def role_required(*roles):
    """Decorator to require specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                from flask import redirect, url_for
                return redirect(url_for('auth.login'))
            if current_user.user_role not in roles:
                from flask import abort
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@knowledge_bp.route('/bartender-library')
@login_required
@role_required('Chef', 'Bartender', 'Manager')
def bartender_library():
    """Display Bartender Library page"""
    return render_template('knowledge/bartender_library.html')


@knowledge_bp.route('/chef-library')
@login_required
@role_required('Chef', 'Bartender', 'Manager')
def chef_library():
    """Display Chef Library page"""
    return render_template('knowledge/chef_library.html')

