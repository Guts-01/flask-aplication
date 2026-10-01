import hashlib

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from .extensions import bcrypt, db
from .models import User
from .validation import normalize_email, validate_account, validate_password


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = normalize_email(request.form.get("email"))
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        error = validate_account(name, email, password)
        if not error and password != confirm:
            error = "As senhas não coincidem."
        if not error and User.query.filter(func.lower(User.email) == email).first():
            error = "Este email já está cadastrado."
        if error:
            flash(error, "error")
        else:
            db.session.add(User(
                name=name,
                email=email,
                password=bcrypt.generate_password_hash(password).decode("utf-8"),
            ))
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("Este email já está cadastrado.", "error")
            else:
                flash("Conta criada. Entre com seus dados para continuar.", "success")
                return redirect(url_for("auth.login"))
    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    if request.method == "POST":
        email = normalize_email(request.form.get("email"))
        password = request.form.get("password", "")
        user = User.query.filter(func.lower(User.email) == email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session.clear()
            login_user(user)
            session["auth_hash"] = hashlib.sha256(user.password.encode("utf-8")).hexdigest()
            return redirect(url_for("main.index"))
        flash("Email ou senha inválidos.", "error")
    return render_template("auth/login.html")


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    flash("Você saiu da sua conta.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.post("/change_password")
@login_required
def change_password():
    old_password = request.form.get("old_password", "")
    new_password = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")
    error = validate_password(new_password)
    if not bcrypt.check_password_hash(current_user.password, old_password):
        error = "A senha atual está incorreta."
    elif not error and new_password != confirm:
        error = "As novas senhas não coincidem."
    elif not error and old_password == new_password:
        error = "Escolha uma senha diferente da atual."
    if error:
        flash(error, "error")
        return redirect(url_for("main.profile"))
    current_user.password = bcrypt.generate_password_hash(new_password).decode("utf-8")
    db.session.commit()
    logout_user()
    session.clear()
    flash("Senha alterada. Entre novamente.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.post("/delete_account")
@login_required
def delete_account():
    password = request.form.get("password", "")
    if not bcrypt.check_password_hash(current_user.password, password):
        flash("Senha incorreta. Sua conta foi mantida.", "error")
        return redirect(url_for("main.profile"))
    user = db.session.get(User, current_user.id)
    logout_user()
    db.session.delete(user)
    db.session.commit()
    session.clear()
    flash("Conta excluída com sucesso.", "success")
    return redirect(url_for("auth.login"))
