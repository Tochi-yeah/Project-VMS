# app/routes/main.py
import os
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import current_user, login_required
from app.models import VisitorLog, Request, db, User, Visitor
from werkzeug.utils import secure_filename
from app.utils.helpers import get_current_time, generate_unique_secure_code
from app.utils.qr_decoder import decode_qr
from datetime import datetime, timedelta
from sqlalchemy import case, func
from sqlalchemy.orm import aliased
from app import socketio, csrf, limiter
import uuid
import pytz


bp = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route("/")
def index():
    return redirect(url_for("auth.login"))

@bp.route("/dashboard")
@login_required
def dashboard():
    manila_tz = pytz.timezone("Asia/Manila")
    now_manila = get_current_time()
    start_of_day = now_manila.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc)
    end_of_day = start_of_day + timedelta(days=1)

    visitor_today = db.session.query(VisitorLog.visit_session_id).filter(
        VisitorLog.status == "Checked-In",
        VisitorLog.timestamp >= start_of_day,
        VisitorLog.timestamp < end_of_day
    ).distinct().count()

    latest_logs_sub = db.session.query(
        VisitorLog.visit_session_id,
        func.max(VisitorLog.timestamp).label("latest_time")
    ).group_by(VisitorLog.visit_session_id).subquery()

    checked_in = db.session.query(VisitorLog).join(
        latest_logs_sub,
        (VisitorLog.visit_session_id == latest_logs_sub.c.visit_session_id) &
        (VisitorLog.timestamp == latest_logs_sub.c.latest_time)
    ).filter(VisitorLog.status == 'Checked-In').count()

    pending_requests = Request.query.filter_by(status="Pending").count()
    
    # ✅ Aliases for all user roles needed in the query
    U_approved = aliased(User, name='u_approved')
    U_checkin = aliased(User, name='u_checkin')
    U_checkout = aliased(User, name='u_checkout')
    
    recent_visitors_query = db.session.query(
        VisitorLog.name,
        VisitorLog.purpose,
        VisitorLog.person_to_visit,
        func.max(case((VisitorLog.status=='Checked-In', VisitorLog.timestamp), else_=None)).label("check_in_time"),
        func.max(case((VisitorLog.status=='Checked-Out', VisitorLog.timestamp), else_=None)).label("check_out_time"),
        # ✅ Fetch all the data needed for the tooltips
        func.max(case((VisitorLog.status=='Checked-In', VisitorLog.check_in_gate), else_=None)).label("gate_in"),
        func.max(case((VisitorLog.status=='Checked-Out', VisitorLog.check_out_gate), else_=None)).label("gate_out"),
        func.max(case((VisitorLog.status == 'Checked-In', U_checkin.username), else_=None)).label('checked_in_by'),
        func.max(case((VisitorLog.status == 'Checked-Out', U_checkout.username), else_=None)).label('checked_out_by'),
        func.max(U_approved.username).label('admin_username'),
        func.date(func.timezone('Asia/Manila', func.max(VisitorLog.timestamp))).label("visit_date")
    ).select_from(VisitorLog).outerjoin(
        U_approved, VisitorLog.approved_by_id == U_approved.id
    ).outerjoin(
        U_checkin, VisitorLog.check_in_by_id == U_checkin.id
    ).outerjoin(
        U_checkout, VisitorLog.check_out_by_id == U_checkout.id
    ).group_by(
        VisitorLog.visit_session_id,
        VisitorLog.name,
        VisitorLog.purpose,
        VisitorLog.person_to_visit,
    ).order_by(func.max(VisitorLog.timestamp).desc()).limit(5).all()


    return render_template(
        "Dashboard.html",
        logs=recent_visitors_query,
        visitor_today=visitor_today,
        checked_in=checked_in,
        pending_requests=pending_requests
    )


