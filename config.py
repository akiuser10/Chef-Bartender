import os

class Config:
    # Use environment variable for SECRET_KEY in production, fallback to default for development
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'supersecretkey'
    
    # Support both SQLite (development) and PostgreSQL (production) via DATABASE_URL
    # Railway provides DATABASE_URL when PostgreSQL service is linked
    # Try multiple environment variable names for compatibility
    database_url = (
        os.environ.get('DATABASE_URL') or 
        os.environ.get('POSTGRES_URL') or 
        os.environ.get('POSTGRESQL_URL') or
        'sqlite:///bar_bartender.db'  # Fallback to SQLite for local development
    )
    
    # Strip quotes if present (Railway might include them)
    if database_url:
        database_url = database_url.strip('"\'')
    
    # Handle PostgreSQL URL format for Render and other platforms
    # SQLAlchemy requires postgresql:// not postgres://
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = database_url
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload folder - use environment variable for production, or default to static/uploads
    # For Railway: Use persistent volume at /data/uploads (survives redeployments)
    # For local dev: Use static/uploads
    if os.environ.get('UPLOAD_FOLDER'):
        # Explicitly set via environment variable (highest priority)
        upload_base = os.environ.get('UPLOAD_FOLDER')
    elif os.path.exists('/data'):
        # Railway persistent volume detected - use /data/uploads
        upload_base = '/data/uploads'
    else:
        # Local development - use static/uploads
        upload_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    UPLOAD_FOLDER = upload_base
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size (for PDFs)
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}

