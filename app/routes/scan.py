# app/routes/scan.py

from flask import Blueprint, request, jsonify
from flask_login import current_user
from app.models import db, VisitorLog, Request, Visitor  
from app import csrf
from app import socketio
from datetime import datetime
import uuid

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

    # ✅ FIX: Check for an approved request FIRST to capture the approver's ID.
    req = Request.query.filter_by(unique_code=code, status="Approve").first()
    if req:
        visitor = Visitor.query.filter_by(name=req.name, number=req.number).first()
        if not visitor:
            # This logic handles cases where a visitor might not exist yet but has a request
            visitor = Visitor(
                name=req.name,
                email=req.email,
                number=req.number,
                qr_code=code, # The code used for the request is now the permanent QR
                last_purpose=req.purpose,
                last_person_to_visit=req.person_to_visit
            )
            db.session.add(visitor)
            db.session.commit()
        
        action = _process_single_visitor(visitor, code, approved_by_id=req.approved_by_id)
        return jsonify({"message": f"{visitor.name} {action}."})

    # 2. If no request is found, check if it's a returning visitor.
    visitor = Visitor.query.filter_by(qr_code=code).first()
    if visitor:
        action = _process_single_visitor(visitor, code, approved_by_id=None) # No approver for a direct check-in
        return jsonify({"message": f"{visitor.name} {action}."})

    # 3. Check if it matches a group_code
    group_requests = Request.query.filter_by(group_code=code, status="Approve").all()
    if group_requests:
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
                    last_person_to_visit=r.person_to_visit
                )
                db.session.add(visitor)
            visitors.append((visitor, r.unique_code))

            last_log = VisitorLog.query.filter_by(visitor_id=visitor.id).order_by(VisitorLog.timestamp.desc()).first()
            if last_log and last_log.status == "Checked-In":
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
    last_log = VisitorLog.query.filter_by(visitor_id=visitor.id).order_by(VisitorLog.timestamp.desc()).first()

    if not last_log or last_log.status == "Checked-Out":
        session_id = str(uuid.uuid4())
        new_log = VisitorLog(
            visitor_id=visitor.id,
            name=visitor.name,
            email=visitor.email,
            number=visitor.number,
            purpose=visitor.last_purpose,
            person_to_visit=visitor.last_person_to_visit,
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
        session_id = last_log.visit_session_id
        approved_by_id = last_log.approved_by_id
        new_log = VisitorLog(
            visitor_id=visitor.id,
            name=visitor.name,
            email=visitor.email,
            number=visitor.number,
            purpose=visitor.last_purpose,
            person_to_visit=visitor.last_person_to_visit,
            status="Checked-Out",
            unique_code=used_code,
            visit_session_id=session_id,
            timestamp=datetime.utcnow(),
            check_out_by_id=current_user.id,
            check_out_gate=current_user.gate_role,
            approved_by_id=approved_by_id
        )
        action = "Checked-Out"

    db.session.add(new_log)
    if commit:
        db.session.commit()
        socketio.emit('dashboard_update')

    return action
