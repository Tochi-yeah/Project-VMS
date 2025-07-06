from flask import request, render_template, send_file, Blueprint
from io import BytesIO
from weasyprint import HTML
from app.models import VisitorLog, db
from datetime import datetime, timedelta
from sqlalchemy import func, case
import pytz

bp = Blueprint('download_log', __name__)

@bp.route('/export-logs-pdf')
def export_logs_pdf():
    filter_date = request.args.get('filter_date')
    search_query = request.args.get('search_query')

    manila_tz = pytz.timezone("Asia/Manila")
    today_manila = datetime.now(manila_tz).strftime('%Y-%m-%d')

    if not filter_date:
        filter_date = today_manila

    query = db.session.query(
        VisitorLog.visit_session_id,
        VisitorLog.name,
        VisitorLog.email,
        VisitorLog.number,
        VisitorLog.purpose,
        VisitorLog.person_to_visit,
        func.max(
            case((VisitorLog.status == 'Checked-In', VisitorLog.timestamp))
        ).label('check_in_time'),
        func.max(
            case((VisitorLog.status == 'Checked-Out', VisitorLog.timestamp))
        ).label('check_out_time'),
        func.date(func.timezone('Asia/Manila', func.max(VisitorLog.timestamp))).label('visit_date')
    ).group_by(
        VisitorLog.visit_session_id,
        VisitorLog.name,
        VisitorLog.email,
        VisitorLog.number,
        VisitorLog.purpose,
        VisitorLog.person_to_visit
    )


    try:
        date_obj = datetime.strptime(filter_date, "%Y-%m-%d")
        start_of_day = manila_tz.localize(date_obj.replace(hour=0, minute=0, second=0, microsecond=0)).astimezone(pytz.utc)
        end_of_day = start_of_day + timedelta(days=1)
        query = query.having(
            func.max(VisitorLog.timestamp).between(start_of_day, end_of_day)
        )
    except ValueError:
        pass  # ignore invalid date

    if search_query:
        query = query.filter(VisitorLog.name.ilike(f"%{search_query}%"))

    query = query.order_by(func.max(VisitorLog.timestamp).desc())
    logs = query.all()

    # Render PDF content and filename
    html = render_template('log-pdf-template.html', logs=logs, filter_date=filter_date)
    pdf = HTML(string=html).write_pdf()
    filename = f"visitor_logs_{filter_date}.pdf"

    return send_file(BytesIO(pdf),
                     download_name=filename,
                     as_attachment=True)
