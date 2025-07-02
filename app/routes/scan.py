# app/routes/scan.py
from flask import Blueprint, request, jsonify
from app.models import db, VisitorLog, Request
from app import csrf
from app import socketio

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

    request_record = Request.query.filter_by(unique_code=unique_code, status="Approve").first()
    if not request_record:
        return jsonify({"message": "Invalid or unapproved QR code."}), 404

    if request_record.code_used:
        return jsonify({"message": "This QR code has already been used and is no longer valid."}), 403

    last_log = VisitorLog.query.filter_by(unique_code=request_record.unique_code).order_by(VisitorLog.timestamp.desc()).first()
    if last_log and last_log.status == "Checked-In":
        new_log = VisitorLog(
            name=request_record.name,
            email=request_record.email,
            number=request_record.number,
            purpose=request_record.purpose,
            person_to_visit=request_record.person_to_visit,
            status="Checked-Out",
            unique_code=request_record.unique_code
        )
        db.session.add(new_log)
        request_record.code_used = True
        db.session.commit()
        socketio.emit('dashboard_update')  # Add this line
        return jsonify({"message": f"{request_record.name} has been Checked-Out.\nQR code is now expired."})
    else:
        new_log = VisitorLog(
            name=request_record.name,
            email=request_record.email,
            number=request_record.number,
            purpose=request_record.purpose,
            person_to_visit=request_record.person_to_visit,
            status="Checked-In",
            unique_code=request_record.unique_code
        )
        db.session.add(new_log)
        db.session.commit()
        socketio.emit('dashboard_update')  # Add this line
        return jsonify({"message": f"{request_record.name} has been Checked-In."})
