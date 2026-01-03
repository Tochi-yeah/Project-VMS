from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import Boolean
from app import db, login_manager
import pytz
from sqlalchemy.dialects.postgresql import TIMESTAMP
from flask_login import UserMixin


class Visitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    number = db.Column(db.String(20), nullable=False)
    qr_code = db.Column(db.String(200), unique=True, nullable=False)
    unique_code = db.Column(db.String(32), unique=True, nullable=True)
    group_code = db.Column(db.String(32), nullable=True)
    last_purpose = db.Column(db.String(200))
    last_address = db.Column(db.String(100))
    last_destination = db.Column(db.String(100), nullable=False, server_default='General')

    def __repr__(self):
        return f'<Visitor {self.name}>'    

# Pending requests table
class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    number = db.Column(db.String(20), nullable=False)
    purpose = db.Column(db.String(200), nullable=False)
    destination = db.Column(db.String(100), nullable=False, server_default='General')
    address = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default="Pending")  # Optional: for future use
    timestamp = db.Column(TIMESTAMP(timezone=True), nullable=False)
    unique_code = db.Column(db.String(10), unique=True, nullable=False)
    # code_used = db.Column(db.Boolean, default=False)
    group_code = db.Column(db.String(64), nullable=True)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    approved_by = db.relationship("User", foreign_keys=[approved_by_id], backref="approved_requests", lazy="joined")

    def __repr__(self):
        return f'<Request {self.name}>'

# Logs table (after request is approved)
class VisitorLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.Integer, db.ForeignKey('visitor.id'))  # link to visitor
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    number = db.Column(db.String(20), nullable=False)
    purpose = db.Column(db.String(200), nullable=False)
    destination = db.Column(db.String(100), nullable=False, server_default='General')
    address = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'Checked-In' or 'Checked-Out'
    timestamp = db.Column(TIMESTAMP(timezone=True), nullable=False)
    unique_code = db.Column(db.String(10))
    visit_session_id = db.Column(db.String(50), nullable=True)
     # ✅ Who approved / scanned
    approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    check_in_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    check_out_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # ✅ Store explicit gate role at the time of scan
    check_in_gate = db.Column(db.String(50), nullable=True)
    check_out_gate = db.Column(db.String(50), nullable=True)

    # ✅ Explicit timestamps
    #check_in_time = db.Column(TIMESTAMP(timezone=True), nullable=True)
    #check_out_time = db.Column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    approved_by = db.relationship("User", foreign_keys=[approved_by_id], backref="logs_approved", lazy="joined")
    check_in_by = db.relationship("User", foreign_keys=[check_in_by_id], backref="logs_checked_in", lazy="joined")
    check_out_by = db.relationship("User", foreign_keys=[check_out_by_id], backref="logs_checked_out", lazy="joined")

    def __repr__(self):
        return f'<VisitorLog {self.name} - {self.status}>'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')
    gate_role = db.Column(db.String(50), nullable=True) 
    profile_picture = db.Column(db.String(255), nullable=True)
    totp_secret = db.Column(db.String(32), nullable=True)
    two_factor_enabled = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

 # ✅ Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    # Always fetch from DB so gate_role is up to date
    return User.query.get(int(user_id))