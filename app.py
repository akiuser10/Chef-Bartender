"""
Bar & Bartender Flask Application Factory
Clean, modular application structure using blueprints
"""
from flask import Flask
from datetime import datetime
import os

# Import extensions
from extensions import db, login_manager, mail

# Import models (must import after extensions to avoid circular imports)
# Models import db from extensions
from models import User, Product, HomemadeIngredient, HomemadeIngredientItem, Recipe, RecipeIngredient, PurchaseRequest, PurchaseItem, Book, HeroSlide, ColdStorageUnit, TemperatureLog, TemperatureEntry, WashingUnit, BarGlassWasherChecklist, KitchenDishWasherChecklist, KitchenGlassWasherChecklist, BarClosingChecklistUnit, BarClosingChecklistPoint, BarClosingChecklistEntry, BarClosingChecklistItem, ChoppingBoardChecklistUnit, ChoppingBoardChecklistPoint, ChoppingBoardChecklistEntry, ChoppingBoardChecklistItem, KitchenChoppingBoardChecklistUnit, KitchenChoppingBoardChecklistPoint, KitchenChoppingBoardChecklistEntry, KitchenChoppingBoardChecklistItem, BarOpeningChecklistUnit, BarOpeningChecklistPoint, BarOpeningChecklistEntry, BarOpeningChecklistItem, BarShiftClosingChecklistUnit, BarShiftClosingChecklistPoint, BarShiftClosingChecklistEntry, BarShiftClosingChecklistItem

# Import blueprints
from blueprints.main import main_bp
from blueprints.auth import auth_bp
from blueprints.products import products_bp
from blueprints.secondary import secondary_bp
from blueprints.recipes import recipes_bp
from blueprints.purchase import purchase_bp
from blueprints.knowledge import knowledge_bp
from blueprints.checklist import checklist_bp

# Import utilities
from utils.helpers import inject_now
from utils.db_helpers import ensure_schema_updates
from utils.currency import format_currency, get_currency_info


