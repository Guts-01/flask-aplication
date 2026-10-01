from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from .extensions import db
from .models import User


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@admin_bp.get("/")
@admin_required
def dashboard():
    users = User.query.order_by(User.name, User.id).all()
    return render_template("admin/dashboard.html", users=users)


@admin_bp.post("/users/<int:user_id>/delete")
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash("Use a página Conta para excluir seu próprio perfil.", "error")
        return redirect(url_for("admin.dashboard"))
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    db.session.delete(user)
    db.session.commit()
    flash("Usuário excluído.", "success")
    return redirect(url_for("admin.dashboard"))
