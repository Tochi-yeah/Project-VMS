# app/routes/request.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required
from app.models import db, Request, Visitor
from app.utils.helpers import generate_unique_secure_code
from app.brevo_mailer import send_visitor_qr_email, send_group_qr_email
# Removed Temporarily
#from app.mailer import send_visitor_qr_email, send_email
from app.utils.qr_decoder import generate_qr_code
from app import csrf, socketio, limiter
from datetime import datetime
from collections import defaultdict
from werkzeug.utils import secure_filename
from io import TextIOWrapper
import pandas as pd
import secrets
import os
import csv


bp = Blueprint('request_bp', __name__)

@bp.route("/request")
@login_required
@csrf.exempt
@limiter.exempt
def request_page():
    requests = Request.query.filter_by(status="Pending").all()

    grouped_requests = defaultdict(list)
    for req in requests:
        if req.group_code:
            grouped_requests[req.group_code].append(req)
        else:
            # single requests are treated as their own "group"
            grouped_requests[f"single-{req.id}"].append(req)

    return render_template(
        "Request.html",
        groups=grouped_requests,
        per_page=10
    )

@bp.route("/Visitor-register-form")
def online_reg():
    return render_template("Visitor-register.html")

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
    purpose = request.form.get("purpose", "").strip()

    if purpose == "Other":
        other_purpose = request.form.get("other_purpose", "").strip()
        purpose = other_purpose

    person_to_visit = request.form.get("person_to_visit", "").strip()

    if not all([first_name, last_name, number, purpose, person_to_visit]):
        flash("Please fill out all required fields.", "danger")
        return redirect(url_for('request_bp.online_reg'))

    unique_code = generate_unique_secure_code()

    new_request = Request(
        name=full_name,
        email=email,
        number=number,
        purpose=purpose,
        person_to_visit=person_to_visit,
        unique_code=unique_code,
        timestamp=datetime.utcnow()
    )
    db.session.add(new_request)
    db.session.commit()
    socketio.emit('dashboard_update')
    socketio.emit('request_update')  # <-- ADD THIS LINE

    flash("Request submitted successfully!", "success")
    return redirect(url_for('request_bp.online_reg'))

@bp.route("/update-status/<int:request_id>", methods=["POST"])
@limiter.exempt
def update_status(request_id):
    req = Request.query.get_or_404(request_id)
    new_status = request.form.get("status")

    if new_status not in ["Approve", "Reject"]:
        flash("Invalid status value.", "error")
        return redirect(url_for('request_bp.request_page'))

    if req.group_code:  
        # --- Handle Group Requests ---
        group_requests = Request.query.filter_by(group_code=req.group_code).all()
        for r in group_requests:
            r.status = new_status
            if new_status == "Approve":
                r.approved_by_id = current_user.id if current_user.is_authenticated else None
        db.session.commit()

        socketio.emit('dashboard_update')
        socketio.emit('request_update')
        flash(f"Group {req.group_code} has been {new_status.lower()}ed.", "success")

        if new_status == "Approve":
            try:
                send_group_qr_email(group_requests)
                flash("Group QR codes sent successfully!", "success")
            except Exception as e:
                flash(f"Failed to send group QR emails: {str(e)}", "danger")

    else:
        # --- Handle Single Request ---
        req.status = new_status
        if new_status == "Approve":
            req.approved_by_id = current_user.id if current_user.is_authenticated else None
        db.session.commit()

        socketio.emit('dashboard_update')
        socketio.emit('request_update')
        flash(f"Request has been {new_status.lower()}ed.", "success")

        if new_status == "Approve" and all([req.name, req.email, req.number, req.purpose, req.person_to_visit]):
            visitor = Visitor.query.filter_by(email=req.email).first()

            if not visitor:
                permanent_qr = generate_unique_secure_code()
                visitor = Visitor(
                    name=req.name,
                    email=req.email,
                    number=req.number,
                    qr_code=permanent_qr,
                    last_purpose=req.purpose,
                    last_person_to_visit=req.person_to_visit
                )
                db.session.add(visitor)
                db.session.commit()
                req.unique_code = permanent_qr
                db.session.commit()

                try:
                    send_visitor_qr_email(req)
                    flash("QR code generated and sent via email.", "success")
                except Exception as e:
                    flash(f"Failed to send email: {str(e)}", "danger")
            else:
                visitor.last_purpose = req.purpose
                visitor.last_person_to_visit = req.person_to_visit
                db.session.commit()
                req.unique_code = visitor.qr_code
                db.session.commit()
                flash("Visitor's details updated and QR code reused.", "success")

        elif new_status == "Approve":
            flash("Incomplete request data. Cannot approve visitor.", "warning")

    return redirect(url_for('request_bp.request_page'))

@bp.route('/Multi-form-entry', methods=['GET', 'POST'])
@limiter.exempt
@csrf.exempt
def multi_form_entry():
    if request.method == 'POST':
        idx = 1
        group_code = secrets.token_urlsafe(12)  # Shared group code
        created_requests = []

        while True:
            first_name = request.form.get(f'first_name_{idx}')
            last_name = request.form.get(f'last_name_{idx}')
            if not first_name or not last_name:
                break

            middle_initial = request.form.get(f'middle_initial_{idx}')
            phone = request.form.get(f'phone_{idx}')
            email = request.form.get(f'email_{idx}')
            no_email = request.form.get(f'no_email_{idx}')
            purpose = request.form.get(f'purpose_{idx}')
            other_purpose = request.form.get(f'other_purpose_{idx}')
            person_to_visit = request.form.get(f'person_to_visit_{idx}')
            final_purpose = other_purpose if purpose == 'Other' else purpose
            full_name = f"{first_name} {middle_initial or ''} {last_name}".strip()

            # Match single registration: empty string if no email
            email = "" if no_email else (email or "").strip()

            # Unique code (10 chars for consistency with model)
            unique_code = secrets.token_urlsafe(8)[:10]

            # Create request
            new_request = Request(
                name=full_name,
                email=email,
                number=phone,
                purpose=final_purpose,
                person_to_visit=person_to_visit,
                unique_code=unique_code,
                status="Pending",
                timestamp=datetime.utcnow(),
                group_code=group_code
            )
            created_requests.append(new_request)

            idx += 1

        db.session.add_all(created_requests)
        db.session.commit()
        socketio.emit('request_update')

        flash(f"{len(created_requests)} requests submitted! Awaiting approval.", "success")
        return redirect(url_for('request_bp.multi_form_entry'))

    return render_template('Multi-form-entry.html')

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
        # --- CSV Upload ---
        if ext == "csv":
            df = pd.read_csv(file)

        # --- Excel Upload ---
        elif ext in ["xlsx", "xls"]:
            df = pd.read_excel(file)

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
        email = str(row.get("Email", "")).strip()
        phone = str(row.get("Phone", "")).strip()
        purpose = str(row.get("Purpose", "")).strip()
        person_to_visit = str(row.get("PersonToVisit", "")).strip()

        if not full_name or not phone or not purpose or not person_to_visit:
            continue  # skip incomplete rows

        unique_code = secrets.token_urlsafe(8)[:10]

        new_request = Request(
            name=full_name,
            email=email,
            number=phone,
            purpose=purpose,
            person_to_visit=person_to_visit,
            unique_code=unique_code,
            status="Pending",
            timestamp=datetime.utcnow(),
            group_code=group_code
        )
        created_requests.append(new_request)

    if created_requests:
        db.session.add_all(created_requests)
        db.session.commit()
        socketio.emit("request_update")
        flash(f"{len(created_requests)} requests uploaded successfully!", "success")
    else:
        flash("No valid rows found in the file.", "warning")

    return redirect(url_for("request_bp.request_page"))
