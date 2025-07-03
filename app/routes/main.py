# app/routes/main.py
from flask import Blueprint, render_template, request, flash, redirect, session, url_for
from app.models import VisitorLog, Request, db, User
from werkzeug.security import generate_password_hash
from app.utils.helpers import login_required, get_current_time
from datetime import datetime, timedelta
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

    latest_logs = (
        db.session.query(
            VisitorLog.unique_code,
            db.func.max(VisitorLog.timestamp).label("max_time")
        ).group_by(VisitorLog.unique_code)
    ).subquery()

    latest_log_entries = db.session.query(VisitorLog).join(
        latest_logs,
        db.and_(
            VisitorLog.unique_code == latest_logs.c.unique_code,
            VisitorLog.timestamp == latest_logs.c.max_time
        )
    )

    checked_in = latest_log_entries.filter(VisitorLog.status == "Checked-In").count()
    pending_requests = Request.query.filter_by(status="Pending").count()
    recent_logs = VisitorLog.query.order_by(VisitorLog.timestamp.desc()).limit(10).all()

    return render_template("Dashboard.html", logs=recent_logs,
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

    logs_query = VisitorLog.query

    manila_tz = pytz.timezone("Asia/Manila")

    if filter_date:
        try:
            filter_date_obj = datetime.strptime(filter_date, "%Y-%m-%d")
            start_of_day = manila_tz.localize(filter_date_obj.replace(hour=0, minute=0, second=0, microsecond=0)).astimezone(pytz.utc)
            end_of_day = start_of_day + timedelta(days=1)
            logs_query = logs_query.filter(
                VisitorLog.timestamp >= start_of_day,
                VisitorLog.timestamp < end_of_day
            )
        except ValueError:
            flash("Invalid date format.", "danger")
            return render_template("Logs.html", logs=[], filter_date=filter_date, search_query=search_query, pagination=None, per_page=per_page)
    else:
        if not search_query:
            now_manila = get_current_time()
            start_of_day = now_manila.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc)
            end_of_day = start_of_day + timedelta(days=1)
            logs_query = logs_query.filter(
                VisitorLog.timestamp >= start_of_day,
                VisitorLog.timestamp < end_of_day
            )

    if search_query:
        logs_query = logs_query.filter(VisitorLog.name.ilike(f"%{search_query}%"))

    logs_query = logs_query.order_by(VisitorLog.timestamp.desc())
    pagination = logs_query.paginate(page=page, per_page=per_page, error_out=False)
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
