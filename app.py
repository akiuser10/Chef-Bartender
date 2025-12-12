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
from models import User, Product, HomemadeIngredient, HomemadeIngredientItem, Recipe, RecipeIngredient

# Import blueprints
from blueprints.main import main_bp
from blueprints.auth import auth_bp
from blueprints.products import products_bp
from blueprints.secondary import secondary_bp
from blueprints.recipes import recipes_bp

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
    # Initialize mail lazily to avoid blocking
    try:
        mail.init_app(app)
    except Exception as e:
        app.logger.warning(f"Mail initialization warning: {str(e)}")
    
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
    
    # Initialize database lazily on first request to prevent blocking worker startup
    # This prevents timeout issues during deployment
    app._db_initialized = False
    import threading
    _init_lock = threading.Lock()
    
    @app.before_request
    def initialize_database():
        """Initialize database lazily on first request"""
        # Skip health check endpoint
        from flask import request
        if request.path == '/health':
            return
        
        if app._db_initialized:
            return
        
        # Use lock to ensure only one thread initializes
        with _init_lock:
            if app._db_initialized:
                return
            
            try:
                # Create upload directories
                upload_folder = app.config['UPLOAD_FOLDER']
                os.makedirs(upload_folder, exist_ok=True)
                os.makedirs(os.path.join(upload_folder, 'products'), exist_ok=True)
                os.makedirs(os.path.join(upload_folder, 'recipes'), exist_ok=True)
                
                # Create all tables first (this will create tables with all model columns)
                db.create_all()
                app.logger.info("Database tables created successfully")
                
                # Run schema updates (adds any missing columns for migrations)
                ensure_schema_updates()
                app.logger.info("Database schema updates completed")
                
                app._db_initialized = True
            except Exception as e:
                app.logger.error(f"Error initializing database: {str(e)}", exc_info=True)
                app._db_initialized = True  # Mark as attempted to prevent repeated failures
                # Continue anyway - the app might still work if tables exist
    
    return app


# Create the app instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5001)

