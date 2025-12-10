import os

class Config:
    # Use environment variable for SECRET_KEY in production, fallback to default for development
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'supersecretkey'
    
    # Support both SQLite (development) and PostgreSQL (production) via DATABASE_URL
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///bar_bartender.db')
    # Handle PostgreSQL URL format for Render and other platforms
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = database_url
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload folder - use environment variable for production, or default to static/uploads
    upload_base = os.environ.get('UPLOAD_FOLDER') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    UPLOAD_FOLDER = upload_base
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
