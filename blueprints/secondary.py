"""
Secondary Ingredients Blueprint
Handles all secondary ingredient (homemade ingredient) routes
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from extensions import db
from models import Product, HomemadeIngredient, HomemadeIngredientItem
from utils.db_helpers import ensure_schema_updates
from datetime import datetime
import time

secondary_bp = Blueprint('secondary', __name__)


@secondary_bp.route('/secondary-ingredients', methods=['GET'])
@login_required
def secondary_ingredients():
    ensure_schema_updates()
    try:
        # Eagerly load ingredients and their products to ensure cost calculation works
        from sqlalchemy.orm import joinedload
        from utils.helpers import get_organization_filter
        org_filter = get_organization_filter(HomemadeIngredient)
        secondary_items = HomemadeIngredient.query.filter(org_filter).options(
            joinedload(HomemadeIngredient.ingredients).joinedload(HomemadeIngredientItem.product)
        ).all()
        
        # Get filter parameters
        category_filter = request.args.get('category', '').strip()
        sub_category_filter = request.args.get('sub_category', '').strip()
        
        # Apply filters
        if category_filter:
            secondary_items = [item for item in secondary_items if item.category == category_filter]
        
        if sub_category_filter:
            # Check if it's a subcategory filter (food:SubCategory or beverage:SubCategory)
            if ':' in sub_category_filter:
                filter_type, filter_value = sub_category_filter.split(':', 1)
                if filter_type == 'food':
                    secondary_items = [item for item in secondary_items if item.category == 'Food' and item.sub_category == filter_value]
                elif filter_type == 'beverage':
                    secondary_items = [item for item in secondary_items if item.category == 'Beverage' and item.sub_category == filter_value]
            else:
                # Direct sub-category match (for backward compatibility)
                secondary_items = [item for item in secondary_items if item.sub_category == sub_category_filter]
        
        table_rows = []
        for item in secondary_items:
            try:
                # Ensure ingredients are loaded
                _ = item.ingredients
                for ingredient_item in item.ingredients:
                    _ = ingredient_item.product
                
                # Calculate total cost - sum of all ingredient costs
                try:
                    # Debug: Check if ingredients exist
                    if not item.ingredients:
                        current_app.logger.warning(f"Secondary ingredient {item.id} ({item.name}) has no ingredients")
                        total_cost = 0.0
                    else:
                        # Debug: Check each ingredient
                        for ing in item.ingredients:
                            if not ing.product:
                                current_app.logger.warning(f"Ingredient item {ing.id} has no product")
                            elif ing.product.cost_per_unit is None:
                                current_app.logger.warning(f"Product {ing.product.id} ({ing.product.description}) has no cost_per_unit")
                        total_cost = item.calculate_cost()
                        current_app.logger.debug(f"Calculated cost for {item.id} ({item.name}): {total_cost}, ingredients count: {len(item.ingredients)}")
                except Exception as e:
                    current_app.logger.error(f"Error calculating cost for {item.id}: {str(e)}", exc_info=True)
                    total_cost = 0.0
                
                # Calculate cost per unit
                try:
                    if item.total_volume_ml and item.total_volume_ml > 0:
                        unit_cost = item.calculate_cost_per_unit()
                    else:
                        unit_cost = 0.0
                except Exception as e:
                    current_app.logger.error(f"Error calculating unit cost for {item.id}: {str(e)}", exc_info=True)
                    unit_cost = 0.0
                
                # Check if item has missing cost
                has_missing = item.has_missing_cost()
                
                # Get creator and editor names
                from utils.helpers import get_user_display_name
                creator_name = get_user_display_name(item.creator) if item.creator else 'Unknown'
                editor_name = get_user_display_name(item.last_editor) if item.last_editor else (creator_name if item.creator else 'Unknown')
                
                table_rows.append({
                    'id': item.id,
                    'code': item.unique_code or f"SEC-{item.id:04d}",
                    'name': item.name or 'Unnamed',
                    'category': item.category,
                    'sub_category': item.sub_category,
                    'unit': item.unit or 'ml',
                    'total_volume': item.total_volume_ml or 0.0,
                    'total_cost': total_cost,
                    'unit_cost': unit_cost,
                    'has_missing_cost': has_missing,
                    'created_by': creator_name,
                    'last_edited_by': editor_name,
                    'created_at': item.created_at,
                    'last_edited_at': item.last_edited_at
                })
            except Exception as e:
                current_app.logger.error(f"Error processing secondary ingredient {item.id}: {str(e)}", exc_info=True)
                # Check if item has missing cost even if there was an error
                has_missing = False
                try:
                    has_missing = item.has_missing_cost()
                except:
                    pass
                table_rows.append({
                    'id': item.id,
                    'code': item.unique_code or f"SEC-{item.id:04d}",
                    'name': item.name or 'Unnamed',
                    'category': item.category,
                    'sub_category': item.sub_category,
                    'unit': item.unit or 'ml',
                    'total_volume': item.total_volume_ml or 0.0,
                    'total_cost': 0.0,
                    'unit_cost': 0.0,
                    'has_missing_cost': has_missing
                })
        return render_template('secondary_ingredients/list.html', 
                              secondary_rows=table_rows,
                              selected_category=category_filter,
                              selected_sub_category=sub_category_filter)
    except Exception as e:
        current_app.logger.error(f"Error in secondary_ingredients route: {str(e)}", exc_info=True)
        flash('An error occurred while loading secondary ingredients.', 'error')
        return render_template('secondary_ingredients/list.html', secondary_rows=[])


@secondary_bp.route('/secondary-ingredients/<int:id>/export-pdf')
@login_required
def export_secondary_ingredient_pdf(id):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from io import BytesIO
        from flask import make_response
        from sqlalchemy.orm import joinedload
        from datetime import datetime
        
        secondary = HomemadeIngredient.query.options(
            joinedload(HomemadeIngredient.ingredients).joinedload(HomemadeIngredientItem.product)
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
        elements.append(Paragraph(secondary.name or "Secondary Ingredient", title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Ingredient Details
        total_cost = sum(item.calculate_cost() for item in secondary.ingredients if item.product)
        # Get user currency
        from utils.currency import format_currency
        currency_code = current_user.currency if current_user.is_authenticated else 'AED'
        
        details_data = [
            ['Unit:', secondary.unit or 'N/A'],
            ['RECIPE COST:', format_currency(total_cost, currency_code)],
            ['TOTAL VOLUME:', f"{secondary.total_volume_ml:.2f} {secondary.unit or ''}"],
            ['COST PER UNIT:', f"{format_currency(secondary.calculate_cost_per_unit(), currency_code, 4)} / {secondary.unit or ''}"],
        ]
        
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
        elements.append(Spacer(1, 0.3*inch))
        
        # Ingredients Table
        elements.append(Paragraph("INGREDIENTS", heading_style))
        
        table_data = [['CODE', 'DESCRIPTION', 'UNIT QTY', 'RECIPE ML', 'RECIPE COST']]
        
        for item in secondary.ingredients:
            if item.product:
                cost = item.calculate_cost()
                display_unit = item.unit or ''
                if display_unit.lower() == 'each':
                    display_unit = ''
                recipe_ml = f"{item.quantity:.2f}"
                if display_unit:
                    recipe_ml += f" {display_unit}"
                
                table_data.append([
                    item.product.barbuddy_code or 'N/A',
                    item.product.description or 'N/A',
                    f"{item.product.ml_in_bottle or 0:.0f}",
                    recipe_ml,
                    format_currency(cost, currency_code)
                ])
        
        table_data.append(['', '', '', 'Total', format_currency(total_cost, currency_code)])
        
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
        if secondary.method:
            elements.append(Paragraph("METHOD", heading_style))
            elements.append(Paragraph(secondary.method, styles['Normal']))
        
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
        
        # Create response with ingredient name as filename
        import re
        ingredient_name = secondary.name or "ingredient"
        # Sanitize filename - remove invalid characters
        safe_filename = re.sub(r'[^\w\s-]', '', ingredient_name).strip()
        safe_filename = re.sub(r'[-\s]+', '_', safe_filename)
        filename = f"{safe_filename}.pdf"
        
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        current_app.logger.error(f'Error generating PDF: {str(e)}', exc_info=True)
        flash(f'Error generating PDF: {str(e)}', 'error')
        return redirect(url_for('secondary.view_secondary_ingredient', id=id))


@secondary_bp.route('/secondary-ingredients/<int:id>')
@login_required
def view_secondary_ingredient(id):
    ensure_schema_updates()
    from sqlalchemy.orm import joinedload
    from utils.helpers import get_organization_filter
    org_filter = get_organization_filter(HomemadeIngredient)
    secondary = HomemadeIngredient.query.filter(org_filter).options(
        joinedload(HomemadeIngredient.ingredients).joinedload(HomemadeIngredientItem.product)
    ).filter_by(id=id).first_or_404()
    # Ensure ingredients and products are loaded
    _ = secondary.ingredients
    for item in secondary.ingredients:
        _ = item.product
    return render_template('secondary_ingredients/view.html', secondary=secondary)


@secondary_bp.route('/secondary-ingredients/add', methods=['GET', 'POST'])
@login_required
def add_secondary_ingredient():
    ensure_schema_updates()
    from utils.helpers import get_organization_filter
    prod_org_filter = get_organization_filter(Product)
    sec_org_filter = get_organization_filter(HomemadeIngredient)
    products = Product.query.filter(prod_org_filter).order_by(Product.description).all()
    existing_secondary = HomemadeIngredient.query.filter(sec_org_filter).order_by(HomemadeIngredient.name).all()
    ingredient_options = [
        {
            'label': f"{p.description} ({p.barbuddy_code})",
            'id': p.id,
            'type': 'Product',
            'code': p.barbuddy_code or 'N/A',
            'unit': p.selling_unit or 'ml',
            'cost_per_unit': p.cost_per_unit or 0.0,
            'container_volume': p.ml_in_bottle or (1 if (p.selling_unit or '').lower() == 'ml' else 0)
        }
        for p in products
    ]
    for sec in existing_secondary:
        if sec.unique_code:
            try:
                cost_per_unit = sec.calculate_cost_per_unit()
            except Exception:
                cost_per_unit = 0.0
            ingredient_options.append({
                'label': f"{sec.name} ({sec.unique_code})",
                'id': sec.id,
                'type': 'Secondary',
                'code': sec.unique_code or 'N/A',
                'unit': sec.unit or 'ml',
                'cost_per_unit': cost_per_unit,
                'container_volume': sec.total_volume_ml or 1
            })

    preset_rows = []

    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            if not name:
                flash('Name is required.')
                return redirect(url_for('secondary.add_secondary_ingredient'))
            
            try:
                total_volume_ml = float(request.form.get('total_volume_ml', 0) or 0)
            except ValueError:
                total_volume_ml = 0
            unit = request.form.get('unit', 'ml')
            method = request.form.get('method', '')

            if total_volume_ml <= 0:
                flash('Total volume must be greater than zero.')
                return redirect(url_for('secondary.add_secondary_ingredient'))

            max_id = db.session.query(db.func.max(HomemadeIngredient.id)).scalar() or 0
            counter = 1
            while True:
                unique_code = f"SEC-{max_id + counter:04d}"
                existing = HomemadeIngredient.query.filter_by(unique_code=unique_code).first()
                if not existing:
                    break
                counter += 1
                if counter > 1000:
                    unique_code = f"SEC-{int(time.time())}"
                    break

            category = request.form.get('category', '').strip() or None
            sub_category = request.form.get('sub_category', '').strip() or None
            
            homemade = HomemadeIngredient(
                name=name,
                unique_code=unique_code,
                total_volume_ml=total_volume_ml,
                unit=unit,
                method=method,
                category=category,
                sub_category=sub_category,
                organisation=(current_user.organisation.strip() if current_user.organisation and current_user.organisation.strip() else None),
                created_by=current_user.id,
                last_edited_by=current_user.id
            )
            db.session.add(homemade)
            db.session.flush()

            ingredient_labels = request.form.getlist('ingredient_label')
            ingredient_ids = request.form.getlist('ingredient_id')
            ingredient_types = request.form.getlist('ingredient_type')
            ingredient_quantities = request.form.getlist('ingredient_qty')
            ingredient_units = request.form.getlist('ingredient_unit')

            lookup = {}
            for opt in ingredient_options:
                lookup[opt['label'].lower()] = opt
                simple = opt['label'].split('(')[0].strip().lower()
                lookup.setdefault(simple, opt)

            matched = []
            for idx, label in enumerate(ingredient_labels):
                label_clean = (label or '').strip()
                if not label_clean:
                    continue
                
                option = None
                if idx < len(ingredient_ids) and ingredient_ids[idx]:
                    try:
                        ing_id = int(ingredient_ids[idx])
                        ing_type = ingredient_types[idx] if idx < len(ingredient_types) else None
                        for opt in ingredient_options:
                            if opt['id'] == ing_id and (not ing_type or opt['type'] == ing_type):
                                option = opt
                                break
                    except (ValueError, TypeError):
                        pass
                
                if not option:
                    option = lookup.get(label_clean.lower())
                
                try:
                    qty = float(ingredient_quantities[idx] or 0)
                except (ValueError, IndexError):
                    qty = 0
                unit_item = ingredient_units[idx] if idx < len(ingredient_units) and ingredient_units[idx] else 'ml'
                if not option or qty <= 0:
                    continue
                matched.append((option, qty, unit_item))

            if not matched:
                flash('Please add at least one valid ingredient.')
                db.session.rollback()
                return redirect(url_for('secondary.add_secondary_ingredient'))

            for option, qty, unit_item in matched:
                try:
                    if option['type'] == 'Secondary':
                        from utils.helpers import get_organization_filter
                        sec_filter = get_organization_filter(HomemadeIngredient)
                        source_secondary = HomemadeIngredient.query.filter(sec_filter).filter_by(id=option['id']).first()
                        if not source_secondary or not source_secondary.total_volume_ml or source_secondary.total_volume_ml <= 0:
                            continue
                        factor = qty / source_secondary.total_volume_ml
                        for component in source_secondary.ingredients:
                            base_qty = component.quantity or 0
                            if base_qty <= 0:
                                continue
                            scaled_qty = base_qty * factor
                            if scaled_qty <= 0:
                                continue
                            if not component.product_id:
                                continue
                            unit_val = component.unit or unit_item
                            quantity_ml_value = scaled_qty
                            
                            # Get product name and code for storage
                            product_name = component.product_name
                            product_code = component.product_code
                            if component.product:
                                product_name = component.product.description
                                product_code = component.product.barbuddy_code
                            
                            item = HomemadeIngredientItem(
                                homemade_id=homemade.id,
                                product_id=component.product_id,
                                quantity=scaled_qty,
                                unit=unit_val,
                                quantity_ml=quantity_ml_value,
                                product_name=product_name,
                                product_code=product_code
                            )
                            db.session.add(item)
                    else:
                        # Apply organization filter to ensure users can only add products from their organization
                        from utils.helpers import get_organization_filter
                        prod_filter = get_organization_filter(Product)
                        product = Product.query.filter(prod_filter).filter_by(id=option['id']).first()
                        if not product:
                            continue
                        quantity_ml_value = qty
                        
                        # Get product name and code for storage
                        product_name = product.description
                        product_code = product.barbuddy_code
                        
                        item = HomemadeIngredientItem(
                            homemade_id=homemade.id,
                            product_id=option['id'],
                            quantity=qty,
                            unit=unit_item,
                            quantity_ml=quantity_ml_value,
                            product_name=product_name,
                            product_code=product_code
                        )
                        db.session.add(item)
                except Exception as e:
                    current_app.logger.error(f"Error adding ingredient item: {str(e)}", exc_info=True)
                    continue

            db.session.commit()
            flash('Secondary ingredient created successfully!')
            return redirect(url_for('secondary.secondary_ingredients'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating secondary ingredient: {str(e)}", exc_info=True)
            flash(f'An error occurred while creating the secondary ingredient: {str(e)}', 'error')
            return redirect(url_for('secondary.add_secondary_ingredient'))

    return render_template(
        'secondary_ingredients/add.html',
        ingredient_options=ingredient_options,
        edit_mode=False,
        secondary=None,
        preset_rows=preset_rows
    )


@secondary_bp.route('/secondary-ingredients/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_secondary_ingredient(id):
    ensure_schema_updates()
    from sqlalchemy.orm import joinedload
    from utils.helpers import get_organization_filter
    org_filter = get_organization_filter(HomemadeIngredient)
    secondary = HomemadeIngredient.query.filter(org_filter).options(
        joinedload(HomemadeIngredient.ingredients).joinedload(HomemadeIngredientItem.product)
    ).filter_by(id=id).first_or_404()
    # Ensure ingredients and products are loaded
    _ = secondary.ingredients
    for item in secondary.ingredients:
        _ = item.product
    # Apply organization filters to ensure users only see ingredients from their organization
    from utils.helpers import get_organization_filter
    prod_org_filter = get_organization_filter(Product)
    sec_org_filter = get_organization_filter(HomemadeIngredient)
    products = Product.query.filter(prod_org_filter).order_by(Product.description).all()
    existing_secondary = HomemadeIngredient.query.filter(sec_org_filter).filter(HomemadeIngredient.id != id).order_by(HomemadeIngredient.name).all()

    ingredient_options = [
        {
            'label': f"{p.description} ({p.barbuddy_code})",
            'id': p.id,
            'type': 'Product',
            'code': p.barbuddy_code or 'N/A',
            'unit': p.selling_unit or 'ml',
            'cost_per_unit': p.cost_per_unit or 0.0,
            'container_volume': p.ml_in_bottle or (1 if (p.selling_unit or '').lower() == 'ml' else 0)
        }
        for p in products
    ]
    for sec in existing_secondary:
        if sec.unique_code:
            try:
                cost_per_unit = sec.calculate_cost_per_unit()
            except Exception:
                cost_per_unit = 0.0
            ingredient_options.append({
                'label': f"{sec.name} ({sec.unique_code})",
                'id': sec.id,
                'type': 'Secondary',
                'code': sec.unique_code or 'N/A',
                'unit': sec.unit or 'ml',
                'cost_per_unit': cost_per_unit,
                'container_volume': sec.total_volume_ml or 1
            })

    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            if not name:
                flash('Name is required.')
                return redirect(url_for('secondary.edit_secondary_ingredient', id=id))
            
            try:
                total_volume_ml = float(request.form.get('total_volume_ml', 0) or 0)
            except ValueError:
                total_volume_ml = 0
            unit = request.form.get('unit', 'ml')
            method = request.form.get('method', '')

            if total_volume_ml <= 0:
                flash('Total volume must be greater than zero.')
                return redirect(url_for('secondary.edit_secondary_ingredient', id=id))

            from utils.helpers import get_organization_filter
            org_filter = get_organization_filter(HomemadeIngredient)
            secondary = HomemadeIngredient.query.filter(org_filter).filter_by(id=id).first_or_404()
            
            secondary.name = name
            secondary.total_volume_ml = total_volume_ml
            secondary.unit = unit
            secondary.method = method
            secondary.category = request.form.get('category', '').strip() or None
            secondary.sub_category = request.form.get('sub_category', '').strip() or None
            secondary.last_edited_by = current_user.id
            secondary.last_edited_at = datetime.utcnow()
            
            # Update organization if user's organization changed (normalized)
            if current_user.organisation and current_user.organisation.strip():
                secondary.organisation = current_user.organisation.strip()

            for item in secondary.ingredients:
                db.session.delete(item)
            db.session.flush()

            ingredient_labels = request.form.getlist('ingredient_label')
            ingredient_ids = request.form.getlist('ingredient_id')
            ingredient_types = request.form.getlist('ingredient_type')
            ingredient_quantities = request.form.getlist('ingredient_qty')
            ingredient_units = request.form.getlist('ingredient_unit')

            lookup = {}
            for opt in ingredient_options:
                lookup[opt['label'].lower()] = opt
                simple = opt['label'].split('(')[0].strip().lower()
                lookup.setdefault(simple, opt)

            matched = []
            for idx, label in enumerate(ingredient_labels):
                label_clean = (label or '').strip()
                if not label_clean:
                    continue
                
                option = None
                if idx < len(ingredient_ids) and ingredient_ids[idx]:
                    try:
                        ing_id = int(ingredient_ids[idx])
                        ing_type = ingredient_types[idx] if idx < len(ingredient_types) else None
                        for opt in ingredient_options:
                            if opt['id'] == ing_id and (not ing_type or opt['type'] == ing_type):
                                option = opt
                                break
                    except (ValueError, TypeError):
                        pass
                
                if not option:
                    option = lookup.get(label_clean.lower())
                
                try:
                    qty = float(ingredient_quantities[idx] or 0)
                except (ValueError, IndexError):
                    qty = 0
                unit_item = ingredient_units[idx] if idx < len(ingredient_units) and ingredient_units[idx] else 'ml'
                
                # Validate that we have both a valid option and a positive quantity
                if not option:
                    current_app.logger.warning(f"Ingredient not found for label: {label_clean}")
                    continue
                if qty <= 0:
                    current_app.logger.warning(f"Invalid quantity {qty} for ingredient: {label_clean}")
                    continue
                    
                matched.append((option, qty, unit_item))

            if not matched:
                flash('Please add at least one valid ingredient with a quantity greater than zero.')
                db.session.rollback()
                return redirect(url_for('secondary.edit_secondary_ingredient', id=id))

            items_added = 0
            for option, qty, unit_item in matched:
                try:
                    if option['type'] == 'Secondary':
                        from utils.helpers import get_organization_filter
                        sec_filter = get_organization_filter(HomemadeIngredient)
                        source_secondary = HomemadeIngredient.query.filter(sec_filter).filter_by(id=option['id']).first()
                        if not source_secondary or not source_secondary.total_volume_ml or source_secondary.total_volume_ml <= 0:
                            current_app.logger.warning(f"Invalid secondary ingredient source: {option['id']}")
                            continue
                        factor = qty / source_secondary.total_volume_ml
                        for component in source_secondary.ingredients:
                            base_qty = component.quantity or 0
                            if base_qty <= 0:
                                continue
                            scaled_qty = base_qty * factor
                            if scaled_qty <= 0:
                                continue
                            if not component.product_id:
                                continue
                            unit_val = component.unit or unit_item
                            quantity_ml_value = scaled_qty
                            
                            # Get product name and code for storage
                            product_name = component.product_name
                            product_code = component.product_code
                            if component.product:
                                product_name = component.product.description
                                product_code = component.product.barbuddy_code
                            
                            item = HomemadeIngredientItem(
                                homemade_id=secondary.id,
                                product_id=component.product_id,
                                quantity=scaled_qty,
                                unit=unit_val,
                                quantity_ml=quantity_ml_value,
                                product_name=product_name,
                                product_code=product_code
                            )
                            db.session.add(item)
                            items_added += 1
                    else:
                        from utils.helpers import get_organization_filter
                        prod_filter = get_organization_filter(Product)
                        product = Product.query.filter(prod_filter).filter_by(id=option['id']).first()
                        if not product:
                            current_app.logger.warning(f"Product not found: {option['id']}")
                            continue
                        quantity_ml_value = qty
                        
                        # Get product name and code for storage
                        product_name = product.description
                        product_code = product.barbuddy_code
                        
                        item = HomemadeIngredientItem(
                            homemade_id=secondary.id,
                            product_id=option['id'],
                            quantity=qty,
                            unit=unit_item,
                            quantity_ml=quantity_ml_value,
                            product_name=product_name,
                            product_code=product_code
                        )
                        db.session.add(item)
                        items_added += 1
                except Exception as e:
                    current_app.logger.error(f"Error adding ingredient item: {str(e)}", exc_info=True)
                    continue

            if items_added == 0:
                flash('No valid ingredients were added. Please check that ingredients are selected and quantities are greater than zero.')
                db.session.rollback()
                return redirect(url_for('secondary.edit_secondary_ingredient', id=id))

            db.session.commit()
            # Expire and reload the secondary ingredient to ensure ingredients are loaded
            db.session.expire(secondary)
            db.session.refresh(secondary)
            # Force reload of ingredients relationship
            _ = secondary.ingredients
            for item in secondary.ingredients:
                _ = item.product
            flash(f'Secondary ingredient updated successfully! {items_added} ingredient(s) added.')
            scroll_to = request.args.get('scroll_to') or request.form.get('scroll_to')
            if scroll_to:
                return redirect(url_for('secondary.secondary_ingredients') + f'#row_{scroll_to}')
            return redirect(url_for('secondary.secondary_ingredients'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating secondary ingredient: {str(e)}", exc_info=True)
            flash(f'An error occurred while updating the secondary ingredient: {str(e)}', 'error')
            scroll_to = request.args.get('scroll_to') or request.form.get('scroll_to')
            if scroll_to:
                return redirect(url_for('secondary.edit_secondary_ingredient', id=id, scroll_to=scroll_to))
            return redirect(url_for('secondary.edit_secondary_ingredient', id=id))

    preset_rows = []
    for component in secondary.ingredients:
        if component.product:
            # Match the exact label format used in ingredient_options
            description = component.product.description or ''
            code = component.product.barbuddy_code or 'N/A'
            label = f"{description} ({code})"
            preset_rows.append({
                'label': label.strip(),
                'id': component.product_id,
                'type': 'Product',
                'qty': float(component.quantity or 0),
                'unit': component.unit or 'ml',
                'code': code
            })

    scroll_to = request.args.get('scroll_to')
    return render_template('secondary_ingredients/edit.html', ingredient_options=ingredient_options, secondary=secondary, preset_rows=preset_rows, scroll_to=scroll_to)


@secondary_bp.route('/secondary-ingredients/<int:id>/delete', methods=['POST'])
@login_required
def delete_secondary_ingredient(id):
    from utils.helpers import get_organization_filter
    org_filter = get_organization_filter(HomemadeIngredient)
    secondary = HomemadeIngredient.query.filter(org_filter).filter_by(id=id).first_or_404()
    db.session.delete(secondary)
    db.session.commit()
    flash('Secondary ingredient deleted successfully!')
    return redirect(url_for('secondary.secondary_ingredients'))


@secondary_bp.route('/secondary-ingredients/<int:id>/link-ingredient', methods=['GET', 'POST'])
@login_required
def link_ingredient_to_secondary(id):
    """Link a product/ingredient to a secondary ingredient via web interface"""
    from utils.helpers import get_organization_filter
    org_filter = get_organization_filter(HomemadeIngredient)
    secondary = HomemadeIngredient.query.filter(org_filter).filter_by(id=id).first_or_404()
    
    if request.method == 'POST':
        try:
            product_id = request.form.get('product_id', type=int)
            quantity = request.form.get('quantity', type=float)
            unit = request.form.get('unit', 'ml')
            
            if not product_id or not quantity or quantity <= 0:
                flash('Please provide a valid product and quantity.')
                return redirect(url_for('secondary.link_ingredient_to_secondary', id=id))
            
            # Apply organization filter to ensure users can only link products from their organization
            prod_filter = get_organization_filter(Product)
            product = Product.query.filter(prod_filter).filter_by(id=product_id).first()
            if not product:
                flash('Product not found.')
                return redirect(url_for('secondary.link_ingredient_to_secondary', id=id))
            
            # Check if link already exists
            existing = HomemadeIngredientItem.query.filter_by(
                homemade_id=id,
                product_id=product_id
            ).first()
            
            if existing:
                existing.quantity = quantity
                existing.unit = unit
                existing.quantity_ml = quantity
                flash(f'Updated link: {product.description} ({quantity} {unit})')
            else:
                item = HomemadeIngredientItem(
                    homemade_id=id,
                    product_id=product_id,
                    quantity=quantity,
                    unit=unit,
                    quantity_ml=quantity
                )
                db.session.add(item)
                flash(f'Successfully linked: {product.description} ({quantity} {unit})')
            
            db.session.commit()
            return redirect(url_for('secondary.view_secondary_ingredient', id=id))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error linking ingredient: {str(e)}", exc_info=True)
            flash(f'An error occurred: {str(e)}', 'error')
            return redirect(url_for('secondary.link_ingredient_to_secondary', id=id))
    
    # GET request - show form
    products = Product.query.order_by(Product.description).all()
    existing_items = HomemadeIngredientItem.query.filter_by(homemade_id=id).all()
    
    return render_template('secondary_ingredients/link_ingredient.html', 
                         secondary=secondary, 
                         products=products,
                         existing_items=existing_items)


@secondary_bp.route('/secondary-ingredients/item/<int:id>/delete', methods=['POST'])
@login_required
def delete_ingredient_item(id):
    """Delete an individual ingredient item from a secondary ingredient"""
    item = HomemadeIngredientItem.query.get_or_404(id)
    secondary_id = item.homemade_id
    db.session.delete(item)
    db.session.commit()
    flash('Ingredient removed successfully!')
    return redirect(url_for('secondary.link_ingredient_to_secondary', id=secondary_id))

