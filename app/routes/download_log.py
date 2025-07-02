from flask import request, render_template, send_file, Blueprint
from io import BytesIO
from weasyprint import HTML
from app.models import VisitorLog, db  # Adjust as needed
from datetime import datetime

bp = Blueprint('download_log', __name__)

@bp.route('/export-logs-pdf')
def export_logs_pdf():
    filter_date = request.args.get('filter_date')
    search_query = request.args.get('search_query')

    query = VisitorLog.query
    if filter_date:
        try:
            # Convert string to date object
            date_obj = datetime.strptime(filter_date, "%Y-%m-%d").date()
            query = query.filter(db.func.date(VisitorLog.timestamp) == date_obj)
        except ValueError:
            pass  # Ignore invalid date
    if search_query:
        query = query.filter(VisitorLog.name.ilike(f"%{search_query}%"))
    logs = query.all()

    html = render_template('log-pdf-template.html', logs=logs)
    pdf = HTML(string=html).write_pdf()
    return send_file(BytesIO(pdf),
                     download_name='visitor_logs.pdf',
                     as_attachment=True)