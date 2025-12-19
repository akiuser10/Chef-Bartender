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

@checklist_bp.route('/bar/cold-storage')
@login_required
@role_required(['Manager', 'Bartender'])
def cold_storage_temperature_log():
    """Main page for Cold Storage Temperature Log"""
    try:
        org_filter = get_organization_filter(ColdStorageUnit)
        units = ColdStorageUnit.query.filter(org_filter).filter_by(is_active=True).order_by(ColdStorageUnit.unit_number).all()
    except Exception as e:
        current_app.logger.error(f"Error loading cold storage units: {str(e)}", exc_info=True)
        # If table doesn't exist yet, return empty list
        units = []
    
    # Get today's date
    today = date.today()
    
    return render_template('checklist/cold_storage_temperature_log.html', units=units, today=today)


@checklist_bp.route('/bar/cold-storage/units', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def manage_cold_storage_units():
    """API endpoint for managing cold storage units"""
    if request.method == 'GET':
        try:
            org_filter = get_organization_filter(ColdStorageUnit)
            units = ColdStorageUnit.query.filter(org_filter).filter_by(is_active=True).order_by(ColdStorageUnit.unit_number).all()
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
                # Validate required fields
                if not data.get('unit_number') or not data.get('location') or not data.get('unit_type'):
                    return jsonify({'success': False, 'error': 'Unit number, location, and unit type are required'}), 400
                
                try:
                    # Handle temperature values - convert to float if provided, otherwise None
                    min_temp = None
                    max_temp = None
                    if data.get('min_temp') and str(data.get('min_temp')).strip():
                        min_temp = float(data['min_temp'])
                    if data.get('max_temp') and str(data.get('max_temp')).strip():
                        max_temp = float(data['max_temp'])
                    
                    unit = ColdStorageUnit(
                        unit_number=data['unit_number'],
                        location=data['location'],
                        unit_type=data['unit_type'],
                        min_temp=min_temp,
                        max_temp=max_temp,
                        organisation=current_user.organisation or current_user.restaurant_bar_name,
                        created_by=current_user.id
                    )
                    db.session.add(unit)
                    db.session.commit()
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
                    return jsonify({'success': False, 'error': f'Invalid temperature value: {str(e)}'}), 400
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error creating unit: {str(e)}", exc_info=True)
                    return jsonify({'success': False, 'error': f'Error creating unit: {str(e)}'}), 500
            
            elif action == 'update':
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


@checklist_bp.route('/bar/cold-storage/log/<int:unit_id>/<date_str>', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def temperature_log_entry(unit_id, date_str):
    """API endpoint for getting/creating temperature log entries"""
    try:
        log_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid date format'}), 400
    
    unit = ColdStorageUnit.query.get_or_404(unit_id)
    org_filter = get_organization_filter(ColdStorageUnit)
    if not ColdStorageUnit.query.filter(org_filter).filter_by(id=unit.id).first():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    if request.method == 'GET':
        # Get or create log for this unit and date
        log = TemperatureLog.query.filter_by(unit_id=unit_id, log_date=log_date).first()
        
        if not log:
            # Create new log
            log = TemperatureLog(
                unit_id=unit_id,
                log_date=log_date,
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
        
        return jsonify({
            'success': True,
            'log': {
                'id': log.id,
                'unit_id': log.unit_id,
                'log_date': log.log_date.isoformat(),
                'supervisor_verified': log.supervisor_verified,
                'supervisor_name': log.supervisor_name,
                'entries': entry_dict
            },
            'unit': {
                'id': unit.id,
                'unit_number': unit.unit_number,
                'location': unit.location,
                'unit_type': unit.unit_type,
                'min_temp': unit.min_temp,
                'max_temp': unit.max_temp
            }
        })
    
    elif request.method == 'POST':
        data = request.get_json()
        action = data.get('action')
        
        if action == 'save_entry':
            # Get or create log
            log = TemperatureLog.query.filter_by(unit_id=unit_id, log_date=log_date).first()
            if not log:
                log = TemperatureLog(
                    unit_id=unit_id,
                    log_date=log_date,
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
        
        elif action == 'verify':
            log = TemperatureLog.query.filter_by(unit_id=unit_id, log_date=log_date).first()
            if not log:
                return jsonify({'success': False, 'error': 'Log not found'}), 404
            
            log.supervisor_verified = True
            log.supervisor_name = data.get('supervisor_name', current_user.first_name or current_user.username)
            log.supervisor_verified_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({'success': True})
        
        return jsonify({'success': False, 'error': 'Invalid action'}), 400


@checklist_bp.route('/bar/cold-storage/pdf', methods=['POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def generate_temperature_log_pdf():
    """Generate PDF for temperature logs"""
    try:
        from utils.pdf_generator import generate_temperature_log_pdf
        
        data = request.get_json()
        unit_ids = data.get('unit_ids', [])
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        
        org_filter = get_organization_filter(ColdStorageUnit)
        units = ColdStorageUnit.query.filter(org_filter).filter(
            ColdStorageUnit.id.in_(unit_ids),
            ColdStorageUnit.is_active == True
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



