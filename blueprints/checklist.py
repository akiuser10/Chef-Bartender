"""
Checklist Blueprint
Handles Bar Checklist and Kitchen Checklist pages
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file, current_app
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, date, timedelta
from sqlalchemy import and_, or_
import json
import io

from models import ColdStorageUnit, TemperatureLog, TemperatureEntry, WashingUnit, BarGlassWasherChecklist, KitchenDishWasherChecklist, KitchenGlassWasherChecklist, BarClosingChecklistUnit, BarClosingChecklistPoint, BarClosingChecklistEntry, BarClosingChecklistItem, ChoppingBoardChecklistUnit, ChoppingBoardChecklistPoint, ChoppingBoardChecklistEntry, ChoppingBoardChecklistItem, KitchenChoppingBoardChecklistUnit, KitchenChoppingBoardChecklistPoint, KitchenChoppingBoardChecklistEntry, KitchenChoppingBoardChecklistItem, IceScoopSanitationUnit, IceScoopSanitationEntry, KitchenIceScoopSanitationUnit, KitchenIceScoopSanitationEntry, BarOpeningChecklistUnit, BarOpeningChecklistPoint, BarOpeningChecklistEntry, BarOpeningChecklistItem, BarShiftClosingChecklistUnit, BarShiftClosingChecklistPoint, BarShiftClosingChecklistEntry, BarShiftClosingChecklistItem
from extensions import db
from utils.helpers import get_organization_filter, get_user_display_name

checklist_bp = Blueprint('checklist', __name__, url_prefix='/checklist')


def role_required(roles):
    """Decorator to check if user has required role"""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.user_role not in roles:
                from flask import abort
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


ICE_SCOOP_TIME_SLOTS = [
    {'index': 1, 'label': '08:00'},
    {'index': 2, 'label': '12:00'},
    {'index': 3, 'label': '16:00'},
    {'index': 4, 'label': '20:00'},
]


def _get_user_initials(user):
    if not user:
        return ''
    first_initial = user.first_name[0] if user.first_name else ''
    last_initial = user.last_name[0] if user.last_name else ''
    if first_initial or last_initial:
        return f"{first_initial}{last_initial}".upper()
    if user.username:
        return user.username[0].upper()
    return ''


@checklist_bp.route('/bar')
@login_required
@role_required(['Manager', 'Bartender'])
def bar_checklist():
    """Bar Checklist page - accessible to Manager and Bartender"""
    return render_template('checklist/bar_checklist.html')


@checklist_bp.route('/kitchen')
@login_required
@role_required(['Chef', 'Manager'])
def kitchen_checklist():
    """Kitchen Checklist page - accessible to Chef and Manager"""
    return render_template('checklist/kitchen_checklist.html')


# ============================================
# ICE SCOOP SANITATION MONITOR ROUTES
# ============================================

@checklist_bp.route('/bar/ice-scoop', methods=['GET'])
@login_required
@role_required(['Manager', 'Bartender'])
def bar_ice_scoop_sanitation():
    """Ice Scoop Sanitation Monitor (Bar) - accessible to Manager and Bartender"""
    today = date.today()
    return render_template('checklist/ice_scoop_sanitation_bar.html', today=today, slots=ICE_SCOOP_TIME_SLOTS)


@checklist_bp.route('/bar/ice-scoop/units', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def manage_bar_ice_scoop_units():
    """Manage bar ice scoop units - Manager only for create/update/delete"""
    if request.method == 'GET':
        try:
            org_filter = get_organization_filter(IceScoopSanitationUnit)
            units = IceScoopSanitationUnit.query.filter(org_filter).filter_by(is_active=True).order_by(IceScoopSanitationUnit.unit_name).all()
            return jsonify([{
                'id': unit.id,
                'unit_name': unit.unit_name,
                'description': unit.description
            } for unit in units])
        except Exception as e:
            current_app.logger.error(f"Error loading ice scoop units: {str(e)}", exc_info=True)
            return jsonify([])

    data = request.get_json() or {}
    action = data.get('action')
    user_role = (current_user.user_role or '').strip()
    if user_role != 'Manager':
        return jsonify({'success': False, 'error': 'Only Managers can manage units'}), 403

    if action == 'create':
        unit_name = data.get('unit_name', '').strip() or 'BAR'
        description = data.get('description', '').strip()
        org_filter = get_organization_filter(IceScoopSanitationUnit)
        existing_unit = IceScoopSanitationUnit.query.filter(org_filter).filter_by(unit_name=unit_name, is_active=True).first()
        if existing_unit:
            return jsonify({'success': False, 'error': f'Unit name "{unit_name}" already exists'}), 400
        organisation = (current_user.organisation or current_user.restaurant_bar_name or '').strip()
        if not organisation:
            return jsonify({'success': False, 'error': 'User organization is required to create units'}), 400
        unit = IceScoopSanitationUnit(
            unit_name=unit_name,
            description=description,
            organisation=organisation,
            created_by=current_user.id,
            is_active=True
        )
        db.session.add(unit)
        db.session.commit()
        return jsonify({'success': True, 'unit': {
            'id': unit.id,
            'unit_name': unit.unit_name,
            'description': unit.description
        }})

    if action == 'update':
        unit_id = data.get('id')
        if not unit_id:
            return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
        unit = IceScoopSanitationUnit.query.get(unit_id)
        if not unit:
            return jsonify({'success': False, 'error': 'Unit not found'}), 404
        org_filter = get_organization_filter(IceScoopSanitationUnit)
        if not IceScoopSanitationUnit.query.filter(org_filter).filter_by(id=unit.id).first():
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        unit.unit_name = data.get('unit_name', unit.unit_name)
        unit.description = data.get('description', unit.description)
        db.session.commit()
        return jsonify({'success': True})

    if action == 'delete':
        unit_id = data.get('id')
        if not unit_id:
            return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
        unit = IceScoopSanitationUnit.query.get(unit_id)
        if not unit:
            return jsonify({'success': False, 'error': 'Unit not found'}), 404
        org_filter = get_organization_filter(IceScoopSanitationUnit)
        if not IceScoopSanitationUnit.query.filter(org_filter).filter_by(id=unit.id).first():
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        unit.is_active = False
        db.session.commit()
        return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'Invalid action'}), 400


@checklist_bp.route('/bar/ice-scoop/entries', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def bar_ice_scoop_entries():
    """Get or save ice scoop sanitation entries (Bar)"""
    if request.method == 'GET':
        unit_id = request.args.get('unit_id', type=int)
        entry_date = request.args.get('entry_date', type=str)
        if not unit_id or not entry_date:
            return jsonify({'success': False, 'error': 'Unit ID and entry date are required'}), 400
        try:
            entry_date_obj = date.fromisoformat(entry_date)
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format'}), 400

        org_filter = get_organization_filter(IceScoopSanitationUnit)
        unit = IceScoopSanitationUnit.query.filter(org_filter).filter_by(id=unit_id, is_active=True).first()
        if not unit:
            return jsonify({'success': False, 'error': 'Unit not found or unauthorized'}), 404

        org_filter_entries = get_organization_filter(IceScoopSanitationEntry)
        entries = IceScoopSanitationEntry.query.filter(org_filter_entries).filter_by(
            unit_id=unit_id,
            entry_date=entry_date_obj
        ).all()
        entry_map = {e.slot_index: e for e in entries}

        slots = []
        for slot in ICE_SCOOP_TIME_SLOTS:
            entry = entry_map.get(slot['index'])
            slots.append({
                'slot_index': slot['index'],
                'label': slot['label'],
                'is_completed': bool(entry.is_completed) if entry else False,
                'staff_initials': entry.staff_initials if entry else ''
            })
        return jsonify({'success': True, 'slots': slots})

    data = request.get_json() or {}
    unit_id = data.get('unit_id')
    entry_date = data.get('entry_date')
    slots = data.get('slots', [])
    if not unit_id or not entry_date:
        return jsonify({'success': False, 'error': 'Unit ID and entry date are required'}), 400
    try:
        entry_date_obj = date.fromisoformat(entry_date)
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid date format'}), 400

    org_filter = get_organization_filter(IceScoopSanitationUnit)
    unit = IceScoopSanitationUnit.query.filter(org_filter).filter_by(id=unit_id, is_active=True).first()
    if not unit:
        return jsonify({'success': False, 'error': 'Unit not found or unauthorized'}), 404

    organisation = (current_user.organisation or current_user.restaurant_bar_name or '').strip()
    if not organisation:
        return jsonify({'success': False, 'error': 'User organization is required'}), 400

    try:
        for slot in slots:
            slot_index = int(slot.get('slot_index'))
            is_completed = bool(slot.get('is_completed'))
            staff_initials = (slot.get('staff_initials') or '').strip()
            if is_completed and not staff_initials:
                staff_initials = _get_user_initials(current_user)

            org_filter_entries = get_organization_filter(IceScoopSanitationEntry)
            entry = IceScoopSanitationEntry.query.filter(org_filter_entries).filter_by(
                unit_id=unit_id,
                entry_date=entry_date_obj,
                slot_index=slot_index
            ).first()
            if not entry:
                entry = IceScoopSanitationEntry(
                    unit_id=unit_id,
                    entry_date=entry_date_obj,
                    slot_index=slot_index,
                    organisation=organisation,
                    created_by=current_user.id
                )
                db.session.add(entry)
            entry.is_completed = is_completed
            entry.staff_initials = staff_initials or None
            entry.completed_at = datetime.utcnow() if is_completed else None

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving ice scoop entries: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@checklist_bp.route('/kitchen/ice-scoop', methods=['GET'])
@login_required
@role_required(['Chef', 'Manager'])
def kitchen_ice_scoop_sanitation():
    """Ice Scoop Sanitation Monitor (Kitchen) - accessible to Chef and Manager"""
    today = date.today()
    return render_template('checklist/ice_scoop_sanitation_kitchen.html', today=today, slots=ICE_SCOOP_TIME_SLOTS)


@checklist_bp.route('/kitchen/ice-scoop/units', methods=['GET', 'POST'])
@login_required
@role_required(['Chef', 'Manager'])
def manage_kitchen_ice_scoop_units():
    """Manage kitchen ice scoop units - Manager only for create/update/delete"""
    if request.method == 'GET':
        try:
            org_filter = get_organization_filter(KitchenIceScoopSanitationUnit)
            units = KitchenIceScoopSanitationUnit.query.filter(org_filter).filter_by(is_active=True).order_by(KitchenIceScoopSanitationUnit.unit_name).all()
            return jsonify([{
                'id': unit.id,
                'unit_name': unit.unit_name,
                'description': unit.description
            } for unit in units])
        except Exception as e:
            current_app.logger.error(f"Error loading kitchen ice scoop units: {str(e)}", exc_info=True)
            return jsonify([])

    data = request.get_json() or {}
    action = data.get('action')
    user_role = (current_user.user_role or '').strip()
    if user_role != 'Manager':
        return jsonify({'success': False, 'error': 'Only Managers can manage units'}), 403

    if action == 'create':
        unit_name = data.get('unit_name', '').strip() or 'KITCHEN'
        description = data.get('description', '').strip()
        org_filter = get_organization_filter(KitchenIceScoopSanitationUnit)
        existing_unit = KitchenIceScoopSanitationUnit.query.filter(org_filter).filter_by(unit_name=unit_name, is_active=True).first()
        if existing_unit:
            return jsonify({'success': False, 'error': f'Unit name "{unit_name}" already exists'}), 400
        organisation = (current_user.organisation or current_user.restaurant_bar_name or '').strip()
        if not organisation:
            return jsonify({'success': False, 'error': 'User organization is required to create units'}), 400
        unit = KitchenIceScoopSanitationUnit(
            unit_name=unit_name,
            description=description,
            organisation=organisation,
            created_by=current_user.id,
            is_active=True
        )
        db.session.add(unit)
        db.session.commit()
        return jsonify({'success': True, 'unit': {
            'id': unit.id,
            'unit_name': unit.unit_name,
            'description': unit.description
        }})

    if action == 'update':
        unit_id = data.get('id')
        if not unit_id:
            return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
        unit = KitchenIceScoopSanitationUnit.query.get(unit_id)
        if not unit:
            return jsonify({'success': False, 'error': 'Unit not found'}), 404
        org_filter = get_organization_filter(KitchenIceScoopSanitationUnit)
        if not KitchenIceScoopSanitationUnit.query.filter(org_filter).filter_by(id=unit.id).first():
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        unit.unit_name = data.get('unit_name', unit.unit_name)
        unit.description = data.get('description', unit.description)
        db.session.commit()
        return jsonify({'success': True})

    if action == 'delete':
        unit_id = data.get('id')
        if not unit_id:
            return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
        unit = KitchenIceScoopSanitationUnit.query.get(unit_id)
        if not unit:
            return jsonify({'success': False, 'error': 'Unit not found'}), 404
        org_filter = get_organization_filter(KitchenIceScoopSanitationUnit)
        if not KitchenIceScoopSanitationUnit.query.filter(org_filter).filter_by(id=unit.id).first():
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        unit.is_active = False
        db.session.commit()
        return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'Invalid action'}), 400


@checklist_bp.route('/kitchen/ice-scoop/entries', methods=['GET', 'POST'])
@login_required
@role_required(['Chef', 'Manager'])
def kitchen_ice_scoop_entries():
    """Get or save ice scoop sanitation entries (Kitchen)"""
    if request.method == 'GET':
        unit_id = request.args.get('unit_id', type=int)
        entry_date = request.args.get('entry_date', type=str)
        if not unit_id or not entry_date:
            return jsonify({'success': False, 'error': 'Unit ID and entry date are required'}), 400
        try:
            entry_date_obj = date.fromisoformat(entry_date)
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format'}), 400

        org_filter = get_organization_filter(KitchenIceScoopSanitationUnit)
        unit = KitchenIceScoopSanitationUnit.query.filter(org_filter).filter_by(id=unit_id, is_active=True).first()
        if not unit:
            return jsonify({'success': False, 'error': 'Unit not found or unauthorized'}), 404

        org_filter_entries = get_organization_filter(KitchenIceScoopSanitationEntry)
        entries = KitchenIceScoopSanitationEntry.query.filter(org_filter_entries).filter_by(
            unit_id=unit_id,
            entry_date=entry_date_obj
        ).all()
        entry_map = {e.slot_index: e for e in entries}

        slots = []
        for slot in ICE_SCOOP_TIME_SLOTS:
            entry = entry_map.get(slot['index'])
            slots.append({
                'slot_index': slot['index'],
                'label': slot['label'],
                'is_completed': bool(entry.is_completed) if entry else False,
                'staff_initials': entry.staff_initials if entry else ''
            })
        return jsonify({'success': True, 'slots': slots})

    data = request.get_json() or {}
    unit_id = data.get('unit_id')
    entry_date = data.get('entry_date')
    slots = data.get('slots', [])
    if not unit_id or not entry_date:
        return jsonify({'success': False, 'error': 'Unit ID and entry date are required'}), 400
    try:
        entry_date_obj = date.fromisoformat(entry_date)
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid date format'}), 400

    org_filter = get_organization_filter(KitchenIceScoopSanitationUnit)
    unit = KitchenIceScoopSanitationUnit.query.filter(org_filter).filter_by(id=unit_id, is_active=True).first()
    if not unit:
        return jsonify({'success': False, 'error': 'Unit not found or unauthorized'}), 404

    organisation = (current_user.organisation or current_user.restaurant_bar_name or '').strip()
    if not organisation:
        return jsonify({'success': False, 'error': 'User organization is required'}), 400

    try:
        for slot in slots:
            slot_index = int(slot.get('slot_index'))
            is_completed = bool(slot.get('is_completed'))
            staff_initials = (slot.get('staff_initials') or '').strip()
            if is_completed and not staff_initials:
                staff_initials = _get_user_initials(current_user)

            org_filter_entries = get_organization_filter(KitchenIceScoopSanitationEntry)
            entry = KitchenIceScoopSanitationEntry.query.filter(org_filter_entries).filter_by(
                unit_id=unit_id,
                entry_date=entry_date_obj,
                slot_index=slot_index
            ).first()
            if not entry:
                entry = KitchenIceScoopSanitationEntry(
                    unit_id=unit_id,
                    entry_date=entry_date_obj,
                    slot_index=slot_index,
                    organisation=organisation,
                    created_by=current_user.id
                )
                db.session.add(entry)
            entry.is_completed = is_completed
            entry.staff_initials = staff_initials or None
            entry.completed_at = datetime.utcnow() if is_completed else None

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving kitchen ice scoop entries: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# COLD STORAGE TEMPERATURE LOG ROUTES
# ============================================

@checklist_bp.route('/kitchen/cold-storage')
@login_required
@role_required(['Chef', 'Manager'])
def kitchen_cold_storage_temperature_log():
    """Kitchen Cold Storage Temperature Log page - accessible only to Chef and Manager"""
    # Ensure schema is up to date (adds missing columns like 'location')
    from utils.db_helpers import ensure_schema_updates
    ensure_schema_updates()
    
    try:
        org_filter = get_organization_filter(ColdStorageUnit)
        # Filter by kitchen context
        units = ColdStorageUnit.query.filter(org_filter).filter_by(
            is_active=True, 
            context='kitchen'
        ).order_by(ColdStorageUnit.unit_number).all()
    except Exception as e:
        current_app.logger.error(f"Error loading cold storage units: {str(e)}", exc_info=True)
        # If table doesn't exist yet, return empty list
        units = []
    
    # Get today's date
    today = date.today()
    
    return render_template('checklist/cold_storage_temperature_log.html', units=units, today=today)

@checklist_bp.route('/bar/cold-storage')
@login_required
@role_required(['Manager', 'Bartender', 'Chef'])
def cold_storage_temperature_log():
    """Main page for Cold Storage Temperature Log"""
    # Ensure schema is up to date (adds missing columns like 'location')
    from utils.db_helpers import ensure_schema_updates
    ensure_schema_updates()
    
    try:
        org_filter = get_organization_filter(ColdStorageUnit)
        # Filter by bar context
        units = ColdStorageUnit.query.filter(org_filter).filter_by(
            is_active=True, 
            context='bar'
        ).order_by(ColdStorageUnit.unit_number).all()
    except Exception as e:
        current_app.logger.error(f"Error loading cold storage units: {str(e)}", exc_info=True)
        # If table doesn't exist yet, return empty list
        units = []
    
    # Get today's date
    today = date.today()
    
    return render_template('checklist/cold_storage_temperature_log.html', units=units, today=today)


@checklist_bp.route('/kitchen/cold-storage/units', methods=['GET', 'POST'])
@login_required
@role_required(['Chef', 'Manager'])
def kitchen_manage_cold_storage_units():
    """API endpoint for managing cold storage units (Kitchen) - accessible only to Chef and Manager"""
    # Ensure schema is up to date before any operations
    from utils.db_helpers import ensure_schema_updates
    ensure_schema_updates()
    
    if request.method == 'GET':
        try:
            org_filter = get_organization_filter(ColdStorageUnit)
            # Filter by kitchen context
            units = ColdStorageUnit.query.filter(org_filter).filter_by(
                is_active=True, 
                context='kitchen'
            ).order_by(ColdStorageUnit.unit_number).all()
            return jsonify([{
                'id': unit.id,
                'unit_number': unit.unit_number,
                'location': unit.location,
                'unit_type': unit.unit_type,
                'min_temp': unit.min_temp,
                'max_temp': unit.max_temp
            } for unit in units])
        except Exception as e:
            current_app.logger.error(f"Error loading units: {str(e)}", exc_info=True)
            return jsonify([])  # Return empty list if error
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'create':
                # Only Managers can create units
                if current_user.user_role != 'Manager':
                    current_app.logger.warning(f"Non-Manager user {current_user.id} ({current_user.user_role}) attempted to create unit")
                    return jsonify({'success': False, 'error': 'Only Managers can create new units'}), 403
                
                # Validate required fields
                unit_number = data.get('unit_number', '').strip()
                location = data.get('location', '').strip()
                unit_type = data.get('unit_type', '').strip()
                
                if not unit_number:
                    return jsonify({'success': False, 'error': 'Unit number is required'}), 400
                if not location:
                    return jsonify({'success': False, 'error': 'Location is required'}), 400
                if not unit_type:
                    return jsonify({'success': False, 'error': 'Unit type is required'}), 400
                
                # Validate unit type (accept both "Chiller" and "Wine Chiller" for backward compatibility)
                valid_types = ['Refrigerator', 'Freezer', 'Chiller', 'Wine Chiller']
                if unit_type not in valid_types:
                    return jsonify({'success': False, 'error': f'Invalid unit type. Must be one of: Refrigerator, Freezer, Chiller'}), 400
                
                # Normalize "Chiller" to "Wine Chiller" for database storage (backward compatibility)
                if unit_type == 'Chiller':
                    unit_type = 'Wine Chiller'
                
                try:
                    # Check if unit number already exists in organization (within same context)
                    org_filter = get_organization_filter(ColdStorageUnit)
                    existing_unit = ColdStorageUnit.query.filter(org_filter).filter_by(
                        unit_number=unit_number,
                        context='kitchen',  # Check within kitchen context
                        is_active=True
                    ).first()
                    
                    if existing_unit:
                        return jsonify({'success': False, 'error': f'Unit number "{unit_number}" already exists in your organization'}), 400
                    
                    # Handle temperature values - convert to float if provided, otherwise None
                    min_temp = None
                    max_temp = None
                    if data.get('min_temp') and str(data.get('min_temp')).strip():
                        try:
                            min_temp = float(data['min_temp'])
                        except (ValueError, TypeError):
                            return jsonify({'success': False, 'error': 'Invalid minimum temperature value'}), 400
                    if data.get('max_temp') and str(data.get('max_temp')).strip():
                        try:
                            max_temp = float(data['max_temp'])
                        except (ValueError, TypeError):
                            return jsonify({'success': False, 'error': 'Invalid maximum temperature value'}), 400
                    
                    # Validate temperature range for Chiller (stored as "Wine Chiller" in DB)
                    if unit_type == 'Wine Chiller':
                        if min_temp is not None and max_temp is not None and min_temp >= max_temp:
                            return jsonify({'success': False, 'error': 'Minimum temperature must be less than maximum temperature'}), 400
                    
                    # Create the unit with kitchen context
                    unit = ColdStorageUnit(
                        unit_number=unit_number,
                        location=location,
                        unit_type=unit_type,
                        context='kitchen',  # Set context to kitchen
                        min_temp=min_temp,
                        max_temp=max_temp,
                        organisation=current_user.organisation or current_user.restaurant_bar_name,
                        created_by=current_user.id,
                        is_active=True
                    )
                    db.session.add(unit)
                    db.session.commit()
                    
                    current_app.logger.info(f"Manager {current_user.id} created unit {unit.id} ({unit.unit_number})")
                    
                    return jsonify({'success': True, 'unit': {
                        'id': unit.id,
                        'unit_number': unit.unit_number,
                        'location': unit.location,
                        'unit_type': unit.unit_type,
                        'min_temp': unit.min_temp,
                        'max_temp': unit.max_temp
                    }})
                except ValueError as e:
                    db.session.rollback()
                    current_app.logger.error(f"ValueError creating unit: {str(e)}")
                    return jsonify({'success': False, 'error': f'Invalid input value: {str(e)}'}), 400
                except Exception as e:
                    db.session.rollback()
                    error_msg = str(e)
                    current_app.logger.error(f"Error creating unit: {error_msg}", exc_info=True)
                    # Provide more user-friendly error message
                    if 'duplicate' in error_msg.lower() or 'unique' in error_msg.lower() or 'already exists' in error_msg.lower():
                        return jsonify({'success': False, 'error': f'Unit number "{unit_number}" already exists'}), 400
                    if 'foreign key' in error_msg.lower() or 'constraint' in error_msg.lower():
                        return jsonify({'success': False, 'error': 'Database constraint error. Please contact support.'}), 500
                    return jsonify({'success': False, 'error': f'Error creating unit: {error_msg}'}), 500
            
            elif action == 'update':
                # Only Managers can update units
                if current_user.user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can update units'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                
                try:
                    unit = ColdStorageUnit.query.get(data['id'])
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found'}), 404
                    
                    org_filter = get_organization_filter(ColdStorageUnit)
                    if not ColdStorageUnit.query.filter(org_filter).filter_by(id=unit.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    # Validate required fields
                    if not data.get('unit_number') or not data.get('location') or not data.get('unit_type'):
                        return jsonify({'success': False, 'error': 'Unit number, location, and unit type are required'}), 400
                    
                    # Handle temperature values - convert to float if provided, otherwise None
                    min_temp = None
                    max_temp = None
                    if data.get('min_temp') and str(data.get('min_temp')).strip():
                        min_temp = float(data['min_temp'])
                    if data.get('max_temp') and str(data.get('max_temp')).strip():
                        max_temp = float(data['max_temp'])
                    
                    # Normalize "Chiller" to "Wine Chiller" for database storage
                    normalized_unit_type = data['unit_type']
                    if normalized_unit_type == 'Chiller':
                        normalized_unit_type = 'Wine Chiller'
                    
                    unit.unit_number = data['unit_number']
                    unit.location = data['location']
                    unit.unit_type = normalized_unit_type
                    unit.min_temp = min_temp
                    unit.max_temp = max_temp
                    db.session.commit()
                    return jsonify({'success': True})
                except ValueError as e:
                    db.session.rollback()
                    return jsonify({'success': False, 'error': f'Invalid temperature value: {str(e)}'}), 400
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error updating unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error updating unit: {str(e)}'}), 500
            
            elif action == 'delete':
                # Only Managers can delete units
                if current_user.user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can delete units'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                
                try:
                    unit = ColdStorageUnit.query.get(data['id'])
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found'}), 404
                    
                    org_filter = get_organization_filter(ColdStorageUnit)
                    if not ColdStorageUnit.query.filter(org_filter).filter_by(id=unit.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    unit.is_active = False
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error deleting unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error deleting unit: {str(e)}'}), 500
            
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            current_app.logger.error(f"Unexpected error in kitchen_manage_cold_storage_units: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500


@checklist_bp.route('/bar/cold-storage/units', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender', 'Chef'])
def manage_cold_storage_units():
    """API endpoint for managing cold storage units"""
    # Ensure schema is up to date before any operations
    from utils.db_helpers import ensure_schema_updates
    ensure_schema_updates()
    
    if request.method == 'GET':
        try:
            org_filter = get_organization_filter(ColdStorageUnit)
            # Filter by bar context
            units = ColdStorageUnit.query.filter(org_filter).filter_by(
                is_active=True, 
                context='bar'
            ).order_by(ColdStorageUnit.unit_number).all()
            return jsonify([{
                'id': unit.id,
                'unit_number': unit.unit_number,
                'location': unit.location,
                'unit_type': unit.unit_type,
                'min_temp': unit.min_temp,
                'max_temp': unit.max_temp
            } for unit in units])
        except Exception as e:
            current_app.logger.error(f"Error loading units: {str(e)}", exc_info=True)
            return jsonify([])  # Return empty list if error
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'create':
                # Only Managers can create units
                if current_user.user_role != 'Manager':
                    current_app.logger.warning(f"Non-Manager user {current_user.id} ({current_user.user_role}) attempted to create unit")
                    return jsonify({'success': False, 'error': 'Only Managers can create new units'}), 403
                
                # Validate required fields
                unit_number = data.get('unit_number', '').strip()
                location = data.get('location', '').strip()
                unit_type = data.get('unit_type', '').strip()
                
                if not unit_number:
                    return jsonify({'success': False, 'error': 'Unit number is required'}), 400
                if not location:
                    return jsonify({'success': False, 'error': 'Location is required'}), 400
                if not unit_type:
                    return jsonify({'success': False, 'error': 'Unit type is required'}), 400
                
                # Validate unit type (accept both "Chiller" and "Wine Chiller" for backward compatibility)
                valid_types = ['Refrigerator', 'Freezer', 'Chiller', 'Wine Chiller']
                if unit_type not in valid_types:
                    return jsonify({'success': False, 'error': f'Invalid unit type. Must be one of: Refrigerator, Freezer, Chiller'}), 400
                
                # Normalize "Chiller" to "Wine Chiller" for database storage (backward compatibility)
                if unit_type == 'Chiller':
                    unit_type = 'Wine Chiller'
                
                try:
                    # Check if unit number already exists in organization (within same context)
                    org_filter = get_organization_filter(ColdStorageUnit)
                    existing_unit = ColdStorageUnit.query.filter(org_filter).filter_by(
                        unit_number=unit_number,
                        context='bar',  # Check within bar context
                        is_active=True
                    ).first()
                    
                    if existing_unit:
                        return jsonify({'success': False, 'error': f'Unit number "{unit_number}" already exists in your organization'}), 400
                    
                    # Handle temperature values - convert to float if provided, otherwise None
                    min_temp = None
                    max_temp = None
                    if data.get('min_temp') and str(data.get('min_temp')).strip():
                        try:
                            min_temp = float(data['min_temp'])
                        except (ValueError, TypeError):
                            return jsonify({'success': False, 'error': 'Invalid minimum temperature value'}), 400
                    if data.get('max_temp') and str(data.get('max_temp')).strip():
                        try:
                            max_temp = float(data['max_temp'])
                        except (ValueError, TypeError):
                            return jsonify({'success': False, 'error': 'Invalid maximum temperature value'}), 400
                    
                    # Validate temperature range for Chiller (stored as "Wine Chiller" in DB)
                    if unit_type == 'Wine Chiller':
                        if min_temp is not None and max_temp is not None and min_temp >= max_temp:
                            return jsonify({'success': False, 'error': 'Minimum temperature must be less than maximum temperature'}), 400
                    
                    # Create the unit with bar context
                    unit = ColdStorageUnit(
                        unit_number=unit_number,
                        location=location,
                        unit_type=unit_type,
                        context='bar',  # Set context to bar
                        min_temp=min_temp,
                        max_temp=max_temp,
                        organisation=current_user.organisation or current_user.restaurant_bar_name,
                        created_by=current_user.id,
                        is_active=True
                    )
                    db.session.add(unit)
                    db.session.commit()
                    
                    current_app.logger.info(f"Manager {current_user.id} created unit {unit.id} ({unit.unit_number})")
                    
                    return jsonify({'success': True, 'unit': {
                        'id': unit.id,
                        'unit_number': unit.unit_number,
                        'location': unit.location,
                        'unit_type': unit.unit_type,
                        'min_temp': unit.min_temp,
                        'max_temp': unit.max_temp
                    }})
                except ValueError as e:
                    db.session.rollback()
                    current_app.logger.error(f"ValueError creating unit: {str(e)}")
                    return jsonify({'success': False, 'error': f'Invalid input value: {str(e)}'}), 400
                except Exception as e:
                    db.session.rollback()
                    error_msg = str(e)
                    current_app.logger.error(f"Error creating unit: {error_msg}", exc_info=True)
                    # Provide more user-friendly error message
                    if 'duplicate' in error_msg.lower() or 'unique' in error_msg.lower() or 'already exists' in error_msg.lower():
                        return jsonify({'success': False, 'error': f'Unit number "{unit_number}" already exists'}), 400
                    if 'foreign key' in error_msg.lower() or 'constraint' in error_msg.lower():
                        return jsonify({'success': False, 'error': 'Database constraint error. Please contact support.'}), 500
                    return jsonify({'success': False, 'error': f'Error creating unit: {error_msg}'}), 500
            
            elif action == 'update':
                # Only Managers can update units
                if current_user.user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can update units'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                
                try:
                    unit = ColdStorageUnit.query.get(data['id'])
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found'}), 404
                    
                    org_filter = get_organization_filter(ColdStorageUnit)
                    if not ColdStorageUnit.query.filter(org_filter).filter_by(id=unit.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    # Validate required fields
                    if not data.get('unit_number') or not data.get('location') or not data.get('unit_type'):
                        return jsonify({'success': False, 'error': 'Unit number, location, and unit type are required'}), 400
                    
                    # Handle temperature values - convert to float if provided, otherwise None
                    min_temp = None
                    max_temp = None
                    if data.get('min_temp') and str(data.get('min_temp')).strip():
                        min_temp = float(data['min_temp'])
                    if data.get('max_temp') and str(data.get('max_temp')).strip():
                        max_temp = float(data['max_temp'])
                    
                    # Normalize "Chiller" to "Wine Chiller" for database storage
                    normalized_unit_type = data['unit_type']
                    if normalized_unit_type == 'Chiller':
                        normalized_unit_type = 'Wine Chiller'
                    
                    unit.unit_number = data['unit_number']
                    unit.location = data['location']
                    unit.unit_type = normalized_unit_type
                    unit.min_temp = min_temp
                    unit.max_temp = max_temp
                    db.session.commit()
                    return jsonify({'success': True})
                except ValueError as e:
                    db.session.rollback()
                    return jsonify({'success': False, 'error': f'Invalid temperature value: {str(e)}'}), 400
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error updating unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error updating unit: {str(e)}'}), 500
            
            elif action == 'delete':
                # Only Managers can delete units
                if current_user.user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can delete units'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                
                try:
                    unit = ColdStorageUnit.query.get(data['id'])
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found'}), 404
                    
                    org_filter = get_organization_filter(ColdStorageUnit)
                    if not ColdStorageUnit.query.filter(org_filter).filter_by(id=unit.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    unit.is_active = False
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error deleting unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error deleting unit: {str(e)}'}), 500
            
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            current_app.logger.error(f"Unexpected error in manage_cold_storage_units: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500


@checklist_bp.route('/kitchen/cold-storage/log/<int:unit_id>/<date_str>', methods=['GET', 'POST'])
@login_required
@role_required(['Chef', 'Manager'])
def kitchen_temperature_log_entry(unit_id, date_str):
    """API endpoint for getting/creating temperature log entries (Kitchen) - accessible only to Chef and Manager"""
    # Forward to the bar route which has the same implementation
    # The access control is already handled by the decorator
    from flask import redirect, url_for
    return temperature_log_entry(unit_id, date_str)


@checklist_bp.route('/bar/cold-storage/log/<int:unit_id>/<date_str>', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender', 'Chef'])
def temperature_log_entry(unit_id, date_str):
    """API endpoint for getting/creating temperature log entries"""
    try:
        # Ensure schema is up to date before accessing data
        from utils.db_helpers import ensure_schema_updates
        ensure_schema_updates()
        
        log_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid date format'}), 400
    except Exception as e:
        current_app.logger.error(f"Error parsing date or updating schema: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'Error processing request: {str(e)}'}), 500
    
    try:
        unit = ColdStorageUnit.query.get_or_404(unit_id)
        org_filter = get_organization_filter(ColdStorageUnit)
        if not ColdStorageUnit.query.filter(org_filter).filter_by(id=unit.id).first():
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    except Exception as e:
        current_app.logger.error(f"Error loading unit {unit_id}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'Error loading unit: {str(e)}'}), 500
    
    if request.method == 'GET':
        try:
            # Get or create log for this unit and date
            log = TemperatureLog.query.filter_by(unit_id=unit_id, log_date=log_date).first()
            
            if not log:
                # Create new log
                # Calculate week_start_date (Monday of the week)
                week_start = TemperatureLog.calculate_week_start(log_date)
                log = TemperatureLog(
                    unit_id=unit_id,
                    log_date=log_date,
                    week_start_date=week_start,
                    time_slot='10:00 AM',  # Default time slot for the log
                    temperature=0.0,  # Default temperature value for database compatibility (if NOT NULL required)
                    organisation=current_user.organisation or current_user.restaurant_bar_name
                )
                db.session.add(log)
                db.session.commit()
            
            # Get all entries for this log, ordered by scheduled time
            entries = log.entries.order_by(TemperatureEntry.scheduled_time).all()
            entry_dict = {entry.scheduled_time: {
                'id': entry.id,
                'temperature': entry.temperature,
                'corrective_action': entry.corrective_action,
                'action_time': entry.action_time.isoformat() if entry.action_time else None,
                'recheck_temperature': entry.recheck_temperature,
                'initial': entry.initial,
                'is_late_entry': entry.is_late_entry,
                'entry_timestamp': entry.entry_timestamp.isoformat() if entry.entry_timestamp else None
            } for entry in entries}
            
            # Safely get location - handle case where column might not exist yet
            try:
                location = unit.location if hasattr(unit, 'location') else 'Unknown'
            except Exception:
                location = 'Unknown'
            
            return jsonify({
                'success': True,
                'log': {
                    'id': log.id,
                    'unit_id': log.unit_id,
                    'log_date': log.log_date.isoformat(),
                    'supervisor_verified': log.supervisor_verified if hasattr(log, 'supervisor_verified') else False,
                    'supervisor_name': log.supervisor_name if hasattr(log, 'supervisor_name') else None,
                    'entries': entry_dict
                },
                'unit': {
                    'id': unit.id,
                    'unit_number': unit.unit_number,
                    'location': location,
                    'unit_type': unit.unit_type,
                    'min_temp': unit.min_temp if hasattr(unit, 'min_temp') else None,
                    'max_temp': unit.max_temp if hasattr(unit, 'max_temp') else None
                }
            })
        except Exception as e:
            current_app.logger.error(f"Error loading temperature log: {str(e)}", exc_info=True)
            db.session.rollback()
            return jsonify({'success': False, 'error': f'Error loading temperature log: {str(e)}'}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'save_entry':
                try:
                    # Get or create log
                    log = TemperatureLog.query.filter_by(unit_id=unit_id, log_date=log_date).first()
                    if not log:
                        # Calculate week_start_date (Monday of the week)
                        week_start = TemperatureLog.calculate_week_start(log_date)
                        # Get the scheduled_time from the entry being saved
                        scheduled_time = data.get('scheduled_time', '10:00 AM')
                        # Get temperature from the entry being saved (for database compatibility)
                        # If temperature is None and database requires NOT NULL, use 0.0 as default
                        temperature = data.get('temperature')
                        if temperature is None:
                            temperature = 0.0  # Default value if database requires NOT NULL
                        log = TemperatureLog(
                            unit_id=unit_id,
                            log_date=log_date,
                            week_start_date=week_start,
                            time_slot=scheduled_time,  # Set time_slot from the entry being saved
                            temperature=temperature,  # Set temperature for database compatibility
                            organisation=current_user.organisation or current_user.restaurant_bar_name
                        )
                        db.session.add(log)
                        db.session.commit()
                    
                    scheduled_time = data['scheduled_time']
                    temperature = data.get('temperature')
                    corrective_action = data.get('corrective_action', '')
                    action_time_str = data.get('action_time')
                    recheck_temperature = data.get('recheck_temperature')
                    initial = data.get('initial', '')
                    is_late_entry = data.get('is_late_entry', False)
                    
                    # Check if entry already exists
                    entry = TemperatureEntry.query.filter_by(log_id=log.id, scheduled_time=scheduled_time).first()
                    
                    if entry:
                        # Update existing entry
                        entry.temperature = temperature
                        entry.corrective_action = corrective_action
                        entry.recheck_temperature = recheck_temperature
                        entry.initial = initial
                        entry.is_late_entry = is_late_entry
                        if action_time_str:
                            entry.action_time = datetime.fromisoformat(action_time_str.replace('Z', '+00:00'))
                        entry.entry_timestamp = datetime.utcnow()
                    else:
                        # Create new entry
                        entry = TemperatureEntry(
                            log_id=log.id,
                            scheduled_time=scheduled_time,
                            temperature=temperature,
                            corrective_action=corrective_action,
                            recheck_temperature=recheck_temperature,
                            initial=initial,
                            is_late_entry=is_late_entry,
                            created_by=current_user.id
                        )
                        if action_time_str:
                            entry.action_time = datetime.fromisoformat(action_time_str.replace('Z', '+00:00'))
                        db.session.add(entry)
                    
                    db.session.commit()
                    
                    # Check if out of range
                    is_out_of_range = entry.is_out_of_range(unit) if temperature is not None else False
                    
                    return jsonify({
                        'success': True,
                        'entry': {
                            'id': entry.id,
                            'temperature': entry.temperature,
                            'corrective_action': entry.corrective_action,
                            'action_time': entry.action_time.isoformat() if entry.action_time else None,
                            'recheck_temperature': entry.recheck_temperature,
                            'initial': entry.initial,
                            'is_late_entry': entry.is_late_entry,
                            'is_out_of_range': is_out_of_range
                        }
                    })
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error saving temperature entry: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error saving entry: {str(e)}'}), 500
            
            elif action == 'verify':
                try:
                    log = TemperatureLog.query.filter_by(unit_id=unit_id, log_date=log_date).first()
                    if not log:
                        return jsonify({'success': False, 'error': 'Log not found'}), 404
                    
                    log.supervisor_verified = True
                    log.supervisor_name = data.get('supervisor_name', current_user.first_name or current_user.username)
                    log.supervisor_verified_at = datetime.utcnow()
                    db.session.commit()
                    
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error verifying log: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error verifying log: {str(e)}'}), 500
            
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            current_app.logger.error(f"Unexpected error in temperature_log_entry POST: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500


@checklist_bp.route('/kitchen/cold-storage/checklist-pdf', methods=['POST'])
@login_required
@role_required(['Chef', 'Manager'])
def kitchen_generate_checklist_pdf():
    """Generate checklist PDF (Kitchen) - accessible only to Chef and Manager"""
    try:
        from utils.pdf_generator import generate_checklist_pdf
        
        data = request.get_json()
        unit_ids = data.get('unit_ids', [])
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        times = data.get('times', [])
        
        if not unit_ids:
            return jsonify({'success': False, 'error': 'No units selected'}), 400
        if not times:
            return jsonify({'success': False, 'error': 'No times selected'}), 400
        
        org_filter = get_organization_filter(ColdStorageUnit)
        # Filter by kitchen context
        units = ColdStorageUnit.query.filter(org_filter).filter(
            ColdStorageUnit.id.in_(unit_ids),
            ColdStorageUnit.is_active == True,
            ColdStorageUnit.context == 'kitchen'  # Only kitchen units
        ).all()
        
        if not units:
            return jsonify({'success': False, 'error': 'No units found'}), 400
        
        # Generate PDF
        pdf_buffer = generate_checklist_pdf(units, start_date, end_date, times)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'temperature_checklist_{start_date}_{end_date}.pdf'
        )
    except Exception as e:
        current_app.logger.error(f"Error generating checklist PDF: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@checklist_bp.route('/bar/cold-storage/checklist-pdf', methods=['POST'])
@login_required
@role_required(['Manager', 'Bartender', 'Chef'])
def generate_checklist_pdf():
    """Generate checklist PDF organized by date/time with all selected units"""
    try:
        from utils.pdf_generator import generate_checklist_pdf
        
        data = request.get_json()
        unit_ids = data.get('unit_ids', [])
        times = data.get('times', [])
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        
        if not unit_ids:
            return jsonify({'success': False, 'error': 'No units selected'}), 400
        
        if not times:
            return jsonify({'success': False, 'error': 'No times selected'}), 400
        
        org_filter = get_organization_filter(ColdStorageUnit)
        # Filter by bar context
        units = ColdStorageUnit.query.filter(org_filter).filter(
            ColdStorageUnit.id.in_(unit_ids),
            ColdStorageUnit.is_active == True,
            ColdStorageUnit.context == 'bar'  # Only bar units
        ).all()
        
        if not units:
            return jsonify({'success': False, 'error': 'No units found'}), 400
        
        # Generate PDF
        pdf_buffer = generate_checklist_pdf(units, start_date, end_date, times)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'temperature_checklist_{start_date}_{end_date}.pdf'
        )
    except Exception as e:
        current_app.logger.error(f"Error generating checklist PDF: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@checklist_bp.route('/kitchen/cold-storage/pdf', methods=['POST'])
@login_required
@role_required(['Chef', 'Manager'])
def kitchen_generate_temperature_log_pdf():
    """Generate PDF for temperature logs (Kitchen) - accessible only to Chef and Manager"""
    try:
        from utils.pdf_generator import generate_temperature_log_pdf
        
        data = request.get_json()
        unit_ids = data.get('unit_ids', [])
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        
        org_filter = get_organization_filter(ColdStorageUnit)
        # Filter by kitchen context
        units = ColdStorageUnit.query.filter(org_filter).filter(
            ColdStorageUnit.id.in_(unit_ids),
            ColdStorageUnit.is_active == True,
            ColdStorageUnit.context == 'kitchen'  # Only kitchen units
        ).all()
        
        if not units:
            return jsonify({'success': False, 'error': 'No units selected'}), 400
        
        # Generate PDF
        pdf_buffer = generate_temperature_log_pdf(units, start_date, end_date)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'temperature_log_{start_date}_{end_date}.pdf'
        )
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@checklist_bp.route('/bar/cold-storage/pdf', methods=['POST'])
@login_required
@role_required(['Manager', 'Bartender', 'Chef'])
def generate_temperature_log_pdf():
    """Generate PDF for temperature logs"""
    try:
        from utils.pdf_generator import generate_temperature_log_pdf
        
        data = request.get_json()
        unit_ids = data.get('unit_ids', [])
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        
        org_filter = get_organization_filter(ColdStorageUnit)
        # Filter by bar context
        units = ColdStorageUnit.query.filter(org_filter).filter(
            ColdStorageUnit.id.in_(unit_ids),
            ColdStorageUnit.is_active == True,
            ColdStorageUnit.context == 'bar'  # Only bar units
        ).all()
        
        if not units:
            return jsonify({'success': False, 'error': 'No units selected'}), 400
        
        # Generate PDF
        pdf_buffer = generate_temperature_log_pdf(units, start_date, end_date)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'temperature_log_{start_date}_{end_date}.pdf'
        )
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# WASHING UNIT MANAGEMENT ROUTES
# ============================================

@checklist_bp.route('/bar/glass-washer/units', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def manage_bar_glass_washer_units():
    """API endpoint for managing bar glass washer units - Manager only for create/update/delete"""
    if request.method == 'GET':
        try:
            org_filter = get_organization_filter(WashingUnit)
            units = WashingUnit.query.filter(org_filter).filter_by(
                is_active=True,
                unit_type='bar_glass_washer'
            ).order_by(WashingUnit.unit_name).all()
            return jsonify([{
                'id': unit.id,
                'unit_name': unit.unit_name,
                'description': unit.description,
                'unit_type': unit.unit_type
            } for unit in units])
        except Exception as e:
            current_app.logger.error(f"Error loading units: {str(e)}", exc_info=True)
            return jsonify([])
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'create':
                if current_user.user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can create new units'}), 403
                
                unit_name = data.get('unit_name', '').strip()
                description = data.get('description', '').strip()
                
                if not unit_name:
                    return jsonify({'success': False, 'error': 'Unit name is required'}), 400
                
                try:
                    org_filter = get_organization_filter(WashingUnit)
                    existing_unit = WashingUnit.query.filter(org_filter).filter_by(
                        unit_name=unit_name,
                        unit_type='bar_glass_washer',
                        is_active=True
                    ).first()
                    
                    if existing_unit:
                        return jsonify({'success': False, 'error': f'Unit name "{unit_name}" already exists'}), 400
                    
                    unit = WashingUnit(
                        unit_name=unit_name,
                        unit_type='bar_glass_washer',
                        description=description,
                        organisation=current_user.organisation or current_user.restaurant_bar_name,
                        created_by=current_user.id,
                        is_active=True
                    )
                    db.session.add(unit)
                    db.session.commit()
                    
                    return jsonify({'success': True, 'unit': {
                        'id': unit.id,
                        'unit_name': unit.unit_name,
                        'description': unit.description,
                        'unit_type': unit.unit_type
                    }})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error creating unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error creating unit: {str(e)}'}), 500
            
            elif action == 'update':
                if current_user.user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can update units'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                
                try:
                    unit = WashingUnit.query.get(data['id'])
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found'}), 404
                    
                    org_filter = get_organization_filter(WashingUnit)
                    if not WashingUnit.query.filter(org_filter).filter_by(id=unit.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    unit.unit_name = data.get('unit_name', unit.unit_name)
                    unit.description = data.get('description', unit.description)
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error updating unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error updating unit: {str(e)}'}), 500
            
            elif action == 'delete':
                if current_user.user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can delete units'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                
                try:
                    unit = WashingUnit.query.get(data['id'])
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found'}), 404
                    
                    org_filter = get_organization_filter(WashingUnit)
                    if not WashingUnit.query.filter(org_filter).filter_by(id=unit.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    # Soft delete - set is_active to False (historical records remain)
                    unit.is_active = False
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error deleting unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error deleting unit: {str(e)}'}), 500
            
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500


@checklist_bp.route('/kitchen/dish-washer/units', methods=['GET', 'POST'])
@login_required
@role_required(['Chef', 'Manager'])
def manage_kitchen_dish_washer_units():
    """API endpoint for managing kitchen dish washer units - Manager only for create/update/delete"""
    if request.method == 'GET':
        try:
            org_filter = get_organization_filter(WashingUnit)
            units = WashingUnit.query.filter(org_filter).filter_by(
                is_active=True,
                unit_type='kitchen_dish_washer'
            ).order_by(WashingUnit.unit_name).all()
            return jsonify([{
                'id': unit.id,
                'unit_name': unit.unit_name,
                'description': unit.description,
                'unit_type': unit.unit_type
            } for unit in units])
        except Exception as e:
            current_app.logger.error(f"Error loading units: {str(e)}", exc_info=True)
            return jsonify([])
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'create':
                if current_user.user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can create new units'}), 403
                
                unit_name = data.get('unit_name', '').strip()
                description = data.get('description', '').strip()
                
                if not unit_name:
                    return jsonify({'success': False, 'error': 'Unit name is required'}), 400
                
                try:
                    org_filter = get_organization_filter(WashingUnit)
                    existing_unit = WashingUnit.query.filter(org_filter).filter_by(
                        unit_name=unit_name,
                        unit_type='kitchen_dish_washer',
                        is_active=True
                    ).first()
                    
                    if existing_unit:
                        return jsonify({'success': False, 'error': f'Unit name "{unit_name}" already exists'}), 400
                    
                    unit = WashingUnit(
                        unit_name=unit_name,
                        unit_type='kitchen_dish_washer',
                        description=description,
                        organisation=current_user.organisation or current_user.restaurant_bar_name,
                        created_by=current_user.id,
                        is_active=True
                    )
                    db.session.add(unit)
                    db.session.commit()
                    
                    return jsonify({'success': True, 'unit': {
                        'id': unit.id,
                        'unit_name': unit.unit_name,
                        'description': unit.description,
                        'unit_type': unit.unit_type
                    }})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error creating unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error creating unit: {str(e)}'}), 500
            
            elif action == 'update':
                if current_user.user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can update units'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                
                try:
                    unit = WashingUnit.query.get(data['id'])
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found'}), 404
                    
                    org_filter = get_organization_filter(WashingUnit)
                    if not WashingUnit.query.filter(org_filter).filter_by(id=unit.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    unit.unit_name = data.get('unit_name', unit.unit_name)
                    unit.description = data.get('description', unit.description)
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error updating unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error updating unit: {str(e)}'}), 500
            
            elif action == 'delete':
                if current_user.user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can delete units'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                
                try:
                    unit = WashingUnit.query.get(data['id'])
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found'}), 404
                    
                    org_filter = get_organization_filter(WashingUnit)
                    if not WashingUnit.query.filter(org_filter).filter_by(id=unit.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    # Soft delete - set is_active to False (historical records remain)
                    unit.is_active = False
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error deleting unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error deleting unit: {str(e)}'}), 500
            
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500

# ============================================
# BAR GLASS WASHER CHECKLIST ROUTES
# ============================================

@checklist_bp.route('/bar/glass-washer', methods=['GET'])
@login_required
@role_required(['Manager', 'Bartender'])
def bar_glass_washer_checklist():
    """Bar Glass Washer Checklist page"""
    today = date.today()
    return render_template('checklist/bar_glass_washer_checklist.html', today=today)


@checklist_bp.route('/bar/glass-washer/entries', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def bar_glass_washer_entries():
    """API endpoint for bar glass washer checklist entries"""
    if request.method == 'GET':
        try:
            unit_id = request.args.get('unit_id', type=int)
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            org_filter = get_organization_filter(BarGlassWasherChecklist)
            query = BarGlassWasherChecklist.query.filter(org_filter)
            
            if unit_id:
                query = query.filter_by(unit_id=unit_id)
            if start_date:
                query = query.filter(BarGlassWasherChecklist.entry_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
            if end_date:
                query = query.filter(BarGlassWasherChecklist.entry_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
            
            entries = query.order_by(BarGlassWasherChecklist.entry_date.desc(), BarGlassWasherChecklist.entry_time.desc()).all()
            
            return jsonify([{
                'id': entry.id,
                'unit_id': entry.unit_id,
                'unit_name': entry.unit.unit_name if entry.unit else 'Unknown',
                'entry_date': entry.entry_date.isoformat(),
                'entry_time': entry.entry_time,
                'staff_name': entry.staff_name,
                'wash_temperature': entry.wash_temperature,
                'rinse_sanitising_temperature': entry.rinse_sanitising_temperature,
                'sanitising_method': entry.sanitising_method,
                'pass_fail': entry.pass_fail,
                'corrective_action': entry.corrective_action,
                'staff_initials': entry.staff_initials,
                'manager_verification_initials': entry.manager_verification_initials,
                'manager_verified': entry.manager_verified,
                'manager_verified_at': entry.manager_verified_at.isoformat() if entry.manager_verified_at else None,
                'created_at': entry.created_at.isoformat() if entry.created_at else None
            } for entry in entries])
        except Exception as e:
            current_app.logger.error(f"Error loading entries: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'create':
                # Validate required fields
                unit_id = data.get('unit_id')
                entry_date_str = data.get('entry_date')
                entry_time = data.get('entry_time', '').strip()
                wash_temperature = data.get('wash_temperature')
                rinse_sanitising_temperature = data.get('rinse_sanitising_temperature')
                sanitising_method = data.get('sanitising_method')
                staff_initials = data.get('staff_initials', '').strip()
                corrective_action = data.get('corrective_action', '').strip()
                
                if not unit_id:
                    return jsonify({'success': False, 'error': 'Unit is required'}), 400
                if not entry_date_str:
                    return jsonify({'success': False, 'error': 'Date is required'}), 400
                if not entry_time:
                    return jsonify({'success': False, 'error': 'Time is required'}), 400
                if wash_temperature is None:
                    return jsonify({'success': False, 'error': 'Wash temperature is required'}), 400
                if not sanitising_method:
                    return jsonify({'success': False, 'error': 'Sanitising method is required'}), 400
                if not staff_initials:
                    return jsonify({'success': False, 'error': 'Staff initials are required'}), 400
                
                # Check if unit exists and user has access
                org_filter = get_organization_filter(WashingUnit)
                unit = WashingUnit.query.filter(org_filter).filter_by(id=unit_id, is_active=True).first()
                if not unit:
                    return jsonify({'success': False, 'error': 'Unit not found or unauthorized'}), 404
                
                # Parse date
                entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').date()
                
                # Convert temperatures to float
                try:
                    wash_temperature = float(wash_temperature)
                    rinse_sanitising_temperature = float(rinse_sanitising_temperature) if rinse_sanitising_temperature else None
                except (ValueError, TypeError):
                    return jsonify({'success': False, 'error': 'Invalid temperature values'}), 400
                
                # Get staff name from current user
                staff_name = get_user_display_name(current_user)
                
                # Create entry
                entry = BarGlassWasherChecklist(
                    unit_id=unit_id,
                    entry_date=entry_date,
                    entry_time=entry_time,
                    staff_name=staff_name,
                    wash_temperature=wash_temperature,
                    rinse_sanitising_temperature=rinse_sanitising_temperature,
                    sanitising_method=sanitising_method,
                    staff_initials=staff_initials,
                    corrective_action=corrective_action if corrective_action else None,
                    organisation=current_user.organisation or current_user.restaurant_bar_name,
                    created_by=current_user.id
                )
                
                # Calculate pass/fail
                entry.pass_fail = entry.calculate_pass_fail()
                
                # Validate: if fail, corrective action is mandatory
                if entry.pass_fail == 'Fail' and not corrective_action:
                    return jsonify({'success': False, 'error': 'Corrective action is required when result is Fail'}), 400
                
                db.session.add(entry)
                db.session.commit()
                
                return jsonify({'success': True, 'entry': {
                    'id': entry.id,
                    'pass_fail': entry.pass_fail
                }})
            
            elif action == 'verify':
                # Only managers can verify
                if current_user.user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can verify entries'}), 403
                
                entry_id = data.get('entry_id')
                manager_initials = data.get('manager_initials', '').strip()
                
                if not entry_id:
                    return jsonify({'success': False, 'error': 'Entry ID is required'}), 400
                if not manager_initials:
                    return jsonify({'success': False, 'error': 'Manager verification initials are required'}), 400
                
                org_filter = get_organization_filter(BarGlassWasherChecklist)
                entry = BarGlassWasherChecklist.query.filter(org_filter).filter_by(id=entry_id).first()
                if not entry:
                    return jsonify({'success': False, 'error': 'Entry not found or unauthorized'}), 404
                
                if entry.manager_verified:
                    return jsonify({'success': False, 'error': 'Entry already verified'}), 400
                
                entry.manager_verification_initials = manager_initials
                entry.manager_verified = True
                entry.manager_verified_at = datetime.utcnow()
                entry.verified_by = current_user.id
                
                db.session.commit()
                
                return jsonify({'success': True})
            
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in bar_glass_washer_entries: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# KITCHEN DISH WASHER CHECKLIST ROUTES
# ============================================

@checklist_bp.route('/kitchen/dish-washer', methods=['GET'])
@login_required
@role_required(['Chef', 'Manager'])
def kitchen_dish_washer_checklist():
    """Kitchen Dish Washer Checklist page"""
    today = date.today()
    return render_template('checklist/kitchen_dish_washer_checklist.html', today=today)


@checklist_bp.route('/kitchen/dish-washer/entries', methods=['GET', 'POST'])
@login_required
@role_required(['Chef', 'Manager'])
def kitchen_dish_washer_entries():
    """API endpoint for kitchen dish washer checklist entries"""
    if request.method == 'GET':
        try:
            unit_id = request.args.get('unit_id', type=int)
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            org_filter = get_organization_filter(KitchenDishWasherChecklist)
            query = KitchenDishWasherChecklist.query.filter(org_filter)
            
            if unit_id:
                query = query.filter_by(unit_id=unit_id)
            if start_date:
                query = query.filter(KitchenDishWasherChecklist.entry_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
            if end_date:
                query = query.filter(KitchenDishWasherChecklist.entry_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
            
            entries = query.order_by(KitchenDishWasherChecklist.entry_date.desc(), KitchenDishWasherChecklist.entry_time.desc()).all()
            
            return jsonify([{
                'id': entry.id,
                'unit_id': entry.unit_id,
                'unit_name': entry.unit.unit_name if entry.unit else 'Unknown',
                'entry_date': entry.entry_date.isoformat(),
                'entry_time': entry.entry_time,
                'staff_name': entry.staff_name,
                'wash_temperature': entry.wash_temperature,
                'final_rinse_temperature': entry.final_rinse_temperature,
                'pass_fail': entry.pass_fail,
                'corrective_action': entry.corrective_action,
                'staff_initials': entry.staff_initials,
                'manager_verification_initials': entry.manager_verification_initials,
                'manager_verified': entry.manager_verified,
                'manager_verified_at': entry.manager_verified_at.isoformat() if entry.manager_verified_at else None,
                'created_at': entry.created_at.isoformat() if entry.created_at else None
            } for entry in entries])
        except Exception as e:
            current_app.logger.error(f"Error loading entries: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'create':
                # Validate required fields
                unit_id = data.get('unit_id')
                entry_date_str = data.get('entry_date')
                entry_time = data.get('entry_time', '').strip()
                wash_temperature = data.get('wash_temperature')
                final_rinse_temperature = data.get('final_rinse_temperature')
                staff_initials = data.get('staff_initials', '').strip()
                corrective_action = data.get('corrective_action', '').strip()
                
                if not unit_id:
                    return jsonify({'success': False, 'error': 'Unit is required'}), 400
                if not entry_date_str:
                    return jsonify({'success': False, 'error': 'Date is required'}), 400
                if not entry_time:
                    return jsonify({'success': False, 'error': 'Time is required'}), 400
                if wash_temperature is None:
                    return jsonify({'success': False, 'error': 'Wash temperature is required'}), 400
                if final_rinse_temperature is None:
                    return jsonify({'success': False, 'error': 'Final rinse temperature is required'}), 400
                if not staff_initials:
                    return jsonify({'success': False, 'error': 'Staff initials are required'}), 400
                
                # Check if unit exists and user has access
                org_filter = get_organization_filter(WashingUnit)
                unit = WashingUnit.query.filter(org_filter).filter_by(id=unit_id, is_active=True).first()
                if not unit:
                    return jsonify({'success': False, 'error': 'Unit not found or unauthorized'}), 404
                
                # Parse date
                entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').date()
                
                # Convert temperatures to float
                try:
                    wash_temperature = float(wash_temperature)
                    final_rinse_temperature = float(final_rinse_temperature)
                except (ValueError, TypeError):
                    return jsonify({'success': False, 'error': 'Invalid temperature values'}), 400
                
                # Get staff name from current user
                staff_name = get_user_display_name(current_user)
                
                # Create entry
                entry = KitchenDishWasherChecklist(
                    unit_id=unit_id,
                    entry_date=entry_date,
                    entry_time=entry_time,
                    staff_name=staff_name,
                    wash_temperature=wash_temperature,
                    final_rinse_temperature=final_rinse_temperature,
                    staff_initials=staff_initials,
                    corrective_action=corrective_action if corrective_action else None,
                    organisation=current_user.organisation or current_user.restaurant_bar_name,
                    created_by=current_user.id
                )
                
                # Calculate pass/fail
                entry.pass_fail = entry.calculate_pass_fail()
                
                # Validate: if fail, corrective action is mandatory
                if entry.pass_fail == 'Fail' and not corrective_action:
                    return jsonify({'success': False, 'error': 'Corrective action is required when result is Fail'}), 400
                
                db.session.add(entry)
                db.session.commit()
                
                return jsonify({'success': True, 'entry': {
                    'id': entry.id,
                    'pass_fail': entry.pass_fail
                }})
            
            elif action == 'verify':
                # Only managers can verify
                if current_user.user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can verify entries'}), 403
                
                entry_id = data.get('entry_id')
                manager_initials = data.get('manager_initials', '').strip()
                
                if not entry_id:
                    return jsonify({'success': False, 'error': 'Entry ID is required'}), 400
                if not manager_initials:
                    return jsonify({'success': False, 'error': 'Manager verification initials are required'}), 400
                
                org_filter = get_organization_filter(KitchenDishWasherChecklist)
                entry = KitchenDishWasherChecklist.query.filter(org_filter).filter_by(id=entry_id).first()
                if not entry:
                    return jsonify({'success': False, 'error': 'Entry not found or unauthorized'}), 404
                
                if entry.manager_verified:
                    return jsonify({'success': False, 'error': 'Entry already verified'}), 400
                
                entry.manager_verification_initials = manager_initials
                entry.manager_verified = True
                entry.manager_verified_at = datetime.utcnow()
                entry.verified_by = current_user.id
                
                db.session.commit()
                
                return jsonify({'success': True})
            
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in kitchen_dish_washer_entries: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# KITCHEN GLASS WASHER CHECKLIST ROUTES
# ============================================

@checklist_bp.route('/kitchen/glass-washer', methods=['GET'])
@login_required
@role_required(['Chef', 'Manager'])
def kitchen_glass_washer_checklist():
    """Kitchen Glass Washer Checklist page"""
    today = date.today()
    return render_template('checklist/kitchen_glass_washer_checklist.html', today=today)


@checklist_bp.route('/kitchen/glass-washer/units', methods=['GET', 'POST'])
@login_required
@role_required(['Chef', 'Manager'])
def manage_kitchen_glass_washer_units():
    """API endpoint for managing kitchen glass washer units - Manager only for create/update/delete"""
    if request.method == 'GET':
        try:
            org_filter = get_organization_filter(WashingUnit)
            units = WashingUnit.query.filter(org_filter).filter_by(
                is_active=True,
                unit_type='kitchen_glass_washer'
            ).order_by(WashingUnit.unit_name).all()
            return jsonify([{
                'id': unit.id,
                'unit_name': unit.unit_name,
                'description': unit.description,
                'unit_type': unit.unit_type
            } for unit in units])
        except Exception as e:
            current_app.logger.error(f"Error loading units: {str(e)}", exc_info=True)
            return jsonify([])
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'create':
                if current_user.user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can create new units'}), 403
                
                unit_name = data.get('unit_name', '').strip()
                description = data.get('description', '').strip()
                
                if not unit_name:
                    return jsonify({'success': False, 'error': 'Unit name is required'}), 400
                
                try:
                    org_filter = get_organization_filter(WashingUnit)
                    existing_unit = WashingUnit.query.filter(org_filter).filter_by(
                        unit_name=unit_name,
                        unit_type='kitchen_glass_washer',
                        is_active=True
                    ).first()
                    
                    if existing_unit:
                        return jsonify({'success': False, 'error': f'Unit name "{unit_name}" already exists'}), 400
                    
                    unit = WashingUnit(
                        unit_name=unit_name,
                        unit_type='kitchen_glass_washer',
                        description=description,
                        organisation=current_user.organisation or current_user.restaurant_bar_name,
                        created_by=current_user.id,
                        is_active=True
                    )
                    db.session.add(unit)
                    db.session.commit()
                    
                    return jsonify({'success': True, 'unit': {
                        'id': unit.id,
                        'unit_name': unit.unit_name,
                        'description': unit.description,
                        'unit_type': unit.unit_type
                    }})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error creating unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error creating unit: {str(e)}'}), 500
            
            elif action == 'update':
                if current_user.user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can update units'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                
                try:
                    unit = WashingUnit.query.get(data['id'])
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found'}), 404
                    
                    org_filter = get_organization_filter(WashingUnit)
                    if not WashingUnit.query.filter(org_filter).filter_by(id=unit.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    unit.unit_name = data.get('unit_name', unit.unit_name)
                    unit.description = data.get('description', unit.description)
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error updating unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error updating unit: {str(e)}'}), 500
            
            elif action == 'delete':
                if current_user.user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can delete units'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                
                try:
                    unit = WashingUnit.query.get(data['id'])
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found'}), 404
                    
                    org_filter = get_organization_filter(WashingUnit)
                    if not WashingUnit.query.filter(org_filter).filter_by(id=unit.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    # Soft delete - set is_active to False (historical records remain)
                    unit.is_active = False
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error deleting unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error deleting unit: {str(e)}'}), 500
            
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500


@checklist_bp.route('/kitchen/glass-washer/entries', methods=['GET', 'POST'])
@login_required
@role_required(['Chef', 'Manager'])
def kitchen_glass_washer_entries():
    """API endpoint for kitchen glass washer checklist entries"""
    if request.method == 'GET':
        try:
            unit_id = request.args.get('unit_id', type=int)
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            org_filter = get_organization_filter(KitchenGlassWasherChecklist)
            query = KitchenGlassWasherChecklist.query.filter(org_filter)
            
            if unit_id:
                query = query.filter_by(unit_id=unit_id)
            if start_date:
                query = query.filter(KitchenGlassWasherChecklist.entry_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
            if end_date:
                query = query.filter(KitchenGlassWasherChecklist.entry_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
            
            entries = query.order_by(KitchenGlassWasherChecklist.entry_date.desc(), KitchenGlassWasherChecklist.entry_time.desc()).all()
            
            return jsonify([{
                'id': entry.id,
                'unit_id': entry.unit_id,
                'unit_name': entry.unit.unit_name if entry.unit else 'Unknown',
                'entry_date': entry.entry_date.isoformat(),
                'entry_time': entry.entry_time,
                'staff_name': entry.staff_name,
                'wash_temperature': entry.wash_temperature,
                'rinse_sanitising_temperature': entry.rinse_sanitising_temperature,
                'sanitising_method': entry.sanitising_method,
                'pass_fail': entry.pass_fail,
                'corrective_action': entry.corrective_action,
                'staff_initials': entry.staff_initials,
                'manager_verification_initials': entry.manager_verification_initials,
                'manager_verified': entry.manager_verified,
                'manager_verified_at': entry.manager_verified_at.isoformat() if entry.manager_verified_at else None,
                'created_at': entry.created_at.isoformat() if entry.created_at else None
            } for entry in entries])
        except Exception as e:
            current_app.logger.error(f"Error loading entries: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'create':
                # Validate required fields
                unit_id = data.get('unit_id')
                entry_date_str = data.get('entry_date')
                entry_time = data.get('entry_time', '').strip()
                wash_temperature = data.get('wash_temperature')
                rinse_sanitising_temperature = data.get('rinse_sanitising_temperature')
                sanitising_method = data.get('sanitising_method')
                staff_initials = data.get('staff_initials', '').strip()
                corrective_action = data.get('corrective_action', '').strip()
                
                if not unit_id:
                    return jsonify({'success': False, 'error': 'Unit is required'}), 400
                if not entry_date_str:
                    return jsonify({'success': False, 'error': 'Date is required'}), 400
                if not entry_time:
                    return jsonify({'success': False, 'error': 'Time is required'}), 400
                if wash_temperature is None:
                    return jsonify({'success': False, 'error': 'Wash temperature is required'}), 400
                if not sanitising_method:
                    return jsonify({'success': False, 'error': 'Sanitising method is required'}), 400
                if not staff_initials:
                    return jsonify({'success': False, 'error': 'Staff initials are required'}), 400
                
                # Check if unit exists and user has access
                org_filter = get_organization_filter(WashingUnit)
                unit = WashingUnit.query.filter(org_filter).filter_by(id=unit_id, is_active=True).first()
                if not unit:
                    return jsonify({'success': False, 'error': 'Unit not found or unauthorized'}), 404
                
                # Parse date
                entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').date()
                
                # Convert temperatures to float
                try:
                    wash_temperature = float(wash_temperature)
                    rinse_sanitising_temperature = float(rinse_sanitising_temperature) if rinse_sanitising_temperature else None
                except (ValueError, TypeError):
                    return jsonify({'success': False, 'error': 'Invalid temperature values'}), 400
                
                # Get staff name from current user
                staff_name = get_user_display_name(current_user)
                
                # Create entry
                entry = KitchenGlassWasherChecklist(
                    unit_id=unit_id,
                    entry_date=entry_date,
                    entry_time=entry_time,
                    staff_name=staff_name,
                    wash_temperature=wash_temperature,
                    rinse_sanitising_temperature=rinse_sanitising_temperature,
                    sanitising_method=sanitising_method,
                    staff_initials=staff_initials,
                    corrective_action=corrective_action if corrective_action else None,
                    organisation=current_user.organisation or current_user.restaurant_bar_name,
                    created_by=current_user.id
                )
                
                # Calculate pass/fail
                entry.pass_fail = entry.calculate_pass_fail()
                
                # Validate: if fail, corrective action is mandatory
                if entry.pass_fail == 'Fail' and not corrective_action:
                    return jsonify({'success': False, 'error': 'Corrective action is required when result is Fail'}), 400
                
                db.session.add(entry)
                db.session.commit()
                
                return jsonify({'success': True, 'entry': {
                    'id': entry.id,
                    'pass_fail': entry.pass_fail
                }})
            
            elif action == 'verify':
                # Only managers can verify
                if current_user.user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can verify entries'}), 403
                
                entry_id = data.get('entry_id')
                manager_initials = data.get('manager_initials', '').strip()
                
                if not entry_id:
                    return jsonify({'success': False, 'error': 'Entry ID is required'}), 400
                if not manager_initials:
                    return jsonify({'success': False, 'error': 'Manager verification initials are required'}), 400
                
                org_filter = get_organization_filter(KitchenGlassWasherChecklist)
                entry = KitchenGlassWasherChecklist.query.filter(org_filter).filter_by(id=entry_id).first()
                if not entry:
                    return jsonify({'success': False, 'error': 'Entry not found or unauthorized'}), 404
                
                if entry.manager_verified:
                    return jsonify({'success': False, 'error': 'Entry already verified'}), 400
                
                entry.manager_verification_initials = manager_initials
                entry.manager_verified = True
                entry.manager_verified_at = datetime.utcnow()
                entry.verified_by = current_user.id
                
                db.session.commit()
                
                return jsonify({'success': True})
            
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in kitchen_glass_washer_entries: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500


# BAR CLOSING CHECKLIST ROUTES
# ============================================

@checklist_bp.route('/bar/closing', methods=['GET'])
@login_required
@role_required(['Manager', 'Bartender'])
def bar_closing_checklist():
    """BAR Closing Checklist page - accessible to Manager and Bartender"""
    today = date.today()
    return render_template('checklist/coffee_machine_cleaning_checklist.html', today=today)


@checklist_bp.route('/bar/closing/units', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def manage_bar_closing_units():
    """API endpoint for managing BAR closing checklist units - Manager only for create/update/delete"""
    if request.method == 'GET':
        try:
            org_filter = get_organization_filter(BarClosingChecklistUnit)
            units = BarClosingChecklistUnit.query.filter(org_filter).filter_by(
                is_active=True
            ).order_by(BarClosingChecklistUnit.unit_name).all()
            return jsonify([{
                'id': unit.id,
                'unit_name': unit.unit_name,
                'description': unit.description
            } for unit in units])
        except Exception as e:
            current_app.logger.error(f"Error loading units: {str(e)}", exc_info=True)
            return jsonify([])
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'create':
                # Normalize role check - strip whitespace and handle None
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    current_app.logger.warning(f"Non-Manager user {current_user.id} (role: '{current_user.user_role}') attempted to create unit")
                    return jsonify({'success': False, 'error': 'Only Managers can create new units'}), 403
                
                unit_name = data.get('unit_name', '').strip() or 'BAR'
                description = data.get('description', '').strip()
                
                try:
                    org_filter = get_organization_filter(BarClosingChecklistUnit)
                    existing_unit = BarClosingChecklistUnit.query.filter(org_filter).filter_by(
                        unit_name=unit_name,
                        is_active=True
                    ).first()
                    
                    if existing_unit:
                        return jsonify({'success': False, 'error': f'Unit name "{unit_name}" already exists'}), 400
                    
                    # Ensure organisation is not None or empty string
                    organisation = (current_user.organisation or current_user.restaurant_bar_name or '').strip()
                    if not organisation:
                        return jsonify({'success': False, 'error': 'User organization is required to create units'}), 400
                    
                    unit = BarClosingChecklistUnit(
                        unit_name=unit_name,
                        description=description,
                        organisation=organisation,
                        created_by=current_user.id,
                        is_active=True
                    )
                    db.session.add(unit)
                    db.session.commit()
                    
                    current_app.logger.info(f"Manager {current_user.id} created coffee machine unit {unit.id} ({unit.unit_name})")
                    return jsonify({'success': True, 'unit': {
                        'id': unit.id,
                        'unit_name': unit.unit_name,
                        'description': unit.description
                    }})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error creating unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error creating unit: {str(e)}'}), 500
            
            elif action == 'update':
                # Normalize role check - strip whitespace and handle None
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can update units'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                
                try:
                    unit = BarClosingChecklistUnit.query.get(data['id'])
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found'}), 404
                    
                    org_filter = get_organization_filter(BarClosingChecklistUnit)
                    if not BarClosingChecklistUnit.query.filter(org_filter).filter_by(id=unit.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    unit.unit_name = data.get('unit_name', unit.unit_name)
                    unit.description = data.get('description', unit.description)
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error updating unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error updating unit: {str(e)}'}), 500
            
            elif action == 'delete':
                # Normalize role check - strip whitespace and handle None
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can delete units'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                
                try:
                    unit = BarClosingChecklistUnit.query.get(data['id'])
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found'}), 404
                    
                    org_filter = get_organization_filter(BarClosingChecklistUnit)
                    if not BarClosingChecklistUnit.query.filter(org_filter).filter_by(id=unit.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    # Soft delete - set is_active to False (historical records remain)
                    unit.is_active = False
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error deleting unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error deleting unit: {str(e)}'}), 500
            
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500


@checklist_bp.route('/bar/closing/points', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def manage_bar_closing_checklist_points():
    """API endpoint for managing checklist points - Manager only for create/update/delete"""
    if request.method == 'GET':
        try:
            unit_id = request.args.get('unit_id', type=int)
            if not unit_id:
                return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
            
            org_filter = get_organization_filter(BarClosingChecklistPoint)
            points = BarClosingChecklistPoint.query.filter(org_filter).filter_by(
                unit_id=unit_id,
                is_active=True
            ).order_by(BarClosingChecklistPoint.display_order).all()
            
            return jsonify([{
                'id': point.id,
                'unit_id': point.unit_id,
                'group_name': point.group_name,
                'point_text': point.point_text,
                'display_order': point.display_order
            } for point in points])
        except Exception as e:
            current_app.logger.error(f"Error loading checklist points: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'create':
                if current_user.user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can create checklist points'}), 403
                
                unit_id = data.get('unit_id')
                group_name = data.get('group_name', '').strip()
                point_text = data.get('point_text', '').strip()
                display_order = data.get('display_order')
                
                if not unit_id:
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                if not group_name:
                    return jsonify({'success': False, 'error': 'Group name is required'}), 400
                if not point_text:
                    return jsonify({'success': False, 'error': 'Checklist point text is required'}), 400
                if display_order is None:
                    return jsonify({'success': False, 'error': 'Display order is required'}), 400
                
                try:
                    # Verify unit exists and user has access
                    org_filter = get_organization_filter(BarClosingChecklistUnit)
                    unit = BarClosingChecklistUnit.query.filter(org_filter).filter_by(id=unit_id, is_active=True).first()
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found or unauthorized'}), 404
                    
                    point = BarClosingChecklistPoint(
                        unit_id=unit_id,
                        group_name=group_name,
                        point_text=point_text,
                        display_order=display_order,
                        organisation=current_user.organisation or current_user.restaurant_bar_name,
                        created_by=current_user.id,
                        is_active=True
                    )
                    db.session.add(point)
                    db.session.commit()
                    
                    return jsonify({'success': True, 'point': {
                        'id': point.id,
                        'unit_id': point.unit_id,
                        'group_name': point.group_name,
                        'point_text': point.point_text,
                        'display_order': point.display_order
                    }})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error creating checklist point: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error creating checklist point: {str(e)}'}), 500
            
            elif action == 'update':
                if current_user.user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can update checklist points'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Point ID is required'}), 400
                
                try:
                    point = BarClosingChecklistPoint.query.get(data['id'])
                    if not point:
                        return jsonify({'success': False, 'error': 'Checklist point not found'}), 404
                    
                    org_filter = get_organization_filter(BarClosingChecklistPoint)
                    if not BarClosingChecklistPoint.query.filter(org_filter).filter_by(id=point.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    if 'group_name' in data:
                        point.group_name = data['group_name']
                    if 'point_text' in data:
                        point.point_text = data['point_text']
                    if 'display_order' in data:
                        point.display_order = data['display_order']
                    
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error updating checklist point: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error updating checklist point: {str(e)}'}), 500
            
            elif action == 'delete':
                if current_user.user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can delete checklist points'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Point ID is required'}), 400
                
                try:
                    point = BarClosingChecklistPoint.query.get(data['id'])
                    if not point:
                        return jsonify({'success': False, 'error': 'Checklist point not found'}), 404
                    
                    org_filter = get_organization_filter(BarClosingChecklistPoint)
                    if not BarClosingChecklistPoint.query.filter(org_filter).filter_by(id=point.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    # Soft delete - set is_active to False
                    point.is_active = False
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error deleting checklist point: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error deleting checklist point: {str(e)}'}), 500
            
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500


@checklist_bp.route('/bar/closing/entries', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def bar_closing_checklist_entries():
    """API endpoint for BAR closing checklist entries"""
    if request.method == 'GET':
        try:
            unit_id = request.args.get('unit_id', type=int)
            entry_date_str = request.args.get('entry_date')
            
            if not unit_id or not entry_date_str:
                return jsonify({'success': False, 'error': 'Unit ID and entry date are required'}), 400
            
            entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').date()
            
            # Get or create entry
            org_filter = get_organization_filter(BarClosingChecklistEntry)
            entry = BarClosingChecklistEntry.query.filter(org_filter).filter_by(
                unit_id=unit_id,
                entry_date=entry_date
            ).first()
            
            if not entry:
                # Create new entry
                entry = BarClosingChecklistEntry(
                    unit_id=unit_id,
                    entry_date=entry_date,
                    organisation=current_user.organisation or current_user.restaurant_bar_name,
                    created_by=current_user.id
                )
                db.session.add(entry)
                db.session.commit()
            
            # Get all checklist points for this unit
            org_filter_points = get_organization_filter(BarClosingChecklistPoint)
            points = BarClosingChecklistPoint.query.filter(org_filter_points).filter_by(
                unit_id=unit_id,
                is_active=True
            ).order_by(BarClosingChecklistPoint.display_order).all()
            
            # Get all items for this entry
            items = {item.checklist_point_id: {
                'id': item.id,
                'is_completed': item.is_completed,
                'staff_initials': item.staff_initials
            } for item in entry.items.all()}
            
            # Build response with points and their completion status
            points_data = []
            for point in points:
                item = items.get(point.id)
                points_data.append({
                    'point_id': point.id,
                    'group_name': point.group_name,
                    'point_text': point.point_text,
                    'display_order': point.display_order,
                    'item_id': item['id'] if item else None,
                    'is_completed': item['is_completed'] if item else False,
                    'staff_initials': item['staff_initials'] if item else None
                })
            
            return jsonify({
                'success': True,
                'entry_id': entry.id,
                'unit_id': entry.unit_id,
                'entry_date': entry.entry_date.isoformat(),
                'points': points_data
            })
        except Exception as e:
            current_app.logger.error(f"Error loading entry: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'update_item':
                # Staff can update items (mark as completed, add initials)
                entry_id = data.get('entry_id')
                checklist_point_id = data.get('checklist_point_id')
                is_completed = data.get('is_completed', False)
                staff_initials = data.get('staff_initials', '').strip()
                
                if not entry_id or not checklist_point_id:
                    return jsonify({'success': False, 'error': 'Entry ID and checklist point ID are required'}), 400
                
                try:
                    # Verify entry exists and user has access
                    org_filter = get_organization_filter(BarClosingChecklistEntry)
                    entry = BarClosingChecklistEntry.query.filter(org_filter).filter_by(id=entry_id).first()
                    if not entry:
                        return jsonify({'success': False, 'error': 'Entry not found or unauthorized'}), 404
                    
                    # Get or create item
                    item = BarClosingChecklistItem.query.filter_by(
                        entry_id=entry_id,
                        checklist_point_id=checklist_point_id
                    ).first()
                    
                    if item:
                        # Update existing item
                        item.is_completed = is_completed
                        item.staff_initials = staff_initials if staff_initials else None
                    else:
                        # Create new item
                        item = BarClosingChecklistItem(
                            entry_id=entry_id,
                            checklist_point_id=checklist_point_id,
                            is_completed=is_completed,
                            staff_initials=staff_initials if staff_initials else None,
                            organisation=current_user.organisation or current_user.restaurant_bar_name
                        )
                        db.session.add(item)
                    
                    db.session.commit()
                    
                    return jsonify({
                        'success': True,
                        'item': {
                            'id': item.id,
                            'is_completed': item.is_completed,
                            'staff_initials': item.staff_initials
                        }
                    })
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error updating item: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error updating item: {str(e)}'}), 500
            
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500


@checklist_bp.route('/bar/closing/pdf', methods=['POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def generate_bar_closing_checklist_pdf():
    """Generate monthly PDF for BAR Closing Checklist - Available to Manager and Bartender"""
    try:
        from utils.pdf_generator import generate_bar_closing_checklist_pdf
        
        data = request.get_json()
        unit_id = data.get('unit_id')
        month = data.get('month')  # Format: 'YYYY-MM'
        year = data.get('year')
        
        if not unit_id:
            return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
        if not month and not year:
            return jsonify({'success': False, 'error': 'Month and year are required'}), 400
        
        # Parse month/year
        if month:
            year, month_num = map(int, month.split('-'))
        elif year:
            # If only year provided, use current month
            from datetime import date
            month_num = date.today().month
            year = int(year)
        else:
            return jsonify({'success': False, 'error': 'Month and year are required'}), 400
        
        # Verify unit exists and user has access
        org_filter = get_organization_filter(BarClosingChecklistUnit)
        unit = BarClosingChecklistUnit.query.filter(org_filter).filter_by(id=unit_id, is_active=True).first()
        if not unit:
            return jsonify({'success': False, 'error': 'Unit not found or unauthorized'}), 404
        
        # Generate PDF
        pdf_buffer = generate_bar_closing_checklist_pdf(unit, year, month_num)
        
        # Generate filename
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']
        filename = f'Coffee_Machine_Checklist_{month_names[month_num-1]}_{year}.pdf'
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# CHOPPING BOARD CHECKLIST ROUTES
# ============================================

@checklist_bp.route('/bar/chopping-board', methods=['GET'])
@login_required
@role_required(['Manager', 'Bartender'])
def chopping_board_checklist():
    """Chopping Board Cleaning & Sanitisation Checklist page - accessible to Manager and Bartender"""
    today = date.today()
    return render_template('checklist/chopping_board_checklist.html', today=today)


@checklist_bp.route('/bar/chopping-board/units', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def manage_chopping_board_units():
    """API endpoint for managing chopping board checklist units - Manager only for create/update/delete"""
    if request.method == 'GET':
        try:
            org_filter = get_organization_filter(ChoppingBoardChecklistUnit)
            units = ChoppingBoardChecklistUnit.query.filter(org_filter).filter_by(
                is_active=True
            ).order_by(ChoppingBoardChecklistUnit.unit_name).all()
            return jsonify([{
                'id': unit.id,
                'unit_name': unit.unit_name,
                'description': unit.description
            } for unit in units])
        except Exception as e:
            current_app.logger.error(f"Error loading units: {str(e)}", exc_info=True)
            return jsonify([])
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'create':
                # Normalize role check - strip whitespace and handle None
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    current_app.logger.warning(f"Non-Manager user {current_user.id} (role: '{current_user.user_role}') attempted to create unit")
                    return jsonify({'success': False, 'error': 'Only Managers can create new units'}), 403
                
                unit_name = data.get('unit_name', '').strip() or 'BAR'
                description = data.get('description', '').strip()
                
                try:
                    org_filter = get_organization_filter(ChoppingBoardChecklistUnit)
                    existing_unit = ChoppingBoardChecklistUnit.query.filter(org_filter).filter_by(
                        unit_name=unit_name,
                        is_active=True
                    ).first()
                    
                    if existing_unit:
                        return jsonify({'success': False, 'error': f'Unit name "{unit_name}" already exists'}), 400
                    
                    # Ensure organisation is not None or empty string
                    organisation = (current_user.organisation or current_user.restaurant_bar_name or '').strip()
                    if not organisation:
                        return jsonify({'success': False, 'error': 'User organization is required to create units'}), 400
                    
                    unit = ChoppingBoardChecklistUnit(
                        unit_name=unit_name,
                        description=description,
                        organisation=organisation,
                        created_by=current_user.id,
                        is_active=True
                    )
                    db.session.add(unit)
                    db.session.commit()
                    
                    current_app.logger.info(f"Manager {current_user.id} created chopping board unit {unit.id} ({unit.unit_name})")
                    return jsonify({'success': True, 'unit': {
                        'id': unit.id,
                        'unit_name': unit.unit_name,
                        'description': unit.description
                    }})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error creating unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error creating unit: {str(e)}'}), 500
            
            elif action == 'update':
                # Normalize role check - strip whitespace and handle None
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can update units'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                
                try:
                    unit = ChoppingBoardChecklistUnit.query.get(data['id'])
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found'}), 404
                    
                    org_filter = get_organization_filter(ChoppingBoardChecklistUnit)
                    if not ChoppingBoardChecklistUnit.query.filter(org_filter).filter_by(id=unit.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    unit.unit_name = data.get('unit_name', unit.unit_name)
                    unit.description = data.get('description', unit.description)
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error updating unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error updating unit: {str(e)}'}), 500
            
            elif action == 'delete':
                # Normalize role check - strip whitespace and handle None
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can delete units'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                
                try:
                    unit = ChoppingBoardChecklistUnit.query.get(data['id'])
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found'}), 404
                    
                    org_filter = get_organization_filter(ChoppingBoardChecklistUnit)
                    if not ChoppingBoardChecklistUnit.query.filter(org_filter).filter_by(id=unit.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    # Soft delete - set is_active to False (historical records remain)
                    unit.is_active = False
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error deleting unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error deleting unit: {str(e)}'}), 500
            
            else:
                return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            current_app.logger.error(f"Error in manage_chopping_board_units: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500


@checklist_bp.route('/bar/chopping-board/points', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def manage_chopping_board_points():
    """API endpoint for managing chopping board checklist points - Manager only for create/update/delete"""
    if request.method == 'GET':
        try:
            unit_id = request.args.get('unit_id', type=int)
            if not unit_id:
                return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
            
            org_filter = get_organization_filter(ChoppingBoardChecklistPoint)
            points = ChoppingBoardChecklistPoint.query.filter(org_filter).filter_by(
                unit_id=unit_id,
                is_active=True
            ).order_by(ChoppingBoardChecklistPoint.display_order).all()
            
            return jsonify([{
                'id': point.id,
                'unit_id': point.unit_id,
                'group_name': point.group_name,
                'point_text': point.point_text,
                'display_order': point.display_order
            } for point in points])
        except Exception as e:
            current_app.logger.error(f"Error loading checklist points: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'create':
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can create checklist points'}), 403
                
                unit_id = data.get('unit_id')
                group_name = data.get('group_name', '').strip() or 'Cleaning & Sanitisation'
                point_text = data.get('point_text', '').strip()
                display_order = data.get('display_order')
                
                if not unit_id:
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                if not point_text:
                    return jsonify({'success': False, 'error': 'Checklist point text is required'}), 400
                if display_order is None:
                    return jsonify({'success': False, 'error': 'Display order is required'}), 400
                
                try:
                    # Verify unit exists and user has access
                    org_filter = get_organization_filter(ChoppingBoardChecklistUnit)
                    unit = ChoppingBoardChecklistUnit.query.filter(org_filter).filter_by(id=unit_id, is_active=True).first()
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found or unauthorized'}), 404
                    
                    point = ChoppingBoardChecklistPoint(
                        unit_id=unit_id,
                        group_name=group_name,
                        point_text=point_text,
                        display_order=display_order,
                        organisation=current_user.organisation or current_user.restaurant_bar_name,
                        created_by=current_user.id,
                        is_active=True
                    )
                    db.session.add(point)
                    db.session.commit()
                    
                    return jsonify({'success': True, 'point': {
                        'id': point.id,
                        'unit_id': point.unit_id,
                        'group_name': point.group_name,
                        'point_text': point.point_text,
                        'display_order': point.display_order
                    }})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error creating checklist point: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error creating checklist point: {str(e)}'}), 500
            
            elif action == 'update':
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can update checklist points'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Point ID is required'}), 400
                
                try:
                    point = ChoppingBoardChecklistPoint.query.get(data['id'])
                    if not point:
                        return jsonify({'success': False, 'error': 'Checklist point not found'}), 404
                    
                    org_filter = get_organization_filter(ChoppingBoardChecklistPoint)
                    if not ChoppingBoardChecklistPoint.query.filter(org_filter).filter_by(id=point.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    if 'group_name' in data:
                        point.group_name = data['group_name']
                    if 'point_text' in data:
                        point.point_text = data['point_text']
                    if 'display_order' in data:
                        point.display_order = data['display_order']
                    
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error updating checklist point: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error updating checklist point: {str(e)}'}), 500
            
            elif action == 'delete':
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can delete checklist points'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Point ID is required'}), 400
                
                try:
                    point = ChoppingBoardChecklistPoint.query.get(data['id'])
                    if not point:
                        return jsonify({'success': False, 'error': 'Checklist point not found'}), 404
                    
                    org_filter = get_organization_filter(ChoppingBoardChecklistPoint)
                    if not ChoppingBoardChecklistPoint.query.filter(org_filter).filter_by(id=point.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    # Soft delete - set is_active to False
                    point.is_active = False
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error deleting checklist point: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error deleting checklist point: {str(e)}'}), 500
            
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500


@checklist_bp.route('/bar/chopping-board/entries', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def chopping_board_checklist_entries():
    """API endpoint for chopping board checklist entries"""
    if request.method == 'GET':
        try:
            unit_id = request.args.get('unit_id', type=int)
            entry_date_str = request.args.get('entry_date')
            
            if not unit_id or not entry_date_str:
                return jsonify({'success': False, 'error': 'Unit ID and entry date are required'}), 400
            
            entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').date()
            
            # Get or create entry
            org_filter = get_organization_filter(ChoppingBoardChecklistEntry)
            entry = ChoppingBoardChecklistEntry.query.filter(org_filter).filter_by(
                unit_id=unit_id,
                entry_date=entry_date
            ).first()
            
            if not entry:
                # Create new entry
                entry = ChoppingBoardChecklistEntry(
                    unit_id=unit_id,
                    entry_date=entry_date,
                    organisation=current_user.organisation or current_user.restaurant_bar_name,
                    created_by=current_user.id
                )
                db.session.add(entry)
                db.session.commit()
            
            # Get all checklist points for this unit
            org_filter_points = get_organization_filter(ChoppingBoardChecklistPoint)
            points = ChoppingBoardChecklistPoint.query.filter(org_filter_points).filter_by(
                unit_id=unit_id,
                is_active=True
            ).order_by(ChoppingBoardChecklistPoint.display_order).all()
            
            # Get all items for this entry
            items = {item.checklist_point_id: {
                'id': item.id,
                'is_completed': item.is_completed,
                'staff_initials': item.staff_initials
            } for item in entry.items.all()}
            
            # Build response with points and their completion status
            points_data = []
            for point in points:
                item = items.get(point.id)
                points_data.append({
                    'point_id': point.id,
                    'group_name': point.group_name,
                    'point_text': point.point_text,
                    'display_order': point.display_order,
                    'item_id': item['id'] if item else None,
                    'is_completed': item['is_completed'] if item else False,
                    'staff_initials': item['staff_initials'] if item else None
                })
            
            return jsonify({
                'success': True,
                'entry_id': entry.id,
                'unit_id': entry.unit_id,
                'entry_date': entry.entry_date.isoformat(),
                'points': points_data
            })
        except Exception as e:
            current_app.logger.error(f"Error loading entry: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'update_item':
                # Staff can update items (mark as completed, add initials)
                entry_id = data.get('entry_id')
                checklist_point_id = data.get('checklist_point_id')
                is_completed = data.get('is_completed', False)
                staff_initials = data.get('staff_initials', '').strip()
                
                if not entry_id or not checklist_point_id:
                    return jsonify({'success': False, 'error': 'Entry ID and checklist point ID are required'}), 400
                
                try:
                    # Verify entry exists and user has access
                    org_filter = get_organization_filter(ChoppingBoardChecklistEntry)
                    entry = ChoppingBoardChecklistEntry.query.filter(org_filter).filter_by(id=entry_id).first()
                    if not entry:
                        return jsonify({'success': False, 'error': 'Entry not found or unauthorized'}), 404
                    
                    # Get or create item
                    item = ChoppingBoardChecklistItem.query.filter_by(
                        entry_id=entry_id,
                        checklist_point_id=checklist_point_id
                    ).first()
                    
                    if item:
                        # Update existing item
                        item.is_completed = is_completed
                        item.staff_initials = staff_initials if staff_initials else None
                    else:
                        # Create new item
                        item = ChoppingBoardChecklistItem(
                            entry_id=entry_id,
                            checklist_point_id=checklist_point_id,
                            is_completed=is_completed,
                            staff_initials=staff_initials if staff_initials else None,
                            organisation=current_user.organisation or current_user.restaurant_bar_name
                        )
                        db.session.add(item)
                    
                    db.session.commit()
                    
                    return jsonify({
                        'success': True,
                        'item': {
                            'id': item.id,
                            'is_completed': item.is_completed,
                            'staff_initials': item.staff_initials
                        }
                    })
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error updating item: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error updating item: {str(e)}'}), 500
            
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500


@checklist_bp.route('/bar/chopping-board/pdf', methods=['POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def generate_chopping_board_checklist_pdf():
    """Generate monthly PDF for Chopping Board Checklist - Available to Manager and Bartender"""
    try:
        from utils.pdf_generator import generate_chopping_board_checklist_pdf
        
        data = request.get_json()
        unit_id = data.get('unit_id')
        month = data.get('month')  # Format: 'YYYY-MM'
        year = data.get('year')
        
        if not unit_id:
            return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
        if not month and not year:
            return jsonify({'success': False, 'error': 'Month and year are required'}), 400
        
        # Parse month/year
        if month:
            year, month_num = map(int, month.split('-'))
        elif year:
            # If only year provided, use current month
            from datetime import date
            month_num = date.today().month
            year = int(year)
        else:
            return jsonify({'success': False, 'error': 'Month and year are required'}), 400
        
        # Verify unit exists and user has access
        org_filter = get_organization_filter(ChoppingBoardChecklistUnit)
        unit = ChoppingBoardChecklistUnit.query.filter(org_filter).filter_by(id=unit_id, is_active=True).first()
        if not unit:
            return jsonify({'success': False, 'error': 'Unit not found or unauthorized'}), 404
        
        # Generate PDF
        pdf_buffer = generate_chopping_board_checklist_pdf(unit, year, month_num)
        
        # Generate filename
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']
        filename = f'BAR_ChoppingBoard_Checklist_{month_names[month_num-1]}_{year}.pdf'
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500



# ============================================
# KITCHEN CHOPPING BOARD CHECKLIST ROUTES
# ============================================

@checklist_bp.route('/kitchen/chopping-board', methods=['GET'])
@login_required
@role_required(['Chef', 'Manager'])
def kitchen_chopping_board_checklist():
    """Kitchen Chopping Board Cleaning & Sanitisation Checklist page - accessible to Chef and Manager"""
    today = date.today()
    return render_template('checklist/kitchen_chopping_board_checklist.html', today=today)


@checklist_bp.route('/kitchen/chopping-board/units', methods=['GET', 'POST'])
@login_required
@role_required(['Chef', 'Manager'])
def manage_kitchen_chopping_board_units():
    """API endpoint for managing kitchen chopping board checklist units - Manager only for create/update/delete"""
    if request.method == 'GET':
        try:
            org_filter = get_organization_filter(KitchenChoppingBoardChecklistUnit)
            units = KitchenChoppingBoardChecklistUnit.query.filter(org_filter).filter_by(
                is_active=True
            ).order_by(KitchenChoppingBoardChecklistUnit.unit_name).all()
            return jsonify([{
                'id': unit.id,
                'unit_name': unit.unit_name,
                'description': unit.description
            } for unit in units])
        except Exception as e:
            current_app.logger.error(f"Error loading units: {str(e)}", exc_info=True)
            return jsonify([])
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'create':
                # Normalize role check - strip whitespace and handle None
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    current_app.logger.warning(f"Non-Manager user {current_user.id} (role: '{current_user.user_role}') attempted to create unit")
                    return jsonify({'success': False, 'error': 'Only Managers can create new units'}), 403
                
                unit_name = data.get('unit_name', '').strip() or 'KITCHEN'
                description = data.get('description', '').strip()
                
                try:
                    org_filter = get_organization_filter(KitchenChoppingBoardChecklistUnit)
                    existing_unit = KitchenChoppingBoardChecklistUnit.query.filter(org_filter).filter_by(
                        unit_name=unit_name,
                        is_active=True
                    ).first()
                    
                    if existing_unit:
                        return jsonify({'success': False, 'error': f'Unit name "{unit_name}" already exists'}), 400
                    
                    # Ensure organisation is not None or empty string
                    organisation = (current_user.organisation or current_user.restaurant_bar_name or '').strip()
                    if not organisation:
                        return jsonify({'success': False, 'error': 'User organization is required to create units'}), 400
                    
                    unit = KitchenChoppingBoardChecklistUnit(
                        unit_name=unit_name,
                        description=description,
                        organisation=organisation,
                        created_by=current_user.id,
                        is_active=True
                    )
                    db.session.add(unit)
                    db.session.commit()
                    
                    current_app.logger.info(f"Manager {current_user.id} created kitchen chopping board unit {unit.id} ({unit.unit_name})")
                    return jsonify({'success': True, 'unit': {
                        'id': unit.id,
                        'unit_name': unit.unit_name,
                        'description': unit.description
                    }})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error creating unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error creating unit: {str(e)}'}), 500
            
            elif action == 'update':
                # Normalize role check - strip whitespace and handle None
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can update units'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                
                try:
                    unit = KitchenChoppingBoardChecklistUnit.query.get(data['id'])
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found'}), 404
                    
                    org_filter = get_organization_filter(KitchenChoppingBoardChecklistUnit)
                    if not KitchenChoppingBoardChecklistUnit.query.filter(org_filter).filter_by(id=unit.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    unit.unit_name = data.get('unit_name', unit.unit_name)
                    unit.description = data.get('description', unit.description)
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error updating unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error updating unit: {str(e)}'}), 500
            
            elif action == 'delete':
                # Normalize role check - strip whitespace and handle None
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can delete units'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                
                try:
                    unit = KitchenChoppingBoardChecklistUnit.query.get(data['id'])
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found'}), 404
                    
                    org_filter = get_organization_filter(KitchenChoppingBoardChecklistUnit)
                    if not KitchenChoppingBoardChecklistUnit.query.filter(org_filter).filter_by(id=unit.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    # Soft delete - set is_active to False (historical records remain)
                    unit.is_active = False
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error deleting unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error deleting unit: {str(e)}'}), 500
            
            else:
                return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            current_app.logger.error(f"Error in manage_chopping_board_units: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500


@checklist_bp.route('/kitchen/chopping-board/points', methods=['GET', 'POST'])
@login_required
@role_required(['Chef', 'Manager'])
def manage_kitchen_chopping_board_points():
    """API endpoint for managing kitchen chopping board checklist points - Manager only for create/update/delete"""
    if request.method == 'GET':
        try:
            unit_id = request.args.get('unit_id', type=int)
            if not unit_id:
                return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
            
            org_filter = get_organization_filter(KitchenChoppingBoardChecklistPoint)
            points = KitchenChoppingBoardChecklistPoint.query.filter(org_filter).filter_by(
                unit_id=unit_id,
                is_active=True
            ).order_by(KitchenChoppingBoardChecklistPoint.display_order).all()
            
            return jsonify([{
                'id': point.id,
                'unit_id': point.unit_id,
                'group_name': point.group_name,
                'point_text': point.point_text,
                'display_order': point.display_order
            } for point in points])
        except Exception as e:
            current_app.logger.error(f"Error loading checklist points: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'create':
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can create checklist points'}), 403
                
                unit_id = data.get('unit_id')
                group_name = data.get('group_name', '').strip() or 'Cleaning & Sanitisation'
                point_text = data.get('point_text', '').strip()
                display_order = data.get('display_order')
                
                if not unit_id:
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                if not point_text:
                    return jsonify({'success': False, 'error': 'Checklist point text is required'}), 400
                if display_order is None:
                    return jsonify({'success': False, 'error': 'Display order is required'}), 400
                
                try:
                    # Verify unit exists and user has access
                    org_filter = get_organization_filter(KitchenChoppingBoardChecklistUnit)
                    unit = KitchenChoppingBoardChecklistUnit.query.filter(org_filter).filter_by(id=unit_id, is_active=True).first()
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found or unauthorized'}), 404
                    
                    point = KitchenChoppingBoardChecklistPoint(
                        unit_id=unit_id,
                        group_name=group_name,
                        point_text=point_text,
                        display_order=display_order,
                        organisation=current_user.organisation or current_user.restaurant_bar_name,
                        created_by=current_user.id,
                        is_active=True
                    )
                    db.session.add(point)
                    db.session.commit()
                    
                    return jsonify({'success': True, 'point': {
                        'id': point.id,
                        'unit_id': point.unit_id,
                        'group_name': point.group_name,
                        'point_text': point.point_text,
                        'display_order': point.display_order
                    }})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error creating checklist point: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error creating checklist point: {str(e)}'}), 500
            
            elif action == 'update':
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can update checklist points'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Point ID is required'}), 400
                
                try:
                    point = KitchenChoppingBoardChecklistPoint.query.get(data['id'])
                    if not point:
                        return jsonify({'success': False, 'error': 'Checklist point not found'}), 404
                    
                    org_filter = get_organization_filter(KitchenChoppingBoardChecklistPoint)
                    if not KitchenChoppingBoardChecklistPoint.query.filter(org_filter).filter_by(id=point.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    if 'group_name' in data:
                        point.group_name = data['group_name']
                    if 'point_text' in data:
                        point.point_text = data['point_text']
                    if 'display_order' in data:
                        point.display_order = data['display_order']
                    
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error updating checklist point: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error updating checklist point: {str(e)}'}), 500
            
            elif action == 'delete':
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can delete checklist points'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Point ID is required'}), 400
                
                try:
                    point = KitchenChoppingBoardChecklistPoint.query.get(data['id'])
                    if not point:
                        return jsonify({'success': False, 'error': 'Checklist point not found'}), 404
                    
                    org_filter = get_organization_filter(KitchenChoppingBoardChecklistPoint)
                    if not KitchenChoppingBoardChecklistPoint.query.filter(org_filter).filter_by(id=point.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    # Soft delete - set is_active to False
                    point.is_active = False
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error deleting checklist point: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error deleting checklist point: {str(e)}'}), 500
            
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500


@checklist_bp.route('/kitchen/chopping-board/entries', methods=['GET', 'POST'])
@login_required
@role_required(['Chef', 'Manager'])
def kitchen_chopping_board_checklist_entries():
    """API endpoint for kitchen chopping board checklist entries"""
    if request.method == 'GET':
        try:
            unit_id = request.args.get('unit_id', type=int)
            entry_date_str = request.args.get('entry_date')
            
            if not unit_id or not entry_date_str:
                return jsonify({'success': False, 'error': 'Unit ID and entry date are required'}), 400
            
            entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').date()
            
            # Get or create entry
            org_filter = get_organization_filter(KitchenChoppingBoardChecklistEntry)
            entry = KitchenChoppingBoardChecklistEntry.query.filter(org_filter).filter_by(
                unit_id=unit_id,
                entry_date=entry_date
            ).first()
            
            if not entry:
                # Create new entry
                entry = KitchenChoppingBoardChecklistEntry(
                    unit_id=unit_id,
                    entry_date=entry_date,
                    organisation=current_user.organisation or current_user.restaurant_bar_name,
                    created_by=current_user.id
                )
                db.session.add(entry)
                db.session.commit()
            
            # Get all checklist points for this unit
            org_filter_points = get_organization_filter(KitchenChoppingBoardChecklistPoint)
            points = KitchenChoppingBoardChecklistPoint.query.filter(org_filter_points).filter_by(
                unit_id=unit_id,
                is_active=True
            ).order_by(KitchenChoppingBoardChecklistPoint.display_order).all()
            
            # Get all items for this entry
            items = {item.checklist_point_id: {
                'id': item.id,
                'is_completed': item.is_completed,
                'staff_initials': item.staff_initials
            } for item in entry.items.all()}
            
            # Build response with points and their completion status
            points_data = []
            for point in points:
                item = items.get(point.id)
                points_data.append({
                    'point_id': point.id,
                    'group_name': point.group_name,
                    'point_text': point.point_text,
                    'display_order': point.display_order,
                    'item_id': item['id'] if item else None,
                    'is_completed': item['is_completed'] if item else False,
                    'staff_initials': item['staff_initials'] if item else None
                })
            
            return jsonify({
                'success': True,
                'entry_id': entry.id,
                'unit_id': entry.unit_id,
                'entry_date': entry.entry_date.isoformat(),
                'points': points_data
            })
        except Exception as e:
            current_app.logger.error(f"Error loading entry: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'update_item':
                # Staff can update items (mark as completed, add initials)
                entry_id = data.get('entry_id')
                checklist_point_id = data.get('checklist_point_id')
                is_completed = data.get('is_completed', False)
                staff_initials = data.get('staff_initials', '').strip()
                
                if not entry_id or not checklist_point_id:
                    return jsonify({'success': False, 'error': 'Entry ID and checklist point ID are required'}), 400
                
                try:
                    # Verify entry exists and user has access
                    org_filter = get_organization_filter(KitchenChoppingBoardChecklistEntry)
                    entry = KitchenChoppingBoardChecklistEntry.query.filter(org_filter).filter_by(id=entry_id).first()
                    if not entry:
                        return jsonify({'success': False, 'error': 'Entry not found or unauthorized'}), 404
                    
                    # Get or create item
                    item = KitchenChoppingBoardChecklistItem.query.filter_by(
                        entry_id=entry_id,
                        checklist_point_id=checklist_point_id
                    ).first()
                    
                    if item:
                        # Update existing item
                        item.is_completed = is_completed
                        item.staff_initials = staff_initials if staff_initials else None
                    else:
                        # Create new item
                        item = KitchenChoppingBoardChecklistItem(
                            entry_id=entry_id,
                            checklist_point_id=checklist_point_id,
                            is_completed=is_completed,
                            staff_initials=staff_initials if staff_initials else None,
                            organisation=current_user.organisation or current_user.restaurant_bar_name
                        )
                        db.session.add(item)
                    
                    db.session.commit()
                    
                    return jsonify({
                        'success': True,
                        'item': {
                            'id': item.id,
                            'is_completed': item.is_completed,
                            'staff_initials': item.staff_initials
                        }
                    })
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error updating item: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error updating item: {str(e)}'}), 500
            
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500


@checklist_bp.route('/kitchen/chopping-board/pdf', methods=['POST'])
@login_required
@role_required(['Chef', 'Manager'])
def generate_kitchen_chopping_board_checklist_pdf():
    """Generate monthly PDF for Chopping Board Checklist - Available to Manager and Bartender"""
    try:
        from utils.pdf_generator import generate_kitchen_chopping_board_checklist_pdf
        
        data = request.get_json()
        unit_id = data.get('unit_id')
        month = data.get('month')  # Format: 'YYYY-MM'
        year = data.get('year')
        
        if not unit_id:
            return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
        if not month and not year:
            return jsonify({'success': False, 'error': 'Month and year are required'}), 400
        
        # Parse month/year
        if month:
            year, month_num = map(int, month.split('-'))
        elif year:
            # If only year provided, use current month
            from datetime import date
            month_num = date.today().month
            year = int(year)
        else:
            return jsonify({'success': False, 'error': 'Month and year are required'}), 400
        
        # Verify unit exists and user has access
        org_filter = get_organization_filter(KitchenChoppingBoardChecklistUnit)
        unit = KitchenChoppingBoardChecklistUnit.query.filter(org_filter).filter_by(id=unit_id, is_active=True).first()
        if not unit:
            return jsonify({'success': False, 'error': 'Unit not found or unauthorized'}), 404
        
        # Generate PDF
        pdf_buffer = generate_kitchen_chopping_board_checklist_pdf(unit, year, month_num)
        
        # Generate filename
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']
        filename = f'KITCHEN_ChoppingBoard_Checklist_{month_names[month_num-1]}_{year}.pdf'
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500



# ============================================
# BAR OPENING CHECKLIST ROUTES
# ============================================

# ============================================
# CHOPPING BOARD CHECKLIST ROUTES
# ============================================

@checklist_bp.route('/bar/opening', methods=['GET'])
@login_required
@role_required(['Manager', 'Bartender'])
def bar_opening_checklist():
    """BAR Opening Checklist page - accessible to Manager and Bartender"""
    today = date.today()
    return render_template('checklist/bar_opening_checklist.html', today=today)


@checklist_bp.route('/bar/opening/units', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def manage_bar_opening_units():
    """API endpoint for managing opening checklist units - Manager only for create/update/delete"""
    if request.method == 'GET':
        try:
            org_filter = get_organization_filter(BarOpeningChecklistUnit)
            units = BarOpeningChecklistUnit.query.filter(org_filter).filter_by(
                is_active=True
            ).order_by(BarOpeningChecklistUnit.unit_name).all()
            return jsonify([{
                'id': unit.id,
                'unit_name': unit.unit_name,
                'description': unit.description
            } for unit in units])
        except Exception as e:
            current_app.logger.error(f"Error loading units: {str(e)}", exc_info=True)
            return jsonify([])
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'create':
                # Normalize role check - strip whitespace and handle None
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    current_app.logger.warning(f"Non-Manager user {current_user.id} (role: '{current_user.user_role}') attempted to create unit")
                    return jsonify({'success': False, 'error': 'Only Managers can create new units'}), 403
                
                unit_name = data.get('unit_name', '').strip() or 'BAR'
                description = data.get('description', '').strip()
                
                try:
                    org_filter = get_organization_filter(BarOpeningChecklistUnit)
                    existing_unit = BarOpeningChecklistUnit.query.filter(org_filter).filter_by(
                        unit_name=unit_name,
                        is_active=True
                    ).first()
                    
                    if existing_unit:
                        return jsonify({'success': False, 'error': f'Unit name "{unit_name}" already exists'}), 400
                    
                    # Ensure organisation is not None or empty string
                    organisation = (current_user.organisation or current_user.restaurant_bar_name or '').strip()
                    if not organisation:
                        return jsonify({'success': False, 'error': 'User organization is required to create units'}), 400
                    
                    unit = BarOpeningChecklistUnit(
                        unit_name=unit_name,
                        description=description,
                        organisation=organisation,
                        created_by=current_user.id,
                        is_active=True
                    )
                    db.session.add(unit)
                    db.session.commit()
                    
                    current_app.logger.info(f"Manager {current_user.id} created opening unit {unit.id} ({unit.unit_name})")
                    return jsonify({'success': True, 'unit': {
                        'id': unit.id,
                        'unit_name': unit.unit_name,
                        'description': unit.description
                    }})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error creating unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error creating unit: {str(e)}'}), 500
            
            elif action == 'update':
                # Normalize role check - strip whitespace and handle None
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can update units'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                
                try:
                    unit = BarOpeningChecklistUnit.query.get(data['id'])
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found'}), 404
                    
                    org_filter = get_organization_filter(BarOpeningChecklistUnit)
                    if not BarOpeningChecklistUnit.query.filter(org_filter).filter_by(id=unit.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    unit.unit_name = data.get('unit_name', unit.unit_name)
                    unit.description = data.get('description', unit.description)
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error updating unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error updating unit: {str(e)}'}), 500
            
            elif action == 'delete':
                # Normalize role check - strip whitespace and handle None
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can delete units'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                
                try:
                    unit = BarOpeningChecklistUnit.query.get(data['id'])
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found'}), 404
                    
                    org_filter = get_organization_filter(BarOpeningChecklistUnit)
                    if not BarOpeningChecklistUnit.query.filter(org_filter).filter_by(id=unit.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    # Soft delete - set is_active to False (historical records remain)
                    unit.is_active = False
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error deleting unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error deleting unit: {str(e)}'}), 500
            
            else:
                return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            current_app.logger.error(f"Error in manage_chopping_board_units: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500


@checklist_bp.route('/bar/opening/points', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def manage_bar_opening_points():
    """API endpoint for managing opening checklist points - Manager only for create/update/delete"""
    if request.method == 'GET':
        try:
            unit_id = request.args.get('unit_id', type=int)
            if not unit_id:
                return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
            
            org_filter = get_organization_filter(BarOpeningChecklistPoint)
            points = BarOpeningChecklistPoint.query.filter(org_filter).filter_by(
                unit_id=unit_id,
                is_active=True
            ).order_by(BarOpeningChecklistPoint.display_order).all()
            
            return jsonify([{
                'id': point.id,
                'unit_id': point.unit_id,
                'group_name': point.group_name,
                'point_text': point.point_text,
                'display_order': point.display_order
            } for point in points])
        except Exception as e:
            current_app.logger.error(f"Error loading checklist points: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'create':
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can create checklist points'}), 403
                
                unit_id = data.get('unit_id')
                group_name = data.get('group_name', '').strip() or 'Cleaning & Sanitisation'
                point_text = data.get('point_text', '').strip()
                display_order = data.get('display_order')
                
                if not unit_id:
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                if not point_text:
                    return jsonify({'success': False, 'error': 'Checklist point text is required'}), 400
                if display_order is None:
                    return jsonify({'success': False, 'error': 'Display order is required'}), 400
                
                try:
                    # Verify unit exists and user has access
                    org_filter = get_organization_filter(BarOpeningChecklistUnit)
                    unit = BarOpeningChecklistUnit.query.filter(org_filter).filter_by(id=unit_id, is_active=True).first()
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found or unauthorized'}), 404
                    
                    point = BarOpeningChecklistPoint(
                        unit_id=unit_id,
                        group_name=group_name,
                        point_text=point_text,
                        display_order=display_order,
                        organisation=current_user.organisation or current_user.restaurant_bar_name,
                        created_by=current_user.id,
                        is_active=True
                    )
                    db.session.add(point)
                    db.session.commit()
                    
                    return jsonify({'success': True, 'point': {
                        'id': point.id,
                        'unit_id': point.unit_id,
                        'group_name': point.group_name,
                        'point_text': point.point_text,
                        'display_order': point.display_order
                    }})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error creating checklist point: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error creating checklist point: {str(e)}'}), 500
            
            elif action == 'update':
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can update checklist points'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Point ID is required'}), 400
                
                try:
                    point = BarOpeningChecklistPoint.query.get(data['id'])
                    if not point:
                        return jsonify({'success': False, 'error': 'Checklist point not found'}), 404
                    
                    org_filter = get_organization_filter(BarOpeningChecklistPoint)
                    if not BarOpeningChecklistPoint.query.filter(org_filter).filter_by(id=point.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    if 'group_name' in data:
                        point.group_name = data['group_name']
                    if 'point_text' in data:
                        point.point_text = data['point_text']
                    if 'display_order' in data:
                        point.display_order = data['display_order']
                    
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error updating checklist point: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error updating checklist point: {str(e)}'}), 500
            
            elif action == 'delete':
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can delete checklist points'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Point ID is required'}), 400
                
                try:
                    point = BarOpeningChecklistPoint.query.get(data['id'])
                    if not point:
                        return jsonify({'success': False, 'error': 'Checklist point not found'}), 404
                    
                    org_filter = get_organization_filter(BarOpeningChecklistPoint)
                    if not BarOpeningChecklistPoint.query.filter(org_filter).filter_by(id=point.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    # Soft delete - set is_active to False
                    point.is_active = False
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error deleting checklist point: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error deleting checklist point: {str(e)}'}), 500
            
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500


@checklist_bp.route('/bar/opening/entries', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def bar_opening_checklist_entries():
    """API endpoint for opening checklist entries"""
    if request.method == 'GET':
        try:
            unit_id = request.args.get('unit_id', type=int)
            entry_date_str = request.args.get('entry_date')
            
            if not unit_id or not entry_date_str:
                return jsonify({'success': False, 'error': 'Unit ID and entry date are required'}), 400
            
            entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').date()
            
            # Get or create entry
            org_filter = get_organization_filter(BarOpeningChecklistEntry)
            entry = BarOpeningChecklistEntry.query.filter(org_filter).filter_by(
                unit_id=unit_id,
                entry_date=entry_date
            ).first()
            
            if not entry:
                # Create new entry
                entry = BarOpeningChecklistEntry(
                    unit_id=unit_id,
                    entry_date=entry_date,
                    organisation=current_user.organisation or current_user.restaurant_bar_name,
                    created_by=current_user.id
                )
                db.session.add(entry)
                db.session.commit()
            
            # Get all checklist points for this unit
            org_filter_points = get_organization_filter(BarOpeningChecklistPoint)
            points = BarOpeningChecklistPoint.query.filter(org_filter_points).filter_by(
                unit_id=unit_id,
                is_active=True
            ).order_by(BarOpeningChecklistPoint.display_order).all()
            
            # Get all items for this entry
            items = {item.checklist_point_id: {
                'id': item.id,
                'is_completed': item.is_completed,
                'staff_initials': item.staff_initials
            } for item in entry.items.all()}
            
            # Build response with points and their completion status
            points_data = []
            for point in points:
                item = items.get(point.id)
                points_data.append({
                    'point_id': point.id,
                    'group_name': point.group_name,
                    'point_text': point.point_text,
                    'display_order': point.display_order,
                    'item_id': item['id'] if item else None,
                    'is_completed': item['is_completed'] if item else False,
                    'staff_initials': item['staff_initials'] if item else None
                })
            
            return jsonify({
                'success': True,
                'entry_id': entry.id,
                'unit_id': entry.unit_id,
                'entry_date': entry.entry_date.isoformat(),
                'points': points_data
            })
        except Exception as e:
            current_app.logger.error(f"Error loading entry: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'update_item':
                # Staff can update items (mark as completed, add initials)
                entry_id = data.get('entry_id')
                checklist_point_id = data.get('checklist_point_id')
                is_completed = data.get('is_completed', False)
                staff_initials = data.get('staff_initials', '').strip()
                
                if not entry_id or not checklist_point_id:
                    return jsonify({'success': False, 'error': 'Entry ID and checklist point ID are required'}), 400
                
                try:
                    # Verify entry exists and user has access
                    org_filter = get_organization_filter(BarOpeningChecklistEntry)
                    entry = BarOpeningChecklistEntry.query.filter(org_filter).filter_by(id=entry_id).first()
                    if not entry:
                        return jsonify({'success': False, 'error': 'Entry not found or unauthorized'}), 404
                    
                    # Get or create item
                    item = BarOpeningChecklistItem.query.filter_by(
                        entry_id=entry_id,
                        checklist_point_id=checklist_point_id
                    ).first()
                    
                    if item:
                        # Update existing item
                        item.is_completed = is_completed
                        item.staff_initials = staff_initials if staff_initials else None
                    else:
                        # Create new item
                        item = BarOpeningChecklistItem(
                            entry_id=entry_id,
                            checklist_point_id=checklist_point_id,
                            is_completed=is_completed,
                            staff_initials=staff_initials if staff_initials else None,
                            organisation=current_user.organisation or current_user.restaurant_bar_name
                        )
                        db.session.add(item)
                    
                    db.session.commit()
                    
                    return jsonify({
                        'success': True,
                        'item': {
                            'id': item.id,
                            'is_completed': item.is_completed,
                            'staff_initials': item.staff_initials
                        }
                    })
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error updating item: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error updating item: {str(e)}'}), 500
            
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500


@checklist_bp.route('/bar/opening/pdf', methods=['POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def generate_bar_opening_checklist_pdf():
    """Generate monthly PDF for Opening Checklist - Available to Manager and Bartender"""
    try:
        from utils.pdf_generator import generate_bar_opening_checklist_pdf
        
        data = request.get_json()
        unit_id = data.get('unit_id')
        month = data.get('month')  # Format: 'YYYY-MM'
        year = data.get('year')
        
        if not unit_id:
            return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
        if not month and not year:
            return jsonify({'success': False, 'error': 'Month and year are required'}), 400
        
        # Parse month/year
        if month:
            year, month_num = map(int, month.split('-'))
        elif year:
            # If only year provided, use current month
            from datetime import date
            month_num = date.today().month
            year = int(year)
        else:
            return jsonify({'success': False, 'error': 'Month and year are required'}), 400
        
        # Verify unit exists and user has access
        org_filter = get_organization_filter(BarOpeningChecklistUnit)
        unit = BarOpeningChecklistUnit.query.filter(org_filter).filter_by(id=unit_id, is_active=True).first()
        if not unit:
            return jsonify({'success': False, 'error': 'Unit not found or unauthorized'}), 404
        
        # Generate PDF
        pdf_buffer = generate_bar_opening_checklist_pdf(unit, year, month_num)
        
        # Generate filename
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']
        filename = f'BAR_Opening_Checklist_{month_names[month_num-1]}_{year}.pdf'
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500





# ============================================
# BAR CLOSING CHECKLIST ROUTES
# ============================================

# ============================================
# CHOPPING BOARD CHECKLIST ROUTES
# ============================================

@checklist_bp.route('/bar/shift-closing', methods=['GET'])
@login_required
@role_required(['Manager', 'Bartender'])
def bar_shift_closing_checklist():
    """BAR Closing Checklist page - accessible to Manager and Bartender"""
    today = date.today()
    return render_template('checklist/bar_shift_closing_checklist.html', today=today)


@checklist_bp.route('/bar/shift-closing/units', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def manage_bar_shift_closing_units():
    """API endpoint for managing closing checklist units - Manager only for create/update/delete"""
    if request.method == 'GET':
        try:
            org_filter = get_organization_filter(BarShiftClosingChecklistUnit)
            units = BarShiftClosingChecklistUnit.query.filter(org_filter).filter_by(
                is_active=True
            ).order_by(BarShiftClosingChecklistUnit.unit_name).all()
            return jsonify([{
                'id': unit.id,
                'unit_name': unit.unit_name,
                'description': unit.description
            } for unit in units])
        except Exception as e:
            current_app.logger.error(f"Error loading units: {str(e)}", exc_info=True)
            return jsonify([])
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'create':
                # Normalize role check - strip whitespace and handle None
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    current_app.logger.warning(f"Non-Manager user {current_user.id} (role: '{current_user.user_role}') attempted to create unit")
                    return jsonify({'success': False, 'error': 'Only Managers can create new units'}), 403
                
                unit_name = data.get('unit_name', '').strip() or 'BAR'
                description = data.get('description', '').strip()
                
                try:
                    org_filter = get_organization_filter(BarShiftClosingChecklistUnit)
                    existing_unit = BarShiftClosingChecklistUnit.query.filter(org_filter).filter_by(
                        unit_name=unit_name,
                        is_active=True
                    ).first()
                    
                    if existing_unit:
                        return jsonify({'success': False, 'error': f'Unit name "{unit_name}" already exists'}), 400
                    
                    # Ensure organisation is not None or empty string
                    organisation = (current_user.organisation or current_user.restaurant_bar_name or '').strip()
                    if not organisation:
                        return jsonify({'success': False, 'error': 'User organization is required to create units'}), 400
                    
                    unit = BarShiftClosingChecklistUnit(
                        unit_name=unit_name,
                        description=description,
                        organisation=organisation,
                        created_by=current_user.id,
                        is_active=True
                    )
                    db.session.add(unit)
                    db.session.commit()
                    
                    current_app.logger.info(f"Manager {current_user.id} created closing unit {unit.id} ({unit.unit_name})")
                    return jsonify({'success': True, 'unit': {
                        'id': unit.id,
                        'unit_name': unit.unit_name,
                        'description': unit.description
                    }})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error creating unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error creating unit: {str(e)}'}), 500
            
            elif action == 'update':
                # Normalize role check - strip whitespace and handle None
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can update units'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                
                try:
                    unit = BarShiftClosingChecklistUnit.query.get(data['id'])
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found'}), 404
                    
                    org_filter = get_organization_filter(BarShiftClosingChecklistUnit)
                    if not BarShiftClosingChecklistUnit.query.filter(org_filter).filter_by(id=unit.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    unit.unit_name = data.get('unit_name', unit.unit_name)
                    unit.description = data.get('description', unit.description)
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error updating unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error updating unit: {str(e)}'}), 500
            
            elif action == 'delete':
                # Normalize role check - strip whitespace and handle None
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can delete units'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                
                try:
                    unit = BarShiftClosingChecklistUnit.query.get(data['id'])
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found'}), 404
                    
                    org_filter = get_organization_filter(BarShiftClosingChecklistUnit)
                    if not BarShiftClosingChecklistUnit.query.filter(org_filter).filter_by(id=unit.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    # Soft delete - set is_active to False (historical records remain)
                    unit.is_active = False
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error deleting unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error deleting unit: {str(e)}'}), 500
            
            else:
                return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            current_app.logger.error(f"Error in manage_chopping_board_units: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500


@checklist_bp.route('/bar/shift-closing/points', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def manage_bar_shift_closing_points():
    """API endpoint for managing closing checklist points - Manager only for create/update/delete"""
    if request.method == 'GET':
        try:
            unit_id = request.args.get('unit_id', type=int)
            if not unit_id:
                return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
            
            org_filter = get_organization_filter(BarShiftClosingChecklistPoint)
            points = BarShiftClosingChecklistPoint.query.filter(org_filter).filter_by(
                unit_id=unit_id,
                is_active=True
            ).order_by(BarShiftClosingChecklistPoint.display_order).all()
            
            return jsonify([{
                'id': point.id,
                'unit_id': point.unit_id,
                'group_name': point.group_name,
                'point_text': point.point_text,
                'display_order': point.display_order
            } for point in points])
        except Exception as e:
            current_app.logger.error(f"Error loading checklist points: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'create':
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can create checklist points'}), 403
                
                unit_id = data.get('unit_id')
                group_name = data.get('group_name', '').strip() or 'Cleaning & Sanitisation'
                point_text = data.get('point_text', '').strip()
                display_order = data.get('display_order')
                
                if not unit_id:
                    return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
                if not point_text:
                    return jsonify({'success': False, 'error': 'Checklist point text is required'}), 400
                if display_order is None:
                    return jsonify({'success': False, 'error': 'Display order is required'}), 400
                
                try:
                    # Verify unit exists and user has access
                    org_filter = get_organization_filter(BarShiftClosingChecklistUnit)
                    unit = BarShiftClosingChecklistUnit.query.filter(org_filter).filter_by(id=unit_id, is_active=True).first()
                    if not unit:
                        return jsonify({'success': False, 'error': 'Unit not found or unauthorized'}), 404
                    
                    point = BarShiftClosingChecklistPoint(
                        unit_id=unit_id,
                        group_name=group_name,
                        point_text=point_text,
                        display_order=display_order,
                        organisation=current_user.organisation or current_user.restaurant_bar_name,
                        created_by=current_user.id,
                        is_active=True
                    )
                    db.session.add(point)
                    db.session.commit()
                    
                    return jsonify({'success': True, 'point': {
                        'id': point.id,
                        'unit_id': point.unit_id,
                        'group_name': point.group_name,
                        'point_text': point.point_text,
                        'display_order': point.display_order
                    }})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error creating checklist point: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error creating checklist point: {str(e)}'}), 500
            
            elif action == 'update':
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can update checklist points'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Point ID is required'}), 400
                
                try:
                    point = BarShiftClosingChecklistPoint.query.get(data['id'])
                    if not point:
                        return jsonify({'success': False, 'error': 'Checklist point not found'}), 404
                    
                    org_filter = get_organization_filter(BarShiftClosingChecklistPoint)
                    if not BarShiftClosingChecklistPoint.query.filter(org_filter).filter_by(id=point.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    if 'group_name' in data:
                        point.group_name = data['group_name']
                    if 'point_text' in data:
                        point.point_text = data['point_text']
                    if 'display_order' in data:
                        point.display_order = data['display_order']
                    
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error updating checklist point: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error updating checklist point: {str(e)}'}), 500
            
            elif action == 'delete':
                user_role = (current_user.user_role or '').strip()
                if user_role != 'Manager':
                    return jsonify({'success': False, 'error': 'Only Managers can delete checklist points'}), 403
                
                if not data.get('id'):
                    return jsonify({'success': False, 'error': 'Point ID is required'}), 400
                
                try:
                    point = BarShiftClosingChecklistPoint.query.get(data['id'])
                    if not point:
                        return jsonify({'success': False, 'error': 'Checklist point not found'}), 404
                    
                    org_filter = get_organization_filter(BarShiftClosingChecklistPoint)
                    if not BarShiftClosingChecklistPoint.query.filter(org_filter).filter_by(id=point.id).first():
                        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
                    
                    # Soft delete - set is_active to False
                    point.is_active = False
                    db.session.commit()
                    return jsonify({'success': True})
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error deleting checklist point: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error deleting checklist point: {str(e)}'}), 500
            
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500


@checklist_bp.route('/bar/shift-closing/entries', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def bar_shift_closing_checklist_entries():
    """API endpoint for closing checklist entries"""
    if request.method == 'GET':
        try:
            unit_id = request.args.get('unit_id', type=int)
            entry_date_str = request.args.get('entry_date')
            
            if not unit_id or not entry_date_str:
                return jsonify({'success': False, 'error': 'Unit ID and entry date are required'}), 400
            
            entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').date()
            
            # Get or create entry
            org_filter = get_organization_filter(BarShiftClosingChecklistEntry)
            entry = BarShiftClosingChecklistEntry.query.filter(org_filter).filter_by(
                unit_id=unit_id,
                entry_date=entry_date
            ).first()
            
            if not entry:
                # Create new entry
                entry = BarShiftClosingChecklistEntry(
                    unit_id=unit_id,
                    entry_date=entry_date,
                    organisation=current_user.organisation or current_user.restaurant_bar_name,
                    created_by=current_user.id
                )
                db.session.add(entry)
                db.session.commit()
            
            # Get all checklist points for this unit
            org_filter_points = get_organization_filter(BarShiftClosingChecklistPoint)
            points = BarShiftClosingChecklistPoint.query.filter(org_filter_points).filter_by(
                unit_id=unit_id,
                is_active=True
            ).order_by(BarShiftClosingChecklistPoint.display_order).all()
            
            # Get all items for this entry
            items = {item.checklist_point_id: {
                'id': item.id,
                'is_completed': item.is_completed,
                'staff_initials': item.staff_initials
            } for item in entry.items.all()}
            
            # Build response with points and their completion status
            points_data = []
            for point in points:
                item = items.get(point.id)
                points_data.append({
                    'point_id': point.id,
                    'group_name': point.group_name,
                    'point_text': point.point_text,
                    'display_order': point.display_order,
                    'item_id': item['id'] if item else None,
                    'is_completed': item['is_completed'] if item else False,
                    'staff_initials': item['staff_initials'] if item else None
                })
            
            return jsonify({
                'success': True,
                'entry_id': entry.id,
                'unit_id': entry.unit_id,
                'entry_date': entry.entry_date.isoformat(),
                'points': points_data
            })
        except Exception as e:
            current_app.logger.error(f"Error loading entry: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'update_item':
                # Staff can update items (mark as completed, add initials)
                entry_id = data.get('entry_id')
                checklist_point_id = data.get('checklist_point_id')
                is_completed = data.get('is_completed', False)
                staff_initials = data.get('staff_initials', '').strip()
                
                if not entry_id or not checklist_point_id:
                    return jsonify({'success': False, 'error': 'Entry ID and checklist point ID are required'}), 400
                
                try:
                    # Verify entry exists and user has access
                    org_filter = get_organization_filter(BarShiftClosingChecklistEntry)
                    entry = BarShiftClosingChecklistEntry.query.filter(org_filter).filter_by(id=entry_id).first()
                    if not entry:
                        return jsonify({'success': False, 'error': 'Entry not found or unauthorized'}), 404
                    
                    # Get or create item
                    item = BarShiftClosingChecklistItem.query.filter_by(
                        entry_id=entry_id,
                        checklist_point_id=checklist_point_id
                    ).first()
                    
                    if item:
                        # Update existing item
                        item.is_completed = is_completed
                        item.staff_initials = staff_initials if staff_initials else None
                    else:
                        # Create new item
                        item = BarShiftClosingChecklistItem(
                            entry_id=entry_id,
                            checklist_point_id=checklist_point_id,
                            is_completed=is_completed,
                            staff_initials=staff_initials if staff_initials else None,
                            organisation=current_user.organisation or current_user.restaurant_bar_name
                        )
                        db.session.add(item)
                    
                    db.session.commit()
                    
                    return jsonify({
                        'success': True,
                        'item': {
                            'id': item.id,
                            'is_completed': item.is_completed,
                            'staff_initials': item.staff_initials
                        }
                    })
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error updating item: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error updating item: {str(e)}'}), 500
            
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500


@checklist_bp.route('/bar/shift-closing/pdf', methods=['POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def generate_bar_shift_closing_checklist_pdf():
    """Generate monthly PDF for Closing Checklist - Available to Manager and Bartender"""
    try:
        from utils.pdf_generator import generate_bar_shift_closing_checklist_pdf
        
        data = request.get_json()
        unit_id = data.get('unit_id')
        month = data.get('month')  # Format: 'YYYY-MM'
        year = data.get('year')
        
        if not unit_id:
            return jsonify({'success': False, 'error': 'Unit ID is required'}), 400
        if not month and not year:
            return jsonify({'success': False, 'error': 'Month and year are required'}), 400
        
        # Parse month/year
        if month:
            year, month_num = map(int, month.split('-'))
        elif year:
            # If only year provided, use current month
            from datetime import date
            month_num = date.today().month
            year = int(year)
        else:
            return jsonify({'success': False, 'error': 'Month and year are required'}), 400
        
        # Verify unit exists and user has access
        org_filter = get_organization_filter(BarShiftClosingChecklistUnit)
        unit = BarShiftClosingChecklistUnit.query.filter(org_filter).filter_by(id=unit_id, is_active=True).first()
        if not unit:
            return jsonify({'success': False, 'error': 'Unit not found or unauthorized'}), 404
        
        # Generate PDF
        pdf_buffer = generate_bar_shift_closing_checklist_pdf(unit, year, month_num)
        
        # Generate filename
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']
        filename = f'BAR_Closing_Checklist_{month_names[month_num-1]}_{year}.pdf'
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500



