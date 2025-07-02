from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import Boolean
from app import db
import pytz


# Pending requests table
class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    number = db.Column(db.String(20), nullable=False)
    purpose = db.Column(db.String(200), nullable=False)
    person_to_visit = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default="Pending")  # Optional: for future use
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.timezone("Asia/Manila")))
    unique_code = db.Column(db.String(10), unique=True, nullable=False)
    code_used = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Request {self.name}>'

# Logs table (after request is approved)
class VisitorLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    number = db.Column(db.String(20), nullable=False)
    purpose = db.Column(db.String(200), nullable=False)
    person_to_visit = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'Checked-In' or 'Checked-Out'
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.timezone("Asia/Manila")))
    unique_code = db.Column(db.String(10))

    def __repr__(self):
        return f'<VisitorLog {self.name} - {self.status}>'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')
    profile_picture = db.Column(db.String(255), nullable=True)
    totp_secret = db.Column(db.String(32), nullable=True)
    two_factor_enabled = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)