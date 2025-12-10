#!/usr/bin/env python3
"""
Database initialization script
Run this script to create all database tables if they don't exist.
Usage: python init_db.py
"""
from app import create_app, db
from models import User, Product, HomemadeIngredient, HomemadeIngredientItem, Recipe, RecipeIngredient
from utils.db_helpers import ensure_schema_updates

def init_database():
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
        
        print("\n✓ Database initialization complete!")
        print("You can now register a user account through the web interface.")
        return True

if __name__ == '__main__':
    init_database()
