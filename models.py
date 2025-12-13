from flask_login import UserMixin
from datetime import datetime
import json

# Import db from extensions (will be initialized in app factory)
from extensions import db

# -------------------------
# USER MODEL
# -------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    user_role = db.Column(db.String(50))
    organisation = db.Column(db.String(200))
    restaurant_bar_name = db.Column(db.String(200))
    company_address = db.Column(db.Text)
    contact_number = db.Column(db.String(20))
    country = db.Column(db.String(10))  # ISO country code (e.g., 'AE', 'US')
    currency = db.Column(db.String(10), default='AED')  # ISO currency code (e.g., 'AED', 'USD')

# -------------------------
# PRODUCT MODEL
# -------------------------
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unique_item_number = db.Column(db.String(50), unique=True)
    supplier = db.Column(db.String(120))
    barbuddy_code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))
    sub_category = db.Column(db.String(50))
    item_level = db.Column(db.String(20), default='Primary')
    ml_in_bottle = db.Column(db.Float)
    abv = db.Column(db.Float)
    selling_unit = db.Column(db.String(20), default="ml")
    cost_per_unit = db.Column(db.Float, nullable=False)
    supplier_product_code = db.Column(db.String(50))
    purchase_type = db.Column(db.String(10), default="each")
    bottles_per_case = db.Column(db.Integer, default=1)
    case_cost = db.Column(db.Float, default=0.0)
    image_path = db.Column(db.String(255))
    organisation = db.Column(db.String(200))  # Organization name for sharing
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_products')
    last_edited_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    last_editor = db.relationship('User', foreign_keys=[last_edited_by], backref='edited_products')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_edited_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def calculate_case_cost(self):
        if self.purchase_type == "case":
            return round(self.cost_per_unit * self.bottles_per_case, 2)
        return self.cost_per_unit

# -------------------------
# HOMEMADE INGREDIENTS (Secondary Ingredients)
# -------------------------
class HomemadeIngredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    unique_code = db.Column(db.String(50), unique=True)
    organisation = db.Column(db.String(200))  # Organization name for sharing
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_secondary_ingredients')
    last_edited_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    last_editor = db.relationship('User', foreign_keys=[last_edited_by], backref='edited_secondary_ingredients')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_edited_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    total_volume_ml = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), default="ml")
    method = db.Column(db.Text)
    category = db.Column(db.String(50))
    sub_category = db.Column(db.String(50))
    ingredients = db.relationship('HomemadeIngredientItem', backref='homemade', cascade='all, delete-orphan')

    def calculate_cost(self):
        return round(sum(i.calculate_cost() for i in self.ingredients), 2)
    
    def calculate_cost_per_unit(self):
        """Calculate cost per unit (ml, gram, etc.)"""
        if self.total_volume_ml > 0:
            return round(self.calculate_cost() / self.total_volume_ml, 4)
        return 0.0
    
    def has_missing_cost(self):
        """Check if any ingredient has missing cost (deleted product or zero cost)"""
        for item in self.ingredients:
            if not item.product and item.product_id:
                # Product was deleted
                return True
            if item.product and (not item.product.cost_per_unit or item.product.cost_per_unit == 0):
                # Product exists but has no cost
                return True
            # Check if cost calculation returns 0 when it shouldn't
            if item.quantity and item.quantity > 0:
                calculated_cost = item.calculate_cost()
                if calculated_cost == 0 and item.product:
                    # Product exists, has quantity, but cost is 0
                    if item.product.cost_per_unit and item.product.cost_per_unit > 0:
                        # This shouldn't happen, but check anyway
                        pass
                    else:
                        return True
        return False

class HomemadeIngredientItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    homemade_id = db.Column(db.Integer, db.ForeignKey('homemade_ingredient.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    quantity_ml = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Float, default=0)
    unit = db.Column(db.String(20), default="ml")
    product_name = db.Column(db.String(200))  # Store product name for deleted products
    product_code = db.Column(db.String(50))  # Store product code for matching
    product = db.relationship('Product')

    def calculate_cost(self):
        """Calculate cost based on product's unit and quantity"""
        prod = self.product
        qty = self.quantity

        # If product is deleted (product_id exists but product is None), return 0
        if not prod:
            # Try to restore link if product was re-added
            if self.product_id and self.product_code:
                restored_product = Product.query.filter_by(barbuddy_code=self.product_code).first()
                if restored_product:
                    self.product_id = restored_product.id
                    self.product = restored_product
                    prod = restored_product
                else:
                    return 0.0
            else:
                return 0.0

        # If cost_per_unit is None or 0, return 0
        if prod.cost_per_unit is None or prod.cost_per_unit == 0:
            return 0.0

        # Calculate cost per unit based on product's selling unit
        if prod.selling_unit == "ml":
            # For ml, cost_per_unit is already per ml
            cost_per_unit = prod.cost_per_unit
        elif prod.selling_unit == "grams":
            # For grams, cost_per_unit is per gram
            cost_per_unit = prod.cost_per_unit
        elif prod.selling_unit == "pieces":
            # For pieces, cost_per_unit is per piece
            cost_per_unit = prod.cost_per_unit
        else:
            # For other units or if ml_in_bottle is set, calculate per ml
            if prod.ml_in_bottle and prod.ml_in_bottle > 0:
                # cost_per_unit is typically the cost of the whole bottle
                # So cost per ml = cost_per_unit / ml_in_bottle
                cost_per_unit = prod.cost_per_unit / prod.ml_in_bottle
            else:
                # Fallback to cost_per_unit as-is
                cost_per_unit = prod.cost_per_unit

        # Calculate total cost: cost per unit * quantity
        total_cost = cost_per_unit * qty
        return round(total_cost, 2)

# -------------------------
# RECIPE MODEL
# -------------------------
class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_code = db.Column(db.String(50), unique=True)
    title = db.Column(db.String(150), nullable=False)
    method = db.Column(db.Text)
    recipe_type = db.Column(db.String(20))
    type = db.Column(db.String(20))
    item_level = db.Column(db.String(20), default='Primary')
    organisation = db.Column(db.String(200))  # Organization name for sharing
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    creator = db.relationship('User', foreign_keys=[user_id], backref='created_recipes')
    last_edited_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    last_editor = db.relationship('User', foreign_keys=[last_edited_by], backref='edited_recipes')
    last_edited_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ingredients = db.relationship('RecipeIngredient', backref='recipe', cascade='all, delete-orphan')
    image_path = db.Column(db.String(255))
    selling_price = db.Column(db.Float, default=0.0)
    vat_percentage = db.Column(db.Float, default=0.0)
    service_charge_percentage = db.Column(db.Float, default=0.0)
    government_fees_percentage = db.Column(db.Float, default=0.0)
    garnish = db.Column(db.Text)
    glassware = db.Column(db.String(200))
    plates = db.Column(db.String(200))
    food_category = db.Column(db.String(50))
    beverage_category = db.Column(db.String(50))

    def calculate_total_cost(self):
        """
        Calculate total cost including nested recipes.
        NOTE: This method calculates costs dynamically from current product prices.
        When product prices change in the Master List, recipe costs automatically update.
        """
        try:
            total = 0.0
            for i in self.ingredients:
                cost = i.calculate_cost()
                total += cost
            return round(total, 2)
        except Exception as e:
            import logging
            logging.error(f"Error calculating total cost for Recipe {self.id}: {str(e)}")
            return 0.0
    
    def has_missing_cost(self):
        """Check if any ingredient has missing cost (deleted product or zero cost)"""
        for ingredient in self.ingredients:
            product = ingredient.get_product()
            if not product:
                # Product/ingredient was deleted
                return True
            if isinstance(product, Product):
                if not product.cost_per_unit or product.cost_per_unit == 0:
                    return True
                # Check if cost calculation returns 0 when it shouldn't
                qty = ingredient.get_quantity()
                if qty and qty > 0:
                    calculated_cost = ingredient.calculate_cost()
                    if calculated_cost == 0:
                        return True
            elif isinstance(product, HomemadeIngredient):
                # Check if secondary ingredient has missing cost
                if product.has_missing_cost():
                    return True
            elif isinstance(product, Recipe):
                # Check if nested recipe has missing cost
                if product.has_missing_cost():
                    return True
        return False

    def cost_percentage(self):
        total_cost = self.calculate_total_cost()
        # Selling price is inclusive of VAT, Service Charge, and Government Fees
        # Calculate base selling price by deducting fees
        if self.selling_price and self.selling_price > 0:
            vat = self.vat_percentage or 0.0
            service_charge = self.service_charge_percentage or 0.0
            govt_fees = self.government_fees_percentage or 0.0
            total_fees_percentage = vat + service_charge + govt_fees
            
            # Calculate base selling price (before fees)
            # SP_inclusive = Base_SP × (1 + fees/100)
            # Base_SP = SP_inclusive / (1 + fees/100)
            if total_fees_percentage > 0:
                base_selling_price = self.selling_price / (1 + total_fees_percentage / 100)
            else:
                base_selling_price = self.selling_price
            
            return round((total_cost / base_selling_price) * 100, 2)
        return None
    
    def total_selling_price_with_fees(self):
        """Calculate total selling price including all fees"""
        if not self.selling_price or self.selling_price <= 0:
            return 0.0
        vat = self.vat_percentage or 0.0
        service_charge = self.service_charge_percentage or 0.0
        govt_fees = self.government_fees_percentage or 0.0
        total_fees_percentage = vat + service_charge + govt_fees
        return round(self.selling_price * (1 + total_fees_percentage / 100), 2)

    def selling_price_value(self):
        return round(self.selling_price or 0.0, 2)

    def batch_summary(self):
        try:
            summary = {"Alcohol":0,"Syrups & Purees":0,"Juices":0,"Fruits":0,"Vegetables":0,"Dairy":0,"Non-Alcohol":0,"Other":0}
            for i in self.ingredients:
                try:
                    prod = i.get_product()
                    if not prod:
                        continue
                        
                    category = "Other"
                    if isinstance(prod, Product):
                        sub_cat = prod.sub_category or ""
                        if sub_cat == "Alcohol":
                            category = "Alcohol"
                        elif sub_cat in ["Syrup", "Puree", "Syrups & Purees"]:
                            category = "Syrups & Purees"
                        elif sub_cat == "Juice":
                            category = "Juices"
                        elif sub_cat == "Fruits":
                            category = "Fruits"
                        elif sub_cat == "Vegetables":
                            category = "Vegetables"
                        elif sub_cat == "Dairy":
                            category = "Dairy"
                        elif sub_cat == "Non-Alcohol":
                            category = "Non-Alcohol"
                    elif isinstance(prod, HomemadeIngredient):
                        category = "Syrups & Purees"
                    elif isinstance(prod, Recipe):
                        category = "Other"
                    
                    qty = i.get_quantity()
                    if qty is None or qty <= 0:
                        continue
                    summary[category] += qty
                except Exception as e:
                    import logging
                    logging.error(f"Error processing ingredient in batch_summary: {str(e)}")
                    continue
            return summary
        except Exception as e:
            import logging
            logging.error(f"Error in batch_summary for Recipe {self.id}: {str(e)}")
            return {"Alcohol":0,"Syrups & Purees":0,"Juices":0,"Fruits":0,"Vegetables":0,"Dairy":0,"Non-Alcohol":0,"Other":0}

class RecipeIngredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    ingredient_type = db.Column(db.String(20))
    ingredient_id = db.Column(db.Integer)
    quantity = db.Column(db.Float)
    unit = db.Column(db.String(20), default="ml")
    quantity_ml = db.Column(db.Float)
    product_type = db.Column(db.String(20))
    product_id = db.Column(db.Integer)
    product_name = db.Column(db.String(200))  # Store product name for deleted products
    product_code = db.Column(db.String(50))  # Store product code for matching
    ingredient_name = db.Column(db.String(200))  # Store ingredient name (for secondary/recipe ingredients)

    def get_product(self):
        """Get the ingredient (Product, HomemadeIngredient, or Recipe)"""
        result = None
        if self.ingredient_type:
            if self.ingredient_type == "Product":
                result = Product.query.get(self.ingredient_id)
                # Try to restore link if product was re-added
                if not result and self.ingredient_id and self.product_code:
                    restored = Product.query.filter_by(barbuddy_code=self.product_code).first()
                    if restored:
                        self.ingredient_id = restored.id
                        result = restored
            elif self.ingredient_type == "Homemade":
                result = HomemadeIngredient.query.get(self.ingredient_id)
            elif self.ingredient_type == "Recipe":
                result = Recipe.query.get(self.ingredient_id)
        elif self.product_type:
            if self.product_type == "Product":
                result = Product.query.get(self.product_id)
                # Try to restore link if product was re-added
                if not result and self.product_id and self.product_code:
                    restored = Product.query.filter_by(barbuddy_code=self.product_code).first()
                    if restored:
                        self.product_id = restored.id
                        result = restored
            else:
                result = HomemadeIngredient.query.get(self.product_id)
        return result
    
    def get_quantity(self):
        """Get quantity, handling both old and new field names"""
        if self.quantity is not None:
            return self.quantity
        elif self.quantity_ml is not None:
            return self.quantity_ml
        return 0.0

    def calculate_cost(self):
        """
        Calculate cost based on ingredient type.
        NOTE: This method dynamically fetches the current product price from the database.
        When product prices are updated in the Master List, recipe costs will automatically
        reflect the new prices without requiring any manual updates.
        """
        try:
            ingredient = self.get_product()
            if not ingredient:
                return 0.0
            
            qty = self.get_quantity()
            if qty is None or qty <= 0:
                return 0.0
            
            if isinstance(ingredient, Product):
                # Uses current cost_per_unit from database - automatically reflects price changes
                if not ingredient.cost_per_unit or ingredient.cost_per_unit == 0:
                    return 0.0
                    
                if ingredient.selling_unit == "ml":
                    return round(ingredient.cost_per_unit * qty, 2)
                elif ingredient.selling_unit == "grams":
                    return round(ingredient.cost_per_unit * qty, 2)
                elif ingredient.selling_unit == "pieces":
                    return round(ingredient.cost_per_unit * qty, 2)
                else:
                    if ingredient.ml_in_bottle and ingredient.ml_in_bottle > 0:
                        return round((ingredient.cost_per_unit / ingredient.ml_in_bottle) * qty, 2)
                    return round(ingredient.cost_per_unit * qty, 2)
            
            elif isinstance(ingredient, HomemadeIngredient):
                # Secondary ingredients also calculate dynamically from their component products
                cost_per_unit = ingredient.calculate_cost_per_unit()
                return round(cost_per_unit * qty, 2)
            
            elif isinstance(ingredient, Recipe):
                # Nested recipes calculate their total cost dynamically
                recipe_cost = ingredient.calculate_total_cost()
                return round(recipe_cost * qty, 2)
            
            return 0.0
        except Exception as e:
            # Log error but return 0 to prevent template errors
            import logging
            logging.error(f"Error calculating cost for RecipeIngredient {self.id}: {str(e)}")
            return 0.0

# -------------------------
# PURCHASE REQUEST MODEL
# -------------------------
class PurchaseRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    ordered_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Pending')  # Pending, Approved, Rejected, Completed
    organisation = db.Column(db.String(200))  # Organization name for sharing
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_purchase_requests')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    invoice_number = db.Column(db.String(100), nullable=True)  # Invoice number when order received (legacy, kept for backward compatibility)
    invoice_value = db.Column(db.Float, nullable=True)  # Invoice value when order received (legacy, kept for backward compatibility)
    supplier_invoices = db.Column(db.Text, nullable=True)  # JSON string storing invoice data per supplier: {"Supplier Name": {"invoice_number": "...", "invoice_value": 0.0}}
    supplier_status = db.Column(db.Text, nullable=True)  # JSON string storing status per supplier: {"Supplier Name": "Pending"}
    supplier_received_dates = db.Column(db.Text, nullable=True)  # JSON string storing received dates per supplier: {"Supplier Name": "2025-12-13 00:01:37"}
    items = db.relationship('PurchaseItem', backref='purchase_request', cascade='all, delete-orphan')
    
    def get_supplier_invoices(self):
        """Get supplier invoices as a dictionary"""
        if self.supplier_invoices:
            try:
                return json.loads(self.supplier_invoices)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    def set_supplier_invoice(self, supplier, invoice_number=None, invoice_value=None):
        """Set invoice data for a specific supplier"""
        invoices = self.get_supplier_invoices()
        if supplier not in invoices:
            invoices[supplier] = {}
        if invoice_number is not None:
            invoices[supplier]['invoice_number'] = invoice_number
        if invoice_value is not None:
            invoices[supplier]['invoice_value'] = invoice_value
        self.supplier_invoices = json.dumps(invoices)
    
    def get_supplier_invoice(self, supplier):
        """Get invoice data for a specific supplier"""
        invoices = self.get_supplier_invoices()
        return invoices.get(supplier, {'invoice_number': '', 'invoice_value': None})
    
    def get_supplier_statuses(self):
        """Get supplier statuses as a dictionary"""
        if self.supplier_status:
            try:
                return json.loads(self.supplier_status)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    def set_supplier_status(self, supplier, status):
        """Set status for a specific supplier"""
        statuses = self.get_supplier_statuses()
        statuses[supplier] = status
        self.supplier_status = json.dumps(statuses)
    
    def get_supplier_status(self, supplier):
        """Get status for a specific supplier, defaults to main status if not set"""
        statuses = self.get_supplier_statuses()
        return statuses.get(supplier, self.status)
    
    def get_supplier_received_dates(self):
        """Get supplier received dates as a dictionary"""
        if self.supplier_received_dates:
            try:
                return json.loads(self.supplier_received_dates)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    def set_supplier_received_date(self, supplier, received_date=None):
        """Set received date for a specific supplier"""
        dates = self.get_supplier_received_dates()
        if received_date is None:
            from datetime import datetime
            received_date = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        dates[supplier] = received_date
        self.supplier_received_dates = json.dumps(dates)
    
    def get_supplier_received_date(self, supplier):
        """Get received date for a specific supplier"""
        dates = self.get_supplier_received_dates()
        return dates.get(supplier, None)
    
    def get_overall_status(self):
        """Calculate overall status based on supplier statuses for display in order lists"""
        # Get all unique suppliers from items
        suppliers = set(item.supplier or 'N/A' for item in self.items if item.supplier)
        if not suppliers:
            return self.status
        
        # Get status for each supplier
        supplier_statuses = {}
        for supplier in suppliers:
            supplier_statuses[supplier] = self.get_supplier_status(supplier)
        
        # Check for partial statuses
        status_values = list(supplier_statuses.values())
        
        # Check for cancelled orders
        cancelled_count = sum(1 for s in status_values if s == 'Order Cancelled')
        has_cancelled = cancelled_count > 0
        
        # Get non-cancelled suppliers
        non_cancelled_statuses = [s for s in status_values if s != 'Order Cancelled']
        non_cancelled_count = len(non_cancelled_statuses)
        
        # If there are cancelled orders
        if has_cancelled:
            # Check if all non-cancelled suppliers are received
            received_count = sum(1 for s in non_cancelled_statuses if s == 'Order Received')
            if received_count == non_cancelled_count and non_cancelled_count > 0:
                # All non-cancelled are received, but some are cancelled
                return 'Order Received, Order Cancelled'
            else:
                # Some cancelled, but not all non-cancelled are received
                return 'Order Cancelled'
        
        # No cancelled orders - check for partial statuses
        received_count = sum(1 for s in status_values if s == 'Order Received')
        if received_count > 0 and received_count < len(status_values):
            return 'Partially Received'
        
        # Check for Partially Ordered
        placed_count = sum(1 for s in status_values if s == 'Order Placed')
        if placed_count > 0 and placed_count < len(status_values):
            # Make sure none are received (if some are received, it's partially received, not partially ordered)
            if received_count == 0:
                return 'Partially Ordered'
        
        # If all suppliers have the same status, return that status
        if len(set(status_values)) == 1:
            return status_values[0]
        
        # Default to main status
        return self.status

    def calculate_total_cost(self):
        """Calculate total cost of all items in the purchase request"""
        return round(sum(item.cost_per_unit * item.order_quantity for item in self.items), 2)
    
    def calculate_received_total_cost(self):
        """Calculate total cost based on quantity received"""
        return round(sum(item.calculate_received_cost() for item in self.items), 2)

class PurchaseItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    purchase_request_id = db.Column(db.Integer, db.ForeignKey('purchase_request.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    code = db.Column(db.String(50))  # Store code for reference
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Float, nullable=False)  # Current quantity in inventory
    supplier = db.Column(db.String(120))
    sub_category = db.Column(db.String(50))
    cost_per_unit = db.Column(db.Float, nullable=False)
    order_quantity = db.Column(db.Float, nullable=False)  # Quantity to order (editable)
    quantity_received = db.Column(db.Float, nullable=True)  # Quantity actually received
    product = db.relationship('Product')
    
    def calculate_received_cost(self):
        """Calculate cost based on quantity received"""
        if self.quantity_received is not None:
            return round(self.cost_per_unit * self.quantity_received, 2)
        return 0.0

# -------------------------
# BOOK MODEL
# -------------------------
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200))
    library_type = db.Column(db.String(20), nullable=False)  # 'bartender' or 'chef'
    cover_image_path = db.Column(db.String(255))  # Path to cover image
    pdf_path = db.Column(db.String(255), nullable=False)  # Path to PDF file
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    organisation = db.Column(db.String(200))  # Organization name for sharing
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_books')
