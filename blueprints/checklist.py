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

from models import ColdStorageUnit, TemperatureLog, TemperatureEntry
from extensions import db
from utils.helpers import get_organization_filter

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
                
                # Validate unit type
                valid_types = ['Refrigerator', 'Freezer', 'Wine Chiller']
                if unit_type not in valid_types:
                    return jsonify({'success': False, 'error': f'Invalid unit type. Must be one of: {", ".join(valid_types)}'}), 400
                
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
                    
                    # Validate temperature range for Wine Chiller
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
                    
                    unit.unit_number = data['unit_number']
                    unit.location = data['location']
                    unit.unit_type = data['unit_type']
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
                
                # Validate unit type
                valid_types = ['Refrigerator', 'Freezer', 'Wine Chiller']
                if unit_type not in valid_types:
                    return jsonify({'success': False, 'error': f'Invalid unit type. Must be one of: {", ".join(valid_types)}'}), 400
                
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
                    
                    # Validate temperature range for Wine Chiller
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
                    
                    unit.unit_number = data['unit_number']
                    unit.location = data['location']
                    unit.unit_type = data['unit_type']
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



