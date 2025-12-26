#!/usr/bin/env python3
"""
Database initialization script
Run this script to create all database tables if they don't exist.
Usage: python init_db.py
"""
from app import create_app, db
from models import User, Product, HomemadeIngredient, HomemadeIngredientItem, Recipe, RecipeIngredient
from utils.db_helpers import ensure_schema_updates
from werkzeug.security import generate_password_hash
import sys

def init_database(create_admin=False, admin_email=None, admin_password=None):
    """Initialize the database with all tables"""
    app = create_app()
    
    with app.app_context():
        print("Creating database tables...")
        try:
            db.create_all()
            print("✓ Tables created successfully")
        except Exception as e:
            print(f"✗ Error creating tables: {str(e)}")
            return False
        
        print("Running schema updates...")
        try:
            ensure_schema_updates()
            print("✓ Schema updates completed")
        except Exception as e:
            print(f"✗ Error running schema updates: {str(e)}")
            return False
        
        # Create admin user if requested
        if create_admin:
            if not admin_email or not admin_password:
                print("✗ Admin email and password required to create admin user")
                return False
            
            # Check if admin user already exists
            existing_user = User.query.filter_by(email=admin_email).first()
            if existing_user:
                print(f"✗ User with email {admin_email} already exists")
                return False
            
            admin_user = User(
                username='admin',
                email=admin_email,
                password=generate_password_hash(admin_password),
                user_role='Manager',
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print(f"✓ Admin user created: {admin_email}")
        
        print("\n✓ Database initialization complete!")
        if not create_admin:
            print("You can now register a user account through the web interface.")
        return True

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--create-admin':
        if len(sys.argv) < 4:
            print("Usage: python init_db.py --create-admin <email> <password>")
            sys.exit(1)
        init_database(create_admin=True, admin_email=sys.argv[2], admin_password=sys.argv[3])
    else:
        init_database()
