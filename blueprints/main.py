"""
Main blueprint - handles index, errors, and file uploads
"""
from flask import Blueprint, render_template, send_from_directory, current_app

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Homepage with recent recipes"""
    from models import Recipe
    from utils.helpers import get_organization_filter
    from sqlalchemy.orm import joinedload
    
    # Fetch 8 most recently created recipes
    org_filter = get_organization_filter(Recipe)
    recent_recipes = Recipe.query.filter(org_filter).options(
        joinedload(Recipe.ingredients)
    ).order_by(Recipe.created_at.desc()).limit(8).all()
    
    return render_template('index.html', recent_recipes=recent_recipes)


@main_bp.route('/about')
def about():
    return render_template('about.html')


@main_bp.route('/contact')
def contact():
    return render_template('contact.html')


@main_bp.route('/user-guide')
def user_guide():
    """Display the user guide from USER_GUIDE.md"""
    import os
    import markdown
    from markupsafe import Markup
    
    try:
        # Get the path to USER_GUIDE.md
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        guide_path = os.path.join(base_dir, 'USER_GUIDE.md')
        
        # Read the markdown file
        with open(guide_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # Convert markdown to HTML
        html_content = markdown.markdown(markdown_content, extensions=['extra', 'codehilite'])
        
        return render_template('user_guide.html', guide_content=Markup(html_content))
    except Exception as e:
        current_app.logger.error(f'Error loading user guide: {str(e)}', exc_info=True)
        return render_template('error.html', error='Unable to load user guide'), 500


@main_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    import os
    from flask import abort
    
    # Remove 'uploads/' prefix if present (for consistency)
    if filename.startswith('uploads/'):
        filename = filename.replace('uploads/', '', 1)
    
    # Construct full path
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    
    # Check if file exists
    if not os.path.exists(file_path):
        current_app.logger.warning(f'File not found: {file_path}, requested filename: {filename}')
        abort(404)
    
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


@main_bp.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error='Page not found'), 404


@main_bp.errorhandler(500)
def internal_error(error):
    from extensions import db
    db.session.rollback()
    current_app.logger.error(f'Internal Server Error: {str(error)}', exc_info=True)
    return render_template('error.html', error=str(error)), 500

