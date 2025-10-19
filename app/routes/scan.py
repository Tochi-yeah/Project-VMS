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
    # TWEAK: We now check for a purpose sent from the modal
    purpose_from_modal = data.get("purpose")

    if not code:
        return jsonify({"message": "Invalid or missing QR code data."}), 400

    # Your original logic to detect if this is a check-out
    last_log = VisitorLog.query.join(Visitor).filter(Visitor.qr_code == code).order_by(VisitorLog.timestamp.desc()).first()
    is_checkout = False
    if last_log and last_log.status == "Checked-In":
        manila_tz = pytz.timezone('Asia/Manila')
        if last_log.timestamp.astimezone(manila_tz).date() == get_current_time().date():
            is_checkout = True
    
    # If it's a check-out, process it immediately and exit.
    if is_checkout:
        visitor = Visitor.query.get(last_log.visitor_id)
        action = _process_single_visitor(visitor, code)
        return jsonify({"message": f"{visitor.name} {action}."})

    # TWEAK: If it's a check-in, we decide whether to show the modal or process the check-in
    if purpose_from_modal is not None:
        # A purpose was sent, so the user has confirmed the modal. We can proceed.
        req = Request.query.filter_by(unique_code=code, status="Approve").first()
        visitor = Visitor.query.filter_by(qr_code=code).first()
        
        target_visitor = None
        if req: # New registration
            target_visitor = _find_or_create_visitor(req)
            req.status = "Completed" # Mark the request as done
        elif visitor: # Returning visitor
            target_visitor = visitor
            target_visitor.last_purpose = purpose_from_modal

        if target_visitor:
            db.session.commit()
            action = _process_single_visitor(target_visitor, code, purpose_override=purpose_from_modal)
            return jsonify({"message": f"{target_visitor.name} {action}."})
        else:
            return jsonify({"message": "Code not recognized."}), 404
    else:
        # No purpose was sent. This is the initial scan. Tell the frontend to show the modal.
        req = Request.query.filter_by(unique_code=code, status="Approve").first()
        if req:
            return jsonify({"action": "show_modal", "name": req.name, "purpose": req.purpose})

        visitor = Visitor.query.filter_by(qr_code=code).first()
        if visitor:
            return jsonify({"action": "show_modal", "name": visitor.name, "purpose": visitor.last_purpose or "" })
        
        # Fallback for group codes if individual checks fail
        group_requests = Request.query.filter_by(group_code=code, status="Approve").all()
        if group_requests:
            # For simplicity, we will process group check-ins directly without a modal
            results = []
            for r in group_requests:
                group_visitor = _find_or_create_visitor(r)
                _process_single_visitor(group_visitor, r.unique_code, commit=False)
                results.append(f"{group_visitor.name}: Checked-In")
                r.status = "Completed"
            db.session.commit()
            socketio.emit('dashboard_update')
            return jsonify({"message": f"Group {code} processed", "details": results})

        return jsonify({"message": "QR code or unique code not recognized."}), 404

def _find_or_create_visitor(req):
    """Helper to find or create a visitor from a Request object."""
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
    """Your original processing function with one crucial fix."""
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
            # FIX: This correctly sets the approver to the person checking them in.
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

    return action