"""
PDF Generation Utility for Temperature Logs
"""
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime, date, timedelta


def format_date_display(log_date):
    """Format date as 'Day, Date, Year' (e.g., 'Friday, December 19, 2025')"""
    return log_date.strftime('%A, %B %d, %Y')


def format_temperature(temp):
    """Format temperature with °C symbol"""
    if temp is None:
        return "—"
    return f"{temp}°C"


def generate_temperature_log_pdf(units, start_date, end_date):
    """Generate PDF for temperature logs in landscape format with times as rows and dates as columns"""
    # Import here to avoid circular imports
    from models import TemperatureLog, TemperatureEntry
    
    buffer = BytesIO()
    # Use landscape orientation
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), topMargin=0.4*inch, bottomMargin=0.4*inch, 
                            leftMargin=0.3*inch, rightMargin=0.3*inch)
    
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=8,
        alignment=TA_CENTER
    )
    
    unit_header_style = ParagraphStyle(
        'UnitHeader',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=4,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Title
    title = Paragraph("Cold Storage Temperature Log – Unit Wise (HACCP)", title_style)
    story.append(title)
    story.append(Spacer(1, 0.15*inch))
    
    # Scheduled times (row headers)
    scheduled_times = ['10:00 AM', '02:00 PM', '06:00 PM', '10:00 PM']
    
    # Group dates by week (Monday to Sunday)
    def get_week_start(d):
        """Get Monday of the week for a given date"""
        days_since_monday = d.weekday()
        return d - timedelta(days=days_since_monday)
    
    # Group dates into weeks
    weeks = {}
    current_date = start_date
    while current_date <= end_date:
        week_start = get_week_start(current_date)
        if week_start not in weeks:
            weeks[week_start] = []
        weeks[week_start].append(current_date)
        current_date += timedelta(days=1)
    
    # Sort weeks
    sorted_weeks = sorted(weeks.keys())
    
    # Generate tables for each week
    for week_start in sorted_weeks:
        week_dates = sorted(weeks[week_start])
        
        # Limit to 7 days per week (or available dates)
        week_dates = week_dates[:7]
        
        # Process each unit separately (stacked vertically)
        for unit in units:
            # Unit Header
            unit_header = f"Unit {unit.unit_number} | {unit.location} | {unit.unit_type}"
            unit_header_para = Paragraph(unit_header, unit_header_style)
            
            # Build table data: times as rows, dates as columns
            # Header row: Time | Date1 | Date2 | Date3 | ...
            header_row = ['TIME'] + [d.strftime('%m/%d') for d in week_dates]
            table_data = [header_row]
            
            # Get all logs for this unit and week
            logs = {}
            for d in week_dates:
                log = TemperatureLog.query.filter_by(unit_id=unit.id, log_date=d).first()
                if log:
                    logs[d] = {entry.scheduled_time: entry for entry in log.entries.all()}
                else:
                    logs[d] = {}
            
            # Add rows for each time slot
            for time_slot in scheduled_times:
                row = [time_slot]
                for d in week_dates:
                    entry = logs.get(d, {}).get(time_slot)
                    if entry and entry.temperature is not None:
                        temp_str = format_temperature(entry.temperature)
                        initial = entry.initial or ""
                        # Combine temperature and initial
                        if initial:
                            cell_value = f"{temp_str} ({initial})"
                        else:
                            cell_value = temp_str
                        # Check if out of range
                        try:
                            if entry.is_out_of_range(unit):
                                cell_value = f"<font color='red'>{cell_value}</font>"
                        except:
                            pass
                        row.append(cell_value)
                    else:
                        row.append("—")
                table_data.append(row)
            
            # Calculate column widths (time column + date columns)
            # Landscape letter: 11 inches width, minus margins = ~10.4 inches
            # Use full width for single unit table
            time_col_width = 1 * inch
            date_col_width = (10.4 * inch - time_col_width) / len(week_dates)
            col_widths = [time_col_width] + [date_col_width] * len(week_dates)
            
            # Create table
            table = Table(table_data, colWidths=col_widths)
            
            # Table style
            table_style = [
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a1a1a')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
                ('TOPPADDING', (0, 0), (-1, 0), 5),
                # Time column (row headers)
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8e8e8')),
                ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 1), (0, -1), 8),
                # Data rows
                ('FONTNAME', (1, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (1, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
            ]
            
            # Highlight out of range temperatures
            for time_idx, time_slot in enumerate(scheduled_times, start=1):
                for date_idx, d in enumerate(week_dates, start=1):
                    entry = logs.get(d, {}).get(time_slot)
                    if entry and entry.temperature is not None:
                        try:
                            if entry.is_out_of_range(unit):
                                table_style.append(('BACKGROUND', (date_idx, time_idx), (date_idx, time_idx), colors.HexColor('#ffe6e6')))
                        except:
                            pass
            
            table.setStyle(TableStyle(table_style))
            
            # Add unit header and table (stacked vertically)
            story.append(KeepTogether([
                unit_header_para,
                Spacer(1, 0.08*inch),
                table
            ]))
            
            story.append(Spacer(1, 0.2*inch))
        
        # Page break between weeks (except last week)
        if week_start != sorted_weeks[-1]:
            story.append(PageBreak())
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_checklist_pdf(units, start_date, end_date, times):
    """Generate checklist PDF organized by date and time, showing all units for each date/time combination"""
    # Import here to avoid circular imports
    from models import TemperatureLog, TemperatureEntry
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=8,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold'
    )
    
    # Title
    title = Paragraph("Cold Storage Temperature Log Checklist (HACCP)", title_style)
    story.append(title)
    story.append(Spacer(1, 0.2*inch))
    
    # Generate one section per date/time combination
    current_date = start_date
    while current_date <= end_date:
        for time_slot in times:
            # Date and Time Header
            date_time_header = f"DATE: {format_date_display(current_date)} | TIME: {time_slot}"
            header_para = Paragraph(date_time_header, header_style)
            story.append(header_para)
            story.append(Spacer(1, 0.1*inch))
            
            # Table Headers
            table_data = [['UNIT NO', 'LOCATION', 'TYPE', 'TEMPERATURE (°C)', 'CORRECTIVE ACTION', 'INITIAL']]
            
            # Add rows for each unit
            for unit in units:
                log = TemperatureLog.query.filter_by(unit_id=unit.id, log_date=current_date).first()
                
                if log:
                    entry = TemperatureEntry.query.filter_by(log_id=log.id, scheduled_time=time_slot).first()
                else:
                    entry = None
                
                if entry and entry.temperature is not None:
                    temp = format_temperature(entry.temperature)
                    corrective = entry.corrective_action or "—"
                    initial = entry.initial or "—"
                else:
                    temp = "—"
                    corrective = "—"
                    initial = "—"
                
                row = [
                    unit.unit_number,
                    unit.location,
                    unit.unit_type,
                    temp,
                    corrective,
                    initial
                ]
                table_data.append(row)
            
            # Create table
            table = Table(table_data, colWidths=[1*inch, 1.5*inch, 1*inch, 1.2*inch, 2*inch, 0.8*inch])
            
            # Table style
            table_style = [
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a1a1a')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                # Data rows
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
                ('TOPPADDING', (0, 1), (-1, -1), 5),
            ]
            
            # Highlight out of range temperatures
            for idx, unit in enumerate(units, start=1):
                log = TemperatureLog.query.filter_by(unit_id=unit.id, log_date=current_date).first()
                if log:
                    entry = TemperatureEntry.query.filter_by(log_id=log.id, scheduled_time=time_slot).first()
                    if entry and entry.temperature is not None:
                        try:
                            if entry.is_out_of_range(unit):
                                table_style.append(('TEXTCOLOR', (3, idx), (3, idx), colors.red))
                                table_style.append(('BACKGROUND', (3, idx), (3, idx), colors.HexColor('#ffe6e6')))
                        except:
                            pass  # Skip if error checking range
            
            table.setStyle(TableStyle(table_style))
            story.append(table)
            story.append(Spacer(1, 0.3*inch))
        
        # Move to next date
        current_date += timedelta(days=1)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_bar_closing_checklist_pdf(unit, year, month_num):
    """Generate monthly PDF for BAR Closing Checklist in landscape format"""
    # Import here to avoid circular imports
    from models import BarClosingChecklistPoint, BarClosingChecklistEntry, BarClosingChecklistItem
    from calendar import monthrange
    from utils.helpers import get_organization_filter
    
    buffer = BytesIO()
    # Use landscape orientation
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), topMargin=0.4*inch, bottomMargin=0.4*inch, 
                            leftMargin=0.3*inch, rightMargin=0.3*inch)
    
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=8,
        alignment=TA_CENTER
    )
    
    # Title
    month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November', 'December']
    title = Paragraph(f"BAR Closing Checklist - {month_names[month_num-1]} {year}", title_style)
    story.append(title)
    story.append(Spacer(1, 0.15*inch))
    
    # Get all checklist points for this unit
    org_filter = get_organization_filter(BarClosingChecklistPoint)
    points = BarClosingChecklistPoint.query.filter(org_filter).filter_by(
        unit_id=unit.id,
        is_active=True
    ).order_by(BarClosingChecklistPoint.display_order).all()
    
    if not points:
        # No points defined
        no_points = Paragraph("No checklist points defined for this unit.", styles['Normal'])
        story.append(no_points)
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    # Get number of days in the month
    _, num_days = monthrange(year, month_num)
    
    # Generate dates for the month
    dates = []
    for day in range(1, num_days + 1):
        dates.append(date(year, month_num, day))
    
    # Get all entries for this month
    start_date = dates[0]
    end_date = dates[-1]
    
    org_filter_entry = get_organization_filter(BarClosingChecklistEntry)
    entries = BarClosingChecklistEntry.query.filter(org_filter_entry).filter(
        BarClosingChecklistEntry.unit_id == unit.id,
        BarClosingChecklistEntry.entry_date >= start_date,
        BarClosingChecklistEntry.entry_date <= end_date
    ).all()
    
    # Create a map of entry_date -> entry
    entries_map = {entry.entry_date: entry for entry in entries}
    
    # Get all items for these entries
    entry_ids = [entry.id for entry in entries]
    items_map = {}  # (entry_id, point_id) -> item
    if entry_ids:
        org_filter_item = get_organization_filter(BarClosingChecklistItem)
        items = BarClosingChecklistItem.query.filter(org_filter_item).filter(
            BarClosingChecklistItem.entry_id.in_(entry_ids)
        ).all()
        for item in items:
            items_map[(item.entry_id, item.checklist_point_id)] = item
    
    # Build table data
    # Header row: Checklist Point | Date1 | Date2 | Date3 | ...
    header_row = ['CHECKLIST POINT'] + [d.strftime('%d') for d in dates]
    table_data = [header_row]
    
    # Add rows for each checklist point
    for point in points:
        row = [f"{point.group_name}: {point.point_text}"]
        for d in dates:
            entry = entries_map.get(d)
            if entry:
                item = items_map.get((entry.id, point.id))
                if item and item.is_completed:
                    cell_value = "✓"
                    if item.staff_initials:
                        cell_value += f" ({item.staff_initials})"
                else:
                    cell_value = ""
            else:
                cell_value = ""
            row.append(cell_value)
        table_data.append(row)
    
    # Calculate column widths
    # Landscape letter: 11 inches width, minus margins = ~10.4 inches
    point_col_width = 2.5 * inch  # Wider for checklist point text
    date_col_width = (10.4 * inch - point_col_width) / len(dates)
    col_widths = [point_col_width] + [date_col_width] * len(dates)
    
    # Create table
    table = Table(table_data, colWidths=col_widths)
    
    # Table style
    table_style = [
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a1a1a')),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('TOPPADDING', (0, 0), (-1, 0), 5),
        # Checklist point column (row headers)
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8e8e8')),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (0, -1), 7),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('VALIGN', (0, 1), (0, -1), 'MIDDLE'),
        # Data rows
        ('FONTNAME', (1, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (1, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('VALIGN', (1, 1), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
    ]
    
    table.setStyle(TableStyle(table_style))
    story.append(table)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer
