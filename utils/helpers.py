"""
Helper utility functions
"""
from datetime import datetime
from flask import current_app
from flask_login import current_user
from sqlalchemy import or_


def inject_now():
    """Context processor to inject current year"""
    return {'current_year': datetime.now().year}


def get_organization_filter(model_class):
    """
    Get organization filter for a model class.
    Returns a filter that matches items from the same organization as current user.
    Organization matching is case-insensitive and trimmed for consistency.
    Also includes items with NULL organization (legacy data) for backward compatibility.
    If user has no organization, returns items with no organization (personal items).
    Allows all authenticated users to create items regardless of organization.
    """
    if not current_user.is_authenticated:
        return model_class.organisation.is_(None)
    
    user_org = current_user.organisation
    if user_org and user_org.strip():
        # Normalize organization name (trimmed)
        user_org_normalized = user_org.strip()
        # Use case-insensitive comparison for organization matching
        # Also include NULL organization items (legacy data) for backward compatibility
        from sqlalchemy import func, or_
        # Compare organizations (case-insensitive) or NULL (legacy data)
        return or_(
            func.upper(model_class.organisation) == func.upper(user_org_normalized),
            model_class.organisation.is_(None)  # Include legacy data without organization
        )
    else:
        # If user has no organization, show items with no organization OR items created by them
        # For Recipe model, use user_id instead of created_by
        if hasattr(model_class, 'user_id'):
            return or_(
                model_class.organisation.is_(None),
                model_class.user_id == current_user.id
            )
        else:
            return or_(
                model_class.organisation.is_(None),
                model_class.created_by == current_user.id
            )


def ensure_user_can_create():
    """
    Ensure the current user can create items.
    All authenticated users can create items - this is just a validation helper.
    """
    if not current_user.is_authenticated:
        from flask import abort
        abort(401)  # Unauthorized
    return True


def get_user_display_name(user):
    """Get display name for a user"""
    if not user:
        return "Unknown"
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    elif user.first_name:
        return user.first_name
    else:
        return user.username

