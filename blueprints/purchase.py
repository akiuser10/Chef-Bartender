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
        
        # Determine initial status based on user role
        # Chef/Bartender orders need Manager approval first
        # Manager orders go directly to Purchase Manager
        if current_user.user_role in ['Chef', 'Bartender']:
            initial_status = 'Pending Manager Approval'
        else:
            initial_status = 'Pending'
        
        # Create purchase request
        purchase_request = PurchaseRequest(
            order_number=order_number,
            ordered_date=datetime.utcnow(),
            status=initial_status,
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
        
        # Check if user wants to download PDF
        download_pdf = request.form.get('download_pdf', '0') == '1'
        if download_pdf:
            return redirect(url_for('purchase.export_new_purchase_pdf', purchase_id=purchase_request.id))
        
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
        from sqlalchemy.orm import joinedload
        org_filter = get_organization_filter(PurchaseRequest)
        
        # Purchase Manager sees only orders approved by Manager (status = 'Pending')
        # Manager sees orders pending their approval (status = 'Pending Manager Approval')
        # Use joinedload to ensure creator relationship is loaded
        if current_user.user_role == 'Purchase Manager':
            # Show only orders approved by Manager (ready for Purchase Manager to process)
            purchase_requests = PurchaseRequest.query.filter(org_filter).filter_by(status='Pending').options(
                joinedload(PurchaseRequest.creator)
            ).order_by(PurchaseRequest.ordered_date.desc()).all()
        else:
            # Manager sees only orders pending their approval
            purchase_requests = PurchaseRequest.query.filter(org_filter).filter_by(status='Pending Manager Approval').options(
                joinedload(PurchaseRequest.creator)
            ).order_by(PurchaseRequest.ordered_date.desc()).all()
        
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
@role_required(['Chef', 'Bartender', 'Manager', 'Purchase Manager'])
def order_list():
    """Display purchase orders - all orders for Purchase Manager, user's own orders for others"""
    try:
        from sqlalchemy.orm import joinedload
        org_filter = get_organization_filter(PurchaseRequest)
        
        # Purchase Manager sees all orders in the organization
        # Others see only their own orders
        # Use joinedload to ensure creator relationship is loaded
        if current_user.user_role == 'Purchase Manager':
            purchase_requests = PurchaseRequest.query.filter(org_filter).options(
                joinedload(PurchaseRequest.creator)
            ).order_by(PurchaseRequest.ordered_date.desc()).all()
        else:
            purchase_requests = PurchaseRequest.query.filter(org_filter).filter_by(created_by=current_user.id).options(
                joinedload(PurchaseRequest.creator)
            ).order_by(PurchaseRequest.ordered_date.desc()).all()
        
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
        
        # Manager can only view orders pending their approval
        if current_user.user_role == 'Manager' and purchase_request.status != 'Pending Manager Approval':
            flash('This order is not pending your approval.', 'error')
            return redirect(url_for('purchase.to_order'))
        
        # Purchase Manager can only view orders approved by Manager
        if current_user.user_role == 'Purchase Manager' and purchase_request.status != 'Pending':
            flash('This order is not ready for processing.', 'error')
            return redirect(url_for('purchase.to_order'))
        
        from utils.currency import get_currency_info
        currency_info = get_currency_info(current_user.currency or 'AED')
        
        return render_template('purchase/view.html', 
                             purchase_request=purchase_request,
                             user_currency_info=currency_info)
    except Exception as e:
        flash(f'Error loading purchase request: {str(e)}', 'error')
        current_app.logger.error(f'Error in view_purchase_request: {str(e)}', exc_info=True)
        return redirect(url_for('purchase.to_order'))


@purchase_bp.route('/purchase/<int:purchase_id>/approve', methods=['POST'])
@login_required
@role_required(['Manager'])
def approve_purchase_request(purchase_id):
    """Manager approves a purchase request, with optional modifications"""
    try:
        ensure_schema_updates()
        org_filter = get_organization_filter(PurchaseRequest)
        purchase_request = PurchaseRequest.query.filter(org_filter).filter_by(id=purchase_id).first_or_404()
        
        # Only allow approval of orders pending Manager approval
        if purchase_request.status != 'Pending Manager Approval':
            flash('This order is not pending your approval.', 'error')
            return redirect(url_for('purchase.to_order'))
        
        # Process item modifications
        # Get all items and check for updates
        items_to_delete = []
        for item in purchase_request.items:
            item_id = str(item.id)
            new_quantity_key = f'order_quantity_{item_id}'
            
            if new_quantity_key in request.form:
                # Update order quantity
                try:
                    new_quantity = float(request.form.get(new_quantity_key, 0) or 0)
                    if new_quantity > 0:
                        item.order_quantity = new_quantity
                    else:
                        # If quantity is 0 or negative, mark item for deletion
                        items_to_delete.append(item)
                except (ValueError, TypeError):
                    pass  # Skip invalid values
        
        # Delete items with quantity 0 or less
        for item in items_to_delete:
            db.session.delete(item)
        
        # Check if any items remain
        remaining_items = [item for item in purchase_request.items if item not in items_to_delete]
        if not remaining_items:
            db.session.rollback()
            flash('Cannot approve order with no items. Please add at least one item.', 'error')
            return redirect(url_for('purchase.view_purchase_request', purchase_id=purchase_id))
        
        # Update status to 'Pending' (ready for Purchase Manager)
        purchase_request.status = 'Pending'
        
        db.session.commit()
        flash('Purchase request approved and forwarded to Purchase Manager!', 'success')
        return redirect(url_for('purchase.to_order'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error approving purchase request: {str(e)}', 'error')
        current_app.logger.error(f'Error in approve_purchase_request: {str(e)}', exc_info=True)
        return redirect(url_for('purchase.view_purchase_request', purchase_id=purchase_id))


@purchase_bp.route('/purchase/<int:purchase_id>/view-order', methods=['GET'])
@login_required
@role_required(['Chef', 'Bartender', 'Manager', 'Purchase Manager'])
def view_order(purchase_id):
    """View details of a purchase order"""
    try:
        org_filter = get_organization_filter(PurchaseRequest)
        
        # Purchase Manager can view any order, others can only view their own
        if current_user.user_role == 'Purchase Manager':
            purchase_request = PurchaseRequest.query.filter(org_filter).filter_by(id=purchase_id).first_or_404()
        else:
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


@purchase_bp.route('/purchase/<int:purchase_id>/update-status', methods=['POST'])
@login_required
def update_status(purchase_id):
    """Update purchase request status"""
    try:
        ensure_schema_updates()
        org_filter = get_organization_filter(PurchaseRequest)
        purchase_request = PurchaseRequest.query.filter(org_filter).filter_by(id=purchase_id).first_or_404()
        
        new_status = request.form.get('status', '').strip()
        if not new_status:
            flash('Status is required.', 'error')
            return redirect(url_for('purchase.view_purchase_request', purchase_id=purchase_id))
        
        # Permission checks
        if new_status == 'Order Placed':
            # Purchase Manager can set to Order Placed from any status
            # Manager can revert from Order Received to Order Placed
            if current_user.user_role == 'Purchase Manager':
                # Purchase Manager can change to Order Placed from any status
                pass
            elif current_user.user_role == 'Manager':
                # Manager can only revert from Order Received to Order Placed
                if purchase_request.status != 'Order Received':
                    flash('Managers can only revert from Order Received to Order Placed.', 'error')
                    return redirect(url_for('purchase.view_order', purchase_id=purchase_id))
            else:
                flash('You do not have permission to change status to Order Placed.', 'error')
                if current_user.user_role == 'Purchase Manager':
                    return redirect(url_for('purchase.view_purchase_request', purchase_id=purchase_id))
                else:
                    return redirect(url_for('purchase.view_order', purchase_id=purchase_id))
        elif new_status == 'Order Received':
            # Chef, Bartender, Manager, and Purchase Manager can set to Order Received
            if current_user.user_role not in ['Chef', 'Bartender', 'Manager', 'Purchase Manager']:
                flash('You do not have permission to change status to Order Received.', 'error')
                if current_user.user_role == 'Purchase Manager':
                    return redirect(url_for('purchase.view_purchase_request', purchase_id=purchase_id))
                else:
                    return redirect(url_for('purchase.view_order', purchase_id=purchase_id))
        elif new_status == 'Order Cancelled':
            # Chef, Bartender, and Manager can cancel orders (Purchase Manager cannot)
            if current_user.user_role not in ['Chef', 'Bartender', 'Manager']:
                flash('You do not have permission to cancel orders.', 'error')
                if current_user.user_role == 'Purchase Manager':
                    return redirect(url_for('purchase.view_purchase_request', purchase_id=purchase_id))
                else:
                    return redirect(url_for('purchase.view_order', purchase_id=purchase_id))
        
        purchase_request.status = new_status
        db.session.commit()
        
        flash(f'Status updated to {new_status} successfully!', 'success')
        
        # Redirect based on user role
        if current_user.user_role == 'Purchase Manager':
            return redirect(url_for('purchase.view_purchase_request', purchase_id=purchase_id))
        else:
            return redirect(url_for('purchase.view_order', purchase_id=purchase_id))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating status: {str(e)}', 'error')
        current_app.logger.error(f'Error in update_status: {str(e)}', exc_info=True)
        return redirect(url_for('purchase.to_order'))


@purchase_bp.route('/purchase/<int:purchase_id>/update-supplier-status', methods=['POST'])
@login_required
def update_supplier_status(purchase_id):
    """Update status for a specific supplier"""
    try:
        ensure_schema_updates()
        org_filter = get_organization_filter(PurchaseRequest)
        
        # Purchase Manager can update any order, others can only update their own
        if current_user.user_role == 'Purchase Manager':
            purchase_request = PurchaseRequest.query.filter(org_filter).filter_by(id=purchase_id).first_or_404()
        else:
            purchase_request = PurchaseRequest.query.filter(org_filter).filter_by(id=purchase_id, created_by=current_user.id).first_or_404()
        
        supplier = request.form.get('supplier', '').strip()
        new_status = request.form.get('status', '').strip()
        
        if not supplier or not new_status:
            flash('Supplier and status are required.', 'error')
            if current_user.user_role == 'Purchase Manager':
                return redirect(url_for('purchase.view_purchase_request', purchase_id=purchase_id))
            else:
                return redirect(url_for('purchase.view_order', purchase_id=purchase_id))
        
        # Permission checks (same as regular status update)
        if new_status == 'Order Placed':
            if current_user.user_role == 'Purchase Manager':
                pass
            elif current_user.user_role == 'Manager':
                current_supplier_status = purchase_request.get_supplier_status(supplier)
                if current_supplier_status != 'Order Received':
                    flash('Managers can only revert from Order Received to Order Placed.', 'error')
                    if current_user.user_role == 'Purchase Manager':
                        return redirect(url_for('purchase.view_purchase_request', purchase_id=purchase_id))
                    else:
                        return redirect(url_for('purchase.view_order', purchase_id=purchase_id))
            else:
                flash('You do not have permission to change status to Order Placed.', 'error')
                if current_user.user_role == 'Purchase Manager':
                    return redirect(url_for('purchase.view_purchase_request', purchase_id=purchase_id))
                else:
                    return redirect(url_for('purchase.view_order', purchase_id=purchase_id))
        elif new_status == 'Order Received':
            if current_user.user_role not in ['Chef', 'Bartender', 'Manager', 'Purchase Manager']:
                flash('You do not have permission to change status to Order Received.', 'error')
                if current_user.user_role == 'Purchase Manager':
                    return redirect(url_for('purchase.view_purchase_request', purchase_id=purchase_id))
                else:
                    return redirect(url_for('purchase.view_order', purchase_id=purchase_id))
        elif new_status == 'Order Cancelled':
            # Chef, Bartender, and Manager can cancel orders (Purchase Manager cannot)
            if current_user.user_role not in ['Chef', 'Bartender', 'Manager']:
                flash('You do not have permission to cancel orders.', 'error')
                if current_user.user_role == 'Purchase Manager':
                    return redirect(url_for('purchase.view_purchase_request', purchase_id=purchase_id))
                else:
                    return redirect(url_for('purchase.view_order', purchase_id=purchase_id))
            
            # Check if order is already placed - cannot cancel once placed
            current_supplier_status = purchase_request.get_supplier_status(supplier)
            if current_supplier_status in ['Order Placed', 'Order Received']:
                flash('Cannot cancel order once it has been placed or received.', 'error')
                if current_user.user_role == 'Purchase Manager':
                    return redirect(url_for('purchase.view_purchase_request', purchase_id=purchase_id))
                else:
                    return redirect(url_for('purchase.view_order', purchase_id=purchase_id))
        
        purchase_request.set_supplier_status(supplier, new_status)
        db.session.commit()
        
        flash(f'Status for {supplier} updated to {new_status} successfully!', 'success')
        
        # Redirect based on user role
        if current_user.user_role == 'Purchase Manager':
            return redirect(url_for('purchase.view_purchase_request', purchase_id=purchase_id))
        else:
            return redirect(url_for('purchase.view_order', purchase_id=purchase_id))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating supplier status: {str(e)}', 'error')
        current_app.logger.error(f'Error in update_supplier_status: {str(e)}', exc_info=True)
        if current_user.user_role == 'Purchase Manager':
            return redirect(url_for('purchase.view_purchase_request', purchase_id=purchase_id))
        else:
            return redirect(url_for('purchase.view_order', purchase_id=purchase_id))


@purchase_bp.route('/purchase/<int:purchase_id>/update-quantities', methods=['POST'])
@login_required
@role_required(['Chef', 'Bartender', 'Manager', 'Purchase Manager'])
def update_quantities(purchase_id):
    """Update quantity received for purchase items"""
    try:
        ensure_schema_updates()
        org_filter = get_organization_filter(PurchaseRequest)
        
        # Purchase Manager can update any order, others can only update their own
        if current_user.user_role == 'Purchase Manager':
            purchase_request = PurchaseRequest.query.filter(org_filter).filter_by(id=purchase_id).first_or_404()
        else:
            purchase_request = PurchaseRequest.query.filter(org_filter).filter_by(id=purchase_id, created_by=current_user.id).first_or_404()
        
        # Get supplier from form (if provided, for supplier-specific updates)
        supplier = request.form.get('supplier', '').strip()
        
        # If supplier is specified, check that supplier's status
        if supplier:
            supplier_status = purchase_request.get_supplier_status(supplier)
            if supplier_status != 'Order Received':
                flash(f'Quantities for {supplier} can only be updated when status is Order Received.', 'error')
                if current_user.user_role == 'Purchase Manager':
                    return redirect(url_for('purchase.view_purchase_request', purchase_id=purchase_id))
                else:
                    return redirect(url_for('purchase.view_order', purchase_id=purchase_id))
        else:
            # Fallback to main status for backward compatibility
            if purchase_request.status != 'Order Received':
                flash('Quantities can only be updated when status is Order Received.', 'error')
                if current_user.user_role == 'Purchase Manager':
                    return redirect(url_for('purchase.view_purchase_request', purchase_id=purchase_id))
                else:
                    return redirect(url_for('purchase.view_order', purchase_id=purchase_id))
        
        # Update quantities for each item
        for item in purchase_request.items:
            qty_key = f'quantity_received_{item.id}'
            if qty_key in request.form:
                try:
                    qty_received = float(request.form.get(qty_key, 0) or 0)
                    item.quantity_received = qty_received if qty_received >= 0 else None
                except (ValueError, TypeError):
                    item.quantity_received = None
        
        # Update invoice number and invoice value per supplier if provided
        # Check for supplier-specific invoice fields (format: invoice_number_{supplier} and invoice_value_{supplier})
        suppliers = set(item.supplier or 'N/A' for item in purchase_request.items)
        for supplier in suppliers:
            invoice_num_key = f'invoice_number_{supplier}'
            invoice_val_key = f'invoice_value_{supplier}'
            
            invoice_number = None
            invoice_value = None
            
            if invoice_num_key in request.form:
                invoice_number = request.form.get(invoice_num_key, '').strip() or None
            if invoice_val_key in request.form:
                try:
                    invoice_val = request.form.get(invoice_val_key, '').strip()
                    invoice_value = float(invoice_val) if invoice_val else None
                except (ValueError, TypeError):
                    invoice_value = None
            
            if invoice_number is not None or invoice_value is not None:
                purchase_request.set_supplier_invoice(supplier, invoice_number, invoice_value)
        
        # Also handle legacy invoice fields (for backward compatibility)
        if 'invoice_number' in request.form and not any(f'invoice_number_{s}' in request.form for s in suppliers):
            purchase_request.invoice_number = request.form.get('invoice_number', '').strip() or None
        if 'invoice_value' in request.form and not any(f'invoice_value_{s}' in request.form for s in suppliers):
            try:
                invoice_val = request.form.get('invoice_value', '').strip()
                purchase_request.invoice_value = float(invoice_val) if invoice_val else None
            except (ValueError, TypeError):
                purchase_request.invoice_value = None
        
        # Set received date for the supplier if quantities were updated
        if supplier:
            # Check if any quantities were actually updated (not all None/0)
            has_quantities = any(
                item.quantity_received and item.quantity_received > 0 
                for item in purchase_request.items 
                if item.supplier == supplier
            )
            if has_quantities:
                purchase_request.set_supplier_received_date(supplier)
        
        db.session.commit()
        flash('Quantities and invoice information updated successfully!', 'success')
        
        # Create supplier anchor for scroll position (sanitize supplier name for URL)
        supplier_anchor = ''
        if supplier:
            supplier_anchor = '#' + supplier.replace(' ', '_').replace('/', '_').replace('\\', '_').replace('.', '_').replace('-', '_')
            supplier_anchor = 'supplier_' + supplier_anchor.lstrip('#')
            supplier_anchor = '#' + supplier_anchor
        
        # Redirect based on user role with supplier anchor
        if current_user.user_role == 'Purchase Manager':
            return redirect(url_for('purchase.view_purchase_request', purchase_id=purchase_id) + supplier_anchor)
        else:
            return redirect(url_for('purchase.view_order', purchase_id=purchase_id) + supplier_anchor)
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating quantities: {str(e)}', 'error')
        current_app.logger.error(f'Error in update_quantities: {str(e)}', exc_info=True)
        if current_user.user_role == 'Purchase Manager':
            return redirect(url_for('purchase.view_purchase_request', purchase_id=purchase_id))
        else:
            return redirect(url_for('purchase.view_order', purchase_id=purchase_id))



@purchase_bp.route('/purchase/<int:purchase_id>/export-pdf')
@login_required
@role_required(['Chef', 'Bartender', 'Manager', 'Purchase Manager'])
def export_purchase_pdf(purchase_id):
    """Export purchase order details to PDF"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from io import BytesIO
        from flask import make_response
        from sqlalchemy.orm import joinedload
        from utils.currency import get_currency_info, format_currency
        import re
        
        ensure_schema_updates()
        org_filter = get_organization_filter(PurchaseRequest)
        
        # Purchase Manager can view any order, others can only view their own
        if current_user.user_role == 'Purchase Manager':
            purchase_request = PurchaseRequest.query.filter(org_filter).filter_by(id=purchase_id).options(
                joinedload(PurchaseRequest.items),
                joinedload(PurchaseRequest.creator)
            ).first_or_404()
        else:
            purchase_request = PurchaseRequest.query.filter(org_filter).filter_by(id=purchase_id, created_by=current_user.id).options(
                joinedload(PurchaseRequest.items),
                joinedload(PurchaseRequest.creator)
            ).first_or_404()
        
        # Get currency code
        currency_code = current_user.currency or 'AED'
        currency_info = get_currency_info(currency_code)
        
        # Group items by supplier
        suppliers = {}
        for item in purchase_request.items:
            supplier_name = item.supplier or 'N/A'
            if supplier_name not in suppliers:
                suppliers[supplier_name] = []
            suppliers[supplier_name].append(item)
        
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
        elements.append(Paragraph("PURCHASE ORDER DETAILS", title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Order Information
        info_data = [
            ['Order Number:', purchase_request.order_number],
            ['Ordered Date & Time:', purchase_request.ordered_date.strftime('%Y-%m-%d %H:%M:%S')],
        ]
        
        if purchase_request.creator:
            creator_name = f"{purchase_request.creator.first_name or ''} {purchase_request.creator.last_name or ''}".strip()
            if creator_name:
                info_data.append(['Ordered By:', creator_name])
        
        info_table = Table(info_data, colWidths=[2.5*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Process each supplier
        for supplier_name, supplier_items in suppliers.items():
            supplier_status = purchase_request.get_supplier_status(supplier_name)
            supplier_received_date = purchase_request.get_supplier_received_date(supplier_name)
            supplier_invoice = purchase_request.get_supplier_invoice(supplier_name)
            
            # Supplier Info Table with all required headings
            supplier_info = [
                ['Supplier:', supplier_name],
                ['Order Number:', purchase_request.order_number],
                ['Ordered Date & Time:', purchase_request.ordered_date.strftime('%Y-%m-%d %H:%M:%S')],
                ['Status:', supplier_status]
            ]
            
            # Add Invoice Number (always show, even if empty)
            invoice_number = supplier_invoice.get('invoice_number', '') if supplier_invoice else ''
            supplier_info.append(['Invoice Number:', invoice_number])
            
            # Add Invoice Value (always show, even if empty)
            invoice_value = supplier_invoice.get('invoice_value', '') if supplier_invoice else ''
            if invoice_value:
                supplier_info.append(['Invoice Value:', format_currency(invoice_value, currency_code)])
            else:
                supplier_info.append(['Invoice Value:', ''])
            
            # Add Received Date & Time if available
            if supplier_received_date:
                supplier_info.append(['Received Date & Time:', supplier_received_date])
            
            supplier_info_table = Table(supplier_info, colWidths=[2*inch, 4.5*inch])
            supplier_info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(supplier_info_table)
            elements.append(Spacer(1, 0.2*inch))
            
            # Items Table
            table_data = [['Code', 'Description', 'Qty', 'Cost/Unit', 'Order Qty', 'Total Cost']]
            
            if supplier_status == 'Order Received':
                table_data[0].extend(['Qty Received', 'Total Cost (Received)'])
            
            supplier_total = 0
            supplier_received_total = 0
            
            for item in supplier_items:
                row = [
                    item.code or 'N/A',
                    item.description or 'N/A',
                    f"{item.quantity:.2f}" if item.quantity else '0.00',
                    format_currency(item.cost_per_unit or 0, currency_code),
                    f"{item.order_quantity:.2f}" if item.order_quantity else '0.00',
                    format_currency((item.cost_per_unit or 0) * (item.order_quantity or 0), currency_code)
                ]
                
                item_total = (item.cost_per_unit or 0) * (item.order_quantity or 0)
                supplier_total += item_total
                
                if supplier_status == 'Order Received':
                    qty_received = item.quantity_received if item.quantity_received is not None else 0
                    received_cost = (item.cost_per_unit or 0) * qty_received
                    supplier_received_total += received_cost
                    row.extend([
                        f"{qty_received:.2f}",
                        format_currency(received_cost, currency_code)
                    ])
                
                table_data.append(row)
            
            # Add totals row
            total_row = ['', '', '', '', 'Total:', format_currency(supplier_total, currency_code)]
            if supplier_status == 'Order Received':
                total_row.extend(['', format_currency(supplier_received_total, currency_code)])
                variance = supplier_total - supplier_received_total
                if variance != 0:
                    total_row.append(f"Variance: {format_currency(variance, currency_code)}")
            table_data.append(total_row)
            
            # Create table
            col_widths = [0.8*inch, 2*inch, 0.6*inch, 0.8*inch, 0.8*inch, 1*inch]
            if supplier_status == 'Order Received':
                col_widths.extend([0.8*inch, 1.2*inch])
            
            items_table = Table(table_data, colWidths=col_widths)
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e0e0e0')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            elements.append(items_table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Add page break if not last supplier
            if supplier_name != list(suppliers.keys())[-1]:
                elements.append(PageBreak())
        
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
        
        # Create response with order number as filename
        order_number = purchase_request.order_number or "purchase_order"
        safe_filename = re.sub(r'[^\w\s-]', '', order_number).strip()
        safe_filename = re.sub(r'[-\s]+', '_', safe_filename)
        filename = f"{safe_filename}.pdf"
        
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        current_app.logger.error(f'Error generating PDF: {str(e)}', exc_info=True)
        flash(f'Error generating PDF: {str(e)}', 'error')
        if current_user.user_role == 'Purchase Manager':
            return redirect(url_for('purchase.view_purchase_request', purchase_id=purchase_id))
        else:
            return redirect(url_for('purchase.view_order', purchase_id=purchase_id))


@purchase_bp.route('/purchase/<int:purchase_id>/export-new-pdf')
@login_required
@role_required(['Chef', 'Bartender', 'Manager'])
def export_new_purchase_pdf(purchase_id):
    """Export new purchase request to PDF (simplified format for initial creation)"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from io import BytesIO
        from flask import make_response
        from sqlalchemy.orm import joinedload
        from utils.currency import get_currency_info, format_currency
        import re
        
        ensure_schema_updates()
        org_filter = get_organization_filter(PurchaseRequest)
        
        # User can only view their own orders
        purchase_request = PurchaseRequest.query.filter(org_filter).filter_by(id=purchase_id, created_by=current_user.id).options(
            joinedload(PurchaseRequest.items),
            joinedload(PurchaseRequest.creator)
        ).first_or_404()
        
        # Get currency code
        currency_code = current_user.currency or 'AED'
        currency_info = get_currency_info(currency_code)
        
        # Group items by supplier
        suppliers = {}
        for item in purchase_request.items:
            supplier_name = item.supplier or 'N/A'
            if supplier_name not in suppliers:
                suppliers[supplier_name] = []
            suppliers[supplier_name].append(item)
        
        # Create a BytesIO buffer for the PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch, 
                                leftMargin=0.5*inch, rightMargin=0.5*inch)
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a2a2a'),
            spaceAfter=15,
            alignment=TA_CENTER
        )
        
        supplier_heading_style = ParagraphStyle(
            'SupplierHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1a2a2a'),
            spaceAfter=8,
            spaceBefore=12,
            alignment=TA_LEFT
        )
        
        # Title
        elements.append(Paragraph("PURCHASE REQUEST", title_style))
        elements.append(Spacer(1, 0.15*inch))
        
        # Order Information
        info_data = [
            ['Order Number:', purchase_request.order_number],
            ['Ordered Date & Time:', purchase_request.ordered_date.strftime('%Y-%m-%d %H:%M:%S')],
        ]
        
        if purchase_request.creator:
            creator_name = f"{purchase_request.creator.first_name or ''} {purchase_request.creator.last_name or ''}".strip()
            if creator_name:
                info_data.append(['Ordered By:', creator_name])
        
        info_table = Table(info_data, colWidths=[2*inch, 4.5*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.25*inch))
        
        # Process each supplier
        supplier_names = list(suppliers.keys())
        for idx, (supplier_name, supplier_items) in enumerate(suppliers.items()):
            # Supplier heading
            elements.append(Paragraph(f"Supplier: {supplier_name}", supplier_heading_style))
            elements.append(Spacer(1, 0.1*inch))
            
            # Items Table with columns: Code, Description, Quantity, Cost Per Unit, Quantity Ordered
            table_data = [['Code', 'Description', 'Quantity', 'Cost Per Unit', 'Quantity Ordered']]
            
            supplier_total = 0
            
            for item in supplier_items:
                cost_per_unit = item.cost_per_unit or 0
                order_quantity = item.order_quantity or 0
                item_total = cost_per_unit * order_quantity
                supplier_total += item_total
                
                row = [
                    item.code or 'N/A',
                    item.description or 'N/A',
                    f"{item.quantity:.2f}" if item.quantity else '0.00',
                    format_currency(cost_per_unit, currency_code),
                    f"{order_quantity:.2f}"
                ]
                table_data.append(row)
            
            # Add total row
            total_row = ['', '', '', 'Total:', format_currency(supplier_total, currency_code)]
            table_data.append(total_row)
            
            # Create table with appropriate column widths for A4
            col_widths = [0.8*inch, 2.5*inch, 0.8*inch, 1.2*inch, 1.2*inch]
            items_table = Table(table_data, colWidths=col_widths)
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
                ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
                ('TOPPADDING', (0, 1), (-1, -1), 5),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e0e0e0')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            elements.append(items_table)
            
            # Add spacing between suppliers (no page break - tables will flow naturally)
            if idx < len(supplier_names) - 1:
                elements.append(Spacer(1, 0.3*inch))
        
        # Footer
        footer_text = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Chef & Bartender"
        elements.append(Paragraph(footer_text, ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)))
        
        # Build PDF
        doc.build(elements)
        
        # Get the value of the BytesIO buffer
        buffer.seek(0)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Create response with order number as filename
        order_number = purchase_request.order_number or "purchase_request"
        safe_filename = re.sub(r'[^\w\s-]', '', order_number).strip()
        safe_filename = re.sub(r'[-\s]+', '_', safe_filename)
        filename = f"{safe_filename}.pdf"
        
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        current_app.logger.error(f'Error generating PDF: {str(e)}', exc_info=True)
        flash(f'Error generating PDF: {str(e)}', 'error')
        return redirect(url_for('purchase.order_list'))
