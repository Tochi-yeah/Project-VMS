# app/routes/scan.py

from flask import Blueprint, request, jsonify
from flask_login import current_user
from app.models import db, VisitorLog, Request, Visitor  
from app import csrf
from app import socketio
from datetime import datetime
import uuid
import pytz
from app.utils.helpers import get_current_time

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
    purpose_from_modal = data.get("purpose")

    if not code:
        return jsonify({"message": "Invalid or missing QR code data."}), 400

    manila_tz = pytz.timezone('Asia/Manila')
    today = get_current_time().date()

    # --- UNIFIED LOGIC ---

    # 1. Check for an active INDIVIDUAL check-in (This is the CHECK-OUT case)
    last_log = db.session.query(VisitorLog).filter(
        VisitorLog.unique_code == code, 
        VisitorLog.status == "Checked-In"
    ).order_by(VisitorLog.timestamp.desc()).first()

    if last_log and last_log.timestamp.astimezone(manila_tz).date() == today:
        visitor = Visitor.query.get(last_log.visitor_id)
        action_result = _process_single_visitor(visitor, code)
        return jsonify({"message": f"{visitor.name} {action_result}."})

    # 2. Check for GROUP check-out using the group code
    # FIXED: The query is now corrected to properly join and find group members.
    group_logs_to_checkout = db.session.query(VisitorLog).join(
        Request, VisitorLog.unique_code == Request.unique_code
    ).filter(
        Request.group_code == code,
        VisitorLog.status == "Checked-In"
    ).all()
    
    if group_logs_to_checkout:
        checkout_count = 0
        for log in group_logs_to_checkout:
            if log.timestamp.astimezone(manila_tz).date() == today:
                visitor = Visitor.query.get(log.visitor_id)
                _process_single_visitor(visitor, log.unique_code, commit=False)
                checkout_count += 1
        if checkout_count > 0:
            db.session.commit()
            socketio.emit('dashboard_update')
            socketio.emit('request_update')
            return jsonify({"message": f"{checkout_count} members of group {code} Checked-Out."})


    # 3. Handle CHECK-IN logic (showing modal or processing)
    if purpose_from_modal is not None:
        req = Request.query.filter_by(unique_code=code, status="Approve").first()
        visitor = Visitor.query.filter_by(qr_code=code).first()
        
        target_visitor = None
        if req:
            target_visitor = _find_or_create_visitor(req)
            req.status = "Completed"
        elif visitor:
            target_visitor = visitor
            target_visitor.last_purpose = purpose_from_modal

        if target_visitor:
            db.session.commit()
            action = _process_single_visitor(target_visitor, code, purpose_override=purpose_from_modal)
            return jsonify({"message": f"{target_visitor.name} {action}."})
        else:
            return jsonify({"message": "Code not recognized."}), 404
    else:
        req = Request.query.filter_by(unique_code=code, status="Approve").first()
        if req:
            return jsonify({"action": "show_modal", "name": req.name, "purpose": req.purpose})

        visitor = Visitor.query.filter_by(qr_code=code).first()
        if visitor:
            return jsonify({"action": "show_modal", "name": visitor.name, "purpose": ""})
        
        group_requests = Request.query.filter_by(group_code=code, status="Approve").all()
        if group_requests:
            results = []
            for r in group_requests:
                group_visitor = _find_or_create_visitor(r)
                _process_single_visitor(group_visitor, r.unique_code, commit=False)
                results.append(f"{group_visitor.name}: Checked-In")
                r.status = "Completed"
            db.session.commit()
            socketio.emit('dashboard_update')
            socketio.emit('request_update')
            return jsonify({"message": f"Group {code} processed", "details": results})

        return jsonify({"message": "QR code or unique code not recognized."}), 404

def _find_or_create_visitor(req):
    visitor = Visitor.query.filter_by(name=req.name, number=req.number).first()
    if not visitor:
        visitor = Visitor(
            name=req.name, email=req.email, number=req.number, qr_code=req.unique_code,
            last_purpose=req.purpose, last_address=req.address
        )
        db.session.add(visitor)
        db.session.commit()
    return visitor

def _process_single_visitor(visitor, used_code, purpose_override=None, commit=True):
    last_log = VisitorLog.query.filter_by(visitor_id=visitor.id).order_by(VisitorLog.timestamp.desc()).first()
    should_check_in = True
    if last_log and last_log.status == "Checked-In":
        manila_tz = pytz.timezone('Asia/Manila')
        if last_log.timestamp.astimezone(manila_tz).date() == get_current_time().date():
            should_check_in = False

    if should_check_in:
        new_log = VisitorLog(
            visitor_id=visitor.id, name=visitor.name, email=visitor.email, number=visitor.number,
            purpose=purpose_override or visitor.last_purpose,
            address=visitor.last_address, status="Checked-In", unique_code=used_code,
            visit_session_id=str(uuid.uuid4()), timestamp=datetime.utcnow(),
            check_in_by_id=current_user.id, check_in_gate=current_user.gate_role,
            approved_by_id=current_user.id
        )
        action = "Checked-In"
    else:
        new_log = VisitorLog(
            visitor_id=visitor.id, name=visitor.name, email=visitor.email, number=visitor.number,
            purpose=last_log.purpose, address=last_log.address, status="Checked-Out",
            unique_code=used_code, visit_session_id=last_log.visit_session_id,
            timestamp=datetime.utcnow(),
            check_out_by_id=current_user.id, check_out_gate=current_user.gate_role,
            approved_by_id=last_log.approved_by_id
        )
        action = "Checked-Out"

    db.session.add(new_log)
    if commit:
        db.session.commit()
        socketio.emit('dashboard_update')
        socketio.emit('request_update')

    return action