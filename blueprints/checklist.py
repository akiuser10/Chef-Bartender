"""
Checklist Blueprint
Handles Bar Checklist and Kitchen Checklist pages
"""
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from functools import wraps

checklist_bp = Blueprint('checklist', __name__, url_prefix='/checklist')


def role_required(roles):
    """Decorator to check if user has required role"""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.user_role not in roles:
                from flask import abort
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@checklist_bp.route('/bar')
@login_required
@role_required(['Manager', 'Bartender'])
def bar_checklist():
    """Bar Checklist page - accessible to Manager and Bartender"""
    return render_template('checklist/bar_checklist.html')


@checklist_bp.route('/kitchen')
@login_required
@role_required(['Chef', 'Manager'])
def kitchen_checklist():
    """Kitchen Checklist page - accessible to Chef and Manager"""
    return render_template('checklist/kitchen_checklist.html')

