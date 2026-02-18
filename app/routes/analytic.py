from flask import Blueprint, request, jsonify
from flask_login import login_required
from datetime import datetime, timedelta
import pytz
from app.models import VisitorLog, Request, db
from sqlalchemy import func, case

bp = Blueprint('analytic', __name__)

@bp.route("/api/visit_durations")
@login_required
def visit_durations():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    # --- Efficient Duration Query ---
    # This query finds sessions that have both a check-in and check-out
    # and calculates the duration in a single database operation.
    query = db.session.query(
        VisitorLog.name,
        (func.max(VisitorLog.timestamp) - func.min(VisitorLog.timestamp)).label('duration')
    ).group_by(VisitorLog.visit_session_id, VisitorLog.name).having(
        # Ensure both statuses exist for a valid duration calculation
        func.count(case((VisitorLog.status == 'Checked-In', 1))) > 0,
        func.count(case((VisitorLog.status == 'Checked-Out', 1))) > 0
    )

    if start_date and end_date:
        try:
            # Convert string dates to datetime objects at the beginning and end of the day in Manila time
            manila_tz = pytz.timezone('Asia/Manila')
            start_dt = manila_tz.localize(datetime.strptime(start_date, "%Y-%m-%d")).astimezone(pytz.utc)
            end_dt = manila_tz.localize(datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).astimezone(pytz.utc)
            query = query.filter(VisitorLog.timestamp.between(start_dt, end_dt))
        except (ValueError, pytz.exceptions.AmbiguousTimeError):
            pass # Ignore invalid date formats

    logs = query.all()

    # Convert duration (which is a timedelta object) to minutes
    result = [{
        'name': log.name,
        'duration_minutes': round(log.duration.total_seconds() / 60, 2)
    } for log in logs]
    
    return jsonify(durations=result)

@bp.route("/api/destination_distribution")  # 1. Renamed Route
@login_required
def destination_distribution():             # 2. Renamed Function
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    
    manila_tz = 'Asia/Manila'
    date_column = func.date(func.timezone(manila_tz, VisitorLog.timestamp))

    # 3. Query 'destination' instead of 'purpose'
    query = db.session.query(
        VisitorLog.destination, 
        func.count(VisitorLog.id)
    ).filter(VisitorLog.status == "Checked-In")

    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(date_column.between(start_dt, end_dt))
        except ValueError:
            pass

    # 4. Group by 'destination'
    logs = query.group_by(VisitorLog.destination).order_by(func.count(VisitorLog.id).desc()).all()
    
    # 5. Return JSON with 'destination' key
    result = [{'destination': row.destination, 'count': row[1]} for row in logs]
    return jsonify(result)

@bp.route("/api/top_visitors")
@login_required
def top_visitors():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    manila_tz = 'Asia/Manila'
    date_column = func.date(func.timezone(manila_tz, VisitorLog.timestamp))

    query = db.session.query(
        VisitorLog.name,
        func.count(VisitorLog.id)
    ).filter(VisitorLog.status == "Checked-In")

    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(date_column.between(start_dt, end_dt))
        except ValueError:
            pass

    logs = query.group_by(VisitorLog.name).order_by(func.count(VisitorLog.id).desc()).limit(5).all()
    result = [{'name': row.name, 'count': row[1]} for row in logs]
    return jsonify(result)


@bp.route("/api/visitor_trend")
@login_required
def visitor_trend():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    manila_tz = 'Asia/Manila'
    date_column = func.date(func.timezone(manila_tz, VisitorLog.timestamp)).label("date")

    query = db.session.query(
        date_column,
        func.count(VisitorLog.id)
    ).filter(VisitorLog.status == "Checked-In")

    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(date_column.between(start_dt, end_dt))
        except ValueError:
            return jsonify({"error": "Invalid date format"}), 400

    logs = query.group_by(date_column).order_by(date_column).all()

    result = [{'date': str(row.date), 'count': row[1]} for row in logs]
    return jsonify(result)
