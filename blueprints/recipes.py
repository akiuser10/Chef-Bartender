"""
Recipes Blueprint
Handles all recipe routes
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from extensions import db
from models import Product, HomemadeIngredient, Recipe, RecipeIngredient
from utils.db_helpers import ensure_schema_updates
from utils.file_upload import save_uploaded_file
from utils.constants import resolve_recipe_category, category_context_from_type, CATEGORY_CONFIG
from datetime import datetime

recipes_bp = Blueprint('recipes', __name__)


@recipes_bp.route('/recipes', methods=['GET'])
@login_required
def recipes_list():
    ensure_schema_updates()
    try:
        from sqlalchemy.orm import joinedload
        from utils.helpers import get_organization_filter
        # Eagerly load ingredients to avoid N+1 queries and ensure cost calculation works
        org_filter = get_organization_filter(Recipe)
        recipes = Recipe.query.filter(org_filter).options(
            joinedload(Recipe.ingredients)
        ).all()
        
        recipe_type_filter = request.args.get('type', '')
        category_filter = (request.args.get('category', '') or '').lower()
        
        if recipe_type_filter:
            recipes = [r for r in recipes if r.recipe_type == recipe_type_filter]
        if category_filter:
            # Check if it's a subcategory filter (food:Category or beverage:Category)
            if ':' in category_filter:
                filter_type, filter_value = category_filter.split(':', 1)
                if filter_type == 'food':
                    recipes = [r for r in recipes if r.food_category == filter_value]
                elif filter_type == 'beverage':
                    recipes = [r for r in recipes if r.beverage_category == filter_value]
            else:
                # Map category slug to db_labels from CATEGORY_CONFIG (legacy support)
                from utils.constants import resolve_recipe_category
                canonical, config = resolve_recipe_category(category_filter)
                if canonical and config:
                    labels = set(config['db_labels'])
                    # Prioritize type field over recipe_type since recipe_type is generic ('Beverage')
                    # and type field has specific values ('Beverages', 'Mocktails', 'Cocktails')
                    def matches_category(recipe):
                        # First check type field (most specific)
                        if recipe.type and recipe.type in labels:
                            return True
                        # Only check recipe_type if type is None or empty
                        if not recipe.type and recipe.recipe_type and recipe.recipe_type in labels:
                            return True
                        return False
                    recipes = [r for r in recipes if matches_category(r)]
        
        # Ensure ingredients are loaded for cost calculation
        for recipe in recipes:
            _ = recipe.ingredients
            for ingredient in recipe.ingredients:
                _ = ingredient.get_product()
        
        return render_template('recipes/list.html', recipes=recipes, selected_type=recipe_type_filter, selected_category=category_filter)
    except Exception as e:
        current_app.logger.error(f"Error in recipes_list: {str(e)}", exc_info=True)
        flash('An error occurred while loading recipes.', 'error')
        return render_template('recipes/list.html', recipes=[], selected_type='', selected_category='')


@recipes_bp.route('/recipes/<category>', methods=['GET'])
@login_required
def recipe_list(category):
    try:
        # Check if this is actually a recipe code (starts with 'REC-')
        # If so, redirect to the recipe code handler
        if category.startswith('REC-'):
            return view_recipe_by_code(category)
        
        canonical, config = resolve_recipe_category(category)
        if not canonical:
            # If category is invalid, redirect to recipes list instead of showing error
            flash(f"Category '{category}' not found. Showing all recipes.")
            return redirect(url_for('recipes.recipes_list'))

        from sqlalchemy.orm import joinedload
        from sqlalchemy import or_, and_
        from utils.helpers import get_organization_filter
        # Prioritize type field over recipe_type since recipe_type is generic ('Beverage')
        # and type field has specific values ('Beverages', 'Mocktails', 'Cocktails')
        org_filter = get_organization_filter(Recipe)
        recipes = Recipe.query.filter(org_filter).options(
            joinedload(Recipe.ingredients)
        ).filter(
            or_(
                Recipe.type.in_(config['db_labels']),
                and_(
                    or_(Recipe.type.is_(None), Recipe.type == ''),
                    Recipe.recipe_type.in_(config['db_labels'])
                )
            )
        ).all()
        
        # Ensure ingredients are loaded for cost calculation
        for recipe in recipes:
            _ = recipe.ingredients
            for ingredient in recipe.ingredients:
                _ = ingredient.get_product()
        
        return render_template(
            config['template'],
            recipes=recipes,
            category=config['display'],
            category_slug=canonical,
            add_label=config['add_label']
        )
    except Exception as e:
        current_app.logger.error(f"Error in recipe_list: {str(e)}", exc_info=True)
        flash('An error occurred while loading recipes.', 'error')
        return redirect(url_for('recipes.recipes_list'))


@recipes_bp.route('/recipes/<code>')
@login_required
def view_recipe_by_code(code):
    try:
        # First check if it looks like a recipe code (starts with REC-)
        # This should take priority over category matching
        if code.startswith('REC-'):
            from sqlalchemy.orm import joinedload
            from utils.helpers import get_organization_filter
            org_filter = get_organization_filter(Recipe)
            # First check if this is a valid recipe code
            recipe = Recipe.query.filter(org_filter).filter_by(recipe_code=code).first()
            if recipe:
                # Reload with eager loading
                recipe = Recipe.query.filter(org_filter).options(
                    joinedload(Recipe.ingredients)
                ).filter_by(recipe_code=code).first()
                
                if not recipe:
                    # Recipe code exists but query failed
                    flash("Recipe not found")
                    return redirect(url_for('recipes.recipes_list'))
                
                # Ensure ingredients are loaded
                _ = recipe.ingredients
                for ingredient in recipe.ingredients:
                    try:
                        _ = ingredient.get_product()
                    except Exception as e:
                        current_app.logger.warning(f"Error loading product for ingredient {ingredient.id}: {str(e)}")
                        continue
                
                try:
                    batch = recipe.batch_summary()
                except Exception as e:
                    current_app.logger.warning(f"Error in batch_summary for recipe {recipe.id}: {str(e)}")
                    batch = {}
                
                category_slug, category_display = category_context_from_type(recipe.type or recipe.recipe_type or '')
                # Ensure category_slug is always valid
                if not category_slug or category_slug not in ['cocktails', 'mocktails', 'beverages', 'food']:
                    category_slug = 'cocktails'
                    category_display = 'Cocktails'
                # Double-check that category_slug is valid before rendering
                canonical_check, _ = resolve_recipe_category(category_slug)
                if not canonical_check:
                    category_slug = 'cocktails'
                    category_display = 'Cocktails'
                return render_template('recipes/view.html', recipe=recipe, batch=batch, category_slug=category_slug, category_display=category_display)
            else:
                # Recipe code not found
                flash("Recipe not found")
                return redirect(url_for('recipes.recipes_list'))
        
        # If not a recipe code, check if it's a category name
        canonical, config = resolve_recipe_category(code)
        if canonical:
            # This is a category, not a recipe code - call the category handler directly
            return recipe_list(canonical)
        
        # Not a recipe code and not a category
        flash("Recipe or category not found")
        return redirect(url_for('recipes.recipes_list'))
    except Exception as e:
        current_app.logger.error(f"Error in view_recipe_by_code: {str(e)}", exc_info=True)
        import traceback
        current_app.logger.error(traceback.format_exc())
        flash(f'An error occurred while loading the recipe: {str(e)}', 'error')
        return redirect(url_for('recipes.recipes_list'))


@recipes_bp.route('/recipe/add/<category>', methods=['GET', 'POST'])
@login_required
def add_recipe(category):
    try:
        canonical, config = resolve_recipe_category(category)
        if not canonical:
            flash("Invalid recipe category")
            return redirect(url_for('main.index'))

        from utils.helpers import get_organization_filter
        prod_org_filter = get_organization_filter(Product)
        sec_org_filter = get_organization_filter(HomemadeIngredient)
        products = Product.query.filter(prod_org_filter).order_by(Product.description).all()
        secondary_ingredients = HomemadeIngredient.query.filter(sec_org_filter).order_by(HomemadeIngredient.name).all()
        ingredient_options = []
        for p in products:
            description = p.description or ''
            code = p.barbuddy_code or ''
            label = f"{description} ({code})" if code else description
            ingredient_options.append({
                'label': label,
                'description': description,
                'code': code,
                'id': p.id,
                'type': 'Product',
                'unit': p.selling_unit or 'ml',
                'cost_per_unit': p.cost_per_unit or 0.0,
                'container_volume': p.ml_in_bottle or (1 if (p.selling_unit or '').lower() == 'ml' else 0)
            })
        ingredient_options.extend([
            {
                'label': f"{sec.name} ({sec.unique_code})",
                'description': sec.name,
                'code': sec.unique_code or '',
                'id': sec.id,
                'type': 'Secondary',
                'unit': sec.unit or 'ml',
                'cost_per_unit': sec.calculate_cost_per_unit(),
                'container_volume': 1
            }
            for sec in secondary_ingredients
            if sec.unique_code
        ])

        if request.method == 'POST':
            try:
                title = request.form.get('title', '').strip()
                if not title:
                    flash('Recipe name is required.')
                    return redirect(url_for('recipes.add_recipe', category=canonical))
                
                method = request.form.get('method', '')
                garnish = request.form.get('garnish', '')
                glassware = request.form.get('glassware', '') if canonical in ['beverages', 'cocktails', 'mocktails'] else None
                plates = request.form.get('plates', '') if canonical == 'food' else None
                food_category = request.form.get('food_category', '') if canonical == 'food' else None
                beverage_category = request.form.get('beverage_category', '') if canonical in ['beverages', 'cocktails', 'mocktails'] else None
                item_level = request.form.get('item_level', 'Primary')
                selling_price = float(request.form.get('selling_price', 0) or 0)
                vat_percentage = float(request.form.get('vat_percentage', 0) or 0)
                service_charge_percentage = float(request.form.get('service_charge_percentage', 0) or 0)
                government_fees_percentage = float(request.form.get('government_fees_percentage', 0) or 0)
                
                # Generate unique recipe code - check within organization first
                from utils.helpers import get_organization_filter
                org_filter = get_organization_filter(Recipe)
                org_count = Recipe.query.filter(org_filter).count()
                max_attempts = 100
                recipe_code = None
                for attempt in range(max_attempts):
                    candidate_code = f"REC-{org_count + attempt + 1:04d}"
                    existing = Recipe.query.filter(org_filter).filter_by(recipe_code=candidate_code).first()
                    if not existing:
                        # Also check globally to ensure uniqueness
                        existing_global = Recipe.query.filter_by(recipe_code=candidate_code).first()
                        if not existing_global:
                            recipe_code = candidate_code
                            break
                
                if not recipe_code:
                    # Fallback to timestamp-based code
                    from datetime import datetime
                    recipe_code = f"REC-{datetime.now().strftime('%Y%m%d%H%M%S')}"

                image_path = None
                if 'image' in request.files:
                    file = request.files['image']
                    if file and file.filename:
                        try:
                            image_path = save_uploaded_file(file, 'recipes')
                        except Exception as e:
                            current_app.logger.warning(f"Error saving image: {str(e)}")
                            # Continue without image if upload fails

                # Determine recipe_type based on category
                recipe_type = 'Food' if canonical == 'food' else 'Beverage'
                
                recipe = Recipe(
                    recipe_code=recipe_code,
                    title=title,
                    method=method,
                    garnish=garnish,
                    glassware=glassware,
                    plates=plates,
                    food_category=food_category,
                    beverage_category=beverage_category,
                    recipe_type=recipe_type,
                    type=config['db_labels'][0],
                    item_level=item_level,
                    user_id=current_user.id,
                    organisation=(current_user.organisation.strip() if current_user.organisation and current_user.organisation.strip() else None),
                    last_edited_by=current_user.id,
                    image_path=image_path,
                    selling_price=selling_price,
                    vat_percentage=vat_percentage,
                    service_charge_percentage=service_charge_percentage,
                    government_fees_percentage=government_fees_percentage
                )
                db.session.add(recipe)
                db.session.flush()

                # Parse ingredients from form data
                # The form sends: ingredient_id[], ingredient_type[], ingredient_qty[], ingredient_unit[]
                ingredient_ids = request.form.getlist('ingredient_id')
                ingredient_types = request.form.getlist('ingredient_type')
                ingredient_qtys = request.form.getlist('ingredient_qty')
                ingredient_units = request.form.getlist('ingredient_unit')
                
                current_app.logger.debug(f"Received {len(ingredient_ids)} ingredient IDs")
                current_app.logger.debug(f"Ingredient IDs: {ingredient_ids}")
                current_app.logger.debug(f"Ingredient types: {ingredient_types}")
                current_app.logger.debug(f"Ingredient qtys: {ingredient_qtys}")
                
                items_added = 0
                for idx, ing_id in enumerate(ingredient_ids):
                    if not ing_id or not str(ing_id).strip():
                        current_app.logger.debug(f"Skipping empty ingredient ID at index {idx}")
                        continue
                    
                    try:
                        ing_type = ingredient_types[idx] if idx < len(ingredient_types) else ''
                        qty_str = ingredient_qtys[idx] if idx < len(ingredient_qtys) else '0'
                        unit = ingredient_units[idx] if idx < len(ingredient_units) else 'ml'
                        
                        if not qty_str or not str(qty_str).strip():
                            current_app.logger.debug(f"Skipping ingredient {idx} - no quantity")
                            continue
                        
                        try:
                            qty = float(qty_str)
                        except (ValueError, TypeError):
                            current_app.logger.warning(f"Invalid quantity '{qty_str}' for ingredient {idx}")
                            continue
                        
                        if qty <= 0:
                            current_app.logger.debug(f"Skipping ingredient {idx} - quantity {qty} <= 0")
                            continue
                        
                        try:
                            ing_id_int = int(ing_id)
                        except (ValueError, TypeError):
                            current_app.logger.warning(f"Invalid ingredient ID '{ing_id}' at index {idx}")
                            continue
                        
                        # Determine ingredient_type for RecipeIngredient
                        db_ingredient_type = None
                        db_product_type = None
                        db_product_id = None
                        if ing_type == 'Product':
                            db_ingredient_type = 'Product'
                            db_product_type = 'Product'
                            db_product_id = ing_id_int
                        elif ing_type == 'Secondary':
                            db_ingredient_type = 'Homemade'
                            db_product_type = 'Homemade'
                            db_product_id = ing_id_int
                        else:
                            # Try to determine from ID - check within organization
                            from utils.helpers import get_organization_filter
                            prod_filter = get_organization_filter(Product)
                            sec_filter = get_organization_filter(HomemadeIngredient)
                            recipe_filter = get_organization_filter(Recipe)
                            if Product.query.filter(prod_filter).filter_by(id=ing_id_int).first():
                                db_ingredient_type = 'Product'
                                db_product_type = 'Product'
                                db_product_id = ing_id_int
                            elif HomemadeIngredient.query.filter(sec_filter).filter_by(id=ing_id_int).first():
                                db_ingredient_type = 'Homemade'
                                db_product_type = 'Homemade'
                                db_product_id = ing_id_int
                            elif Recipe.query.filter(recipe_filter).filter_by(id=ing_id_int).first():
                                db_ingredient_type = 'Recipe'
                                db_product_type = 'Recipe'
                                db_product_id = ing_id_int
                            else:
                                current_app.logger.warning(f"Unknown ingredient type for ID {ing_id_int}, type was '{ing_type}'")
                                continue
                        
                        if not db_ingredient_type:
                            current_app.logger.warning(f"Could not determine ingredient type for ID {ing_id_int}")
                            continue
                        
                        # Calculate quantity_ml - ensure it's never None
                        quantity_ml = float(qty)  # Default to qty
                        if unit and unit != 'ml':
                            # Try to convert if we have the product info
                            if db_ingredient_type == 'Product':
                                from utils.helpers import get_organization_filter
                                prod_filter = get_organization_filter(Product)
                                product = Product.query.filter(prod_filter).filter_by(id=ing_id_int).first()
                                if product and product.ml_in_bottle and product.ml_in_bottle > 0:
                                    # Assume unit is in bottles/containers
                                    quantity_ml = qty * product.ml_in_bottle
                            elif db_ingredient_type == 'Homemade':
                                # For secondary ingredients, assume ml
                                quantity_ml = qty
                        
                        # Ensure quantity_ml is a valid number
                        if quantity_ml is None or quantity_ml <= 0:
                            quantity_ml = qty
                        
                        # Get product name and code for storage
                        product_name = None
                        product_code = None
                        ingredient_name = None
                        
                        if db_ingredient_type == 'Product':
                            from utils.helpers import get_organization_filter
                            prod_filter = get_organization_filter(Product)
                            product = Product.query.filter(prod_filter).filter_by(id=ing_id_int).first()
                            if product:
                                product_name = product.description
                                product_code = product.barbuddy_code
                        elif db_ingredient_type == 'Homemade':
                            from utils.helpers import get_organization_filter
                            sec_filter = get_organization_filter(HomemadeIngredient)
                            secondary = HomemadeIngredient.query.filter(sec_filter).filter_by(id=ing_id_int).first()
                            if secondary:
                                ingredient_name = secondary.name
                                product_code = secondary.unique_code
                        elif db_ingredient_type == 'Recipe':
                            from utils.helpers import get_organization_filter
                            recipe_filter = get_organization_filter(Recipe)
                            nested_recipe = Recipe.query.filter(recipe_filter).filter_by(id=ing_id_int).first()
                            if nested_recipe:
                                ingredient_name = nested_recipe.title
                                product_code = nested_recipe.recipe_code
                        
                        item = RecipeIngredient(
                            recipe_id=recipe.id,
                            ingredient_type=db_ingredient_type,
                            ingredient_id=ing_id_int,
                            quantity=float(qty),
                            unit=str(unit) if unit else 'ml',
                            quantity_ml=float(quantity_ml),
                            product_type=db_product_type or db_ingredient_type,
                            product_id=db_product_id or ing_id_int,
                            product_name=product_name,
                            product_code=product_code,
                            ingredient_name=ingredient_name
                        )
                        db.session.add(item)
                        items_added += 1
                        current_app.logger.debug(f"Added ingredient {idx}: type={db_ingredient_type}, id={ing_id_int}, qty={qty}, unit={unit}")
                    except (ValueError, TypeError) as e:
                        current_app.logger.warning(f"Error processing ingredient {idx}: {str(e)}", exc_info=True)
                        continue
                    except Exception as e:
                        current_app.logger.error(f"Unexpected error processing ingredient {idx}: {str(e)}", exc_info=True)
                        continue

                if items_added == 0:
                    flash('Please add at least one ingredient with a quantity greater than zero.')
                    db.session.rollback()
                    return redirect(url_for('recipes.add_recipe', category=canonical))

                db.session.commit()
                flash(f'{config["add_label"]} recipe added successfully!')
                return redirect(url_for('recipes.recipes_list'))
            except Exception as e:
                db.session.rollback()
                error_msg = str(e)
                current_app.logger.error(f"Error creating recipe: {error_msg}", exc_info=True)
                
                # Provide more specific error messages
                if 'UNIQUE constraint' in error_msg or 'unique' in error_msg.lower():
                    flash('A recipe with this code already exists. Please try again.', 'error')
                elif 'NOT NULL constraint' in error_msg or 'null' in error_msg.lower():
                    flash('Missing required information. Please ensure all required fields are filled.', 'error')
                elif 'ingredient' in error_msg.lower():
                    flash(f'Error with ingredients: {error_msg}. Please check your ingredient selections.', 'error')
                else:
                    flash(f'An error occurred while creating the recipe: {error_msg}. Please try again.', 'error')
                
                return redirect(url_for('recipes.add_recipe', category=canonical))

        return render_template(
            'recipes/add_recipe.html',
            products=products,
            secondary_ingredients=secondary_ingredients,
            category=config['display'],
            add_label=config['add_label'],
            category_slug=canonical,
            ingredient_options=ingredient_options,
            edit_mode=False,
            recipe=None,
            preset_rows=[]
        )
    except Exception as e:
        current_app.logger.error(f"Error in add_recipe: {str(e)}", exc_info=True)
        flash('An error occurred while loading the recipe creation page.', 'error')
        return redirect(url_for('recipes.recipes_list'))


@recipes_bp.route('/recipe/<int:id>/export-pdf')
@login_required
def export_recipe_pdf(id):
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from io import BytesIO
        from flask import make_response
        from sqlalchemy.orm import joinedload
        from datetime import datetime
        
        recipe = Recipe.query.options(
            joinedload(Recipe.ingredients)
        ).get_or_404(id)
        
        # Create a BytesIO buffer for the PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#1a2a2a'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1a2a2a'),
            spaceAfter=10,
            spaceBefore=10
        )
        
        # Title
        elements.append(Paragraph(recipe.title or "Recipe", title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Ingredients Table (First, as shown in screenshot)
        elements.append(Paragraph("INGREDIENTS", heading_style))
        
        table_data = [['CODE', 'DESCRIPTION', 'UNIT QTY', 'RECIPE ML', 'RECIPE COST']]
        
        total_cost = 0.0
        # Initialize currency code before the loop to ensure it's always available
        from utils.currency import format_currency
        from flask_login import current_user
        pdf_currency_code = current_user.currency if current_user.is_authenticated else 'AED'
        
        if recipe.ingredients:
            for i in recipe.ingredients:
                ingredient = i.get_product()
                if ingredient:
                    ingredient_type = ingredient.__class__.__name__
                    qty = i.get_quantity()
                    cost = i.calculate_cost()
                    total_cost += cost
                    
                    code = 'N/A'
                    desc = 'N/A'
                    unit_qty = '0'
                    
                    if ingredient_type == 'Product':
                        code = ingredient.barbuddy_code or 'N/A'
                        desc = ingredient.description or 'N/A'
                        unit_qty = f"{ingredient.ml_in_bottle or 0:.0f}"
                    elif ingredient_type == 'HomemadeIngredient':
                        code = ingredient.unique_code or 'N/A'
                        desc = f"{ingredient.name} (Secondary)"
                        unit_qty = f"{ingredient.total_volume_ml or 0:.2f}"
                    elif ingredient_type == 'Recipe':
                        code = ingredient.recipe_code or 'N/A'
                        desc = f"{ingredient.title} (Recipe)"
                        unit_qty = "1"
                    
                    display_unit = i.unit or ''
                    if display_unit.lower() == 'each':
                        display_unit = ''
                    recipe_ml = f"{qty:.2f}"
                    if display_unit:
                        recipe_ml += f" {display_unit}"
                    
                    table_data.append([code, desc, unit_qty, recipe_ml, format_currency(cost, pdf_currency_code)])
        
        table_data.append(['', '', '', 'Total', format_currency(total_cost, pdf_currency_code)])
        
        ingredients_table = Table(table_data, colWidths=[1*inch, 2.5*inch, 0.8*inch, 1*inch, 1*inch])
        ingredients_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a2a2a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (4, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
            ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(ingredients_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Method
        if recipe.method:
            elements.append(Paragraph("METHOD", heading_style))
            elements.append(Paragraph(recipe.method, styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
        
        # Garnish
        if recipe.garnish:
            elements.append(Paragraph("GARNISH:", heading_style))
            elements.append(Paragraph(recipe.garnish, styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
        
        # Glassware (for beverage recipes)
        is_beverage = recipe.beverage_category or (recipe.type and recipe.type in ['Cocktails', 'Mocktails', 'Beverages', 'Classic', 'Signature']) or (recipe.recipe_type and recipe.recipe_type == 'Beverage')
        if is_beverage and recipe.glassware:
            elements.append(Paragraph("GLASSWARE:", heading_style))
            elements.append(Paragraph(recipe.glassware, styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
        
        # Plates (for food recipes)
        is_food = recipe.food_category or (recipe.type and recipe.type == 'Food') or (recipe.recipe_type and recipe.recipe_type == 'Food')
        if is_food and recipe.plates:
            elements.append(Paragraph("PLATES:", heading_style))
            elements.append(Paragraph(recipe.plates, styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
        
        # Get user currency
        from utils.currency import format_currency
        currency_code = current_user.currency if current_user.is_authenticated else 'AED'
        
        # Recipe Details (Last, as shown in screenshot)
        elements.append(Paragraph("RECIPE DETAILS", heading_style))
        
        details_data = [
            ['RECIPE COST:', format_currency(recipe.calculate_total_cost(), currency_code)],
        ]
        
        sp = recipe.selling_price_value()
        if sp and sp > 0:
            details_data.append(['SELLING PRICE:', format_currency(sp, currency_code)])
        else:
            details_data.append(['SELLING PRICE:', '--'])
        
        details_data.extend([
            ['VAT %:', f"{recipe.vat_percentage or 0:.2f}%"],
            ['SERVICE CHARGE %:', f"{recipe.service_charge_percentage or 0:.2f}%"],
            ['GOVERNMENT FEES %:', f"{recipe.government_fees_percentage or 0:.2f}%"],
        ])
        
        pct = recipe.cost_percentage()
        if pct is not None:
            details_data.append(['COST % OF SP:', f"{pct:.2f}%"])
        else:
            details_data.append(['COST % OF SP:', '--'])
        
        details_table = Table(details_data, colWidths=[2.5*inch, 2.5*inch])
        details_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(details_table)
        
        # Footer
        elements.append(Spacer(1, 0.3*inch))
        footer_text = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Chef & Bartender"
        elements.append(Paragraph(footer_text, ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)))
        
        # Build PDF
        doc.build(elements)
        
        # Get the value of the BytesIO buffer
        buffer.seek(0)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Create response with recipe name as filename
        import re
        recipe_name = recipe.title or "recipe"
        # Sanitize filename - remove invalid characters
        safe_filename = re.sub(r'[^\w\s-]', '', recipe_name).strip()
        safe_filename = re.sub(r'[-\s]+', '_', safe_filename)
        filename = f"{safe_filename}.pdf"
        
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        current_app.logger.error(f'Error generating PDF: {str(e)}', exc_info=True)
        flash(f'Error generating PDF: {str(e)}', 'error')
        return redirect(url_for('recipes.view_recipe', id=id))


@recipes_bp.route('/recipe/<int:id>')
@login_required
def view_recipe(id):
    try:
        from sqlalchemy.orm import joinedload
        from utils.helpers import get_organization_filter
        org_filter = get_organization_filter(Recipe)
        recipe = Recipe.query.filter(org_filter).options(
            joinedload(Recipe.ingredients)
        ).filter_by(id=id).first_or_404()
        
        # Ensure ingredients are loaded
        _ = recipe.ingredients
        for ingredient in recipe.ingredients:
            try:
                _ = ingredient.get_product()
            except Exception as e:
                current_app.logger.warning(f"Error loading product for ingredient {ingredient.id}: {str(e)}")
                continue
        
        try:
            batch = recipe.batch_summary()
        except Exception as e:
            current_app.logger.warning(f"Error in batch_summary for recipe {recipe.id}: {str(e)}")
            batch = {}
        
        category_slug, category_display = category_context_from_type(recipe.type or recipe.recipe_type or '')
        # Ensure category_slug is always valid
        if not category_slug or category_slug not in ['cocktails', 'mocktails', 'beverages', 'food']:
            category_slug = 'cocktails'
            category_display = 'Cocktails'
        # Double-check that category_slug is valid before rendering
        canonical_check, _ = resolve_recipe_category(category_slug)
        if not canonical_check:
            category_slug = 'cocktails'
            category_display = 'Cocktails'
        return render_template('recipes/view.html', recipe=recipe, batch=batch, category_slug=category_slug, category_display=category_display)
    except Exception as e:
        current_app.logger.error(f"Error in view_recipe: {str(e)}", exc_info=True)
        import traceback
        current_app.logger.error(traceback.format_exc())
        flash(f'An error occurred while loading the recipe: {str(e)}', 'error')
        return redirect(url_for('recipes.recipes_list'))




@recipes_bp.route('/recipes/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_recipe(id):
    ensure_schema_updates()
    try:
        from sqlalchemy.orm import joinedload
        from utils.helpers import get_organization_filter
        org_filter = get_organization_filter(Recipe)
        recipe = Recipe.query.filter(org_filter).options(
            joinedload(Recipe.ingredients)
        ).filter_by(id=id).first_or_404()
        
        # Ensure ingredients are loaded
        _ = recipe.ingredients
        for ingredient in recipe.ingredients:
            _ = ingredient.get_product()
        
        # Determine category_slug: check food_category/beverage_category first, then type fields
        if recipe.food_category:
            category_slug = 'food'
            category_display = 'Food'
        elif recipe.beverage_category:
            # If beverage_category is set, determine which beverage category_slug to use
            category_slug, category_display = category_context_from_type(recipe.type or recipe.recipe_type or 'beverages')
            if category_slug not in ['beverages', 'cocktails', 'mocktails']:
                category_slug = 'beverages'
                category_display = 'Beverages'
        else:
            category_slug, category_display = category_context_from_type(recipe.type or recipe.recipe_type or '')
            if not category_slug:
                category_slug = 'cocktails'
                category_display = 'Cocktails'
        config = CATEGORY_CONFIG.get(category_slug, CATEGORY_CONFIG['cocktails'])
        
        # Apply organization filters to ensure users only see ingredients from their organization
        from utils.helpers import get_organization_filter
        prod_org_filter = get_organization_filter(Product)
        sec_org_filter = get_organization_filter(HomemadeIngredient)
        products = Product.query.filter(prod_org_filter).order_by(Product.description).all()
        secondary_ingredients = HomemadeIngredient.query.filter(sec_org_filter).order_by(HomemadeIngredient.name).all()
        
        ingredient_options = []
        for p in products:
            description = p.description or ''
            code = p.barbuddy_code or ''
            label = f"{description} ({code})" if code else description
            ingredient_options.append({
                'label': label,
                'description': description,
                'code': code,
                'id': int(p.id),
                'type': 'Product',
                'unit': p.selling_unit or 'ml',
                'cost_per_unit': float(p.cost_per_unit or 0.0),
                'container_volume': float(p.ml_in_bottle or (1 if (p.selling_unit or '').lower() == 'ml' else 0))
            })
        for sec in secondary_ingredients:
            if sec.unique_code:
                try:
                    cost_per_unit = sec.calculate_cost_per_unit()
                except Exception:
                    cost_per_unit = 0.0
                ingredient_options.append({
                    'label': f"{sec.name} ({sec.unique_code})",
                    'description': sec.name,
                    'code': sec.unique_code or '',
                    'id': int(sec.id),
                    'type': 'Secondary',
                    'unit': sec.unit or 'ml',
                    'cost_per_unit': float(cost_per_unit),
                    'container_volume': 1.0
                })

        if request.method == 'POST':
            try:
                from utils.helpers import get_organization_filter
                org_filter = get_organization_filter(Recipe)
                recipe = Recipe.query.filter(org_filter).filter_by(id=id).first_or_404()
                
                recipe.title = request.form['title']
                recipe.item_level = request.form.get('item_level', recipe.item_level or 'Primary')
                recipe.method = request.form.get('method', '')
                recipe.garnish = request.form.get('garnish', '')
                if category_slug in ['beverages', 'cocktails', 'mocktails']:
                    recipe.glassware = request.form.get('glassware', '')
                if category_slug == 'food':
                    recipe.plates = request.form.get('plates', '')
                    recipe.food_category = request.form.get('food_category', '')
                elif category_slug in ['beverages', 'cocktails', 'mocktails']:
                    recipe.beverage_category = request.form.get('beverage_category', '')
                recipe.selling_price = float(request.form.get('selling_price', recipe.selling_price or 0))
                recipe.vat_percentage = float(request.form.get('vat_percentage', recipe.vat_percentage or 0))
                recipe.service_charge_percentage = float(request.form.get('service_charge_percentage', recipe.service_charge_percentage or 0))
                recipe.government_fees_percentage = float(request.form.get('government_fees_percentage', recipe.government_fees_percentage or 0))
                recipe.last_edited_by = current_user.id
                recipe.last_edited_at = datetime.utcnow()
                
                # Update organization if user's organization changed (normalized)
                if current_user.organisation and current_user.organisation.strip():
                    recipe.organisation = current_user.organisation.strip()

                if 'image' in request.files:
                    file = request.files['image']
                    if file.filename:
                        recipe.image_path = save_uploaded_file(file, 'recipes')

                RecipeIngredient.query.filter_by(recipe_id=recipe.id).delete()

                ingredient_ids = request.form.getlist('ingredient_id')
                ingredient_types = request.form.getlist('ingredient_type')
                ingredient_quantities = request.form.getlist('ingredient_qty')
                ingredient_units = request.form.getlist('ingredient_unit')

                for idx, ing_id in enumerate(ingredient_ids):
                    if not ing_id or idx >= len(ingredient_types) or idx >= len(ingredient_quantities):
                        continue
                    
                    ing_type = (ingredient_types[idx] or '').strip()
                    try:
                        ing_id_int = int(ing_id)
                    except (ValueError, TypeError):
                        continue
                    
                    try:
                        qty = float(ingredient_quantities[idx] or 0)
                    except (ValueError, IndexError, TypeError):
                        qty = 0
                    
                    if qty <= 0:
                        continue
                    
                    unit = ingredient_units[idx] if idx < len(ingredient_units) and ingredient_units[idx] else 'ml'
                    
                    # Normalize type, and also set product_type/id for NOT NULL schema
                    if ing_type == 'Secondary':
                        db_ingredient_type = 'Homemade'
                    elif ing_type in ['Product', 'Homemade', 'Recipe']:
                        db_ingredient_type = ing_type
                    else:
                        # Best-effort detection - check within organization
                        from utils.helpers import get_organization_filter
                        prod_filter = get_organization_filter(Product)
                        sec_filter = get_organization_filter(HomemadeIngredient)
                        recipe_filter = get_organization_filter(Recipe)
                        if Product.query.filter(prod_filter).filter_by(id=ing_id_int).first():
                            db_ingredient_type = 'Product'
                        elif HomemadeIngredient.query.filter(sec_filter).filter_by(id=ing_id_int).first():
                            db_ingredient_type = 'Homemade'
                        elif Recipe.query.filter(recipe_filter).filter_by(id=ing_id_int).first():
                            db_ingredient_type = 'Recipe'
                        else:
                            db_ingredient_type = 'Product'  # Default fallback
                    
                    db_product_type = db_ingredient_type
                    db_product_id = ing_id_int
                    
                    # Compute quantity_ml; convert if not ml and product has ml_in_bottle
                    quantity_ml = qty
                    if unit and unit != 'ml':
                        if db_ingredient_type == 'Product':
                            from utils.helpers import get_organization_filter
                            prod_filter = get_organization_filter(Product)
                            prod = Product.query.filter(prod_filter).filter_by(id=ing_id_int).first()
                            if prod and prod.ml_in_bottle and prod.ml_in_bottle > 0:
                                quantity_ml = qty * prod.ml_in_bottle
                        # For Homemade/Recipe, treat qty as ml/serving
                    
                    if quantity_ml is None or quantity_ml <= 0:
                        quantity_ml = qty
                    
                    # Get product name and code for storage
                    product_name = None
                    product_code = None
                    ingredient_name = None
                    
                    if db_ingredient_type == 'Product':
                        from utils.helpers import get_organization_filter
                        prod_filter = get_organization_filter(Product)
                        product = Product.query.filter(prod_filter).filter_by(id=ing_id_int).first()
                        if product:
                            product_name = product.description
                            product_code = product.barbuddy_code
                    elif db_ingredient_type == 'Homemade':
                        from utils.helpers import get_organization_filter
                        sec_filter = get_organization_filter(HomemadeIngredient)
                        secondary = HomemadeIngredient.query.filter(sec_filter).filter_by(id=ing_id_int).first()
                        if secondary:
                            ingredient_name = secondary.name
                            product_code = secondary.unique_code
                    elif db_ingredient_type == 'Recipe':
                        from utils.helpers import get_organization_filter
                        recipe_filter = get_organization_filter(Recipe)
                        nested_recipe = Recipe.query.filter(recipe_filter).filter_by(id=ing_id_int).first()
                        if nested_recipe:
                            ingredient_name = nested_recipe.title
                            product_code = nested_recipe.recipe_code
                    
                    item = RecipeIngredient(
                        recipe_id=recipe.id,
                        ingredient_type=db_ingredient_type,
                        ingredient_id=ing_id_int,
                        quantity=qty,
                        unit=unit,
                        quantity_ml=float(quantity_ml),
                        product_type=db_product_type,
                        product_id=db_product_id,
                        product_name=product_name,
                        product_code=product_code,
                        ingredient_name=ingredient_name
                    )
                    db.session.add(item)

                db.session.commit()
                flash('Recipe updated successfully!')
                scroll_to = request.args.get('scroll_to') or request.form.get('scroll_to')
                if scroll_to:
                    return redirect(url_for('recipes.recipes_list') + f'#row_{scroll_to}')
                return redirect(url_for('recipes.recipes_list'))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error updating recipe: {str(e)}", exc_info=True)
                flash(f'An error occurred while updating the recipe: {str(e)}', 'error')
                scroll_to = request.args.get('scroll_to') or request.form.get('scroll_to')
                if scroll_to:
                    return redirect(url_for('recipes.edit_recipe', id=id, scroll_to=scroll_to))
                return redirect(url_for('recipes.edit_recipe', id=id))

        preset_rows = []
        recipe_ingredients = RecipeIngredient.query.filter_by(recipe_id=recipe.id).all()
        current_app.logger.info(f"Edit recipe {recipe.id}: Found {len(recipe_ingredients)} ingredients")
        for ingredient in recipe_ingredients:
            ing_type = ingredient.ingredient_type
            if ing_type == 'Homemade':
                ing_type = 'Secondary'
            
            label = ''
            description = ''
            code = ''
            if ing_type == 'Product':
                product = Product.query.get(ingredient.ingredient_id)
                if product:
                    description = product.description or ''
                    code = product.barbuddy_code or ''
                    label = f"{description} ({code})" if code else description
            elif ing_type == 'Secondary':
                sec = HomemadeIngredient.query.get(ingredient.ingredient_id)
                if sec and sec.unique_code:
                    description = sec.name or ''
                    code = sec.unique_code or ''
                    label = f"{description} ({code})" if code else description
            elif ing_type == 'Recipe':
                rec = Recipe.query.get(ingredient.ingredient_id)
                if rec and rec.recipe_code:
                    description = rec.title or ''
                    code = rec.recipe_code or ''
                    label = f"{description} ({code})" if code else description
            
            if label:
                preset_rows.append({
                    'label': label,
                    'description': description,
                    'code': code,
                    'id': int(ingredient.ingredient_id),
                    'type': ing_type,
                    'qty': float(ingredient.quantity or 0),
                    'unit': ingredient.unit or 'ml'
                })

        scroll_to = request.args.get('scroll_to')
        return render_template('recipes/edit.html',
                               products=products,
                               secondary_ingredients=secondary_ingredients,
                               category=category_display,
                               add_label=config['add_label'],
                               category_slug=category_slug,
                               ingredient_options=ingredient_options,
                               recipe=recipe,
                               preset_rows=preset_rows,
                               scroll_to=scroll_to)
    except Exception as e:
        current_app.logger.error(f"Error in edit_recipe: {str(e)}", exc_info=True)
        flash('An error occurred while loading the recipe for editing.', 'error')
        return redirect(url_for('recipes.recipes_list'))


@recipes_bp.route('/recipes/<int:id>/delete', methods=['POST'])
@login_required
def delete_recipe(id):
    from utils.helpers import get_organization_filter
    org_filter = get_organization_filter(Recipe)
    recipe = Recipe.query.filter(org_filter).filter_by(id=id).first_or_404()
    db.session.delete(recipe)
    db.session.commit()
    flash('Recipe deleted successfully!')
    return redirect(url_for('recipes.recipes_list'))

