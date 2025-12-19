"""
Checklist Blueprint
Handles Bar Checklist and Kitchen Checklist pages
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta, date
from sqlalchemy import and_, or_
from extensions import db
from models import ColdStorageUnit, TemperatureLog, WeeklyTemperatureLog
from flask import make_response
from io import BytesIO
from werkzeug.utils import secure_filename

# HACCP Predefined Corrective Actions
CORRECTIVE_ACTIONS = [
    'Adjusted thermostat settings',
    'Repaired/replaced equipment',
    'Moved items to alternative storage',
    'Discarded compromised items',
    'Contacted maintenance',
    'Other (specify in notes)'
]
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


# =====================
# TEMPERATURE LOG ROUTES
# =====================

# HACCP Predefined Corrective Actions
CORRECTIVE_ACTIONS = [
    'Adjusted thermostat settings',
    'Repaired/replaced equipment',
    'Moved items to alternative storage',
    'Discarded compromised items',
    'Contacted maintenance',
    'Other (specify in notes)'
]

@checklist_bp.route('/temperature-log')
@login_required
@role_required(['Manager', 'Bartender'])
def temperature_log_index():
    """Temperature log main page - HACCP Compliant"""
    # Get all active units for the organization
    org_filter = get_organization_filter(ColdStorageUnit)
    units = ColdStorageUnit.query.filter(org_filter).filter_by(is_active=True).order_by(ColdStorageUnit.unit_type, ColdStorageUnit.unit_number).all()
    
    # Get recent weekly logs
    log_org_filter = get_organization_filter(TemperatureLog)
    recent_logs = TemperatureLog.query.filter(log_org_filter).order_by(TemperatureLog.week_start_date.desc()).limit(10).all()
    
    # Get unique week start dates
    week_dates = db.session.query(TemperatureLog.week_start_date).filter(log_org_filter).distinct().order_by(TemperatureLog.week_start_date.desc()).all()
    week_dates = [w[0] for w in week_dates]
    
    return render_template('checklist/temperature_log_index.html', units=units, recent_logs=recent_logs, week_dates=week_dates, corrective_actions=CORRECTIVE_ACTIONS)


@checklist_bp.route('/temperature-log/units')
@login_required
@role_required(['Manager', 'Bartender'])
def manage_units():
    """Manage cold storage units"""
    org_filter = get_organization_filter(ColdStorageUnit)
    units = ColdStorageUnit.query.filter(org_filter).order_by(ColdStorageUnit.unit_type, ColdStorageUnit.unit_number).all()
    
    return render_template('checklist/manage_units.html', units=units)


@checklist_bp.route('/temperature-log/units/add', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def add_unit():
    """Add a new cold storage unit"""
    if request.method == 'POST':
        unit_number = request.form.get('unit_number', '').strip()
        unit_name = request.form.get('unit_name', '').strip()
        unit_type = request.form.get('unit_type', '').strip()
        min_temp = request.form.get('min_temp', '').strip()
        max_temp = request.form.get('max_temp', '').strip()
        
        if not unit_number or not unit_type:
            flash('Unit number and type are required.', 'error')
            return redirect(url_for('checklist.add_unit'))
        
        # Check if unit number already exists for this organization
        org_filter = get_organization_filter(ColdStorageUnit)
        existing = ColdStorageUnit.query.filter(org_filter).filter_by(unit_number=unit_number, is_active=True).first()
        if existing:
            flash(f'Unit number "{unit_number}" already exists.', 'error')
            return redirect(url_for('checklist.add_unit'))
        
        # Parse temperatures
        min_temp_val = float(min_temp) if min_temp else None
        max_temp_val = float(max_temp) if max_temp else None
        
        # Set default ranges based on unit type
        if unit_type == 'Freezer':
            min_temp_val = -22.0
            max_temp_val = -12.0
        elif unit_type == 'Refrigerator':
            min_temp_val = 0.0
            max_temp_val = 4.0
        # Wine Chiller uses user-defined values
        
        unit = ColdStorageUnit(
            unit_number=unit_number,
            unit_name=unit_name or None,
            unit_type=unit_type,
            min_temp=min_temp_val,
            max_temp=max_temp_val,
            organisation=current_user.organisation or current_user.restaurant_bar_name,
            created_by=current_user.id
        )
        
        db.session.add(unit)
        db.session.commit()
        
        flash(f'Unit "{unit_number}" added successfully.', 'success')
        return redirect(url_for('checklist.manage_units'))
    
    return render_template('checklist/add_unit.html')


@checklist_bp.route('/temperature-log/units/<int:unit_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def edit_unit(unit_id):
    """Edit a cold storage unit"""
    org_filter = get_organization_filter(ColdStorageUnit)
    unit = ColdStorageUnit.query.filter(org_filter).filter_by(id=unit_id).first_or_404()
    
    if request.method == 'POST':
        unit_number = request.form.get('unit_number', '').strip()
        unit_name = request.form.get('unit_name', '').strip()
        unit_type = request.form.get('unit_type', '').strip()
        min_temp = request.form.get('min_temp', '').strip()
        max_temp = request.form.get('max_temp', '').strip()
        
        if not unit_number or not unit_type:
            flash('Unit number and type are required.', 'error')
            return redirect(url_for('checklist.edit_unit', unit_id=unit_id))
        
        # Check if unit number already exists (excluding current unit)
        existing = ColdStorageUnit.query.filter(org_filter).filter(
            ColdStorageUnit.unit_number == unit_number,
            ColdStorageUnit.id != unit_id,
            ColdStorageUnit.is_active == True
        ).first()
        if existing:
            flash(f'Unit number "{unit_number}" already exists.', 'error')
            return redirect(url_for('checklist.edit_unit', unit_id=unit_id))
        
        # Parse temperatures
        min_temp_val = float(min_temp) if min_temp else None
        max_temp_val = float(max_temp) if max_temp else None
        
        # Set default ranges based on unit type
        if unit_type == 'Freezer':
            min_temp_val = -22.0
            max_temp_val = -12.0
        elif unit_type == 'Refrigerator':
            min_temp_val = 0.0
            max_temp_val = 4.0
        # Wine Chiller uses user-defined values
        
        unit.unit_number = unit_number
        unit.unit_name = unit_name or None
        unit.unit_type = unit_type
        unit.min_temp = min_temp_val
        unit.max_temp = max_temp_val
        unit.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash(f'Unit "{unit_number}" updated successfully.', 'success')
        return redirect(url_for('checklist.manage_units'))
    
    return render_template('checklist/edit_unit.html', unit=unit)


@checklist_bp.route('/temperature-log/units/<int:unit_id>/delete', methods=['POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def delete_unit(unit_id):
    """Delete (soft delete) a cold storage unit"""
    from utils.helpers import get_organization_filter
    
    org_filter = get_organization_filter(ColdStorageUnit)
    unit = ColdStorageUnit.query.filter(org_filter).filter_by(id=unit_id).first_or_404()
    
    # Soft delete
    unit.is_active = False
    unit.updated_at = datetime.utcnow()
    db.session.commit()
    
    flash(f'Unit "{unit.unit_number}" deleted successfully.', 'success')
    return redirect(url_for('checklist.manage_units'))


@checklist_bp.route('/temperature-log/weekly', methods=['GET', 'POST'])
@login_required
@role_required(['Manager', 'Bartender'])
def weekly_log():
    """Create or edit weekly temperature log - HACCP Compliant"""
    # Get week start date (default to current week's Monday)
    week_start_str = request.args.get('week_start', '')
    if week_start_str:
        try:
            week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
        except:
            week_start = None
    else:
        # Get Monday of current week
        today = date.today()
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday)
    
    if not week_start:
        week_start = date.today()
        days_since_monday = week_start.weekday()
        week_start = week_start - timedelta(days=days_since_monday)
    
    # Check if log is locked
    weekly_meta = WeeklyTemperatureLog.query.filter_by(week_start_date=week_start).first()
    is_locked = weekly_meta and weekly_meta.is_locked
    
    # Get all active units
    org_filter = get_organization_filter(ColdStorageUnit)
    units = ColdStorageUnit.query.filter(org_filter).filter_by(is_active=True).order_by(ColdStorageUnit.unit_type, ColdStorageUnit.unit_number).all()
    
    if not units:
        flash('Please add at least one cold storage unit before creating a log.', 'error')
        return redirect(url_for('checklist.manage_units'))
    
    # Time slots
    time_slots = ['10:00 AM', '02:00 PM', '06:00 PM', '10:00 PM']
    
    # Days of the week
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    week_dates = [week_start + timedelta(days=i) for i in range(7)]
    
    # Get existing logs for this week
    log_org_filter = get_organization_filter(TemperatureLog)
    existing_logs = TemperatureLog.query.filter(
        log_org_filter,
        TemperatureLog.week_start_date == week_start
    ).all()
    
    # Organize existing logs by date, time, and unit
    log_dict = {}
    for log in existing_logs:
        key = (log.log_date, log.time_slot, log.unit_id)
        log_dict[key] = log
    
    # Get metadata
    if weekly_meta:
        metadata = {
            'bar_name': weekly_meta.bar_name or '',
            'location': weekly_meta.location or '',
            'checked_by': weekly_meta.checked_by or '',
            'supervisor_name': weekly_meta.supervisor_name or '',
            'supervisor_signature': weekly_meta.supervisor_signature or '',
            'supervisor_date': weekly_meta.supervisor_date.strftime('%Y-%m-%d') if weekly_meta.supervisor_date else '',
            'is_locked': weekly_meta.is_locked
        }
    elif existing_logs:
        first_log = existing_logs[0]
        metadata = {
            'bar_name': first_log.bar_name or '',
            'location': first_log.location or '',
            'checked_by': first_log.checked_by or '',
            'supervisor_name': first_log.supervisor_name or '',
            'supervisor_signature': first_log.supervisor_signature or '',
            'supervisor_date': first_log.supervisor_date.strftime('%Y-%m-%d') if first_log.supervisor_date else '',
            'is_locked': False
        }
    else:
        # Default metadata from user
        metadata = {
            'bar_name': current_user.restaurant_bar_name or '',
            'location': current_user.company_address or '',
            'checked_by': f'{current_user.first_name or ""} {current_user.last_name or ""}'.strip() or current_user.username,
            'supervisor_name': '',
            'supervisor_signature': '',
            'supervisor_date': '',
            'is_locked': False
        }
    
    if request.method == 'POST':
        if is_locked:
            flash('This log is locked and cannot be edited.', 'error')
            return redirect(url_for('checklist.view_weekly_log', week_start=week_start.strftime('%Y-%m-%d')))
        
        # Get metadata
        bar_name = request.form.get('bar_name', '').strip()
        location = request.form.get('location', '').strip()
        checked_by = request.form.get('checked_by', '').strip()
        supervisor_name = request.form.get('supervisor_name', '').strip()
        supervisor_signature = request.form.get('supervisor_signature', '').strip()
        supervisor_date_str = request.form.get('supervisor_date', '').strip()
        lock_record = request.form.get('lock_record', '') == 'on'
        
        supervisor_date = None
        if supervisor_date_str:
            try:
                supervisor_date = datetime.strptime(supervisor_date_str, '%Y-%m-%d').date()
            except:
                pass
        
        # Validate required fields
        if not bar_name or not location or not checked_by:
            flash('Bar name, location, and checked by are required.', 'error')
            return redirect(url_for('checklist.weekly_log', week_start=week_start.strftime('%Y-%m-%d')))
        
        # Get or create weekly metadata
        if not weekly_meta:
            weekly_meta = WeeklyTemperatureLog(
                week_start_date=week_start,
                bar_name=bar_name,
                location=location,
                checked_by=checked_by,
                organisation=current_user.organisation or current_user.restaurant_bar_name,
                created_by=current_user.id
            )
            db.session.add(weekly_meta)
        else:
            weekly_meta.bar_name = bar_name
            weekly_meta.location = location
            weekly_meta.checked_by = checked_by
        
        # Delete existing logs for this week
        TemperatureLog.query.filter(
            log_org_filter,
            TemperatureLog.week_start_date == week_start
        ).delete()
        
        # Track validation errors
        validation_errors = []
        out_of_range_count = 0
        
        # Create new logs
        for day_idx, day_date in enumerate(week_dates):
            for time_slot in time_slots:
                for unit in units:
                    temp_key = f'temp_{day_idx}_{time_slot}_{unit.id}'
                    action_type_key = f'action_type_{day_idx}_{time_slot}_{unit.id}'
                    action_key = f'action_{day_idx}_{time_slot}_{unit.id}'
                    recheck_key = f'recheck_{day_idx}_{time_slot}_{unit.id}'
                    action_time_key = f'action_time_{day_idx}_{time_slot}_{unit.id}'
                    daily_verified_key = f'daily_verified_{day_idx}'
                    
                    temp_str = request.form.get(temp_key, '').strip()
                    action_type = request.form.get(action_type_key, '').strip()
                    action = request.form.get(action_key, '').strip()
                    recheck_str = request.form.get(recheck_key, '').strip()
                    action_time = request.form.get(action_time_key, '').strip()
                    daily_verified = request.form.get(daily_verified_key, '') == 'on'
                    
                    if temp_str:
                        try:
                            temperature = float(temp_str)
                            
                            # Check if temperature is valid
                            is_valid = unit.is_temp_valid(temperature)
                            status = 'OK' if is_valid else 'OUT OF RANGE'
                            
                            if not is_valid:
                                out_of_range_count += 1
                                # Validate corrective action is provided
                                if not action_type or not action:
                                    validation_errors.append(f'{day_date.strftime("%A")} {time_slot} - {unit.unit_number}: Corrective action required for out-of-range temperature')
                            
                            recheck_temp = None
                            if recheck_str:
                                try:
                                    recheck_temp = float(recheck_str)
                                except:
                                    pass
                            
                            log = TemperatureLog(
                                week_start_date=week_start,
                                log_date=day_date,
                                time_slot=time_slot,
                                unit_id=unit.id,
                                temperature=temperature,
                                status=status,
                                corrective_action_type=action_type or None,
                                corrective_action=action or None,
                                recheck_temperature=recheck_temp,
                                corrective_action_time=action_time or None,
                                checked_by=checked_by,
                                bar_name=bar_name,
                                location=location,
                                daily_verified=daily_verified,
                                daily_verified_by=checked_by if daily_verified else None,
                                daily_verified_date=day_date if daily_verified else None,
                                supervisor_name=supervisor_name or None,
                                supervisor_signature=supervisor_signature or None,
                                supervisor_date=supervisor_date,
                                organisation=current_user.organisation or current_user.restaurant_bar_name,
                                created_by=current_user.id
                            )
                            
                            log.update_status()  # Ensure status is correct
                            db.session.add(log)
                        except ValueError:
                            pass  # Invalid temperature, skip
        
        # Check validation errors
        if validation_errors:
            db.session.rollback()
            error_msg = 'Cannot save: Corrective actions required for out-of-range temperatures:\n' + '\n'.join(validation_errors[:5])
            if len(validation_errors) > 5:
                error_msg += f'\n... and {len(validation_errors) - 5} more'
            flash(error_msg, 'error')
            return redirect(url_for('checklist.weekly_log', week_start=week_start.strftime('%Y-%m-%d')))
        
        # Update supervisor info
        weekly_meta.supervisor_name = supervisor_name or None
        weekly_meta.supervisor_signature = supervisor_signature or None
        weekly_meta.supervisor_date = supervisor_date
        
        # Lock if requested
        if lock_record and supervisor_name and supervisor_signature:
            weekly_meta.is_locked = True
            weekly_meta.locked_at = datetime.utcnow()
            weekly_meta.locked_by = current_user.id
        
        db.session.commit()
        
        if out_of_range_count > 0:
            flash(f'Weekly temperature log saved successfully. {out_of_range_count} out-of-range temperature(s) detected and corrective actions recorded.', 'warning')
        else:
            flash('Weekly temperature log saved successfully.', 'success')
        
        return redirect(url_for('checklist.view_weekly_log', week_start=week_start.strftime('%Y-%m-%d')))
    
    return render_template('checklist/weekly_log_haccp.html', 
                         units=units, 
                         time_slots=time_slots, 
                         days=days, 
                         week_dates=week_dates,
                         week_start=week_start,
                         log_dict=log_dict,
                         metadata=metadata,
                         corrective_actions=CORRECTIVE_ACTIONS,
                         is_locked=is_locked)


@checklist_bp.route('/temperature-log/weekly/<week_start>')
@login_required
@role_required(['Manager', 'Bartender'])
def view_weekly_log(week_start):
    """View/print weekly temperature log - HACCP Compliant"""
    try:
        week_start_date = datetime.strptime(week_start, '%Y-%m-%d').date()
    except:
        flash('Invalid week start date.', 'error')
        return redirect(url_for('checklist.temperature_log_index'))
    
    # Get weekly metadata
    weekly_meta = WeeklyTemperatureLog.query.filter_by(week_start_date=week_start_date).first()
    
    # Get all active units
    org_filter = get_organization_filter(ColdStorageUnit)
    units = ColdStorageUnit.query.filter(org_filter).filter_by(is_active=True).order_by(ColdStorageUnit.unit_type, ColdStorageUnit.unit_number).all()
    
    # Get logs for this week
    log_org_filter = get_organization_filter(TemperatureLog)
    logs = TemperatureLog.query.filter(
        log_org_filter,
        TemperatureLog.week_start_date == week_start_date
    ).all()
    
    # Organize logs
    log_dict = {}
    out_of_range_count = 0
    for log in logs:
        key = (log.log_date, log.time_slot, log.unit_id)
        log_dict[key] = log
        if log.status == 'OUT OF RANGE':
            out_of_range_count += 1
    
    # Get metadata
    if weekly_meta:
        metadata = {
            'bar_name': weekly_meta.bar_name or '',
            'location': weekly_meta.location or '',
            'checked_by': weekly_meta.checked_by or '',
            'supervisor_name': weekly_meta.supervisor_name or '',
            'supervisor_signature': weekly_meta.supervisor_signature or '',
            'supervisor_date': weekly_meta.supervisor_date,
            'is_locked': weekly_meta.is_locked
        }
    elif logs:
        first_log = logs[0]
        metadata = {
            'bar_name': first_log.bar_name or '',
            'location': first_log.location or '',
            'checked_by': first_log.checked_by or '',
            'supervisor_name': first_log.supervisor_name or '',
            'supervisor_signature': first_log.supervisor_signature or '',
            'supervisor_date': first_log.supervisor_date,
            'is_locked': False
        }
    else:
        metadata = {
            'bar_name': '',
            'location': '',
            'checked_by': '',
            'supervisor_name': '',
            'supervisor_signature': '',
            'supervisor_date': None,
            'is_locked': False
        }
    
    # Time slots and days
    time_slots = ['10:00 AM', '02:00 PM', '06:00 PM', '10:00 PM']
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    week_dates = [week_start_date + timedelta(days=i) for i in range(7)]
    
    return render_template('checklist/view_weekly_log_haccp.html',
                         units=units,
                         time_slots=time_slots,
                         days=days,
                         week_dates=week_dates,
                         week_start=week_start_date,
                         log_dict=log_dict,
                         metadata=metadata,
                         out_of_range_count=out_of_range_count)


@checklist_bp.route('/temperature-log/weekly/<week_start>/pdf')
@login_required
@role_required(['Manager', 'Bartender'])
def export_weekly_log_pdf(week_start):
    """Export weekly temperature log to PDF for audit purposes - HACCP Compliant"""
    try:
        week_start_date = datetime.strptime(week_start, '%Y-%m-%d').date()
    except:
        flash('Invalid week start date.', 'error')
        return redirect(url_for('checklist.temperature_log_index'))
    
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        
        # Get data
        weekly_meta = WeeklyTemperatureLog.query.filter_by(week_start_date=week_start_date).first()
        org_filter = get_organization_filter(ColdStorageUnit)
        units = ColdStorageUnit.query.filter(org_filter).filter_by(is_active=True).order_by(ColdStorageUnit.unit_type, ColdStorageUnit.unit_number).all()
        
        log_org_filter = get_organization_filter(TemperatureLog)
        logs = TemperatureLog.query.filter(
            log_org_filter,
            TemperatureLog.week_start_date == week_start_date
        ).all()
        
        log_dict = {}
        for log in logs:
            key = (log.log_date, log.time_slot, log.unit_id)
            log_dict[key] = log
        
        time_slots = ['10:00 AM', '02:00 PM', '06:00 PM', '10:00 PM']
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        week_dates = [week_start_date + timedelta(days=i) for i in range(7)]
        
        # Create PDF buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                               rightMargin=0.5*inch, leftMargin=0.5*inch,
                               topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        # Container for the 'Flowable' objects
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=12,
            alignment=TA_CENTER
        )
        elements.append(Paragraph('Weekly Cold Storage Temperature Log – HACCP Compliant', title_style))
        elements.append(Paragraph('<b>CCP (Critical Control Point)</b>', styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Metadata
        meta_data = []
        if weekly_meta:
            meta_data = [
                ['Bar/Outlet Name:', weekly_meta.bar_name or ''],
                ['Location:', weekly_meta.location or ''],
                ['Week Start Date:', week_start_date.strftime('%B %d, %Y')],
                ['Checked By:', weekly_meta.checked_by or ''],
            ]
            if weekly_meta.supervisor_name:
                meta_data.append(['Supervisor Name:', weekly_meta.supervisor_name])
                meta_data.append(['Supervisor Signature:', weekly_meta.supervisor_signature or ''])
                if weekly_meta.supervisor_date:
                    meta_data.append(['Supervisor Date:', weekly_meta.supervisor_date.strftime('%B %d, %Y')])
                meta_data.append(['Status:', 'LOCKED' if weekly_meta.is_locked else 'UNLOCKED'])
        
        if meta_data:
            meta_table = Table(meta_data, colWidths=[2*inch, 3*inch])
            meta_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.grey),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('BACKGROUND', (1, 0), (1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(meta_table)
            elements.append(Spacer(1, 0.2*inch))
        
        # Build table data
        table_data = []
        
        # Header row 1
        header1 = ['Day/Time']
        for unit in units:
            header1.append(unit.unit_number)
            header1.append('Status')
        header1.append('Corrective Action')
        table_data.append(header1)
        
        # Header row 2
        header2 = ['']
        for unit in units:
            min_temp, max_temp = unit.get_temp_range()
            if min_temp is not None and max_temp is not None:
                header2.append(f'Temp (°C)\n{min_temp}°-{max_temp}°')
            else:
                header2.append('Temp (°C)')
            header2.append('')
        header2.append('')
        table_data.append(header2)
        
        # Data rows
        for day_idx, day_date in enumerate(week_dates):
            day_name = days[day_idx]
            for time_idx, time_slot in enumerate(time_slots):
                row = []
                if time_idx == 0:
                    row.append(f'{day_name}\n{day_date.strftime("%b %d")}')
                else:
                    row.append('')
                row.append(time_slot)
                
                for unit in units:
                    log_key = (day_date, time_slot, unit.id)
                    log = log_dict.get(log_key)
                    if log:
                        row.append(f'{log.temperature}°C')
                        row.append(log.status)
                    else:
                        row.append('-')
                        row.append('-')
                
                # Corrective action
                action_text = ''
                for unit in units:
                    log_key = (day_date, time_slot, unit.id)
                    log = log_dict.get(log_key)
                    if log and log.status == 'OUT OF RANGE':
                        if log.corrective_action_type:
                            action_text += f'{unit.unit_number}: {log.corrective_action_type}'
                            if log.corrective_action:
                                action_text += f' - {log.corrective_action}'
                            if log.recheck_temperature:
                                action_text += f' (Recheck: {log.recheck_temperature}°C)'
                            action_text += '; '
                row.append(action_text.strip('; '))
                table_data.append(row)
        
        # Create table
        table = Table(table_data, repeatRows=2)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 1), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 1), 12),
            ('BACKGROUND', (0, 2), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 2), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        elements.append(Paragraph(f'Generated on {datetime.now().strftime("%B %d, %Y at %I:%M %p")} - HACCP Compliant Record', footer_style))
        
        # Build PDF
        doc.build(elements)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Create response
        filename = f"Temperature_Log_{week_start_date.strftime('%Y%m%d')}.pdf"
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
        
        return response
    except Exception as e:
        current_app.logger.error(f'Error generating PDF: {str(e)}', exc_info=True)
        flash(f'Error generating PDF: {str(e)}', 'error')
        return redirect(url_for('checklist.view_weekly_log', week_start=week_start))

