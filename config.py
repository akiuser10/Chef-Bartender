import os

class Config:
    # Use environment variable for SECRET_KEY in production, fallback to default for development
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'supersecretkey'
    
    # Support both SQLite (development) and PostgreSQL (production) via DATABASE_URL
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///bar_bartender.db')
    # Strip quotes if present (Railway might include them)
    if database_url:
        database_url = database_url.strip('"\'')
    # Handle PostgreSQL URL format for Render and other platforms
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = database_url
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload folder - use environment variable for production, or default to static/uploads
    upload_base = os.environ.get('UPLOAD_FOLDER') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    UPLOAD_FOLDER = upload_base
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size (for PDFs)
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}
    
    # Email configuration for OTP
    # Strip quotes from environment variables (Railway might include them)
    def _strip_quotes(value):
        """Strip quotes from environment variable values"""
        if value:
            return value.strip('"\'')
        return value
    
    MAIL_SERVER = _strip_quotes(os.environ.get('MAIL_SERVER', 'smtp.gmail.com'))
    # Try port 465 with SSL first (Railway may block port 587)
    mail_port_str = _strip_quotes(os.environ.get('MAIL_PORT', '465'))
    MAIL_PORT = int(mail_port_str) if mail_port_str else 465
    mail_use_tls_str = _strip_quotes(os.environ.get('MAIL_USE_TLS', 'false'))
    MAIL_USE_TLS = mail_use_tls_str.lower() in ['true', 'on', '1'] if mail_use_tls_str else False
    # Use SSL for port 465
    mail_use_ssl_str = _strip_quotes(os.environ.get('MAIL_USE_SSL', 'true'))
    MAIL_USE_SSL = mail_use_ssl_str.lower() in ['true', 'on', '1'] if mail_use_ssl_str else True
    MAIL_USERNAME = _strip_quotes(os.environ.get('MAIL_USERNAME'))
    MAIL_PASSWORD = _strip_quotes(os.environ.get('MAIL_PASSWORD'))
    mail_default_sender = _strip_quotes(os.environ.get('MAIL_DEFAULT_SENDER'))
    MAIL_DEFAULT_SENDER = mail_default_sender if mail_default_sender else MAIL_USERNAME
    
    # Additional Flask-Mail settings for better reliability
    MAIL_DEBUG = False
    MAIL_SUPPRESS_SEND = False
    # Set timeout for SMTP connections (in seconds)
    MAIL_TIMEOUT = 10
    
    # Email API configurations (preferred for Railway - bypasses SMTP blocking)
    # Resend API (simplest, no phone verification required)
    RESEND_API_KEY = _strip_quotes(os.environ.get('RESEND_API_KEY'))
    # SendGrid API (alternative option)
    SENDGRID_API_KEY = _strip_quotes(os.environ.get('SENDGRID_API_KEY'))
