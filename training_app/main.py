from flask import Blueprint, render_template
from flask_login import login_required


main_bp = Blueprint("main", __name__)


@main_bp.get("/")
@login_required
def index():
    return render_template("dashboard.html")


@main_bp.get("/profile")
@login_required
def profile():
    return render_template("profile.html")
