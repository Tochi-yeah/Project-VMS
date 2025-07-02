# app/routes/request.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import db, Request
from app.utils.helpers import generate_unique_secure_code
from app.mailer import send_visitor_qr_email
from app.utils.helpers import login_required
from app import csrf, socketio, limiter

bp = Blueprint('request_bp', __name__)

@bp.route("/request")
@login_required
@csrf.exempt
@limiter.exempt
def request_page():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    pagination = Request.query.filter_by(status="Pending").paginate(page=page, per_page=per_page, error_out=False)
    requests = pagination.items
    return render_template("Request.html", requests=requests, pagination=pagination, per_page=per_page)

@bp.route("/online-reg")
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
        unique_code=unique_code
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

    if new_status in ["Approve", "Reject"]:
        req.status = new_status
        db.session.commit()
        socketio.emit('dashboard_update')  # <-- ADD THIS LINE
        socketio.emit('request_update')  # <-- ADD THIS LINE  
        flash(f"Request has been {new_status.lower()}ed.", "success")

        if new_status == "Approve" and all([req.name, req.email, req.number, req.purpose, req.person_to_visit]):
            try:
                send_visitor_qr_email(req)
                flash("QR code generated and sent via email.", "success")
            except Exception as e:
                flash(f"Failed to send email: {str(e)}", "danger")
        else:
            flash("Incomplete request data. Cannot log visitor.", "warning")
    else:
        flash("Invalid status value.", "error")

    return redirect(url_for('request_bp.request_page'))
