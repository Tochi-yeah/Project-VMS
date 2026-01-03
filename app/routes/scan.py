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
        return jsonify({"message": "Authentication required."}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"message": "Invalid or missing JSON data."}), 400

    code = (data.get("qr_data") or "").strip()
    purpose_from_modal = data.get("purpose")
    # ✅ NEW: Get destination from the modal
    destination_from_modal = data.get("destination") 

    if not code:
        return jsonify({"message": "Invalid or missing QR code data."}), 400

    manila_tz = pytz.timezone('Asia/Manila')
    today = get_current_time().date()

    # 1) Modal submission: user confirmed purpose/destination -> perform check-in
    if purpose_from_modal is not None:
        # accept single requests whether still "Approve" or already "Completed"
        req = Request.query.filter(Request.unique_code == code, Request.status.in_(["Approve", "Completed"])).first()
        visitor = Visitor.query.filter_by(qr_code=code).first()

        target_visitor = visitor or (req and _find_or_create_visitor(req))

        if not target_visitor:
            return jsonify({"message": "Code not recognized."}), 404

        # ✅ Update last purpose AND destination
        target_visitor.last_purpose = purpose_from_modal
        if destination_from_modal:
            target_visitor.last_destination = destination_from_modal
            
        if req:
            req.status = "Completed"
        db.session.commit()

        action = _process_single_visitor(target_visitor, code, approved_by_id=current_user.id)
        return jsonify({"message": f"{target_visitor.name} {action}."})

    # 2) Initial scan: decide whether to show modal or immediately check-out

    # If it's a permanent visitor record
    visitor = Visitor.query.filter_by(qr_code=code).first()
    if visitor:
        # look at the latest log entry (any status) to determine current state
        last_entry = VisitorLog.query.filter_by(visitor_id=visitor.id) \
                                     .order_by(VisitorLog.timestamp.desc()).first()
        # If latest entry is Checked-In and it's today -> this is a CHECK-OUT, process immediately
        if last_entry and last_entry.status == "Checked-In" and last_entry.timestamp.astimezone(manila_tz).date() == today:
            action = _process_single_visitor(visitor, code)
            return jsonify({"message": f"{visitor.name} {action}."})
        
        # Otherwise ALWAYS show the purpose modal for individual check-ins
        # ✅ Return existing destination to pre-fill the modal if you want (optional)
        return jsonify({
            "action": "show_modal", 
            "name": visitor.name, 
            "purpose": visitor.last_purpose or "",
            "destination": visitor.last_destination or "" 
        })

    # If not a permanent visitor, check for an individual registration (single request)
    req = Request.query.filter(Request.unique_code == code, Request.status.in_(["Approve", "Completed"])).first()
    if req:
        # ensure permanent visitor exists
        _find_or_create_visitor(req)
        return jsonify({
            "action": "show_modal", 
            "name": req.name, 
            "purpose": req.purpose or "",
            "destination": req.destination or "" 
        })

    # Check for a group code (group check-in/check-out). Group behavior unchanged.
    group_requests = Request.query.filter(Request.group_code == code, Request.status.in_(["Approve", "Completed"])).all()
    if group_requests:
        any_checked_in = False
        visitors_in_group = []
        for r in group_requests:
            v = _find_or_create_visitor(r)
            visitors_in_group.append(v)
            last_entry = VisitorLog.query.filter_by(visitor_id=v.id) \
                                         .order_by(VisitorLog.timestamp.desc()).first()
            if last_entry and last_entry.status == "Checked-In" and last_entry.timestamp.astimezone(manila_tz).date() == today:
                any_checked_in = True

        results = []
        if any_checked_in:
            # check everyone out (no modal)
            for v in visitors_in_group:
                _process_single_visitor(v, v.qr_code, commit=False)
                results.append(f"{v.name}: Checked-Out")
        else:
            # check everyone in (group flow remains automated)
            for r in group_requests:
                v = _find_or_create_visitor(r)
                _process_single_visitor(v, r.unique_code, approved_by_id=r.approved_by_id, commit=False)
                r.status = "Completed"
                results.append(f"{v.name}: Checked-In")

        db.session.commit()
        socketio.emit('dashboard_update')
        return jsonify({"message": f"Group {code} processed", "details": results})

    return jsonify({"message": "QR code or unique code not recognized."}), 404


def _find_or_create_visitor(req):
    visitor = Visitor.query.filter_by(name=req.name, number=req.number).first()
    if not visitor:
        visitor = Visitor(
            name=req.name,
            email=req.email,
            number=req.number,
            qr_code=req.unique_code,
            last_purpose=req.purpose,
            # ✅ NEW: Save destination from Request to Visitor history
            last_destination=getattr(req, "destination", "General"),
            last_address=getattr(req, "address", None)
        )
        db.session.add(visitor)
        db.session.commit()
    elif visitor.qr_code != req.unique_code:
        visitor.qr_code = req.unique_code
        db.session.commit()
    return visitor


def _process_single_visitor(visitor, used_code, approved_by_id=None, commit=True):
    last_log = VisitorLog.query.filter_by(visitor_id=visitor.id).order_by(VisitorLog.timestamp.desc()).first()
    should_check_in = True
    if last_log and last_log.status == "Checked-In":
        manila_tz = pytz.timezone('Asia/Manila')
        now_manila = get_current_time()
        last_log_manila = last_log.timestamp.astimezone(manila_tz)
        if last_log_manila.date() == now_manila.date():
            should_check_in = False

    if should_check_in:
        new_log = VisitorLog(
            visitor_id=visitor.id,
            name=visitor.name,
            email=visitor.email,
            number=visitor.number,
            purpose=visitor.last_purpose,
            # ✅ NEW: Use the updated destination
            destination=visitor.last_destination, 
            address=visitor.last_address,
            status="Checked-In",
            unique_code=used_code,
            visit_session_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            check_in_by_id=current_user.id,
            check_in_gate=current_user.gate_role,
            approved_by_id=approved_by_id or current_user.id
        )
        action = "Checked-In"
    else:
        new_log = VisitorLog(
            visitor_id=visitor.id,
            name=visitor.name,
            email=visitor.email,
            number=visitor.number,
            purpose=last_log.purpose,
            # ✅ NEW: Copy destination from previous log (or visitor history)
            destination=getattr(last_log, "destination", visitor.last_destination), 
            address=last_log.address,
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