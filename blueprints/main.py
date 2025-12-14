"""
Main blueprint - handles index, errors, and file uploads
"""
from flask import Blueprint, render_template, send_from_directory, current_app

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/about')
def about():
    return render_template('about.html')


@main_bp.route('/contact')
def contact():
    return render_template('contact.html')


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

