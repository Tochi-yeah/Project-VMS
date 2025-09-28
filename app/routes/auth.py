# app/routes/auth.py
from flask import current_app
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from app.forms import ForgotPasswordForm, ResetPasswordForm
from app.brevo_mailer import send_email
#Removed temporarily
#from flask_mail import Message
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import User
from app.utils.totp import verify_totp
from app.forms import LoginForm
from app import db, limiter #,mail
from flask_login import login_user, logout_user

bp = Blueprint('auth', __name__)

@bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user.two_factor_enabled:
            session['pending_2fa_user'] = user.id
            return redirect(url_for("auth.totp_verify"))
        else:
            login_user(user, remember=form.remember_me.data) 
            flash("Login successful!", "success")
            return redirect(url_for("main.dashboard"))
            
    return render_template("Login.html", form=form)

@bp.route("/totp-verify", methods=["GET", "POST"])
def totp_verify():
    user_id = session.get('pending_2fa_user')
    if not user_id:
        return redirect(url_for('auth.login'))
        
    user = User.query.get(user_id)
    if request.method == "POST":
        token = request.form.get("token")
        if user and verify_totp(token, user.totp_secret):
            login_user(user)
            session.pop('pending_2fa_user', None)
            flash("Login successful!", "success")
            return redirect(url_for("main.dashboard"))
        else:
            flash("Invalid authentication code.", "danger")
    return render_template("TOTPVerify.html")

@bp.route("/logout")
def logout():
    logout_user()
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))

# In app/routes/auth.py

@bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data.strip()
        user = User.query.filter_by(email=email).first()
        if user:
            s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
            token = s.dumps(user.email, salt='password-reset-salt')
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            
            # --- THIS IS THE CORRECTED CODE BLOCK ---
            subject = "Password Reset Request"
            html_content = f"""
            <p>To reset your password, click the following link:</p>
            <p><a href="{reset_url}">{reset_url}</a></p>
            <p>If you did not request this, please ignore this email.</p>
            """
            try:
                if not send_email(subject, html_content, user.email, user.username):
                     raise Exception("Brevo sending failed")
            except Exception as e:
                print("Mail sending error:", e)
                flash("There was an issue sending the reset email. Please try again later.", "danger")
                return redirect(url_for('auth.login'))
            # --- END OF CORRECTED BLOCK ---

        flash("If the email exists, a reset link has been sent.", "info")
        return redirect(url_for('auth.login'))
    return render_template("ForgotPassword.html", form=form, show_modal=True)

@bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    form = ResetPasswordForm()
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=3600)
    except (SignatureExpired, BadSignature):
        flash("The reset link is invalid or has expired.", "danger")
        return redirect(url_for('auth.forgot_password'))
    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Invalid reset link.", "danger")
        return redirect(url_for('auth.forgot_password'))
    
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Your password has been reset. Please log in.", "success")
        return redirect(url_for('auth.login'))
    else:
        # ✅ This block will catch and flash any form validation errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{error}", "danger")

    return render_template("ResetPassword.html", form=form)
