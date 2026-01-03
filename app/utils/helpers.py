import string
import secrets
from app.models import Request
from functools import wraps
from flask import session, redirect, url_for, flash
from datetime import datetime
import pytz

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

def convert_to_ph_time_only(dt):
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.utc)
    ph_dt = dt.astimezone(pytz.timezone('Asia/Manila'))
    return ph_dt.strftime("%#I:%M %p")  # Example: 9:35 AM    
