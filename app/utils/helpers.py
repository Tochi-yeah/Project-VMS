import string
import secrets
from app.models import Request
from functools import wraps
from flask import session, redirect, url_for, flash
from datetime import datetime
import pytz

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print("Session user_id:", session.get('user_id'))
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def generate_unique_secure_code(length=8):
    characters = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(secrets.choice(characters) for _ in range(length))
        if not Request.query.filter_by(unique_code=code).first():
            return code

def get_current_time():
    manila_tz = pytz.timezone('Asia/Manila')
    return datetime.now(manila_tz)

def convert_to_ph_time(dt):
    if dt is None:
        return "N/A"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.utc)
    ph_dt = dt.astimezone(pytz.timezone('Asia/Manila'))
    return ph_dt.strftime("%B %#d, %Y - %#I:%M %p")