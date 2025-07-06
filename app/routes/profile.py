from flask import Blueprint, request, flash, redirect, session, url_for, current_app, render_template
from app.models import db, User
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from app.utils.totp import generate_totp_secret, get_totp_uri, generate_qr_code_base64
from app import csrf
import os

bp = Blueprint('profile', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route("/create-account", methods=["POST"])
@csrf.exempt
def create_account():
    if 'role' not in session or session['role'] != 'admin':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('main.setting'))

    username = request.form.get("new_username", "").strip()
    email = request.form.get("new_email", "").strip()
    password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")
    role = request.form.get("role", "user")

    # Basic validation
    if not username or not email or not password or not confirm_password:
        flash("All fields are required.", "danger")
        return redirect(url_for('main.setting'))

    if password != confirm_password:
        flash("Passwords do not match.", "danger")
        return redirect(url_for('main.setting'))

    if User.query.filter_by(email=email).first():
        flash("Email already exists.", "danger")
        return redirect(url_for('main.setting'))

    if User.query.filter_by(username=username).first():
        flash("Username already exists.", "danger")
        return redirect(url_for('main.setting'))

    # Create new user
    new_user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        role=role
    )
    db.session.add(new_user)
    db.session.commit()
    flash("Account created successfully!", "success")
    return redirect(url_for('main.setting'))

@bp.route("/update-profile", methods=["POST"])
@csrf.exempt
def update_profile():
    if 'user_id' not in session:
        flash("You must be logged in to update your profile.", "danger")
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('main.setting'))

    new_username = request.form.get("name", "").strip()
    new_email = request.form.get("email", "").strip()
    new_password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    # Check for duplicate email or username (if changed)
    if new_email != user.email and User.query.filter_by(email=new_email).first():
        flash("Email already exists.", "danger")
        return redirect(url_for('main.setting'))

    if new_username != user.username and User.query.filter_by(username=new_username).first():
        flash("Username already exists.", "danger")
        return redirect(url_for('main.setting'))

    if new_password and new_password != confirm_password:
        flash("Passwords do not match.", "danger")
        return redirect(url_for('main.setting'))

    enable_2fa = request.form.get("two-factor") == "on"
    if enable_2fa and not user.two_factor_enabled:
        # Enable 2FA: generate secret and show QR
        user.totp_secret = generate_totp_secret()
        user.two_factor_enabled = True
        db.session.commit()
        # Show QR code for setup
        uri = get_totp_uri(user.totp_secret, user.email)
        qr_base64 = generate_qr_code_base64(uri)
        flash("Scan this QR code with your authenticator app.", "info")
        return render_template("Setting.html", user=user, qr_base64=qr_base64, secret=user.totp_secret, active_tab="2fa")
    elif not enable_2fa and user.two_factor_enabled:
        # Disable 2FA
        user.totp_secret = None
        user.two_factor_enabled = False
        db.session.commit()
        flash("Two-factor authentication disabled.", "info")

    # Handle profile picture upload
    file = request.files.get('profile_picture')
    if file and file.filename:
        filename = secure_filename(file.filename)
        # Use the actual static folder (project root/static/profile_pics)
        static_folder = os.path.abspath(os.path.join(current_app.root_path, '..', 'static', 'profile_pics'))
        os.makedirs(static_folder, exist_ok=True)
        file_path = os.path.join(static_folder, filename)
        file.save(file_path)
        user.profile_picture = filename
        print("Profile picture uploaded successfully:", filename)

    user.username = new_username
    user.email = new_email
    if new_password:
        user.password_hash = generate_password_hash(new_password)

    db.session.commit()
    flash("Profile updated successfully!", "success")
    return redirect(url_for('main.setting'))