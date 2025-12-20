"""
Database helper utilities
"""
from extensions import db
from flask import current_app
import logging


def get_table_columns(conn, table_name):
    """
    Get column names for a table, works with both SQLite and PostgreSQL.
    Returns empty list if table doesn't exist.
    """
    try:
        # Detect database type
        db_url = str(db.engine.url)
        is_postgres = 'postgresql' in db_url.lower() or 'postgres' in db_url.lower()
        
        if is_postgres:
            # PostgreSQL query
            result = conn.execute(db.text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = :table_name
            """), {'table_name': table_name})
            return [row[0] for row in result]
        else:
            # SQLite query
            result = conn.execute(db.text(f'PRAGMA table_info({table_name})'))
            return [row[1] for row in result]
    except Exception as e:
        current_app.logger.warning(f"Could not get columns for table {table_name}: {str(e)}")
        return []


def table_exists(conn, table_name):
    """
    Check if a table exists, works with both SQLite and PostgreSQL.
    """
    try:
        db_url = str(db.engine.url)
        is_postgres = 'postgresql' in db_url.lower() or 'postgres' in db_url.lower()
        
        if is_postgres:
            # PostgreSQL query
            result = conn.execute(db.text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = :table_name
                )
            """), {'table_name': table_name})
            return result.scalar()
        else:
            # SQLite query
            result = conn.execute(db.text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"))
            return result.fetchone() is not None
    except Exception:
        return False


def ensure_schema_updates():
    """
    Ensure database schema is up to date with migrations.
    Works with both SQLite and PostgreSQL.
    """
    try:
        with current_app.app_context():
            # First, ensure all tables are created
            db.create_all()
            
            with db.engine.begin() as conn:
                # Recipe table updates
                if table_exists(conn, 'recipe'):
                    recipe_columns = get_table_columns(conn, 'recipe')
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
                    if 'glassware' not in recipe_columns:
                        conn.execute(db.text("ALTER TABLE recipe ADD COLUMN glassware VARCHAR(200)"))
                    if 'plates' not in recipe_columns:
                        conn.execute(db.text("ALTER TABLE recipe ADD COLUMN plates VARCHAR(200)"))
                    if 'food_category' not in recipe_columns:
                        conn.execute(db.text("ALTER TABLE recipe ADD COLUMN food_category VARCHAR(50)"))
                    if 'beverage_category' not in recipe_columns:
                        conn.execute(db.text("ALTER TABLE recipe ADD COLUMN beverage_category VARCHAR(50)"))
                    if 'organisation' not in recipe_columns:
                        conn.execute(db.text("ALTER TABLE recipe ADD COLUMN organisation VARCHAR(200)"))
                    if 'last_edited_by' not in recipe_columns:
                        conn.execute(db.text("ALTER TABLE recipe ADD COLUMN last_edited_by INTEGER"))
                    if 'last_edited_at' not in recipe_columns:
                        conn.execute(db.text("ALTER TABLE recipe ADD COLUMN last_edited_at DATETIME"))

                # Product table updates
                if table_exists(conn, 'product'):
                    product_columns = get_table_columns(conn, 'product')
                    if 'item_level' not in product_columns:
                        conn.execute(db.text("ALTER TABLE product ADD COLUMN item_level VARCHAR(20) DEFAULT 'Primary'"))
                    if 'organisation' not in product_columns:
                        conn.execute(db.text("ALTER TABLE product ADD COLUMN organisation VARCHAR(200)"))
                    if 'created_by' not in product_columns:
                        conn.execute(db.text("ALTER TABLE product ADD COLUMN created_by INTEGER"))
                    if 'last_edited_by' not in product_columns:
                        conn.execute(db.text("ALTER TABLE product ADD COLUMN last_edited_by INTEGER"))
                    if 'created_at' not in product_columns:
                        conn.execute(db.text("ALTER TABLE product ADD COLUMN created_at TIMESTAMP"))
                    if 'last_edited_at' not in product_columns:
                        conn.execute(db.text("ALTER TABLE product ADD COLUMN last_edited_at TIMESTAMP"))
            
                # Recipe ingredient table updates
                if table_exists(conn, 'recipe_ingredient'):
                    recipe_ingredient_columns = get_table_columns(conn, 'recipe_ingredient')
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
                    try:
                        conn.execute(db.text("UPDATE recipe_ingredient SET ingredient_id = product_id WHERE ingredient_id IS NULL AND product_id IS NOT NULL"))
                        conn.execute(db.text("UPDATE recipe_ingredient SET ingredient_type = COALESCE(ingredient_type, product_type)"))
                        conn.execute(db.text("UPDATE recipe_ingredient SET quantity = COALESCE(quantity, quantity_ml)"))
                        conn.execute(db.text("UPDATE recipe_ingredient SET unit = COALESCE(unit, 'ml')"))
                    except Exception:
                        pass  # May fail if columns don't exist
                    
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
                if table_exists(conn, 'homemade_ingredient_item'):
                    homemade_item_columns = get_table_columns(conn, 'homemade_ingredient_item')
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
                if table_exists(conn, 'homemade_ingredient'):
                    homemade_columns = get_table_columns(conn, 'homemade_ingredient')
                    if 'category' not in homemade_columns:
                        conn.execute(db.text("ALTER TABLE homemade_ingredient ADD COLUMN category VARCHAR(50)"))
                    if 'sub_category' not in homemade_columns:
                        conn.execute(db.text("ALTER TABLE homemade_ingredient ADD COLUMN sub_category VARCHAR(50)"))
                    if 'organisation' not in homemade_columns:
                        conn.execute(db.text("ALTER TABLE homemade_ingredient ADD COLUMN organisation VARCHAR(200)"))
                    if 'created_by' not in homemade_columns:
                        conn.execute(db.text("ALTER TABLE homemade_ingredient ADD COLUMN created_by INTEGER"))
                    if 'last_edited_by' not in homemade_columns:
                        conn.execute(db.text("ALTER TABLE homemade_ingredient ADD COLUMN last_edited_by INTEGER"))
                    if 'created_at' not in homemade_columns:
                        conn.execute(db.text("ALTER TABLE homemade_ingredient ADD COLUMN created_at TIMESTAMP"))
                    if 'last_edited_at' not in homemade_columns:
                        conn.execute(db.text("ALTER TABLE homemade_ingredient ADD COLUMN last_edited_at TIMESTAMP"))
                    
                    # Backfill organization for existing items based on creator's organization
                    try:
                        conn.execute(db.text("""
                            UPDATE homemade_ingredient 
                            SET organisation = (SELECT organisation FROM "user" WHERE "user".id = homemade_ingredient.created_by)
                            WHERE organisation IS NULL AND created_by IS NOT NULL
                        """))
                    except Exception:
                        pass  # May fail if tables don't exist

                # User table updates
                if table_exists(conn, 'user'):
                    user_columns = get_table_columns(conn, 'user')
                    if 'first_name' not in user_columns:
                        conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN first_name VARCHAR(80)"))
                    if 'last_name' not in user_columns:
                        conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN last_name VARCHAR(80)"))
                    if 'user_role' not in user_columns:
                        conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN user_role VARCHAR(50)"))
                    if 'organisation' not in user_columns:
                        conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN organisation VARCHAR(200)"))
                    if 'restaurant_bar_name' not in user_columns:
                        conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN restaurant_bar_name VARCHAR(200)"))
                    if 'company_address' not in user_columns:
                        conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN company_address TEXT"))
                    if 'contact_number' not in user_columns:
                        conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN contact_number VARCHAR(20)"))
                    if 'country' not in user_columns:
                        conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN country VARCHAR(10)"))
                    if 'currency' not in user_columns:
                        conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN currency VARCHAR(10) DEFAULT 'AED'"))
                
                # Purchase item table updates
                if table_exists(conn, 'purchase_item'):
                    purchase_item_columns = get_table_columns(conn, 'purchase_item')
                    if 'quantity_received' not in purchase_item_columns:
                        # Add quantity_received column (nullable FLOAT)
                        conn.execute(db.text("ALTER TABLE purchase_item ADD COLUMN quantity_received FLOAT"))
                
                # Purchase request table updates
                if table_exists(conn, 'purchase_request'):
                    purchase_request_columns = get_table_columns(conn, 'purchase_request')
                    # Update status column size if it exists and is too small
                    try:
                        # Check current column type and alter if needed
                        db_url = str(db.engine.url)
                        is_postgres = 'postgresql' in db_url.lower() or 'postgres' in db_url.lower()
                        if is_postgres:
                            # For PostgreSQL, check and alter the column type
                            result = conn.execute(db.text("""
                                SELECT character_maximum_length 
                                FROM information_schema.columns 
                                WHERE table_name = 'purchase_request' AND column_name = 'status'
                            """))
                            max_length = result.scalar()
                            if max_length and max_length < 50:
                                conn.execute(db.text("ALTER TABLE purchase_request ALTER COLUMN status TYPE VARCHAR(50)"))
                        else:
                            # For SQLite, we can't easily check, but we can try to alter
                            # SQLite doesn't support ALTER COLUMN, so we'll need to recreate
                            # For now, just ensure the model is correct
                            pass
                    except Exception as e:
                        current_app.logger.warning(f"Could not update status column size: {str(e)}")
                    
                    if 'invoice_number' not in purchase_request_columns:
                        conn.execute(db.text("ALTER TABLE purchase_request ADD COLUMN invoice_number VARCHAR(100)"))
                    if 'invoice_value' not in purchase_request_columns:
                        conn.execute(db.text("ALTER TABLE purchase_request ADD COLUMN invoice_value FLOAT"))
                    if 'supplier_invoices' not in purchase_request_columns:
                        conn.execute(db.text("ALTER TABLE purchase_request ADD COLUMN supplier_invoices TEXT"))
                    if 'supplier_status' not in purchase_request_columns:
                        conn.execute(db.text("ALTER TABLE purchase_request ADD COLUMN supplier_status TEXT"))
                    if 'supplier_received_dates' not in purchase_request_columns:
                        conn.execute(db.text("ALTER TABLE purchase_request ADD COLUMN supplier_received_dates TEXT"))
                
                # Backfill organization for existing items based on creator's organization
                # This helps migrate existing data to the new organization system
                try:
                    # Backfill products: set organization from creator's organization
                    if table_exists(conn, 'product') and table_exists(conn, 'user'):
                        conn.execute(db.text("""
                            UPDATE product 
                            SET organisation = (SELECT organisation FROM "user" WHERE "user".id = product.created_by)
                            WHERE organisation IS NULL AND created_by IS NOT NULL
                        """))
                    # Backfill recipes: set organization from creator's organization
                    if table_exists(conn, 'recipe') and table_exists(conn, 'user'):
                        conn.execute(db.text("""
                            UPDATE recipe 
                            SET organisation = (SELECT organisation FROM "user" WHERE "user".id = recipe.user_id)
                            WHERE organisation IS NULL AND user_id IS NOT NULL
                        """))
                except Exception as e:
                    current_app.logger.warning(f"Could not backfill organization data: {str(e)}")
                    pass  # Continue even if backfill fails
                
                # Book table updates
                if table_exists(conn, 'book'):
                    book_columns = get_table_columns(conn, 'book')
                    if 'article_url' not in book_columns:
                        conn.execute(db.text("ALTER TABLE book ADD COLUMN article_url VARCHAR(500)"))
                    # Make pdf_path nullable if it's not already
                    # Note: SQLite doesn't support ALTER COLUMN, so this is mainly for PostgreSQL
                    try:
                        db_url = str(db.engine.url)
                        is_postgres = 'postgresql' in db_url.lower() or 'postgres' in db_url.lower()
                        if is_postgres and 'pdf_path' in book_columns:
                            # Check if pdf_path is currently NOT NULL
                            result = conn.execute(db.text("""
                                SELECT is_nullable 
                                FROM information_schema.columns 
                                WHERE table_name = 'book' AND column_name = 'pdf_path'
                            """))
                            is_nullable = result.scalar()
                            if is_nullable == 'NO':
                                conn.execute(db.text("ALTER TABLE book ALTER COLUMN pdf_path DROP NOT NULL"))
                    except Exception as e:
                        current_app.logger.warning(f"Could not update pdf_path column: {str(e)}")
                
                # Cold Storage Unit table updates
                if table_exists(conn, 'cold_storage_unit'):
                    cold_storage_columns = get_table_columns(conn, 'cold_storage_unit')
                    if 'location' not in cold_storage_columns:
                        # Add location column - for existing records, set a default value
                        try:
                            db_url = str(db.engine.url)
                            is_postgres = 'postgresql' in db_url.lower() or 'postgres' in db_url.lower()
                            
                            if is_postgres:
                                # For PostgreSQL: Add column with default, update existing rows, then set NOT NULL
                                conn.execute(db.text("ALTER TABLE cold_storage_unit ADD COLUMN location VARCHAR(200) DEFAULT 'Unknown'"))
                                conn.execute(db.text("UPDATE cold_storage_unit SET location = 'Unknown' WHERE location IS NULL"))
                                # Now make it NOT NULL
                                conn.execute(db.text("ALTER TABLE cold_storage_unit ALTER COLUMN location SET NOT NULL"))
                            else:
                                # For SQLite: Add column with default (SQLite doesn't support NOT NULL on ALTER)
                                conn.execute(db.text("ALTER TABLE cold_storage_unit ADD COLUMN location VARCHAR(200) DEFAULT 'Unknown'"))
                                conn.execute(db.text("UPDATE cold_storage_unit SET location = 'Unknown' WHERE location IS NULL"))
                        except Exception as e:
                            current_app.logger.warning(f"Could not add location column to cold_storage_unit: {str(e)}")
                    if 'min_temp' not in cold_storage_columns:
                        conn.execute(db.text("ALTER TABLE cold_storage_unit ADD COLUMN min_temp FLOAT"))
                    if 'max_temp' not in cold_storage_columns:
                        conn.execute(db.text("ALTER TABLE cold_storage_unit ADD COLUMN max_temp FLOAT"))
                    if 'organisation' not in cold_storage_columns:
                        conn.execute(db.text("ALTER TABLE cold_storage_unit ADD COLUMN organisation VARCHAR(200)"))
                    if 'created_by' not in cold_storage_columns:
                        conn.execute(db.text("ALTER TABLE cold_storage_unit ADD COLUMN created_by INTEGER"))
                    if 'created_at' not in cold_storage_columns:
                        conn.execute(db.text("ALTER TABLE cold_storage_unit ADD COLUMN created_at TIMESTAMP"))
                    if 'is_active' not in cold_storage_columns:
                        conn.execute(db.text("ALTER TABLE cold_storage_unit ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
                
                # Temperature Log table updates
                if table_exists(conn, 'temperature_log'):
                    temp_log_columns = get_table_columns(conn, 'temperature_log')
                    # Handle week_start_date column
                    if 'week_start_date' not in temp_log_columns:
                        try:
                            db_url = str(db.engine.url)
                            is_postgres = 'postgresql' in db_url.lower() or 'postgres' in db_url.lower()
                            
                            if is_postgres:
                                # For PostgreSQL: Add column, calculate week_start_date for existing rows, then set NOT NULL
                                conn.execute(db.text("ALTER TABLE temperature_log ADD COLUMN week_start_date DATE"))
                                # Calculate week_start_date for existing rows (Monday of the week)
                                # date_trunc('week', date) gives Monday of the week in PostgreSQL
                                conn.execute(db.text("""
                                    UPDATE temperature_log 
                                    SET week_start_date = DATE(date_trunc('week', log_date))
                                    WHERE week_start_date IS NULL
                                """))
                                # Set NOT NULL constraint
                                conn.execute(db.text("ALTER TABLE temperature_log ALTER COLUMN week_start_date SET NOT NULL"))
                            else:
                                # For SQLite: Add column with default (SQLite doesn't support NOT NULL on ALTER easily)
                                conn.execute(db.text("ALTER TABLE temperature_log ADD COLUMN week_start_date DATE"))
                                # Calculate week_start_date for existing rows (Monday of the week)
                                # strftime('%w', date) returns 0-6 where 0=Sunday, 1=Monday, etc.
                                # To get to Monday: subtract (day_of_week - 1) days, handling Sunday specially
                                conn.execute(db.text("""
                                    UPDATE temperature_log 
                                    SET week_start_date = date(log_date, '-' || CASE 
                                        WHEN CAST(strftime('%%w', log_date) AS INTEGER) = 0 THEN '6'
                                        ELSE CAST(strftime('%%w', log_date) AS INTEGER) - 1
                                    END || ' days')
                                    WHERE week_start_date IS NULL
                                """))
                        except Exception as e:
                            current_app.logger.warning(f"Could not add week_start_date column to temperature_log: {str(e)}")
                    else:
                        # Column exists, but update any NULL values
                        try:
                            db_url = str(db.engine.url)
                            is_postgres = 'postgresql' in db_url.lower() or 'postgres' in db_url.lower()
                            
                            if is_postgres:
                                # Update NULL week_start_date values for existing rows
                                conn.execute(db.text("""
                                    UPDATE temperature_log 
                                    SET week_start_date = DATE(date_trunc('week', log_date))
                                    WHERE week_start_date IS NULL
                                """))
                            else:
                                # Update NULL week_start_date values for existing rows in SQLite
                                conn.execute(db.text("""
                                    UPDATE temperature_log 
                                    SET week_start_date = date(log_date, '-' || CASE 
                                        WHEN CAST(strftime('%%w', log_date) AS INTEGER) = 0 THEN '6'
                                        ELSE CAST(strftime('%%w', log_date) AS INTEGER) - 1
                                    END || ' days')
                                    WHERE week_start_date IS NULL
                                """))
                        except Exception as e:
                            current_app.logger.warning(f"Could not update week_start_date values in temperature_log: {str(e)}")
                    if 'supervisor_verified' not in temp_log_columns:
                        try:
                            db_url = str(db.engine.url)
                            is_postgres = 'postgresql' in db_url.lower() or 'postgres' in db_url.lower()
                            
                            if is_postgres:
                                conn.execute(db.text("ALTER TABLE temperature_log ADD COLUMN supervisor_verified BOOLEAN DEFAULT FALSE"))
                            else:
                                conn.execute(db.text("ALTER TABLE temperature_log ADD COLUMN supervisor_verified BOOLEAN DEFAULT 0"))
                        except Exception as e:
                            current_app.logger.warning(f"Could not add supervisor_verified column to temperature_log: {str(e)}")
                    if 'supervisor_name' not in temp_log_columns:
                        conn.execute(db.text("ALTER TABLE temperature_log ADD COLUMN supervisor_name VARCHAR(200)"))
                    if 'supervisor_verified_at' not in temp_log_columns:
                        conn.execute(db.text("ALTER TABLE temperature_log ADD COLUMN supervisor_verified_at TIMESTAMP"))
                    if 'organisation' not in temp_log_columns:
                        conn.execute(db.text("ALTER TABLE temperature_log ADD COLUMN organisation VARCHAR(200)"))
                    if 'created_at' not in temp_log_columns:
                        conn.execute(db.text("ALTER TABLE temperature_log ADD COLUMN created_at TIMESTAMP"))
                    if 'updated_at' not in temp_log_columns:
                        conn.execute(db.text("ALTER TABLE temperature_log ADD COLUMN updated_at TIMESTAMP"))
                    # Handle temperature column - add if missing, or update NULL values if it exists with NOT NULL constraint
                    if 'temperature' not in temp_log_columns:
                        try:
                            db_url = str(db.engine.url)
                            is_postgres = 'postgresql' in db_url.lower() or 'postgres' in db_url.lower()
                            
                            if is_postgres:
                                # For PostgreSQL: Add column as nullable first (temperature should be in entries, not log)
                                conn.execute(db.text("ALTER TABLE temperature_log ADD COLUMN temperature FLOAT"))
                            else:
                                # For SQLite: Add column as nullable
                                conn.execute(db.text("ALTER TABLE temperature_log ADD COLUMN temperature FLOAT"))
                        except Exception as e:
                            current_app.logger.warning(f"Could not add temperature column to temperature_log: {str(e)}")
                    else:
                        # Column exists - if it has NOT NULL constraint, we need to handle it
                        # Since temperature should be in entries, we'll set a default or make it nullable
                        try:
                            db_url = str(db.engine.url)
                            is_postgres = 'postgresql' in db_url.lower() or 'postgres' in db_url.lower()
                            
                            # Try to alter column to allow NULL if it's currently NOT NULL
                            # This is a workaround for databases that have this constraint incorrectly
                            try:
                                if is_postgres:
                                    # Check if column is NOT NULL and try to make it nullable
                                    # Note: This may fail if constraint exists, but we'll try
                                    conn.execute(db.text("""
                                        DO $$ 
                                        BEGIN
                                            IF EXISTS (
                                                SELECT 1 FROM information_schema.columns 
                                                WHERE table_name = 'temperature_log' 
                                                AND column_name = 'temperature' 
                                                AND is_nullable = 'NO'
                                            ) THEN
                                                ALTER TABLE temperature_log ALTER COLUMN temperature DROP NOT NULL;
                                            END IF;
                                        END $$;
                                    """))
                            except Exception as alter_error:
                                # If we can't alter, set default values for NULL rows
                                current_app.logger.warning(f"Could not alter temperature column: {str(alter_error)}")
                                # Set a default temperature for NULL values (0.0 as placeholder)
                                conn.execute(db.text("""
                                    UPDATE temperature_log 
                                    SET temperature = 0.0
                                    WHERE temperature IS NULL
                                """))
                        except Exception as e:
                            current_app.logger.warning(f"Could not update temperature column in temperature_log: {str(e)}")
                    # Handle time_slot column - add if missing, or update NULL values if it exists
                    if 'time_slot' not in temp_log_columns:
                        try:
                            db_url = str(db.engine.url)
                            is_postgres = 'postgresql' in db_url.lower() or 'postgres' in db_url.lower()
                            
                            if is_postgres:
                                # For PostgreSQL: Add column with default, update existing rows, then set NOT NULL if needed
                                conn.execute(db.text("ALTER TABLE temperature_log ADD COLUMN time_slot VARCHAR(10) DEFAULT '10:00 AM'"))
                                conn.execute(db.text("UPDATE temperature_log SET time_slot = '10:00 AM' WHERE time_slot IS NULL"))
                                # Note: We keep it nullable in the model for backward compatibility, but DB may have NOT NULL
                            else:
                                # For SQLite: Add column with default
                                conn.execute(db.text("ALTER TABLE temperature_log ADD COLUMN time_slot VARCHAR(10) DEFAULT '10:00 AM'"))
                                conn.execute(db.text("UPDATE temperature_log SET time_slot = '10:00 AM' WHERE time_slot IS NULL"))
                        except Exception as e:
                            current_app.logger.warning(f"Could not add time_slot column to temperature_log: {str(e)}")
                    else:
                        # Column exists - update any NULL values to ensure NOT NULL constraint is satisfied
                        try:
                            db_url = str(db.engine.url)
                            is_postgres = 'postgresql' in db_url.lower() or 'postgres' in db_url.lower()
                            
                            if is_postgres:
                                # For PostgreSQL: Set a default value for NULL time_slot values
                                # Use the first scheduled time as default
                                conn.execute(db.text("""
                                    UPDATE temperature_log 
                                    SET time_slot = '10:00 AM'
                                    WHERE time_slot IS NULL
                                """))
                            else:
                                # For SQLite: Set default for NULL values
                                conn.execute(db.text("""
                                    UPDATE temperature_log 
                                    SET time_slot = '10:00 AM'
                                    WHERE time_slot IS NULL
                                """))
                        except Exception as e:
                            current_app.logger.warning(f"Could not update time_slot values in temperature_log: {str(e)}")
                
                # Temperature Entry table updates
                if table_exists(conn, 'temperature_entry'):
                    temp_entry_columns = get_table_columns(conn, 'temperature_entry')
                    if 'action_time' not in temp_entry_columns:
                        conn.execute(db.text("ALTER TABLE temperature_entry ADD COLUMN action_time TIMESTAMP"))
                    if 'recheck_temperature' not in temp_entry_columns:
                        conn.execute(db.text("ALTER TABLE temperature_entry ADD COLUMN recheck_temperature FLOAT"))
                    if 'initial' not in temp_entry_columns:
                        try:
                            db_url = str(db.engine.url)
                            is_postgres = 'postgresql' in db_url.lower() or 'postgres' in db_url.lower()
                            
                            if is_postgres:
                                conn.execute(db.text("ALTER TABLE temperature_entry ADD COLUMN initial VARCHAR(10) DEFAULT ''"))
                                conn.execute(db.text("UPDATE temperature_entry SET initial = '' WHERE initial IS NULL"))
                                conn.execute(db.text("ALTER TABLE temperature_entry ALTER COLUMN initial SET NOT NULL"))
                            else:
                                conn.execute(db.text("ALTER TABLE temperature_entry ADD COLUMN initial VARCHAR(10) DEFAULT ''"))
                        except Exception as e:
                            current_app.logger.warning(f"Could not add initial column to temperature_entry: {str(e)}")
                    if 'is_late_entry' not in temp_entry_columns:
                        try:
                            db_url = str(db.engine.url)
                            is_postgres = 'postgresql' in db_url.lower() or 'postgres' in db_url.lower()
                            
                            if is_postgres:
                                conn.execute(db.text("ALTER TABLE temperature_entry ADD COLUMN is_late_entry BOOLEAN DEFAULT FALSE"))
                            else:
                                conn.execute(db.text("ALTER TABLE temperature_entry ADD COLUMN is_late_entry BOOLEAN DEFAULT 0"))
                        except Exception as e:
                            current_app.logger.warning(f"Could not add is_late_entry column to temperature_entry: {str(e)}")
                    if 'entry_timestamp' not in temp_entry_columns:
                        conn.execute(db.text("ALTER TABLE temperature_entry ADD COLUMN entry_timestamp TIMESTAMP"))
                    if 'created_by' not in temp_entry_columns:
                        conn.execute(db.text("ALTER TABLE temperature_entry ADD COLUMN created_by INTEGER"))
                    
    except Exception as e:
        current_app.logger.error(f"Error in ensure_schema_updates: {str(e)}", exc_info=True)
        # Don't raise - allow app to continue even if schema updates fail
        pass


def cleanup_old_temperature_logs():
    """
    Clean up temperature logs older than 12 weeks for audit purposes.
    Keeps only the last 12 weeks of data.
    """
    try:
        from models import TemperatureLog, TemperatureEntry
        from datetime import date, timedelta
        
        with current_app.app_context():
            # Calculate cutoff date (12 weeks ago)
            cutoff_date = date.today() - timedelta(weeks=12)
            
            # Find all logs older than 12 weeks
            old_logs = TemperatureLog.query.filter(
                TemperatureLog.log_date < cutoff_date
            ).all()
            
            if not old_logs:
                current_app.logger.info("No old temperature logs to clean up")
                return 0
            
            deleted_count = 0
            deleted_entries_count = 0
            
            for log in old_logs:
                # Count entries before deletion (for logging)
                entry_count = log.entries.count()
                deleted_entries_count += entry_count
                
                # Delete the log (entries will be cascade deleted)
                db.session.delete(log)
                deleted_count += 1
            
            # Commit the deletions
            db.session.commit()
            
            current_app.logger.info(
                f"Cleaned up {deleted_count} temperature log(s) and {deleted_entries_count} entry/entries "
                f"older than {cutoff_date} (12 weeks retention)"
            )
            
            return deleted_count
            
    except Exception as e:
        current_app.logger.error(f"Error cleaning up old temperature logs: {str(e)}", exc_info=True)
        db.session.rollback()
        # Don't raise - allow app to continue even if cleanup fails
        return 0
