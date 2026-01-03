# app/routes/request.py
# This version sends emails directly (synchronously) without using background threads.

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_login import current_user, login_required
from app.models import db, Request, Visitor, VisitorLog
from app.utils.helpers import generate_unique_secure_code, get_current_time
from app.brevo_mailer import send_visitor_qr_email, send_group_qr_email
from app import csrf, socketio, limiter
from datetime import datetime
from collections import defaultdict
from werkzeug.utils import secure_filename
import pytz
import uuid
import pandas as pd
import secrets

bp = Blueprint('request_bp', __name__)

@bp.route("/request")
@login_required
def request_page():
    search_query = request.args.get("search_query", "").strip()
    filter_date_str = request.args.get("filter_date")
    # Get the page number from URL arguments, default to 1
    page = request.args.get('page', 1, type=int)
    
    # --- ADDED: LOGIC TO REMEMBER PER_PAGE SETTING ---
    per_page_from_request = request.args.get("per_page")
    if per_page_from_request:
        session['per_page'] = int(per_page_from_request)
    per_page = session.get('per_page', 10)
    # --- END OF ADDED LOGIC ---

    query = Request.query
    if filter_date_str:
        try:
            target_date = datetime.strptime(filter_date_str, "%Y-%m-%d").date()
            query = query.filter(db.func.date(db.func.timezone('Asia/Manila', Request.timestamp)) == target_date)
        except ValueError:
            pass
    elif filter_date_str is None:
        today = get_current_time().date()
        query = query.filter(db.func.date(db.func.timezone('Asia/Manila', Request.timestamp)) == today)
    
    if search_query:
        query = query.filter(Request.name.ilike(f"%{search_query}%"))
    
    # MODIFIED: Use paginate() instead of all()
    pagination = query.order_by(Request.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
    all_matching_requests = pagination.items

    checked_in_codes = set()
    if all_matching_requests:
        unique_codes = [req.unique_code for req in all_matching_requests]
        subquery = db.session.query(VisitorLog.unique_code, db.func.max(VisitorLog.timestamp).label('max_timestamp')).filter(VisitorLog.unique_code.in_(unique_codes)).group_by(VisitorLog.unique_code).subquery()
        checked_in_logs = db.session.query(VisitorLog.unique_code).join(subquery, db.and_(VisitorLog.unique_code == subquery.c.unique_code, VisitorLog.timestamp == subquery.c.max_timestamp)).filter(VisitorLog.status == 'Checked-In').all()
        checked_in_codes = {log.unique_code for log in checked_in_logs}

    grouped_requests = defaultdict(list)
    for req in all_matching_requests:
        if req.group_code:
            grouped_requests[req.group_code].append(req)
        else:
            grouped_requests[f"single-{req.id}"].append(req)

    return render_template(
        "Request.html",
        groups=grouped_requests,
        checked_in_codes=checked_in_codes,
        search_query=search_query,
        filter_date=filter_date_str,
        pagination=pagination  # Pass the pagination object to the template
    )

@bp.route("/Visitor-register-form")
def online_reg():
    return render_template("Visitor-register.html")

@bp.route("/help-faq")
def public_help():
    return render_template("public_help.html")   

@bp.route("/registration-success")
def registration_success():
    # Get data from the session, or redirect if accessed directly
    unique_code = session.pop('reg_success_code', None)
    name = session.pop('reg_success_name', None)
    email = session.pop('reg_success_email', None)

    if not unique_code or not name:
        # If no code/name, they didn't just register. Send them back.
        return redirect(url_for('request_bp.online_reg'))

    return render_template(
        "registration_success.html", 
        unique_code=unique_code, 
        name=name, 
        email=email
    )

@bp.route("/multi-registration-success")
def multi_registration_success():
    # Get data from the session
    visitors = session.pop('multi_reg_visitors', None)
    group_code = session.pop('multi_reg_group_code', None)

    if not visitors:
        # If no visitor data, they didn't just register. Send them back.
        return redirect(url_for('request_bp.multi_form_entry'))

    return render_template(
        "multi_registration_success.html",
        visitors=visitors,
        group_code=group_code
    )

# ✅ UPDATED: submit_request (Added destination)
@bp.route("/submit-request", methods=["POST"])
@csrf.exempt
@limiter.exempt
def submit_request():
    first_name = request.form.get("first_name", "").strip()
    middle_initial_raw = request.form.get("middle_initial", "").strip()
    last_name = request.form.get("last_name", "").strip()
    middle_initial = middle_initial_raw[0].upper() if middle_initial_raw else ""
    full_name = f"{first_name} {middle_initial+'. ' if middle_initial else ''}{last_name}"

    no_email = request.form.get("no_email")
    email = "" if no_email else request.form.get("email", "").strip()

    if not no_email and not email:
        flash("Email is required unless you check the 'No Email' box.", "danger")
        return redirect(url_for('request_bp.online_reg'))

    number = request.form.get("cell_number", "").strip()
    
    # Purpose Logic
    purpose = request.form.get("purpose", "").strip()
    if purpose == "Other":
        purpose = request.form.get("other_purpose", "").strip()
    
    # 🆕 NEW: Destination Logic
    destination = request.form.get("destination", "").strip()
    
    address = request.form.get("address", "").strip()

    # Validate all fields including destination
    if not all([first_name, last_name, number, purpose, destination, address]):
        flash("Please fill out all required fields.", "danger")
        return redirect(url_for('request_bp.online_reg'))

    unique_code = generate_unique_secure_code()
    new_request = Request(
        name=full_name, email=email, number=number, purpose=purpose,
        destination=destination, # <--- Added here
        address=address, unique_code=unique_code, status="Approve",
        timestamp=datetime.utcnow()
    )
    db.session.add(new_request)
    db.session.commit()

    if new_request.email:
        try:
            send_visitor_qr_email(new_request)
        except Exception as e:
            print(f"Error sending email for {new_request.email}: {e}")

    socketio.emit('dashboard_update')
    socketio.emit('request_update')

    session['reg_success_code'] = new_request.unique_code
    session['reg_success_name'] = new_request.name
    session['reg_success_email'] = new_request.email

    return redirect(url_for('request_bp.registration_success'))


# ✅ UPDATED: direct_checkin (Saves destination to logs)
@bp.route("/direct-checkin/<int:request_id>", methods=["POST"])
@login_required
def direct_checkin(request_id):
    req = Request.query.get_or_404(request_id)

    last_log = VisitorLog.query.filter_by(unique_code=req.unique_code).order_by(VisitorLog.timestamp.desc()).first()
    if last_log and last_log.status == "Checked-In" and last_log.timestamp.astimezone(pytz.timezone('Asia/Manila')).date() == get_current_time().date():
        flash(f"{req.name} is already checked in.", "warning")
        return redirect(url_for('request_bp.request_page'))

    visitor = Visitor.query.filter_by(name=req.name, number=req.number).first()
    if not visitor:
        visitor = Visitor(
            name=req.name, email=req.email, number=req.number, qr_code=req.unique_code, 
            last_purpose=req.purpose, 
            last_destination=req.destination, # <--- Added here
            last_address=req.address
        )
        db.session.add(visitor)
        db.session.flush()
    else:
        visitor.last_purpose = req.purpose
        visitor.last_destination = req.destination # <--- Update here
        visitor.last_address = req.address

    new_log = VisitorLog(
        visitor_id=visitor.id,
        name=visitor.name,
        email=visitor.email,
        number=visitor.number,
        purpose=req.purpose,
        destination=req.destination, # <--- Added here
        address=req.address,
        status="Checked-In",
        unique_code=req.unique_code,
        visit_session_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow(),
        check_in_by_id=current_user.id,
        check_in_gate=current_user.gate_role,
        approved_by_id=current_user.id
    )
    db.session.add(new_log)
    db.session.commit()
    flash(f"{visitor.name} has been checked in.", "success")
    socketio.emit('dashboard_update')
    socketio.emit('request_update')
    return redirect(url_for('request_bp.request_page'))


# ✅ UPDATED: direct_checkin_group (Saves destination to logs)
@bp.route("/direct-checkin-group/<group_code>", methods=["POST"])
@login_required
def direct_checkin_group(group_code):
    group_requests = Request.query.filter_by(group_code=group_code).all()
    checked_in_count = 0
    for req in group_requests:
        last_log = VisitorLog.query.filter_by(unique_code=req.unique_code).order_by(VisitorLog.timestamp.desc()).first()
        if last_log and last_log.status == "Checked-In" and last_log.timestamp.astimezone(pytz.timezone('Asia/Manila')).date() == get_current_time().date():
            continue

        visitor = Visitor.query.filter_by(name=req.name, number=req.number).first()
        if not visitor:
            visitor = Visitor(
                name=req.name, email=req.email, number=req.number,
                qr_code=req.unique_code, last_purpose=req.purpose, 
                last_destination=req.destination, # <--- Added here
                last_address=req.address
            )
            db.session.add(visitor)
            db.session.flush()
        else:
            visitor.last_purpose = req.purpose
            visitor.last_destination = req.destination # <--- Update here
            visitor.last_address = req.address

        new_log = VisitorLog(
            visitor_id=visitor.id, name=visitor.name, email=visitor.email,
            number=visitor.number, purpose=req.purpose, 
            destination=req.destination, # <--- Added here
            address=req.address,
            status="Checked-In", unique_code=req.unique_code,
            visit_session_id=str(uuid.uuid4()), timestamp=datetime.utcnow(),
            check_in_by_id=current_user.id, check_in_gate=current_user.gate_role,
            approved_by_id=current_user.id
        )
        db.session.add(new_log)
        checked_in_count += 1
    
    db.session.commit()
    flash(f"{checked_in_count} new members of group {group_code} have been checked in.", "success")
    socketio.emit('dashboard_update')
    socketio.emit('request_update')
    return redirect(url_for('request_bp.request_page'))


# ✅ UPDATED: multi_form_entry (Added destination loop)
@bp.route('/Multi-form-entry', methods=['GET', 'POST'])
@limiter.exempt
@csrf.exempt
def multi_form_entry():
    if request.method == 'POST':
        created = []
        idx = 1
        group_code = None 

        while True:
            first = request.form.get(f"first_name_{idx}", "").strip()
            if not first: break
            middle_raw = request.form.get(f"middle_initial_{idx}", "").strip()
            middle = (middle_raw[0].upper() + ".") if middle_raw else ""
            last = request.form.get(f"last_name_{idx}", "").strip()
            phone = request.form.get(f"phone_{idx}", "").strip()
            no_email = request.form.get(f"no_email_{idx}")
            email = "" if no_email else request.form.get(f"email_{idx}", "").strip()
            
            # Purpose Logic
            purpose = request.form.get(f"purpose_{idx}", "").strip()
            if purpose == "Other":
                other = request.form.get(f"other_purpose_{idx}", "").strip()
                if other: purpose = other
            
            # 🆕 Destination Logic
            destination = request.form.get(f"destination_{idx}", "").strip()
            
            address = request.form.get(f"address_{idx}", "").strip()
            
            # Added destination to validation
            if not all([first, last, phone, purpose, destination, address]):
                idx += 1
                continue
            
            full_name = f"{first} {middle+' ' if middle else ''}{last}".strip()
            unique_code = generate_unique_secure_code()
            new_request = Request(
                name=full_name, email=email, number=phone, purpose=purpose, 
                destination=destination, # <--- Added here
                address=address,
                unique_code=unique_code, status="Approve", timestamp=datetime.utcnow()
            )
            db.session.add(new_request)
            created.append(new_request)
            idx += 1
        
        if created:
            if len(created) > 1:
                group_code = generate_unique_secure_code()
                for r in created:
                    r.group_code = group_code
            db.session.commit()

            if group_code and len(created) > 1:
                try:
                    send_group_qr_email(created)
                except Exception as e:
                    print(f"Error sending group email for multi-form: {e}")
            elif created and created[0].email:
                try:
                    send_visitor_qr_email(created[0])
                except Exception as e:
                    print(f"Error sending email for {created[0].email}: {e}")

            socketio.emit('dashboard_update')
            socketio.emit('request_update')

            visitors_data = [
                {"name": r.name, "unique_code": r.unique_code} for r in created
            ]

            session['multi_reg_visitors'] = visitors_data
            session['multi_reg_group_code'] = group_code

            return redirect(url_for('request_bp.multi_registration_success'))
        else:
            flash("No valid visitor entries submitted.", "danger")
            return redirect(url_for('request_bp.multi_form_entry'))
    return render_template("Multi-form-entry.html")


# ✅ UPDATED: upload_csv (Added Destination column read)
@bp.route("/upload_csv", methods=["POST"])
@csrf.exempt
def upload_csv():
    file = request.files.get("file")
    if not file:
        flash("No file selected.", "danger")
        return redirect(url_for("request_bp.request_page"))
    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower()
    try:
        if ext == "csv": df = pd.read_csv(file)
        elif ext in ["xlsx", "xls"]: df = pd.read_excel(file)
        else:
            flash("Invalid file format. Please upload a CSV or Excel file.", "danger")
            return redirect(url_for("request_bp.request_page"))
    except Exception as e:
        flash(f"Failed to process file: {str(e)}", "danger")
        return redirect(url_for("request_bp.request_page"))
    created_requests = []
    group_code = secrets.token_urlsafe(12)
    for _, row in df.iterrows():
        full_name = str(row.get("Name", "")).strip()
        if not full_name: continue
        new_request = Request(
            name=full_name, email=str(row.get("Email", "")).strip(), number=str(row.get("Phone", "")).strip(),
            purpose=str(row.get("Purpose", "")).strip(), 
            destination=str(row.get("Destination", "")).strip(), # <--- Added here (Ensure CSV has "Destination" column)
            address=str(row.get("Address", "")).strip(),
            unique_code=generate_unique_secure_code(), status="Approve",
            timestamp=datetime.utcnow(), group_code=group_code
        )
        created_requests.append(new_request)
    if created_requests:
        db.session.add_all(created_requests)
        db.session.commit()
        try:
            send_group_qr_email(created_requests)
        except Exception as e:
            print(f"Error sending group email for CSV upload: {e}")
        socketio.emit("request_update")
        flash(f"{len(created_requests)} requests uploaded successfully!", "success")
    else:
        flash("No valid rows found in the file.", "warning")
    return redirect(url_for("request_bp.request_page"))