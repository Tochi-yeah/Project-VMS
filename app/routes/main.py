# app/routes/main.py
from flask import Blueprint, render_template, request, flash, redirect, session, url_for
from app.models import VisitorLog, Request, db, User
from werkzeug.security import generate_password_hash
from app.utils.helpers import login_required, get_current_time
from datetime import datetime, timedelta
from sqlalchemy import case, func
import pytz

bp = Blueprint('main', __name__)

@bp.route("/")
def index():
    return redirect(url_for("auth.login"))

@bp.route("/dashboard")
@login_required
def dashboard():
    # Manila timezone date range for today
    manila_tz = pytz.timezone("Asia/Manila")
    now_manila = get_current_time()
    start_of_day = now_manila.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc)
    end_of_day = start_of_day + timedelta(days=1)

    visitor_today = db.session.query(VisitorLog.unique_code).filter(
        VisitorLog.timestamp >= start_of_day,
        VisitorLog.timestamp < end_of_day,
        VisitorLog.status == "Checked-In"
    ).distinct().count()

    latest_logs_sub = db.session.query(
        VisitorLog.unique_code,
        func.max(VisitorLog.timestamp).label("latest_time")
    ).group_by(VisitorLog.unique_code).subquery()

# Join latest log entries and count those still Checked-In
    checked_in = db.session.query(VisitorLog).join(
        latest_logs_sub,
        (VisitorLog.unique_code == latest_logs_sub.c.unique_code) &
        (VisitorLog.timestamp == latest_logs_sub.c.latest_time)
    ).filter(VisitorLog.status == 'Checked-In').count()

    pending_requests = Request.query.filter_by(status="Pending").count()

    # ✅ Fixed recent logs query — getting latest check-in and check-out per visitor
    recent_visitors_sub = db.session.query(
        VisitorLog.name,
        VisitorLog.purpose,
        VisitorLog.person_to_visit,
        VisitorLog.unique_code,
        func.max(
            case(
                (VisitorLog.status == 'Checked-In', VisitorLog.timestamp)
            )
        ).label("check_in_time"),
        func.max(
            case(
                (VisitorLog.status == 'Checked-Out', VisitorLog.timestamp)
            )
        ).label("check_out_time"),
        func.date(func.max(VisitorLog.timestamp)).label("visit_date")
    ).group_by(
        VisitorLog.unique_code,
        VisitorLog.name,
        VisitorLog.purpose,
        VisitorLog.person_to_visit
    ).order_by(func.max(VisitorLog.timestamp).desc()).limit(5).all()

    return render_template("Dashboard.html", logs=recent_visitors_sub,
                           visitor_today=visitor_today,
                           checked_in=checked_in,
                           pending_requests=pending_requests)

@bp.route("/logs")
@login_required
def logs():
    filter_date = request.args.get("filter_date")
    search_query = request.args.get("search_query", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    manila_tz = pytz.timezone("Asia/Manila")

    base_query = db.session.query(
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

    # Apply date filter if needed
    if filter_date:
        try:
            filter_date_obj = datetime.strptime(filter_date, "%Y-%m-%d")
            start_of_day = manila_tz.localize(filter_date_obj.replace(hour=0, minute=0, second=0, microsecond=0)).astimezone(pytz.utc)
            end_of_day = start_of_day + timedelta(days=1)
            base_query = base_query.having(
                func.max(VisitorLog.timestamp).between(start_of_day, end_of_day)
            )
        except ValueError:
            flash("Invalid date format.", "danger")
            return render_template("Logs.html", logs=[], filter_date=filter_date, search_query=search_query, pagination=None, per_page=per_page)

    if search_query:
        base_query = base_query.filter(VisitorLog.name.ilike(f"%{search_query}%"))

    base_query = base_query.order_by(func.max(VisitorLog.timestamp).desc())

    pagination = base_query.paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items

    return render_template(
        "Logs.html",
        logs=logs,
        filter_date=filter_date,
        search_query=search_query,
        pagination=pagination,
        per_page=per_page
    )

@bp.route("/analytic")
@login_required
def analytic():
    return render_template("Analytic.html")

@bp.route("/setting")
@login_required
def setting():
    user = User.query.get(session['user_id'])
    return render_template("Setting.html", user=user)