def create_app(config_object='config.Config'):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config_object)
    
    # Register health check endpoint FIRST - before any blocking operations
    @app.route('/health')
    def health_check():
        """Health check endpoint for Railway - responds immediately"""
        return {'status': 'ok'}, 200
    
    # Initialize extensions (these should not block)
    db.init_app(app)
    login_manager.init_app(app)
    # Initialize mail - this should not block, just sets up configuration
    mail.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(secondary_bp)
    app.register_blueprint(recipes_bp)
    app.register_blueprint(purchase_bp)
    app.register_blueprint(knowledge_bp)
    app.register_blueprint(checklist_bp)
    
    # Register CLI commands
    @app.cli.command('link-ingredient')
    def link_ingredient():
        """Link a product/ingredient to a secondary ingredient"""
        import click
        from utils.link_ingredients import link_ingredient_to_secondary
        
        secondary_id = click.prompt('Secondary ingredient ID', type=int)
        product_id = click.prompt('Product ID', type=int)
        quantity = click.prompt('Quantity', type=float)
        unit = click.prompt('Unit', default='ml', type=str)
        
        if link_ingredient_to_secondary(secondary_id, product_id, quantity, unit):
            click.echo('✓ Successfully linked ingredient!')
        else:
            click.echo('✗ Failed to link ingredient')
    
    @app.cli.command('list-secondary')
    def list_secondary():
        """List all secondary ingredients"""
        from utils.link_ingredients import list_secondary_ingredients
        list_secondary_ingredients()
    
    @app.cli.command('show-secondary')
    def show_secondary():
        """Show details of a secondary ingredient"""
        import click
        from utils.link_ingredients import show_secondary_ingredient_details
        
        secondary_id = click.prompt('Secondary ingredient ID', type=int)
        show_secondary_ingredient_details(secondary_id)
    
    @app.cli.command('cleanup-temperature-logs')
    def cleanup_temperature_logs():
        """Clean up temperature logs older than 12 weeks"""
        import click
        from utils.db_helpers import cleanup_old_temperature_logs
        
        with app.app_context():
            deleted_count = cleanup_old_temperature_logs()
            if deleted_count > 0:
                click.echo(f'✓ Cleaned up {deleted_count} old temperature log(s)')
            else:
                click.echo('✓ No old temperature logs to clean up')
    
    # Template filter for currency formatting
    @app.template_filter('currency')
    def currency_filter(amount, decimals=2):
        """Format amount with user's selected currency"""
        from flask_login import current_user
        try:
            if current_user.is_authenticated:
                currency_code = current_user.currency or 'AED'
            else:
                currency_code = 'AED'  # Default
        except:
            currency_code = 'AED'
        return format_currency(float(amount), currency_code, decimals)
    
    # Template filter for user display name
    @app.template_filter('user_display')
    def user_display_filter(user):
        """Get display name for a user"""
        from utils.helpers import get_user_display_name
        return get_user_display_name(user)
    
    # Context processor
    @app.context_processor
    def inject_context():
        from flask_login import current_user
        from utils.helpers import get_user_display_name
        context = inject_now()
        # Add user currency info to all templates
        try:
            if current_user.is_authenticated:
                currency_code = current_user.currency or 'AED'
                context['user_currency'] = currency_code
                context['user_currency_info'] = get_currency_info(currency_code)
            else:
                context['user_currency'] = 'AED'
                context['user_currency_info'] = get_currency_info('AED')
        except:
            # Fallback if there's any issue
            context['user_currency'] = 'AED'
            context['user_currency_info'] = get_currency_info('AED')
        
        # Add helper function to templates
        context['get_user_display_name'] = get_user_display_name
        return context
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template
        return render_template('error.html', error='Page not found'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        db.session.rollback()
        app.logger.error(f'Internal Server Error: {str(error)}', exc_info=True)
        return render_template('error.html', error=str(error)), 500
    
    # Create upload directories at startup (fast, non-blocking)
    try:
        upload_folder = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        os.makedirs(os.path.join(upload_folder, 'products'), exist_ok=True)
        os.makedirs(os.path.join(upload_folder, 'recipes'), exist_ok=True)
        os.makedirs(os.path.join(upload_folder, 'slides'), exist_ok=True)
        os.makedirs(os.path.join(upload_folder, 'slides', 'default'), exist_ok=True)
        os.makedirs(os.path.join(upload_folder, 'books'), exist_ok=True)
        os.makedirs(os.path.join(upload_folder, 'books', 'covers'), exist_ok=True)
        os.makedirs(os.path.join(upload_folder, 'books', 'covers', 'default'), exist_ok=True)
        os.makedirs(os.path.join(upload_folder, 'books', 'pdfs'), exist_ok=True)
        app.logger.info("Upload directories created")
    except Exception as e:
        app.logger.warning(f"Could not create upload directories: {str(e)}")
    
    # Initialize database at startup (required for Railway and other production platforms)
    # This ensures tables are created before the app starts serving requests
    def initialize_database():
        """Initialize database tables and schema"""
        try:
            with app.app_context():
                app.logger.info("Starting database initialization...")
                
                # Check if DATABASE_URL is set (required for production)
                db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
                if not db_uri or db_uri == 'sqlite:///bar_bartender.db':
                    # Check if we're in production (Railway sets PORT or RAILWAY_ENVIRONMENT)
                    is_production = os.environ.get('PORT') or os.environ.get('RAILWAY_ENVIRONMENT')
                    if is_production:
                        app.logger.error("DATABASE_URL not set in production environment!")
                        app.logger.error("Please ensure PostgreSQL service is added and linked in Railway dashboard")
                        app.logger.error("Railway automatically provides DATABASE_URL when PostgreSQL service is linked")
                        raise Exception("DATABASE_URL environment variable is required in production")
                
                # Test database connection first
                try:
                    # Get database URL for logging (without password)
                    db_url = str(db.engine.url)
                    # Mask password in URL for logging
                    if '@' in db_url:
                        safe_url = db_url.split('@')[0].split('//')[0] + '//***@' + '@'.join(db_url.split('@')[1:])
                    else:
                        safe_url = db_url
                    app.logger.info(f"Connecting to database: {safe_url}")
                    
                    # Test connection with timeout
                    with db.engine.connect() as conn:
                        conn.execute(db.text("SELECT 1"))
                    app.logger.info("Database connection successful")
                except Exception as conn_error:
                    app.logger.error(f"Database connection failed: {str(conn_error)}")
                    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')
                    if db_uri and len(db_uri) > 100:
                        # Show first 50 and last 50 chars for long URLs
                        app.logger.error(f"Database URL: {db_uri[:50]}...{db_uri[-50:]}")
                    else:
                        app.logger.error(f"Database URL: {db_uri}")
                    raise  # Re-raise to prevent table creation attempts
                
                # Create all tables (this is the critical part)
                app.logger.info("Creating database tables...")
                db.create_all()
                app.logger.info("Database tables created successfully")
                
                # Run schema updates (this can be slow, but necessary)
                try:
                    app.logger.info("Running schema updates...")
                    ensure_schema_updates()
                    app.logger.info("Schema updates completed")
                except Exception as schema_error:
                    app.logger.warning(f"Schema updates skipped due to error: {str(schema_error)}")
                    # Continue anyway - tables are created
                
                app.logger.info("Database initialization completed successfully")
                return True
        except Exception as e:
            app.logger.error(f"Error initializing database: {str(e)}", exc_info=True)
            # Log additional diagnostic information
            app.logger.error(f"SQLALCHEMY_DATABASE_URI is set: {bool(app.config.get('SQLALCHEMY_DATABASE_URI'))}")
            if app.config.get('SQLALCHEMY_DATABASE_URI'):
                db_uri = app.config['SQLALCHEMY_DATABASE_URI']
                # Log first 100 chars (should show protocol and host)
                app.logger.error(f"Database URI prefix: {db_uri[:100]}...")
            return False
    
    # Initialize database during app startup
    # This ensures the database is ready before Railway marks the service as healthy
    app._db_initialized = False
    try:
        if initialize_database():
            app._db_initialized = True
    except Exception as e:
        # If initialization fails, log but don't crash - app can retry on first request
        app.logger.error(f"Failed to initialize database at startup: {str(e)}")
        app.logger.warning("App will attempt to initialize database on first request")
        app._db_initialized = False
    
    # Fallback: Initialize database on first request if startup initialization failed
    # This ensures the app works even if startup initialization had issues
    import threading
    _init_lock = threading.Lock()
    
    @app.before_request
    def ensure_database_initialized():
        """Fallback: Ensure database is initialized if startup initialization failed"""
        from flask import request
        # Skip health check - it should work without database
        if request.path == '/health':
            return
        
        if app._db_initialized:
            return
        
        # Use lock to ensure only one thread initializes
        with _init_lock:
            if app._db_initialized:
                return
            
            try:
                app.logger.info("Attempting database initialization on first request (fallback)...")
                if initialize_database():
                    app._db_initialized = True
                    app.logger.info("Database initialized successfully on first request")
            except Exception as e:
                app.logger.error(f"Failed to initialize database on first request: {str(e)}")
                # Don't mark as initialized if it failed
                app._db_initialized = False
    
    return app


# Create the app instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5001)

