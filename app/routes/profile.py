from flask import Blueprint, request, flash, redirect, session, url_for, current_app, render_template
from app.models import db, User
from flask_login import current_user
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
    if not current_user.is_authenticated or current_user.role != 'admin':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('main.setting'))

    username = request.form.get("new_username", "").strip()
    email = request.form.get("new_email", "").strip()
    password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")
    role = request.form.get("role", "user")
    gate_role = request.form.get("gate_role", "").strip()  # ✅ added

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
        role=role,
        gate_role=gate_role if gate_role else None   # ✅ save gate role
    )
    db.session.add(new_user)
    db.session.commit()
    flash("Account created successfully!", "success")
    return redirect(url_for('main.setting'))

@bp.route("/update-profile", methods=["POST"])
@csrf.exempt
def update_profile():
    if not current_user.is_authenticated:
        flash("You must be logged in to update your profile.", "danger")
        return redirect(url_for('auth.login'))

    user = current_user
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('main.setting'))

    new_username = request.form.get("name", "").strip()
    new_email = request.form.get("email", "").strip()
    new_password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    new_gate_role = request.form.get("gate_role", "").strip()  # ✅ new

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

    # ✅ Update gate role if provided
    if new_gate_role:
        user.gate_role = new_gate_role

    # Handle 2FA toggle
    enable_2fa = request.form.get("two-factor") == "on"
    if enable_2fa and not user.two_factor_enabled:
        user.totp_secret = generate_totp_secret()
        user.two_factor_enabled = True
        db.session.commit()
        uri = get_totp_uri(user.totp_secret, user.email)
        qr_base64 = generate_qr_code_base64(uri)
        flash("Scan this QR code with your authenticator app.", "info")
        return render_template(
            "Setting.html",
            user=user,
            qr_base64=qr_base64,
            secret=user.totp_secret,
            active_tab="2fa"
        )
    elif not enable_2fa and user.two_factor_enabled:
        user.totp_secret = None
        user.two_factor_enabled = False
        db.session.commit()
        flash("Two-factor authentication disabled.", "info")

    # Handle profile picture upload
    file = request.files.get('profile_picture')
    if file and file.filename:
        filename = secure_filename(file.filename)
        static_folder = os.path.abspath(os.path.join(current_app.root_path, '..', 'static', 'profile_pics'))
        os.makedirs(static_folder, exist_ok=True)
        file_path = os.path.join(static_folder, filename)
        file.save(file_path)
        user.profile_picture = filename
        print("Profile picture uploaded successfully:", filename)

    # Update other profile details
    user.username = new_username
    user.email = new_email
    if new_password:
        user.password_hash = generate_password_hash(new_password)

    db.session.commit()
    flash("Profile updated successfully!", "success")
    return redirect(url_for('main.setting'))
