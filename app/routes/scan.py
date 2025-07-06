from flask import Blueprint, request, jsonify
from app.models import db, VisitorLog, Request, Visitor  
from app import csrf
from app import socketio
from datetime import datetime
import uuid

bp = Blueprint('scan', __name__)

@bp.route("/scan-checkin", methods=["POST"])
@csrf.exempt
def scan_checkin():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"message": "Invalid or missing JSON data."}), 400

    unique_code = data.get("qr_data", "").strip().upper()
    if not unique_code:
        return jsonify({"message": "Invalid or missing QR code data."}), 400

    # Try finding visitor first
    visitor = Visitor.query.filter_by(qr_code=unique_code).first()

    if not visitor:
        # If no visitor found, check for an approved request with this code
        req = Request.query.filter_by(unique_code=unique_code, status="Approve").first()
        if not req:
            return jsonify({"message": "QR code or unique code not recognized."}), 404

        # Create Visitor record from the approved request
        visitor = Visitor(
            name=req.name,
            email=req.email,
            number=req.number,
            qr_code=unique_code,  # Use their approved code as permanent QR
            last_purpose=req.purpose,
            last_person_to_visit=req.person_to_visit
        )
        db.session.add(visitor)
        db.session.commit()

    # Get latest log for this visitor
    last_log = VisitorLog.query.filter_by(visitor_id=visitor.id).order_by(VisitorLog.timestamp.desc()).first()

    if not last_log or last_log.status == "Checked-Out":
        # New Check-In
        session_id = str(uuid.uuid4())
        new_log = VisitorLog(
            visitor_id=visitor.id,
            name=visitor.name,
            email=visitor.email,
            number=visitor.number,
            purpose=visitor.last_purpose,
            person_to_visit=visitor.last_person_to_visit,
            status="Checked-In",
            unique_code=unique_code,
            visit_session_id=session_id,
            timestamp=datetime.utcnow()
        )
        action = "Checked-In"
    else:
        # Check-Out
        session_id = last_log.visit_session_id
        new_log = VisitorLog(
            visitor_id=visitor.id,
            name=visitor.name,
            email=visitor.email,
            number=visitor.number,
            purpose=visitor.last_purpose,
            person_to_visit=visitor.last_person_to_visit,
            status="Checked-Out",
            unique_code=unique_code,
            visit_session_id=session_id,
            timestamp=datetime.utcnow()
        )
        action = "Checked-Out"

    db.session.add(new_log)
    db.session.commit()
    socketio.emit('dashboard_update')
    return jsonify({"message": f"{visitor.name} has been {action}."})
