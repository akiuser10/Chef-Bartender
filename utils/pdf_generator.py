"""
PDF Generation Utility for Temperature Logs
"""
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime, date, timedelta
from models import TemperatureLog, TemperatureEntry


def format_date_display(log_date):
    """Format date as 'Day, Date, Year' (e.g., 'Friday, December 19, 2025')"""
    return log_date.strftime('%A, %B %d, %Y')


def format_temperature(temp):
    """Format temperature with °C symbol"""
    if temp is None:
        return "—"
    return f"{temp}°C"


def generate_temperature_log_pdf(units, start_date, end_date):
    """Generate PDF for temperature logs for given units and date range"""
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
        fontSize=10,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=6,
        alignment=TA_LEFT
    )
    
    # Title
    title = Paragraph("Cold Storage Temperature Log – Unit Wise (HACCP)", title_style)
    story.append(title)
    story.append(Spacer(1, 0.2*inch))
    
    # Generate one page per unit
    for unit in units:
        # Unit Header
        unit_header_data = [
            [f"UNIT NO: {unit.unit_number}", f"LOCATION: {unit.location}"],
            [f"UNIT TYPE: {unit.unit_type}", ""]
        ]
        
        unit_header_table = Table(unit_header_data, colWidths=[3.5*inch, 3.5*inch])
        unit_header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(unit_header_table)
        story.append(Spacer(1, 0.1*inch))
        
        # Get logs for date range
        current_date = start_date
        while current_date <= end_date:
            log = TemperatureLog.query.filter_by(unit_id=unit.id, log_date=current_date).first()
            
            # Date Header
            date_para = Paragraph(f"DATE: {format_date_display(current_date)}", header_style)
            story.append(date_para)
            story.append(Spacer(1, 0.1*inch))
            
            # Table Headers
            table_data = [['TIME', 'TEMPERATURE (°C)', 'CORRECTIVE ACTION', 'INITIAL']]
            
            # Scheduled times
            scheduled_times = ['10:00 AM', '02:00 PM', '06:00 PM', '10:00 PM']
            
            if log:
                entries = {entry.scheduled_time: entry for entry in log.entries.all()}
            else:
                entries = {}
            
            # Add rows for each scheduled time
            for time_slot in scheduled_times:
                entry = entries.get(time_slot)
                
                if entry and entry.temperature is not None:
                    temp = format_temperature(entry.temperature)
                    corrective = entry.corrective_action or "—"
                    initial = entry.initial or "—"
                    
                    # Check if out of range
                    is_out_of_range = entry.is_out_of_range(unit)
                else:
                    temp = "—"
                    corrective = "—"
                    initial = "—"
                    is_out_of_range = False
                
                row = [time_slot, temp, corrective, initial]
                table_data.append(row)
            
            # Create table
            table = Table(table_data, colWidths=[1.5*inch, 2*inch, 2.5*inch, 1*inch])
            
            # Table style
            table_style = [
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a1a1a')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                # Data rows
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
            ]
            
            # Highlight out of range temperatures in red
            if log:
                for idx, time_slot in enumerate(scheduled_times, start=1):
                    entry = entries.get(time_slot)
                    if entry and entry.temperature is not None:
                        try:
                            if entry.is_out_of_range(unit):
                                table_style.append(('TEXTCOLOR', (1, idx), (1, idx), colors.red))
                                table_style.append(('BACKGROUND', (1, idx), (1, idx), colors.HexColor('#ffe6e6')))
                        except:
                            pass  # Skip if error checking range
            
            table.setStyle(TableStyle(table_style))
            story.append(table)
            
            # Supervisor verification section
            if log and log.supervisor_verified:
                story.append(Spacer(1, 0.1*inch))
                verify_text = f"Verified by: {log.supervisor_name or 'N/A'} on {log.supervisor_verified_at.strftime('%Y-%m-%d %H:%M') if log.supervisor_verified_at else 'N/A'}"
                verify_para = Paragraph(verify_text, styles['Normal'])
                story.append(verify_para)
            
            story.append(Spacer(1, 0.2*inch))
            
            # Move to next date
            current_date += timedelta(days=1)
        
        # Add page break between units (except for last unit)
        if unit != units[-1]:
            story.append(PageBreak())
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer
