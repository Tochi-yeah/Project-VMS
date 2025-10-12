# app/routes/scan.py

from flask import Blueprint, request, jsonify
from flask_login import current_user
from app.models import db, VisitorLog, Request, Visitor  
from app import csrf
from app import socketio
from datetime import datetime
import uuid
import pytz
from app.utils.helpers import get_current_time # Import the time helper

bp = Blueprint('scan', __name__)

@bp.route("/scan-checkin", methods=["POST"])
@csrf.exempt
def scan_checkin():
    if not current_user.is_authenticated:
        return jsonify({"message": "Authentication required. Please log in."}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"message": "Invalid or missing JSON data."}), 400

    code = data.get("qr_data", "").strip()
    if not code:
        return jsonify({"message": "Invalid or missing QR code data."}), 400

    # 1. Check for an approved request FIRST
    req = Request.query.filter_by(unique_code=code, status="Approve").first()
    if req:
        visitor = Visitor.query.filter_by(name=req.name, number=req.number).first()
        if not visitor:
            visitor = Visitor(
                name=req.name,
                email=req.email,
                number=req.number,
                qr_code=code,
                last_purpose=req.purpose,
                last_address=req.address
            )
            db.session.add(visitor)
            db.session.commit()
        
        action = _process_single_visitor(visitor, code, approved_by_id=req.approved_by_id)
        return jsonify({"message": f"{visitor.name} {action}."})

    # 2. If no request is found, check if it's a returning visitor.
    visitor = Visitor.query.filter_by(qr_code=code).first()
    if visitor:
        action = _process_single_visitor(visitor, code, approved_by_id=None)
        return jsonify({"message": f"{visitor.name} {action}."})

    # 3. Check if it matches a group_code
    group_requests = Request.query.filter_by(group_code=code, status="Approve").all()
    if group_requests:
        # This group logic remains unchanged
        results = []
        any_checked_in = False
        visitors = []
        
        approved_by_id = group_requests[0].approved_by_id if group_requests else None

        for r in group_requests:
            visitor = Visitor.query.filter_by(name=r.name, number=r.number).first()
            if not visitor:
                visitor = Visitor(
                    name=r.name,
                    email=r.email,
                    number=r.number,
                    qr_code=r.unique_code,
                    group_code=code,
                    last_purpose=r.purpose,
                    last_address=r.address
                )
                db.session.add(visitor)
            visitors.append((visitor, r.unique_code))

            last_log = VisitorLog.query.filter_by(visitor_id=visitor.id).order_by(VisitorLog.timestamp.desc()).first()
            if last_log and last_log.status == "Checked-In":
                # Check if the last check-in was today
                manila_tz = pytz.timezone('Asia/Manila')
                now_manila = get_current_time()
                last_log_manila = last_log.timestamp.astimezone(manila_tz)
                if last_log_manila.date() == now_manila.date():
                    any_checked_in = True
        
        db.session.commit()

        if any_checked_in:
            for visitor, used_code in visitors:
                _process_single_visitor(visitor, used_code, commit=False)
                results.append(f"{visitor.name}: Checked-Out")
        else:
            for visitor, used_code in visitors:
                _process_single_visitor(visitor, used_code, approved_by_id=approved_by_id, commit=False)
                results.append(f"{visitor.name}: Checked-In")
        
        db.session.commit()
        socketio.emit('dashboard_update')
        return jsonify({"message": f"Group {code} processed", "details": results})

    return jsonify({"message": "QR code or unique code not recognized."}), 404


def _process_single_visitor(visitor, used_code, approved_by_id=None, commit=True):
    """
    Processes a check-in or check-out for a single visitor.
    If the last check-in was on a previous day, it forces a new check-in.
    """
    last_log = VisitorLog.query.filter_by(visitor_id=visitor.id).order_by(VisitorLog.timestamp.desc()).first()

    # Default action is to check-in
    should_check_in = True
    
    if last_log and last_log.status == "Checked-In":
        # A check-in exists, let's see when it was
        manila_tz = pytz.timezone('Asia/Manila')
        now_manila = get_current_time()
        last_log_manila = last_log.timestamp.astimezone(manila_tz)

        # If the last check-in was on the same day as today, then we should check them out.
        if last_log_manila.date() == now_manila.date():
            should_check_in = False

    if should_check_in:
        # This is a new visit (or a new day)
        session_id = str(uuid.uuid4())
        new_log = VisitorLog(
            visitor_id=visitor.id,
            name=visitor.name,
            email=visitor.email,
            number=visitor.number,
            purpose=visitor.last_purpose,
            address=visitor.last_address,
            status="Checked-In",
            unique_code=used_code,
            visit_session_id=session_id,
            timestamp=datetime.utcnow(),
            check_in_by_id=current_user.id,
            check_in_gate=current_user.gate_role,
            approved_by_id=approved_by_id
        )
        action = "Checked-In"
    else:
        # This is a check-out for an existing session from today
        new_log = VisitorLog(
            visitor_id=visitor.id,
            name=visitor.name,
            email=visitor.email,
            number=visitor.number,
            purpose=last_log.purpose,       # Use purpose from the original check-in
            address=last_log.address,       # Use address from the original check-in
            status="Checked-Out",
            unique_code=used_code,
            visit_session_id=last_log.visit_session_id,
            timestamp=datetime.utcnow(),
            check_out_by_id=current_user.id,
            check_out_gate=current_user.gate_role,
            approved_by_id=last_log.approved_by_id
        )
        action = "Checked-Out"

    db.session.add(new_log)
    if commit:
        db.session.commit()
        socketio.emit('dashboard_update')

    return action