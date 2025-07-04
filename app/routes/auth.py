# app/routes/auth.py
from flask import current_app
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from app.forms import ForgotPasswordForm, ResetPasswordForm
from flask_mail import Message
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import User
from app.utils.totp import verify_totp
from app.forms import LoginForm
from app import db, limiter, mail


bp = Blueprint('auth', __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("The email you entered is not registered.", "danger")
        elif not user.check_password(password):
            print("Login attempt: entered password:", password)
            print("User hash:", user.password_hash)
            flash("Incorrect password. Please try again.", "danger")
        elif user.two_factor_enabled:
            session['pending_2fa_user'] = user.id
            session['pending_2fa_pw'] = password
            return redirect(url_for("auth.totp_verify"))
        else:
            session['user_id'] = user.id
            session['email'] = user.email
            session['role'] = user.role
            flash("Login successful!", "success")
            return redirect(url_for("main.dashboard"))
    return render_template("Login.html", form=form)

@bp.route("/totp-verify", methods=["GET", "POST"])
def totp_verify():
    user_id = session.get('pending_2fa_user')
    user = User.query.get(user_id)
    if request.method == "POST":
        token = request.form.get("token")
        if user and verify_totp(token, user.totp_secret):
            session['user_id'] = user.id
            session['email'] = user.email
            session['role'] = user.role
            session.pop('pending_2fa_user', None)
            session.pop('pending_2fa_pw', None)
            flash("Login successful!", "success")
            return redirect(url_for("main.dashboard"))
        else:
            flash("Invalid authentication code.", "danger")
    return render_template("TOTPVerify.html")

@bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))

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
            msg = Message("Password Reset Request", recipients=[user.email])
            msg.body = f"To reset your password, click the following link:\n{reset_url}\nIf you did not request this, ignore this email."
            try:
                mail.send(msg)
            except Exception as e:
                print("Mail sending error:", e)
                flash("There was an issue sending the reset email. Please try again later.", "danger")
                return redirect(url_for('auth.login'))
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
        print("Old hash:", user.password_hash)
        user.set_password(form.password.data)
        print("New hash:", user.password_hash)
        db.session.add(user)
        db.session.commit()
        flash("Your password has been reset. Please log in.", "success")
        return redirect(url_for('auth.login'))
    else:
        if request.method == "POST":
            print("Form errors:", form.errors)
    return render_template("ResetPassword.html", form=form)