@bp.route("/logs")
@login_required
def logs():
    filter_date = request.args.get("filter_date")
    search_query = request.args.get("search_query", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    now_manila = get_current_time()

    U_checkin = aliased(User, name='u_checkin')
    U_checkout = aliased(User, name='u_checkout')
    U_approved = aliased(User, name='u_approved') 

    base_query = db.session.query(
        VisitorLog.visit_session_id,
        VisitorLog.visitor_id,
        VisitorLog.name,
        VisitorLog.email,
        VisitorLog.number,
        VisitorLog.purpose,
        VisitorLog.person_to_visit,
        VisitorLog.unique_code,
        func.max(case((VisitorLog.status=='Checked-In', VisitorLog.timestamp), else_=None)).label('check_in_time'),
        func.max(case((VisitorLog.status=='Checked-In', VisitorLog.check_in_gate), else_=None)).label('gate_in'),
        func.max(case((VisitorLog.status=='Checked-Out', VisitorLog.timestamp), else_=None)).label('check_out_time'),
        func.max(case((VisitorLog.status=='Checked-Out', VisitorLog.check_out_gate), else_=None)).label('gate_out'),
        func.max(case((VisitorLog.status == 'Checked-In', U_checkin.username), else_=None)).label('checked_in_by'),
        func.max(case((VisitorLog.status == 'Checked-Out', U_checkout.username), else_=None)).label('checked_out_by'),
        func.max(U_approved.username).label('approved_by'), 
        func.date(func.timezone('Asia/Manila', func.max(VisitorLog.timestamp))).label('visit_date')
    ).select_from(VisitorLog).outerjoin(
        U_checkin, VisitorLog.check_in_by_id == U_checkin.id
    ).outerjoin(
        U_checkout, VisitorLog.check_out_by_id == U_checkout.id
    ).outerjoin(
        U_approved, VisitorLog.approved_by_id == U_approved.id 
    ).group_by(
        VisitorLog.visit_session_id,
        VisitorLog.visitor_id,
        VisitorLog.name,
        VisitorLog.email,
        VisitorLog.number,
        VisitorLog.purpose,
        VisitorLog.person_to_visit,
        VisitorLog.unique_code
    )
    if search_query:
        base_query = base_query.filter(VisitorLog.name.ilike(f"%{search_query}%"))

    if filter_date:
        try:
            filter_date_obj = datetime.strptime(filter_date, "%Y-%m-%d").date()
            base_query = base_query.having(
                func.date(func.timezone('Asia/Manila', func.max(VisitorLog.timestamp))) == filter_date_obj
            )
        except ValueError:
            flash("Invalid date format.", "danger")
            return render_template("Logs.html", logs=[], filter_date=filter_date, search_query=search_query, pagination=None, per_page=per_page)
    else:
        if not search_query:
            today_date = now_manila.date()
            base_query = base_query.having(
                func.date(func.timezone('Asia/Manila', func.max(VisitorLog.timestamp))) == today_date
            )

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
    return render_template("Setting.html")

@bp.route("/Registered-visitor-update", methods=["GET", "POST"])
@csrf.exempt
@limiter.exempt
def revisit():
    if request.method == "POST":
        qr_file = request.files.get("qr_upload")
        purpose = request.form.get("purpose", "").strip()
        if purpose == "Other":
            other_purpose = request.form.get("other_purpose", "").strip()
            if other_purpose:
                purpose = other_purpose
                
        person_to_visit = request.form.get("person", "").strip()

        if not qr_file or not allowed_file(qr_file.filename):
            flash("Invalid or missing QR code image.", "danger")
            return redirect(url_for('main.revisit'))

        temp_dir = os.path.join(current_app.root_path, 'static', 'temp')
        os.makedirs(temp_dir, exist_ok=True)

        filename = f"qr_{uuid.uuid4().hex}.png"
        temp_path = os.path.join(temp_dir, filename)
        qr_file.save(temp_path)

        qr_code_value = decode_qr(temp_path)

        os.remove(temp_path)

        if not qr_code_value:
            flash("Could not read QR code. Please try a clearer image.", "danger")
            return redirect(url_for('main.revisit'))

        visitor = Visitor.query.filter_by(qr_code=qr_code_value).first()
        if not visitor:
            flash("QR code not recognized. Visitor not found.", "danger")
            return redirect(url_for('main.revisit'))

        unique_code = generate_unique_secure_code()

        new_request = Request(
            name=visitor.name,
            email=visitor.email,
            number=visitor.number,
            purpose=purpose,
            person_to_visit=person_to_visit if person_to_visit else visitor.last_person_to_visit,
            unique_code=unique_code,
            status="Pending",
            timestamp=datetime.utcnow()
        )

        db.session.add(new_request)
        db.session.commit()
        socketio.emit('request_update')

        flash("Your visit request has been submitted for approval.", "success")
        return redirect(url_for('main.revisit'))

    return render_template("Already-registered.html")

