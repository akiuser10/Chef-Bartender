"""
Purchase Request Blueprint
Handles purchase request creation and management
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app
from flask_login import login_required, current_user
from extensions import db
from models import Product, PurchaseRequest, PurchaseItem
from utils.db_helpers import ensure_schema_updates
from utils.permissions import role_required
from utils.helpers import get_organization_filter
from datetime import datetime
import uuid

purchase_bp = Blueprint('purchase', __name__)


@purchase_bp.route('/purchase', methods=['GET'])
@login_required
@role_required(['Chef', 'Bartender', 'Manager'])
def purchase():
    """Display purchase request creation page"""
    try:
        # Get all products from master list for dropdown
        org_filter = get_organization_filter(Product)
        products = Product.query.filter(org_filter).all()
        
        # Format products for dropdown
        product_options = []
        for product in products:
            product_options.append({
                'id': int(product.id),
                'code': product.barbuddy_code or 'N/A',
                'description': product.description or '',
                'quantity': float(product.ml_in_bottle or 0),
                'supplier': product.supplier or 'N/A',
                'sub_category': product.sub_category or 'Other',
                'cost_per_unit': float(product.cost_per_unit or 0.0)
            })
        
        from utils.currency import get_currency_info
        currency_info = get_currency_info(current_user.currency or 'AED')
        
        return render_template('purchase/purchase.html', 
                             product_options=product_options,
                             user_currency_info=currency_info)
    except Exception as e:
        flash(f'Error loading purchase page: {str(e)}', 'error')
        current_app.logger.error(f'Error in purchase: {str(e)}', exc_info=True)
        return redirect(url_for('main.index'))


@purchase_bp.route('/purchase/create', methods=['POST'])
@login_required
@role_required(['Chef', 'Bartender', 'Manager'])
def create_purchase_request():
    """Create a new purchase request"""
    try:
        ensure_schema_updates()
        
        # Generate unique order number
        order_number = f"PO-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        # Create purchase request
        purchase_request = PurchaseRequest(
            order_number=order_number,
            ordered_date=datetime.utcnow(),
            status='Pending',
            organisation=(current_user.organisation.strip() if current_user.organisation and current_user.organisation.strip() else None),
            created_by=current_user.id
        )
        db.session.add(purchase_request)
        db.session.flush()  # Get the ID
        
        # Process items from form
        item_count = 0
        item_index = 0
        
        while True:
            # Check if we have more items
            description_key = f'item_description_{item_index}'
            if description_key not in request.form:
                break
            
            description = request.form.get(description_key, '').strip()
            if not description:
                item_index += 1
                continue
            
            # Get product ID if available
            product_id = request.form.get(f'item_product_id_{item_index}', '')
            try:
                product_id = int(product_id) if product_id else None
            except (ValueError, TypeError):
                product_id = None
            
            # Get other fields
            code = request.form.get(f'item_code_{item_index}', '').strip()
            quantity = float(request.form.get(f'item_quantity_{item_index}', 0) or 0)
            supplier = request.form.get(f'item_supplier_{item_index}', '').strip() or 'N/A'
            sub_category = request.form.get(f'item_sub_category_{item_index}', '').strip() or 'Other'
            cost_per_unit = float(request.form.get(f'item_cost_per_unit_{item_index}', 0) or 0)
            order_quantity = float(request.form.get(f'item_order_quantity_{item_index}', 0) or 0)
            
            # Only add item if order_quantity > 0
            if order_quantity > 0:
                purchase_item = PurchaseItem(
                    purchase_request_id=purchase_request.id,
                    product_id=product_id,
                    code=code,
                    description=description,
                    quantity=quantity,
                    supplier=supplier,
                    sub_category=sub_category,
                    cost_per_unit=cost_per_unit,
                    order_quantity=order_quantity
                )
                db.session.add(purchase_item)
                item_count += 1
            
            item_index += 1
        
        if item_count == 0:
            db.session.rollback()
            flash('Please add at least one item with order quantity greater than 0.', 'error')
            return redirect(url_for('purchase.purchase'))
        
        db.session.commit()
        flash(f'Purchase request {order_number} created successfully!', 'success')
        return redirect(url_for('purchase.order_list'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating purchase request: {str(e)}', 'error')
        current_app.logger.error(f'Error in create_purchase_request: {str(e)}', exc_info=True)
        return redirect(url_for('purchase.purchase'))


@purchase_bp.route('/purchase/to-order', methods=['GET'])
@login_required
@role_required(['Purchase Manager', 'Manager'])
def to_order():
    """Display purchase requests for Purchase Manager and Manager"""
    try:
        # Get all pending purchase requests
        org_filter = get_organization_filter(PurchaseRequest)
        purchase_requests = PurchaseRequest.query.filter(org_filter).filter_by(status='Pending').order_by(PurchaseRequest.ordered_date.desc()).all()
        
        from utils.currency import get_currency_info
        currency_info = get_currency_info(current_user.currency or 'AED')
        
        return render_template('purchase/to_order.html', 
                             purchase_requests=purchase_requests,
                             user_currency_info=currency_info)
    except Exception as e:
        flash(f'Error loading purchase requests: {str(e)}', 'error')
        current_app.logger.error(f'Error in to_order: {str(e)}', exc_info=True)
        return redirect(url_for('main.index'))


@purchase_bp.route('/purchase/order-list', methods=['GET'])
@login_required
@role_required(['Chef', 'Bartender', 'Manager'])
def order_list():
    """Display purchase orders created by the current user (Chef, Bartender, Manager)"""
    try:
        # Get all purchase requests created by the current user
        org_filter = get_organization_filter(PurchaseRequest)
        purchase_requests = PurchaseRequest.query.filter(org_filter).filter_by(created_by=current_user.id).order_by(PurchaseRequest.ordered_date.desc()).all()
        
        from utils.currency import get_currency_info
        currency_info = get_currency_info(current_user.currency or 'AED')
        
        return render_template('purchase/order_list.html', 
                             purchase_requests=purchase_requests,
                             user_currency_info=currency_info)
    except Exception as e:
        flash(f'Error loading order list: {str(e)}', 'error')
        current_app.logger.error(f'Error in order_list: {str(e)}', exc_info=True)
        return redirect(url_for('main.index'))


@purchase_bp.route('/purchase/<int:purchase_id>/view', methods=['GET'])
@login_required
@role_required(['Purchase Manager', 'Manager'])
def view_purchase_request(purchase_id):
    """View details of a purchase request"""
    try:
        org_filter = get_organization_filter(PurchaseRequest)
        purchase_request = PurchaseRequest.query.filter(org_filter).filter_by(id=purchase_id).first_or_404()
        
        from utils.currency import get_currency_info
        currency_info = get_currency_info(current_user.currency or 'AED')
        
        return render_template('purchase/view.html', 
                             purchase_request=purchase_request,
                             user_currency_info=currency_info)
    except Exception as e:
        flash(f'Error loading purchase request: {str(e)}', 'error')
        current_app.logger.error(f'Error in view_purchase_request: {str(e)}', exc_info=True)
        return redirect(url_for('purchase.to_order'))


@purchase_bp.route('/purchase/<int:purchase_id>/view-order', methods=['GET'])
@login_required
@role_required(['Chef', 'Bartender', 'Manager'])
def view_order(purchase_id):
    """View details of a purchase order (for Chef, Bartender, Manager)"""
    try:
        # Only allow users to view their own purchase orders
        org_filter = get_organization_filter(PurchaseRequest)
        purchase_request = PurchaseRequest.query.filter(org_filter).filter_by(id=purchase_id, created_by=current_user.id).first_or_404()
        
        from utils.currency import get_currency_info
        currency_info = get_currency_info(current_user.currency or 'AED')
        
        return render_template('purchase/view_order.html', 
                             purchase_request=purchase_request,
                             user_currency_info=currency_info)
    except Exception as e:
        flash(f'Error loading purchase order: {str(e)}', 'error')
        current_app.logger.error(f'Error in view_order: {str(e)}', exc_info=True)
        return redirect(url_for('purchase.order_list'))

