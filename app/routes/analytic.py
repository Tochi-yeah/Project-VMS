from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import pytz
from app.models import VisitorLog, Request, db

bp = Blueprint('analytic', __name__)

# Clean visitor durations
def get_visit_durations(start_date=None, end_date=None):
    query = db.session.query(
        VisitorLog.visit_session_id,
        VisitorLog.name,
        db.func.min(VisitorLog.timestamp).label("check_in"),
        db.func.max(VisitorLog.timestamp).label("check_out")
    ).group_by(VisitorLog.visit_session_id, VisitorLog.name)

    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            query = query.filter(db.func.date(VisitorLog.timestamp).between(start_dt, end_dt))
        except Exception as e:
            print("Date parsing error:", e)

    logs = query.all()

    result = []
    for log in logs:
        # Get statuses within this visit_session_id
        statuses = db.session.query(VisitorLog.status).filter_by(visit_session_id=log.visit_session_id).all()
        statuses = [s[0] for s in statuses]

        # Only compute if both check-in and check-out exist
        if "Checked-In" in statuses and "Checked-Out" in statuses and log.check_in != log.check_out:
            duration = (log.check_out - log.check_in).total_seconds() / 60  # minutes
            result.append({
                'name': log.name,
                'duration_minutes': round(duration, 2)
            })
    return result



@bp.route("/api/visit_durations")
def visit_durations():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    durations = get_visit_durations(start_date, end_date)
    return jsonify(durations=durations)


@bp.route("/api/request_status_distribution")
def request_status_distribution():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    manila_tz = 'Asia/Manila'
    date_column = db.func.date(db.func.timezone(manila_tz, Request.timestamp)).label("date")

    query = db.session.query(
        Request.status,
        db.func.count(Request.id)
    ).filter(Request.status.in_(["Approve", "Reject"]))

    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(date_column.between(start_dt, end_dt))
        except ValueError:
            pass

    statuses = query.group_by(Request.status).all()

    # Initialize counts to zero to avoid missing keys
    result_dict = {'Approve': 0, 'Reject': 0}
    for row in statuses:
        result_dict[row.status] = row[1]

    result = [{'status': key, 'count': value} for key, value in result_dict.items()]
    return jsonify(result)

@bp.route("/api/purpose_distribution")
def purpose_distribution():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    query = db.session.query(
        VisitorLog.purpose,
        db.func.count(VisitorLog.id)
    ).filter(VisitorLog.status == "Checked-In")

    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            query = query.filter(db.func.date(VisitorLog.timestamp).between(start_dt, end_dt))
        except ValueError:
            pass

    logs = query.group_by(VisitorLog.purpose).order_by(db.func.count(VisitorLog.id).desc()).all()
    result = [{'purpose': row.purpose, 'count': row[1]} for row in logs]
    return jsonify(result)


@bp.route("/api/top_visitors")
def top_visitors():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    query = db.session.query(
        VisitorLog.name,
        db.func.count(VisitorLog.id)
    ).filter(VisitorLog.status == "Checked-In")

    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            query = query.filter(db.func.date(VisitorLog.timestamp).between(start_dt, end_dt))
        except ValueError:
            pass

    logs = query.group_by(VisitorLog.name).order_by(db.func.count(VisitorLog.id).desc()).limit(5).all()
    result = [{'name': row.name, 'count': row[1]} for row in logs]
    return jsonify(result)


@bp.route("/api/visitor_trend")
def visitor_trend():
    days = request.args.get("days", type=int)
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    manila_tz = 'Asia/Manila'

    # Convert timestamp to Manila time before extracting the date
    date_column = db.func.date(db.func.timezone(manila_tz, VisitorLog.timestamp)).label("date")

    query = db.session.query(
        date_column,
        db.func.count(VisitorLog.id)
    ).filter(VisitorLog.status == "Checked-In")

    today = datetime.now(pytz.timezone(manila_tz)).date()

    if days:
        date_from = today - timedelta(days=days)
        query = query.filter(date_column >= date_from)
    elif start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(date_column.between(start_dt, end_dt))
        except ValueError:
            return jsonify({"error": "Invalid date format"}), 400

    logs = query.group_by(date_column).order_by(date_column).all()

    result = [{'date': str(row.date), 'count': row[1]} for row in logs]
    return jsonify(result)

