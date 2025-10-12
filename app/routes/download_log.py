from flask import request, Response, Blueprint
from app.models import VisitorLog, db, User
from datetime import datetime
from sqlalchemy import func, case
from sqlalchemy.orm import aliased
import openpyxl
from openpyxl.styles import Font, Alignment
from io import BytesIO
import pytz

bp = Blueprint('download_log', __name__)

@bp.route('/export-logs-excel')
def export_logs_excel():
    filter_date = request.args.get('filter_date')
    search_query = request.args.get('search_query')

    # --- Database Query (same as your logs page) ---
    U_checkin = aliased(User, name='u_checkin')
    U_checkout = aliased(User, name='u_checkout')
    U_approved = aliased(User, name='u_approved')

    query = db.session.query(
        VisitorLog.name,
        VisitorLog.email,
        VisitorLog.number,
        VisitorLog.purpose,
        VisitorLog.address,
        func.max(U_approved.username).label('approved_by'),
        func.max(case((VisitorLog.status == 'Checked-In', VisitorLog.timestamp))).label('check_in_time'),
        func.max(case((VisitorLog.status == 'Checked-In', VisitorLog.check_in_gate))).label('gate_in'),
        func.max(case((VisitorLog.status == 'Checked-In', U_checkin.username))).label('checked_in_by'),
        func.max(case((VisitorLog.status == 'Checked-Out', VisitorLog.timestamp))).label('check_out_time'),
        func.max(case((VisitorLog.status == 'Checked-Out', VisitorLog.check_out_gate))).label('gate_out'),
        func.max(case((VisitorLog.status == 'Checked-Out', U_checkout.username))).label('checked_out_by'),
        func.date(func.timezone('Asia/Manila', func.max(VisitorLog.timestamp))).label('visit_date')
    ).select_from(VisitorLog).outerjoin(
        U_checkin, VisitorLog.check_in_by_id == U_checkin.id
    ).outerjoin(
        U_checkout, VisitorLog.check_out_by_id == U_checkout.id
    ).outerjoin(
        U_approved, VisitorLog.approved_by_id == U_approved.id
    ).group_by(
        VisitorLog.visit_session_id,
        VisitorLog.name,
        VisitorLog.email,
        VisitorLog.number,
        VisitorLog.purpose,
        VisitorLog.address
    )

    if filter_date:
        try:
            date_obj = datetime.strptime(filter_date, "%Y-%m-%d").date()
            query = query.having(func.date(func.timezone('Asia/Manila', func.max(VisitorLog.timestamp))) == date_obj)
        except ValueError:
            pass 

    if search_query:
        query = query.filter(VisitorLog.name.ilike(f"%{search_query}%"))

    logs = query.order_by(func.max(VisitorLog.timestamp).desc()).all()

    # --- Excel File Generation ---
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Visitor Logs"

    # Define headers
    headers = [
        "Name", "Email", "Number", "Purpose", "Address",
        "Approved By", "Check-In Time", "Check-In Gate", "Checked-In By",
        "Check-Out Time", "Check-Out Gate", "Checked-Out By", "Date"
    ]
    sheet.append(headers)

    # Style headers
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')

    # Add data rows
    manila_tz = pytz.timezone('Asia/Manila')
    for log in logs:
        check_in_time = log.check_in_time.astimezone(manila_tz).strftime('%I:%M %p') if log.check_in_time else '—'
        check_out_time = log.check_out_time.astimezone(manila_tz).strftime('%I:%M %p') if log.check_out_time else '—'
        visit_date = log.visit_date.strftime('%B %d, %Y') if log.visit_date else '—'
        
        row_data = [
            log.name, log.email, log.number, log.purpose, log.address,
            log.approved_by or '—',
            check_in_time,
            log.gate_in or '—',
            log.checked_in_by or '—',
            check_out_time,
            log.gate_out or '—',
            log.checked_out_by or '—',
            visit_date
        ]
        sheet.append(row_data)

    # Adjust column widths
    for col_cells in sheet.columns:
        max_length = 0
        column = col_cells[0].column_letter 
        for cell in col_cells:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = (max_length + 2)
        sheet.column_dimensions[column].width = adjusted_width

    # Save to a memory buffer
    excel_buffer = BytesIO()
    workbook.save(excel_buffer)
    excel_buffer.seek(0)
    
    # Create filename
    filename_date = filter_date or datetime.now(manila_tz).strftime('%Y-%m-%d')
    filename = f"visitor_logs_{filename_date}.xlsx"

    return Response(
        excel_buffer,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )