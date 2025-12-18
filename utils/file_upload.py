"""
File upload utilities
"""
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def save_uploaded_file(file, folder):
    """Save uploaded file and return the relative path"""
    if file and allowed_file(file.filename):
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], folder)
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        
        # Return relative path from static folder
        return os.path.join('uploads', folder, filename)
    return None


def save_slide_image(file):
    """Save slide image to UPLOAD_FOLDER/slides/ and return the relative path for uploaded_file route"""
    if file and allowed_file(file.filename):
        # Use UPLOAD_FOLDER for persistent storage (works on deployment platforms)
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'slides')
        
        # Create directory if it doesn't exist
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        
        # Return relative path for uploaded_file route (e.g., 'uploads/slides/filename.jpg')
        return os.path.join('uploads', 'slides', filename)
    return None

