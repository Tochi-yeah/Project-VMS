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

    query = db.session.query(
        VisitorLog.name,
        VisitorLog.email,
        VisitorLog.number,
        VisitorLog.purpose,
        VisitorLog.person_to_visit,
        VisitorLog.unique_code,
        func.max(
            case((VisitorLog.status == 'Checked-In', VisitorLog.timestamp))
        ).label('check_in_time'),
        func.max(
            case((VisitorLog.status == 'Checked-Out', VisitorLog.timestamp))
        ).label('check_out_time'),
        func.date(func.max(VisitorLog.timestamp)).label('visit_date')
    ).group_by(
        VisitorLog.unique_code,
        VisitorLog.name,
        VisitorLog.email,
        VisitorLog.number,
        VisitorLog.purpose,
        VisitorLog.person_to_visit
    )

    if filter_date:
        try:
            date_obj = datetime.strptime(filter_date, "%Y-%m-%d")
            start_of_day = manila_tz.localize(date_obj.replace(hour=0, minute=0, second=0, microsecond=0)).astimezone(pytz.utc)
            end_of_day = start_of_day + timedelta(days=1)
            query = query.having(
                func.max(VisitorLog.timestamp).between(start_of_day, end_of_day)
            )
        except ValueError:
            pass  # Ignore invalid date

    if search_query:
        query = query.filter(VisitorLog.name.ilike(f"%{search_query}%"))

    query = query.order_by(func.max(VisitorLog.timestamp).desc())

    logs = query.all()

    html = render_template('log-pdf-template.html', logs=logs)
    pdf = HTML(string=html).write_pdf()
    return send_file(BytesIO(pdf),
                     download_name='visitor_logs.pdf',
                     as_attachment=True)
