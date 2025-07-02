# app/utils/helpers.py
import string
import secrets
from app.models import Request
from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print("Session user_id:", session.get('user_id'))  # <--- debug line
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

def convert_to_ph_time(ph_dt):
    if ph_dt is None:
        return "N/A"
    return ph_dt.strftime("%B %#d, %Y - %#I:%M %p")  # Windows-friendly

