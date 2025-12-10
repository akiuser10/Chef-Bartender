"""
Database helper utilities
"""
from extensions import db
from flask import current_app
import logging


def ensure_schema_updates():
    """
    Ensure database schema is up to date with migrations.
    """
    with current_app.app_context():
        with db.engine.begin() as conn:
            # Recipe table updates
            recipe_columns = [col[1] for col in conn.execute(db.text('PRAGMA table_info(recipe)'))]
            if 'item_level' not in recipe_columns:
                conn.execute(db.text("ALTER TABLE recipe ADD COLUMN item_level VARCHAR(20) DEFAULT 'Primary'"))
            if 'selling_price' not in recipe_columns:
                conn.execute(db.text("ALTER TABLE recipe ADD COLUMN selling_price FLOAT DEFAULT 0"))
            if 'vat_percentage' not in recipe_columns:
                conn.execute(db.text("ALTER TABLE recipe ADD COLUMN vat_percentage FLOAT DEFAULT 0"))
            if 'service_charge_percentage' not in recipe_columns:
                conn.execute(db.text("ALTER TABLE recipe ADD COLUMN service_charge_percentage FLOAT DEFAULT 0"))
            if 'government_fees_percentage' not in recipe_columns:
                conn.execute(db.text("ALTER TABLE recipe ADD COLUMN government_fees_percentage FLOAT DEFAULT 0"))
            if 'garnish' not in recipe_columns:
                conn.execute(db.text("ALTER TABLE recipe ADD COLUMN garnish TEXT"))
            if 'food_category' not in recipe_columns:
                conn.execute(db.text("ALTER TABLE recipe ADD COLUMN food_category VARCHAR(50)"))
            if 'beverage_category' not in recipe_columns:
                conn.execute(db.text("ALTER TABLE recipe ADD COLUMN beverage_category VARCHAR(50)"))

            # Product table updates
            product_columns = [col[1] for col in conn.execute(db.text('PRAGMA table_info(product)'))]
            if 'item_level' not in product_columns:
                conn.execute(db.text("ALTER TABLE product ADD COLUMN item_level VARCHAR(20) DEFAULT 'Primary'"))
            if 'organisation' not in product_columns:
                conn.execute(db.text("ALTER TABLE product ADD COLUMN organisation VARCHAR(200)"))
            if 'created_by' not in product_columns:
                conn.execute(db.text("ALTER TABLE product ADD COLUMN created_by INTEGER"))
            if 'last_edited_by' not in product_columns:
                conn.execute(db.text("ALTER TABLE product ADD COLUMN last_edited_by INTEGER"))
            if 'created_at' not in product_columns:
                conn.execute(db.text("ALTER TABLE product ADD COLUMN created_at DATETIME"))
            if 'last_edited_at' not in product_columns:
                conn.execute(db.text("ALTER TABLE product ADD COLUMN last_edited_at DATETIME"))

            # Recipe table updates
            recipe_columns = [col[1] for col in conn.execute(db.text('PRAGMA table_info(recipe)'))]
            if 'organisation' not in recipe_columns:
                conn.execute(db.text("ALTER TABLE recipe ADD COLUMN organisation VARCHAR(200)"))
            if 'last_edited_by' not in recipe_columns:
                conn.execute(db.text("ALTER TABLE recipe ADD COLUMN last_edited_by INTEGER"))
            if 'last_edited_at' not in recipe_columns:
                conn.execute(db.text("ALTER TABLE recipe ADD COLUMN last_edited_at DATETIME"))
            
            # Recipe ingredient table updates
            recipe_ingredient_columns = [col[1] for col in conn.execute(db.text('PRAGMA table_info(recipe_ingredient)'))]
            if 'ingredient_type' not in recipe_ingredient_columns:
                conn.execute(db.text("ALTER TABLE recipe_ingredient ADD COLUMN ingredient_type VARCHAR(20)"))
            if 'ingredient_id' not in recipe_ingredient_columns:
                conn.execute(db.text("ALTER TABLE recipe_ingredient ADD COLUMN ingredient_id INTEGER"))
            if 'quantity' not in recipe_ingredient_columns:
                conn.execute(db.text("ALTER TABLE recipe_ingredient ADD COLUMN quantity FLOAT"))
            if 'unit' not in recipe_ingredient_columns:
                conn.execute(db.text("ALTER TABLE recipe_ingredient ADD COLUMN unit VARCHAR(20) DEFAULT 'ml'"))
            if 'product_name' not in recipe_ingredient_columns:
                conn.execute(db.text("ALTER TABLE recipe_ingredient ADD COLUMN product_name VARCHAR(200)"))
            if 'product_code' not in recipe_ingredient_columns:
                conn.execute(db.text("ALTER TABLE recipe_ingredient ADD COLUMN product_code VARCHAR(50)"))
            if 'ingredient_name' not in recipe_ingredient_columns:
                conn.execute(db.text("ALTER TABLE recipe_ingredient ADD COLUMN ingredient_name VARCHAR(200)"))

            # Backfill new columns from legacy data where possible
            conn.execute(db.text("UPDATE recipe_ingredient SET ingredient_id = product_id WHERE ingredient_id IS NULL AND product_id IS NOT NULL"))
            conn.execute(db.text("UPDATE recipe_ingredient SET ingredient_type = COALESCE(ingredient_type, product_type)"))
            conn.execute(db.text("UPDATE recipe_ingredient SET quantity = COALESCE(quantity, quantity_ml)"))
            conn.execute(db.text("UPDATE recipe_ingredient SET unit = COALESCE(unit, 'ml')"))
            
            # Backfill product_name and product_code from existing products
            try:
                conn.execute(db.text("""
                    UPDATE recipe_ingredient 
                    SET product_name = (SELECT description FROM product WHERE product.id = recipe_ingredient.product_id),
                        product_code = (SELECT barbuddy_code FROM product WHERE product.id = recipe_ingredient.product_id)
                    WHERE product_id IS NOT NULL AND product_name IS NULL
                """))
            except Exception:
                pass  # May fail if tables don't exist or columns don't match

            # Homemade ingredient item table updates
            homemade_item_columns = [col[1] for col in conn.execute(db.text('PRAGMA table_info(homemade_ingredient_item)'))]
            if 'quantity' not in homemade_item_columns:
                conn.execute(db.text("ALTER TABLE homemade_ingredient_item ADD COLUMN quantity FLOAT DEFAULT 0"))
            if 'unit' not in homemade_item_columns:
                conn.execute(db.text("ALTER TABLE homemade_ingredient_item ADD COLUMN unit VARCHAR(20) DEFAULT 'ml'"))
            if 'product_name' not in homemade_item_columns:
                conn.execute(db.text("ALTER TABLE homemade_ingredient_item ADD COLUMN product_name VARCHAR(200)"))
            if 'product_code' not in homemade_item_columns:
                conn.execute(db.text("ALTER TABLE homemade_ingredient_item ADD COLUMN product_code VARCHAR(50)"))
            
            # Backfill quantity_ml if it's NULL (for existing records)
            try:
                conn.execute(db.text("UPDATE homemade_ingredient_item SET quantity_ml = COALESCE(quantity_ml, COALESCE(quantity, 0)) WHERE quantity_ml IS NULL"))
            except Exception:
                pass  # Column might not exist or already updated
            
            # Backfill product_name and product_code from existing products
            try:
                conn.execute(db.text("""
                    UPDATE homemade_ingredient_item 
                    SET product_name = (SELECT description FROM product WHERE product.id = homemade_ingredient_item.product_id),
                        product_code = (SELECT barbuddy_code FROM product WHERE product.id = homemade_ingredient_item.product_id)
                    WHERE product_id IS NOT NULL AND product_name IS NULL
                """))
            except Exception:
                pass  # May fail if tables don't exist or columns don't match

            # Homemade ingredient table updates
            homemade_columns = [col[1] for col in conn.execute(db.text('PRAGMA table_info(homemade_ingredient)'))]
            if 'category' not in homemade_columns:
                conn.execute(db.text("ALTER TABLE homemade_ingredient ADD COLUMN category VARCHAR(50)"))
            if 'sub_category' not in homemade_columns:
                conn.execute(db.text("ALTER TABLE homemade_ingredient ADD COLUMN sub_category VARCHAR(50)"))
            if 'organisation' not in homemade_columns:
                conn.execute(db.text("ALTER TABLE homemade_ingredient ADD COLUMN organisation VARCHAR(200)"))
            if 'last_edited_by' not in homemade_columns:
                conn.execute(db.text("ALTER TABLE homemade_ingredient ADD COLUMN last_edited_by INTEGER"))
            if 'last_edited_at' not in homemade_columns:
                conn.execute(db.text("ALTER TABLE homemade_ingredient ADD COLUMN last_edited_at DATETIME"))
            
            # Backfill organization for existing items based on creator's organization
            # This helps migrate existing data to the new organization system
            try:
                # Backfill products: set organization from creator's organization
                conn.execute(db.text("""
                    UPDATE product 
                    SET organisation = (SELECT organisation FROM user WHERE user.id = product.created_by)
                    WHERE organisation IS NULL AND created_by IS NOT NULL
                """))
                # Backfill recipes: set organization from creator's organization
                conn.execute(db.text("""
                    UPDATE recipe 
                    SET organisation = (SELECT organisation FROM user WHERE user.id = recipe.user_id)
                    WHERE organisation IS NULL AND user_id IS NOT NULL
                """))
                # Backfill secondary ingredients: set organization from creator's organization
                conn.execute(db.text("""
                    UPDATE homemade_ingredient 
                    SET organisation = (SELECT organisation FROM user WHERE user.id = homemade_ingredient.created_by)
                    WHERE organisation IS NULL AND created_by IS NOT NULL
                """))
            except Exception as e:
                current_app.logger.warning(f"Could not backfill organization data: {str(e)}")
                pass  # Continue even if backfill fails

            # User table updates
            user_columns = [col[1] for col in conn.execute(db.text('PRAGMA table_info(user)'))]
            if 'first_name' not in user_columns:
                conn.execute(db.text("ALTER TABLE user ADD COLUMN first_name VARCHAR(80)"))
            if 'last_name' not in user_columns:
                conn.execute(db.text("ALTER TABLE user ADD COLUMN last_name VARCHAR(80)"))
            if 'organisation' not in user_columns:
                conn.execute(db.text("ALTER TABLE user ADD COLUMN organisation VARCHAR(200)"))
            if 'restaurant_bar_name' not in user_columns:
                conn.execute(db.text("ALTER TABLE user ADD COLUMN restaurant_bar_name VARCHAR(200)"))
            if 'company_address' not in user_columns:
                conn.execute(db.text("ALTER TABLE user ADD COLUMN company_address TEXT"))
            if 'contact_number' not in user_columns:
                conn.execute(db.text("ALTER TABLE user ADD COLUMN contact_number VARCHAR(20)"))
            if 'country' not in user_columns:
                conn.execute(db.text("ALTER TABLE user ADD COLUMN country VARCHAR(10)"))
            if 'currency' not in user_columns:
                conn.execute(db.text("ALTER TABLE user ADD COLUMN currency VARCHAR(10) DEFAULT 'AED'"))

